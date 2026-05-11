# auto_git_notify.ps1
$ROOT_DIR = $PSScriptRoot
$DISCORD_WEBHOOK = "https://discordapp.com/api/webhooks/1443135453837529098/apii1DGNJeeGhew3GiIatGEBCanLcR2wfMRI-8UyNCRbJeyxaHCOPUqinbNu_lfVnRvk"
$LOG_DIR = Join-Path $ROOT_DIR "logs"
if (-not (Test-Path $LOG_DIR)) { New-Item -ItemType Directory -Path $LOG_DIR | Out-Null }

$TODAY = Get-Date -Format "yyyy-MM-dd"
$NOW = Get-Date -Format "HH:mm:ss"
$LOG_FILE = Join-Path $LOG_DIR "$TODAY.log"
$ERR_FILE = Join-Path $LOG_DIR "$TODAY-error.log"
$COMMIT_MSG = $TODAY

Add-Content $LOG_FILE "[$TODAY $NOW] ================= START Git Batch ================="
Add-Content $LOG_FILE ""

Get-ChildItem -Path $ROOT_DIR -Directory | ForEach-Object {
    $dir = $_.FullName
    if (Test-Path (Join-Path $dir ".git")) {

        Write-Host "------------------------------" -ForegroundColor Cyan
        Write-Host "Entering Git repo: $($_.Name)" -ForegroundColor Yellow
        Add-Content $LOG_FILE "[$TODAY $NOW] Entering Git repo: $($_.Name)"

        Push-Location $dir

        $branch = git symbolic-ref --short HEAD 2>$null
        if (-not $branch) { $branch = "main" }

        try {
            # 一律加入全部檔案（包含新增 txt）
            # git add .fatal: Unable t...': File exists.:String 不能看中文待處理 2026-04-22
            git add . 2>>$ERR_FILE

            # 判斷暫存區是否有變更
            git diff --cached --quiet
            if ($LASTEXITCODE -ne 0) {
                git commit -m $COMMIT_MSG 2>>$ERR_FILE
                # git add .fatal: Unable t...': File exists.:String 不能看中文待處理 2026-04-22
                git push origin $branch 2>>$ERR_FILE
                $status = "SUCCESS"
                Write-Host "Commit & Push: SUCCESS" -ForegroundColor Green
            } else {
                $status = "NO CHANGE"
                Write-Host "No changes detected." -ForegroundColor Gray
            }
        } catch {
            $status = "FAILED"
            Write-Host "Commit & Push: FAILED" -ForegroundColor Red
            Add-Content $ERR_FILE "Git operation error: $_"
        }

        # Discord embed
        $TIME = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $fields = @(
            @{ name="Repository"; value=$_.Name; inline=$true },
            @{ name="Branch";     value=$branch; inline=$true },
            @{ name="Status";     value=$status; inline=$true },
            @{ name="Time";       value=$TIME; inline=$false }
        )

        # Color based on status
        $color = switch ($status) {
            "SUCCESS"   { 3066993 }  # green
            "FAILED"    { 15158332 } # red
            default     { 3447003 }  # yellow
        }

        $embed = @{
            title       = "Git Auto Update"
            description = "Repository update status"
            color       = $color
            fields      = $fields
        }

        $payload = @{
            username = "AutoUp"
            embeds   = @($embed)
        }

        try {
            Invoke-RestMethod -Uri $DISCORD_WEBHOOK -Method Post -ContentType "application/json" `
                -Body ($payload | ConvertTo-Json -Compress -Depth 4)
        } catch {
            Add-Content $ERR_FILE "Discord webhook error: $_"
        }

        Pop-Location
        Add-Content $LOG_FILE ""
    }
}

Add-Content $LOG_FILE "[$TODAY $NOW] ================= All repos completed ================="
Write-Host "All repos processed." -ForegroundColor Cyan

Add-Type -AssemblyName System.Windows.Forms

# 顯示訊息視窗
$result = [System.Windows.Forms.MessageBox]::Show(
    "All repos processed. Update done.`nDo you want to shut down the system now?",
    "Auto Update",
    [System.Windows.Forms.MessageBoxButtons]::YesNo,
    [System.Windows.Forms.MessageBoxIcon]::Question
)

if ($result -eq [System.Windows.Forms.DialogResult]::Yes) {
    Write-Host "System will shut down..." -ForegroundColor Red
    Shutdown /s /f /t 0
} else {
    Write-Host "Shutdown cancelled." -ForegroundColor Green
}