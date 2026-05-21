# Momence Authentication & Cookie Management Reference

**Project:** Ritual Studio — Momence Data Pipeline  
**Last updated:** 2026-04-28

---

## Overview

The pipeline uses two completely separate authentication systems. Understanding the distinction is critical when something breaks.

| System | Used by | Auth method | Expires |
|---|---|---|---|
| **Browser cookies** | Selenium/Chrome scripts | Pickle file loaded into Chrome | ~10 days |
| **API OAuth** | `momence_sessions_api.py`, `momence_class_customers_api.py`, `momence_class_customers_full_api.py`, `momence_courses_sync.py` | Password-flow OAuth token, refreshed per run | Per session (auto-refreshed) |

These two systems are independent. An expired browser cookie does **not** affect the API scripts, and vice versa. When the nightly chain partially completes — API steps succeed but report downloads fail — the cookie is almost always the cause.

---

## Browser Cookie System

### What the cookie does

The browser session cookie (`ribbon.connect.sid`) is the equivalent of being logged in to `momence.com` in Chrome. All scripts that use Selenium to drive a real Chrome window inject this cookie at startup so they can access the Momence dashboard without a manual login.

### Cookie files

Two pickle files hold the same set of 22 cookies. They are written simultaneously by `momence_first_login_setup.py` and must always be in sync.

| File | Used by |
|---|---|
| `momence_cookies.pkl` | `Momence_bookings_update.py`, `momence_sessions_scrape_lite.py`, `momence_waitlist_scrape.py` (via `config.py → COOKIES_FILE`) |
| `momence_cookies.pickle` | `Momence_no_card_customers.py` |

> **Important:** If only one file is updated, scripts reading the other will still use expired cookies and fail silently at authentication.

### Cookie lifetime

Momence issues `ribbon.connect.sid` with approximately a 10-day expiry. The exact expiry is stored in the pickle and checked by `check_cookie_expiry.py` at the start of every nightly chain run. A fresh login performed at 07:41 AEST on 28 April 2026 produced a cookie expiring **2026-05-08 07:41 AEST**.

### Which scripts require the browser cookie

| Script | Role | Cookie dependent |
|---|---|---|
| `Momence_bookings_update.py` | Downloads bookings report, updates master CSV | Yes (`.pkl`) |
| `Momence_no_card_customers.py` | Downloads 6 CRM reports (no-card, penalty charges, late cancellations, no-shows, total sales, membership sales) | Yes (`.pickle`) |
| `momence_sessions_scrape_lite.py` | Scrapes session list for substitute teacher flag and waitlist count | Yes (`.pkl`) |
| `momence_waitlist_scrape.py` | Scrapes waitlist details for full classes | Yes (`.pkl`) |
| `momence_new_reports.py` | Downloads 7 KPI reports (active members, occupancy, teacher payroll, etc.) | Yes (Chrome, uses cookies indirectly) |

---

## Cookie Renewal Scripts

### ✅ Correct script: `momence_first_login_setup.py`

**This is the only script that should be used for renewal.**

What it does:
1. Opens a visible Chrome window to `https://momence.com/login`
2. Waits for the user to log in manually (handles MFA)
3. Verifies the dashboard loaded (checks the URL is not `/login`)
4. Saves all 22 cookies to **both** `momence_cookies.pickle` **and** `momence_cookies.pkl`
5. Prints a confirmation with cookie count

Run it from a terminal in the `Momence_data` folder:

```
python momence_first_login_setup.py
```

If cookies already exist, it asks for confirmation before overwriting. Allow ~2 minutes for the login process.

---

### ❌ Wrong script: `get_pickle_2.py`

This is an older prototype. It does the same manual-login process but **only saves to `momence_cookies.pkl`** — it does not write `momence_cookies.pickle`. Running it leaves `Momence_no_card_customers.py` and any other script that reads `.pickle` operating with a stale, expired cookie.

**Do not use this script.** It exists as a development artefact and should be considered obsolete. The file can be deleted or renamed to avoid confusion.

---

### `check_cookie_expiry.py` — Monitoring only, not renewal

This script does **not** renew cookies. It reads the expiry timestamp from `momence_cookies.pickle` and:

- If expiry is more than 48 hours away: logs `OK` to `Momence_batch_log.txt`
- If expiry is within 48 hours: logs `WARN` and attempts to create a Google Calendar reminder
- If already expired: logs `ERROR` and attempts the same calendar reminder

It runs automatically as Step 0 of `Run_Momence_Chain.bat`. The batch chain continues regardless of the result — an expired cookie does not halt the chain, it simply causes individual steps to fail when they attempt to authenticate.

**Current status (as of 2026-04-28):** The Google Calendar reminder function is broken. The OAuth refresh token for the Google Calendar API has been revoked (`invalid_grant`). To fix it, run `check_cookie_expiry.py` interactively once in a terminal — it will open a browser window to re-authorise Google Calendar access and save a new `token.json`.

