#!/usr/bin/env python3
"""
momence_waitlist_scrape.py
Momence Waitlist Scraper v1.0

Reads a list of Momence class numbers from the most recently modified
"momence_full_classes_*.csv" file, navigates to each class's session page,
and checks for a Waitlist tab with a count > 0.  For every such class it
clicks the Waitlist tab, extracts all waitlisted customers, and appends
the results to a single combined CSV file.

Classes where the Waitlist count is zero (or where the Waitlist tab is
absent entirely) are skipped without navigating further, making the run
significantly faster than scraping every class.

Overview of execution
---------------------
1. Find the newest momence_full_classes_*.csv file in the working directory.
2. Skip the run if the log file already contains a "WAITLIST SCRAPE COMPLETE"
   entry for that file (prevents reprocessing in repeated batch runs).
3. Launch Chrome and authenticate using saved session cookies.
4. Resume from checkpoint if waitlist_checkpoint.json exists for the same
   input file.
5. For each class in the input file:
   a. Navigate to https://momence.com/dashboard/32083/sessions/<class_number>
   b. Look for a "Waitlist" tab button.  Read its count badge.
   c. If count == 0 or tab is absent: log "no waitlist" and move on.
   d. If count > 0: click the Waitlist tab, wait for entries to render, then
      parse the page source with BeautifulSoup to extract:
        - Person Name
        - Email (if shown in the row; blank otherwise)
        - Time of Signup
        - Payment Line 1  (first line of payment details)
        - Payment Line 2  (second line of payment details, if present)
   e. Append one row per waitlisted person to Momence_waitlist_combined.csv.
   f. Save a checkpoint after each class so the run can resume if interrupted.
   g. Periodically clear the browser cache to manage memory.
6. Log a completion summary to both the run log and the shared batch log.

Authentication
--------------
Cookie-based — uses momence_cookies.pkl (same file as momence_class_customers_scrape_4.py).
Created by running momence_first_login_setup.py and logging in once manually.
If cookies are missing or expired the script prompts for a manual login at
the console, then saves the new cookies before continuing.

CSS selector note
-----------------
Waitlist rows are expected to use the same styled-component class patterns as
the Signups tab:
  div[class*='sc-1ovdf80-7']   — row container
  span[class*='sc-1ta22rh-0']  — person name
  div[class*='sc-13fi9me-0']   — payment tag(s)

Email may appear as:
  a[href^='mailto:']           — clickable mailto link within the row
  span / div containing '@'    — plain text email element

These are auto-generated styled-component class names and may change when
Momence redeploys.  If no entries are being captured, open:
  Log_files/debug_waitlist_page_source.html
and inspect the element structure to find the updated class names.

Input files
-----------
momence_full_classes_<YYYY MM DD HH MM>.csv   (most recently modified)
    The primary input.  Must have at minimum "Class Number" and "Class Name"
    columns (or underscore variants "Class_Number" / "Class_Name").
    Produced by extract_full_classes2.py earlier in the batch chain.
    Location: same directory as this script.

momence_cookies.pkl
    Serialised browser session cookies.  Shared with
    momence_class_customers_scrape_4.py.
    Location: same directory as this script (Config.COOKIES_FILE).

waitlist_checkpoint.json
    JSON checkpoint written after each successfully processed class.
    Allows the scraper to resume from where it left off after a crash.
    Contains: filename, last_class_idx, last_class_number, last_class_name,
    timestamp.
    Location: same directory as this script.

Output files
------------
Momence_waitlist_combined.csv
    The primary output.  Opened in append mode so multiple runs accumulate
    data.  One row per waitlisted person.
    Columns:
      Class Number   — Momence session/class ID.
      Class Name     — Human-readable class name from the input file.
      Capture Date   — Date this script ran (YYYY-MM-DD).
      Person Name    — Full name of the waitlisted customer.
      Email          — Email address (blank if not exposed in the list view).
      Time of Signup — Time the customer joined the waitlist.
      Payment Line 1 — First line of the payment details shown on the row.
      Payment Line 2 — Second line of payment details (blank if only one line).
    Location: same directory as this script.

Log / operational files
-----------------------
Log_files/Momence_waitlist_log.txt
    Append-only run log.  Every call to log_message() / log_error() writes
    a timestamped line here.  Also holds the "WAITLIST SCRAPE COMPLETE:
    <filename>" sentinel that prevents reprocessing on re-run.

Log_files/Momence_batch_log.txt    (Config.BATCH_LOG_FILE)
    Shared batch-chain log.  This script appends start, completion, and
    error messages.

Log_files/debug_waitlist_page_source.html
    Full HTML source of the first class page that returned zero waitlist
    entries after all retries (written at most once per run).  Use this to
    inspect the DOM and update CSS selectors if Momence has redeployed.

waitlist_checkpoint.json
    See "Input files" above — read at startup, written after each class.

All paths are relative to the working directory:
    C:\\Users\\markj\\OneDrive - MFPL\\Documents\\Customer Projects\\Ritual\\Momence_data\\

Dependencies
------------
config.py — configuration constants shared with the scraper suite.
  Key values used:
    DASHBOARD_URL         https://momence.com/dashboard/32083
    LOGIN_URL             https://momence.com/login
    BATCH_LOG_FILE        Log_files/Momence_batch_log.txt
    COOKIES_FILE          momence_cookies.pkl
    MAX_MEMORY_PERCENT    80
    CACHE_CLEAR_INTERVAL  10
    MAX_RETRIES           3
    RETRY_DELAYS          [5, 10, 20]
    STATUS_INTERVAL       300
    HEARTBEAT_INTERVAL    300
"""

