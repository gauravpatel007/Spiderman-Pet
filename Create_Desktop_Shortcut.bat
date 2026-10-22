@echo off
:: ============================================================================
:: 🕷️ Spider-Buddy — One-Click Windows Desktop Shortcut Creator
:: ============================================================================

cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\set_live_desktop_shortcut.ps1"
if %ERRORLEVEL% equ 0 (
    echo.
    echo Spider-Buddy shortcut has been placed on your Windows Desktop (Silent / No-Terminal)!
) else (
    echo.
    echo Failed to create desktop shortcut.
)
pause
