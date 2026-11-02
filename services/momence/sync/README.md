# services/momence/sync — CleanSweep Momence scripts (27 Oct 2026)

These scripts run on Mark's PC so the Momence login never leaves it (CleanSweep decision D1 = B).

| File | What it does |
|---|---|
| `sync_members.py` | Copies Momence customers (member ID, name, email, tags; no phone numbers) into Supabase `public.momence_members`. The CleanSweep person search reads this table. Records each run in `momence_sync_runs`. About 300 API calls, ~4 minutes. |
| `process_momence_tag_queue.py` | Applies pending rows in `public.momence_tag_requests` (Karma Yogi tag for new cleaners). Leaves a request pending, with a note, while the tag does not exist in Momence. Exits immediately when the queue is empty. |
| `cs_common.py` | Shared helpers. Reads credentials from `Momence_data\.env` (override with `MOMENCE_DATA_DIR` or `MOMENCE_ENV_FILE`) and signs in with `..\momence_api_client.py`. |
| `Run_CleanSweep_Momence.bat` | `full` = copy + queue (nightly); `queue` = queue only (every 30 minutes). Logs to `C:\Users\markj\Momence_local_logs\CleanSweep_Momence.log`. |
| `Install_CleanSweep_Tasks.bat` | Run once to create the two scheduled tasks (05:15 nightly; every 30 minutes 07:00–21:00). |

Both scripts accept `--dry-run`. First run: `python sync_members.py --dry-run`, then `python process_momence_tag_queue.py --dry-run`.

These run separately from the nightly Momence chain (`Momence_data\Run_Momence_Chain.bat`), which is unchanged.