import os
import sys
import glob
import csv
import re
import json
import pickle
import time
import traceback
import psutil
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime, date

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, StaleElementReferenceException, NoSuchElementException
)
from bs4 import BeautifulSoup

import config
Config = config  # Alias for readability throughout the script.

# ── script-level constants ────────────────────────────────────────────────────

# Log file for this script only (separate from the customers scraper log).
LOG_FILE = 'Log_files/Momence_waitlist_log.txt'

# Checkpoint file for this script (separate from the customers scraper checkpoint).
CHECKPOINT_FILE = 'waitlist_checkpoint.json'

# Output CSV that accumulates all waitlist rows across runs.
OUTPUT_FILE = 'Momence_waitlist_combined.csv'

# Output CSV columns — written as the header and used by csv.DictWriter.
OUTPUT_FIELDS = [
    "Class Number",
    "Class Name",
    "Capture Date",
    "Position",
    "Person Name",
    "Email",
    "Time of Signup",
    "Payment Line 1",
    "Payment Line 2",
]

# Date this run started — written to every output row as "Capture Date".
CAPTURE_DATE = date.today().isoformat()  # YYYY-MM-DD


# ══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════════════════════════

def log_message(msg: str) -> None:
    """
    Write a message to stdout and append it to the waitlist run log.

    Log file: Log_files/Momence_waitlist_log.txt  (LOG_FILE)
    Format:   <ISO timestamp> <msg>
    Mode:     Append.

    Args:
        msg: Message text to log.
    """
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode(sys.stdout.encoding or "utf-8", errors="replace")
                 .decode(sys.stdout.encoding or "utf-8"))
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as lf:
            lf.write(f"{datetime.now().isoformat()} {msg}\n")
    except OSError as e:
        print(f"Failed to write to log file: {e}")


def log_error(msg: str, exc_info: Optional[Exception] = None) -> None:
    """
    Write an error (with optional traceback and browser state) to log and stdout.

    Log file: Log_files/Momence_waitlist_log.txt  (LOG_FILE)

    Args:
        msg:      Short description of the error.
        exc_info: Optional exception; full traceback is appended if provided.
    """
    parts = [f"ERROR: {msg}"]
    if exc_info:
        parts.append("Exception details:")
        parts.append(traceback.format_exc())
    try:
        if 'driver' in globals():
            parts.append(f"\nBrowser URL at error: {driver.current_url}")
    except Exception:
        pass
    full_msg = "\n".join(parts)
    try:
        print(full_msg)
    except UnicodeEncodeError:
        print(full_msg.encode(sys.stdout.encoding or "utf-8", errors="replace")
                      .decode(sys.stdout.encoding or "utf-8"))
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as lf:
            lf.write(f"{datetime.now().isoformat()} {full_msg}\n")
    except OSError as e:
        print(f"Failed to write to log file: {e}")


def append_to_batch_log(message: str) -> None:
    """
    Append a timestamped message to the shared batch chain log.

    Log file: Log_files/Momence_batch_log.txt  (Config.BATCH_LOG_FILE)

    Args:
        message: Status message to append.
    """
    try:
        with open(Config.BATCH_LOG_FILE, 'a', encoding='utf-8') as bf:
            bf.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# STATUS TRACKING
# ══════════════════════════════════════════════════════════════════════════════

