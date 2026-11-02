@echo off
REM Run_CleanSweep_Momence.bat  (27 Oct 2026)  CleanSweep <-> Momence, run on Mark's PC.
REM   Run_CleanSweep_Momence.bat full    copy Momence customers to Supabase, then apply queued tags (nightly)
REM   Run_CleanSweep_Momence.bat queue   apply queued Karma Yogi tags only (every 30 minutes; exits fast if none)
REM Credentials: Momence_data\.env (Momence login, Supabase service key). Nothing is stored here.
REM Log: C:\Users\markj\Momence_local_logs\CleanSweep_Momence.log ; summary lines also go to Momence_batch_log.txt
SETLOCAL
SET PYTHONIOENCODING=utf-8
SET LOGDIR=C:\Users\markj\Momence_local_logs
IF NOT EXIST "%LOGDIR%\" mkdir "%LOGDIR%"
SET LOGFILE=%LOGDIR%\CleanSweep_Momence.log
cd /d "%~dp0"
ECHO ===== %DATE% %TIME% mode=%1 >> "%LOGFILE%"
IF /I "%~1"=="full" python sync_members.py >> "%LOGFILE%" 2>&1
python process_momence_tag_queue.py >> "%LOGFILE%" 2>&1
ENDLOCAL
