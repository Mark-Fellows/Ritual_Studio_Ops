@echo off

REM --------------------------------------------------------------------
REM Redirect all stdout and stderr to a dated log file in Log_files\
REM This captures output from every step below.
REM
REM Use PowerShell to generate an unambiguous ISO timestamp for the log
REM filename — avoids locale-dependent %DATE% parsing and filename collisions
REM (the old %DATE:~n,m% approach produced indistinguishable names for
REM different Saturdays whose day number shared the same tens digit).
SET LOGDIR=%~dp0Log_files
FOR /F "tokens=*" %%A IN ('powershell -NoProfile -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"') DO SET TIMESTAMP=%%A
SET LOGFILE=%LOGDIR%\Run_Momence_Chain_%TIMESTAMP%.log

REM --------------------------------------------------------------------
REM Master batch log location.
REM
REM 2026-05-18: moved out of OneDrive to a local-only folder. Sync conflicts
REM on the previous path (...\Momence_data\Log_files\Momence_batch_log.txt)
REM were truncating PowerShell appends mid-line and silently swallowing
REM subsequent writes from every writer. The local folder is created by
REM hand once; if it ever goes missing we fall back to the old in-tree
REM location so the chain still produces SOMETHING auditable.
SET LOCAL_LOGDIR=C:\Users\markj\Momence_local_logs
IF EXIST "%LOCAL_LOGDIR%\" (
    SET BATCH_LOG=%LOCAL_LOGDIR%\Momence_batch_log.txt
) ELSE (
    SET BATCH_LOG=%~dp0Log_files\Momence_batch_log.txt
)

REM Retry-capable batch-log appender. Replaces every inline Add-Content
REM in this file with a 6×5s retry loop so transient OneDrive / AV locks
REM no longer truncate writes. See write_batch_log.ps1.
SET BATCH_LOG_HELPER=%~dp0write_batch_log.ps1

REM Ensure Python can output Unicode characters to the log file redirect
SET PYTHONIOENCODING=utf-8

REM Lockfile path — used to coordinate with Run_Momence_Retry_Past.bat so the
REM 03:00 retry never starts while the main chain is still running its own
REM Step 1a (past sessions).  Stale lockfiles older than 6 hours are reclaimed.
SET CHAIN_LOCK=%~dp0Log_files\Run_Momence_Chain.lock

REM Ensure we are running from the correct directory
cd /d "%~dp0"

REM --------------------------------------------------------------------
REM Refuse to start if another chain is already running.  This guards
REM against accidental double-launch (manual run while the 02:00
REM scheduled task is still going) which previously left two concurrent
REM Selenium / API sessions competing for the same Momence cookie.
REM Stale locks (file older than 6 hours) are reclaimed automatically.
REM
REM PowerShell makes the decision and outputs the age info; cmd then
REM logs through the retry helper so the entry can't be lost mid-write.
powershell -NoProfile -Command "if (Test-Path -LiteralPath $env:CHAIN_LOCK) { $age = (New-TimeSpan -Start (Get-Item -LiteralPath $env:CHAIN_LOCK).LastWriteTime -End (Get-Date)).TotalHours; if ($age -lt 6) { Write-Output ('lockfile age ' + ('{0:N1}' -f $age) + 'h'); exit 2 } else { Write-Output ('age ' + ('{0:N1}' -f $age) + 'h'); Remove-Item -LiteralPath $env:CHAIN_LOCK -Force; exit 1 } } else { exit 0 }" > "%TEMP%\chain_lockcheck.txt" 2>&1
SET LOCK_ERR=%ERRORLEVEL%
SET LOCK_INFO=
FOR /F "usebackq delims=" %%A IN ("%TEMP%\chain_lockcheck.txt") DO SET LOCK_INFO=%%A
DEL "%TEMP%\chain_lockcheck.txt" >nul 2>&1

