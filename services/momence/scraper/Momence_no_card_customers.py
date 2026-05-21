"""
Momence_no_card_customers.py

Contains Selenium download and CSV processing functions for six Momence
reports. Each report function downloads a CSV, appends it to its master
CSV (with deduplication and data cleanup), and archives the raw download.

NOTE on entry point: when run directly (python Momence_no_card_customers.py),
__main__ currently only executes the Membership Sales update
(create_or_update_master_membership_sales). The other five report functions
are defined here and are called from an external batch/orchestration script.

Reports
-------
1. No Card Customers  - CRM customers with no payment card on file.
   Download file: Momence-Customers.csv (renamed to Momence-No-Card-Customers.csv)
   Deduplication key: Customer Email.
   URL: static (filter pre-encoded in MOMENCE_CRM_URL).

2. Failed Penalty Charges - Declined penalty charges from the last 4 weeks.
   Download file: momence-failed-penaly-charges-report.csv
   Deduplication key: Customer Name + Amount + Last Fail date.
   Requires: click "Apply filters" after page load before downloading.
   Data cleanup: removes "Home location" column.

3. Late Cancellations - Late-cancelled bookings from the last 4 weeks.
   Download file: late-cancellations-report.csv
   Deduplication key: Customer Name + Cancelled Class + Cancelled Date.
   Requires: click "Apply filters" after page load before downloading.
   Data cleanup: fills blank "Membership name" with "blank"; fills blank
   "Penalty charged" with 0; removes "Home location" column.

4. No Shows - No-show bookings from the last 4 weeks.
   Download file: momence-no-shows-report.csv
   Deduplication key: Customer Name + Class + Class Date.
   Requires: click "Apply filters" after page load before downloading.
   Data cleanup: fills blank "Membership used" with "blank"; fills blank
   "Penalty charged" with 0; removes "Home location" column.
   Note: also extracts Class Numbers from page links (in addition to
   Customer Numbers).

5. Total Sales - All sales transactions.
   Download file: momence-latest-payments-report.csv
   Deduplication key: Date + Sale reference.
   Date range: 1 day before most recent sale in master to yesterday.
   Initial load (no master data): 9 Dec 2025 to yesterday.

6. Membership Sales - Membership purchase transactions.
   Download file: membership-sales-report.csv (renamed from Chrome default).
   Master file: master_membership_sales_summary.csv
   Deduplication: full-row .drop_duplicates() (no keyed column).
   Date range: 1 day before most recent sale in master to yesterday.
   Initial load (no master data): 1 July 2025 to yesterday.
   Special: converts "Bought Date/Time (GMT)" to "Sale Date" in
   Australia/Brisbane timezone.
   Utility: process_manual_membership_sales() can process a manually
   downloaded history file instead of triggering a Selenium download.

For reports 2-6 the script builds a dynamic date range URL
(timestamps expressed as UTC, calculated from Brisbane timezone UTC+10).

Download Button Strategy (open_report_and_download)
----------------------------------------------------
Four strategies are attempted in order for each report:
1. Open the three-dots menu button first, then click the download option.
   This is the primary strategy — Momence's current UI always puts the
   download option inside a dropdown.  Uses a 3s per-selector probe so
   failures are fast.
2. Direct XPath wait for the button (5s timeout) — for pages where the
   button is directly visible without a dropdown.
2b. Icon-attribute JS fallback — find the button containing the
   download_outline_20 icon and JS-click it (bypasses overlay issues).
3. JavaScript text scan of all clickable elements.
If all strategies fail, the page source is saved to
Log_files/debug_page_source_no_button.html for diagnostics.

Customer / Class Number Extraction
-----------------------------------
After page load (before downloading), customer IDs are scraped from
/crm/{id} links and class IDs from /sessions/{id} links on the report page.
These are added as "Customer Number" and "Class Number" columns to the
master CSV.

Files Created / Updated
-----------------------
Master CSVs (appended with new records, duplicates removed):
  Momence-No-Card-Customers.csv         - No Card Customers
  master_failed_penalties.csv           - Failed Penalty Charges
  master_late_cancellations.csv         - Late Cancellations
  master_no_shows.csv                   - No Shows
  master-sales-summary.csv              - Total Sales
  master_membership_sales_summary.csv   - Membership Sales

Downloaded CSVs (moved here after processing):
  momence_downloads\\Archive\\

Cookie file (created by momence_first_login_setup.py, read by this script):
  momence_cookies.pickle

Debug files (created only when a download button cannot be found):
  Log_files/debug_page_source_no_button.html

All paths are relative to the script directory:
  C:\\Users\\markj\\OneDrive - MFPL\\Documents\\Customer Projects\\Ritual\\Momence_data\\

Authentication
--------------
Cookie-based (NOT form submission).
- First run: execute  python momence_first_login_setup.py  and log in
  manually.  Cookies are saved to momence_cookies.pickle.
- Subsequent runs: cookies are loaded automatically - no interaction
  needed.  Works with Windows Task Scheduler.
- Credentials can also be set via MOMENCE_USERNAME / MOMENCE_PASSWORD
  environment variables or a .env file in the script directory.
"""

import os
import time
import glob
import pickle
import traceback
import re
import io
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print("[INFO] Loaded credentials from .env file")
    else:
        print("[INFO] No .env file found, using environment variables")
except ImportError:
    print("[WARN] python-dotenv not installed - skipping .env loading")
    print("[INFO] Install with: pip install python-dotenv")


import pandas as pd  # for CSV reading/writing and de-duplication

from selenium import webdriver  # Selenium main entry
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ==============================
# 1. USER CONFIGURATION SECTION
# ==============================

# --- OneDrive paths (EDIT THESE) ---

# Folder where Chrome should automatically download the CSV.
DOWNLOAD_DIR = r"C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\momence_downloads"

# Full path to your master CSV (combined customers).
MASTER_FILE = r"C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\Momence-No-Card-Customers.csv"

# Full path to your master CSV for failed penalties.
MASTER_PENALTIES_FILE = r"C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\master_failed_penalties.csv"

# Full path to your master CSV for late cancellations.
MASTER_LATE_CANCELLATIONS_FILE = r"C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\master_late_cancellations.csv"

# Full path to your master CSV for no shows.
MASTER_NO_SHOWS_FILE = r"C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\master_no_shows.csv"

# Full path to your master CSV for total sales.
MASTER_SALES_FILE = r"C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\master-sales-summary.csv"

# Optional archive folder where downloaded CSVs are moved after processing.
ARCHIVE_DIR = os.path.join(DOWNLOAD_DIR, "Archive")


# --- Momence Report URLs ---

# The URL for the "No Card" customers report.
MOMENCE_CRM_URL = "https://momence.com/dashboard/32083/crm?f=eyJ0eXBlIjoiYW5kIiwiZnV0dXJlQm9va2luZ3MiOnsiY291bnQiOnsidHlwZSI6Im1vcmVUaGFuIiwidmFsdWUiOjB9fSwicGFyZW50c0NoaWxkcmVuIjpbIm5vbi1jaGlsZHJlbiJdLCJjdXN0b21lclRhZ3MiOnsidHlwZSI6bnVsbCwidGFncyI6WzEzNDMxOV0sImN1c3RvbWVySGF2ZVRhZyI6ImhhdmUifX0%3D&tab=ALL_CUSTOMERS_TAB"

# Base URL for the "Failed Penalty Charges" report (dates will be injected).
MOMENCE_PENALTIES_BASE_URL = "https://momence.com/dashboard/32083/reports/declined-penalty-charges/7954094?computedSaleValue=true&excludeCustomersWithoutVisits=false&excludeGiftCardPaymentMethod=false&excludeInactiveMembers=false&excludeMembershipRenews=false&groupRecurring=false&hideVoided=false&hostId=32083&includeCustomersActivityLog=false&includeCustomersDetails=false&includeRefunds=false&includeVatInRevenue=true&moneyCreditSalesFilter=filterOutSalesPaidByMoneyCredits&preset=-1&preset2=-1&showOnlySpotfillerRevenue=false&timeZone=Australia%2FBrisbane&useBookedEntityDateRange=false"

# Base URL for the "Late Cancellations" report (dates will be injected).
MOMENCE_LATE_CANCELLATIONS_BASE_URL = "https://momence.com/dashboard/32083/reports/late-cancellations/7952318?computedSaleValue=true&excludeCustomersWithoutVisits=false&excludeGiftCardPaymentMethod=false&excludeInactiveMembers=false&excludeMembershipRenews=false&groupRecurring=false&hideVoided=false&hostId=32083&includeCustomersActivityLog=false&includeCustomersDetails=false&includeRefunds=false&includeVatInRevenue=true&moneyCreditSalesFilter=filterOutSalesPaidByMoneyCredits&preset=-1&preset2=-1&showOnlySpotfillerRevenue=false&timeZone=Australia%2FBrisbane&useBookedEntityDateRange=false"

# Base URL for the "No Shows" report (dates will be injected).
MOMENCE_NO_SHOWS_BASE_URL = "https://momence.com/dashboard/32083/reports/no-shows/7954137?computedSaleValue=false&excludeCustomersWithoutVisits=false&excludeGiftCardPaymentMethod=false&excludeInactiveMembers=false&excludeMembershipRenews=false&groupRecurring=false&hideVoided=false&hostId=32083&includeCustomersActivityLog=false&includeCustomersDetails=false&includeRefunds=false&includeVatInRevenue=false&moneyCreditSalesFilter=filterOutSalesPaidByMoneyCredits&preset=-1&showOnlySpotfillerRevenue=false&timeZone=Australia%2FBrisbane&useBookedEntityDateRange=false"

# Base URL for the "Total Sales" report (dates will be injected).
MOMENCE_SALES_BASE_URL = "https://momence.com/dashboard/32083/reports/total-sales/7959682?computedSaleValue=true&excludeCustomersWithoutVisits=false&excludeGiftCardPaymentMethod=false&excludeInactiveMembers=false&excludeMembershipRenews=false&groupRecurring=false&hideVoided=false&hostId=32083&includeCustomersActivityLog=false&includeCustomersDetails=false&includeRefunds=false&includeVatInRevenue=true&moneyCreditSalesFilter=filterOutSalesPaidByMoneyCredits&preset=-1&preset2=-1&showOnlySpotfillerRevenue=false&subFilters=%5B%7B%2210%22%3A%22%5B%5D%22%7D%5D&timeZone=Australia%2FBrisbane&useBookedEntityDateRange=false"

# Initial start date for Total Sales (first load covers 9 Dec 2025 to yesterday).
SALES_INITIAL_START_DATE = datetime(2025, 12, 9)


# --- Login Credentials ---
# Set these credentials for automatic login (or use environment variables)
# Environment variable names: MOMENCE_USERNAME, MOMENCE_PASSWORD
MOMENCE_USERNAME = os.environ.get(
    "MOMENCE_USERNAME", ""
)  # Leave empty to use env var or prompt
MOMENCE_PASSWORD = os.environ.get(
    "MOMENCE_PASSWORD", ""
)  # Leave empty to use env var or prompt

# --- Login cookie pickle (EDIT PATH IF YOU LIKE) ---
# This file will store cookies once you have logged in manually in this Selenium browser.
COOKIE_PICKLE = r"C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\momence_cookies.pickle"


# --- Column names used in CSVs (SHOULD MATCH MOMENCE EXPORT HEADERS) ---

# No Card Customers report
COL_CUSTOMER_EMAIL = "Email"
COL_CUSTOMER_FIRST_NAME = "First Name"
COL_CUSTOMER_LAST_NAME = "Last Name"

# Failed Penalties report
COL_PENALTIES_CUSTOMER_NAME = "Customer Name"
COL_PENALTIES_DATE = "Last fail"

# Late Cancellations report
COL_LATE_CANCEL_CUSTOMER_NAME = "Customer name"  # Note: lowercase 'n'
COL_LATE_CANCEL_CLASS = "Cancelled Class"
COL_LATE_CANCEL_DATE = "Cancelled Date"

# No Shows report
COL_NO_SHOWS_CUSTOMER_NAME = "Customer Name"
COL_NO_SHOWS_CLASS_NAME = "Class"  # Not "Class Name"
COL_NO_SHOWS_CLASS_DATE = "Class Date"

# Total Sales report
COL_SALES_DATE = "Date"
COL_SALES_REFERENCE = "Sale reference"


# --- CSS or XPath selector for the menu button (three dots) ---
# Open the Momence CRM page, inspect the three dots button.