class ScraperStatus:
    """
    Tracks run progress and generates periodic status reports.

    Attributes
    ----------
    start_time        : datetime  — when the run started.
    processed_classes : int       — total classes visited (including skipped).
    waitlisted_classes: int       — classes that had a waitlist count > 0.
    skipped_classes   : int       — classes skipped because waitlist count == 0.
    total_entries     : int       — cumulative waitlist rows written.
    processing_times  : list      — wall-clock seconds per class.
    memory_readings   : list      — Chrome memory % per class.
    errors            : list      — ring buffer of last 100 error dicts.
    auth_failures     : int       — count of /sign-in redirects detected.
    """

    def __init__(self):
        self.start_time = datetime.now()
        self.last_status_time = self.start_time
        self.last_heartbeat = self.start_time
        self.processed_classes = 0
        self.waitlisted_classes = 0
        self.skipped_classes = 0
        self.total_entries = 0
        self.processing_times: List[float] = []
        self.memory_readings: List[float] = []
        self.errors: List[Dict[str, Any]] = []
        self.auth_failures = 0

    def record_auth_failure(self) -> None:
        """Increment the auth failure counter."""
        self.auth_failures += 1

    def log_error(self, msg: str, details: Optional[Exception] = None) -> None:
        """Add an error to the internal ring buffer (capped at 100 entries)."""
        self.errors.append({
            'timestamp': datetime.now(),
            'message': msg,
            'details': str(details) if details else None,
        })
        if len(self.errors) > 100:
            self.errors.pop(0)

    def maybe_send_heartbeat(self) -> None:
        """Write a heartbeat log line if Config.HEARTBEAT_INTERVAL seconds have passed."""
        now = datetime.now()
        if (now - self.last_heartbeat).seconds >= Config.HEARTBEAT_INTERVAL:
            log_message("HEARTBEAT: Waitlist scraper still running")
            self.last_heartbeat = now

    def log_status(self, force: bool = False) -> None:
        """
        Write a status report if Config.STATUS_INTERVAL seconds have elapsed
        (or immediately if force=True).
        """
        now = datetime.now()
        if force or (now - self.last_status_time).seconds >= Config.STATUS_INTERVAL:
            duration = now - self.start_time
            hours = max(duration.total_seconds() / 3600, 0.0001)
            msg = (
                f"\nStatus Report — {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"  Runtime       : {duration}\n"
                f"  Classes visited : {self.processed_classes} "
                f"({self.waitlisted_classes} with waitlist, "
                f"{self.skipped_classes} skipped)\n"
                f"  Waitlist entries written: {self.total_entries}\n"
                f"  Throughput    : {self.processed_classes / hours:.1f} classes/hour\n"
                f"  Avg memory    : "
                f"{sum(self.memory_readings[-10:]) / max(len(self.memory_readings[-10:]), 1):.1f}%\n"
                f"  Auth failures : {self.auth_failures}\n"
                f"  Errors        : {len(self.errors)}\n"
            )
            log_message(msg)
            self.last_status_time = now


# ══════════════════════════════════════════════════════════════════════════════
# BROWSER MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

class BrowserManager:
    """
    Chrome browser lifecycle: creation, authentication, memory management,
    and recovery.  All methods are static/class methods — no instance needed.
    """

    @staticmethod
    def create_browser() -> webdriver.Chrome:
        """
        Create and return a new Chrome WebDriver.

        Flags:
          --disable-gpu            Prevents GPU crashes in VM/headless environments.
          --no-sandbox             Required on some Windows setups.
          --disable-dev-shm-usage  Prevents /dev/shm exhaustion on Linux VMs.
          --disable-extensions     Keeps the browser clean.
        """
        options = webdriver.ChromeOptions()
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-extensions')
        # Uncomment to run headless once selectors are confirmed working:
        # options.add_argument('--headless=new')
        return webdriver.Chrome(options=options)

    @staticmethod
    def load_cookies(driver: webdriver.Chrome) -> bool:
        """
        Inject saved session cookies and verify the dashboard is accessible.

        Input file read: momence_cookies.pkl  (Config.COOKIES_FILE)

        Steps:
          1. Navigate to Config.LOGIN_URL (sets correct cookie domain).
          2. Load cookies from Config.COOKIES_FILE; strip sameSite / expiry.
          3. Navigate to Config.DASHBOARD_URL.
          4. Return False if redirected to /sign-in.

        Returns:
            True if authentication verified, False otherwise.
        """
        try:
            driver.get(Config.LOGIN_URL)
            if not os.path.exists(Config.COOKIES_FILE):
                return False
            with open(Config.COOKIES_FILE, 'rb') as f:
                cookies = pickle.load(f)
            for cookie in cookies:
                cookie.pop('sameSite', None)
                cookie.pop('expiry', None)
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    log_error(f"Could not add cookie '{cookie.get('name')}': {e}")
            driver.get(Config.DASHBOARD_URL)
            time.sleep(2)
            if '/sign-in' in driver.current_url or 'login' in driver.current_url:
                return False
            return True
        except Exception as e:
            log_error("Failed to load cookies", exc_info=e)
            return False

    @staticmethod
    def save_cookies(driver: webdriver.Chrome) -> None:
        """
        Serialise current browser cookies to Config.COOKIES_FILE.

        Output file written: momence_cookies.pkl  (Config.COOKIES_FILE)
        """
        try:
            with open(Config.COOKIES_FILE, 'wb') as f:
                pickle.dump(driver.get_cookies(), f)
            log_message("Saved new cookies to file.")
        except Exception as e:
            log_error("Failed to save cookies", exc_info=e)

    @staticmethod
    def check_memory(driver: webdriver.Chrome) -> float:
        """Return Chrome process memory as % of total system RAM (0.0 on failure)."""
        try:
            return psutil.Process(driver.service.process.pid).memory_percent()
        except Exception:
            return 0.0

    @staticmethod
    def clear_cache(driver: webdriver.Chrome) -> None:
        """Clear browser localStorage and sessionStorage to manage memory growth."""
        try:
            driver.execute_script("window.localStorage.clear();")
            driver.execute_script("window.sessionStorage.clear();")
            driver.delete_all_cookies()
        except Exception as e:
            log_error("Failed to clear browser cache", exc_info=e)

    @classmethod
    def restart_browser(cls, old_driver: webdriver.Chrome) -> Tuple[Optional[webdriver.Chrome], bool]:
        """
        Quit the old browser, start a fresh one, and restore authentication.

        Called when Chrome memory exceeds Config.MAX_MEMORY_PERCENT.

        Returns:
            (new_driver, success) — new_driver is None if creation failed.
        """
        try:
            old_driver.quit()
        except Exception:
            pass
        try:
            new_driver = cls.create_browser()
            success = cls.load_cookies(new_driver)
            if success:
                log_message("Browser restarted successfully.")
            return new_driver, success
        except Exception as e:
            log_error("Failed to restart browser", exc_info=e)
            return None, False

    @classmethod
    def handle_auth_failure(cls, driver: webdriver.Chrome, status: ScraperStatus) -> bool:
        """
        Attempt to recover from a /sign-in redirect detected mid-run.

        Steps:
          1. Record the failure in status.
          2. Try reloading cookies from disk.
          3. If that fails, prompt for manual login, save new cookies, retry.

        Returns:
            True if authentication restored, False otherwise.
        """
        status.record_auth_failure()
        log_message("Auth failure detected — attempting recovery.")
        if cls.load_cookies(driver):
            return True
        log_message("Cookie reload failed.  Please log in manually...")
        input("Press Enter after logging in to continue...")
        cls.save_cookies(driver)
        return cls.load_cookies(driver)


