"""
check_cookie_expiry.py
----------------------
Checks whether the Momence session cookie (ribbon.connect.sid) expires within
the next 48 hours. If so, creates a Google Calendar event at 9am (Brisbane
time) as a reminder to re-run momence_first_login_setup.py.

Requirements:
    pip install google-api-python-client google-auth-oauthlib google-auth-httplib2

First run: opens a browser window to authorise access to Google Calendar.
Subsequent runs: uses the saved token.json silently.
"""

import pickle
import datetime
import os
import sys

from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR      = os.path.dirname(os.path.abspath(__file__))
COOKIE_PICKLE   = os.path.join(SCRIPT_DIR, "momence_cookies.pickle")
CREDENTIALS_JSON = os.path.join(SCRIPT_DIR, "credentials.json")
TOKEN_JSON      = os.path.join(SCRIPT_DIR, "token.json")

SESSION_COOKIE  = "ribbon.connect.sid"   # The cookie that controls login
WARNING_HOURS   = 48                      # Alert when expiry is within this many hours
TIMEZONE        = "Australia/Brisbane"    # AEST — no DST
CALENDAR_ID     = "primary"
# Master batch log — moved out of OneDrive on 2026-05-18 to stop sync locks
# truncating writes. Falls back to the legacy in-tree path if the local
# folder is absent (e.g. clean checkout on a new machine).
_LOCAL_BATCH_LOG_DIR = r"C:\Users\markj\Momence_local_logs"
if os.path.isdir(_LOCAL_BATCH_LOG_DIR):
    BATCH_LOG_FILE = os.path.join(_LOCAL_BATCH_LOG_DIR, "Momence_batch_log.txt")
else:
    BATCH_LOG_FILE = os.path.join(SCRIPT_DIR, "Log_files", "Momence_batch_log.txt")

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

# ---------------------------------------------------------------------------
# Batch log helper
# ---------------------------------------------------------------------------

def append_to_batch_log(message: str) -> None:
    """Append a timestamped line to the shared Momence_batch_log.txt.

    Retries up to 3 times (2-second gap) to handle transient OneDrive locks.
    Falls back to stderr so the message appears in the chain log.
    """
    import time
    os.makedirs(os.path.dirname(BATCH_LOG_FILE), exist_ok=True)
    line = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n"
    for attempt in range(3):
        try:
            with open(BATCH_LOG_FILE, "a", encoding="utf-8") as bf:
                bf.write(line)
            return
        except Exception as exc:
            if attempt < 2:
                time.sleep(2)
            else:
                print(f"[BATCH LOG WRITE FAILED after 3 attempts: {exc}] {line.rstrip()}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_session_cookie_expiry():
    """Return the expiry datetime (UTC) of ribbon.connect.sid, or None."""
    if not os.path.exists(COOKIE_PICKLE):
        print(f"[ERROR] Cookie pickle not found: {COOKIE_PICKLE}")
        sys.exit(1)

    with open(COOKIE_PICKLE, "rb") as f:
        cookies = pickle.load(f)

    for c in cookies:
        if c.get("name") == SESSION_COOKIE:
            exp = c.get("expiry")
            if exp:
                return datetime.datetime.fromtimestamp(exp, tz=datetime.timezone.utc)
            else:
                print(f"[INFO] {SESSION_COOKIE} is a session cookie with no fixed expiry.")
                return None

    print(f"[WARN] Cookie '{SESSION_COOKIE}' not found in pickle.")
    return None


def get_calendar_service():
    """Authenticate and return a Google Calendar API service object."""
    creds = None

    if os.path.exists(TOKEN_JSON):
        creds = Credentials.from_authorized_user_file(TOKEN_JSON, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_JSON):
                print(f"[ERROR] credentials.json not found at: {CREDENTIALS_JSON}")
                print("        Download it from Google Cloud Console → APIs & Services → Credentials.")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_JSON, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_JSON, "w") as f:
            f.write(creds.to_json())
        print("[INFO] Google Calendar token saved to token.json.")

    return build("calendar", "v3", credentials=creds)


def next_9am(tz_name):
    """Return the next 9am in the given timezone (today if before 9am, else tomorrow)."""
    tz = ZoneInfo(tz_name)
    now = datetime.datetime.now(tz)
    candidate = now.replace(hour=9, minute=0, second=0, microsecond=0)
    if now >= candidate:
        candidate += datetime.timedelta(days=1)
    return candidate


