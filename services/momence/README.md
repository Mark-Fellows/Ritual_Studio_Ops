# services/momence

Momence data ingestion code, relocated here from `Momence_data/` as part of Phase 0.

**The daily scraper chain still runs from the original location** (`C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\`). This directory is the canonical source for code going forward — the original is the live running copy until Phase 3 re-pointing.

---

## What is here

### Root (services/momence/)

| File | Purpose |
|---|---|
| `momence_api_client.py` | Momence API v2 client. Authenticates with client credentials. Used by CM stage 1 and Phase 7 sync. |
| `momence_data_service.py` | Higher-level data service wrapping the API client. |
| `momence_service_client.py` | Service client utilities. |
| `config.py` | **Updated for RSO** — now reads `MOMENCE_DATA_DIR` from environment for all data file paths (CSVs, cookies, checkpoints, logs). Falls back to its own directory if env var not set. |
| `Run_Momence_Chain.bat` | Master batch orchestrator — **Phase 3 update needed** before running from this location (scripts are now in `scraper/` subdirectory; bat file still references them by flat name). |
| `Run_Chain_Heartbeat_Guard.bat` | Background watchdog launcher — Phase 3 update needed. |
| `Run_Momence_Retry_Past.bat` | Retry-past-sessions launcher — Phase 3 update needed. |
| `write_batch_log.ps1` | Retry-capable batch log appender used by the bat files. |

### scraper/ (services/momence/scraper/)

The 11-step chain scripts (the merger plan documented 7; the chain has since grown):

| Step | Script | Method |
|---|---|---|
| 0 | `check_cookie_expiry.py` | Checks Momence session cookie; alerts if expiry within 48h |
| 1a | `momence_sessions_api.py p` | Fetches past sessions via API v2 |
| 1b | `momence_sessions_api.py f` | Fetches future sessions via API v2 |
| 1c | `momence_sessions_scrape_lite.py` | Selenium — substitute teacher flag + waitlist count |
| 2 | `extract_full_classes2.py` | CSV processing — extracts fully booked classes |
| 3 | `momence_class_customers_full_api.py` | API — customer details for full classes |
| 4 | `momence_waitlist_scrape.py` | Selenium — waitlists for full classes |
| 5 | `Momence_bookings_update.py` | Selenium — master bookings CSV update |
| 6 | `Momence_no_card_customers.py` | Selenium — no-card CRM report exports |
| 7 | `extract_all_classes_1.py` | CSV processing — all future classes with signups |
| 8 | `momence_class_customers_api.py` | API — customer details for all classes |
| 9 | `momence_courses_sync.py` | API — teacher-training courses to Supabase |
| 10 | `momence_new_reports.py` | Selenium — KPI report downloads |
| 11 | `build_master_customers.py` | CSV merge — master_customers.csv refresh |
| post | `archive_old_files.py` | Archives dated files (keep 8 days, 1/week 3 months, 1/month thereafter) |
| support | `chain_heartbeat_guard.py` | Background watchdog process |
| support | `momence_teacher_utils.py` | Shared teacher lookup utilities |

### sync/ (services/momence/sync/)

**Phase 7 — empty, to be built post-cutover.**

Will contain upsert scripts for the three Supabase mirror tables:
- `sync_sessions.py` — upserts into `momence_sessions`
- `sync_members.py` — upserts into `momence_members`
- `sync_bookings.py` — upserts into `momence_bookings`
- `verify.py` — nightly row-count and sample comparison

### docs/ (services/momence/docs/)

Canonical Momence documentation (consolidated from two sources in Phase 0).

---

## Phase 3 actions required (pipeline re-pointing)

When Phase 3 re-points the chain to run from `services/momence/`:

1. **Update bat files** — change `python check_cookie_expiry.py` etc. to `python scraper\check_cookie_expiry.py` (or add `scraper/` to the Python path).

2. **Set MOMENCE_DATA_DIR** — in the `.env` file at the project root, set:
   ```
   MOMENCE_DATA_DIR=C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data
   ```
   `config.py` already reads this variable (updated in Phase 0).

3. **Update CM stage 1 import** — in `Ritual_Cover_Management/stage1/momence_teacher_sync.py`, replace:
   ```python
   sys.path.insert(0, r"C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data")
   from momence_api_client import MomenceAPIClient
   ```
   with:
   ```python
   from services.momence.momence_api_client import MomenceAPIClient
   ```

4. **Test with dry run** — run `momence_teacher_sync.py --dry-run` and confirm output matches previous run.

5. **Update Task Scheduler** — change the scheduled task to run `Run_Momence_Chain.bat` from `services/momence/` instead of the original location. Keep the original as rollback for 30 days.

---

## config.py — MOMENCE_DATA_DIR behaviour

The `config.py` in this directory has been updated from the original. Key change:

```python
# Original (in Momence_data/):
_BASE = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(_BASE, 'Log_files', ...)

# RSO copy (here):
_DATA_DIR = os.environ.get('MOMENCE_DATA_DIR', _CODE_DIR)
LOG_FILE = os.path.join(_DATA_DIR, 'Log_files', ...)
```

This means:
- **With `MOMENCE_DATA_DIR` set** → all data paths resolve to the original OneDrive folder ✓
- **Without `MOMENCE_DATA_DIR`** → falls back to this directory (same behaviour as original) ✓
- **Original `config.py` in Momence_data/** → unchanged; daily chain unaffected ✓
