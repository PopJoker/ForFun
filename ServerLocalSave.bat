@echo off
REM =====================================================
REM One-click download of /home/gus-server to local Windows
REM Supports jump host, sudo-protected files, and incremental sync
REM =====================================================

REM Local destination path
set "LOCAL_PATH=C:\Users\G11407007\Downloads\gus-server-home"

REM Remote temporary directory (to handle sudo-protected files)
set "REMOTE_TMP=/tmp/gus-server-copy/"

REM Jump host configuration
set "JUMP_HOST=serveruat@61.219.42.242"
set "TARGET_HOST=gus-server@172.16.1.10"

echo =====================================================
echo Step 1: Create a temporary copy on the server to avoid permission issues
echo =====================================================
ssh -t -J %JUMP_HOST% %TARGET_HOST% "sudo cp -r /home/gus-server %REMOTE_TMP% && sudo chown -R gus-server:gus-server %REMOTE_TMP%"

IF %ERRORLEVEL% NEQ 0 (
    echo Failed to create temporary copy on the server. Please check sudo permissions.
    pause
    exit /b
)

echo =====================================================
echo Step 2: Use rsync to download from server to local
echo =====================================================
rsync -avz -e "ssh -J %JUMP_HOST%" %TARGET_HOST%:%REMOTE_TMP% "%LOCAL_PATH%"

IF %ERRORLEVEL% EQU 0 (
    echo =====================================================
    echo Download completed. Files saved to %LOCAL_PATH%
    echo =====================================================
) ELSE (
    echo =====================================================
    echo Download failed. Please check SSH connection and permissions.
    echo =====================================================
    pause
    exit /b
)

echo =====================================================
echo Step 3 (optional): Remove temporary copy on server
echo =====================================================
ssh -t -J %JUMP_HOST% %TARGET_HOST% "sudo rm -rf %REMOTE_TMP%"

pause