MENU_BUTTON_BY = By.CSS_SELECTOR
MENU_BUTTON_SELECTOR = "#page-scroll > section > div.sc-1xb42nd-9.eRZSPm > div > div > div > div.ud8ncp-3.hVzPpy > div.ud8ncp-2.eUHHfp > button.sc-1kz352d-4.gjiXBQ.fpjope-0.ixALIZ.ud8ncp-0.iOFXRv"


# --- Selector for the download button ---
DOWNLOAD_BUTTON_BY = By.XPATH
DOWNLOAD_BUTTON_SELECTOR = "//button[contains(., 'Download summary')]"

# --- Miscellaneous timing parameters ---

PAGE_LOAD_TIMEOUT = 300  # seconds to wait for the report to be ready
DOWNLOAD_WAIT_TIMEOUT = 300  # seconds to wait for CSV to finish downloading
POLL_INTERVAL = 2  # seconds between polling attempts when waiting


# =========================
# 2. SELENIUM / BROWSER HANDLING
# =========================
# Browser setup, authentication, and page interaction functions
# Features:
# - Automated Chrome launch with download preferences
# - Cookie-based session authentication
# - Robust button detection and clicking mechanisms
# - Comprehensive error logging and debugging


def ensure_directories():
    """Create necessary directories if they do not exist."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)


def create_chrome_driver():
    """
    Create and return a Selenium Chrome WebDriver configured to:

    - Download files automatically into DOWNLOAD_DIR.
    - Suppress the "save as" dialog for downloads.

    You must have ChromeDriver installed that matches your Chrome version.
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

    # Memory optimization: disable unnecessary features to reduce resource usage.
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument(
        "--disable-dev-shm-usage"
    )  # Overcome limited resource problems
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")

    # Optional: run headless (no visible browser window).
    # For initial debugging, keep this commented out.
    # chrome_options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    return driver


def load_cookies_if_available(driver):
    """
    Load Momence cookies from COOKIE_PICKLE if it exists.

    This function enables fully unattended operation by restoring your authenticated
    session using previously saved browser cookies.

    How it works:
    - Navigates to Momence base domain (so cookies apply correctly)
    - Loads all cookies from the pickle file
    - Removes incompatible attributes (sameSite) for Selenium compatibility
    - Handles per-cookie failures gracefully (skips problematic cookies)

    Setup:
    - First run: Use momence_first_login_setup.py to create momence_cookies.pickle
    - Subsequent runs: This function automatically loads those cookies

    If the pickle file does not exist:
    - This function does nothing (no error)
    - You'll need to run momence_first_login_setup.py to generate it

    Cookie expiration:
    - Cookies typically expire after 30 days of inactivity
    - If the script stops working, regenerate cookies using the setup script
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

    This function is called by momence_first_login_setup.py after you manually
    log into Momence. It persists your authenticated session so that future runs
    can use the saved cookies instead of requiring manual login.

    How it works:
    - Extracts all cookies from the current browser session
    - Serializes them to a pickle file for safe storage
    - Enables fully unattended operation on subsequent runs

    Note:
    - Cookies contain your encrypted session, NOT your password
    - Keep the pickle file secure like you would a browser session
    - If cookies expire or are compromised, simply re-run the setup script
    """
    cookies = driver.get_cookies()
    with open(COOKIE_PICKLE, "wb") as f:
        pickle.dump(cookies, f)
    print("[INFO] Cookies saved to pickle.")


def debug_log(message):
    """
    Simple logging function that prints to console.
    """
    print(message)


def _wait_apply_filters_idle(driver, timeout=180):
    """Wait until the 'Apply filters' button becomes enabled again.

    After Apply Filters is clicked, Momence disables the button while the
    underlying API request is in flight and the report renders. Polling for
    re-enablement is a more reliable "report finished" signal than the old
    fixed 15-second sleep — which caused the 2026-05-12 No Shows failure on
    a slow render. Returns True if the button became enabled within the
    timeout, False otherwise. The caller continues either way (the existing
    'Loading report...' text wait is applied immediately afterwards).
    """
    deadline = time.time() + timeout
    poll = 2
    while time.time() < deadline:
        try:
            state = driver.execute_script(
                """
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => /apply\\s*filters?/i.test(b.textContent || ''));
                if (!btn) return 'missing';
                if (btn.disabled || btn.getAttribute('aria-disabled') === 'true') return 'disabled';
                return 'ready';
                """
            )
            if state == "ready":
                debug_log("[INFO] 'Apply filters' is idle again — report ready to fetch")
                return True
            if state == "missing":
                return True
        except Exception as e:
            debug_log(f"[DEBUG] _wait_apply_filters_idle probe failed: {e}")
        time.sleep(poll)
    debug_log(
        f"[WARN] 'Apply filters' still disabled after {timeout}s – proceeding anyway"
    )
    return False


def wait_for_new_download(before_files, timeout=DOWNLOAD_WAIT_TIMEOUT):
    """
    Wait for a new CSV file to appear in the download directory.

    Args:
        before_files (set): Set of file paths that existed before download
        timeout (int): Maximum seconds to wait for download

    Returns:
        str: Full path to the new downloaded CSV file, or None if timeout
    """
    print(f"[INFO] Waiting up to {timeout} seconds for new CSV file...")
    print(f"[DEBUG] Download directory: {DOWNLOAD_DIR}")
    print(f"[DEBUG] Files before download: {len(before_files)}")

    elapsed = 0
    for i in range(timeout // POLL_INTERVAL):
        elapsed = i * POLL_INTERVAL

        # Check for .crdownload files (Chrome in-progress downloads)
        crdownload_files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.crdownload"))
        if crdownload_files and i == 0:
            print(
                f"[INFO] Chrome is downloading: {os.path.basename(crdownload_files[0])}"
            )

        # Check for completed CSV or ZIP files
        after_files = set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv"))) | set(
            glob.glob(os.path.join(DOWNLOAD_DIR, "*.zip"))
        )
        new_files = after_files - before_files

        if new_files:
            new_file = list(new_files)[0]
            print(
                f"[INFO] New file detected after {elapsed} seconds: {os.path.basename(new_file)}"
            )
            # Wait a bit more to ensure download is complete
            time.sleep(2)
            return new_file

        # Progress update every 30 seconds
        if elapsed > 0 and elapsed % 30 == 0:
            print(f"[INFO] Still waiting... ({elapsed}/{timeout} seconds)")
            all_files = os.listdir(DOWNLOAD_DIR)
            print(f"[DEBUG] Current files in download dir: {len(all_files)} files")
            if crdownload_files:
                print(
                    f"[DEBUG] Chrome download in progress: {len(crdownload_files)} .crdownload file(s)"
                )

        time.sleep(POLL_INTERVAL)

    # Timeout - provide diagnostic info
    print(f"[ERROR] Timeout: No new CSV file appeared after {timeout} seconds")
    all_files = os.listdir(DOWNLOAD_DIR)
    csv_files = [f for f in all_files if f.endswith(".csv")]
    crdownload_files = [f for f in all_files if f.endswith(".crdownload")]

    print(f"[DEBUG] Files in download directory: {len(all_files)} total")
    print(f"[DEBUG] CSV files found: {len(csv_files)}")
    if csv_files:
        print(f"[DEBUG] CSV files: {csv_files[:5]}")  # Show first 5
    if crdownload_files:
        print(f"[ERROR] Incomplete downloads found: {crdownload_files}")

    return None


