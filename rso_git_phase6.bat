@echo off
set RSO=C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Studio_Ops
set GIT=git
"%GIT%" -C "%RSO%" add app/index.html docs/CHANGELOG.md docs/LESSONS_LEARNED.md
"%GIT%" -C "%RSO%" commit -m "[Portal] Fix Cover Dashboard and Teacher Portal tiles showing login screen -- Phase 6"
"%GIT%" -C "%RSO%" push origin master
"%GIT%" -C "%RSO%" log --oneline -3
