@echo off
REM Install_CleanSweep_Tasks.bat  (27 Oct 2026)  Run once. Creates two Windows scheduled tasks:
REM   Ritual\CleanSweep Momence nightly  05:15 daily      copy Momence customers + apply queued tags
REM   Ritual\CleanSweep tag queue        every 30 minutes, 07:00 to 21:00   apply queued tags only
REM Re-running replaces them (/F). Remove with: schtasks /Delete /TN "Ritual\CleanSweep tag queue" /F
SET RUNNER=%~dp0Run_CleanSweep_Momence.bat
schtasks /Create /F /TN "Ritual\CleanSweep Momence nightly" /TR "\"%RUNNER%\" full" /SC DAILY /ST 05:15
schtasks /Create /F /TN "Ritual\CleanSweep tag queue" /TR "\"%RUNNER%\" queue" /SC DAILY /ST 07:00 /RI 30 /DU 0014:00
ECHO.
ECHO Done. Check them in Task Scheduler under the "Ritual" folder.
pause
