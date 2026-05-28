@echo off
set RSO=C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Studio_Ops
set GIT=git
"%GIT%" -C "%RSO%" add app/ritual-studio-ops-v2.html docs/CHANGELOG.md docs/LESSONS_LEARNED.md
"%GIT%" -C "%RSO%" commit -m "[v2] Fix login screen: remove 737-line duplicate code block (SyntaxError pendingBookingPayload) -- Phase 10"
"%GIT%" -C "%RSO%" push origin master
"%GIT%" -C "%RSO%" log --oneline -3