IF %LOCK_ERR% EQU 2 (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "SKIPPED: Run_Momence_Chain.bat - another chain run is already active (%LOCK_INFO%)" >> "%LOGFILE%" 2>&1
    ECHO [Concurrency guard] Another chain is already running - exiting. >> "%LOGFILE%" 2>&1
    EXIT /B 0
)
IF %LOCK_ERR% EQU 1 (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "Run_Momence_Chain.bat - clearing stale lockfile (%LOCK_INFO%)" >> "%LOGFILE%" 2>&1
)

REM Create lockfile (records PID and start timestamp).
powershell -NoProfile -Command "Set-Content -LiteralPath $env:CHAIN_LOCK -Encoding utf8 -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' PID=' + $PID)"

ECHO === Run_Momence_Chain.bat started %DATE% %TIME% === >> "%LOGFILE%" 2>&1
REM Write a guaranteed start entry to the batch log directly from the bat file.
REM This appears even if every Python script's own append_to_batch_log fails.
powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "Run_Momence_Chain.bat started" >> "%LOGFILE%" 2>&1

REM --------------------------------------------------------------------
REM Launch background watchdog: emits a heartbeat to the master batch log
REM every 5 minutes while the chain lockfile exists, capped at 4 hours.
REM If cmd.exe dies mid-chain, the watchdog process survives and keeps
REM heartbeating until the lockfile is removed or the 4h cap is hit -
REM the gap between the last per-step HEARTBEAT and the next WATCHDOG
REM line reveals exactly when cmd.exe terminated.
ECHO [Watchdog] Starting background heartbeat (5 min interval, 4h cap) >> "%LOGFILE%" 2>&1
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "$start = Get-Date; $helper = $env:BATCH_LOG_HELPER; while ((Test-Path -LiteralPath $env:CHAIN_LOCK) -and ((New-TimeSpan -Start $start -End (Get-Date)).TotalMinutes -lt 240)) { Start-Sleep -Seconds 300; if (Test-Path -LiteralPath $env:CHAIN_LOCK) { $msg = 'WATCHDOG: chain alive (uptime ' + [int]((New-TimeSpan -Start $start -End (Get-Date)).TotalMinutes) + ' min)'; & $helper -Message $msg } }"

REM --------------------------------------------------------------------
REM Step 0: Check Momence session cookie expiry — creates a Google Calendar
REM         reminder if the cookie expires within the next 48 hours.
REM         Still required: Steps 4, 5, 6 continue to use Selenium/cookies.
ECHO [Step 0] check_cookie_expiry.py >> "%LOGFILE%" 2>&1
python check_cookie_expiry.py >> "%LOGFILE%" 2>&1
SET STEP_ERR=%ERRORLEVEL%
powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "HEARTBEAT: Step 0 returned (rc=%STEP_ERR%)" >> "%LOGFILE%" 2>&1
IF %STEP_ERR% NEQ 0 (
    ECHO [Step 0 FAILED - exit code %STEP_ERR%] >> "%LOGFILE%" 2>&1
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "ERROR: Step 0 check_cookie_expiry.py failed (exit code %STEP_ERR%)" >> "%LOGFILE%" 2>&1
) ELSE (
    ECHO [Step 0 OK] >> "%LOGFILE%" 2>&1
)

REM --------------------------------------------------------------------
REM Step 1: Fetch Momence class schedule via the v2 API.
REM         Replaces momence_scraper8.py (Selenium, ~30 min).
REM         Uses date-range queries instead of paging through the UI.
REM         Produces identical output filenames so downstream steps are unchanged.
REM Step 1a: Past sessions fetch. No external watchdog needed -- momence_sessions_api.py
REM now detects ascending API sort order and binary-searches for the start page,
REM keeping runtime to ~20 min regardless of sort direction.
ECHO [Step 1a] momence_sessions_api.py p >> "%LOGFILE%" 2>&1
python momence_sessions_api.py p >> "%LOGFILE%" 2>&1
SET STEP_ERR=%ERRORLEVEL%
powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "HEARTBEAT: Step 1a returned (rc=%STEP_ERR%)" >> "%LOGFILE%" 2>&1
IF %STEP_ERR% NEQ 0 (
    ECHO [Step 1a FAILED - exit code %STEP_ERR%] >> "%LOGFILE%" 2>&1
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "ERROR: Step 1a momence_sessions_api.py p failed (exit code %STEP_ERR%)" >> "%LOGFILE%" 2>&1
) ELSE (
    ECHO [Step 1a OK] >> "%LOGFILE%" 2>&1
)

