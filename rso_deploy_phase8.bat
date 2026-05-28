@echo off
set RSO=C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Studio_Ops
set WRANGLER_HOME=%USERPROFILE%\AppData\Roaming\xdg.config
pushd "%RSO%"
npx wrangler pages deploy app/ --project-name ritual-studio-ops
popd