# ══════════════════════════════════════════════════════════════════════════════
# WAITLIST DETECTION & EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

class WaitlistExtractor:
    """
    Detects and extracts waitlist data from a Momence class session page.

    The session page has a tab row: Signups | Checked in | Cancelled | Waitlist
    Each tab shows a count badge.  This class:
      1. Reads the Waitlist badge count without clicking the tab (fast check).
      2. If count > 0, clicks the tab and parses the rendered HTML.
      3. Extracts per-person: name, email, time of signup, payment (2 lines).

    Confirmed DOM structure (from debug_waitlist_page_source.html, 2026-03-13):

      Tab bar buttons — each tab is a <button class="mwhi97-0 ...">
        Count badge inside tab : div[class*='sc-1gjzzge-0']  (text = the number)
        Waitlist tab icon      : i[name="waitlist_outline_20"]
        Signups tab icon       : i[name="users_3_outline_20"]

      Table  — role="table" aria-label="table of entities"
        Header row  — role="row"
          Columns (role="columnheader"):
            [0] drag handle (empty)
            [1] "Customer name"
            [2] "E-mail"
            [3] "Time of signup"
            [4] "Payment"
            [5] status icons (empty header)
            [6] actions (empty header)

        Data rows — div[class*='sc-1ovdf80-7'] with role="button"
                    and data-rbd-draggable-id="<customer_id>"
          Each row has cells with role="cell":
            cells[1]  name          plain text, e.g. "DANI RADLEY"
            cells[2]  email         plain text, e.g. "dradl2@eq.edu.au"
            cells[3]  time of signup  <i name="calendar_outline_20"> + text
                                    e.g. "Sun, 8 Mar 2026 21:59"
            cells[4]  payment       div[class*='sc-1pvjkb7-1'] container
                                      first child div  = line 1 e.g. "Package deal"
                                      div[class*='sc-1pvjkb7-2'] = line 2 e.g. "4x reformer session"

    CSS selectors are auto-generated styled-component names and may change on
    redeploy.  If extraction stops working, open:
      Log_files/debug_waitlist_page_source.html
    and search for a known customer name to identify the updated class names.
    """

    # Written at most once per run to avoid flooding the disk.
    _debug_dumped = False

    @staticmethod
    def get_waitlist_count(driver: webdriver.Chrome) -> int:
        """
        Read the Waitlist tab badge count without clicking the tab.

        Waits up to 15 s for the Signups tab to appear (confirming the tab bar
        has rendered) before looking for the Waitlist button.  This prevents
        false-zero reads caused by calling the function before the React tab bar
        has mounted — which was the cause of some classes being wrongly skipped.

        The Waitlist button text is structured as:
            "Waitlist\\n<count>"  (icon div + label div with nested badge div)
        re.findall(r'\\d+', text) extracts all digit sequences; the last one is
        the count badge (the first digit sequence, if any, belongs to the icon
        or label and is not a count).

        Returns:
            int: the waitlist count, or 0 if the tab is absent or count is 0.
        """
        try:
            # Wait for the tab bar to render by waiting for the Signups button.
            # This ensures the Waitlist button (if present) is also in the DOM.
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[contains(.,'Signups')]")
                )
            )
        except TimeoutException:
            # Tab bar never appeared — page may not have loaded properly.
            return 0

        try:
            btns = driver.find_elements(By.XPATH, "//button[contains(.,'Waitlist')]")
            for btn in btns:
                text = btn.text.strip()
                # Extract all digit sequences; the count badge is the last one.
                numbers = re.findall(r'\d+', text)
                if numbers:
                    return int(numbers[-1])
                # Waitlist button found but no digit — count is 0.
                return 0
        except Exception:
            pass
        return 0  # No Waitlist tab present on this page.

    @staticmethod
    def click_waitlist_tab(driver: webdriver.Chrome) -> bool:
        """
        Click the Waitlist tab button and wait for the list to render.

        Waits up to 10 s for the button to be clickable, clicks it, then
        waits 3 s for the React component to re-render the list.

        Returns:
            True if the tab was clicked, False if it could not be found/clicked.
        """
        try:
            btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Waitlist')]"))
            )
            btn.click()
            time.sleep(3)  # Allow React to render the waitlist entries.
            return True
        except Exception as e:
            log_error("Could not click Waitlist tab", exc_info=e)
            return False

    @classmethod
    def get_waitlist_entries(cls, driver: webdriver.Chrome,
                             max_retries: int = 3) -> List[Dict[str, str]]:
        """
        Click the Waitlist tab and extract all waitlisted persons from the page.

        Strategy:
          1. Click the Waitlist tab (already verified to have count > 0).
          2. Wait for row containers (div[class*='sc-1ovdf80-7']) to appear.
          3. Capture a static page source snapshot and parse with BeautifulSoup.
             Parsing from snapshot avoids StaleElementReferenceException.
          4. If zero entries found, refresh and retry up to max_retries times.
          5. On final failure, save debug HTML once per run.

        Args:
            driver:      Chrome WebDriver on the class session page.
            max_retries: Maximum attempts before giving up (default 3).

        Returns:
            list[dict]: Each dict has keys:
              'name', 'email', 'time_of_signup', 'payment_line_1', 'payment_line_2'
        """
        entries = []
        retry_count = 0

        while retry_count < max_retries:
            try:
                if not cls.click_waitlist_tab(driver):
                    return []

                # Wait for row containers — TimeoutException is tolerated because
                # the wait count may drop to 0 between the badge check and tab click.
                try:
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_all_elements_located(
                            (By.CSS_SELECTOR, "div[class*='sc-1ovdf80-7']")
                        )
                    )
                    time.sleep(1)  # Extra moment for React to finish rendering.
                except TimeoutException:
                    pass

                entries = cls._parse_waitlist_source(driver.page_source)
                if entries:
                    return entries

                # No entries despite count > 0 — retry after back-off.
                retry_count += 1
                if retry_count < max_retries:
                    log_message(f"No waitlist entries found (attempt {retry_count}), retrying...")
                    time.sleep(retry_count * 2)
                    driver.refresh()

            except Exception as e:
                log_error(f"Error extracting waitlist (attempt {retry_count + 1})", exc_info=e)
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(retry_count * 2)
                    driver.refresh()

        # All retries exhausted — save debug HTML once to help fix selectors.
        if not entries and not cls._debug_dumped:
            cls._debug_dumped = True
            try:
                os.makedirs('Log_files', exist_ok=True)
                with open('Log_files/debug_waitlist_page_source.html', 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                log_message("Saved debug HTML to Log_files/debug_waitlist_page_source.html")
            except Exception:
                pass

        return entries

    @staticmethod
    def _parse_waitlist_source(page_source: str) -> List[Dict[str, str]]:
        """
        Parse waitlist entries from a static HTML snapshot of the session page.

        Uses BeautifulSoup to avoid StaleElementReferenceException.

        Confirmed column layout (role="cell" divs within each row, 0-indexed):
          cells[0]  position       the waitlist queue number shown in the left
                                   column (e.g. "1", "2").  get_text() returns
                                   this digit; falls back to loop index if empty.
          cells[1]  name           plain text, e.g. "DANI RADLEY"
          cells[2]  email          plain text, e.g. "dradl2@eq.edu.au"
          cells[3]  time of signup <i name="calendar_outline_20"> + text node
                                   e.g. "Sun, 8 Mar 2026 21:59"
                                   The <i> tag is empty so get_text() returns
                                   only the date/time text node.
          cells[4]  payment        contains div[class*='sc-1pvjkb7-1']:
                                     first child div  = Payment Line 1
                                                        e.g. "Package deal"
                                     div[class*='sc-1pvjkb7-2'] = Payment Line 2
                                                        e.g. "4x reformer session"

        Row selector: div[class*='sc-1ovdf80-7'] with role="button" and
        data-rbd-draggable-id attribute (React drag-and-drop row).
        Rows with fewer than 3 cells are skipped (header artefacts, empty rows).

        Args:
            page_source: Full HTML string captured after the Waitlist tab has
                         been clicked and the list has rendered.

        Returns:
            list[dict]: Each dict has:
              'position'       — str: "1", "2", … (or loop index if cell is blank)
              'name'           — str
              'email'          — str (blank if cell is empty)
              'time_of_signup' — str (blank if cell is empty)
              'payment_line_1' — str (blank if payment cell is absent/empty)
              'payment_line_2' — str (blank if only one payment line)
        """
        entries = []
        soup = BeautifulSoup(page_source, 'html.parser')

        # Row containers: div[class*='sc-1ovdf80-7'] — confirmed present in debug HTML.
        # These are the individual customer rows rendered by the React drag-and-drop list.
        rows = soup.select("div[class*='sc-1ovdf80-7']")

        for row_idx, row in enumerate(rows, start=1):
            # Collect all role="cell" divs within this row in document order.
            # This matches the confirmed column layout above.
            cells = row.find_all('div', attrs={'role': 'cell'})

            # Need at least 3 cells (position + name + email) to be a valid row.
            if len(cells) < 3:
                continue

            # ── Position (cells[0]) ───────────────────────────────────────────
            # The left-most cell shows the waitlist queue number (1, 2, …).
            # Fall back to the loop index if the cell text is not a digit
            # (e.g. if Momence renders only an icon in this cell).
            position_text = cells[0].get_text(strip=True)
            position = position_text if position_text.isdigit() else str(row_idx)

            # ── Name (cells[1]) ───────────────────────────────────────────────
            name = cells[1].get_text(strip=True)
            if not name:
                continue  # Skip rows with no identifiable person name.

            # ── Email (cells[2]) ──────────────────────────────────────────────
            email = cells[2].get_text(strip=True) if len(cells) > 2 else ''

            # ── Time of Signup (cells[3]) ─────────────────────────────────────
            # The cell contains an empty <i> calendar icon followed by a text
            # node with the date/time string.  get_text(strip=True) returns
            # only the text node because the <i> tag has no text content.
            time_of_signup = cells[3].get_text(strip=True) if len(cells) > 3 else ''

            # ── Payment (cells[4]) ────────────────────────────────────────────
            # Structure inside the payment cell:
            #   div[class*='sc-1pvjkb7-1']          outer payment container
            #     <div>Package deal</div>             Payment Line 1 (first child)
            #     div[class*='sc-1pvjkb7-2']         Payment Line 2
            payment_line_1 = ''
            payment_line_2 = ''

            if len(cells) > 4:
                pay_cell = cells[4]
                pay_container = pay_cell.select_one("[class*='sc-1pvjkb7-1']")
                if pay_container:
                    # First direct-child div = Payment Line 1 (e.g. "Package deal").
                    child_divs = pay_container.find_all('div', recursive=False)
                    if child_divs:
                        payment_line_1 = child_divs[0].get_text(strip=True)
                    # Payment Line 2 is in the nested div with class sc-1pvjkb7-2.
                    line2_elem = pay_container.select_one("[class*='sc-1pvjkb7-2']")
                    if line2_elem:
                        payment_line_2 = line2_elem.get_text(strip=True)
                else:
                    # Fallback: no sc-1pvjkb7-1 container found — get all cell text
                    # and split on the first newline.
                    raw = pay_cell.get_text(separator='\n', strip=True)
                    parts = [p.strip() for p in raw.split('\n') if p.strip()]
                    payment_line_1 = parts[0] if parts else ''
                    payment_line_2 = parts[1] if len(parts) > 1 else ''

            entries.append({
                'position': position,
                'name': name,
                'email': email,
                'time_of_signup': time_of_signup,
                'payment_line_1': payment_line_1,
                'payment_line_2': payment_line_2,
            })

        return entries


# ══════════════════════════════════════════════════════════════════════════════
# CLASS PROCESSING
# ══════════════════════════════════════════════════════════════════════════════

def process_class(driver: webdriver.Chrome, class_info: Dict[str, Any],
                  writer: csv.DictWriter, status: ScraperStatus) -> Tuple[int, bool]:
    """
    Visit a single class session page and write any waitlist rows to the output CSV.

    URL pattern: https://momence.com/dashboard/32083/sessions/<class_number>

    Steps:
      1. Navigate to the session URL; detect /sign-in redirects.
      2. Read the Waitlist badge count (WaitlistExtractor.get_waitlist_count).
         If count == 0, return immediately (skipped = True).
      3. Extract all waitlist entries (WaitlistExtractor.get_waitlist_entries).
      4. Write one CSV row per entry.

    Output written to (via writer):
        Momence_waitlist_combined.csv
        Columns: Class Number, Class Name, Capture Date, Person Name, Email,
                 Time of Signup, Payment Line 1, Payment Line 2

    Args:
        driver:     Active Chrome WebDriver.
        class_info: Dict with 'number' and 'name' keys from the input CSV.
        writer:     csv.DictWriter open on Momence_waitlist_combined.csv.
        status:     ScraperStatus for auth failure tracking.

    Returns:
        (entry_count, skipped)
          entry_count — rows written (0 if skipped or empty waitlist).
          skipped     — True if the class had no waitlist and was not scraped.
    """
    class_number = class_info['number']
    url = f"{Config.DASHBOARD_URL}/sessions/{class_number}"

    start_time = time.time()
    driver.get(url)
    time.sleep(1)  # Brief pause to avoid hammering the server.

    # Detect auth expiry — Momence redirects to /sign-in on session timeout.
    if '/sign-in' in driver.current_url or 'login' in driver.current_url:
        if not BrowserManager.handle_auth_failure(driver, status):
            raise Exception("Authentication recovery failed")
        driver.get(url)
        time.sleep(1)

    # ── Fast check: read waitlist count before clicking anything ──────────────
    # Avoids the overhead of clicking the tab and parsing the DOM for the
    # majority of classes that have no waitlist.
    waitlist_count = WaitlistExtractor.get_waitlist_count(driver)
    if waitlist_count == 0:
        status.skipped_classes += 1
        return 0, True  # Skipped — no waitlist.

    log_message(
        f"  Waitlist count = {waitlist_count} — extracting entries..."
    )
    status.waitlisted_classes += 1

    # ── Extract waitlist entries ──────────────────────────────────────────────
    entries = WaitlistExtractor.get_waitlist_entries(driver)
    entry_count = 0

    for entry in entries:
        writer.writerow({
            "Class Number":   class_number,
            "Class Name":     class_info['name'],
            "Capture Date":   CAPTURE_DATE,
            "Position":       entry['position'],
            "Person Name":    entry['name'],
            "Email":          entry['email'],
            "Time of Signup": entry['time_of_signup'],
            "Payment Line 1": entry['payment_line_1'],
            "Payment Line 2": entry['payment_line_2'],
        })
        entry_count += 1

    status.total_entries += entry_count
    status.processing_times.append(time.time() - start_time)
    return entry_count, False


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    """
    Orchestrate the full waitlist scrape run.

    Execution flow
    --------------
    1. Find the newest momence_full_classes_*.csv input file.
    2. Skip if LOG_FILE already holds "WAITLIST SCRAPE COMPLETE: <filename>".
    3. Launch Chrome; authenticate via cookies (prompt manual login if needed).
    4. Load waitlist_checkpoint.json to resume a previous partial run.
    5. Open Momence_waitlist_combined.csv in append mode (write header if new).
    6. Iterate over classes from start_idx:
         a. Check heartbeat / status intervals.
         b. Check Chrome memory; restart browser if above Config.MAX_MEMORY_PERCENT.
         c. Call process_class() with up to Config.MAX_RETRIES retries and
            exponential back-off (Config.RETRY_DELAYS).
         d. On success: save checkpoint to waitlist_checkpoint.json.
         e. Every Config.CACHE_CLEAR_INTERVAL classes: clear browser cache.
    7. Write final status and "WAITLIST SCRAPE COMPLETE" sentinel to log.

    Input files read:
        momence_full_classes_<YYYY MM DD HH MM>.csv  — class list (most recent).
        momence_cookies.pkl                          — session cookies.
        waitlist_checkpoint.json                     — resume index (if exists).

    Output files written:
        Momence_waitlist_combined.csv    — waitlist rows (append mode).
        waitlist_checkpoint.json         — updated after each class.
        Log_files/Momence_waitlist_log.txt   — run log (append mode).
        Log_files/Momence_batch_log.txt      — batch chain log (append mode).
    """
    global driver

    os.makedirs('Log_files', exist_ok=True)
    status = ScraperStatus()
    append_to_batch_log("Waitlist scraper started")
    log_message(f"[INFO] Starting Momence waitlist scrape — {datetime.now()}")
    log_message(f"[INFO] Capture date: {CAPTURE_DATE}")

    try:
        # ── Step 1: Find input file ───────────────────────────────────────────
        files = glob.glob("momence_full_classes_*.csv")
        if not files:
            log_message("No momence_full_classes_*.csv files found — nothing to do.")
            append_to_batch_log("Waitlist scrape concluded — no input file.")
            return

        latest_file = max(files, key=os.path.getmtime)
        filename_only = os.path.basename(latest_file)
        log_message(f"[INFO] Input file: {latest_file}")

        # ── Step 2: Skip if already processed ────────────────────────────────
        sentinel = f"WAITLIST SCRAPE COMPLETE: {filename_only}"
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r', encoding='utf-8') as lf:
                if any(sentinel in line for line in lf):
                    log_message(f"[INFO] Already processed {filename_only} — skipping.")
                    append_to_batch_log("Waitlist scrape concluded — already processed.")
                    return

        # ── Step 3: Launch browser and authenticate ───────────────────────────
        driver = BrowserManager.create_browser()
        if not BrowserManager.load_cookies(driver):
            log_message("Cookies missing or expired.  Please log in manually...")
            input("Press Enter after logging in...")
            BrowserManager.save_cookies(driver)

        # ── Step 4: Read class list from input CSV ────────────────────────────
        class_info_list = []
        with open(latest_file, encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                number = row.get("Class Number") or row.get("Class_Number") or ""
                name   = row.get("Class Name")   or row.get("Class_Name")   or ""
                if number:
                    class_info_list.append({'number': number, 'name': name})

        if not class_info_list:
            log_message("No classes found in input file — nothing to do.")
            append_to_batch_log("Waitlist scrape concluded — empty input file.")
            return

        log_message(f"[INFO] {len(class_info_list)} classes to process.")

        # ── Step 5: Load checkpoint ───────────────────────────────────────────
        # waitlist_checkpoint.json records the last successfully processed
        # class index so a crashed run resumes instead of restarting.
        start_idx = 0
        if os.path.exists(CHECKPOINT_FILE):
            try:
                with open(CHECKPOINT_FILE, 'r') as f:
                    checkpoint = json.load(f)
                if checkpoint.get('filename') == filename_only:
                    start_idx = checkpoint['last_class_idx']
                    log_message(f"[INFO] Resuming from checkpoint: class index {start_idx + 1}")
            except Exception as e:
                log_error("Could not load checkpoint — starting from beginning.", exc_info=e)

        # ── Step 6: Open output CSV and iterate ──────────────────────────────
        file_is_new = not os.path.exists(OUTPUT_FILE) or os.path.getsize(OUTPUT_FILE) == 0

        with open(OUTPUT_FILE, 'a', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=OUTPUT_FIELDS)
            if file_is_new:
                writer.writeheader()

            for idx, class_info in enumerate(class_info_list[start_idx:], start_idx + 1):
                status.processed_classes += 1
                status.maybe_send_heartbeat()
                status.log_status()

                # Memory management: restart Chrome if consumption is too high.
                mem_pct = BrowserManager.check_memory(driver)
                status.memory_readings.append(mem_pct)
                if mem_pct > Config.MAX_MEMORY_PERCENT:
                    log_message(f"[WARN] High memory ({mem_pct:.1f}%) — restarting browser...")
                    driver, ok = BrowserManager.restart_browser(driver)
                    if not ok:
                        raise Exception("Browser restart failed")

                log_message(
                    f"[INFO] Class {idx}/{len(class_info_list)}: "
                    f"{class_info['name']} (#{class_info['number']})"
                )

                # Per-class retry loop with exponential back-off.
                retry_count = 0
                while retry_count < Config.MAX_RETRIES:
                    try:
                        entry_count, skipped = process_class(
                            driver, class_info, writer, status
                        )
                        if skipped:
                            log_message("  -> No waitlist -- skipped.")
                        else:
                            log_message(f"  -> {entry_count} waitlist entries written.")

                        # Save checkpoint after every class (skipped or not).
                        with open(CHECKPOINT_FILE, 'w') as f:
                            json.dump({
                                'filename': filename_only,
                                'last_class_idx': idx,
                                'last_class_number': class_info['number'],
                                'last_class_name': class_info['name'],
                                'timestamp': datetime.now().isoformat(),
                            }, f)
                        break  # Success — exit retry loop.

                    except Exception as e:
                        retry_count += 1
                        if retry_count < Config.MAX_RETRIES:
                            delay = Config.RETRY_DELAYS[retry_count - 1]
                            log_error(
                                f"Attempt {retry_count} failed; retrying in {delay}s",
                                exc_info=e
                            )
                            time.sleep(delay)
                        else:
                            log_error(
                                f"Class {class_info['number']} failed after "
                                f"{Config.MAX_RETRIES} attempts — skipping.",
                                exc_info=e
                            )
                            status.log_error(str(e), e)

                # Periodic cache clear to prevent memory growth on long runs.
                if idx % Config.CACHE_CLEAR_INTERVAL == 0:
                    BrowserManager.clear_cache(driver)

        # ── Step 7: Completion ────────────────────────────────────────────────
        status.log_status(force=True)
        complete_msg = (
            f"Waitlist scrape completed for {filename_only} — "
            f"{status.processed_classes} classes visited, "
            f"{status.waitlisted_classes} had waitlists, "
            f"{status.skipped_classes} skipped, "
            f"{status.total_entries} entries written."
        )
        log_message(complete_msg)
        append_to_batch_log(complete_msg)
        log_message(sentinel)  # "WAITLIST SCRAPE COMPLETE: <filename>" — skip sentinel.
        append_to_batch_log("Waitlist scrape concluded successfully.")

    except Exception as e:
        log_error("Waitlist scraper failed", exc_info=e)
        append_to_batch_log(f"ERROR: Waitlist scraper failed — {e}")
        append_to_batch_log(f"Stack trace: {traceback.format_exc()}")
        raise

    finally:
        if 'driver' in locals():
            driver.quit()
            log_message("[INFO] Browser closed.")


if __name__ == "__main__":
    main()