REM Step 1a completeness check - flag MISSING OUTPUT if no past sessions CSV was produced today
powershell -NoProfile -Command "$d = Get-Date -Format 'yyyy MM dd'; $f = Get-ChildItem -Path '.' -Filter ('momence_classes_p_' + $d + '*.csv') -ErrorAction SilentlyContinue; if (-not $f) { Write-Output ('MISSING ' + $d) } else { Write-Output ('PRESENT ' + $f.Name) }" > "%TEMP%\chain_past_check.txt" 2>&1
SET PAST_CHECK=
FOR /F "usebackq delims=" %%A IN ("%TEMP%\chain_past_check.txt") DO SET PAST_CHECK=%%A
DEL "%TEMP%\chain_past_check.txt" >nul 2>&1
ECHO Past sessions completeness: %PAST_CHECK% >> "%LOGFILE%" 2>&1
ECHO %PAST_CHECK% | findstr /B "MISSING" >nul && (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "MISSING OUTPUT: momence_classes_p - past sessions data absent for today" >> "%LOGFILE%" 2>&1
)

ECHO [Step 1b] momence_sessions_api.py f >> "%LOGFILE%" 2>&1
python momence_sessions_api.py f >> "%LOGFILE%" 2>&1
SET STEP_ERR=%ERRORLEVEL%
powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "HEARTBEAT: Step 1b returned (rc=%STEP_ERR%)" >> "%LOGFILE%" 2>&1
IF %STEP_ERR% NEQ 0 (
    ECHO [Step 1b FAILED - exit code %STEP_ERR%] >> "%LOGFILE%" 2>&1
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "ERROR: Step 1b momence_sessions_api.py f failed (exit code %STEP_ERR%)" >> "%LOGFILE%" 2>&1
) ELSE (
    ECHO [Step 1b OK] >> "%LOGFILE%" 2>&1
)

REM --------------------------------------------------------------------
REM Step 1c: Scrape sessions list for substitute teacher flag and waitlist count.
REM          Selenium — reads the sessions list page (NOT per-class detail pages).
REM          Covers last 30 days past + next 60 days future.  ~5-8 minutes.
REM          Non-fatal: pipeline continues if this step fails.
ECHO [Step 1c] momence_sessions_scrape_lite.py >> "%LOGFILE%" 2>&1
python momence_sessions_scrape_lite.py >> "%LOGFILE%" 2>&1
SET STEP_ERR=%ERRORLEVEL%
powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "HEARTBEAT: Step 1c returned (rc=%STEP_ERR%)" >> "%LOGFILE%" 2>&1
IF %STEP_ERR% NEQ 0 (
    ECHO [Step 1c WARN - exit code %STEP_ERR%] Lite scraper failed - substitute/waitlist will be absent this run >> "%LOGFILE%" 2>&1
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "WARN: Step 1c momence_sessions_scrape_lite.py failed (non-fatal)" >> "%LOGFILE%" 2>&1
) ELSE (
    ECHO [Step 1c OK] >> "%LOGFILE%" 2>&1
)

REM --------------------------------------------------------------------
REM Step 2: Extract fully booked classes from most recent future classes file.
REM         Unchanged — pure CSV processing, no Selenium.
ECHO [Step 2] extract_full_classes2.py >> "%LOGFILE%" 2>&1
python extract_full_classes2.py >> "%LOGFILE%" 2>&1
SET STEP_ERR=%ERRORLEVEL%
powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "HEARTBEAT: Step 2 returned (rc=%STEP_ERR%)" >> "%LOGFILE%" 2>&1
IF %STEP_ERR% NEQ 0 (
    ECHO [Step 2 FAILED - exit code %STEP_ERR%] >> "%LOGFILE%" 2>&1
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "ERROR: Step 2 extract_full_classes2.py failed (exit code %STEP_ERR%)" >> "%LOGFILE%" 2>&1
) ELSE (
    ECHO [Step 2 OK] >> "%LOGFILE%" 2>&1
)

