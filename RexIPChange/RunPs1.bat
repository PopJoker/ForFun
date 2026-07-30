@echo off
chcp 65001 >nul
echo 正在以系統管理員權限啟動 PowerShell 進行除錯...
echo --------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Menu.ps1"
echo --------------------------------------------------
echo.
echo [除錯中] PowerShell 程式已結束。請查看上方是否有紅字錯誤！
pause