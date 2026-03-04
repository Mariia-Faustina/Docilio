@echo off
chcp 65001 >nul
title Docilio Build

cd /d "%~dp0"

echo.
echo  Docilio Build Tool
echo  ------------------
echo.
echo  Installing dependencies...

python -m pip install pyinstaller --quiet

echo  Writing UAC manifest...

echo ^<?xml version="1.0" encoding="UTF-8" standalone="yes"?^>                          > manifest.xml
echo ^<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0"^>        >> manifest.xml
echo   ^<trustInfo xmlns="urn:schemas-microsoft-com:asm.v3"^>                           >> manifest.xml
echo     ^<security^>                                                                    >> manifest.xml
echo       ^<requestedPrivileges^>                                                       >> manifest.xml
echo         ^<requestedExecutionLevel level="requireAdministrator" uiAccess="false"/^> >> manifest.xml
echo       ^</requestedPrivileges^>                                                      >> manifest.xml
echo     ^</security^>                                                                   >> manifest.xml
echo   ^</trustInfo^>                                                                    >> manifest.xml
echo ^</assembly^>                                                                       >> manifest.xml

echo  Building - this may take a minute...
echo.

python -m PyInstaller --onedir --windowed --name Docilio --icon=Docilio.ico ^
    --manifest manifest.xml ^
    --hidden-import PIL ^
    --hidden-import PIL._imagingtk ^
    --hidden-import mss ^
    --hidden-import keyboard ^
    --hidden-import openpyxl ^
    --hidden-import docx ^
    --hidden-import reportlab ^
    --hidden-import pptx ^
    --add-data "settings.py;." ^
    --add-data "file_manager.py;." ^
    --add-data "screenshot.py;." ^
    --add-data "exporter.py;." ^
    --add-data "comment_popup.py;." ^
    --add-data "stitch_tool.py;." ^
    --add-data "compare_tool.py;." ^
    --add-data "toast.py;." ^
    --add-data "ui.py;." ^
    --add-data "Docilio.ico;." ^
    main.py

del manifest.xml >nul 2>&1

echo.
if exist dist\Docilio\Docilio.exe (
    echo  Build complete. Docilio.exe is in the dist\Docilio\ folder.
    echo.

    copy /y Docilio.ico dist\Docilio\Docilio.ico >nul

    echo  Creating desktop shortcut...
    powershell -NoProfile -Command ^
        "$ws = New-Object -ComObject WScript.Shell;" ^
        "$s = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Docilio.lnk');" ^
        "$s.TargetPath = '%~dp0dist\Docilio\Docilio.exe';" ^
        "$s.IconLocation = '%~dp0dist\Docilio\Docilio.exe';" ^
        "$s.WorkingDirectory = '%~dp0dist\Docilio';" ^
        "$s.Description = 'Docilio - Screenshot Documentation Tool';" ^
        "$s.Save()"

    if exist "%USERPROFILE%\Desktop\Docilio.lnk" (
        echo  Desktop shortcut created.
    ) else (
        echo  Could not create shortcut automatically.
        echo  Right-click dist\Docilio\Docilio.exe and choose Send to ^> Desktop to do it manually.
    )

    echo.
    echo  Note: Windows may show a security prompt on first launch.
    echo  This is expected - the Alt+X hotkey requires elevated permissions.
    echo.
) else (
    echo  Build failed. Check the output above for details.
    echo.
)

pause
