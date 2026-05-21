"""
momence_new_reports.py
======================

Downloads seven new Momence KPI reports (Priority 3) and maintains
rolling master CSV files for each.  Modelled on Momence_no_card_customers.py
and applying all lessons from Momence_data_scraping_wisdom.md.

Reports
-------
1. Active Members with KPIs         → master_active_members.csv           (SNAPSHOT – replace each run)
2. Membership Cancellations         → master_membership_cancellations.csv  (ACCUMULATE – append + dedup)
3. Upcoming Membership Expirations  → master_upcoming_expirations.csv      (SNAPSHOT – replace each run)
4. Non-member Customers             → master_non_member_customers.csv      (SNAPSHOT – replace each run)
5. Intro Offer Conversions          → master_intro_offer_conversions.csv   (ACCUMULATE – append + dedup)
6. Class Occupancy                  → master_class_occupancy.csv           (ACCUMULATE – append + dedup)
7. Teacher Payroll (per teacher)    → master_teacher_payroll.csv           (SNAPSHOT – replace each run)

SNAPSHOT reports represent point-in-time state; the downloaded file
completely replaces the master on each run (like Momence-No-Card-Customers.csv).

ACCUMULATE reports grow over time; new rows are appended with 1-day
lookback overlap to catch late-arriving records (like master-sales-summary.csv).

Debug mode
----------
Set DEBUG_MODE = True to restrict date ranges to a short window so the
script runs quickly during testing.  Set to False for production runs.

Authentication
--------------
Cookie-based.  First run: python momence_first_login_setup.py
Subsequent runs: automatic.

All paths relative to:
  C:\\Users\\markj\\OneDrive - MFPL\\Documents\\Customer Projects\\Ritual\\Momence_data\\
"""

import os
import sys
import time
import glob
import pickle
import re
import traceback
from datetime import datetime, timedelta
from pathlib import Path

# ── optional .env loading ────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print("[INFO] Loaded credentials from .env file")
    else:
        print("[INFO] No .env file found; using environment variables only")
except ImportError:
    print("[WARN] python-dotenv not installed – skipping .env loading")

import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ============================================================
# 1.  DEBUG MODE
# ============================================================
# When True, accumulating reports use a short date window (last N days)
# instead of querying all history.  Snapshot reports use the current week
# instead of the full current month.  Set False for production.

# DEBUG_MODE controls the date window for downloads.
# Production: False (use full date range from master file or initial_start).
# Testing:    True  (limit to last DEBUG_DAYS days for a fast test run).
# Override via environment variable: set MOMENCE_DEBUG_MODE=true to force debug.
DEBUG_MODE = os.environ.get("MOMENCE_DEBUG_MODE", "false").lower() == "true"
DEBUG_DAYS = 14   # accumulating reports: look back this many days in debug mode
DEBUG_SNAP_DAYS = 7   # snapshot reports: look back this many days in debug mode

print(f"[CONFIG] DEBUG_MODE = {DEBUG_MODE}")
if DEBUG_MODE:
    print(f"[CONFIG] Accumulating reports: last {DEBUG_DAYS} days only")
    print(f"[CONFIG] Snapshot reports:     last {DEBUG_SNAP_DAYS} days only")


# ============================================================
# 2.  USER CONFIGURATION
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DOWNLOAD_DIR = os.path.join(SCRIPT_DIR, "momence_downloads")
ARCHIVE_DIR  = os.path.join(DOWNLOAD_DIR, "Archive")
LOG_DIR      = os.path.join(SCRIPT_DIR, "Log_files")

# Master batch log — moved out of OneDrive on 2026-05-18 to stop sync locks
# truncating writes. Falls back to the legacy in-tree path if the local
# folder is absent (e.g. clean checkout on a new machine).
_LOCAL_BATCH_LOG_DIR = r"C:\Users\markj\Momence_local_logs"
if os.path.isdir(_LOCAL_BATCH_LOG_DIR):
    BATCH_LOG_FILE = os.path.join(_LOCAL_BATCH_LOG_DIR, "Momence_batch_log.txt")
else:
    BATCH_LOG_FILE = os.path.join(LOG_DIR, "Momence_batch_log.txt")
DEBUG_HTML_FILE = os.path.join(LOG_DIR, "debug_page_source_no_button.html")
DIAGNOSTICS_DIR = os.path.join(LOG_DIR, "diagnostics")

COOKIE_PICKLE = os.path.join(SCRIPT_DIR, "momence_cookies.pickle")

# ── Master CSV paths ─────────────────────────────────────────────────────────
MASTER_ACTIVE_MEMBERS       = os.path.join(SCRIPT_DIR, "master_active_members.csv")
MASTER_CANCELLATIONS        = os.path.join(SCRIPT_DIR, "master_membership_cancellations.csv")
MASTER_EXPIRATIONS          = os.path.join(SCRIPT_DIR, "master_upcoming_expirations.csv")
MASTER_NON_MEMBERS          = os.path.join(SCRIPT_DIR, "master_non_member_customers.csv")
MASTER_INTRO_CONVERSIONS    = os.path.join(SCRIPT_DIR, "master_intro_offer_conversions.csv")
MASTER_OCCUPANCY            = os.path.join(SCRIPT_DIR, "master_class_occupancy.csv")
MASTER_PAYROLL              = os.path.join(SCRIPT_DIR, "master_teacher_payroll.csv")

# ── Initial load start dates for ACCUMULATING reports (no master yet) ────────
CANCELLATIONS_INITIAL_START = datetime(2025, 7, 1)
INTRO_CONV_INITIAL_START    = datetime(2025, 7, 1)
OCCUPANCY_INITIAL_START     = datetime(2025, 12, 9)
# PAYROLL_INITIAL_START was used when Teacher Payroll was an ACCUMULATE report.
# Kept here (commented) for reference in case Momence reverts the export format.
# PAYROLL_INITIAL_START       = datetime(2025, 12, 9)

# ── Base URLs (date params stripped; injected at runtime) ────────────────────
#    Source: "Recommended reports to add to the dashboard 2026 03 16.txt"

ACTIVE_MEMBERS_BASE_URL = (
    "https://momence.com/dashboard/32083/reports/active-members/8548778"
    "?computedSaleValue=true&excludeCustomersWithoutVisits=false"
    "&excludeGiftCardPaymentMethod=false&excludeInactiveMembers=false"
    "&excludeMembershipRenews=false&groupRecurring=false&hideVoided=false"
    "&hostId=32083&includeCustomersActivityLog=false&includeCustomersDetails=false"
    "&includeRefunds=false&includeVatInRevenue=true"
    "&moneyCreditSalesFilter=filterOutSalesPaidByMoneyCredits"
    "&preset=4&preset2=4&showOnlySpotfillerRevenue=false&splitByTeacher=false"
    "&timeZone=Australia%2FBrisbane&useBookedEntityDateRange=false"
)

CANCELLATIONS_BASE_URL = (
    "https://momence.com/dashboard/32083/reports/membership-cancellations/8548788"
    "?computedSaleValue=true&excludeCustomersWithoutVisits=false"
    "&excludeGiftCardPaymentMethod=false&excludeInactiveMembers=false"
    "&excludeMembershipRenews=false&groupRecurring=false&hideVoided=false"
    "&hostId=32083&includeCustomersActivityLog=false&includeCustomersDetails=false"
    "&includeRefunds=false&includeVatInRevenue=true"
    "&moneyCreditSalesFilter=filterOutSalesPaidByMoneyCredits"
    "&preset=-1&preset2=4&showOnlySpotfillerRevenue=false&splitByTeacher=false"
    "&subFilters=%5B%7B%222%22%3A%22%5B%5D%22%7D%5D"
    "&timeZone=Australia%2FBrisbane&useBookedEntityDateRange=false"
)

