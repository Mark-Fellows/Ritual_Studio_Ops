@echo off
set RSO=C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Studio_Ops
set GIT=git
"%GIT%" -C "%RSO%" add app/index.html app/v2-relay.html docs/CHANGELOG.md docs/LESSONS_LEARNED.md
"%GIT%" -C "%RSO%" commit -m "[Portal] Fix v2 login screen: lock-free localStorage relay -- Phase 9"
"%GIT%" -C "%RSO%" push origin master
"%GIT%" -C "%RSO%" log --oneline -3
