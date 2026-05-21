"""
momence_weekly.py

High-level behaviour
--------------------
1. Decide WHAT date range to download:
   - If a master CSV already exists, find the most recent booking date in it.
     Use that datetime as the start of the new download window.
   - Otherwise (first run), start from a configured default date.
   - Always end at "yesterday 23:59" (local time), then convert both to UTC
     for Momence's URL parameters.

2. Use Selenium + Chrome to:
   - Launch Chrome with download preferences so CSV files are saved directly
     into a specific OneDrive folder WITHOUT showing the save dialog.
   - Load cookies from a pickle file (if present) to keep you logged in.
   - Open the report URL with the computed date range.
   - Wait for the report to be ready and click the "Download CSV" button.
   - Wait until the CSV has finished downloading.

3. Append the weekly CSV to the master CSV:
   - Read the new CSV and the master CSV with pandas.
   - Construct a deduplication key from:
        Sale Date
        Class Name
        Class Date
        Location
        Teacher
        Customer Email
   - Concatenate and drop duplicates on that key.
   - Save back to the master file and optionally move the weekly CSV to an
     Archive subfolder.

Schedule:
---------
Use Windows Task Scheduler to run:

   python "C:\\full\\path\\to\\momence_weekly.py"

once per day or week, as you prefer. [web:27][web:30]
"""

import os
import sys
import time
import glob
import pickle
from datetime import datetime, timedelta

import pandas as pd  # for CSV reading/writing and de-duplication [web:20][web:35]
from dateutil import tz  # convenient time-zone handling [web:26]

from selenium import webdriver  # Selenium main entry [web:7]
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ==============================
# 1. USER CONFIGURATION SECTION
# ==============================

# --- OneDrive paths (EDIT THESE) ---

# Folder where Chrome should automatically download the weekly Momence CSV.
DOWNLOAD_DIR = r"C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\momence_downloads"

# Full path to your master CSV (combined bookings).
MASTER_FILE = r"C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\master_bookings.csv"

# Optional archive folder where downloaded weekly CSVs are moved after processing.
ARCHIVE_DIR = os.path.join(DOWNLOAD_DIR, "Archive")


# --- Momence account / URL details (EDIT THESE) ---

# Your Momence "session bookings" base URL with placeholders for startDate and endDate.
# NOTE: This is based on the example you gave. Adjust parameters if your URL differs.
MOMENCE_URL_TEMPLATE = (
    "https://momence.com/dashboard/32083/reports/session-bookings"
    "?startDate={start}"
    "&endDate={end}"
    "&preset=-1"
)

# If Momence expects UTC timestamps like "2024-12-31T14:00:00.000Z" then
# the format below is appropriate.
MOMENCE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.000Z"


# --- Login cookie pickle (EDIT PATH IF YOU LIKE) ---
# This file will store cookies once you have logged in manually in this Selenium browser.
COOKIE_PICKLE = r"C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\momence_cookies.pkl"


# --- Default start date if master file DOES NOT exist (EDIT IF NEEDED) ---

DEFAULT_START_LOCAL = datetime(2025, 1, 1, 0, 0, 0)  # local datetime for first-ever run


# --- Column names used in CSVs (SHOULD MATCH MOMENCE EXPORT HEADERS) ---

COL_SALE_DATE = "Sale Date"
COL_CLASS_NAME = "Class Name"
COL_CLASS_DATE = "Class Date"
COL_LOCATION = "Location"
COL_TEACHER = "Teacher"
COL_CUSTOMER_EMAIL = "Customer Email"


# --- CSS or XPath selector for the "Download CSV" button (MUST EDIT) ---
# Open the Momence report page in Chrome, inspect the download button,
# and copy a stable CSS selector or XPath into one of these.

DOWNLOAD_BUTTON_BY = By.XPATH
DOWNLOAD_BUTTON_SELECTOR = "//button[contains(., 'Download summary')]"

