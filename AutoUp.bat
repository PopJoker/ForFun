@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: 設定要掃描的根目錄
set "ROOT_DIR=C:\Users\G11407007\Desktop\Flutter\15kW_NEWAPP_API"

:: 輸入 commit 訊息
set /p COMMIT_MSG=請輸入 commit 訊息: 

:: 遍歷子資料夾
for /d %%D in ("%ROOT_DIR%\*") do (
    if exist "%%D\.git" (
        echo -----------------------------
        echo 進入 Git 專案: %%D
        cd "%%D"

        :: 檢查是否有變更
        git status --porcelain > temp_status.txt
        set /p FILE_CHANGED=<temp_status.txt
        if defined FILE_CHANGED (
            echo 有變更，開始 commit & push
            git add .
            git commit -m "!COMMIT_MSG!"

            :: 取得目前分支
            for /f "delims=" %%B in ('git symbolic-ref --short HEAD') do set BRANCH=%%B

            :: 嘗試 push main，失敗再 push master
            git push origin !BRANCH! || git push origin master || git push origin main
        ) else (
            echo 無變更，跳過
        )
        del temp_status.txt
    )
)
echo 完成所有專案操作
pause