EXPIRATIONS_BASE_URL = (
    "https://momence.com/dashboard/32083/reports/upcoming-memberships-expiration/8548784"
    "?computedSaleValue=true&excludeCustomersWithoutVisits=false"
    "&excludeGiftCardPaymentMethod=false&excludeInactiveMembers=false"
    "&excludeMembershipRenews=false&groupRecurring=false&hideVoided=false"
    "&hostId=32083&includeCustomersActivityLog=false&includeCustomersDetails=false"
    "&includeRefunds=false&includeVatInRevenue=true"
    "&moneyCreditSalesFilter=filterOutSalesPaidByMoneyCredits"
    "&preset=-1&preset2=4&showOnlySpotfillerRevenue=false&splitByTeacher=false"
    "&timeZone=Australia%2FBrisbane&useBookedEntityDateRange=false"
)

NON_MEMBERS_BASE_URL = (
    "https://momence.com/dashboard/32083/reports/non-member-customers/8548793"
    "?computedSaleValue=true&excludeCustomersWithoutVisits=false"
    "&excludeGiftCardPaymentMethod=false&excludeInactiveMembers=false"
    "&excludeMembershipRenews=false&groupRecurring=false&hideVoided=false"
    "&hostId=32083&includeCustomersActivityLog=false&includeCustomersDetails=false"
    "&includeRefunds=false&includeVatInRevenue=true"
    "&moneyCreditSalesFilter=filterOutSalesPaidByMoneyCredits"
    "&preset=-1&preset2=4&showOnlySpotfillerRevenue=false&splitByTeacher=false"
    "&timeZone=Australia%2FBrisbane&useBookedEntityDateRange=false"
)

INTRO_CONV_BASE_URL = (
    "https://momence.com/dashboard/32083/reports/intro-offers-conversions/8548800"
    "?computedSaleValue=true&excludeCustomersWithoutVisits=false"
    "&excludeGiftCardPaymentMethod=false&excludeInactiveMembers=false"
    "&excludeMembershipRenews=false&groupRecurring=false&hideVoided=false"
    "&hostId=32083&includeCustomersActivityLog=false&includeCustomersDetails=false"
    "&includeRefunds=false&includeVatInRevenue=true"
    "&moneyCreditSalesFilter=filterOutSalesPaidByMoneyCredits"
    "&preset=-1&preset2=4&showOnlySpotfillerRevenue=false&splitByTeacher=false"
    "&subFilters=%5B%7B%224%22%3A%22%5B%5D%22%7D%5D"
    "&timeZone=Australia%2FBrisbane&useBookedEntityDateRange=false"
)

OCCUPANCY_BASE_URL = (
    "https://momence.com/dashboard/32083/reports/session-occupancy/8548803"
    "?computedSaleValue=true&excludeCustomersWithoutVisits=false"
    "&excludeGiftCardPaymentMethod=false&excludeInactiveMembers=false"
    "&excludeMembershipRenews=false&groupRecurring=false&hideVoided=false"
    "&hostId=32083&includeCustomersActivityLog=false&includeCustomersDetails=false"
    "&includeRefunds=false&includeVatInRevenue=true"
    "&moneyCreditSalesFilter=filterOutSalesPaidByMoneyCredits"
    "&preset=-1&preset2=4&showOnlySpotfillerRevenue=false&splitByTeacher=false"
    "&timeZone=Australia%2FBrisbane&useBookedEntityDateRange=false"
)

PAYROLL_BASE_URL = (
    "https://momence.com/dashboard/32083/reports/teacher-payroll/8548810"
    "?computedSaleValue=true&excludeCustomersWithoutVisits=false"
    "&excludeGiftCardPaymentMethod=false&excludeInactiveMembers=false"
    "&excludeMembershipRenews=false&groupRecurring=false&hideVoided=false"
    "&hostId=32083&includeCustomersActivityLog=false&includeCustomersDetails=false"
    "&includeRefunds=false&includeVatInRevenue=true"
    "&moneyCreditSalesFilter=filterOutSalesPaidByMoneyCredits"
    "&preset=-1&preset2=4&showOnlySpotfillerRevenue=false&splitByTeacher=false"
    "&timeZone=Australia%2FBrisbane&useBookedEntityDateRange=false"
)

# ── Timing ───────────────────────────────────────────────────────────────────
PAGE_LOAD_TIMEOUT    = 300   # seconds – page load timeout for Chrome
DOWNLOAD_WAIT_TIMEOUT = 300  # seconds – wait for CSV to finish downloading
POLL_INTERVAL        = 2     # seconds – polling interval for download detection


# ============================================================
# 3.  UTILITY HELPERS
# ============================================================

def ensure_directories():
    """Create download, archive, and log directories if they do not exist."""
    for d in [DOWNLOAD_DIR, ARCHIVE_DIR, LOG_DIR]:
        os.makedirs(d, exist_ok=True)
        print(f"[INFO] Directory exists (or created): {d}")