---

## API OAuth System

Scripts that access the Momence API directly use OAuth Password Flow, configured via the `.env` file in the `Momence_data` folder.

**Credentials required in `.env`:**

```
MOMENCE_CLIENT_ID
MOMENCE_CLIENT_SECRET
MOMENCE_USERNAME       # Staff email address
MOMENCE_PASSWORD       # Staff password
MOMENCE_HOST_ID        # From the Momence dashboard URL
```

These credentials are managed by `momence_api_client.py`, which handles token acquisition, automatic token refresh when the access token nears expiry, and re-authentication on failure. Unlike the browser cookie, this system is fully self-managing and does not require any manual intervention under normal operation.

Additional credentials in `.env`:
- `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` — used by `momence_courses_sync.py` to write training course and enrolment data to Supabase.

---

## Google Calendar Alert System

`check_cookie_expiry.py` is designed to create a calendar event at 9am Brisbane time when the cookie is within 48 hours of expiry. The event is titled **"ACTION REQUIRED: Refresh Momence login cookie"** and includes a popup reminder 30 minutes before and an email reminder 1 hour before.

**Files involved:**
- `credentials.json` — OAuth client credentials downloaded from Google Cloud Console
- `token.json` — Saved OAuth token (refreshed automatically); last written 2026-03-17. This is the file that needs to be regenerated.

To reauthorise, open a terminal and run:

```
python check_cookie_expiry.py
```

On first run after token expiry, a browser window will open asking for Google account authorisation. Approve it, and a new `token.json` will be saved. Subsequent automated runs will use it silently.

---

## Nightly Chain — Cookie-Related Steps

The chain (`Run_Momence_Chain.bat`) runs at 02:00 AEST. Step order and cookie dependency:

| Step | Script | Cookie needed | Fatal if fails |
|---|---|---|---|
| 0 | `check_cookie_expiry.py` | Reads `.pickle` | No |
| 1a | `momence_sessions_api.py p` | No (API OAuth) | No (retry at 03:00) |
| 1b | `momence_sessions_api.py f` | No (API OAuth) | No |
| 1c | `momence_sessions_scrape_lite.py` | Yes (`.pkl`) | No (non-fatal) |
| 2 | `extract_full_classes2.py` | No | Yes |
| 3 | `momence_class_customers_full_api.py` | No (API OAuth) | Yes |
| 4 | `momence_waitlist_scrape.py` | Yes (`.pkl`) | Yes |
| 5 | `Momence_bookings_update.py` | Yes (`.pkl`) | Yes |
| 6 | `Momence_no_card_customers.py` | Yes (`.pickle`) | Yes |
| 7 | `extract_all_classes_1.py` | No | Yes |
| 8 | `momence_class_customers_api.py` | No (API OAuth) | Yes |
| 9 | `momence_courses_sync.py` | No (API OAuth + Supabase) | Yes |
| 10 | `momence_new_reports.py` | Yes (Chrome) | No (non-fatal) |

A separate scheduled task (`Run_Momence_Retry_Past.bat`) runs at 03:00 AEST and re-runs the past sessions API scraper if today's output file is absent. This acts as a safety net for transient Step 1a failures (e.g., 504 gateway timeouts).

---

## What Happened on 2026-04-28

A brief chronology for reference:

| Time (AEST) | Event |
|---|---|
| 2026-04-27 02:17 | Cookie expiry warning — 3h remaining |
| 2026-04-27 05:17 | `ribbon.connect.sid` expired |
| 2026-04-28 01:02 | `Momence_bookings_update.py` pre-chain run failed — cookie expired |
| 2026-04-28 02:00 | Chain started; `check_cookie_expiry.py` logged ERROR; API steps ran fine; browser steps (Steps 4–6, 10) failed silently or aborted; chain never logged completion |
| 2026-04-28 07:41 | `momence_first_login_setup.py` run manually; both cookie files refreshed; new expiry 2026-05-08 07:41 AEST |

The 28 April chain did not produce: bookings update, no-card customers, penalty charges, late cancellations, no-shows, total sales, membership sales, class customers (all classes), courses sync, or new reports. These will need to be run manually once to recover the missed day.

---

## Quick Reference — Renewal Procedure

1. Open a terminal in `C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\`
2. Run: `python momence_first_login_setup.py`
3. Log in manually in the Chrome window that opens (email, password, MFA if prompted)
4. Wait for the dashboard to load, then press Enter in the terminal
5. Confirm that both files are reported as saved with 22 cookies

Do **not** run `get_pickle_2.py` — it is the wrong script.

**Next renewal due:** approximately **2026-05-06** (48-hour warning will appear in `Momence_batch_log.txt` on that date, assuming the Google Calendar token has been fixed).