def open_report_and_download(
    driver, url, prefer_button_text=None, click_apply_filters=False, set_date_range=None
):
    """
    Enhanced to include detailed logging for download failures and ensure robust file saving logic.
    Uses multiple strategies to find and click the download button.

    Args:
        driver: Selenium WebDriver instance.
        url: The report URL to navigate to.
        prefer_button_text: If set (e.g. "Download summary"), click only
            a button whose visible text matches this string.  This is
            needed when a page has multiple download buttons.
        click_apply_filters: If True, click the "Apply filters" button
            after page load and wait for the report data to refresh
            before downloading.  Required for reports like Late
            Cancellations, Failed Penalties, and No Shows whose URL
            parameters only pre-populate the form but do not
            automatically execute the query.
    """
    debug_log(f"[INFO] Opening CRM report URL: {url}")
    debug_log(f"[DEBUG] Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    max_retries = 3
    retry_delay = 5

    for attempt in range(1, max_retries + 1):
        try:
            debug_log(f"[DEBUG] Navigating to URL (attempt {attempt}/{max_retries})...")
            driver.get(url)
            debug_log("[DEBUG] URL loaded, waiting for page to stabilize...")
            break
        except Exception as e:
            debug_log(f"[ERROR] Failed to load URL on attempt {attempt}: {e}")
            if attempt == max_retries:
                raise
            time.sleep(retry_delay)

    debug_log("[INFO] Waiting 10 seconds for page to fully load...")
    time.sleep(10)

    # ---- Check authentication (detect login redirect) ----
    current_url = driver.current_url
    page_title = driver.title
    debug_log(f"[INFO] After navigation: URL = {current_url}, Title = {page_title}")
    if (
        "sign-in" in current_url
        or "login" in current_url
        or "Login" in page_title
        or "Sign" in page_title
    ):
        raise Exception(
            f"Authentication failed: redirected to login page ({current_url}). "
            "Cookies may have expired – run momence_first_login_setup.py to refresh them."
        )

    # ---- Click "Apply filters" if requested ----
    if click_apply_filters:

        # ---- Explicitly set date inputs if caller provided a date range ----
        if set_date_range:
            start_dt, end_dt = set_date_range
            # Momence uses flatpickr date pickers that store UTC ISO timestamps.
            # Brisbane (AEST) is UTC+10, so midnight Brisbane = 14:00 previous day UTC.
            # We must use the flatpickr JS API (_flatpickr.setDate) — text input or
            # React nativeSetter approaches do not update flatpickr's internal state.
            from datetime import timedelta

            start_utc = (start_dt - timedelta(days=1)).strftime(
                "%Y-%m-%d"
            ) + "T14:00:00.000Z"
            end_utc = end_dt.strftime("%Y-%m-%d") + "T13:59:59.999Z"
            debug_log(f"[INFO] Setting flatpickr date range: {start_utc} to {end_utc}")
            try:
                result = driver.execute_script(
                    """
                    // flatpickr wrap mode: _flatpickr lives on a wrapper ancestor,
                    // not on the input element that has data-input="true".
                    function findFlatpickr(el) {
                        for (var i = 0; i < 6 && el; i++) {
                            if (el._flatpickr) return el._flatpickr;
                            el = el.parentElement;
                        }
                        return null;
                    }
                    var fromEl = document.getElementById('dateTimeRangeFrom');
                    var toEl   = document.getElementById('dateTimeRangeTo');
                    if (!fromEl || !toEl) return 'inputs not found';
                    var fromFp = findFlatpickr(fromEl);
                    var toFp   = findFlatpickr(toEl);
                    if (!fromFp || !toFp) {
                        // Fallback: scan all DOM elements for _flatpickr instances
                        var allFp = [];
                        document.querySelectorAll('*').forEach(function(el) {
                            if (el._flatpickr) allFp.push(el._flatpickr);
                        });
                        if (allFp.length >= 2) {
                            fromFp = allFp[0];
                            toFp   = allFp[1];
                        } else {
                            return 'flatpickr not found (found ' + allFp.length + ' instances)';
                        }
                    }
                    fromFp.setDate(arguments[0], true);
                    toFp.setDate(arguments[1], true);
                    return 'ok: from=' + fromEl.value + ' to=' + toEl.value;
                    """,
                    start_utc,
                    end_utc,
                )
                debug_log(f"[INFO] flatpickr setDate result: {result}")
                time.sleep(1)
            except Exception as e:
                debug_log(f"[WARN] Could not set flatpickr date inputs: {e}")

        # ---- Log current flatpickr date values (before Apply Filters) ----
        try:
            fp_state = driver.execute_script(
                """
                var result = {inputs: {}, flatpickrs: []};
                // Read date input elements
                var dateInputs = document.querySelectorAll(
                    'input[id*="dateTimeRange"], input[placeholder*="date" i], input[type="date"]'
                );
                dateInputs.forEach(function(el) {
                    result.inputs[el.id || el.name || el.placeholder] = el.value;
                });
                // Read flatpickr instances
                document.querySelectorAll('*').forEach(function(el) {
                    if (el._flatpickr && result.flatpickrs.length < 4) {
                        var fp = el._flatpickr;
                        result.flatpickrs.push({
                            element: el.id || el.className.substring(0, 40),
                            inputValue: fp.input ? fp.input.value : 'n/a',
                            selectedDates: fp.selectedDates
                                ? fp.selectedDates.map(function(d){ return d.toISOString(); })
                                : []
                        });
                    }
                });
                return result;
                """
            )
            debug_log(f"[INFO] Flatpickr state BEFORE Apply Filters: {fp_state}")
        except Exception as _fp_err:
            debug_log(f"[DEBUG] Could not read flatpickr state: {_fp_err}")

        debug_log("[INFO] Looking for 'Apply filters' button...")
        apply_clicked = False

        # Strategy A: XPath text match
        apply_xpaths = [
            "//button[contains(., 'Apply filters')]",
            "//button[contains(., 'Apply Filters')]",
            "//button[contains(., 'Apply')]",
        ]
        for xpath in apply_xpaths:
            try:
                apply_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                debug_log(f"[INFO] 'Apply filters' button found: '{apply_btn.text}'")
                apply_btn.click()
                apply_clicked = True
                # Wait for the button to become enabled again instead of a
                # fixed 15s sleep. The button is disabled while the request
                # is in flight, so its re-enablement is a reliable signal
                # that the report has finished fetching.
                debug_log(
                    "[INFO] 'Apply filters' clicked – waiting for it to become idle..."
                )
                _wait_apply_filters_idle(driver, timeout=180)
                break
            except Exception:
                continue

        # Strategy B: JavaScript fallback
        if not apply_clicked:
            debug_log("[INFO] Trying JavaScript fallback for 'Apply filters'...")
            try:
                js_result = driver.execute_script(
                    """
                    const btns = Array.from(document.querySelectorAll('button'));
                    const btn = btns.find(b => /apply\\s*filters?/i.test(b.textContent));
                    if (btn) { btn.click(); return btn.textContent; }
                    return null;
                """
                )
                if js_result:
                    apply_clicked = True
                    debug_log(
                        f"[INFO] JS clicked 'Apply filters': '{js_result}' – waiting for idle..."
                    )
                    _wait_apply_filters_idle(driver, timeout=180)
                else:
                    debug_log("[WARN] 'Apply filters' button not found by JS either")
            except Exception as e:
                debug_log(f"[WARN] JS 'Apply filters' attempt failed: {e}")

        if not apply_clicked:
            debug_log(
                "[WARN] Could not find 'Apply filters' button – proceeding anyway"
            )

        # Wait for the report to finish loading before looking for download buttons.
        # Some reports (especially Total Sales) show a "Loading report..." overlay
        # while fetching data.  The download button only appears after loading completes.
        debug_log("[INFO] Waiting for report to finish loading...")
        max_loading_wait = (
            360  # up to 6 minutes (Total Sales with new date range can be slow)
        )
        poll_interval = 5
        waited = 0
        while waited < max_loading_wait:
            try:
                loading_el = driver.find_element(
                    By.XPATH, "//*[contains(text(), 'Loading report')]"
                )
                # Still loading – wait and retry
                debug_log(f"[INFO] Report still loading... ({waited}s elapsed)")
                time.sleep(poll_interval)
                waited += poll_interval
            except Exception:
                # Element not found → loading finished (or was never shown)
                debug_log(f"[INFO] Report loading complete (waited {waited}s)")
                break
        else:
            debug_log(
                f"[WARN] Report still loading after {max_loading_wait}s – proceeding anyway"
            )

        # ---- Log flatpickr state AFTER Apply Filters + loading ----
        try:
            fp_state_after = driver.execute_script(
                """
                var result = {inputs: {}, flatpickrs: []};
                var dateInputs = document.querySelectorAll(
                    'input[id*="dateTimeRange"], input[placeholder*="date" i], input[type="date"]'
                );
                dateInputs.forEach(function(el) {
                    result.inputs[el.id || el.name || el.placeholder] = el.value;
                });
                document.querySelectorAll('*').forEach(function(el) {
                    if (el._flatpickr && result.flatpickrs.length < 4) {
                        var fp = el._flatpickr;
                        result.flatpickrs.push({
                            element: el.id || el.className.substring(0, 40),
                            inputValue: fp.input ? fp.input.value : 'n/a',
                            selectedDates: fp.selectedDates
                                ? fp.selectedDates.map(function(d){ return d.toISOString(); })
                                : []
                        });
                    }
                });
                // Also try to count visible table rows as a proxy for data loaded
                var rows = document.querySelectorAll('table tbody tr, [role="row"]');
                result.visibleRows = rows.length;
                return result;
                """
            )
            debug_log(f"[INFO] Flatpickr state AFTER Apply Filters: {fp_state_after}")
        except Exception as _fp_err2:
            debug_log(f"[DEBUG] Could not read post-Apply-Filters state: {_fp_err2}")

    # Build the XPath and JS regex depending on whether a specific button is preferred
    if prefer_button_text:
        # Exact-match XPath for the preferred button (e.g. "Download summary")
        button_xpath = f"//button[contains(., '{prefer_button_text}')]"
        js_regex = prefer_button_text.replace(
            " ", "\\s+"
        )  # allow flexible whitespace (\\\\ was wrong — produced JS \\s which matches a literal backslash)
        debug_log(f"[INFO] Preferred button text: '{prefer_button_text}'")
    else:
        button_xpath = "//button[contains(., 'Export to CSV') or contains(., 'Download summary') or contains(., 'Download') or contains(., 'Export')]"
        js_regex = "export to csv|download summary|download|export"

    download_button = None
    download_clicked = False
    _MAX_BTN_RETRIES = 3
    _BTN_RETRY_WAIT = 25  # seconds to wait between download-button retry attempts

    for _btn_attempt in range(1, _MAX_BTN_RETRIES + 1):
        if _btn_attempt > 1:
            debug_log(
                f"[WARN] Download button not found on attempt {_btn_attempt - 1} — "
                f"waiting {_BTN_RETRY_WAIT}s then retrying all strategies "
                f"(attempt {_btn_attempt}/{_MAX_BTN_RETRIES})..."
            )
            time.sleep(_BTN_RETRY_WAIT)
        download_clicked = False

        # Dismiss any open modal (e.g. notification-permission dialogs, promo
        # popups, "What's new" overlays) that might intercept clicks on the
        # download button.
        #
        # 2026-05-02: hardened after Step 6 failure caused by a Notifications
        # modal (class "modal-animation-appear-done modal-animation-enter-done")
        # that has no close button and ignores Escape. We now (a) try the close
        # button, (b) try Escape, (c) click the backdrop, and (d) as a last
        # resort remove the modal element + any backdrop from the DOM directly
        # so the underlying menu button becomes clickable.
        try:
            removed_modals = driver.execute_script(
                """
                const modalSelectors = [
                    '.modal-animation-appear-done',
                    '.modal-animation-enter-done',
                    '[role="dialog"]',
                    '[role="alertdialog"]',
                    '.ReactModal__Content',
                ];
                const backdropSelectors = [
                    '.ReactModal__Overlay',
                    '.modal-backdrop',
                    '[class*="backdrop" i]',
                    '[class*="overlay" i]',
                ];
                let removed = 0;
                for (const sel of modalSelectors) {
                    document.querySelectorAll(sel).forEach(modal => {
                        // a) Try a close button inside the modal
                        const closeBtn = modal.querySelector(
                            'button[aria-label*="close" i], button[aria-label*="dismiss" i], '
                            + 'button[aria-label*="not now" i], button.close, button[title*="close" i]'
                        );
                        if (closeBtn) { try { closeBtn.click(); } catch(e) {} }
                        // b) Try Escape on the modal itself
                        try {
                            modal.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape', bubbles:true}));
                        } catch(e) {}
                        // c) Last resort — remove from DOM so it can't intercept clicks
                        try { modal.remove(); removed++; } catch(e) {}
                    });
                }
                // Remove any associated backdrops/overlays so pointer-events are restored
                for (const sel of backdropSelectors) {
                    document.querySelectorAll(sel).forEach(el => {
                        try { el.remove(); } catch(e) {}
                    });
                }
                // Notifications flyout (bell-icon dropdown) — this was the
                // overlay visible in the 2026-05-12 No Shows failure
                // screenshot. Collapse it by toggling the bell off and
                // removing the panel from the DOM if it lingers.
                const bellButtons = document.querySelectorAll(
                    'button[aria-label*="notification" i],'
                  + 'button[aria-label*="alerts" i],'
                  + '[data-test*="notification" i] button'
                );
                bellButtons.forEach(btn => {
                    if (btn.getAttribute('aria-expanded') === 'true') {
                        try { btn.click(); } catch(e) {}
                    }
                });
                const notifPanels = document.querySelectorAll(
                    '[class*="notification" i][class*="panel" i],'
                  + '[class*="notification" i][class*="dropdown" i],'
                  + '[class*="notification" i][class*="menu" i],'
                  + '[data-test*="notification" i][role="menu"],'
                  + '[data-test*="notification-list" i]'
                );
                notifPanels.forEach(p => { try { p.remove(); removed++; } catch(e) {} });

                // Also dispatch a global Escape — covers modals not matched above
                document.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape', bubbles:true}));
                return removed;
                """
            )
            if removed_modals:
                debug_log(f"[INFO] Dismissed {removed_modals} blocking modal(s) before download click")
            time.sleep(1)
        except Exception as _modal_err:
            debug_log(f"[DEBUG] Modal dismiss attempt failed (non-fatal): {_modal_err}")

        # STRATEGY 1: Click the three-dots menu button first, then click the download option.
        # This is the primary strategy because Momence's current UI puts the download option
        # inside a dropdown menu — it is not directly accessible without opening the menu first.
        debug_log(
            f"[INFO] Strategy 1: Looking for menu button first (attempt {_btn_attempt}/{_MAX_BTN_RETRIES})..."
        )
        try:
            wait_short = WebDriverWait(driver, 15)
            wait_fast = WebDriverWait(
                driver, 3
            )  # Short timeout for each individual selector probe

            # Try multiple menu button selectors in order of reliability
            menu_button = None
            menu_selectors = [
                (By.CSS_SELECTOR, "div.sc-1kz352d-1.sc-1kz352d-3.jnInLk.fqEeHB"),
                (By.CSS_SELECTOR, "button[aria-label*='menu' i]"),
                (By.CSS_SELECTOR, "button[aria-label*='more' i]"),
                (By.XPATH, "//button[contains(@class, 'menu')]"),
                (
                    By.XPATH,
                    "//button/*[name()='svg']/../..",
                ),  # Button with SVG (common for menu icons)
            ]

            for selector_type, selector_value in menu_selectors:
                try:
                    menu_button = wait_fast.until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    debug_log(
                        f"[INFO] Menu button found with selector: {selector_value}"
                    )
                    break
                except:
                    continue

            if menu_button:
                menu_button.click()
                debug_log("[INFO] Menu button clicked, waiting for dropdown...")
                time.sleep(2)

                # Now find and click the download button in the dropdown
                download_button = wait_short.until(
                    EC.element_to_be_clickable((By.XPATH, button_xpath))
                )
                debug_log(
                    f"[INFO] Download button found after menu click: '{download_button.text}'"
                )
                download_button.click()
                download_clicked = True
                debug_log("[INFO] Download button clicked successfully")
            else:
                debug_log(
                    "[DEBUG] No menu button found with any selector — falling through to Strategy 2"
                )
        except Exception as e:
            debug_log(f"[DEBUG] Strategy 1 failed: {e}")

        # STRATEGY 2: Try to find the download button directly (no menu required).
        # Used on pages where the button is visible without opening a dropdown.
        # Also tries an icon-attribute variant via JS click to bypass overlay issues.
        if not download_clicked:
            debug_log("[INFO] Strategy 2: Looking for download button directly...")
            try:
                wait_short = WebDriverWait(
                    driver, 5
                )  # Short timeout — button either exists or it doesn't
                download_button = wait_short.until(
                    EC.element_to_be_clickable((By.XPATH, button_xpath))
                )
                debug_log(
                    f"[INFO] Download button found directly: '{download_button.text}'"
                )
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", download_button
                )
                time.sleep(0.5)
                download_button.click()
                download_clicked = True
                debug_log("[INFO] Download button clicked successfully")
            except Exception as e:
                debug_log(f"[DEBUG] Strategy 2 failed: {e}")

        # STRATEGY 2b: Icon-attribute fallback — find button containing the download icon by name.
        # Uses JS click to bypass Selenium's clickability check (e.g. if button is off-screen or
        # covered by a transparent overlay).
        if not download_clicked:
            debug_log(
                "[INFO] Strategy 2b: Looking for button via icon name attribute..."
            )
            try:
                icon_xpath = "//button[.//i[@name='download_outline_20']]"
                btn_icon = driver.find_element(By.XPATH, icon_xpath)
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", btn_icon
                )
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", btn_icon)
                download_clicked = True
                debug_log(
                    "[INFO] Download button found via icon attribute and JS-clicked successfully"
                )
            except Exception as e:
                debug_log(f"[DEBUG] Strategy 2b failed: {e}")

        # STRATEGY 3: Use JavaScript to find and click any button with download-related text
        if not download_clicked:
            debug_log("[INFO] Strategy 3: Using JavaScript to find download button...")
            try:
                js_script = f"""
                // Try text-content match first
                const buttons = Array.from(document.querySelectorAll('button, a, div[role="button"]'));
                let downloadButton = buttons.find(btn => {{
                    const text = btn.textContent || btn.innerText || '';
                    return text.match(/{js_regex}/i);
                }});
                // Fallback: find button containing the download icon by its name attribute
                if (!downloadButton) {{
                    const icon = document.querySelector('i[name="download_outline_20"]');
                    if (icon) downloadButton = icon.closest('button');
                }}
                if (downloadButton) {{
                    downloadButton.scrollIntoView({{block: 'center'}});
                    downloadButton.click();
                    return downloadButton.textContent || downloadButton.innerText;
                }}
                return null;
                """
                button_text = driver.execute_script(js_script)
                if button_text:
                    download_clicked = True
                    debug_log(
                        f"[INFO] JavaScript found and clicked button: '{button_text}'"
                    )
                else:
                    debug_log("[DEBUG] JavaScript didn't find any download button")
            except Exception as e:
                debug_log(f"[DEBUG] Strategy 3 failed: {e}")

        if download_clicked:
            break  # Button successfully clicked — exit retry loop

    if not download_clicked:
        debug_log("[ERROR] All strategies failed to find and click download button")
        # Save timestamped page source AND screenshot to a diagnostics folder so
        # successive failures don't overwrite each other, and we can see what
        # the page actually looked like (overlay? error? logged-out?).
        try:
            from datetime import datetime as _dt
            stamp = _dt.now().strftime("%Y%m%d_%H%M%S")
            diag_dir = "Log_files/diagnostics"
            os.makedirs(diag_dir, exist_ok=True)
            html_path = f"{diag_dir}/no_button_{stamp}.html"
            png_path = f"{diag_dir}/no_button_{stamp}.png"
            try:
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                debug_log(f"[INFO] Page source saved: {html_path}")
            except Exception as _e:
                debug_log(f"[WARN] Page source dump failed: {_e}")
            try:
                driver.save_screenshot(png_path)
                debug_log(f"[INFO] Screenshot saved: {png_path}")
            except Exception as _e:
                debug_log(f"[WARN] Screenshot failed: {_e}")
            try:
                debug_log(f"[DIAG] Current URL: {driver.current_url}")
                debug_log(f"[DIAG] Page title : {driver.title}")
            except Exception:
                pass
        except Exception:
            pass
        raise Exception("Could not find or click download button with any strategy")

    # Wait a moment for download to start
    debug_log("[INFO] Waiting for download to start...")
    time.sleep(3)

    # Note: The actual file download completion is now handled by wait_for_new_download()
    # in the main() function, so we don't wait here anymore
    debug_log("[INFO] Download initiated successfully")
    return None  # Return None since we're not tracking the file here anymore


