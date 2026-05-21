#!/usr/bin/env python3
"""
momence_sessions_scrape_lite.py
================================
Lightweight sessions list scraper — substitute teacher flag and waitlist count.

Navigates the Momence sessions admin LIST pages (NOT individual class detail
pages) to extract per-session substitute and waitlist data.  Much faster than
the old full-scrape approach because it only reads the paginated list view.

Coverage window (configurable below):
  - Past:   last PAST_DAYS days from today
  - Future: next FUTURE_DAYS days from today

Output:
  momence_classes_lite_<YYYY MM DD HH MM>.csv
  Columns: Timestamp, Class Number, Teacher, Substitute, Waitlist

Selector note:
  Momence uses styled-component CSS class names that change on redeployment.
  If fields stop being captured, set DEBUG_SAVE_HTML = True, inspect the
  saved HTML in Log_files/debug_lite_session_list.html, and update the
  selector constants in the SELECTORS section below.

Authentication:
  Uses momence_cookies.pkl (Config.COOKIES_FILE) — same as the rest of
  the chain.  Run momence_first_login_setup.py if cookies are expired.
"""

import os
import re
import csv
import sys
import glob
import time
import pickle
import logging
import traceback
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
from bs4.element import Tag

import config

Config = config

# ── Configuration ──────────────────────────────────────────────────────────────
PAST_DAYS = 30  # days of past classes to cover
FUTURE_DAYS = 60  # days of future classes to cover
PAGE_WAIT = 4  # seconds to wait after each page navigation
MAX_PAGES = 100  # safety limit on pages per direction
DEBUG_SAVE_HTML = True  # set True to save page HTML for selector debugging

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, "Log_files")
# Master batch log — moved out of OneDrive on 2026-05-18 to stop sync locks
# truncating writes. Falls back to the legacy in-tree path if the local
# folder is absent (e.g. clean checkout on a new machine).
_LOCAL_BATCH_LOG_DIR = r"C:\Users\markj\Momence_local_logs"
if os.path.isdir(_LOCAL_BATCH_LOG_DIR):
    BATCH_LOG_FILE = os.path.join(_LOCAL_BATCH_LOG_DIR, "Momence_batch_log.txt")
else:
    BATCH_LOG_FILE = os.path.join(LOG_DIR, "Momence_batch_log.txt")
DEBUG_HTML = os.path.join(LOG_DIR, "debug_lite_session_list.html")
OUTPUT_FIELDS = ["Timestamp", "Class Number", "Teacher", "Substitute", "Waitlist"]

# ── Selectors ──────────────────────────────────────────────────────────────────
# These are candidate CSS selectors tried in order; first match wins.
# Update if Momence redeploys with new styled-component class names.

# Session row: the repeating container for one class entry on the list page.
ROW_SELECTORS = [
    "tr[class*='ession']",  # table row variant
    "div[class*='session-row']",
    "div[class*='SessionRow']",
    "li[class*='session']",
]

# Class ID: extracted from href of a link pointing to /sessions/<id>
CLASS_LINK_PATTERN = re.compile(r"/sessions/(\d+)")

# Teacher name: link to a teacher profile
TEACHER_SELECTORS = [
    "a[href*='/teachers/']",
    "[class*='teacher'] a",
    "[class*='instructor'] a",
    "[class*='TeacherName']",
]

# Substitute indicator: any element that flags a class as covered by a sub
SUBSTITUTE_SELECTORS = [
    "[class*='substitute']",
    "[class*='Substitute']",
    "[class*='sub-badge']",
    "[class*='SubBadge']",
    "[class*='cover']",
    "[class*='Cover']",
    "[title*='ubstitute']",
    "[aria-label*='ubstitute']",
]

# Waitlist count: an element showing how many people are on the waitlist
WAITLIST_SELECTORS = [
    "[class*='waitlist']",
    "[class*='Waitlist']",
    "[class*='wait-list']",
    "[class*='WaitList']",
]

# Pagination: the "Next" button or page navigation
NEXT_PAGE_SELECTORS = [
    "button[aria-label*='Next']",
    "a[aria-label*='Next']",
    "[class*='pagination'] button:last-child",
    "button[class*='next']",
    "button:contains('Next')",
]


# ── Logging helpers ────────────────────────────────────────────────────────────


def setup_logging(timestamp_str: str) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(LOG_DIR, f"momence_sessions_lite_{timestamp_str}.txt"),
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
    )


def log(msg: str) -> None:
    print(msg)
    logging.info(msg)


def append_to_batch_log(message: str) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for attempt in range(3):
        try:
            with open(BATCH_LOG_FILE, "a", encoding="utf-8") as fh:
                fh.write(f"{ts} - {message}\n")
            return
        except Exception:
            time.sleep(2)


