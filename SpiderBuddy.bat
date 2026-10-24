@echo off
:: ============================================================================
:: 🕷️ Spider-Buddy — Desktop Companion Launcher
:: Launches Spider-Buddy quietly in the background without keeping a console open
:: ============================================================================

setlocal
cd /d "%~dp0"

:: Check Python 3.13 location where dependencies are installed, then PATH
if exist "C:\Program Files\Python313\pythonw.exe" (
    start "" "C:\Program Files\Python313\pythonw.exe" main.py
    exit /b 0
)

where pythonw.exe >nul 2>&1
if %ERRORLEVEL% equ 0 (
    start "" pythonw.exe main.py
    exit /b 0
)

:: Fallback to python
where python.exe >nul 2>&1
if %ERRORLEVEL% equ 0 (
    start "" python.exe main.py
    exit /b 0
)

echo [Spider-Buddy] Python not found in PATH or standard installation directory.
pause
exit /b 1
