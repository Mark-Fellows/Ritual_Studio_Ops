# Momence Data Pipeline — Maintenance Guide

**Last updated:** 2026-03-23
**Scope:** Nightly Momence scraper chain and Ritual Dashboard pipeline

---

## 1. System Overview

Two separate scheduled tasks run each night:

| Task name | Scheduled time | What it runs | Typical duration |
|---|---|---|---|
| **Momence scraper** | 02:00 AM | `Run_Momence_Chain.bat` — full scrape + customer data | ~2 hours |
| **Momence bookings** | 01:02 AM | `Momence_bookings_update.py` — downloads bookings CSV from Momence and appends to `master_bookings.csv` | ~5 min |
| **Momence dashboard 2** | 05:09 AM | Ritual Dashboard pipeline (`run_pipeline.js`) | ~1 min |

The **Momence bookings** task runs first (01:02 AM) and writes its "N records added to Bookings" entry to `Momence_batch_log.txt`. Because this entry has no timestamp prefix, it appears in the log immediately after the previous night's scraper entries — this is normal and is not a missing step.

---

## 2. Log File Locations

| Log | Path | Purpose |
|---|---|---|
| `Momence_batch_log.txt` | `Momence_data\Log_files\` | Master batch log — high-level outcomes for every step across all scripts |
| `momence_scraper_log_f_YYYY MM DD HH MM.txt` | `Momence_data\Log_files\` | Detailed future-classes scraper log (one file per run) |
| `momence_scraper_log_p_YYYY MM DD HH MM.txt` | `Momence_data\Log_files\` | Detailed past-classes scraper log (one file per run) |
| `Run_Momence_Chain_*.log` | `Momence_data\Log_files\` | Full stdout/stderr from `Run_Momence_Chain.bat` |
| `pipeline_YYYYMMDD_HHmmss.log` | `Momence_data\logs\` | Ritual Dashboard pipeline log (one file per run) |

---

## 3. Run_Momence_Chain.bat — Step Reference

Steps run in order. Each step now logs its outcome to both the chain log and `Momence_batch_log.txt`.

| Step | Script | Purpose |
|---|---|---|
| 0 | `check_cookie_expiry.py` | Warns if Momence session cookies expire within 48 hours |
| 1a | `momence_scraper8.py p 150` | Scrapes 150 pages of past classes |
| 1b | `momence_scraper8.py f 100` | Scrapes 100 pages of future classes |
| 2 | `extract_full_classes2.py` | Identifies fully-booked classes from the f-scraper output |
| 3 | `momence_class_customers_scrape_4.py` | Scrapes customer details for fully-booked classes |
| 4 | `momence_waitlist_scrape.py` | Scrapes waitlists for fully-booked classes |
| 5 | `Momence_bookings_update.py` | Downloads latest bookings CSV from Momence, appends to `master_bookings.csv` |
| 6 | `Momence_no_card_customers.py` | Updates No Card, Failed Penalty, Late Cancellation, No Show, and Total Sales datasets |
| 7 | `extract_all_classes_1.py` | Extracts all classes with at least one sign-up |
| 8 | `momence_class_customers_scrape_1 all.py` | Scrapes customer details for all active classes |

A final `Run_Momence_Chain.bat completed` entry is written to `Momence_batch_log.txt` when all steps finish.

---

## 4. Recognising and Diagnosing Errors

### 4.1 Checking Task Scheduler results

Open PowerShell and run:

```powershell
Get-ScheduledTask | Where-Object { $_.TaskName -like "*Momence*" -or $_.TaskName -like "*Ritual*" } |
    Get-ScheduledTaskInfo |
    Select-Object TaskName, LastRunTime, LastTaskResult, NextRunTime |
    Format-List