# ── Browser helpers ────────────────────────────────────────────────────────────


def create_browser() -> webdriver.Chrome:
    """Create a Chrome WebDriver with standard Ritual pipeline settings."""
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    # Uncomment for headless mode once selectors are confirmed:
    # options.add_argument('--headless=new')
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(Config.PAGE_LOAD_TIMEOUT)
    return driver


def load_cookies(driver: webdriver.Chrome) -> bool:
    """Load session cookies from Config.COOKIES_FILE and verify authentication."""
    if not os.path.exists(Config.COOKIES_FILE):
        log(f"[ERROR] Cookie file not found: {Config.COOKIES_FILE}")
        log("[ERROR] Run momence_first_login_setup.py to create it.")
        return False
    driver.get(Config.LOGIN_URL)
    try:
        with open(Config.COOKIES_FILE, "rb") as f:
            cookies = pickle.load(f)
        loaded = 0
        for cookie in cookies:
            cookie.pop("sameSite", None)
            cookie.pop("expiry", None)
            try:
                driver.add_cookie(cookie)
                loaded += 1
            except Exception:
                pass
        log(f"[AUTH] Loaded {loaded}/{len(cookies)} cookies")
        driver.get(Config.DASHBOARD_URL)
        time.sleep(3)
        if "sign-in" in driver.current_url or "login" in driver.current_url:
            log("[ERROR] Authentication failed — redirected to login page.")
            log("[ERROR] Cookies may be expired. Run momence_first_login_setup.py.")
            return False
        log(f"[AUTH] Authenticated OK: {driver.current_url}")
        return True
    except Exception as e:
        log(f"[ERROR] Cookie load failed: {e}")
        return False


def hide_intercom(driver: webdriver.Chrome) -> None:
    """Suppress the Intercom overlay that can block button clicks."""
    try:
        driver.execute_script(
            """
            var el = document.querySelector('[data-intercom-frame="true"]');
            if (el) el.style.display='none';
            var ic = document.querySelector('.intercom-lightweight-app-launcher');
            if (ic) ic.style.display='none';
        """
        )
    except Exception:
        pass


# ── Selector utilities ─────────────────────────────────────────────────────────


def first_match(
    soup_element, selectors: list, attr: Optional[str] = None
) -> Optional[str]:
    """Try each selector in order; return text (or attr value) of first match."""
    for sel in selectors:
        try:
            found = soup_element.select_one(sel)
            if found:
                if attr:
                    return found.get(attr, "").strip() or None
                return found.get_text(strip=True) or None
        except Exception:
            continue
    return None


def any_match(soup_element, selectors: list) -> bool:
    """Return True if any selector matches."""
    for sel in selectors:
        try:
            if soup_element.select_one(sel):
                return True
        except Exception:
            continue
    return False


def extract_class_id(soup_element) -> Optional[str]:
    """Extract the numeric Momence session ID from a /sessions/<id> link."""
    for link in soup_element.find_all("a", href=True):
        m = CLASS_LINK_PATTERN.search(str(link.get("href") or ""))
        if m:
            return m.group(1)
    return None


