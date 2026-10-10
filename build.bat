@echo off
cd /d "%~dp0"
set PY=
where py >nul 2>nul && set PY=py
if not defined PY where python >nul 2>nul && set PY=python
if not defined PY goto nopython
echo Using: %PY%
echo.
echo Installing PyInstaller...
%PY% -m pip install pyinstaller
if errorlevel 1 goto fail
echo.
echo Building Games.exe...
%PY% -m PyInstaller --onefile --noconsole --name Games gamelist.pyw
if errorlevel 1 goto fail
echo.
echo Done. Your app is in the dist folder: dist\Games.exe
pause
exit /b 0
:nopython
echo Python was not found. Re-run the Python installer, choose Modify,
echo and make sure "Add Python to environment variables" is ticked.
pause
exit /b 1
:fail
echo Something went wrong - see the messages above.
pause
exit /b 1