# =====================================
# 4. APPEND AND DEDUPE CSV FILES
# =====================================
# CSV processing functions
# - Reads new and master CSV files
# - Adds customer numbers from the current page
# - Normalizes email addresses for deduplication
# - Concatenates and removes duplicates
# - Saves the updated master file
# - Archives the processed CSV file


def build_dedupe_key(df):
    """
    Add a 'dedupe_key' column built from Customer Email.
    """

    if COL_CUSTOMER_EMAIL not in df.columns:
        raise ValueError(f"Expected column '{COL_CUSTOMER_EMAIL}' not found in CSV.")

    # Normalize email for deduplication.
    df["dedupe_key"] = df[COL_CUSTOMER_EMAIL].astype(str).str.strip().str.upper()

    return df


def append_and_dedupe(new_csv_path, driver):
    """
    Append the newly downloaded CSV to the master CSV and remove duplicates.

    Steps:
    ------
    1. Read the new CSV.
    2. If MASTER_FILE exists, read it; otherwise, create an empty DataFrame
       with the same columns as the new CSV.
    3. Extract customer numbers from the page
    4. Add customer numbers as a new column
    5. Add 'dedupe_key' to both DataFrames.
    6. Concatenate and drop duplicates on 'dedupe_key'.
    7. Save combined DataFrame back to MASTER_FILE.
    8. Move the CSV into ARCHIVE_DIR.
    """
    print(f"[INFO] Reading new CSV: {new_csv_path}")
    df_new = pd.read_csv(new_csv_path)

    # Extract customer mapping from the current page
    customer_mapping = extract_customer_numbers_from_html(driver)

    # Add customer number column
    # No Card CSV has separate First Name / Last Name columns, so construct full name
    if (
        COL_CUSTOMER_FIRST_NAME in df_new.columns
        and COL_CUSTOMER_LAST_NAME in df_new.columns
    ):
        full_names = (
            df_new[COL_CUSTOMER_FIRST_NAME].astype(str).str.strip()
            + " "
            + df_new[COL_CUSTOMER_LAST_NAME].astype(str).str.strip()
        )
        df_new["Customer Number"] = full_names.apply(
            lambda x: customer_mapping.get(x, "")
        )
        print(f"[INFO] Added Customer Number column ({len(customer_mapping)} mapped)")

    if os.path.exists(MASTER_FILE):
        print(f"[INFO] Reading existing master CSV: {MASTER_FILE}")
        df_master = pd.read_csv(MASTER_FILE)
    else:
        print("[INFO] Master CSV does not exist yet; will create a new one.")
        df_master = pd.DataFrame(columns=df_new.columns)

    original_master_len = len(df_master)

    # Build dedupe keys for both old and new.
    df_new = build_dedupe_key(df_new)
    df_master = build_dedupe_key(df_master)

    # Concatenate and drop duplicates based on 'dedupe_key'.
    combined = pd.concat([df_master, df_new], ignore_index=True)
    before = len(combined)
    combined = combined.drop_duplicates(subset="dedupe_key", keep="first")
    after = len(combined)

    print(f"[INFO] Rows before de-duplication: {before}")
    print(f"[INFO] Rows after  de-duplication: {after}")
    print(f"[INFO] Removed {before - after} duplicate rows.")

    # Drop 'dedupe_key' before saving.
    combined = combined.drop(columns=["dedupe_key"])

    combined.to_csv(MASTER_FILE, index=False)
    print(f"[INFO] Master CSV updated: {MASTER_FILE}")

    # Move CSV to archive folder, renaming to match our naming convention.
    base_name = os.path.basename(new_csv_path)
    if base_name.lower() == "momence-customers.csv":
        base_name = "Momence-No-Card-Customers.csv"
    archive_path = os.path.join(ARCHIVE_DIR, base_name)
    os.replace(new_csv_path, archive_path)
    print(f"[INFO] CSV moved to archive: {archive_path}")

    added = after - original_master_len
    return added


# ============================================
# 5. FAILED PENALTY CHARGES REPORT FUNCTIONS
# ============================================