def extract_waitlist_count(soup_element) -> int:
    """
    Extract the waitlist count from a session row.
    Looks for explicit waitlist elements, then falls back to text containing
    a number followed by 'waitlist' or 'waiting'.
    """
    # Try explicit selectors first
    for sel in WAITLIST_SELECTORS:
        try:
            el = soup_element.select_one(sel)
            if el:
                text = el.get_text(strip=True)
                nums = re.findall(r"\d+", text)
                if nums:
                    return int(nums[0])
        except Exception:
            pass
    # Fallback: look for 'N waitlist' or 'N waiting' pattern anywhere in row text
    row_text = soup_element.get_text(" ", strip=True)
    m = re.search(r"(\d+)\s*(?:on\s+)?wait(?:list|ing)", row_text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return 0


# ── Date parsing ───────────────────────────────────────────────────────────────

# Momence session list shows dates in various formats; try common ones.
DATE_PATTERNS = [
    # "Thu, 16 Apr 2026" — Momence sessions list primary format
    ("%A, %d %b %Y", re.compile(r"\w{3},\s+\d{1,2}\s+\w{3}\s+\d{4}")),
    # "16 Apr 2026" — without weekday prefix
    ("%d %b %Y", re.compile(r"\d{1,2}\s+\w{3}\s+\d{4}")),
    # ISO: "2026-04-16"
    ("%Y-%m-%d", re.compile(r"\d{4}-\d{2}-\d{2}")),
    # slash: "16/04/2026"
    ("%d/%m/%Y", re.compile(r"\d{1,2}/\d{1,2}/\d{4}")),
]


def parse_date_from_text(text: str) -> Optional[date]:
    """Attempt to parse a date from a text string using common Momence formats."""
    for fmt, pattern in DATE_PATTERNS:
        m = pattern.search(text)
        if m:
            try:
                return datetime.strptime(m.group(0), fmt).date()
            except ValueError:
                continue
    return None


# ── Core scraping logic ────────────────────────────────────────────────────────


def scrape_sessions_page(
    driver: webdriver.Chrome,
    run_timestamp: str,
    start_date: date,
    end_date: date,
    debug_saved: list,
) -> tuple[List[Dict], bool]:
    """
    Parse the current sessions list page and extract rows within the date window.

    Returns a list of row dicts and a boolean 'done' flag (True = all rows on
    this page were outside the window, so stop paginating).
    """
    time.sleep(PAGE_WAIT)
    hide_intercom(driver)
    html = driver.page_source

    if DEBUG_SAVE_HTML and not debug_saved:
        try:
            with open(DEBUG_HTML, "w", encoding="utf-8") as f:
                f.write(html)
            log(f"[DEBUG] Saved page source to {DEBUG_HTML}")
            debug_saved.append(True)
        except Exception:
            pass

    soup = BeautifulSoup(html, "html.parser")
    rows_out = []
    in_window_count = 0

    # Try each row selector until one yields results
    row_elements = []
    for sel in ROW_SELECTORS:
        row_elements = soup.select(sel)
        if row_elements:
            log(f"[PARSE] Using row selector '{sel}', found {len(row_elements)} rows")
            break

    if not row_elements:
        # Fallback: walk up from each /sessions/<id> link until we find
        # an ancestor element whose text contains a date — this gives us
        # the full session row rather than just the narrow link parent.
        seen_ids = set()
        row_tuples = []
        for link in soup.find_all("a", href=CLASS_LINK_PATTERN):
            m_id = CLASS_LINK_PATTERN.search(str(link.get("href") or ""))
            if not m_id:
                continue
            class_id_val = m_id.group(1)
            if class_id_val in seen_ids:
                continue  # same session can have multiple links per row
            candidate = link.parent
            for _ in range(12):
                if candidate is None or candidate.name in ("body", "html", "main"):
                    break
                if parse_date_from_text(candidate.get_text(" ", strip=True)):
                    break  # found an ancestor containing date text
                candidate = candidate.parent
            if candidate and candidate.name not in ("body", "html", "main"):
                seen_ids.add(class_id_val)
                row_tuples.append((class_id_val, candidate))
        if row_tuples:
            log(f"[PARSE] Fallback: found {len(row_tuples)} rows via ancestor walk")
        else:
            log("[WARN] No session rows found on this page — check ROW_SELECTORS")
            return rows_out, True  # stop paginating
        # Wrap as (class_id, row) pairs for the loop below
        row_elements = row_tuples
        use_preextracted_id = True
    else:
        use_preextracted_id = False

    for item in row_elements:
        if use_preextracted_id:
            class_id, row = item
        else:
            row = item
            class_id = extract_class_id(row)
            if not class_id:
                continue  # not a session row

        # Date: try to parse from the row text to apply window filter
        row_text = row.get_text(" ", strip=True)
        row_date = parse_date_from_text(row_text)

        if row_date is not None:
            if row_date < start_date or row_date > end_date:
                continue  # outside coverage window
        # Count every row with a parseable date as in-window;
        # rows with no parseable date are included anyway (date comes from sessions API).
        in_window_count += 1

        # Teacher + Substitute: the sessions list shows TWO /teachers/ profile
        # links in the row when a substitute is covering â€” the cover teacher
        # first, then the original.  A single link means no substitute.
        # Ensure `row` is a Tag so static type checkers know `find_all` exists.
        if isinstance(row, Tag):
            teacher_links = row.find_all("a", href=re.compile(r"/teachers/"))
        else:
            teacher_links = []
        substitute = "Yes" if len(teacher_links) >= 2 else "No"
        teacher = (
            teacher_links[0].get_text(strip=True)
            if teacher_links
            else (first_match(row, TEACHER_SELECTORS) or "NA")
        )

        # Waitlist
        waitlist = extract_waitlist_count(row)

        rows_out.append(
            {
                "Timestamp": run_timestamp,
                "Class Number": class_id or "",
                "Teacher": teacher,
                "Substitute": substitute,
                "Waitlist": str(waitlist),
            }
        )

    # Stop only when the page returned no rows at all — not when dates fail to parse.
    done = len(row_elements) == 0
    return rows_out, done


def navigate_to_sessions_list(driver: webdriver.Chrome, direction: str) -> bool:
    """
    Navigate to the sessions list filtered by direction ('past' or 'future').
    Returns True if navigation succeeded, False otherwise.
    """
    # Momence sessions list URL — adjust if Momence changes routing
    url = f"{Config.DASHBOARD_URL}/sessions"
    if direction == "past":
        url += "?direction=past"
    else:
        url += "?direction=future"
    try:
        driver.get(url)
        time.sleep(PAGE_WAIT)
        if "sign-in" in driver.current_url or "login" in driver.current_url:
            log("[ERROR] Redirected to login — cookies expired")
            return False
        log(f"[NAV] Sessions list loaded ({direction}): {driver.current_url}")
        return True
    except Exception as e:
        log(f"[ERROR] Failed to navigate to sessions list: {e}")
        return False


def click_next_page(driver: webdriver.Chrome) -> bool:
    """Click the next-page button. Returns True if clicked, False if not found."""
    hide_intercom(driver)
    for sel in NEXT_PAGE_SELECTORS:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            if btn.is_enabled() and btn.is_displayed():
                btn.click()
                log(f"[PAGE] Next page clicked (selector: {sel})")
                return True
        except Exception:
            continue
    # JavaScript fallback: look for any enabled button with 'Next' text
    try:
        clicked = driver.execute_script(
            """
            var btns = Array.from(document.querySelectorAll('button, a'));
            var next = btns.find(b =>
                /^next$/i.test(b.textContent.trim()) && !b.disabled);
            if (next) { next.click(); return true; }
            return false;
        """
        )
        if clicked:
            log("[PAGE] Next page clicked (JS fallback)")
            return True
    except Exception:
        pass
    return False


def scrape_direction(
    driver: webdriver.Chrome,
    direction: str,
    start_date: date,
    end_date: date,
    run_timestamp: str,
) -> List[Dict]:
    """Paginate through all list pages for one direction and collect rows."""
    if not navigate_to_sessions_list(driver, direction):
        return []

    all_rows = []
    debug_saved = []

    for page_num in range(1, MAX_PAGES + 1):
        log(f"[PAGE] {direction} page {page_num}")
        rows, done = scrape_sessions_page(
            driver, run_timestamp, start_date, end_date, debug_saved
        )
        all_rows.extend(rows)
        log(
            f"[PAGE] {direction} page {page_num}: {len(rows)} rows in window "
            f"(total so far: {len(all_rows)})"
        )

        if done:
            log(f"[PAGE] All rows outside window — stopping {direction} pagination")
            break
        if not click_next_page(driver):
            log(f"[PAGE] No next-page button found — end of {direction} list")
            break

    return all_rows


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    now = datetime.now()
    timestamp_str = now.strftime("%Y %m %d %H %M")
    run_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    output_file = os.path.join(SCRIPT_DIR, f"momence_classes_lite_{timestamp_str}.csv")
    today = now.date()
    start_date = today - timedelta(days=PAST_DAYS)
    end_date = today + timedelta(days=FUTURE_DAYS)

    setup_logging(timestamp_str)
    append_to_batch_log("momence_sessions_scrape_lite.py started")
    log(f"[INFO] Coverage: {start_date} → {end_date}")
    log(f"[INFO] Output:   {output_file}")

    driver = None
    try:
        driver = create_browser()
        if not load_cookies(driver):
            log("[ABORT] Could not authenticate — exiting")
            append_to_batch_log("ERROR: momence_sessions_scrape_lite.py — auth failed")
            sys.exit(1)

        all_rows = []
        for direction in ("past", "future"):
            rows = scrape_direction(
                driver, direction, start_date, end_date, run_timestamp
            )
            all_rows.extend(rows)

        # Deduplicate by Class Number (keep last occurrence)
        seen = {}
        for row in all_rows:
            seen[row["Class Number"]] = row
        deduped = list(seen.values())
        log(f"[INFO] Total rows: {len(all_rows)} raw, " f"{len(deduped)} after dedup")

        with open(output_file, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=OUTPUT_FIELDS)
            writer.writeheader()
            writer.writerows(deduped)

        sub_count = sum(1 for r in deduped if r["Substitute"] == "Yes")
        wait_count = sum(1 for r in deduped if int(r["Waitlist"]) > 0)
        msg = (
            f"momence_sessions_scrape_lite.py complete: "
            f"{len(deduped)} sessions, {sub_count} substitutes, "
            f"{wait_count} with waitlist → {os.path.basename(output_file)}"
        )
        log(f"[OK] {msg}")
        append_to_batch_log(msg)

    except Exception as e:
        msg = f"ERROR: momence_sessions_scrape_lite.py failed: {e}"
        log(f"[ERROR] {msg}")
        log(traceback.format_exc())
        append_to_batch_log(msg)
        sys.exit(1)
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    main()
