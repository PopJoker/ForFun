@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ==============================
:: 設定
:: ==============================
set "ROOT_DIR=C:\Users\G11407007\Desktop\pop"
set "DISCORD_WEBHOOK=https://discordapp.com/api/webhooks/1443135453837529098/apii1DGNJeeGhew3GiIatGEBCanLcR2wfMRI-8UyNCRbJeyxaHCOPUqinbNu_lfVnRvk"
set "LOG_DIR=%ROOT_DIR%\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: 取得日期時間
for /f "delims=" %%a in ('powershell -NoProfile -Command "Get-Date -Format \"yyyy-MM-dd\""' ) do set "TODAY=%%a"
for /f "delims=" %%a in ('powershell -NoProfile -Command "Get-Date -Format \"HH:mm:ss\""' ) do set "NOW=%%a"

set "LOG_FILE=%LOG_DIR%\%TODAY%.log"
set "ERR_FILE=%LOG_DIR%\%TODAY%-error.log"
set "COMMIT_MSG=%TODAY%"

echo [%TODAY% %NOW%] ===== 開始執行 Git 批次 ===== >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

:: ==============================
:: 遍歷子資料夾
:: ==============================
for /d %%D in ("%ROOT_DIR%\*") do (
    if exist "%%D\.git" (
        echo -----------------------------
        echo 進入 Git 專案: %%D
        echo [%TODAY% %NOW%] 進入 Git 專案: %%D >> "%LOG_FILE%"

        pushd "%%D"

        :: 判斷是否有未提交變更
        git diff --quiet
        if errorlevel 1 (
            set "HAS_CHANGE=1"
        ) else (
            git diff --cached --quiet
            if errorlevel 1 (
                set "HAS_CHANGE=1"
            ) else (
                set "HAS_CHANGE=0"
            )
        )

        :: 取得 branch
        for /f "delims=" %%B in ('git symbolic-ref --short HEAD 2^>nul') do set "BRANCH=%%B"
        if not defined BRANCH set "BRANCH=main"

        if !HAS_CHANGE! EQU 1 (
            git add . >> "%LOG_FILE%" 2>>"%ERR_FILE%"
            git commit -m "%COMMIT_MSG%" >> "%LOG_FILE%" 2>>"%ERR_FILE%"
            git push origin "!BRANCH!" >> "%LOG_FILE%" 2>>"%ERR_FILE%"
            if errorlevel 1 (
                set "STATUS=FAILED"
            ) else (
                set "STATUS=SUCCESS"
            )
        ) else (
            set "STATUS=NO CHANGE"
        )

        :: 發送 Discord
        powershell -NoProfile -ExecutionPolicy Bypass -Command ^
            "$repo='%%~nxD'; $branch='!BRANCH!'; $status='!STATUS!'; $time='%TODAY% %NOW%';" ^
            "$msg=\"**Repo:** $repo`n**Branch:** $branch`n**Status:** $status`n**Time:** $time\";" ^
            "$payload=@{username='AutoUp'; content=$msg}; Invoke-RestMethod -Uri '%DISCORD_WEBHOOK%' -Method Post -ContentType 'application/json' -Body ($payload | ConvertTo-Json -Compress)"

        popd
        echo. >> "%LOG_FILE%"
    )
)

echo [%TODAY% %NOW%] ===== 所有專案完成 ===== >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

exit /b