def build_penalties_url():
    """
    Build the Failed Penalty Charges URL with the last 4 weeks date range.

    Returns:
        url (str): Complete URL with date range parameters
    """
    # Calculate date range: last 4 weeks (28 days back)
    today = datetime.now()
    four_weeks_ago = today - timedelta(days=28)

    # Momence expects UTC timestamps (Z suffix).
    # Brisbane is UTC+10, so:
    #   midnight Brisbane  = 14:00 UTC  previous calendar day
    #   23:59:59 Brisbane  = 13:59:59 UTC same calendar day
    start_utc = (four_weeks_ago - timedelta(days=1)).replace(
        hour=14, minute=0, second=0, microsecond=0
    )
    end_utc = today.replace(hour=13, minute=59, second=59, microsecond=999000)
    day_utc = today.replace(hour=0, minute=0, second=0, microsecond=0)

    start_date_str = (
        start_utc.strftime("%Y-%m-%dT%H:%M:%S.")
        + f"{start_utc.microsecond // 1000:03d}Z"
    )
    end_date_str = (
        end_utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{end_utc.microsecond // 1000:03d}Z"
    )
    day_str = (
        day_utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{day_utc.microsecond // 1000:03d}Z"
    )

    # Build complete URL with date parameters
    url = (
        f"{MOMENCE_PENALTIES_BASE_URL}"
        f"&startDate={start_date_str}"
        f"&startDate2={start_date_str}"
        f"&endDate={end_date_str}"
        f"&endDate2={end_date_str}"
        f"&day={day_str}"
    )

    print(
        f"[INFO] Built penalties URL for date range: {four_weeks_ago.date()} to {today.date()}"
    )
    return url, four_weeks_ago.date(), today.date()


def extract_customer_numbers_from_html(driver):
    """
    Extract customer numbers from customer name links in the page.

    Looks for links like: https://momence.com/dashboard/32083/crm/17082596
    Extracts the numeric customer ID from the end of the URL.

    Returns:
        mapping (dict): {customer_name: customer_number, ...}
    """
    mapping = {}
    try:
        # Find all customer name links - these should link to /crm/{customer_id}
        links = driver.find_elements(By.XPATH, "//a[contains(@href, '/crm/')]")

        for link in links:
            href = link.get_attribute("href")
            customer_name = link.text.strip()

            if customer_name and href:
                # Extract customer number from URL: /crm/12345
                match = re.search(r"/crm/(\d+)$", href)
                if match:
                    customer_id = match.group(1)
                    mapping[customer_name] = customer_id
                    print(f"[DEBUG] Found customer: {customer_name} -> {customer_id}")

        print(f"[INFO] Extracted {len(mapping)} customer numbers from page")
        return mapping

    except Exception as e:
        print(f"[WARN] Failed to extract customer numbers: {e}")
        return {}


def append_and_dedupe_penalties(new_csv_path, driver):
    """
    Append the newly downloaded Failed Penalties CSV to master and add customer numbers.

    Steps:
    ------
    1. Extract customer numbers from the page
    2. Read the new CSV
    3. Add customer numbers as a new column
    4. Append to master file with deduplication on (Customer Name + Date)
    5. Move CSV to archive
    """
    print(f"[INFO] Reading penalties CSV: {new_csv_path}")
    if new_csv_path.lower().endswith(".zip"):
        with zipfile.ZipFile(new_csv_path) as zf:
            csv_members = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            print(
                f"[INFO] Multi-member ZIP detected — concatenating {len(csv_members)} CSVs"
            )
            frames = [pd.read_csv(io.BytesIO(zf.read(n))) for n in csv_members]
            df_new = pd.concat(frames, ignore_index=True)
    else:
        df_new = pd.read_csv(new_csv_path)

    # --- Detailed logging: downloaded CSV diagnostics ---
    print(f"[INFO] Downloaded penalties CSV: {len(df_new)} rows")
    print(f"[INFO] Downloaded penalties CSV columns: {list(df_new.columns)}")
    if len(df_new) == 0:
        print(
            "[WARN] Downloaded penalties CSV is EMPTY (header only) — no data to process"
        )
    else:
        if COL_PENALTIES_DATE in df_new.columns:
            date_min = df_new[COL_PENALTIES_DATE].min()
            date_max = df_new[COL_PENALTIES_DATE].max()
            print(f"[INFO] Penalties CSV date range: {date_min} to {date_max}")
        else:
            print(
                f"[WARN] Expected date column '{COL_PENALTIES_DATE}' not found in CSV"
            )
        if COL_PENALTIES_CUSTOMER_NAME not in df_new.columns:
            print(
                f"[WARN] Expected column '{COL_PENALTIES_CUSTOMER_NAME}' not found in CSV"
            )

    # Extract customer mapping from the current page
    customer_mapping = extract_customer_numbers_from_html(driver)

    # Add customer number column
    if COL_PENALTIES_CUSTOMER_NAME in df_new.columns:
        df_new["Customer Number"] = df_new[COL_PENALTIES_CUSTOMER_NAME].apply(
            lambda x: customer_mapping.get(x, "")
        )
        print(f"[INFO] Added Customer Number column ({len(customer_mapping)} mapped)")

    # Read master file if it exists
    if os.path.exists(MASTER_PENALTIES_FILE):
        print(f"[INFO] Reading existing master penalties CSV: {MASTER_PENALTIES_FILE}")
        df_master = pd.read_csv(MASTER_PENALTIES_FILE)
    else:
        print("[INFO] Master penalties CSV does not exist yet; will create a new one.")
        df_master = pd.DataFrame(columns=df_new.columns)

    original_master_len = len(df_master)
    print(f"[INFO] Master penalties has {original_master_len} existing rows")

    # Create deduplication key: Customer Name + Amount + Date
    # Includes Amount so that two different penalty charges for the same
    # customer at the same time (but different amounts) are kept.
    df_new["dedupe_key"] = (
        df_new[COL_PENALTIES_CUSTOMER_NAME].astype(str).str.strip().str.upper()
        + "|"
        + df_new["Amount"].astype(str).str.strip()
        + "|"
        + df_new[COL_PENALTIES_DATE].astype(str).str.strip()
    )
    df_master["dedupe_key"] = (
        df_master[COL_PENALTIES_CUSTOMER_NAME].astype(str).str.strip().str.upper()
        + "|"
        + df_master["Amount"].astype(str).str.strip()
        + "|"
        + df_master[COL_PENALTIES_DATE].astype(str).str.strip()
    )

    # Count genuinely new records before concat
    master_keys = set(df_master["dedupe_key"])
    new_only = df_new[~df_new["dedupe_key"].isin(master_keys)]
    print(f"[INFO] Genuinely new penalty rows (not in master): {len(new_only)}")
    print(f"[INFO] Already in master (will be skipped): {len(df_new) - len(new_only)}")
    if len(new_only) > 0:
        print(
            f"[INFO] Sample of new penalty records:\n{new_only[[COL_PENALTIES_CUSTOMER_NAME, COL_PENALTIES_DATE]].head(5).to_string(index=False)}"
        )
    else:
        print("[INFO] All downloaded penalty rows are duplicates of master records")
        if (
            COL_PENALTIES_DATE in df_new.columns
            and len(df_new) > 0
            and original_master_len > 0
        ):
            try:
                new_max_date = df_new[COL_PENALTIES_DATE].max()
                master_max_date = df_master[COL_PENALTIES_DATE].max()
                print(f"[INFO] Latest date in downloaded CSV: {new_max_date}")
                print(f"[INFO] Latest date in master: {master_max_date}")
                if new_max_date <= master_max_date:
                    print(
                        "[WARN] Downloaded data does not extend beyond master — "
                        "date range may not be applied or no new failures since last run"
                    )
            except Exception:
                pass

    # Concatenate and drop duplicates
    combined = pd.concat([df_master, df_new], ignore_index=True)
    before = len(combined)
    combined = combined.drop_duplicates(subset="dedupe_key", keep="first")
    after = len(combined)

    print(f"[INFO] Rows before de-duplication: {before}")
    print(f"[INFO] Rows after  de-duplication: {after}")
    print(f"[INFO] Removed {before - after} duplicate rows.")

    # Drop dedupe_key before saving
    combined = combined.drop(columns=["dedupe_key"])

    # Data cleanup: Remove "Home location" column if it exists
    if "Home location" in combined.columns:
        combined = combined.drop(columns=["Home location"])
        print(f"[INFO] Removed 'Home location' column")

    combined.to_csv(MASTER_PENALTIES_FILE, index=False)
    print(f"[INFO] Master penalties CSV updated: {MASTER_PENALTIES_FILE}")

    # Move CSV to archive folder
    base_name = os.path.basename(new_csv_path)
    archive_path = os.path.join(ARCHIVE_DIR, base_name)
    os.replace(new_csv_path, archive_path)
    print(f"[INFO] CSV moved to archive: {archive_path}")

    added = after - original_master_len
    return added


def build_late_cancellations_url():
    """
    Build the Late Cancellations URL with the last 4 weeks date range.

    Returns:
        url (str): Complete URL with date range parameters
    """
    # Calculate date range: last 4 weeks (28 days back)
    today = datetime.now()
    four_weeks_ago = today - timedelta(days=28)

    # Momence expects UTC timestamps (Z suffix).
    # Brisbane is UTC+10, so:
    #   midnight Brisbane  = 14:00 UTC  previous calendar day
    #   23:59:59 Brisbane  = 13:59:59 UTC same calendar day
    start_utc = (four_weeks_ago - timedelta(days=1)).replace(
        hour=14, minute=0, second=0, microsecond=0
    )
    end_utc = today.replace(hour=13, minute=59, second=59, microsecond=999000)
    day_utc = today.replace(hour=0, minute=0, second=0, microsecond=0)

    start_date_str = (
        start_utc.strftime("%Y-%m-%dT%H:%M:%S.")
        + f"{start_utc.microsecond // 1000:03d}Z"
    )
    end_date_str = (
        end_utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{end_utc.microsecond // 1000:03d}Z"
    )
    day_str = (
        day_utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{day_utc.microsecond // 1000:03d}Z"
    )

    # Build complete URL with date parameters
    url = (
        f"{MOMENCE_LATE_CANCELLATIONS_BASE_URL}"
        f"&startDate={start_date_str}"
        f"&startDate2={start_date_str}"
        f"&endDate={end_date_str}"
        f"&endDate2={end_date_str}"
        f"&day={day_str}"
    )

    print(
        f"[INFO] Built late cancellations URL for date range: {four_weeks_ago.date()} to {today.date()}"
    )
    return url, four_weeks_ago.date(), today.date()


def append_and_dedupe_late_cancellations(new_csv_path, driver):
    """
    Append the newly downloaded Late Cancellations CSV to master and add customer numbers.

    Steps:
    ------
    1. Extract customer numbers from the page
    2. Read the new CSV
    3. Add customer numbers as a new column
    4. Append to master file with deduplication on (Customer Name + Date)
    5. Move CSV to archive
    """
    print(f"[INFO] Reading late cancellations CSV: {new_csv_path}")
    df_new = pd.read_csv(new_csv_path)

    # --- Detailed logging: downloaded CSV diagnostics ---
    print(f"[INFO] Downloaded late cancellations CSV: {len(df_new)} rows")
    print(f"[INFO] Downloaded late cancellations CSV columns: {list(df_new.columns)}")
    if len(df_new) == 0:
        print(
            "[WARN] Downloaded late cancellations CSV is EMPTY (header only) — no data to process"
        )
    else:
        if COL_LATE_CANCEL_DATE in df_new.columns:
            date_min = df_new[COL_LATE_CANCEL_DATE].min()
            date_max = df_new[COL_LATE_CANCEL_DATE].max()
            print(f"[INFO] Late cancellations CSV date range: {date_min} to {date_max}")
        else:
            print(
                f"[WARN] Expected date column '{COL_LATE_CANCEL_DATE}' not found in CSV"
            )
        if COL_LATE_CANCEL_CUSTOMER_NAME not in df_new.columns:
            print(
                f"[WARN] Expected column '{COL_LATE_CANCEL_CUSTOMER_NAME}' not found in CSV"
            )

    # Extract customer mapping from the current page
    customer_mapping = extract_customer_numbers_from_html(driver)

    # Add customer number column
    if COL_LATE_CANCEL_CUSTOMER_NAME in df_new.columns:
        df_new["Customer Number"] = df_new[COL_LATE_CANCEL_CUSTOMER_NAME].apply(
            lambda x: customer_mapping.get(x, "")
        )
        print(f"[INFO] Added Customer Number column ({len(customer_mapping)} mapped)")

    # Read master file if it exists
    if os.path.exists(MASTER_LATE_CANCELLATIONS_FILE):
        print(
            f"[INFO] Reading existing master late cancellations CSV: {MASTER_LATE_CANCELLATIONS_FILE}"
        )
        df_master = pd.read_csv(MASTER_LATE_CANCELLATIONS_FILE)
    else:
        print(
            "[INFO] Master late cancellations CSV does not exist yet; will create a new one."
        )
        df_master = pd.DataFrame(columns=df_new.columns)

    original_master_len = len(df_master)
    print(f"[INFO] Master late cancellations has {original_master_len} existing rows")

    # Create deduplication key: Customer Name + Cancelled Class + Date
    # Includes the class name so that cancelling two different classes at
    # the same time is correctly treated as two separate records.
    df_new["dedupe_key"] = (
        df_new[COL_LATE_CANCEL_CUSTOMER_NAME].astype(str).str.strip().str.upper()
        + "|"
        + df_new[COL_LATE_CANCEL_CLASS].astype(str).str.strip().str.upper()
        + "|"
        + df_new[COL_LATE_CANCEL_DATE].astype(str).str.strip()
    )
    df_master["dedupe_key"] = (
        df_master[COL_LATE_CANCEL_CUSTOMER_NAME].astype(str).str.strip().str.upper()
        + "|"
        + df_master[COL_LATE_CANCEL_CLASS].astype(str).str.strip().str.upper()
        + "|"
        + df_master[COL_LATE_CANCEL_DATE].astype(str).str.strip()
    )

    # Count genuinely new records before concat
    master_keys = set(df_master["dedupe_key"])
    new_only = df_new[~df_new["dedupe_key"].isin(master_keys)]
    print(
        f"[INFO] Genuinely new late cancellation rows (not in master): {len(new_only)}"
    )
    print(f"[INFO] Already in master (will be skipped): {len(df_new) - len(new_only)}")
    if len(new_only) > 0:
        print(
            f"[INFO] Sample of new late cancellation records:\n"
            f"{new_only[[COL_LATE_CANCEL_CUSTOMER_NAME, COL_LATE_CANCEL_DATE]].head(5).to_string(index=False)}"
        )
    else:
        print(
            "[INFO] All downloaded late cancellation rows are duplicates of master records"
        )
        if (
            COL_LATE_CANCEL_DATE in df_new.columns
            and len(df_new) > 0
            and original_master_len > 0
        ):
            try:
                new_max_date = df_new[COL_LATE_CANCEL_DATE].max()
                master_max_date = df_master[COL_LATE_CANCEL_DATE].max()
                print(f"[INFO] Latest date in downloaded CSV: {new_max_date}")
                print(f"[INFO] Latest date in master: {master_max_date}")
                if new_max_date <= master_max_date:
                    print(
                        "[WARN] Downloaded data does not extend beyond master — "
                        "date range may not be applied or no new cancellations since last run"
                    )
            except Exception:
                pass

    # Concatenate and drop duplicates
    combined = pd.concat([df_master, df_new], ignore_index=True)
    before = len(combined)
    combined = combined.drop_duplicates(subset="dedupe_key", keep="first")
    after = len(combined)

    print(f"[INFO] Rows before de-duplication: {before}")
    print(f"[INFO] Rows after  de-duplication: {after}")
    print(f"[INFO] Removed {before - after} duplicate rows.")

    # Drop dedupe_key before saving
    combined = combined.drop(columns=["dedupe_key"])

    # Data cleanup for Late Cancellations
    # 1. Fill empty "Membership name" with "blank"
    if "Membership name" in combined.columns:
        combined["Membership name"] = combined["Membership name"].fillna("blank")
        combined["Membership name"] = combined["Membership name"].replace("", "blank")
        print(f"[INFO] Filled empty 'Membership name' with 'blank'")

    # 2. Fill empty "Penalty charged" with 0
    if "Penalty charged" in combined.columns:
        combined["Penalty charged"] = combined["Penalty charged"].fillna(0)
        combined["Penalty charged"] = combined["Penalty charged"].replace("", 0)
        print(f"[INFO] Filled empty 'Penalty charged' with 0")

    # 3. Remove "Home location" column
    if "Home location" in combined.columns:
        combined = combined.drop(columns=["Home location"])
        print(f"[INFO] Removed 'Home location' column")

    combined.to_csv(MASTER_LATE_CANCELLATIONS_FILE, index=False)
    print(
        f"[INFO] Master late cancellations CSV updated: {MASTER_LATE_CANCELLATIONS_FILE}"
    )

    # Move CSV to archive folder
    base_name = os.path.basename(new_csv_path)
    archive_path = os.path.join(ARCHIVE_DIR, base_name)
    os.replace(new_csv_path, archive_path)
    print(f"[INFO] CSV moved to archive: {archive_path}")

    added = after - original_master_len
    return added


def build_no_shows_url():
    """
    Build the No Shows URL with the last 4 weeks date range.

    Returns:
        url (str): Complete URL with date range parameters
    """
    # Calculate date range: last 4 weeks (28 days back)
    today = datetime.now()
    four_weeks_ago = today - timedelta(days=28)

    # Momence expects UTC timestamps (Z suffix).
    # Brisbane is UTC+10, so:
    #   midnight Brisbane  = 14:00 UTC  previous calendar day
    #   23:59:59 Brisbane  = 13:59:59 UTC same calendar day
    start_utc = (four_weeks_ago - timedelta(days=1)).replace(
        hour=14, minute=0, second=0, microsecond=0
    )
    end_utc = today.replace(hour=13, minute=59, second=59, microsecond=999000)
    day_utc = today.replace(hour=0, minute=0, second=0, microsecond=0)

    start_date_str = (
        start_utc.strftime("%Y-%m-%dT%H:%M:%S.")
        + f"{start_utc.microsecond // 1000:03d}Z"
    )
    end_date_str = (
        end_utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{end_utc.microsecond // 1000:03d}Z"
    )
    day_str = (
        day_utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{day_utc.microsecond // 1000:03d}Z"
    )

    # Build complete URL with date parameters
    url = (
        f"{MOMENCE_NO_SHOWS_BASE_URL}"
        f"&startDate={start_date_str}"
        f"&endDate={end_date_str}"
        f"&day={day_str}"
    )

    print(
        f"[INFO] Built no shows URL for date range: {four_weeks_ago.date()} to {today.date()}"
    )
    return url, four_weeks_ago.date(), today.date()


def extract_customer_and_class_numbers_from_html(driver):
    """
    Extract both customer numbers and class numbers from page links.

    Customer links: https://momence.com/dashboard/32083/crm/{customer_id}
    Class links: https://momence.com/dashboard/32083/sessions/{class_id}

    Returns:
        tuple: (customer_mapping dict, class_mapping dict)
            - customer_mapping: {customer_name: customer_number, ...}
            - class_mapping: {class_name: class_number, ...}
    """
    customer_mapping = {}
    class_mapping = {}

    try:
        # Find all customer name links - these should link to /crm/{customer_id}
        customer_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/crm/')]")

        for link in customer_links:
            href = link.get_attribute("href")
            customer_name = link.text.strip()

            if customer_name and href:
                # Extract customer number from URL: /crm/12345
                match = re.search(r"/crm/(\d+)$", href)
                if match:
                    customer_id = match.group(1)
                    customer_mapping[customer_name] = customer_id
                    print(f"[DEBUG] Found customer: {customer_name} -> {customer_id}")

        # Find all class links - these should link to /sessions/{class_id}
        class_links = driver.find_elements(
            By.XPATH, "//a[contains(@href, '/sessions/')]"
        )

        for link in class_links:
            href = link.get_attribute("href")
            class_name = link.text.strip()

            if class_name and href:
                # Extract class number from URL: /sessions/112531845
                match = re.search(r"/sessions/(\d+)$", href)
                if match:
                    class_id = match.group(1)
                    class_mapping[class_name] = class_id
                    print(f"[DEBUG] Found class: {class_name} -> {class_id}")

        print(
            f"[INFO] Extracted {len(customer_mapping)} customer numbers and {len(class_mapping)} class numbers from page"
        )
        return customer_mapping, class_mapping

    except Exception as e:
        print(f"[WARN] Failed to extract customer and class numbers: {e}")
        return {}, {}


def append_and_dedupe_no_shows(new_csv_path, driver):
    """
    Append the newly downloaded No Shows CSV to master and add customer/class numbers.

    Steps:
    ------
    1. Extract customer and class numbers from the page
    2. Read the new CSV
    3. Add customer and class numbers as new columns
    4. Append to master file with deduplication on (Customer Number + Class Number)
    5. Move CSV to archive
    """
    print(f"[INFO] Reading no shows CSV: {new_csv_path}")
    df_new = pd.read_csv(new_csv_path)

    # --- Detailed logging: downloaded CSV diagnostics ---
    print(f"[INFO] Downloaded no shows CSV: {len(df_new)} rows")
    print(f"[INFO] Downloaded no shows CSV columns: {list(df_new.columns)}")
    if len(df_new) == 0:
        print(
            "[WARN] Downloaded no shows CSV is EMPTY (header only) — no data to process"
        )
    else:
        if COL_NO_SHOWS_CLASS_DATE in df_new.columns:
            date_min = df_new[COL_NO_SHOWS_CLASS_DATE].min()
            date_max = df_new[COL_NO_SHOWS_CLASS_DATE].max()
            print(f"[INFO] No shows CSV date range: {date_min} to {date_max}")
        else:
            print(
                f"[WARN] Expected date column '{COL_NO_SHOWS_CLASS_DATE}' not found in CSV"
            )
        if COL_NO_SHOWS_CUSTOMER_NAME not in df_new.columns:
            print(
                f"[WARN] Expected column '{COL_NO_SHOWS_CUSTOMER_NAME}' not found in CSV"
            )

    # Extract customer and class mappings from the current page
    customer_mapping, class_mapping = extract_customer_and_class_numbers_from_html(
        driver
    )

    # Add customer and class number columns
    if COL_NO_SHOWS_CUSTOMER_NAME in df_new.columns:
        df_new["Customer Number"] = df_new[COL_NO_SHOWS_CUSTOMER_NAME].apply(
            lambda x: customer_mapping.get(x, "")
        )
        print(f"[INFO] Added Customer Number column ({len(customer_mapping)} mapped)")

    if COL_NO_SHOWS_CLASS_NAME in df_new.columns:
        df_new["Class Number"] = df_new[COL_NO_SHOWS_CLASS_NAME].apply(
            lambda x: class_mapping.get(x, "")
        )
        print(f"[INFO] Added Class Number column ({len(class_mapping)} mapped)")

    # Read master file if it exists
    if os.path.exists(MASTER_NO_SHOWS_FILE):
        print(f"[INFO] Reading existing master no shows CSV: {MASTER_NO_SHOWS_FILE}")
        df_master = pd.read_csv(MASTER_NO_SHOWS_FILE)
    else:
        print("[INFO] Master no shows CSV does not exist yet; will create a new one.")
        df_master = pd.DataFrame(columns=df_new.columns)

    original_master_len = len(df_master)
    print(f"[INFO] Master no shows has {original_master_len} existing rows")

    # Create deduplication key: Customer Name + Class + Class Date
    # Using CSV column values (not HTML-extracted IDs) ensures reliable dedup
    # regardless of whether the HTML extraction succeeds or how pandas
    # formats numeric columns (float vs string).
    df_new["dedupe_key"] = (
        df_new[COL_NO_SHOWS_CUSTOMER_NAME].astype(str).str.strip().str.upper()
        + "|"
        + df_new[COL_NO_SHOWS_CLASS_NAME].astype(str).str.strip().str.upper()
        + "|"
        + df_new[COL_NO_SHOWS_CLASS_DATE].astype(str).str.strip()
    )
    df_master["dedupe_key"] = (
        df_master[COL_NO_SHOWS_CUSTOMER_NAME].astype(str).str.strip().str.upper()
        + "|"
        + df_master[COL_NO_SHOWS_CLASS_NAME].astype(str).str.strip().str.upper()
        + "|"
        + df_master[COL_NO_SHOWS_CLASS_DATE].astype(str).str.strip()
    )

    # Count genuinely new records before concat
    master_keys = set(df_master["dedupe_key"])
    new_only = df_new[~df_new["dedupe_key"].isin(master_keys)]
    print(f"[INFO] Genuinely new no-show rows (not in master): {len(new_only)}")
    print(f"[INFO] Already in master (will be skipped): {len(df_new) - len(new_only)}")
    if len(new_only) > 0:
        print(
            f"[INFO] Sample of new no-show records:\n"
            f"{new_only[[COL_NO_SHOWS_CUSTOMER_NAME, COL_NO_SHOWS_CLASS_DATE]].head(5).to_string(index=False)}"
        )
    else:
        print("[INFO] All downloaded no-show rows are duplicates of master records")
        if (
            COL_NO_SHOWS_CLASS_DATE in df_new.columns
            and len(df_new) > 0
            and original_master_len > 0
        ):
            try:
                new_max_date = df_new[COL_NO_SHOWS_CLASS_DATE].max()
                master_max_date = df_master[COL_NO_SHOWS_CLASS_DATE].max()
                print(f"[INFO] Latest date in downloaded CSV: {new_max_date}")
                print(f"[INFO] Latest date in master: {master_max_date}")
                if new_max_date <= master_max_date:
                    print(
                        "[WARN] Downloaded data does not extend beyond master — "
                        "date range may not be applied or no new no-shows since last run"
                    )
            except Exception:
                pass

    # Concatenate and drop duplicates
    combined = pd.concat([df_master, df_new], ignore_index=True)
    before = len(combined)
    combined = combined.drop_duplicates(subset="dedupe_key", keep="first")
    after = len(combined)

    print(f"[INFO] Rows before de-duplication: {before}")
    print(f"[INFO] Rows after  de-duplication: {after}")
    print(f"[INFO] Removed {before - after} duplicate rows.")

    # Drop dedupe_key before saving
    combined = combined.drop(columns=["dedupe_key"])

    # Data cleanup for No Shows
    # 1. Fill empty "Membership used" with "blank"
    if "Membership used" in combined.columns:
        combined["Membership used"] = combined["Membership used"].fillna("blank")
        combined["Membership used"] = combined["Membership used"].replace("", "blank")
        print(f"[INFO] Filled empty 'Membership used' with 'blank'")

    # 2. Fill empty "Penalty charged" with 0
    if "Penalty charged" in combined.columns:
        combined["Penalty charged"] = combined["Penalty charged"].fillna(0)
        combined["Penalty charged"] = combined["Penalty charged"].replace("", 0)
        print(f"[INFO] Filled empty 'Penalty charged' with 0")

    # 3. Remove "Home location" column
    if "Home location" in combined.columns:
        combined = combined.drop(columns=["Home location"])
        print(f"[INFO] Removed 'Home location' column")

    combined.to_csv(MASTER_NO_SHOWS_FILE, index=False)
    print(f"[INFO] Master no shows CSV updated: {MASTER_NO_SHOWS_FILE}")

    # Move CSV to archive folder
    base_name = os.path.basename(new_csv_path)
    archive_path = os.path.join(ARCHIVE_DIR, base_name)
    os.replace(new_csv_path, archive_path)
    print(f"[INFO] CSV moved to archive: {archive_path}")

    added = after - original_master_len
    return added


# ============================================
# 6. TOTAL SALES REPORT FUNCTIONS
# ============================================


def build_sales_url():
    """
    Build the Total Sales URL with the appropriate date range.

    The start date is 1 day before the most recent Date found in
    master-sales-summary.csv (to catch any late-arriving transactions).
    If the master does not exist or is empty, falls back to
    SALES_INITIAL_START_DATE (9 Dec 2025).

    Returns:
        url (str): Complete URL with date range parameters
    """
    today = datetime.now()
    yesterday = today - timedelta(days=1)

    # Determine start date from the most recent sale in the master file
    range_start = SALES_INITIAL_START_DATE  # fallback
    if os.path.exists(MASTER_SALES_FILE):
        try:
            df_master = pd.read_csv(MASTER_SALES_FILE, usecols=[COL_SALES_DATE])
            if len(df_master) > 0:
                # Date format in CSV is like "2025-12-12, 08:15"
                most_recent = pd.to_datetime(
                    df_master[COL_SALES_DATE], format="mixed"
                ).max()
                range_start = most_recent - timedelta(days=1)
                print(
                    f"[INFO] Most recent sale in master: {most_recent.date()}, "
                    f"starting download from: {range_start.date()}"
                )
        except Exception as e:
            print(f"[WARN] Could not read dates from master sales file: {e}")

    print(f"[INFO] Sales date range: {range_start.date()} to {today.date()}")

    # Brisbane is UTC+10:
    #   midnight Brisbane  = 14:00 UTC previous calendar day
    #   23:59:59 Brisbane  = 13:59:59 UTC same calendar day
    start_utc = (range_start - timedelta(days=1)).replace(
        hour=14, minute=0, second=0, microsecond=0
    )
    # Use end of today (Brisbane) so same-day transactions are included.
    end_utc = today.replace(hour=13, minute=59, second=59, microsecond=999000)
    day_utc = today.replace(hour=0, minute=0, second=0, microsecond=0)

    start_date_str = (
        start_utc.strftime("%Y-%m-%dT%H:%M:%S.")
        + f"{start_utc.microsecond // 1000:03d}Z"
    )
    end_date_str = (
        end_utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{end_utc.microsecond // 1000:03d}Z"
    )
    day_str = (
        day_utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{day_utc.microsecond // 1000:03d}Z"
    )

    url = (
        f"{MOMENCE_SALES_BASE_URL}"
        f"&startDate={start_date_str}"
        f"&startDate2={start_date_str}"
        f"&endDate={end_date_str}"
        f"&endDate2={end_date_str}"
        f"&day={day_str}"
    )

    return url, range_start.date(), today.date()


# ============================================
# 7. TOTAL SALES APPEND AND DEDUPE
# ============================================


def append_and_dedupe_sales(new_csv_path, driver, start_date, end_date):
    """
    Append the newly downloaded Total Sales CSV to master and remove duplicates.

    Steps:
    ------
    1. Read the new CSV
    2. Append to master file with deduplication on (Date + Sale reference)
    3. Move CSV to archive

    Args:
        new_csv_path: Path to the newly downloaded CSV file
        driver: Selenium WebDriver instance (unused but kept for API consistency)
        start_date: Start date of the report period (for logging)
        end_date: End date of the report period (for logging)
    """
    print(f"[INFO] Reading sales file: {new_csv_path}")
    if new_csv_path.lower().endswith(".zip"):
        # Momence now exports Total Sales as a multi-product ZIP.
        # The ZIP contains per-product CSVs plus a combined summary.
        # Extract the combined CSV (avoids the per-product payment-method-only schema).
        import io as _io

        with zipfile.ZipFile(new_csv_path) as _zf:
            _names = _zf.namelist()
            # Prefer the non-aggregate combined file; fall back to concatenating all CSVs
            _combined = next(
                (
                    n
                    for n in _names
                    if n.lower().endswith("-combined.csv")
                    and "aggregate" not in n.lower()
                ),
                None,
            )
            if _combined:
                print(f"[INFO] ZIP detected — extracting combined report: {_combined}")
                df_new = pd.read_csv(_io.BytesIO(_zf.read(_combined)))
            else:
                _csvs = [n for n in _names if n.lower().endswith(".csv")]
                print(
                    f"[INFO] ZIP detected (no combined CSV) — concatenating {len(_csvs)} CSVs"
                )
                df_new = pd.concat(
                    [pd.read_csv(_io.BytesIO(_zf.read(n))) for n in _csvs],
                    ignore_index=True,
                )
    else:
        df_new = pd.read_csv(new_csv_path)

    # Normalize column names: Momence sometimes exports "Payment date"+"Service date" instead of "Date"
    # Use case-insensitive matching to handle any capitalisation variant.
    col_map = {c.lower(): c for c in df_new.columns}
    if "payment date" in col_map and COL_SALES_DATE not in df_new.columns:
        df_new = df_new.rename(columns={col_map["payment date"]: COL_SALES_DATE})
    if "service date" in col_map:
        df_new = df_new.drop(columns=[col_map["service date"]])

    if COL_SALES_DATE not in df_new.columns:
        print(
            f"[ERROR] Downloaded sales CSV has no '{COL_SALES_DATE}' or 'Payment date' column. "
            f"Columns found: {list(df_new.columns)}"
        )
        return 0

    if os.path.exists(MASTER_SALES_FILE):
        print(f"[INFO] Reading existing master sales CSV: {MASTER_SALES_FILE}")
        df_master = pd.read_csv(MASTER_SALES_FILE)
    else:
        print("[INFO] Master sales CSV does not exist yet; will create a new one.")
        df_master = pd.DataFrame(columns=df_new.columns)

    original_master_len = len(df_master)

    # Warn if the downloaded file doesn't extend beyond what's already in master.
    if original_master_len > 0 and COL_SALES_DATE in df_master.columns:
        try:
            new_max = pd.to_datetime(df_new[COL_SALES_DATE], format="mixed").max()
            master_max = pd.to_datetime(df_master[COL_SALES_DATE], format="mixed").max()
            if new_max <= master_max:
                print(
                    f"[WARN] Downloaded sales data only extends to {new_max.date()} "
                    f"which is not beyond master max {master_max.date()}. "
                    "The download button may be returning a cached/monthly snapshot "
                    "rather than the requested date range. 0 new records will be added."
                )
        except Exception:
            pass

    # Deduplication key: Date + Sale reference
    df_new["dedupe_key"] = (
        df_new[COL_SALES_DATE].astype(str).str.strip()
        + "|"
        + df_new[COL_SALES_REFERENCE].astype(str).str.strip()
    )
    df_master["dedupe_key"] = (
        df_master[COL_SALES_DATE].astype(str).str.strip()
        + "|"
        + df_master[COL_SALES_REFERENCE].astype(str).str.strip()
    )

    combined = pd.concat([df_master, df_new], ignore_index=True)
    before = len(combined)
    combined = combined.drop_duplicates(subset="dedupe_key", keep="first")
    after = len(combined)

    print(f"[INFO] Rows before de-duplication: {before}")
    print(f"[INFO] Rows after  de-duplication: {after}")
    print(f"[INFO] Removed {before - after} duplicate rows.")

    combined = combined.drop(columns=["dedupe_key"])
    combined.to_csv(MASTER_SALES_FILE, index=False)
    print(f"[INFO] Master sales CSV updated: {MASTER_SALES_FILE}")

    base_name = os.path.basename(new_csv_path)
    archive_path = os.path.join(ARCHIVE_DIR, base_name)
    os.replace(new_csv_path, archive_path)
    print(f"[INFO] CSV moved to archive: {archive_path}")

    added = after - original_master_len
    return added


# ==============================
# 8. MEMBERSHIP SALES REPORT
# ==============================


def download_membership_sales_report(driver):
    """
    Download the Membership Sales report for the specified date range.

    Arguments:
        driver: Selenium WebDriver instance.
    """
    membership_sales_url = (
        "https://momence.com/dashboard/32083/reports/membership-sales/8262815"
        "?computedSaleValue=true&day=2026-03-02T00%3A00%3A00.000Z"
        "&endDate=2026-03-31T13%3A59%3A59.999Z&endDate2=2026-03-31T13%3A59%3A59.999Z"
        "&excludeCustomersWithoutVisits=false&excludeGiftCardPaymentMethod=false"
        "&excludeInactiveMembers=false&excludeMembershipRenews=false&groupRecurring=false"
        "&hideVoided=false&hostId=32083&includeCustomersActivityLog=false"
        "&includeCustomersDetails=false&includeRefunds=false&includeVatInRevenue=true"
        "&moneyCreditSalesFilter=filterOutSalesPaidByMoneyCredits&preset=4&preset2=4"
        "&showOnlySpotfillerRevenue=false&splitByTeacher=false"
        "&startDate=2026-02-28T14%3A00%3A00.000Z&startDate2=2026-02-28T14%3A00%3A00.000Z"
        "&subFilters=%5B%7B%221%22%3A%22%22%2C%226%22%3A%22%5B%5D%22%7D%5D"
        "&timeZone=Australia%2FBrisbane&useBookedEntityDateRange=false"
    )

    print(f"[INFO] Navigating to Membership Sales report URL: {membership_sales_url}")
    driver.get(membership_sales_url)

    try:
        print("[INFO] Waiting for the download button to become clickable...")
        wait = WebDriverWait(driver, PAGE_LOAD_TIMEOUT)
        download_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, DOWNLOAD_BUTTON_SELECTOR))
        )

        print("[INFO] Clicking the download button...")
        download_button.click()

        # Wait for the file to download completely (include ZIPs so a leftover
        # Total Sales ZIP is not mistaken for a Membership Sales download).
        before_files = set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv"))) | set(
            glob.glob(os.path.join(DOWNLOAD_DIR, "*.zip"))
        )
        new_file = wait_for_new_download(before_files)

        if new_file:
            print(f"[INFO] Membership Sales report downloaded: {new_file}")
            # Rename the file to avoid conflicts
            renamed_file = os.path.join(DOWNLOAD_DIR, "membership-sales-report.csv")
            if os.path.exists(renamed_file):
                print(f"[WARNING] Target file already exists. Deleting: {renamed_file}")
                os.remove(renamed_file)  # Delete the existing file
            os.rename(new_file, renamed_file)
            print(f"[INFO] Renamed downloaded file to: {renamed_file}")
            new_file = renamed_file

            # Verify the renamed file exists
            if not os.path.exists(new_file):
                print(f"[ERROR] Renamed file does not exist: {new_file}")
                return
        else:
            print("[ERROR] Membership Sales report download failed or timed out.")
            print(
                f"[DEBUG] Files in download directory: {glob.glob(os.path.join(DOWNLOAD_DIR, '*.csv'))}"
            )
            return

    except Exception as e:
        print(f"[ERROR] Failed to download Membership Sales report: {e}")


# ==============================
# 9. MASTER MEMBERSHIP SALES SUMMARY
# ==============================


def create_or_update_master_membership_sales(driver):
    """
    Create or update the master membership sales summary file.

    Arguments:
        driver: Selenium WebDriver instance.
    """
    master_file = r"C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\master_membership_sales_summary.csv"

    # Determine the date range for the report
    if os.path.exists(master_file):
        # Load the master file to find the latest sale date
        master_df = pd.read_csv(master_file)
        master_df["Sale Date"] = pd.to_datetime(
            master_df["Sale Date"], format="mixed", utc=True
        ).dt.tz_localize(None)
        latest_date = master_df["Sale Date"].max()
        start_date = (latest_date - timedelta(days=1)).strftime(
            "%Y-%m-%dT%H:%M:%S.000Z"
        )
    else:
        # Initial load: start from 1 July 2025
        start_date = "2025-07-01T00:00:00.000Z"

    end_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")

    # Build the URL with the date range
    membership_sales_url = (
        f"https://momence.com/dashboard/32083/reports/membership-sales/9554206"
        f"?startDate={start_date}&endDate={end_date}"
        f"&computedSaleValue=true&excludeCustomersWithoutVisits=false"
        f"&excludeGiftCardPaymentMethod=false&excludeInactiveMembers=false"
        f"&excludeMembershipRenews=false&groupRecurring=false&hideVoided=false"
        f"&hostId=32083&includeCustomersActivityLog=false&includeCustomersDetails=false"
        f"&includeRefunds=false&includeVatInRevenue=true&moneyCreditSalesFilter=filterOutSalesPaidByMoneyCredits"
        f"&preset=4&preset2=4&showOnlySpotfillerRevenue=false&splitByTeacher=false"
        f"&timeZone=Australia%2FBrisbane&useBookedEntityDateRange=false"
    )

    print(f"[INFO] Navigating to Membership Sales report URL: {membership_sales_url}")
    driver.get(membership_sales_url)

    try:
        print("[INFO] Waiting for the download button to become clickable...")
        wait = WebDriverWait(driver, PAGE_LOAD_TIMEOUT)
        download_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, DOWNLOAD_BUTTON_SELECTOR))
        )

        print("[INFO] Clicking the download button...")
        download_button.click()

        # Wait for the file to download completely (include ZIPs so a leftover
        # Total Sales ZIP is not mistaken for a Membership Sales download).
        before_files = set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv"))) | set(
            glob.glob(os.path.join(DOWNLOAD_DIR, "*.zip"))
        )
        new_file = wait_for_new_download(before_files)

        if new_file:
            print(f"[INFO] Membership Sales report downloaded: {new_file}")
            # Rename the file to avoid conflicts
            renamed_file = os.path.join(DOWNLOAD_DIR, "membership-sales-report.csv")
            if os.path.exists(renamed_file):
                print(f"[WARNING] Target file already exists. Deleting: {renamed_file}")
                os.remove(renamed_file)  # Delete the existing file
            os.rename(new_file, renamed_file)
            print(f"[INFO] Renamed downloaded file to: {renamed_file}")
            new_file = renamed_file

            # Verify the renamed file exists
            if not os.path.exists(new_file):
                print(f"[ERROR] Renamed file does not exist: {new_file}")
                return
        else:
            print("[ERROR] Membership Sales report download failed or timed out.")
            print(
                f"[DEBUG] Files in download directory: {glob.glob(os.path.join(DOWNLOAD_DIR, '*.csv'))}"
            )
            return

        # Load the downloaded file
        new_df = pd.read_csv(new_file)
        # Rename 'Bought Date/Time (GMT)' to 'Sale Date' and handle timezone conversion
        if "Bought Date/Time (GMT)" in new_df.columns:
            new_df["Sale Date"] = pd.to_datetime(new_df["Bought Date/Time (GMT)"])
            if new_df["Sale Date"].dt.tz is None:
                # If naive, localize to UTC first
                new_df["Sale Date"] = new_df["Sale Date"].dt.tz_localize("UTC")
            # Convert to Australia/Brisbane timezone and strip tz info
            # (so CSV saves as plain local datetime, not ISO with +10:00 offset)
            new_df["Sale Date"] = (
                new_df["Sale Date"]
                .dt.tz_convert("Australia/Brisbane")
                .dt.tz_localize(None)
            )
        else:
            print(
                "[ERROR] 'Bought Date/Time (GMT)' column not found in the downloaded file."
            )
            print(f"[DEBUG] Available columns: {list(new_df.columns)}")
            return

        # Ensure 'Sale Date' column exists
        if "Sale Date" not in new_df.columns:
            print("[ERROR] 'Sale Date' column not found in the downloaded file.")
            print(f"[DEBUG] Available columns: {list(new_df.columns)}")
            return

        # Debug: Check if new_df contains data
        print(f"[DEBUG] New DataFrame shape: {new_df.shape}")

        # Append to the master file with deduplication
        if os.path.exists(master_file):
            print(f"[INFO] Reading existing master file: {master_file}")
            master_df = pd.read_csv(master_file)
            combined_df = pd.concat([master_df, new_df]).drop_duplicates(
                subset=["Purchase ID"]
            )
        else:
            print("[INFO] Master file does not exist. Creating a new one.")
            combined_df = new_df

        # Debug: Check combined DataFrame shape
        print(f"[DEBUG] Combined DataFrame shape: {combined_df.shape}")

        # Save the updated master file
        combined_df.to_csv(master_file, index=False)
        print(f"[INFO] Master membership sales summary updated: {master_file}")

    except Exception as e:
        append_to_batch_log(f"Exception during Membership Sales: {e}")
        append_to_batch_log(f"Stack trace: {traceback.format_exc()}")