# ^ This is just an EXAMPLE. Replace the selector with the real one from the page.


# --- Timezone handling ---
# Change this if your local timezone is different.
LOCAL_TZ = tz.gettz(
    "Australia/Brisbane"
)  # AEST without DST; adjust if needed. [web:26]


# --- Miscellaneous timing parameters ---

PAGE_LOAD_TIMEOUT = 300  # seconds to wait for the report to be ready
DOWNLOAD_WAIT_TIMEOUT = 300  # seconds to wait for CSV to finish downloading
POLL_INTERVAL = 2  # seconds between polling attempts when waiting


# =========================
# 2. DATE RANGE CALCULATION
# =========================


def ensure_directories():
    """Create necessary directories if they do not exist."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)


def get_date_range_from_master():
    """
    Decide the start and end datetimes for the Momence query.

    - If MASTER_FILE exists:
        * Read it with pandas.
        * Parse COL_SALE_DATE as datetime.
        * Use the maximum Sale Date as start_dt_local.
        * SUBTRACT 14 DAYS from that date to capture status updates for recent classes.
          (Momence updates No show/Cancelled status after classes occur)
    - Otherwise:
        * Use DEFAULT_START_LOCAL.

    - Then set end_dt_local to "yesterday at 23:59" in LOCAL_TZ.
      (Changed 2026-05-02 from "3 days ago" to "yesterday" — Mark wants
      near-real-time data in the dashboard. Trade-off: the 60-day rolling
      re-read window below catches retrospective Momence updates to
      status/cancellation, so the original 3-day buffer was redundant.
      Same-day bookings are still excluded because Momence's Sales report
      can take a few hours to settle a "today" entry.)

    - Window WAS 14 days; widened to 60 on 2026-05-02 after empirical
      evidence (v3 reconciliation probe) that cancellations made >14 days
      after the original Sale Date were being silently lost. 60 catches
      essentially all real-world advance-booking cancellations; the long
      tail beyond 60 days is unlikely to matter operationally.
    - Finally, convert both to UTC and format them as Momence expects.

    Returns:
        start_str (str): formatted UTC start timestamp for URL.
        end_str (str): formatted UTC end timestamp for URL.
        start_dt_local (datetime): local start datetime (for logging).
        end_dt_local (datetime): local end datetime (for logging).
    """
    # Determine local date "yesterday" at 23:59. The 14-day rolling re-read
    # of the start date below remains the safety net for late-arriving
    # status updates (no-show / cancel / late-cancel).
    now_local = datetime.now(LOCAL_TZ)
    target_date_local = now_local.date() - timedelta(days=1)
    end_dt_local = datetime(
        year=target_date_local.year,
        month=target_date_local.month,
        day=target_date_local.day,
        hour=23,
        minute=59,
        second=0,
        tzinfo=LOCAL_TZ,
    )

    # Determine start date from master, or default.
    if os.path.exists(MASTER_FILE):
        df_master = pd.read_csv(MASTER_FILE)
        # Parse Sale Date as datetime; adjust format if needed. [web:23][web:26]
        df_master[COL_SALE_DATE] = pd.to_datetime(
            df_master[COL_SALE_DATE], errors="coerce"
        )
        latest = df_master[COL_SALE_DATE].max()
        if pd.isna(latest):
            # Fallback if parsing failed or column empty.
            start_dt_local = DEFAULT_START_LOCAL.replace(tzinfo=LOCAL_TZ)
        else:
            # Use latest booking as start, but go back 60 days to capture status updates.
            # Momence updates No show/Cancelled/Late Cancelled status after classes occur,
            # so we need to re-download recent records to get accurate attendance data.
            # Window widened from 14 → 60 days on 2026-05-02 (see comment block above).
            # 2026-05-02: widened from 14 to 60 days. The 14-day window
            # silently lost late status updates on advance bookings (see
            # Memberships_Dashboard_Investigation_2026-05-01.md Priority 1.7
            # and the v3 reconciliation probe finding for class_id=129596742).
            start_dt_local = latest - timedelta(days=60)
            if start_dt_local.tzinfo is None:
                # If parsed as naive, assume local timezone.
                start_dt_local = start_dt_local.replace(tzinfo=LOCAL_TZ)
    else:
        # First run: start from configured default.
        start_dt_local = DEFAULT_START_LOCAL.replace(tzinfo=LOCAL_TZ)

    # Convert to UTC for Momence URL.
    start_dt_utc = start_dt_local.astimezone(tz.UTC)
    end_dt_utc = end_dt_local.astimezone(tz.UTC)

    # Format according to Momence's expected format.
    start_str = start_dt_utc.strftime(MOMENCE_TIME_FORMAT)
    end_str = end_dt_utc.strftime(MOMENCE_TIME_FORMAT)

    print(f"[INFO] Start (local): {start_dt_local}  -> URL: {start_str}")
    print(f"[INFO] End   (local): {end_dt_local}  -> URL: {end_str}")

    return start_str, end_str, start_dt_local, end_dt_local


# ==============================
# 3. SELENIUM / BROWSER HANDLING
# ==============================


def create_chrome_driver():
    """
    Create and return a Selenium Chrome WebDriver configured to:

    - Download files automatically into DOWNLOAD_DIR.
    - Suppress the "save as" dialog for downloads. [web:31][web:32]

    You must have ChromeDriver installed that matches your Chrome version. [web:7]
    """
    chrome_options = Options()

    # IMPORTANT for automated downloads: set the default directory and disable prompt.
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        # Optionally: avoid automatic opening of certain file types after download.
        "download.extensions_to_open": "",
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # Optional: run headless (no visible browser window).
    # For initial debugging, keep this commented out.
    # chrome_options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    return driver


def load_cookies_if_available(driver):
    """
    Load Momence cookies from COOKIE_PICKLE if it exists.

    - This assumes you have previously logged in to Momence in this Selenium
      browser and saved the cookies using save_cookies(). [web:7]

    - If the pickle does not exist, this function does nothing; you will then
      need to manually log in once, and call save_cookies() afterwards.
    """
    if not os.path.exists(COOKIE_PICKLE):
        print("[INFO] No cookie pickle found; you may need to log in manually.")
        return

    driver.get("https://momence.com/")  # base domain so cookies apply.
    try:
        with open(COOKIE_PICKLE, "rb") as f:
            cookies = pickle.load(f)
        for cookie in cookies:
            # Selenium requires expiry to be int; some cookies may not have it.
            cookie.pop("sameSite", None)
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"[WARN] Unable to add cookie {cookie.get('name')}: {e}")
        print("[INFO] Cookies loaded from pickle.")
    except Exception as e:
        print(f"[WARN] Failed to load cookies: {e}")


def save_cookies(driver):
    """
    Save current browser cookies to COOKIE_PICKLE.

    - Use this AFTER you have logged into Momence in the Selenium-driven
      browser. [web:7]
    """
    cookies = driver.get_cookies()
    with open(COOKIE_PICKLE, "wb") as f:
        pickle.dump(cookies, f)
    print("[INFO] Cookies saved to pickle.")


def dismiss_loading_report_popup(driver, max_wait=10):
    """If Momence's 'Loading report' modal appears, click its Close button.

    The modal blocks pointer events on the toolbar and, when it closes,
    causes the React tree to remount the 'Download summary' button,
    which has been the source of the chromedriver crash on attempt 1.
    Polls for up to max_wait seconds. Returns True if dismissed, False
    otherwise. Never raises.
    """
    end = time.time() + max_wait
    while time.time() < end:
        try:
            modal = driver.find_element(
                By.XPATH,
                "//*[contains(normalize-space(.), 'Loading report')]"
                "/ancestor::*[self::div or self::section][1]",
            )
            if modal.is_displayed():
                close_btn = modal.find_element(
                    By.XPATH, ".//button[normalize-space()='Close']"
                )
                close_btn.click()
                print("[INFO] Dismissed 'Loading report' popup.")
                time.sleep(1)
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _try_dismiss_loading_report_popup(driver):
    """Single-pass version of dismiss_loading_report_popup. Safe to call
    on every iteration of a poll loop — does NOT internally sleep beyond
    the 1 s post-click settle. Returns True if a popup was just dismissed.

    Tries multiple selector strategies, since Momence's modal wrapper
    has changed shape in the past. The reliable invariant is: a 'Close'
    button exists somewhere whose page contains the 'Loading report'
    heading at the same time. We use that as the anchor.
    """
    # First confirm the 'Loading report' modal is on screen at all.
    try:
        heading = driver.find_element(
            By.XPATH, "//*[normalize-space(text())='Loading report']"
        )
        if not heading.is_displayed():
            return False
    except Exception:
        return False

    # Now find a visible 'Close' button anywhere on the page. The first
    # visible match in document order is the one inside the modal because
    # the modal sits at the top of the stack.
    candidate_xpaths = [
        # Close button whose ancestor contains the 'Loading report' text
        "//button[normalize-space()='Close' and "
        "ancestor::*[contains(normalize-space(.), 'Loading report')]]",
        # Any visible Close button (broadest fallback)
        "//button[normalize-space()='Close']",
        # Some Momence dialogs use an inner span for the label
        "//button[.//span[normalize-space()='Close']]",
    ]
    for xp in candidate_xpaths:
        try:
            for btn in driver.find_elements(By.XPATH, xp):
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    print("[INFO] Dismissed 'Loading report' popup.")
                    time.sleep(1)
                    return True
        except Exception:
            continue

    # Heading is showing but no Close button matched. Print this at most
    # once per Python process so we have diagnostic evidence without
    # flooding the log when the wait loop runs for several minutes.
    if not getattr(_try_dismiss_loading_report_popup, "_warned", False):
        print(
            "[WARN] 'Loading report' modal visible but no 'Close' button "
            "matched any of the candidate selectors."
        )
        _try_dismiss_loading_report_popup._warned = True
    return False


def open_report_and_download(driver, start_str, end_str):
    """
    Using an existing Selenium driver:

    1. Build the Momence report URL from start_str and end_str.
    2. Navigate to that URL.
    3. Wait for the "Download CSV" button to be present and clickable.
    4. Click the button to start the CSV download. [web:7]

    NOTE: On first ever run, you may need to:
      - Let the page open.
      - Log in manually (email + password + authenticator).
      - Optionally then call save_cookies(driver) in an interactive run.
    """
    url = MOMENCE_URL_TEMPLATE.format(start=start_str, end=end_str)
    print(f"[INFO] Opening report URL: {url}")

    driver.get(url)
    time.sleep(3)

    # Check if redirected to login page (cookies expired)
    if "sign-in" in driver.current_url or "login" in driver.current_url:
        raise Exception(
            "Authentication failed - redirected to login page. "
            "Cookies have expired. Run: python momence_first_login_setup.py"
        )

    dismiss_loading_report_popup(driver)

    print("[INFO] Waiting for download button to become clickable...")
    deadline = time.time() + PAGE_LOAD_TIMEOUT
    button = None
    while time.time() < deadline:
        # Dismiss the 'Loading report' modal if it has appeared at any
        # point during the wait — Momence shows it only after the report
        # has been loading for a while, so a one-shot check before this
        # loop is not enough.
        if _try_dismiss_loading_report_popup(driver):
            time.sleep(1)
        try:
            candidate = driver.find_element(
                DOWNLOAD_BUTTON_BY, DOWNLOAD_BUTTON_SELECTOR
            )
            if candidate.is_displayed() and candidate.is_enabled():
                button = candidate
                break
        except Exception:
            pass
        time.sleep(1)

    if button is None:
        # Capture diagnostics before raising — previous failures gave us only
        # the bare exception message, so we never knew whether the page had
        # loaded, was showing an error overlay, or had a different DOM.
        try:
            diag_dir = os.path.join(DOWNLOAD_DIR, "diagnostics")
            os.makedirs(diag_dir, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            shot = os.path.join(diag_dir, f"download_button_missing_{stamp}.png")
            html = os.path.join(diag_dir, f"download_button_missing_{stamp}.html")
            try:
                driver.save_screenshot(shot)
                print(f"[DIAG] Screenshot saved: {shot}")
            except Exception as _e:
                print(f"[DIAG] Screenshot failed: {_e}")
            try:
                with open(html, "w", encoding="utf-8") as _fh:
                    _fh.write(driver.page_source)
                print(f"[DIAG] Page source saved: {html}")
            except Exception as _e:
                print(f"[DIAG] Page source dump failed: {_e}")
            print(f"[DIAG] Current URL: {driver.current_url}")
            print(f"[DIAG] Page title : {driver.title}")
        except Exception as _e:
            print(f"[DIAG] Diagnostic capture failed entirely: {_e}")
        raise Exception(
            f"Download button never became clickable within {PAGE_LOAD_TIMEOUT}s"
        )

    # Three-strategy click cascade.  The native Selenium click has historically
    # failed silently or raised "element not interactable" on Momence's reports
    # page when the button is briefly overlaid by a loading spinner or React
    # rerender.  JavaScript click bypasses interactability checks; ActionChains
    # is a last-resort native-mouse fallback that also handles cases where the
    # element is technically off-screen.
    print("[INFO] Clicking download button...")
    click_errors = []
    try:
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", button)
        except Exception:
            pass
        button.click()
        return
    except Exception as exc:
        click_errors.append(f"native: {exc}")

    try:
        driver.execute_script("arguments[0].click();", button)
        print("[INFO] Native click failed; JavaScript click succeeded.")
        return
    except Exception as exc:
        click_errors.append(f"javascript: {exc}")

    try:
        ActionChains(driver).move_to_element(button).pause(0.3).click().perform()
        print("[INFO] Native + JS clicks failed; ActionChains click succeeded.")
        return
    except Exception as exc:
        click_errors.append(f"action_chains: {exc}")

    raise Exception(
        "Download button could not be clicked with any strategy: "
        + " | ".join(click_errors)
    )


# =====================================
# 4. WAIT FOR DOWNLOAD & FIND NEW FILE
# =====================================


def wait_for_new_download(before_files):
    """
    Wait until a new CSV appears in DOWNLOAD_DIR that was not in before_files,
    and all temporary '.crdownload' files are gone. [web:32][web:33]

    Arguments:
        before_files (set[str]): set of file paths present before clicking download.

    Returns:
        new_file (str): path to the new CSV file, or None if timeout.
    """
    print("[INFO] Waiting for CSV to be fully downloaded...")

    end_time = time.time() + DOWNLOAD_WAIT_TIMEOUT
    while time.time() < end_time:
        # All CSV files currently present.
        csv_files = set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv")))

        # Check for Chrome temporary download files (.crdownload).
        temp_files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.crdownload"))

        # Look for any CSV not in 'before_files'.
        new_files = csv_files - before_files

        if new_files and not temp_files:
            # When at least one new CSV exists and there are no temp files,
            # we assume the download is finished.
            new_file = max(new_files, key=os.path.getmtime)
            print(f"[INFO] New CSV detected: {new_file}")
            return new_file

        time.sleep(POLL_INTERVAL)

    print("[ERROR] Timed out waiting for the CSV download.")
    return None


# ================================
# 5. APPEND & DE-DUPLICATE MASTER
# ================================

# Split the combined 'Class Date' column into separate Date and Time columns
# This allows the dashboard to join bookings and classes with 100% precision.
def build_dedupe_key(df):
    """
    Refined dedupe key using core identifiers and the new Class Time column.
    """
    # Verify mandatory columns exist
    required_cols = [COL_CLASS_NAME, COL_CLASS_DATE, COL_LOCATION, COL_CUSTOMER_EMAIL]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Expected column '{col}' not found in CSV.")

    def normalize(series):
        return series.astype(str).str.strip().str.upper()

    # --- DEFINE THE VARIABLES (This fixes the 'not defined' error) ---
    c_name  = normalize(df[COL_CLASS_NAME])
    c_date  = normalize(df[COL_CLASS_DATE])
    c_loc   = normalize(df[COL_LOCATION])
    c_email = normalize(df[COL_CUSTOMER_EMAIL])

    # Use Class Time if it was created by the split logic; otherwise use empty string
    c_time  = normalize(df['Class Time']) if 'Class Time' in df.columns else ""

    # Combine them into the final key
    df["dedupe_key"] = (
        c_name  + "|" +
        c_date  + "|" +
        c_time  + "|" +
        c_loc   + "|" +
        c_email
    )

    return df


def append_and_dedupe(new_csv_path):
    """
    Append the newly downloaded CSV to the master CSV and remove duplicates.

    Steps:
    ------
    1. Read the new CSV.
    2. If MASTER_FILE exists, read it; otherwise, create an empty DataFrame
       with the same columns as the new CSV.
    3. Add 'dedupe_key' to both DataFrames.
    4. Concatenate and drop duplicates on 'dedupe_key', keeping the NEWEST records
       from the newly downloaded CSV (which have the most up-to-date information). [web:35]
    5. Save combined DataFrame back to MASTER_FILE.
    6. Move the new CSV into ARCHIVE_DIR (optional but recommended).
    """
    print(f"[INFO] Reading new weekly CSV: {new_csv_path}")
    df_new = pd.read_csv(new_csv_path)

# --- UPDATED SPLIT LOGIC ---
    # Use 'df_new' because that is the variable name in this function
    if 'Class Date' in df_new.columns:
        # Split "2026-04-12, 16:30" into separate Date and Time
        if df_new['Class Date'].str.contains(',').any():
            split_cols = df_new['Class Date'].str.split(',', expand=True)
            df_new['Class Date'] = split_cols[0].str.strip()
            df_new['Class Time'] = split_cols[1].str.strip()
 # ---------------------------
    if os.path.exists(MASTER_FILE):
        print(f"[INFO] Reading existing master CSV: {MASTER_FILE}")
        df_master = pd.read_csv(MASTER_FILE)
        # 2. Split Logic for EXISTING master data (Migration)
        # This handles records saved before this modification was added.
        if 'Class Date' in df_master.columns:
            # Only split rows that still contain a comma
            mask = df_master['Class Date'].astype(str).str.contains(',')
            if mask.any():
                split_master = df_master.loc[mask, 'Class Date'].str.split(',', expand=True)
                df_master.loc[mask, 'Class Date'] = split_master[0].str.strip()
                df_master.loc[mask, 'Class Time'] = split_master[1].str.strip()


    else:
        print("[INFO] Master CSV does not exist yet; will create a new one.")
        df_master = pd.DataFrame(columns=df_new.columns)

    original_master_len = len(df_master)

    # Build dedupe keys for both old and new. [web:35][web:37]
    df_new = build_dedupe_key(df_new)
    df_master = build_dedupe_key(df_master)

    # Concatenate and drop duplicates based on 'dedupe_key', keeping the LAST occurrence
    # (which is from the newly downloaded CSV with the most current information).
    combined = pd.concat([df_master, df_new], ignore_index=True)
    before = len(combined)
    combined = combined.drop_duplicates(subset="dedupe_key", keep="last")
    after = len(combined)

    print(f"[INFO] Rows before de-duplication: {before}")
    print(f"[INFO] Rows after  de-duplication: {after}")
    print(f"[INFO] Removed {before - after} duplicate rows.")

    # Drop 'dedupe_key' before saving.
    combined = combined.drop(columns=["dedupe_key"])

    combined.to_csv(MASTER_FILE, index=False)
    print(f"[INFO] Master CSV updated: {MASTER_FILE}")

    # Move weekly CSV to archive folder.
    base_name = os.path.basename(new_csv_path)
    archive_path = os.path.join(ARCHIVE_DIR, base_name)
    os.replace(new_csv_path, archive_path)
    print(f"[INFO] Weekly CSV moved to archive: {archive_path}")

    added = after - original_master_len
    return added


# ============
# 6. MAIN FLOW
# ============


_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_BATCH_LOG = os.path.join(_SCRIPT_DIR, "Log_files", "Momence_batch_log.txt")


def _batch_log(message):
    """Append a timestamped message to Momence_batch_log.txt.

    Retries up to 3 times (2-second gap) to handle transient OneDrive locks.
    Falls back to stderr so the message appears in the chain log.
    """
    os.makedirs(os.path.dirname(_BATCH_LOG), exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} - {message}\n"
    for attempt in range(3):
        try:
            with open(_BATCH_LOG, "a", encoding="utf-8") as f:
                f.write(line)
            return
        except Exception as exc:
            if attempt < 2:
                time.sleep(2)
            else:
                print(
                    f"[BATCH LOG WRITE FAILED after 3 attempts: {exc}] {line.rstrip()}",
                    file=sys.stderr,
                )


def main():
    ensure_directories()
    _batch_log("Momence_bookings_update.py started")

    # 1. Compute date range.
    start_str, end_str, start_dt_local, end_dt_local = get_date_range_from_master()

    # 2. Attempt download with up to 5 tries (Chrome occasionally crashes on large reports).
    max_attempts = 5
    new_csv_path = None

    for attempt in range(1, max_attempts + 1):
        driver = create_chrome_driver()
        try:
            # 3. Load cookies if available.
            load_cookies_if_available(driver)

            # NOTE: On the *very first* run, you may want to:
            #   - comment out load_cookies_if_available()
            #   - driver.get("https://momence.com/login") and log in manually
            #   - then call save_cookies(driver)
            # so that future runs can be fully unattended.

            # Keep track of files that already exist before we click download.
            before_files = set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv")))

            # 4. Open report and click download.
            open_report_and_download(driver, start_str, end_str)

            # 5. Wait for the CSV file to appear and finish downloading.
            new_csv_path = wait_for_new_download(before_files)
            if not new_csv_path:
                print("[ERROR] No new CSV file detected; aborting append.")
                _batch_log(
                    f"ERROR: Momence_bookings_update.py - failed to download CSV from {start_dt_local} to {end_dt_local}"
                )
                sys.exit(1)

            break  # Success – exit retry loop

        except Exception as e:
            print(f"[ERROR] Exception occurred (attempt {attempt}/{max_attempts}): {e}")
            if attempt < max_attempts:
                print("[INFO] Retrying with a fresh Chrome instance...")
                _batch_log(
                    f"WARNING: Momence_bookings_update.py - Chrome crash on attempt {attempt}, retrying: {e}"
                )
            else:
                _batch_log(
                    f"ERROR: Momence_bookings_update.py - failed after {max_attempts} attempts from {start_dt_local} to {end_dt_local}: {e}"
                )
                sys.exit(1)

        finally:
            # Always close the browser.
            try:
                driver.quit()
            except Exception:
                pass

    # 6. Append new CSV to master and de-duplicate.
    try:
        added = append_and_dedupe(new_csv_path)
        print("[INFO] All done.")
        _batch_log(
            f"Momence_bookings_update.py completed OK — {added} records added to Bookings from {start_dt_local} to {end_dt_local}"
        )
    except Exception as e:
        print(f"[ERROR] Exception during append: {e}")
        _batch_log(
            f"ERROR: Momence_bookings_update.py - exception during append from {start_dt_local} to {end_dt_local}: {e}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