```

**Result codes to know:**

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Script exited with error |
| `267014` (0x41306) | `SCHED_S_TASK_TERMINATED` — task was stopped externally (e.g. exceeded configured time limit). Check whether the bat actually completed by reading `Momence_batch_log.txt`. |

If the **Momence scraper** task shows `267014` but `Momence_batch_log.txt` contains `Run_Momence_Chain.bat completed`, all steps finished and the termination code is benign. If the completion line is absent, review the chain log for the step that failed.

### 4.2 Reading Momence_batch_log.txt

Things to flag as problems:

- `ERROR:` prefix on any line — a step explicitly failed
- Negative record count, e.g. `-593 records added to Total Sales` — see Section 5 below
- `0 records added to No Card Customers` — normal if no customers have missing cards today
- `0 records added to Bookings from ...` — normal for the Step 5 run (that date window has already been processed); the actual bookings update is written by the 01:02 AM task
- Missing `Run_Momence_Chain.bat completed` at the end of today's entries — the chain was terminated before finishing

### 4.3 Ritual Dashboard pipeline failures

Check `Momence_data\logs\pipeline_YYYYMMDD_*.log` for today's date. Key patterns:

- `SD FAIL` — `generate_sales_tracker_data.py` failed. Most likely cause: `DATA_DIR` in the script is stale. The script now reads the path from `config\settings.json` → `momence.csv_export_path`, which is stable. If this recurs, verify that `settings.json` path is correct.
- `C3 SKIP / C4 SKIP` — GA4 and Meta collection modules not yet deployed; intentional, not an error.
- `Pipeline FAILED` in the log body but `SUCCESS` in the footer — the Windows batch wrapper (`RitualPipeline.bat`) reads the Node.js process exit code. As of 2026-03-23, `run_pipeline.js` now exits with code `1` when the pipeline fails, so this discrepancy should no longer occur.

---

## 5. The −593 Total Sales Anomaly (2026-03-19)

**What happened:** On 19 March 2026, `Momence_batch_log.txt` recorded:
```
2026-03-19 02:36:24 -593 records added to Total Sales (2026-03-14 to 2026-03-19)
```

**Root cause:** The `append_and_dedupe` function uses `keep='last'` deduplication, which replaces existing records with the freshly-downloaded versions. If Momence had deleted or reversed 593 transactions during that period (e.g. refunds processed, test bookings removed, or a data correction), the net record count after deduplication would be negative.

**Data integrity confirmed:** The `master-sales-summary.csv` currently holds 43,237 rows with continuous daily coverage from 2023-12-12 to 2026-03-23. March 14–19 shows 42–88 rows per day with no gap. No data loss occurred.

**What a negative count means in future:** A negative net count is expected when Momence retracts more records from a period than it adds. It is not itself an error, but values more negative than −100 should be investigated by comparing the downloaded weekly CSV (in `momence_downloads\Archive\`) against the previous master backup.

---

## 6. Cookie Expiry

Momence session cookies are stored in `momence_cookies.pkl`. Step 0 (`check_cookie_expiry.py`) checks expiry and creates a Google Calendar reminder if expiry is within 48 hours.

If the scraper starts redirecting to the Momence login page, cookies have expired. Regenerate them by running:

```
python momence_first_login_setup.py
```

This opens a Chrome window for manual login; cookies are saved automatically on completion.

---

## 7. Changes Made 2026-03-23

The following fixes were applied as a result of the diagnostic review on this date:

### 7.1 Ritual Dashboard — `generate_sales_tracker_data.py`
**Problem:** `DATA_DIR` and `OUTPUT_JS` were hardcoded to a VM session path (`/sessions/optimistic-sharp-feynman/mnt/...`) that does not persist between sessions, causing `SD FAIL` in the pipeline.

**Fix:** The script now derives both paths dynamically:
- `DATA_DIR` — read from `config\settings.json` → `momence.csv_export_path`
- `OUTPUT_JS` — derived from the script's own directory using `__file__`

No manual path updates are needed when sessions change.

### 7.2 Ritual Dashboard — `run_pipeline.js`
**Problem:** The Node.js runner discarded `runPipeline()`'s return value, so the process always exited with code `0` even when the pipeline failed. The Windows batch wrapper consequently always wrote `SUCCESS` in the log footer.

**Fix:** `run_pipeline.js` now checks `log.overall_status` and calls `process.exit(1)` for any non-success outcome, propagating the correct exit code to the batch wrapper.

### 7.3 Momence scraper — `Momence_bookings_update.py`
**Problem:** All failure paths called `return` from `main()`, exiting with code `0`. Silent failures (failed download, Chrome crash, append exception) were logged to `Momence_batch_log.txt` but did not surface in Task Scheduler's `LastTaskResult`.

**Fix:**
- Added `import sys` and a `_batch_log()` helper for consistent timestamped log writes
- All failure paths now call `sys.exit(1)` after logging
- A `Momence_bookings_update.py started` entry is written at the beginning of each run
- The success entry now reads `Momence_bookings_update.py completed OK — N records added to Bookings from ... to ...`

### 7.4 Momence scraper — `Run_Momence_Chain.bat`
**Problem:** No exit-code checking on any step; silent failures were invisible in the batch log.

**Fix:** After every step (0–8), the bat now:
1. Captures `%ERRORLEVEL%` immediately into `%STEP_ERR%`
2. On failure: echoes `[Step N FAILED - exit code X]` to the chain log and appends a timestamped `ERROR: Step N ... failed` line to `Momence_batch_log.txt` via PowerShell
3. On success: echoes `[Step N OK]` to the chain log
4. Appends `Run_Momence_Chain.bat completed` to `Momence_batch_log.txt` on normal exit

### 7.5 Scheduled task — pipeline log path correction
**Problem:** The `momence-log-review` scheduled task was looking for Ritual Dashboard pipeline logs at `C:\Users\markj\OneDrive\Desktop\Ritual Dashboard\data\logs\`, where no files exist. The actual logs are in `Momence_data\logs\`.

**Fix:** The scheduled task prompt was updated to point to `C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\logs`.

---

## 8. Task Scheduler — Recommended Settings Check

To prevent the `Momence scraper` task from being terminated mid-run, verify its time limit setting:

1. Open **Task Scheduler**
2. Find **Momence scraper** → right-click → **Properties** → **Settings** tab
3. Check **"Stop the task if it runs longer than"** — if set to 2 hours or less, increase to **4 hours** (the chain takes ~2 hours on busy days)
4. Confirm **"If the running task does not end when requested, force it to stop"** is appropriate for your needs
