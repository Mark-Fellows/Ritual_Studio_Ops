@echo off
REM Phase 6 - Teacher Applications - commit script (run on your machine)
set GIT=git
set RSO=C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Studio_Ops

"%GIT%" -C "%RSO%" add app/ritual-studio-ops-v2.html app/apply.html migrations/2026-06-01-teacher-applications.sql migrations/2026-06-01-teacher-cvs-bucket.sql docs/CHANGELOG.md docs/LESSONS_LEARNED.md docs/DOCS_INDEX.md
"%GIT%" -C "%RSO%" commit -m "[Teachers] Public teacher application intake + applicant review, import 31 applicants - Phase 6"
"%GIT%" -C "%RSO%" push origin master
"%GIT%" -C "%RSO%" log --oneline -3
pause
