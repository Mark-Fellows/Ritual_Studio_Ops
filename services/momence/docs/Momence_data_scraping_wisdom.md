# Momence Data Scraping Wisdom

A comprehensive reference guide for successfully scraping data from the Momence platform. Based on hard-won experience from building and maintaining the Ritual Yoga & Pilates automated data pipeline.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Authentication](#2-authentication)
3. [Scraping Strategies & Selectors](#3-scraping-strategies--selectors)
4. [Known Traps & Pitfalls](#4-known-traps--pitfalls)
5. [Error Handling Patterns](#5-error-handling-patterns)
6. [Logging & Diagnostics](#6-logging--diagnostics)
7. [Data Processing & Deduplication](#7-data-processing--deduplication)
8. [Browser Management](#8-browser-management)
9. [Scheduling & Orchestration](#9-scheduling--orchestration)
10. [Safety Checks & Data Integrity](#10-safety-checks--data-integrity)
11. [Configuration Reference](#11-configuration-reference)
12. [Troubleshooting Guide](#12-troubleshooting-guide)
13. [Lessons Learned](#13-lessons-learned)
14. [Change History](#14-change-history)

---

## 1. System Overview

### Architecture

The system consists of 7 scripts run in sequence by `Run_Momence_Chain.bat`, scheduled daily via Windows Task Scheduler at 2:00 AM Brisbane time:

```
Step 1: momence_scraper8.py p 150        → Scrape past classes (150 pages)
        momence_scraper8.py f 100        → Scrape future classes (100 pages)
Step 2: extract_full_classes2.py         → Filter fully-booked classes
Step 3: momence_class_customers_scrape_4.py  → Scrape customers for full classes
Step 4: Momence_bookings_update.py       → Update master bookings CSV
Step 5: Momence_no_card_customers.py     → Download 5 reports, update masters
Step 6: extract_all_classes_1.py         → Filter all classes with signups > 0
Step 7: momence_class_customers_scrape_1 all.py → Scrape customers for all classes
```

### Data Flow

```
Momence Website
    │
    ├── Sessions Page ──→ momence_classes_p_*.csv (past)
    │                  ──→ momence_classes_f_*.csv (future)
    │                        │
    │                        ├──→ momence_full_classes_*.csv (full only)
    │                        │       └──→ Momence_class_customers_combined.csv
    │                        │
    │                        └──→ momence_all_classes_*.csv (signups > 0)
    │                                └──→ Momence_class_customers_all_*.csv
    │
    ├── CRM Page ──────→ Momence-No-Card-Customers.csv (master)
    │
    ├── Reports ───────→ master_failed_penalties.csv
    │                  → master_late_cancellations.csv
    │                  → master_no_shows.csv
    │                  → master-sales-summary.csv
    │
    └── Bookings ──────→ master_bookings.csv
```

### Key Files

| File | Purpose |
|------|---------|
| `momence_cookies.pkl` | Session cookies for unattended auth |
| `Momence_batch_log.txt` | Shared log across all scripts |
| `Momence_customer_log.txt` | Detailed customer scraper log |
| `momence_scraper_log_*.txt` | Per-run class scraper logs |
| `config.py` | Central configuration |
| `Run_Momence_Chain.bat` | Orchestration batch file |

---

## 2. Authentication

### Method: Cookie-Based (NOT Form Submission)

Momence uses session cookies that persist across browser sessions. The system avoids form-based login entirely, making it reliable for unattended scheduled runs.

### Initial Setup (One-Time)

```bash
python momence_first_login_setup.py
```

1. Opens a visible Chrome window
2. Navigates to `https://momence.com/login`
3. User manually logs in (email + password + 2FA)
4. User presses ENTER after dashboard loads
5. Script saves cookies to `momence_cookies.pkl` and `momence_cookies.pickle`

### Cookie Loading Pattern

```python
driver.get("https://momence.com")  # MUST visit base domain first
cookies = pickle.load(open("momence_cookies.pkl", "rb"))
for cookie in cookies:
    cookie.pop('sameSite', None)   # Selenium incompatibility
    cookie.pop('expiry', None)     # Can cause add_cookie failures
    try:
        driver.add_cookie(cookie)
    except Exception:
        pass  # Some cookies may fail; continue with others
driver.refresh()  # Apply cookies
```

### Auth Failure Detection

Check at multiple points throughout execution:

```python
if "sign-in" in driver.current_url or "login" in driver.current_url:
    # Authentication has failed - cookies expired or invalid
```

**Check these URLs after:**
- Initial cookie load and page refresh
- Navigating to the dashboard
- Navigating to the sessions page
- Each individual class page load (customer scraper)

### Cookie Expiry

- Typical lifespan: ~30 days of inactivity
- No explicit warning before expiry
- Recovery: re-run `momence_first_login_setup.py`
- The customer scraper has automatic recovery with `BrowserManager.handle_auth_failure()`

---

## 3. Scraping Strategies & Selectors

### The Golden Rule: Never Trust CSS Class Names Alone

Momence uses styled-components which generate CSS class names like `sc-1ovdf80-7`, `h3leu5-0`. These **change without warning** when Momence deploys updates. Always have fallback strategies.

### Selector Reliability Tiers

| Tier | Type | Example | Stability |
|------|------|---------|-----------|
| **Tier 1 (Best)** | Semantic/href-based | `.//a[contains(@href,'/sessions/')]` | Very stable |
| **Tier 2 (Good)** | Icon-based | `.//i[@name='location_outline_20']/following-sibling::div//span` | Stable |
| **Tier 3 (Fragile)** | CSS class-based | `.//div[contains(@class,'h3leu5-0 gwIVRD')]` | Can break any time |
| **Tier 4 (Fallback)** | JavaScript regex | `text.match(/\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}/)` | Very resilient |

### Recommended Two-Strategy Pattern

For every field extraction, implement two strategies:

```python
# Strategy 1: CSS class selector (fast, may break)
value = ""
try:
    value = session.find_element(By.XPATH, ".//div[contains(@class,'h3leu5-0 gwIVRD')]").text
except Exception:
    pass

# Strategy 2: JavaScript regex fallback (slower, resilient)
if not value:
    try:
        value = driver.execute_script("""
            var el = arguments[0];
            var allEls = el.querySelectorAll('div, span');
            for (var i = 0; i < allEls.length; i++) {
                var t = allEls[i].textContent.trim();
                if (/^\\d+\\s*\\/\\s*\\d+$/.test(t)) return t;
            }
            return '';
        """, session) or ""
    except Exception:
        pass
```

### Field-by-Field Extraction Reference

#### Sessions/Classes Page (`momence_scraper8.py`)

**Session Row Container** (stable):
```python
session_divs = driver.find_elements(By.CSS_SELECTOR, "div.sc-1ovdf80-7.cIVhim")
```

| Field | Primary Selector | JS Fallback Pattern |
|-------|-----------------|---------------------|
| Date | `h3leu5-0 jSFAww` div[1] | Regex: `\d{1,2}\s+(Jan\|Feb\|...)\s+\d{4}` |
| Time | `h3leu5-0 jSFAww` div[2] | Regex: `\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}` |
| Class Number | `a[href*='/sessions/']` then regex | Very stable (href-based) |
| Class Name | `a[href*='/sessions/']//span` | Fallback: `span.b0xl4x-0` |
| Teacher | `a[href*='/teachers/']//span` | Stable (href-based) |
| Substitute | `i[@name='teacher-substitution_outline_20']` sibling | Stable (icon-based) |
| Location | `i[@name='location_outline_20']` sibling | Stable (icon-based) |
| Signups/Capacity | `h3leu5-0 gwIVRD` | Regex: `^\d+\s*/\s*\d+$` |
| Waitlist | `i[@name='waitlist_outline_20']` sibling | Stable (icon-based) |
| Checked In | `span.wu9s39-0` | Fragile (CSS class) |

#### Customer Detail Pages (`momence_class_customers_scrape_4.py`)

Uses **BeautifulSoup on page source** rather than live Selenium elements to avoid StaleElementReferenceException:

```python
soup = BeautifulSoup(driver.page_source, 'html.parser')
rows = soup.select("div[class*='sc-1ovdf80-7']")
for row in rows:
    name_elem = row.select_one("span[class*='sc-1ta22rh-0']")
    payment_elem = row.select_one("div[class*='sc-13fi9me-0']")
```

#### Report Download Pages (`Momence_no_card_customers.py`)

Three download button detection strategies:

1. **XPath text match**: `//button[contains(., 'Download summary')]`
2. **Menu + button**: Click hamburger menu first, then find download option
3. **JavaScript**: `document.querySelectorAll('button')` + regex on textContent

### Pagination

```python
next_btn = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="Next page"]'))
)
if not next_btn.is_enabled():
    break  # No more pages

# Hide Intercom BEFORE clicking (see Traps section)
driver.execute_script("arguments[0].scrollIntoView();", next_btn)
next_btn.click()

# Smart wait for new content
try:
    WebDriverWait(driver, 7).until(
        lambda d: len(d.find_elements(By.CSS_SELECTOR, "div.sc-1ovdf80-7.cIVhim")) > 0
    )
except:
    time.sleep(3)  # Fallback fixed sleep
```

---

## 4. Known Traps & Pitfalls

### Trap 1: Intercom Chat Overlay Blocks Clicks

Momence loads an Intercom chat widget that sits on top of page elements. It **will block button clicks** (especially "Next page") unless hidden.

**Fix: Run this JavaScript before EVERY page navigation click:**
```javascript
var iframe = document.querySelector('iframe[data-intercom-frame="true"]');
if (iframe) { iframe.style.display = 'none'; }
var icon = document.querySelector('.intercom-lightweight-app-launcher');
if (icon) { icon.style.display = 'none'; }
```

### Trap 2: CSS Classes Change Without Warning

Momence uses styled-components. Class names like `h3leu5-0 jSFAww` are auto-generated hashes that change when Momence deploys updates. This happened on Feb 16-17, 2026 and broke date/time and signups extraction for several days.

**Mitigation:**
- Always have JavaScript regex fallbacks for every field
- Write diagnostic HTML dumps when extraction fails
- Monitor the batch log for `"extracted 0 classes"` entries

### Trap 3: CSV Column Alignment Bugs

If you write CSV files manually with `",".join(row)`:
- Fields containing commas (like `"Mon, 16 Feb 2026"`) will split across columns
- Fields with quotes, newlines, or special characters will corrupt the file

**Fix: Always use Python's `csv.writer` or `csv.DictWriter`:**
```python
import csv
with open(file, "w", newline='', encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    writer.writerow(row)  # Handles quoting automatically
```

### Trap 4: Report "Loading" State

The Total Sales report can take 60+ seconds to load data after clicking "Apply filters". The page shows "Loading report... This report is loading a lot of data and may take a while to finish." The download button **does not appear** until loading completes.

**Fix: Poll for the loading indicator to disappear:**
```python
max_wait = 180  # 3 minutes
waited = 0
while waited < max_wait:
    try:
        driver.find_element(By.XPATH, "//*[contains(text(), 'Loading report')]")
        time.sleep(5)
        waited += 5
    except Exception:
        break  # Loading finished
```

### Trap 5: Stale Element References

After any AJAX call, page refresh, or DOM re-render, previously found Selenium elements become stale. Interacting with them throws `StaleElementReferenceException`.

**Fix: Parse `driver.page_source` with BeautifulSoup instead of live elements:**
```python
soup = BeautifulSoup(driver.page_source, 'html.parser')
# Parse from the static HTML snapshot
```

### Trap 6: Download File Detection Race Condition

After clicking a download button, Chrome creates a `.crdownload` temp file that gets renamed to `.csv` when complete. If you check too early, you miss it; too late, you waste time.

**Fix: Poll for new CSV files and check for .crdownload:**
```python
before_files = set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv")))
# ... click download ...
timeout = 300
while timeout > 0:
    after_files = set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv")))
    new_files = after_files - before_files
    if new_files:
        return new_files.pop()
    crdownloads = glob.glob(os.path.join(DOWNLOAD_DIR, "*.crdownload"))
    if crdownloads:
        pass  # Download in progress, keep waiting
    time.sleep(2)
    timeout -= 2
```

### Trap 7: Brisbane Timezone (UTC+10) Date Calculations

Momence report URLs use UTC dates but the business operates in Brisbane time (UTC+10, no daylight saving). Incorrect timezone handling causes missing or duplicate data.

**Key rules:**
- "Yesterday" in Brisbane = `datetime.now(tz=Brisbane) - timedelta(days=1)`
- URL parameters use ISO 8601 UTC: `2026-02-18T14:00:00.000Z`
- Always overlap date ranges by 1 day to catch boundary records

### Trap 8: Multiple Download Buttons on Total Sales Page

The Total Sales report page has TWO download buttons: "Download summary" and "Download details". The wrong one downloads a different format.

**Fix: Use `prefer_button_text="Download summary"` parameter** to target the correct button.

### Trap 9: Memory Leaks in Long Scraping Runs

The customer scraper processes 400+ classes, taking 1-2 hours. Chrome's memory usage grows continuously.

**Fix: Monitor and restart browser:**
```python
memory_percent = psutil.Process(driver.service.process.pid).memory_percent()
if memory_percent > 80:
    driver.quit()
    driver = create_new_browser()
    load_cookies(driver)
```

### Trap 10: Cookie Domain Mismatch

Cookies must be loaded while on the correct domain. Loading cookies from `momence.com` while on `google.com` will silently fail.

**Fix: Always navigate to `https://momence.com` before loading cookies.**

---

## 5. Error Handling Patterns

### Retry Configuration

```python
MAX_RETRIES = 3
RETRY_DELAYS = [5, 10, 20]  # Exponential backoff in seconds
```

### Three-Level Retry Strategy

**Level 1 - Element Retry (within a page):**
```python
for attempt in range(MAX_RETRIES):
    try:
        element = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        element.click()
        break
    except Exception:
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAYS[attempt])
```

**Level 2 - Page Retry (reload and try again):**
```python
for attempt in range(MAX_RETRIES):
    try:
        driver.get(url)
        # ... extract data ...
        break
    except Exception:
        if attempt == MAX_RETRIES - 1:
            raise
        time.sleep(RETRY_DELAYS[attempt])
```

**Level 3 - Browser Restart (nuclear option):**
```python
if memory_percent > MAX_MEMORY_PERCENT or consecutive_failures > 5:
    driver.quit()
    driver = BrowserManager.create_browser()
    BrowserManager.load_cookies(driver)
```

### Checkpoint/Resume for Long Runs

The customer scrapers save progress after each class:

```python
checkpoint = {
    'filename': filename_only,
    'last_class_idx': idx,
    'last_class_number': class_info['number'],
    'timestamp': datetime.now().isoformat()
}
with open(Config.CHECKPOINT_FILE, 'w') as f:
    json.dump(checkpoint, f)
```

On restart, the scraper resumes from the last checkpoint:
```python
if os.path.exists(Config.CHECKPOINT_FILE):
    checkpoint = json.load(open(Config.CHECKPOINT_FILE))
    if checkpoint['filename'] == current_filename:
        start_idx = checkpoint['last_class_idx']
```

### Exception Isolation

Each report in `Momence_no_card_customers.py` is wrapped in its own try/except:
```python
try:
    # Report 1: No Card Customers
    ...
except Exception as e:
    log_error_to_batch_log("No Card Customers", e)

try:
    # Report 2: Failed Penalties
    ...
except Exception as e:
    log_error_to_batch_log("Failed Penalties", e)
```

This ensures one report failure doesn't prevent the others from running.

---

## 6. Logging & Diagnostics

### Three-Tier Logging System

| Tier | File | Purpose | Written By |
|------|------|---------|-----------|
| **Batch Log** | `Momence_batch_log.txt` | High-level summary of all script runs | All scripts |
| **Customer Log** | `Momence_customer_log.txt` | Detailed per-class scraping progress | Customer scrapers |
| **Scraper Logs** | `momence_scraper_log_{p\|f}_{timestamp}.txt` | Verbose per-run logging | `momence_scraper8.py` |

### Batch Log Format

```
2026-02-19 02:00:04 - Script started - Retrieving p classes for 150 pages
2026-02-19 02:10:25 - Momence scraper ran successfully, 150 pages extracted.
2026-02-19 02:18:59 - Customer scraper started
2026-02-19 02:21:00 0 records added to No Card Customers (current snapshot)
2026-02-19 02:24:14 - Customer scrape concluded successfully
```

### What to Log (Recommendations)

**Always log:**
- Script start and completion with timestamps
- Authentication success or failure
- Record counts (rows read, written, deduplicated)
- Exception details with stack traces (in customer log, not batch log)
- Performance metrics (pages scraped, time taken, memory usage)
- File operations (created, moved, archived)

**Never log:**
- Passwords or credentials
- Full HTML page source (save to debug files instead)
- Every single element click (too noisy)

### Diagnostic File Dumps

When extraction fails, save targeted HTML for debugging:

| Condition | File Created | Contents |
|-----------|-------------|----------|
| Date/time or signups missing | `debug_session_div.html` | HTML of one session container |
| Download button not found | `debug_page_source_no_button.html` | Full report page HTML |
| Customer extraction fails | `debug_class_page_source.html` | Full class page HTML |

These are created **once per run** (not per failure) to avoid disk spam.

### Status Reports (Customer Scraper)

Every 5 minutes during long runs:
```
Status Report at 2026-02-15 02:24:25
Runtime: 0:04:00.846458
Classes: 24 processed, 24 successful (100.0%)
Performance: 240.0 classes/hour, 11.9 customers/class
Memory: 0.1% usage
Auth Failures: 2
Errors: 0 total
```

---

## 7. Data Processing & Deduplication

### Deduplication Keys by Report

| Report | Key Fields | Strategy |
|--------|-----------|----------|
| No Card Customers | Customer Email | `keep='last'` (latest snapshot) |
| Failed Penalties | Customer Name + Amount + Last Fail Date | Composite key |
| Late Cancellations | Customer Name + Cancelled Class + Cancelled Date | Composite key |
| No Shows | Customer Name + Class + Class Date | Composite key |
| Total Sales | Date + Sale Reference | Composite key |
| Bookings | Booking ID or composite | `keep='last'` |

### Master File Update Pattern

```python
# 1. Read new download
new_df = pd.read_csv(new_file)

# 2. Read existing master (or create empty)
if os.path.exists(master_file):
    master_df = pd.read_csv(master_file)
else:
    master_df = pd.DataFrame()

# 3. Concatenate
combined = pd.concat([master_df, new_df], ignore_index=True)

# 4. Deduplicate (keep='last' = newest wins)
deduped = combined.drop_duplicates(subset=KEY_FIELDS, keep='last')

# 5. Save
deduped.to_csv(master_file, index=False)

# 6. Archive raw download
shutil.move(new_file, os.path.join(ARCHIVE_DIR, new_file))
```

### Date Range Calculations

For reports with date-range parameters (Brisbane UTC+10):

```python
# Calculate "from" date: 1 day before most recent record in master
if master has data:
    start = most_recent_date - timedelta(days=1)
else:
    start = datetime(2025, 12, 9)  # Initial load date

# Calculate "to" date: yesterday at 23:59
end = datetime.now() - timedelta(days=1)

# Convert to UTC for URL parameters
# Brisbane is UTC+10, so midnight Brisbane = 14:00 UTC previous day
start_utc = f"{(start - timedelta(hours=10)).strftime('%Y-%m-%dT%H:%M:%S')}.000Z"
end_utc = f"{(end - timedelta(hours=10) + timedelta(hours=23, minutes=59, seconds=59)).strftime('%Y-%m-%dT%H:%M:%S')}.999Z"
```

### Data Cleanup Rules

Applied in `cleanup_existing_masters.py`:
- Remove "Home location" column (appears in some exports)
- Fill empty "Membership name" with "blank"
- Fill empty "Penalty charged" with 0
- Fill empty "Membership used" with "blank"
- Normalize email addresses (lowercase, strip whitespace)

---

## 8. Browser Management

### Chrome Configuration

```python
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

options = webdriver.ChromeOptions()
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-extensions')

# Download preferences
prefs = {
    "download.default_directory": DOWNLOAD_DIR,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
}
options.add_experimental_option("prefs", prefs)

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
```

### ChromeDriver Version Management

`webdriver_manager` auto-installs the matching ChromeDriver. When Chrome auto-updates, the cached driver may become incompatible.

**Watch for:** Chrome major version changes (e.g., 144 -> 145). These coincide with Momence UI changes that break selectors.

### Memory Management

```python
import psutil

# Check memory after each class
process = psutil.Process(driver.service.process.pid)
memory_pct = process.memory_percent()

if memory_pct > Config.MAX_MEMORY_PERCENT:  # 80%
    driver.quit()
    driver = create_new_browser()
    load_cookies(driver)
```

### Cache Clearing (Every N Classes)

```python
if class_count % Config.CACHE_CLEAR_INTERVAL == 0:  # Every 10 classes
    driver.execute_script("window.localStorage.clear();")
    driver.execute_script("window.sessionStorage.clear();")
    # Note: Do NOT delete cookies here - breaks authentication
```

### Timeout Configuration

```python
driver.set_page_load_timeout(60)  # 60 seconds for page loads
# Use explicit waits (not implicit):
WebDriverWait(driver, 40).until(EC.element_to_be_clickable(...))
```

---

## 9. Scheduling & Orchestration

### Run_Momence_Chain.bat

```batch
@echo off
cd /d "C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data"

REM Step 1: Scrape classes
python momence_scraper8.py p 150
python momence_scraper8.py f 100

REM Step 2: Extract full classes
python extract_full_classes2.py

REM Step 3: Scrape customers for full classes
python momence_class_customers_scrape_4.py

REM Step 4: Update bookings
python Momence_bookings_update.py

REM Step 5: Download reports
python Momence_no_card_customers.py

REM Step 6: Extract all classes with signups
python extract_all_classes_1.py

REM Step 7: Scrape customers for all classes
python "momence_class_customers_scrape_1 all.py"
```

### Dependency Chain

```
momence_scraper8.py (p + f)
         │
         ├── extract_full_classes2.py
         │         │
         │         └── momence_class_customers_scrape_4.py
         │
         ├── Momence_bookings_update.py
         │
         ├── Momence_no_card_customers.py
         │
         └── extract_all_classes_1.py
                   │
                   └── momence_class_customers_scrape_1 all.py
```

### Windows Task Scheduler Setup

- Trigger: Daily at 2:00 AM (or 11:00 PM previous day)
- Action: Run `Run_Momence_Chain.bat`
- Working directory: Script folder
- Requirements: Computer must be awake, user logged in (Chrome needs display)
- Prerequisite: Run `momence_first_login_setup.py` once to create cookie file

### Typical Run Times

| Script | Duration |
|--------|----------|
| momence_scraper8.py p 150 | ~10 minutes |
| momence_scraper8.py f 100 | ~8 minutes |
| extract_full_classes2.py | < 1 second |
| momence_class_customers_scrape_4.py | 4-6 minutes (20-25 classes) |
| Momence_bookings_update.py | ~2 minutes |
| Momence_no_card_customers.py | ~5 minutes |
| extract_all_classes_1.py | < 1 second |
| momence_class_customers_scrape_1 all.py | 60-80 minutes (400+ classes) |
| **Total** | **~90-110 minutes** |

---

## 10. Safety Checks & Data Integrity

### Pre-Run Checks

1. **Cookie file exists:** `momence_cookies.pkl` must be present
2. **Download directory exists:** `momence_downloads/` and `momence_downloads/Archive/`
3. **Master files writable:** Not locked by Excel or OneDrive sync

### Data Validation Checks

**Empty file detection:**
```python
if os.path.getsize(OUTPUT_FILE) <= len(",".join(headers)) + 10:
    os.remove(OUTPUT_FILE)
    log_error("Scraper produced empty file")
```

**Zero-class extraction alert:**
```python
if extracted_count == 0:
    # Log as potential issue - check if selectors broke
    append_to_batch_log(f"WARNING: extracted 0 classes - selectors may need updating")
```

**Deduplication sanity check:**
```python
before_count = len(combined_df)
after_count = len(deduped_df)
removed = before_count - after_count
log_message(f"{removed} duplicates removed, {after_count} records in master")
```

### Authentication Verification Points

1. After cookie load → check URL for "login"/"sign-in"
2. After dashboard navigation → check URL
3. After sessions page load → check URL
4. During class iteration → check for redirect (customer scraper)

### File Integrity

- Downloaded CSVs are moved to `Archive/` after processing (not deleted)
- Master files are overwritten (consider keeping backups)
- Debug HTML files are overwritten each run (one copy only)

---

## 11. Configuration Reference

From `config.py`:

```python
# URLs
BASE_URL = "https://momence.com"
DASHBOARD_URL = "https://momence.com/dashboard/32083"

# Files
LOG_FILE = 'Momence_customer_log.txt'
BATCH_LOG_FILE = 'Momence_batch_log.txt'
CHECKPOINT_FILE = 'scraper_checkpoint.json'

# Timing
STATUS_INTERVAL = 300         # 5-minute status reports
HEARTBEAT_INTERVAL = 300      # 5-minute heartbeat
ELEMENT_WAIT_TIMEOUT = 40     # Max wait for elements (seconds)
PAGE_LOAD_TIMEOUT = 60        # Max wait for page load (seconds)

# Browser
MAX_MEMORY_PERCENT = 80       # Restart browser threshold
CACHE_CLEAR_INTERVAL = 10     # Clear cache every N classes

# Retries
MAX_RETRIES = 3
RETRY_DELAYS = [5, 10, 20]   # Exponential backoff (seconds)
```

### Report URLs

| Report | Base URL Pattern |
|--------|-----------------|
| No Card Customers | `/dashboard/32083/crm?f=...&tab=ALL_CUSTOMERS_TAB` |
| Failed Penalties | `/dashboard/32083/reports/declined-penalty-charges/7954094?...` |
| Late Cancellations | `/dashboard/32083/reports/late-cancellations/7952318?...` |
| No Shows | `/dashboard/32083/reports/no-shows/7954137?...` |
| Total Sales | `/dashboard/32083/reports/total-sales/7959682?...` |

---

## 12. Troubleshooting Guide

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| "Redirected to login" in batch log | Cookies expired | Run `momence_first_login_setup.py` |
| "extracted 0 classes with signups > 0" | CSS selectors changed (Momence updated) | Check `debug_session_div.html`, update selectors in `momence_scraper8.py` |
| "Could not find download button" | Report still loading OR button text changed | Check `debug_page_source_no_button.html`, increase wait time |
| PermissionError on master CSV | File open in Excel or locked by OneDrive | Close Excel, wait for OneDrive sync |
| KeyError: 'Date' in sales processing | Downloaded CSV has different column names | Check raw download in `momence_downloads/` |
| Empty customer scrape (0 customers) | Auth failure mid-run OR page structure changed | Check `Momence_customer_log.txt` for auth failures |
| Browser crashes after 30+ minutes | Memory leak | Reduce `MAX_MEMORY_PERCENT` or `CACHE_CLEAR_INTERVAL` |
| "Next page button not enabled" early | Fewer pages available than requested | Normal - scraper stops gracefully |
| High auth failure count | Cookies aging or network issues | Re-generate cookies if > 10 failures per run |
| .crdownload files left behind | Download interrupted | Delete manually; they'll be regenerated next run |

### How to Investigate a Failure

1. **Check `Momence_batch_log.txt`** for the most recent entries
2. **Look for "Exception" or "ERROR"** entries with timestamps
3. **Check the specific scraper log** (`momence_scraper_log_*.txt`) for that timestamp
4. **Check `Momence_customer_log.txt`** for detailed per-class errors
5. **Look for debug HTML files** (`debug_*.html`) for DOM snapshots
6. **Compare working vs broken CSV files** to identify column shifts

---

## 13. Lessons Learned

### What Works Well

1. **Cookie-based auth** is more reliable than form login for unattended runs
2. **Page source parsing** (BeautifulSoup) avoids stale element issues entirely
3. **Icon-based selectors** (`i[@name='location_outline_20']`) are far more stable than CSS classes
4. **href-based selectors** (`a[contains(@href,'/sessions/')]`) are the most reliable
5. **JavaScript regex fallbacks** catch data even when CSS classes change
6. **Checkpoint/resume** saves hours when a long scrape is interrupted
7. **Shared batch log** gives one-stop visibility into the entire pipeline
8. **Memory monitoring** with auto-restart prevents crashes in long runs

### What Goes Wrong

1. **Styled-component CSS classes change** when Momence deploys updates (no warning)
2. **Intercom chat overlay** blocks clicks if not hidden on every page
3. **Manual CSV writing** (`",".join()`) breaks when fields contain commas
4. **15-second static waits** aren't enough for slow-loading reports
5. **Single-strategy selectors** leave no fallback when things change
6. **Missing completion log entries** make it hard to tell if scripts finished
7. **No date range overlap** causes missing records at boundaries

### Rules for Future Development

1. **Every CSS-based selector MUST have a JavaScript regex fallback**
2. **Always use `csv.writer`** (never manual comma joining) for CSV output
3. **Poll for page state changes** instead of using fixed `time.sleep()`
4. **Log completion entries** for every exit path (including early returns)
5. **Save diagnostic HTML** when extraction fails unexpectedly
6. **Test with 1 page first** before running full 100-150 page scrapes
7. **Keep the batch log clean** - summaries only, details in per-script logs
8. **Overlap date ranges** by 1 day minimum to catch boundary records

---

## 14. Change History

| Date | Change | Files Modified |
|------|--------|---------------|
| 2026-02-19 | Fixed CSS selector breakage for date/time and signups fields. Added JavaScript regex fallbacks. Switched to `csv.writer` for proper CSV formatting. Added weekday/date column splitting. Added diagnostic HTML dump. | `momence_scraper8.py` |
| 2026-02-19 | Fixed Total Sales download failure caused by report loading slowly. Added polling loop (up to 3 min) that waits for "Loading report" text to disappear before searching for download button. | `Momence_no_card_customers.py` |
| 2026-02-19 | Added "Customer scrape concluded successfully" batch log entry to all exit paths (no files, already processed, no classes, normal completion). | `momence_class_customers_scrape_4.py`, `momence_class_customers_scrape_1 all.py` |