REM --------------------------------------------------------------------
REM Step 3: Fetch customer details for each fully booked class via API.
REM         Replaces momence_class_customers_scrape_4.py (Selenium).
REM         Reads momence_full_classes_*.csv; writes Momence_class_customers_combined.csv.
ECHO [Step 3] momence_class_customers_full_api.py >> "%LOGFILE%" 2>&1
python momence_class_customers_full_api.py >> "%LOGFILE%" 2>&1
SET STEP_ERR=%ERRORLEVEL%
powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "HEARTBEAT: Step 3 returned (rc=%STEP_ERR%)" >> "%LOGFILE%" 2>&1
IF %STEP_ERR% NEQ 0 (
    ECHO [Step 3 FAILED - exit code %STEP_ERR%] >> "%LOGFILE%" 2>&1
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "ERROR: Step 3 momence_class_customers_full_api.py failed (exit code %STEP_ERR%)" >> "%LOGFILE%" 2>&1
) ELSE (
    ECHO [Step 3 OK] >> "%LOGFILE%" 2>&1
)

REM --------------------------------------------------------------------
REM Step 4: Scrape waitlists for each full class found in Step 2.
REM         Selenium — no API waitlist endpoint available.
REM         Uses the same full classes file as Step 3.
REM         Output: Momence_waitlist_combined.csv (one row per waitlisted person).
ECHO [Step 4] momence_waitlist_scrape.py >> "%LOGFILE%" 2>&1
python momence_waitlist_scrape.py >> "%LOGFILE%" 2>&1
SET STEP_ERR=%ERRORLEVEL%
powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "HEARTBEAT: Step 4 returned (rc=%STEP_ERR%)" >> "%LOGFILE%" 2>&1
IF %STEP_ERR% NEQ 0 (
    ECHO [Step 4 FAILED - exit code %STEP_ERR%] >> "%LOGFILE%" 2>&1
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "ERROR: Step 4 momence_waitlist_scrape.py failed (exit code %STEP_ERR%)" >> "%LOGFILE%" 2>&1
) ELSE (
    ECHO [Step 4 OK] >> "%LOGFILE%" 2>&1
)

REM --------------------------------------------------------------------
REM Step 5: Update master bookings CSV with latest data from Momence.
REM         Selenium — API lacks Payment Method, Sale Value and other report fields.
ECHO [Step 5] Momence_bookings_update.py >> "%LOGFILE%" 2>&1
python Momence_bookings_update.py >> "%LOGFILE%" 2>&1
SET STEP_ERR=%ERRORLEVEL%
powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "HEARTBEAT: Step 5 returned (rc=%STEP_ERR%)" >> "%LOGFILE%" 2>&1
IF %STEP_ERR% NEQ 0 (
    ECHO [Step 5 FAILED - exit code %STEP_ERR%] >> "%LOGFILE%" 2>&1
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "ERROR: Step 5 Momence_bookings_update.py failed (exit code %STEP_ERR%)" >> "%LOGFILE%" 2>&1
) ELSE (
    ECHO [Step 5 OK] >> "%LOGFILE%" 2>&1
)

REM --------------------------------------------------------------------
REM Step 6: Download and process 'No Card' customers and other CRM reports.
REM         Selenium — no API equivalent for these six CRM report exports.
ECHO [Step 6] Momence_no_card_customers.py >> "%LOGFILE%" 2>&1
python Momence_no_card_customers.py >> "%LOGFILE%" 2>&1
SET STEP_ERR=%ERRORLEVEL%
powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "HEARTBEAT: Step 6 returned (rc=%STEP_ERR%)" >> "%LOGFILE%" 2>&1
IF %STEP_ERR% NEQ 0 (
    ECHO [Step 6 FAILED - exit code %STEP_ERR%] >> "%LOGFILE%" 2>&1
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "ERROR: Step 6 Momence_no_card_customers.py failed (exit code %STEP_ERR%)" >> "%LOGFILE%" 2>&1
) ELSE (
    ECHO [Step 6 OK] >> "%LOGFILE%" 2>&1
)