def process_manual_membership_sales(file_path):
    """
    Process a manually downloaded Membership Sales history file and update the master summary file.

    Arguments:
        file_path (str): Path to the manually downloaded file.
    """
    master_file = r"C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\master_membership_sales_summary.csv"

    # Load the manually downloaded file
    print(
        r"[INFO] Reading manually downloaded file: C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\momence_downloads\momence--membership-sales-export history.csv"
    )
    new_df = pd.read_csv(
        r"C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\momence_downloads\momence--membership-sales-export history.csv"
    )

    # Rename 'Bought Date/Time (GMT)' to 'Sale Date' and handle timezone conversion
    if "Bought Date/Time (GMT)" in new_df.columns:
        new_df["Sale Date"] = pd.to_datetime(new_df["Bought Date/Time (GMT)"])
        if new_df["Sale Date"].dt.tz is None:
            # If naive, localize to UTC first
            new_df["Sale Date"] = new_df["Sale Date"].dt.tz_localize("UTC")
        # Convert to Australia/Brisbane timezone and strip tz info
        # (so CSV saves as plain local datetime, not ISO with +10:00 offset)
        new_df["Sale Date"] = (
            new_df["Sale Date"].dt.tz_convert("Australia/Brisbane").dt.tz_localize(None)
        )
    else:
        print("[ERROR] 'Bought Date/Time (GMT)' column not found in the file.")
        print(f"[DEBUG] Available columns: {list(new_df.columns)}")
        return

    # Ensure 'Sale Date' column exists
    if "Sale Date" not in new_df.columns:
        print("[ERROR] 'Sale Date' column not found after processing.")
        print(f"[DEBUG] Available columns: {list(new_df.columns)}")
        return

    # Append to the master file with deduplication
    if os.path.exists(master_file):
        print(f"[INFO] Reading existing master file: {master_file}")
        master_df = pd.read_csv(master_file)
        combined_df = pd.concat([master_df, new_df]).drop_duplicates(
            subset=["Purchase ID"]
        )
    else:
        print("[INFO] Master file does not exist. Creating a new one.")
        combined_df = new_df

    # Save the updated master file
    combined_df.to_csv(master_file, index=False)
    print(f"[INFO] Master membership sales summary updated: {master_file}")


