@echo off

REM --------------------------------------------------------------------
REM Run_Momence_Retry_Past.bat
REM Scheduled at 03:00 daily.
REM
REM If today's past sessions CSV (momence_classes_p_YYYY MM DD*.csv) does
REM NOT yet exist — because the 02:00 run failed — this script re-runs
REM momence_sessions_api.py p to produce it.  If the file already exists
REM the script exits immediately without doing anything.
REM --------------------------------------------------------------------

SET LOGDIR=%~dp0Log_files
FOR /F "tokens=*" %%A IN ('powershell -NoProfile -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"') DO SET TIMESTAMP=%%A
SET LOGFILE=%LOGDIR%\Run_Momence_Retry_Past_%TIMESTAMP%.log

REM --------------------------------------------------------------------
REM Master batch log location — must match Run_Momence_Chain.bat.
REM 2026-05-18: moved out of OneDrive to a local-only folder to stop sync
REM conflicts truncating writes mid-line.
SET LOCAL_LOGDIR=C:\Users\markj\Momence_local_logs
IF EXIST "%LOCAL_LOGDIR%\" (
    SET BATCH_LOG=%LOCAL_LOGDIR%\Momence_batch_log.txt
) ELSE (
    SET BATCH_LOG=%~dp0Log_files\Momence_batch_log.txt
)
SET BATCH_LOG_HELPER=%~dp0write_batch_log.ps1
SET CHAIN_LOCK=%~dp0Log_files\Run_Momence_Chain.lock
REM Ensure Python can output Unicode characters to the log file redirect
SET PYTHONIOENCODING=utf-8

REM Ensure we are running from the correct directory
cd /d "%~dp0"

ECHO === Run_Momence_Retry_Past.bat started %DATE% %TIME% === >> "%LOGFILE%" 2>&1

REM --------------------------------------------------------------------
REM Concurrency guard: if the main chain is still running (lockfile present
REM and fresh) defer the retry by exiting cleanly.  Without this guard the
REM retry has previously launched a SECOND momence_sessions_api.py p in
REM parallel with the chain's own Step 1a, fighting it for the Momence
REM cookie.  Stale locks (>6h) are ignored so a crashed chain does not
REM permanently block the retry.
REM
REM PowerShell makes the decision; cmd then logs via the retry helper so
REM the entry can't be lost mid-write.
powershell -NoProfile -Command "if (Test-Path -LiteralPath $env:CHAIN_LOCK) { $age = (New-TimeSpan -Start (Get-Item -LiteralPath $env:CHAIN_LOCK).LastWriteTime -End (Get-Date)).TotalHours; if ($age -lt 6) { Write-Output ('lock age ' + ('{0:N1}' -f $age) + 'h'); exit 2 } else { Write-Output ('age ' + ('{0:N1}' -f $age) + 'h'); exit 1 } } else { exit 0 }" > "%TEMP%\retry_lockcheck.txt" 2>&1
SET LOCK_ERR=%ERRORLEVEL%
SET LOCK_INFO=
FOR /F "usebackq delims=" %%A IN ("%TEMP%\retry_lockcheck.txt") DO SET LOCK_INFO=%%A
DEL "%TEMP%\retry_lockcheck.txt" >nul 2>&1

IF %LOCK_ERR% EQU 2 (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "Retry 03:00: chain still running (%LOCK_INFO%) - skipping retry" >> "%LOGFILE%" 2>&1
    ECHO [Retry 03:00] Chain still running - retry deferred. >> "%LOGFILE%" 2>&1
    ECHO === Run_Momence_Retry_Past.bat finished %DATE% %TIME% === >> "%LOGFILE%" 2>&1
    EXIT /B 0
)
IF %LOCK_ERR% EQU 1 (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "Retry 03:00: ignoring stale chain lock (%LOCK_INFO%)" >> "%LOGFILE%" 2>&1
)

REM --------------------------------------------------------------------
REM Check whether today's past sessions CSV was already produced.
REM PowerShell exits with code 0 if the file exists, 1 if it is missing.
powershell -NoProfile -Command "$d = Get-Date -Format 'yyyy MM dd'; $f = Get-ChildItem -Path '.' -Filter ('momence_classes_p_' + $d + '*.csv') -ErrorAction SilentlyContinue; if ($f) { Write-Output $f.Name; exit 0 } else { exit 1 }" > "%TEMP%\retry_pastcheck.txt" 2>&1
SET NEED_RETRY=%ERRORLEVEL%
SET PAST_FILE=
FOR /F "usebackq delims=" %%A IN ("%TEMP%\retry_pastcheck.txt") DO SET PAST_FILE=%%A
DEL "%TEMP%\retry_pastcheck.txt" >nul 2>&1

IF %NEED_RETRY% EQU 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "Retry 03:00: past sessions CSV already exists (%PAST_FILE%) - no retry needed" >> "%LOGFILE%" 2>&1
    ECHO [Retry 03:00] Past sessions CSV already present - nothing to do. >> "%LOGFILE%" 2>&1
    ECHO === Run_Momence_Retry_Past.bat finished %DATE% %TIME% === >> "%LOGFILE%" 2>&1
    EXIT /B 0
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "Retry 03:00: past sessions CSV missing - re-running momence_sessions_api.py p" >> "%LOGFILE%" 2>&1

REM --------------------------------------------------------------------
REM Past sessions CSV is missing — run the API scraper now.
ECHO [Retry 03:00] Running momence_sessions_api.py p >> "%LOGFILE%" 2>&1
python momence_sessions_api.py p >> "%LOGFILE%" 2>&1
SET STEP_ERR=%ERRORLEVEL%

IF %STEP_ERR% NEQ 0 (
    ECHO [Retry 03:00 FAILED - exit code %STEP_ERR%] >> "%LOGFILE%" 2>&1
    powershell -NoProfile -ExecutionPolicy Bypass -File "%BATCH_LOG_HELPER%" -Message "ERROR: Retry 03:00 momence_sessions_api.py p failed (exit code %STEP_ERR%)" >> "%LOGFILE%" 2>&1
) ELSE (
    ECHO [Retry 03:00 OK] >> "%LOGFILE%" 2>&1
)

ECHO === Run_Momence_Retry_Past.bat finished %DATE% %TIME% === >> "%LOGFILE%" 2>&1
REM End of retry script
