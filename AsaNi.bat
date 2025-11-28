@echo off
title NI-VISA DLL Checker
color 0A
echo ================================================
echo Checking for niVisa.dll every 5 seconds
echo Press Ctrl+C to stop
echo ================================================

:loop
echo.
echo ================================================
echo Check time: %date% %time%
echo --------------------------------
where niVisa.dll >nul 2>&1
if %errorlevel%==0 (
    echo [OK] niVisa.dll found!
    where niVisa.dll
) else (
    echo [WARNING] niVisa.dll not found!
    echo Please make sure NI-VISA Runtime is installed or PATH is set correctly.
)
echo Next check in 5 seconds...
timeout /t 5 /nobreak >nul
goto loop