# ==============================
# 10. BATCH LOGGING AND MAIN
# ==============================


_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Master batch log — moved out of OneDrive on 2026-05-18 to stop sync locks
# truncating writes. Falls back to the legacy in-tree path if the local
# folder is absent (e.g. clean checkout on a new machine).
_LOCAL_BATCH_LOG_DIR = r"C:\Users\markj\Momence_local_logs"
if os.path.isdir(_LOCAL_BATCH_LOG_DIR):
    _BATCH_LOG = os.path.join(_LOCAL_BATCH_LOG_DIR, "Momence_batch_log.txt")
else:
    _BATCH_LOG = os.path.join(_SCRIPT_DIR, "Log_files", "Momence_batch_log.txt")


def append_to_batch_log(message):
    """Append a timestamped message to the shared batch log.

    Retries up to 3 times (2-second gap) to handle transient OneDrive locks.
    Falls back to stderr so the message appears in the chain log.
    """
    import sys

    os.makedirs(os.path.dirname(_BATCH_LOG), exist_ok=True)
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {message}\n"
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
    """
    Orchestrate all six Momence report downloads in sequence.

    Reports run in order: No Card Customers, Failed Penalty Charges,
    Late Cancellations, No Shows, Total Sales, Membership Sales.
    Each report is wrapped in its own try/except so a failure in one
    report does not prevent the remaining reports from running.
    """
    import traceback

    ensure_directories()
    driver = create_chrome_driver()
    try:
        load_cookies_if_available(driver)

        # ---- Report 1: No Card Customers ----
        try:
            before_files = set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv"))) | set(
                glob.glob(os.path.join(DOWNLOAD_DIR, "*.zip"))
            )
            open_report_and_download(driver, MOMENCE_CRM_URL)
            new_file = wait_for_new_download(before_files)
            if new_file:
                added = append_and_dedupe(new_file, driver)
                append_to_batch_log(
                    f"{added} records added to No Card Customers (current snapshot)"
                )
            else:
                append_to_batch_log(
                    "Failed to download new CSV file for No Card customers"
                )
        except Exception as e:
            append_to_batch_log(f"Exception during No Card Customers: {e}")
            append_to_batch_log(f"Stack trace: {traceback.format_exc()}")

        # ---- Report 2: Failed Penalty Charges ----
        try:
            penalties_url, start_date, end_date = build_penalties_url()
            before_files = set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv"))) | set(
                glob.glob(os.path.join(DOWNLOAD_DIR, "*.zip"))
            )
            open_report_and_download(
                driver,
                penalties_url,
                prefer_button_text="Download summary",
                click_apply_filters=True,
                set_date_range=(start_date, end_date),
            )
            new_file = wait_for_new_download(before_files)
            if new_file:
                added = append_and_dedupe_penalties(new_file, driver)
                append_to_batch_log(
                    f"{added} records added to Failed Penalty Charges"
                    f" ({start_date} to {end_date})"
                )
            else:
                append_to_batch_log(
                    f"Failed to download Failed Penalty Charges"
                    f" ({start_date} to {end_date})"
                )
        except Exception as e:
            append_to_batch_log(f"Exception during Failed Penalty Charges: {e}")
            append_to_batch_log(f"Stack trace: {traceback.format_exc()}")

        # ---- Report 3: Late Cancellations ----
        try:
            late_url, start_date, end_date = build_late_cancellations_url()
            before_files = set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv"))) | set(
                glob.glob(os.path.join(DOWNLOAD_DIR, "*.zip"))
            )
            open_report_and_download(
                driver,
                late_url,
                prefer_button_text="Download summary",
                click_apply_filters=True,
                set_date_range=(start_date, end_date),
            )
            new_file = wait_for_new_download(before_files)
            if new_file:
                added = append_and_dedupe_late_cancellations(new_file, driver)
                append_to_batch_log(
                    f"{added} records added to Late Cancellations"
                    f" ({start_date} to {end_date})"
                )
            else:
                append_to_batch_log(
                    f"Failed to download Late Cancellations"
                    f" ({start_date} to {end_date})"
                )
        except Exception as e:
            append_to_batch_log(f"Exception during Late Cancellations: {e}")
            append_to_batch_log(f"Stack trace: {traceback.format_exc()}")

        # ---- Report 4: No Shows ----
        try:
            no_shows_url, start_date, end_date = build_no_shows_url()
            before_files = set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv"))) | set(
                glob.glob(os.path.join(DOWNLOAD_DIR, "*.zip"))
            )
            open_report_and_download(
                driver,
                no_shows_url,
                prefer_button_text="Download summary",
                click_apply_filters=True,
                set_date_range=(start_date, end_date),
            )
            new_file = wait_for_new_download(before_files)
            if new_file:
                added = append_and_dedupe_no_shows(new_file, driver)
                append_to_batch_log(
                    f"{added} records added to No Shows"
                    f" ({start_date} to {end_date})"
                )
            else:
                append_to_batch_log(
                    f"Failed to download No Shows ({start_date} to {end_date})"
                )
        except Exception as e:
            append_to_batch_log(f"Exception during No Shows: {e}")
            append_to_batch_log(f"Stack trace: {traceback.format_exc()}")

        # ---- Report 5: Total Sales ----
        try:
            sales_url, start_date, end_date = build_sales_url()
            before_files = set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv"))) | set(
                glob.glob(os.path.join(DOWNLOAD_DIR, "*.zip"))
            )
            open_report_and_download(
                driver,
                sales_url,
                prefer_button_text="Download summary",
                click_apply_filters=True,
                set_date_range=(start_date, end_date),
            )
            new_file = wait_for_new_download(before_files)
            if new_file:
                added = append_and_dedupe_sales(new_file, driver, start_date, end_date)
                append_to_batch_log(
                    f"{added} records added to Total Sales"
                    f" ({start_date} to {end_date})"
                )
            else:
                append_to_batch_log(
                    f"Failed to download Total Sales ({start_date} to {end_date})"
                )
        except Exception as e:
            append_to_batch_log(f"Exception during Total Sales: {e}")
            append_to_batch_log(f"Stack trace: {traceback.format_exc()}")

        # ---- Report 6: Membership Sales ----
        try:
            create_or_update_master_membership_sales(driver)
            append_to_batch_log("Membership Sales updated")
        except Exception as e:
            append_to_batch_log(f"Exception during Membership Sales: {e}")
            append_to_batch_log(f"Stack trace: {traceback.format_exc()}")

    finally:
        # 2026-05-02: driver.quit() was hanging on the 02:00 chain run after
        # Membership Sales completed, freezing the entire Run_Momence_Chain.bat
        # so Steps 7-10 never ran. Wrap quit() in a worker thread with a hard
        # timeout, then force-kill any leftover Chrome / chromedriver processes
        # so Python returns control to the .bat file no matter what.
        _quit_driver_safely(driver, timeout_seconds=30)