REM --------------------------------------------------------------------
REM Step 7: Extract all future classes with signups from most recent f file.
REM         Unchanged — pure CSV processing, no Selenium.
ECHO [Step 7] extract_all_classes_1.py >> "%LOGFILE%" 2>&1
python extract_all_classes_1.py >> "%LOGFILE%" 2>&1
SET STEP_ERR=%ERRORLEVEL%
powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "HEARTBEAT: Step 7 returned (rc=%STEP_ERR%)" >> "%LOGFILE%" 2>&1
IF %STEP_ERR% NEQ 0 (
    ECHO [Step 7 FAILED - exit code %STEP_ERR%] >> "%LOGFILE%" 2>&1
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "ERROR: Step 7 extract_all_classes_1.py failed (exit code %STEP_ERR%)" >> "%LOGFILE%" 2>&1
) ELSE (
    ECHO [Step 7 OK] >> "%LOGFILE%" 2>&1
)

REM --------------------------------------------------------------------
REM Step 8: Fetch customer details for ALL classes with signups via API.
REM         Replaces momence_class_customers_scrape_1 all.py (Selenium, 60-80 min).
REM         Reads momence_all_classes_*.csv; writes Momence_class_customers_combined.csv.
ECHO [Step 8] momence_class_customers_api.py >> "%LOGFILE%" 2>&1
python momence_class_customers_api.py >> "%LOGFILE%" 2>&1
SET STEP_ERR=%ERRORLEVEL%
powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "HEARTBEAT: Step 8 returned (rc=%STEP_ERR%)" >> "%LOGFILE%" 2>&1
IF %STEP_ERR% NEQ 0 (
    ECHO [Step 8 FAILED - exit code %STEP_ERR%] >> "%LOGFILE%" 2>&1
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "ERROR: Step 8 momence_class_customers_api.py failed (exit code %STEP_ERR%)" >> "%LOGFILE%" 2>&1
) ELSE (
    ECHO [Step 8 OK] >> "%LOGFILE%" 2>&1
)

REM --------------------------------------------------------------------
REM Step 9: Sync teacher-training courses and trainee enrolments to Supabase.
REM         API-based — reads the latest momence_classes_f_*.csv to identify
REM         training courses by name keyword, fetches bookings per session,
REM         and upserts into training_courses / trainee_enrollments / teachers.
ECHO [Step 9] momence_courses_sync.py >> "%LOGFILE%" 2>&1
python momence_courses_sync.py >> "%LOGFILE%" 2>&1
SET STEP_ERR=%ERRORLEVEL%
powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "HEARTBEAT: Step 9 returned (rc=%STEP_ERR%)" >> "%LOGFILE%" 2>&1
IF %STEP_ERR% NEQ 0 (
    ECHO [Step 9 FAILED - exit code %STEP_ERR%] >> "%LOGFILE%" 2>&1
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "ERROR: Step 9 momence_courses_sync.py failed (exit code %STEP_ERR%)" >> "%LOGFILE%" 2>&1
) ELSE (
    ECHO [Step 9 OK] >> "%LOGFILE%" 2>&1
)

REM --------------------------------------------------------------------
REM Step 10: Download Momence KPI reports including Class Occupancy.
REM          Selenium — downloads 7 reports, accumulates into master CSVs.
REM          Provides teacher names, check-ins, no-shows, late cancellations.
REM          Non-fatal: pipeline continues if this step fails.
ECHO [Step 10] momence_new_reports.py >> "%LOGFILE%" 2>&1
python momence_new_reports.py >> "%LOGFILE%" 2>&1
SET STEP_ERR=%ERRORLEVEL%
powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "HEARTBEAT: Step 10 returned (rc=%STEP_ERR%)" >> "%LOGFILE%" 2>&1
IF %STEP_ERR% NEQ 0 (
    ECHO [Step 10 WARN - exit code %STEP_ERR%] New reports failed - occupancy/teacher enrichment may be stale >> "%LOGFILE%" 2>&1
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "WARN: Step 10 momence_new_reports.py failed (non-fatal)" >> "%LOGFILE%" 2>&1
) ELSE (
    ECHO [Step 10 OK] >> "%LOGFILE%" 2>&1
)

