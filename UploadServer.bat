@echo off
REM =====================================================
REM 一鍵將本地 Windows gus-server-home 上傳到伺服器 /home/gus-server
REM 支援跳板機、增量同步，並自動設置權限
REM =====================================================

REM 本地資料夾
set "LOCAL_PATH=C:\Users\G11407007\Downloads\gus-server-home\"

REM 伺服器暫存目錄
set "REMOTE_TMP=/tmp/gus-server-upload/"

REM 跳板機設定
set "JUMP_HOST=serveruat@61.219.42.242"
set "TARGET_HOST=gus-server@172.16.1.10"

echo =====================================================
echo 步驟 1：使用 rsync 上傳到伺服器暫存目錄
echo =====================================================
rsync -avz -e "ssh -J %JUMP_HOST%" "%LOCAL_PATH%" %TARGET_HOST%:%REMOTE_TMP%

IF %ERRORLEVEL% NEQ 0 (
    echo 上傳失敗，請確認 SSH 連線與權限
    pause
    exit /b
)

echo =====================================================
echo 步驟 2：在伺服器將暫存資料移動到正式家目錄
echo =====================================================
ssh -J %JUMP_HOST% %TARGET_HOST% "sudo rm -rf /home/gus-server && sudo mv %REMOTE_TMP% /home/gus-server && sudo chown -R gus-server:gus-server /home/gus-server"

IF %ERRORLEVEL% EQU 0 (
    echo =====================================================
    echo 上傳完成，已同步到 /home/gus-server
    echo =====================================================
) ELSE (
    echo =====================================================
    echo 移動或改權限失敗，請確認 sudo 權限
    echo =====================================================
)

pause