def append_to_batch_log(message):
    """Append a timestamped message to the shared batch log file."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} {message}"
    print(f"[LOG] {line}")
    try:
        with open(BATCH_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"[WARN] Could not write to batch log: {e}")


def log_columns(df, report_name):
    """
    Log column names (and a sample row) from a downloaded CSV.
    This is critical on first run to verify dedup key column names.
    """
    print(f"[COLUMNS] {report_name}: {list(df.columns)}")
    if len(df) > 0:
        print(f"[SAMPLE]  {report_name} first row:\n{df.iloc[0].to_dict()}")
    else:
        print(f"[WARN] {report_name}: downloaded CSV is EMPTY (header only)")


# ============================================================
# 4.  DATE HELPERS  (Brisbane UTC+10, no DST)
# ============================================================

def brisbane_utc_strings(start_dt, end_dt):
    """
    Convert Brisbane local datetimes to the UTC timestamp strings that
    Momence expects in report URL parameters.

    Brisbane (AEST) is UTC+10, no daylight saving.
    Midnight Brisbane  = 14:00 UTC the *previous* calendar day.
    23:59:59 Brisbane  = 13:59:59 UTC the *same* calendar day.

    Returns (start_utc_str, end_utc_str, day_utc_str)
      where day_utc_str = today at 00:00 UTC (used for the 'day' param).
    """
    # start: midnight Brisbane on start_dt.date() → subtract 10h → UTC
    start_utc = datetime(start_dt.year, start_dt.month, start_dt.day, 0, 0, 0) - timedelta(hours=10)
    # end: 23:59:59 Brisbane on end_dt.date()
    end_utc   = datetime(end_dt.year, end_dt.month, end_dt.day, 23, 59, 59) - timedelta(hours=10)
    # day: today at midnight UTC (used unchanged by Momence)
    day_utc   = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    fmt = "%Y-%m-%dT%H:%M:%S.000Z"
    s = start_utc.strftime(fmt)
    e = end_utc.strftime(fmt)
    d = day_utc.strftime(fmt)

    print(f"[DATE]   Brisbane range: {start_dt.date()} → {end_dt.date()}")
    print(f"[DATE]   UTC start:  {s}")
    print(f"[DATE]   UTC end:    {e}")
    print(f"[DATE]   UTC day:    {d}")
    return s, e, d


def build_date_url(base_url, start_dt, end_dt):
    """
    Append startDate, startDate2, endDate, endDate2, day parameters to a
    Momence base URL.  All date values are derived from Brisbane local times.
    """
    s, e, d = brisbane_utc_strings(start_dt, end_dt)
    url = (
        f"{base_url}"
        f"&startDate={s}"
        f"&startDate2={s}"
        f"&endDate={e}"
        f"&endDate2={e}"
        f"&day={d}"
    )
    return url


def accumulating_date_range(master_file, date_col, initial_start, label):
    """
    Determine (start_dt, end_dt) for an ACCUMULATING report.

    start_dt = most recent date in master minus 1 day (to catch late arrivals).
               Falls back to initial_start if master is empty or missing.
    end_dt   = yesterday (Brisbane).

    In DEBUG_MODE the window is capped at DEBUG_DAYS regardless of master state.
    """
    today_brisbane = datetime.now()
    yesterday = today_brisbane - timedelta(days=1)

    if DEBUG_MODE:
        start_dt = today_brisbane - timedelta(days=DEBUG_DAYS)
        print(f"[DEBUG] {label}: DEBUG_MODE – using last {DEBUG_DAYS} days only")
        print(f"[DEBUG] {label}: start_dt = {start_dt.date()}, end_dt = {yesterday.date()}")
        return start_dt, yesterday

    # Normal mode: look at master to find most recent date
    start_dt = initial_start  # fallback
    if os.path.exists(master_file):
        try:
            df = pd.read_csv(master_file, usecols=[date_col])
            if len(df) > 0:
                most_recent = pd.to_datetime(df[date_col], format="mixed").max()
                start_dt = most_recent - timedelta(days=1)
                print(f"[INFO] {label}: most recent in master = {most_recent.date()}, "
                      f"start_dt = {start_dt.date()}")
        except Exception as ex:
            print(f"[WARN] {label}: could not read date column '{date_col}' "
                  f"from master ({ex}). Falling back to {initial_start.date()}")
    else:
        print(f"[INFO] {label}: no master file yet; starting from {initial_start.date()}")

    print(f"[INFO] {label}: date range {start_dt.date()} → {yesterday.date()}")
    return start_dt, yesterday


def snapshot_date_range(label):
    """
    Determine (start_dt, end_dt) for a SNAPSHOT report.

    Production: start of current month → end of current month.
    Debug:      last DEBUG_SNAP_DAYS days.

    Snapshot masters are REPLACED each run (not appended).
    """
    today = datetime.now()
    if DEBUG_MODE:
        start_dt = today - timedelta(days=DEBUG_SNAP_DAYS)
        end_dt   = today
        print(f"[DEBUG] {label}: SNAPSHOT DEBUG – last {DEBUG_SNAP_DAYS} days "
              f"({start_dt.date()} → {end_dt.date()})")
    else:
        start_dt = today.replace(day=1)
        # End of current month: first day of next month minus 1 day
        if today.month == 12:
            end_dt = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_dt = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        print(f"[INFO] {label}: SNAPSHOT – current month "
              f"({start_dt.date()} → {end_dt.date()})")
    return start_dt, end_dt


# ============================================================
# 5.  BROWSER / AUTH
# ============================================================

def create_chrome_driver():
    """
    Create a Selenium Chrome WebDriver configured for:
    - Automatic CSV downloads to DOWNLOAD_DIR (no save dialog)
    - Reduced resource usage (no GPU, no extensions, no sandbox)
    """
    print("[INFO] Creating Chrome WebDriver...")
    chrome_options = Options()
    prefs = {
        "download.default_directory":   DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade":   True,
        "download.extensions_to_open":  "",
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    # Uncomment for headless (no visible window) – leave visible during debugging:
    # chrome_options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    print("[INFO] Chrome WebDriver created OK")
    return driver


def load_cookies_if_available(driver):
    """
    Load Momence session cookies from COOKIE_PICKLE so that the script
    can run without manual login.

    Pattern from Momence_data_scraping_wisdom.md:
    1. Navigate to base domain first (cookies must match domain).
    2. Load each cookie; skip any that raise an exception.
    3. Refresh to apply cookies.

    If the pickle does not exist the script continues without cookies
    (Momence will redirect to the login page, which is detected later).
    """
    if not os.path.exists(COOKIE_PICKLE):
        print(f"[WARN] Cookie file not found: {COOKIE_PICKLE}")
        print("[WARN] Run momence_first_login_setup.py to generate it.")
        return

    print(f"[INFO] Loading cookies from: {COOKIE_PICKLE}")
    driver.get("https://momence.com/")   # must visit base domain first
    try:
        with open(COOKIE_PICKLE, "rb") as f:
            cookies = pickle.load(f)
        loaded = 0
        for cookie in cookies:
            cookie.pop("sameSite", None)   # Selenium incompatibility
            cookie.pop("expiry",   None)   # can cause add_cookie failures
            try:
                driver.add_cookie(cookie)
                loaded += 1
            except Exception as ce:
                print(f"[WARN] Skipped cookie '{cookie.get('name')}': {ce}")
        print(f"[INFO] Cookies loaded: {loaded}/{len(cookies)}")
        driver.refresh()
        time.sleep(3)
        print(f"[INFO] Post-cookie URL: {driver.current_url}")
    except Exception as e:
        print(f"[ERROR] Failed to load cookies: {e}")


def check_auth(driver, context=""):
    """
    Raise an exception if Momence has redirected to the login page.
    Called after navigating to report URLs to catch expired cookies early.
    """
    url   = driver.current_url
    title = driver.title
    print(f"[AUTH] {context} | URL: {url} | Title: {title}")
    if ("sign-in" in url or "login" in url or
            "Login"  in title or "Sign" in title):
        raise RuntimeError(
            f"Authentication failed ({context}): redirected to login page. "
            "Cookies may have expired – run momence_first_login_setup.py."
        )


def hide_intercom(driver):
    """
    Suppress the Intercom chat overlay that can block button clicks.
    Must be called before clicking pagination or download buttons.
    (Trap 1 from Momence_data_scraping_wisdom.md)
    """
    try:
        driver.execute_script("""
            var iframe = document.querySelector('iframe[data-intercom-frame="true"]');
            if (iframe) { iframe.style.display = 'none'; }
            var icon = document.querySelector('.intercom-lightweight-app-launcher');
            if (icon) { icon.style.display = 'none'; }
        """)
    except Exception:
        pass  # non-fatal – keep going


def dismiss_overlays(driver, label=""):
    """Dismiss anything that could intercept a download-button click.

    Covers four overlay families that have caused real failures:
      1. Modal dialogs (.modal-animation-*, [role="dialog"], ReactModal).
      2. The Momence top-right notifications flyout — the bell-icon dropdown
         showing "X sent you Call message" entries. This was the overlay
         visible in the 2026-05-12 No Shows failure screenshot.
      3. Backdrops/overlays that linger after a modal closes.
      4. The Intercom chat icon (re-hidden via hide_intercom).

    Best-effort. Errors are swallowed; the caller falls back to its existing
    click strategies regardless.
    """
    try:
        removed = driver.execute_script("""
            let removed = 0;

            // 1) Modal-style overlays
            const modalSelectors = [
                '.modal-animation-appear-done',
                '.modal-animation-enter-done',
                '[role="dialog"]',
                '[role="alertdialog"]',
                '.ReactModal__Content',
            ];
            for (const sel of modalSelectors) {
                document.querySelectorAll(sel).forEach(m => {
                    const closeBtn = m.querySelector(
                        'button[aria-label*="close" i],'
                      + 'button[aria-label*="dismiss" i],'
                      + 'button[aria-label*="not now" i],'
                      + 'button.close,'
                      + 'button[title*="close" i]'
                    );
                    if (closeBtn) { try { closeBtn.click(); } catch(e) {} }
                    try { m.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape', bubbles:true})); } catch(e) {}
                    try { m.remove(); removed++; } catch(e) {}
                });
            }

            // 2) Notifications flyout (bell-icon dropdown).
            //    Selectors target both the trigger and the visible panel; we
            //    collapse it by toggling aria-expanded off and removing the
            //    panel from the DOM if it lingers.
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

            // 3) Generic backdrops / overlays still hanging around
            const backdropSelectors = [
                '.ReactModal__Overlay',
                '.modal-backdrop',
                '[class*="backdrop" i]',
                '[class*="overlay" i]',
            ];
            for (const sel of backdropSelectors) {
                document.querySelectorAll(sel).forEach(el => { try { el.remove(); } catch(e) {} });
            }

            // 4) Final Escape, in case anything else is listening
            document.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape', bubbles:true}));

            return removed;
        """)
        if removed:
            print(f"[INFO] {label}: dismiss_overlays removed {removed} blocking element(s)")
    except Exception as e:
        # Non-fatal — the caller's strategies will still try
        print(f"[DEBUG] {label}: dismiss_overlays failed (non-fatal): {e}")
    # Also re-hide Intercom in case it reappeared
    hide_intercom(driver)


def wait_for_apply_filters_idle(driver, label="", timeout=120):
    """Wait until the 'Apply filters' button is enabled again.

    After clicking Apply Filters, Momence disables the button while the
    underlying API request is in flight and the report is rendering.
    Polling for it to become clickable again is a more reliable "report
    finished loading" signal than a fixed sleep, because long date ranges
    can comfortably take > 15s (the old fixed wait that caused the
    2026-05-12 No Shows failure).

    Returns True if the button became enabled within the timeout,
    False otherwise. Either way the caller continues — the existing
    "Loading report..." text wait is still applied afterwards.
    """
    deadline = time.time() + timeout
    poll = 2
    while time.time() < deadline:
        try:
            state = driver.execute_script("""
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => /apply\\s*filters?/i.test(b.textContent || ''));
                if (!btn) return 'missing';
                if (btn.disabled || btn.getAttribute('aria-disabled') === 'true') return 'disabled';
                return 'ready';
            """)
            if state == 'ready':
                print(f"[INFO] {label}: Apply Filters is idle again — report ready to fetch")
                return True
            if state == 'missing':
                # No Apply Filters button visible at all — assume nothing to wait for
                return True
        except Exception as e:
            print(f"[DEBUG] {label}: wait_for_apply_filters_idle probe failed: {e}")
        time.sleep(poll)
    print(f"[WARN] {label}: Apply Filters still disabled after {timeout}s — proceeding anyway")
    return False


# ============================================================
# 6.  DOWNLOAD DETECTION
# ============================================================

def wait_for_new_download(before_files, timeout=DOWNLOAD_WAIT_TIMEOUT, label=""):
    """
    Poll DOWNLOAD_DIR until a new CSV (or ZIP) file appears.

    Args:
        before_files: set of file paths that existed BEFORE clicking download
        timeout:      maximum seconds to wait
        label:        report name for logging

    Returns:
        Full path to the new downloaded file, or None if timeout.
    """
    print(f"[INFO] {label}: waiting for new download (up to {timeout}s)...")
    for i in range(timeout // POLL_INTERVAL):
        elapsed = i * POLL_INTERVAL

        # Check for in-progress Chrome downloads
        crdownloads = glob.glob(os.path.join(DOWNLOAD_DIR, "*.crdownload"))
        if crdownloads and i == 0:
            print(f"[INFO] {label}: Chrome download in progress: "
                  f"{os.path.basename(crdownloads[0])}")

        # Check for completed CSV or ZIP files
        after_files = (
            set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv")))
            | set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.zip")))
        )
        new_files = after_files - before_files
        if new_files:
            new_file = list(new_files)[0]
            print(f"[INFO] {label}: download complete after {elapsed}s – "
                  f"{os.path.basename(new_file)}")
            time.sleep(2)   # brief pause to ensure file is fully flushed
            return new_file

        if elapsed > 0 and elapsed % 30 == 0:
            print(f"[INFO] {label}: still waiting… ({elapsed}/{timeout}s) "
                  f"crdownloads={len(crdownloads)}")

        time.sleep(POLL_INTERVAL)

    print(f"[ERROR] {label}: download timed out after {timeout}s")
    return None


# ============================================================
# 7.  OPEN REPORT AND TRIGGER DOWNLOAD  (core 3-strategy logic)
# ============================================================

def open_report_and_download(driver, url, label="", prefer_button_text=None,
                             click_apply_filters=True, set_date_range=None):
    """
    Navigate to a Momence report URL, optionally click Apply Filters,
    wait for the report to load, then click the download button.

    Uses three strategies to find the download button:
      1. Direct XPath wait
      2. Open three-dots menu first, then XPath
      3. JavaScript text search

    Args:
        driver:              Selenium WebDriver
        url:                 Full report URL (with date params already injected)
        label:               Report name for logging
        prefer_button_text:  If set, only click a button whose text matches this
                             (e.g. "Download summary" to avoid "Download details")
        click_apply_filters: If True, click Apply Filters before downloading
        set_date_range:      (start_dt, end_dt) tuple; if provided, also sets
                             flatpickr date pickers before clicking Apply Filters
    """
    print(f"\n{'='*60}")
    print(f"[INFO] {label}: navigating to report URL")
    print(f"[URL]  {url[:120]}...")
    print(f"[TIME] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ── Load the page ────────────────────────────────────────────────────────
    for attempt in range(1, 4):
        try:
            driver.get(url)
            print(f"[INFO] {label}: page loaded (attempt {attempt})")
            break
        except Exception as e:
            print(f"[WARN] {label}: page load attempt {attempt} failed: {e}")
            if attempt == 3:
                raise
            time.sleep(5 * attempt)

    print(f"[INFO] {label}: waiting 10s for page to stabilise...")
    time.sleep(10)

    check_auth(driver, f"{label} – after page load")

    # ── Optionally set date range via flatpickr ──────────────────────────────
    if click_apply_filters and set_date_range:
        start_dt, end_dt = set_date_range
        s, e, _ = brisbane_utc_strings(start_dt, end_dt)
        print(f"[INFO] {label}: setting flatpickr dates: {s} → {e}")
        try:
            result = driver.execute_script("""
                function findFlatpickr(el) {
                    for (var i = 0; i < 6 && el; i++) {
                        if (el._flatpickr) return el._flatpickr;
                        el = el.parentElement;
                    }
                    return null;
                }
                var fromEl = document.getElementById('dateTimeRangeFrom');
                var toEl   = document.getElementById('dateTimeRangeTo');
                if (!fromEl || !toEl) {
                    // Fallback: scan all DOM elements
                    var allFp = [];
                    document.querySelectorAll('*').forEach(function(el) {
                        if (el._flatpickr) allFp.push(el._flatpickr);
                    });
                    if (allFp.length >= 2) {
                        allFp[0].setDate(arguments[0], true);
                        allFp[1].setDate(arguments[1], true);
                        return 'ok via fallback scan';
                    }
                    return 'inputs not found';
                }
                var fromFp = findFlatpickr(fromEl);
                var toFp   = findFlatpickr(toEl);
                if (!fromFp || !toFp) return 'flatpickr instances not found';
                fromFp.setDate(arguments[0], true);
                toFp.setDate(arguments[1], true);
                return 'ok: from=' + fromEl.value + ' to=' + toEl.value;
            """, s, e)
            print(f"[INFO] {label}: flatpickr setDate result: {result}")
            time.sleep(1)
        except Exception as fe:
            print(f"[WARN] {label}: could not set flatpickr dates: {fe}")

    # ── Click Apply Filters ──────────────────────────────────────────────────
    if click_apply_filters:
        print(f"[INFO] {label}: looking for Apply Filters button...")
        apply_clicked = False

        # Strategy A: XPath
        for xpath in ["//button[contains(., 'Apply filters')]",
                      "//button[contains(., 'Apply Filters')]",
                      "//button[contains(., 'Apply')]"]:
            try:
                btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                print(f"[INFO] {label}: clicking Apply Filters: '{btn.text}'")
                hide_intercom(driver)
                btn.click()
                apply_clicked = True
                # Wait for the request to come back rather than guessing 15s.
                # The button stays disabled while data is loading; once it
                # becomes clickable again the fetch has completed.
                print(f"[INFO] {label}: Apply Filters clicked; waiting for it to become idle...")
                wait_for_apply_filters_idle(driver, label=label, timeout=180)
                break
            except Exception:
                continue

        # Strategy B: JavaScript fallback
        if not apply_clicked:
            try:
                js_result = driver.execute_script("""
                    const btns = Array.from(document.querySelectorAll('button'));
                    const btn = btns.find(b => /apply\\s*filters?/i.test(b.textContent));
                    if (btn) { btn.click(); return btn.textContent.trim(); }
                    return null;
                """)
                if js_result:
                    apply_clicked = True
                    print(f"[INFO] {label}: JS clicked Apply Filters ('{js_result}'); waiting for idle...")
                    wait_for_apply_filters_idle(driver, label=label, timeout=180)
            except Exception as je:
                print(f"[WARN] {label}: JS Apply Filters failed: {je}")

        if not apply_clicked:
            print(f"[WARN] {label}: could not find Apply Filters button – proceeding anyway")

        # ── Wait for "Loading report…" overlay to disappear ──────────────────
        print(f"[INFO] {label}: waiting for report data to finish loading...")
        max_loading_wait = 360   # up to 6 minutes for large date ranges
        poll = 5
        waited = 0
        while waited < max_loading_wait:
            try:
                driver.find_element(By.XPATH, "//*[contains(text(), 'Loading report')]")
                print(f"[INFO] {label}: still loading... ({waited}s elapsed)")
                time.sleep(poll)
                waited += poll
            except Exception:
                print(f"[INFO] {label}: loading complete (waited {waited}s)")
                break
        else:
            print(f"[WARN] {label}: still loading after {max_loading_wait}s – proceeding anyway")

    # ── Find and click the download button ───────────────────────────────────
    if prefer_button_text:
        button_xpath = f"//button[contains(., '{prefer_button_text}')]"
        js_regex     = prefer_button_text.replace(" ", "\\s+")
        print(f"[INFO] {label}: looking for '{prefer_button_text}' button...")
    else:
        button_xpath = ("//button[contains(., 'Export to CSV') or "
                        "contains(., 'Download summary') or "
                        "contains(., 'Download') or contains(., 'Export')]")
        js_regex = "export to csv|download summary|download|export"
        print(f"[INFO] {label}: looking for any download button...")

    download_clicked = False
    _MAX_BTN_RETRIES = 3
    _BTN_RETRY_WAIT  = 25  # seconds between retry rounds

    for _btn_attempt in range(1, _MAX_BTN_RETRIES + 1):
        if _btn_attempt > 1:
            print(
                f"[WARN] {label}: download button not found on attempt {_btn_attempt - 1} — "
                f"waiting {_BTN_RETRY_WAIT}s then retrying all strategies "
                f"(attempt {_btn_attempt}/{_MAX_BTN_RETRIES})..."
            )
            time.sleep(_BTN_RETRY_WAIT)

        download_clicked = False

        # Clear any overlay (notifications flyout, lingering modal, intercom)
        # that could intercept the click. This is what caused the recurring
        # "element click intercepted" warnings on Strategy 1/2 in production.
        dismiss_overlays(driver, label=label)

        # Strategy 1: Direct XPath
        try:
            hide_intercom(driver)
            btn = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath))
            )
            print(f"[INFO] {label}: Strategy 1 found download button: '{btn.text}'")
            btn.click()
            download_clicked = True
            print(f"[INFO] {label}: download button clicked (Strategy 1)")
        except Exception as e1:
            print(f"[DEBUG] {label}: Strategy 1 failed: {e1}")

        # Strategy 2: Open three-dots menu first
        if not download_clicked:
            print(f"[INFO] {label}: trying Strategy 2 (menu button)...")
            menu_selectors = [
                (By.CSS_SELECTOR, "div.sc-1kz352d-1.sc-1kz352d-3.jnInLk.fqEeHB"),
                (By.CSS_SELECTOR, "button[aria-label*='menu' i]"),
                (By.CSS_SELECTOR, "button[aria-label*='more' i]"),
                (By.XPATH,        "//button[contains(@class, 'menu')]"),
                (By.XPATH,        "//button/*[name()='svg']/../.."),  # icon-only menu buttons
            ]
            for sel_type, sel_val in menu_selectors:
                try:
                    dismiss_overlays(driver, label=label)
                    menu_btn = WebDriverWait(driver, 8).until(
                        EC.element_to_be_clickable((sel_type, sel_val))
                    )
                    menu_btn.click()
                    print(f"[INFO] {label}: menu opened with selector: {sel_val}")
                    time.sleep(2)
                    hide_intercom(driver)
                    btn = WebDriverWait(driver, 8).until(
                        EC.element_to_be_clickable((By.XPATH, button_xpath))
                    )
                    btn.click()
                    download_clicked = True
                    print(f"[INFO] {label}: download clicked after menu (Strategy 2)")
                    break
                except Exception:
                    continue
            if not download_clicked:
                print(f"[DEBUG] {label}: Strategy 2 failed (no menu found)")

        # Strategy 2b: Icon-attribute fallback — find button containing the
        # download_outline_20 icon and JS-click it.  Handles cases where Momence's
        # UI update replaced text buttons with icon-only controls.
        if not download_clicked:
            print(f"[INFO] {label}: trying Strategy 2b (icon name attribute)...")
            try:
                icon_xpath = "//button[.//i[@name='download_outline_20']]"
                btn_icon = driver.find_element(By.XPATH, icon_xpath)
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", btn_icon
                )
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", btn_icon)
                download_clicked = True
                print(f"[INFO] {label}: Strategy 2b clicked download via icon attribute")
            except Exception as e2b:
                print(f"[DEBUG] {label}: Strategy 2b failed: {e2b}")

        # Strategy 3: JavaScript text scan + icon fallback
        if not download_clicked:
            print(f"[INFO] {label}: trying Strategy 3 (JavaScript)...")
            try:
                result = driver.execute_script(f"""
                    const els = Array.from(document.querySelectorAll('button, a, div[role="button"]'));
                    let el = els.find(e => (e.textContent || '').match(/{js_regex}/i));
                    // Fallback: find button containing the download icon by its name attribute
                    if (!el) {{
                        const icon = document.querySelector('i[name="download_outline_20"]');
                        if (icon) el = icon.closest('button');
                    }}
                    if (el) {{ el.scrollIntoView({{block: 'center'}}); el.click(); return (el.textContent || el.getAttribute('aria-label') || 'icon-btn').trim(); }}
                    return null;
                """)
                if result:
                    download_clicked = True
                    print(f"[INFO] {label}: JS clicked download button: '{result}' (Strategy 3)")
                else:
                    print(f"[DEBUG] {label}: Strategy 3 found no matching button")
            except Exception as e3:
                print(f"[DEBUG] {label}: Strategy 3 failed: {e3}")

        if download_clicked:
            break  # success — exit retry loop

    if not download_clicked:
        print(f"[ERROR] {label}: ALL STRATEGIES FAILED – capturing diagnostics")
        # Save a timestamped page source AND screenshot under Log_files/diagnostics/
        # so successive failures don't overwrite each other (matches the helper
        # used in Momence_no_card_customers.py). Also log URL + page title for
        # quick context when reading the report later.
        try:
            from datetime import datetime as _dt
            stamp = _dt.now().strftime("%Y%m%d_%H%M%S")
            safe_label = (label or "report").lower().replace(" ", "_")
            try:
                os.makedirs(DIAGNOSTICS_DIR, exist_ok=True)
            except Exception:
                pass
            html_path = os.path.join(DIAGNOSTICS_DIR, f"no_button_{safe_label}_{stamp}.html")
            png_path  = os.path.join(DIAGNOSTICS_DIR, f"no_button_{safe_label}_{stamp}.png")
            try:
                with open(html_path, "w", encoding="utf-8") as fh:
                    fh.write(driver.page_source)
                print(f"[INFO] {label}: page source saved to {html_path}")
            except Exception as _e:
                print(f"[WARN] {label}: page source dump failed: {_e}")
            try:
                driver.save_screenshot(png_path)
                print(f"[INFO] {label}: screenshot saved to {png_path}")
            except Exception as _e:
                print(f"[WARN] {label}: screenshot failed: {_e}")
            try:
                print(f"[DIAG] {label}: current URL = {driver.current_url}")
                print(f"[DIAG] {label}: page title  = {driver.title}")
            except Exception:
                pass
            # Also keep the legacy single-file HTML for backwards compat
            try:
                with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as fh:
                    fh.write(driver.page_source)
            except Exception:
                pass
        except Exception:
            pass
        raise RuntimeError(f"{label}: could not find or click download button")

    print(f"[INFO] {label}: waiting 3s for download to start...")
    time.sleep(3)


# ============================================================
# 8.  CSV ARCHIVE HELPER
# ============================================================

def archive_file(src_path, label=""):
    """Move a downloaded CSV to the Archive folder after processing."""
    base = os.path.basename(src_path)
    dst  = os.path.join(ARCHIVE_DIR, base)
    try:
        os.replace(src_path, dst)
        print(f"[INFO] {label}: archived {base} → Archive/")
    except Exception as e:
        print(f"[WARN] {label}: could not archive {base}: {e}")


# ============================================================
# 9.  SNAPSHOT MASTER REPLACEMENT
#     Used by: Active Members, Upcoming Expirations, Non-member Customers,
#              Teacher Payroll (moved here 2026-05-17 after Momence changed the
#              report to per-teacher aggregate)
# ============================================================

def replace_master_snapshot(new_csv_path, master_file, label):
    """
    Replace the master CSV with the freshly downloaded file.
    Snapshot reports are point-in-time (no historical accumulation).
    The old master is overwritten; the download is archived.

    Logs column names to help verify dedup keys on first run.
    """
    print(f"[INFO] {label}: reading downloaded CSV: {new_csv_path}")
    try:
        df_new = pd.read_csv(new_csv_path)
    except Exception as e:
        print(f"[ERROR] {label}: could not read CSV: {e}")
        return 0

    log_columns(df_new, label)

    if len(df_new) == 0:
        print(f"[WARN] {label}: downloaded CSV is empty – master NOT replaced")
        archive_file(new_csv_path, label)
        return 0

    df_new.to_csv(master_file, index=False)
    print(f"[INFO] {label}: master replaced with {len(df_new)} rows → {master_file}")

    archive_file(new_csv_path, label)
    return len(df_new)


# ============================================================
# 10. ACCUMULATE + DEDUP HELPER
#     Used by: Cancellations, Intro Conversions, Occupancy
#              (Payroll moved to SNAPSHOT helper 2026-05-17)
# ============================================================

def append_and_dedupe_generic(new_csv_path, master_file, dedup_cols, label,
                               cleanup_fn=None):
    """
    Append a newly downloaded CSV to the master, deduplicate, and save.

    Args:
        new_csv_path: path to the freshly downloaded CSV
        master_file:  path to the master CSV (may not exist yet)
        dedup_cols:   list of column names to use as the dedup key.
                      If any column is missing the script logs a warning and
                      falls back to full-row deduplication.
        label:        report name for logging
        cleanup_fn:   optional function(df) -> df applied after concatenation
                      (for data-cleanup rules specific to a report)

    Returns:
        Number of net-new rows added to the master.
    """
    print(f"[INFO] {label}: reading downloaded CSV: {new_csv_path}")
    try:
        df_new = pd.read_csv(new_csv_path)
    except Exception as e:
        print(f"[ERROR] {label}: could not read CSV: {e}")
        return 0

    log_columns(df_new, label)

    # ── Verify dedup columns exist ───────────────────────────────────────────
    missing_cols = [c for c in dedup_cols if c not in df_new.columns]
    if missing_cols:
        print(f"[WARN] {label}: dedup columns {missing_cols} not found in download. "
              f"Available: {list(df_new.columns)}")
        print(f"[WARN] {label}: falling back to full-row deduplication")
        dedup_cols = None   # signal to use drop_duplicates() with no subset

    # ── Read existing master ─────────────────────────────────────────────────
    if os.path.exists(master_file):
        print(f"[INFO] {label}: reading master: {master_file}")
        try:
            df_master = pd.read_csv(master_file)
            print(f"[INFO] {label}: master has {len(df_master)} existing rows")
        except Exception as e:
            print(f"[WARN] {label}: could not read master ({e}); starting fresh")
            df_master = pd.DataFrame(columns=df_new.columns)
    else:
        print(f"[INFO] {label}: no master yet; will create one")
        df_master = pd.DataFrame(columns=df_new.columns)

    original_count = len(df_master)
    new_rows_count = len(df_new)

    # ── Build composite keys (or sentinel for full-row dedup) ────────────────
    if dedup_cols:
        master_keys = (
            df_master[dedup_cols].astype(str).agg("|".join, axis=1)
            if not df_master.empty
            else pd.Series([], dtype=str)
        )
        new_keys = (
            df_new[dedup_cols].astype(str).agg("|".join, axis=1)
            if not df_new.empty
            else pd.Series([], dtype=str)
        )
    else:
        # Full-row dedup — fingerprint each row by its whole tuple of values
        master_keys = df_master.astype(str).agg("|".join, axis=1) if not df_master.empty else pd.Series([], dtype=str)
        new_keys    = df_new.astype(str).agg("|".join, axis=1)    if not df_new.empty    else pd.Series([], dtype=str)

    master_keys_set = set(master_keys)

    # ── Accurate accounting (additive — no behaviour change) ─────────────────
    # truly_new            : rows in the download whose key is NOT in the
    #                        existing master (the real "new arrivals").
    # updates_dropped      : rows in the download whose key IS already in the
    #                        master. With keep="first" semantics the old master
    #                        row wins, so any payload change in the download
    #                        is silently discarded — this metric makes that
    #                        loss visible.
    # collapsed_in_master  : legacy duplicates in the master that the current
    #                        dedup key now collapses (the cause of "-99" /
    #                        "-25" deltas after the 2026-05-08 key tightening).
    truly_new       = int((~new_keys.isin(master_keys_set)).sum()) if new_rows_count else 0
    updates_dropped = new_rows_count - truly_new
    # collapsed_in_master = how many duplicate keys exist *within the master
    # alone* — i.e. would still be removed even if df_new were empty.
    collapsed_in_master = int(master_keys.duplicated().sum())

    # ── Concatenate ──────────────────────────────────────────────────────────
    combined = pd.concat([df_master, df_new], ignore_index=True)
    before   = len(combined)

    # ── Deduplicate ──────────────────────────────────────────────────────────
    if dedup_cols:
        # Build a composite string key for reliable deduplication
        combined["_dedup_key"] = combined[dedup_cols].astype(str).agg("|".join, axis=1)
        combined = combined.drop_duplicates(subset="_dedup_key", keep="first")
        combined = combined.drop(columns=["_dedup_key"])
    else:
        combined = combined.drop_duplicates(keep="first")

    after = len(combined)
    print(f"[INFO] {label}: rows before dedup: {before}, after: {after}, "
          f"removed: {before - after}")

    # ── Optional data cleanup ────────────────────────────────────────────────
    if cleanup_fn:
        combined = cleanup_fn(combined)

    # ── Save master ──────────────────────────────────────────────────────────
    combined.to_csv(master_file, index=False)
    print(f"[INFO] {label}: master saved ({len(combined)} rows) → {master_file}")

    archive_file(new_csv_path, label)

    added = after - original_count
    # The legacy "added" figure is the net change in master size and can go
    # negative when the dedup pass collapses legacy duplicates. The three
    # signals below explain WHY in any given run.
    print(
        f"[INFO] {label}: net master delta = {added} "
        f"(truly_new={truly_new}, updates_dropped={updates_dropped}, "
        f"collapsed_in_master={collapsed_in_master})"
    )
    if added < 0:
        print(
            f"[INFO] {label}: negative delta is the dedup pass cleaning up "
            f"{collapsed_in_master} legacy duplicate(s) in the master — not data loss."
        )
    if updates_dropped > 0:
        print(
            f"[INFO] {label}: {updates_dropped} download row(s) matched existing "
            f"master keys; payload differences (if any) were dropped because "
            f"the dedup keeps the first occurrence. If Momence edits rows in "
            f"place, switch keep='first' → keep='last' to let updates win."
        )
    return added


# ============================================================
# 11. REPORT-SPECIFIC FUNCTIONS
# ============================================================

# ── Report 1: Active Members with KPIs  (SNAPSHOT) ─────────────────────────

def run_active_members(driver):
    label = "Active Members"
    print(f"\n{'#'*60}")
    print(f"# REPORT: {label}")
    start_dt, end_dt = snapshot_date_range(label)
    url = build_date_url(ACTIVE_MEMBERS_BASE_URL, start_dt, end_dt)

    before_files = (set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv")))
                    | set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.zip"))))

    open_report_and_download(
        driver, url, label=label,
        prefer_button_text="Download summary",
        click_apply_filters=True,
        set_date_range=(start_dt, end_dt),
    )

    new_file = wait_for_new_download(before_files, label=label)
    if not new_file:
        raise RuntimeError(f"{label}: download timed out")

    rows = replace_master_snapshot(new_file, MASTER_ACTIVE_MEMBERS, label)
    return rows


# ── Report 2: Membership Cancellations  (ACCUMULATE) ───────────────────────

def run_membership_cancellations(driver):
    label = "Membership Cancellations"
    print(f"\n{'#'*60}")
    print(f"# REPORT: {label}")

    # Dedup key columns – verified 2026-05-08 against download + master headers.
    # Download columns: Customer Name, Customer Email, Membership, Cancelled at,
    # Reason, Possible improvements, Home location
    DEDUP_COLS = ["Customer Email", "Membership", "Cancelled at"]
    DATE_COL   = "Cancelled at"

    start_dt, end_dt = accumulating_date_range(
        MASTER_CANCELLATIONS, DATE_COL, CANCELLATIONS_INITIAL_START, label
    )
    url = build_date_url(CANCELLATIONS_BASE_URL, start_dt, end_dt)

    before_files = (set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv")))
                    | set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.zip"))))

    open_report_and_download(
        driver, url, label=label,
        prefer_button_text="Download summary",
        click_apply_filters=True,
        set_date_range=(start_dt, end_dt),
    )

    new_file = wait_for_new_download(before_files, label=label)
    if not new_file:
        raise RuntimeError(f"{label}: download timed out")

    added = append_and_dedupe_generic(
        new_file, MASTER_CANCELLATIONS, DEDUP_COLS, label
    )
    return added


# ── Report 3: Upcoming Membership Expirations  (SNAPSHOT) ──────────────────

def run_upcoming_expirations(driver):
    label = "Upcoming Expirations"
    print(f"\n{'#'*60}")
    print(f"# REPORT: {label}")
    start_dt, end_dt = snapshot_date_range(label)
    url = build_date_url(EXPIRATIONS_BASE_URL, start_dt, end_dt)

    before_files = (set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv")))
                    | set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.zip"))))

    open_report_and_download(
        driver, url, label=label,
        prefer_button_text="Download summary",
        click_apply_filters=True,
        set_date_range=(start_dt, end_dt),
    )

    new_file = wait_for_new_download(before_files, label=label)
    if not new_file:
        raise RuntimeError(f"{label}: download timed out")

    rows = replace_master_snapshot(new_file, MASTER_EXPIRATIONS, label)
    return rows


# ── Report 4: Non-member Customers  (SNAPSHOT) ─────────────────────────────

def run_non_member_customers(driver):
    label = "Non-member Customers"
    print(f"\n{'#'*60}")
    print(f"# REPORT: {label}")
    start_dt, end_dt = snapshot_date_range(label)
    url = build_date_url(NON_MEMBERS_BASE_URL, start_dt, end_dt)

    before_files = (set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv")))
                    | set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.zip"))))

    open_report_and_download(
        driver, url, label=label,
        prefer_button_text="Download summary",
        click_apply_filters=True,
        set_date_range=(start_dt, end_dt),
    )

    new_file = wait_for_new_download(before_files, label=label)
    if not new_file:
        raise RuntimeError(f"{label}: download timed out")

    rows = replace_master_snapshot(new_file, MASTER_NON_MEMBERS, label)
    return rows


# ── Report 5: Intro Offer Conversions  (ACCUMULATE) ────────────────────────

def run_intro_offer_conversions(driver):
    label = "Intro Offer Conversions"
    print(f"\n{'#'*60}")
    print(f"# REPORT: {label}")

    # Dedup key – verified 2026-05-08 against download + master headers.
    # Download columns: First name, Last name, E-mail, Intro offer, Converted to,
    # Paid, Tax, Purchase date, Expiration date, Class bookings, Appointment
    # bookings, All bookings, Home location
    DEDUP_COLS = ["E-mail", "Intro offer", "Purchase date"]
    DATE_COL   = "Purchase date"

    start_dt, end_dt = accumulating_date_range(
        MASTER_INTRO_CONVERSIONS, DATE_COL, INTRO_CONV_INITIAL_START, label
    )
    url = build_date_url(INTRO_CONV_BASE_URL, start_dt, end_dt)

    before_files = (set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv")))
                    | set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.zip"))))

    open_report_and_download(
        driver, url, label=label,
        prefer_button_text="Download summary",
        click_apply_filters=True,
        set_date_range=(start_dt, end_dt),
    )

    new_file = wait_for_new_download(before_files, label=label)
    if not new_file:
        raise RuntimeError(f"{label}: download timed out")

    added = append_and_dedupe_generic(
        new_file, MASTER_INTRO_CONVERSIONS, DEDUP_COLS, label
    )
    return added


# ── Report 6: Class Occupancy  (ACCUMULATE) ────────────────────────────────

def run_class_occupancy(driver):
    label = "Class Occupancy"
    print(f"\n{'#'*60}")
    print(f"# REPORT: {label}")

    # Dedup key – verified 2026-05-08 against download + master headers.
    # Download columns: Class Name, Date, Teacher Name, Location, Capacity,
    # Bookings, Check-Ins, No Shows, Late Cancellations, Occupancy %
    DEDUP_COLS = ["Class Name", "Date", "Teacher Name"]
    DATE_COL   = "Date"

    start_dt, end_dt = accumulating_date_range(
        MASTER_OCCUPANCY, DATE_COL, OCCUPANCY_INITIAL_START, label
    )
    url = build_date_url(OCCUPANCY_BASE_URL, start_dt, end_dt)

    before_files = (set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv")))
                    | set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.zip"))))

    open_report_and_download(
        driver, url, label=label,
        prefer_button_text="Download summary",
        click_apply_filters=True,
        set_date_range=(start_dt, end_dt),
    )

    new_file = wait_for_new_download(before_files, label=label)
    if not new_file:
        raise RuntimeError(f"{label}: download timed out")

    added = append_and_dedupe_generic(
        new_file, MASTER_OCCUPANCY, DEDUP_COLS, label
    )
    return added


# ── Report 7: Teacher Payroll (per teacher)  (SNAPSHOT) ────────────────────
#
# 2026-05-17: Momence changed this report from a per-class detail export to a
# per-teacher aggregate export.  New columns are:
#     Teacher First Name, Teacher Last Name, Teacher E-mail,
#     Average attendance, Total Bookings, Gross Revenue, Teacher Payout,
#     # of classes, Total time (h)
# There is no longer a Class Date or Class Name column, so the previous
# ACCUMULATE-with-per-class-dedup approach produced 'all rows new' on every
# run (because the per-teacher totals shift each day).  Converted to SNAPSHOT
# semantics matching Active Members / Upcoming Expirations: the master is
# fully REPLACED each run with the current-month totals.

def run_teacher_payroll(driver):
    label = "Teacher Payroll"
    print(f"\n{'#'*60}")
    print(f"# REPORT: {label}")

    start_dt, end_dt = snapshot_date_range(label)
    url = build_date_url(PAYROLL_BASE_URL, start_dt, end_dt)

    before_files = (set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv")))
                    | set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.zip"))))

    open_report_and_download(
        driver, url, label=label,
        prefer_button_text="Download summary",
        click_apply_filters=True,
        set_date_range=(start_dt, end_dt),
    )

    new_file = wait_for_new_download(before_files, label=label)
    if not new_file:
        raise RuntimeError(f"{label}: download timed out")

    rows = replace_master_snapshot(new_file, MASTER_PAYROLL, label)
    return rows


# ============================================================
# 12. MAIN
# ============================================================

def main():
    """
    Run all 7 new KPI reports in sequence.  Each report is wrapped in its
    own try/except so a failure in one does not block the others.
    Results are written to the shared Momence_batch_log.txt.
    """
    print(f"\n{'='*60}")
    print(f"  momence_new_reports.py  –  started {datetime.now()}")
    print(f"  DEBUG_MODE = {DEBUG_MODE}")
    print(f"{'='*60}\n")

    ensure_directories()
    append_to_batch_log("momence_new_reports.py started")

    driver = create_chrome_driver()
    try:
        load_cookies_if_available(driver)

        # ── Report 1: Active Members ─────────────────────────────────────────
        try:
            rows = run_active_members(driver)
            append_to_batch_log(f"Active Members: {rows} rows in snapshot master")
        except Exception as e:
            append_to_batch_log(f"EXCEPTION Active Members: {e}")
            append_to_batch_log(traceback.format_exc())

        # ── Report 2: Membership Cancellations ───────────────────────────────
        try:
            added = run_membership_cancellations(driver)
            append_to_batch_log(f"Membership Cancellations: {added} new rows added")
        except Exception as e:
            append_to_batch_log(f"EXCEPTION Membership Cancellations: {e}")
            append_to_batch_log(traceback.format_exc())

        # ── Report 3: Upcoming Expirations ───────────────────────────────────
        try:
            rows = run_upcoming_expirations(driver)
            append_to_batch_log(f"Upcoming Expirations: {rows} rows in snapshot master")
        except Exception as e:
            append_to_batch_log(f"EXCEPTION Upcoming Expirations: {e}")
            append_to_batch_log(traceback.format_exc())

        # ── Report 4: Non-member Customers ───────────────────────────────────
        try:
            rows = run_non_member_customers(driver)
            append_to_batch_log(f"Non-member Customers: {rows} rows in snapshot master")
        except Exception as e:
            append_to_batch_log(f"EXCEPTION Non-member Customers: {e}")
            append_to_batch_log(traceback.format_exc())

        # ── Report 5: Intro Offer Conversions ────────────────────────────────
        try:
            added = run_intro_offer_conversions(driver)
            append_to_batch_log(f"Intro Offer Conversions: {added} new rows added")
        except Exception as e:
            append_to_batch_log(f"EXCEPTION Intro Offer Conversions: {e}")
            append_to_batch_log(traceback.format_exc())

        # ── Report 6: Class Occupancy ─────────────────────────────────────────
        try:
            added = run_class_occupancy(driver)
            append_to_batch_log(f"Class Occupancy: {added} new rows added")
        except Exception as e:
            append_to_batch_log(f"EXCEPTION Class Occupancy: {e}")
            append_to_batch_log(traceback.format_exc())

        # ── Report 7: Teacher Payroll ─────────────────────────────────────────
        try:
            rows = run_teacher_payroll(driver)
            append_to_batch_log(f"Teacher Payroll: {rows} rows in snapshot master")
        except Exception as e:
            append_to_batch_log(f"EXCEPTION Teacher Payroll: {e}")
            append_to_batch_log(traceback.format_exc())

    finally:
        print(f"\n[INFO] Closing Chrome...")
        driver.quit()
        append_to_batch_log("momence_new_reports.py finished")
        print(f"\n{'='*60}")
        print(f"  Finished {datetime.now()}")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