REM --------------------------------------------------------------------
REM Step 11: Refresh master_customers.csv (member name lookup for the dashboard
REM          per-class popup). Pure data merge from CSVs already produced by
REM          Steps 6 and 10 - no Selenium, no API call, runs in seconds.
REM          Non-fatal: chain continues if this step fails.
ECHO [Step 11] build_master_customers.py >> "%LOGFILE%" 2>&1
python build_master_customers.py >> "%LOGFILE%" 2>&1
SET STEP_ERR=%ERRORLEVEL%
powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "HEARTBEAT: Step 11 returned (rc=%STEP_ERR%)" >> "%LOGFILE%" 2>&1
IF %STEP_ERR% NEQ 0 (
    ECHO [Step 11 WARN - exit code %STEP_ERR%] master_customers refresh failed - popup may show emails instead of names >> "%LOGFILE%" 2>&1
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "WARN: Step 11 build_master_customers.py failed (non-fatal)" >> "%LOGFILE%" 2>&1
) ELSE (
    ECHO [Step 11 OK] >> "%LOGFILE%" 2>&1
)

ECHO === Run_Momence_Chain.bat finished %DATE% %TIME% === >> "%LOGFILE%" 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "Run_Momence_Chain.bat completed" >> "%LOGFILE%" 2>&1

REM --------------------------------------------------------------------
REM Copy latest Momence_classes_f*.csv to Ritual Cover Management data folder
REM Find the most recent future classes file and copy to fixed destination
ECHO [POSTPROCESSING] Copying latest Momence_classes_f*.csv to Ritual_Cover_Management >> "%LOGFILE%" 2>&1

REM PowerShell finds + copies; outcome message goes through the retry helper.
powershell -NoProfile -Command "$src = Get-ChildItem -Path '.' -Filter 'momence_classes_f*.csv' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1; if ($src) { $dest = 'C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Cover_Management\data\momence_classes_future.csv'; try { Copy-Item -LiteralPath $src.FullName -Destination $dest -Force; Write-Output ('Copied ' + $src.Name + ' to momence_classes_future.csv') } catch { Write-Output ('ERROR copying file: ' + $_.Exception.Message) } } else { Write-Output 'WARNING: No momence_classes_f*.csv file found to copy' }" > "%TEMP%\chain_postcopy.txt" 2>&1
SET COPY_MSG=
FOR /F "usebackq delims=" %%A IN ("%TEMP%\chain_postcopy.txt") DO SET COPY_MSG=%%A
DEL "%TEMP%\chain_postcopy.txt" >nul 2>&1
ECHO %COPY_MSG% >> "%LOGFILE%" 2>&1
IF DEFINED COPY_MSG (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "%COPY_MSG%" >> "%LOGFILE%" 2>&1
)

REM --------------------------------------------------------------------
REM Archive old dated files (keeps last 8 days, 1/week for 3 months, 1/month thereafter)
ECHO [POSTPROCESSING] Archiving old files >> "%LOGFILE%" 2>&1
python archive_old_files.py >> "%LOGFILE%" 2>&1
SET STEP_ERR=%ERRORLEVEL%
IF %STEP_ERR% NEQ 0 (
    ECHO [ARCHIVE WARN - exit code %STEP_ERR%] archive_old_files.py reported an error >> "%LOGFILE%" 2>&1
) ELSE (
    ECHO [ARCHIVE OK] >> "%LOGFILE%" 2>&1
)

REM Release the concurrency lockfile so Run_Momence_Retry_Past.bat can run.
powershell -NoProfile -Command "if (Test-Path -LiteralPath $env:CHAIN_LOCK) { Remove-Item -LiteralPath $env:CHAIN_LOCK -Force }"

REM End of chain