def reminder_already_exists(service):
    """Return True if a reminder event with the same summary already exists in the future."""
    now_utc = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
    result = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=now_utc,
        q="ACTION REQUIRED: Refresh Momence login cookie",
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    events = result.get("items", [])
    return len(events) > 0


def create_calendar_event(service, expiry_utc):
    """Create a Google Calendar event at the next 9am Brisbane time."""
    if reminder_already_exists(service):
        print("[INFO] Calendar reminder already exists — skipping duplicate creation.")
        return None

    event_start = next_9am(TIMEZONE)
    event_end   = event_start + datetime.timedelta(hours=1)

    expiry_local = expiry_utc.astimezone(ZoneInfo(TIMEZONE))
    expiry_str   = expiry_local.strftime("%A %d %B %Y at %I:%M %p")

    event = {
        "summary": "ACTION REQUIRED: Refresh Momence login cookie",
        "description": (
            f"The Momence session cookie ({SESSION_COOKIE}) expires on {expiry_str} "
            f"(Brisbane time).\n\n"
            "Run momence_first_login_setup.py to refresh it before the batch chain fails.\n\n"
            "Location: Momence_data folder"
        ),
        "start": {
            "dateTime": event_start.isoformat(),
            "timeZone": TIMEZONE,
        },
        "end": {
            "dateTime": event_end.isoformat(),
            "timeZone": TIMEZONE,
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup",  "minutes": 30},
                {"method": "email",  "minutes": 60},
            ],
        },
        "colorId": "11",  # Tomato red
    }

    created = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    print(f"[INFO] Calendar event created: {created.get('htmlLink')}")
    return created


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("[INFO] Checking Momence session cookie expiry...")

    expiry_utc = load_session_cookie_expiry()
    if expiry_utc is None:
        print("[INFO] No fixed expiry found. Skipping calendar check.")
        append_to_batch_log(f"check_cookie_expiry.py — no fixed expiry found for {SESSION_COOKIE}")
        return

    now_utc      = datetime.datetime.now(tz=datetime.timezone.utc)
    hours_left   = (expiry_utc - now_utc).total_seconds() / 3600
    expiry_local = expiry_utc.astimezone(ZoneInfo(TIMEZONE))
    expiry_str   = expiry_local.strftime("%Y-%m-%d %H:%M %Z")

    print(f"[INFO] {SESSION_COOKIE} expires: {expiry_local.strftime('%A %d %B %Y at %I:%M %p')} Brisbane time")
    print(f"[INFO] Hours remaining: {hours_left:.1f}")

    if hours_left <= 0:
        print("[WARN] Cookie has already expired! Re-run momence_first_login_setup.py immediately.")
        append_to_batch_log(
            f"check_cookie_expiry.py ERROR — cookie expired {expiry_str}. "
            "Run momence_first_login_setup.py immediately."
        )
        try:
            service = get_calendar_service()
            create_calendar_event(service, expiry_utc)
            append_to_batch_log("check_cookie_expiry.py — Google Calendar reminder created.")
        except Exception as cal_err:
            print(f"[WARN] Could not create Google Calendar reminder (token may need re-auth): {cal_err}")
            print("[WARN] To fix: run check_cookie_expiry.py interactively once to refresh the Google token.")
            append_to_batch_log(
                f"check_cookie_expiry.py WARN — Calendar reminder failed (token needs re-auth): {cal_err}"
            )
    elif hours_left <= WARNING_HOURS:
        print(f"[WARN] Cookie expires within {WARNING_HOURS} hours — creating calendar reminder.")
        append_to_batch_log(
            f"check_cookie_expiry.py WARN — cookie expires in {hours_left:.0f}h ({expiry_str}). "
            "Calendar reminder attempted."
        )
        try:
            service = get_calendar_service()
            create_calendar_event(service, expiry_utc)
            append_to_batch_log("check_cookie_expiry.py — Google Calendar reminder created.")
        except Exception as cal_err:
            print(f"[WARN] Could not create Google Calendar reminder (token may need re-auth): {cal_err}")
            print("[WARN] To fix: run check_cookie_expiry.py interactively once to refresh the Google token.")
            append_to_batch_log(
                f"check_cookie_expiry.py WARN — Calendar reminder failed (token needs re-auth): {cal_err}"
            )
    else:
        print(f"[INFO] Cookie is fine — {hours_left:.1f} hours remaining. No action needed.")
        append_to_batch_log(
            f"check_cookie_expiry.py OK — {hours_left:.0f}h remaining, expires {expiry_str}"
        )


if __name__ == "__main__":
    main()