def _quit_driver_safely(driver, timeout_seconds=30):
    """Quit a Selenium driver with a hard timeout + Chrome force-kill fallback.

    Prevents the whole chain from hanging if chromedriver or Chrome itself
    refuses to exit cleanly (a known Selenium failure mode after long-running
    sessions or when a tab is mid-network-request).
    """
    import threading, sys

    quit_done = threading.Event()

    def _quit_worker():
        try:
            driver.quit()
        except Exception as exc:
            print(f"[WARN] driver.quit() raised: {exc}", file=sys.stderr)
        finally:
            quit_done.set()

    t = threading.Thread(target=_quit_worker, name="driver-quit", daemon=True)
    t.start()
    if not quit_done.wait(timeout_seconds):
        msg = (
            f"[WARN] driver.quit() did not return within {timeout_seconds}s — "
            "force-killing chromedriver/Chrome to release the chain"
        )
        print(msg, file=sys.stderr)
        try:
            append_to_batch_log(
                f"WARN: driver.quit() hung after {timeout_seconds}s — force-killed Chrome"
            )
        except Exception:
            pass
        # Best-effort kill on Windows; ignore failures so we still exit cleanly
        try:
            import subprocess
            for proc in ("chromedriver.exe", "chrome.exe"):
                subprocess.run(
                    ["taskkill", "/F", "/T", "/IM", proc],
                    capture_output=True,
                    timeout=10,
                )
        except Exception as kill_exc:
            print(f"[WARN] Force-kill failed: {kill_exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
