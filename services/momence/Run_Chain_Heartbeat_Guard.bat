@echo off
REM --------------------------------------------------------------------
REM Run_Chain_Heartbeat_Guard.bat
REM
REM Schedules-friendly wrapper that calls chain_heartbeat_guard.py and
REM records the result. Register in Task Scheduler with the trigger:
REM   Hourly, between 04:00 and 23:00 local time, repeat indefinitely.
REM --------------------------------------------------------------------
SET SCRIPT_DIR=%~dp0
SET LOGDIR=%SCRIPT_DIR%Log_files
SET TS=%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%
SET TS=%TS: =0%
SET GUARDLOG=%LOGDIR%\heartbeat_guard_%TS%.log

cd /d "%SCRIPT_DIR%"

python chain_heartbeat_guard.py %* > "%GUARDLOG%" 2>&1
SET RC=%ERRORLEVEL%

IF %RC% NEQ 0 (
    ECHO [%date% %time%] Guard returned rc=%RC% — see %GUARDLOG% 1>&2
)
EXIT /B %RC%
