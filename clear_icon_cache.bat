@echo off
echo Clearing Windows icon cache...

taskkill /f /im explorer.exe >nul 2>&1

del /f /q "%localappdata%\IconCache.db" >nul 2>&1
del /f /q "%localappdata%\Microsoft\Windows\Explorer\iconcache*" >nul 2>&1
del /f /q "%localappdata%\Microsoft\Windows\Explorer\thumbcache*" >nul 2>&1

start explorer.exe

echo Done. Your icons will refresh in a moment.
timeout /t 2 >nul
