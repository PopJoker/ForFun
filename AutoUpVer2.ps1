# 強制讓 PowerShell 認得 Git 的中文輸出，解決亂碼問題
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ROOT_DIR = $PSScriptRoot
$DISCORD_WEBHOOK = "https://discordapp.com/api/webhooks/1443135453837529098/apii1DGNJeeGhew3GiIatGEBCanLcR2wfMRI-8UyNCRbJeyxaHCOPUqinbNu_lfVnRvk"
$LOG_DIR = Join-Path $ROOT_DIR "logs"
if (-not (Test-Path $LOG_DIR)) { New-Item -ItemType Directory -Path $LOG_DIR | Out-Null }

$TODAY = Get-Date -Format "yyyy-MM-dd"
$NOW = Get-Date -Format "HH:mm:ss"
$LOG_FILE = Join-Path $LOG_DIR "$TODAY.log"
$ERR_FILE = Join-Path $LOG_DIR "$TODAY-error.log"
$COMMIT_MSG = $TODAY

# ================= Gitea 自動化連線設定 =================
$GITEA_URL  = "http://gusmodule-gittea"     # Gitea 的網址
$GITEA_USER = "PopJoker"                    # 你的 Gitea 帳號
$GITEA_TOKEN = "62114a3b3e60386552fea158728bf0e7d81e82dd"
# ==========================================================

Add-Content $LOG_FILE "[$TODAY $NOW] ================= START Git Batch ================="
Add-Content $LOG_FILE ""

Get-ChildItem -Path $ROOT_DIR -Directory | ForEach-Object {
    $dir = $_.FullName
    $repoName = $_.Name
    if (Test-Path (Join-Path $dir ".git")) {

        Write-Host "------------------------------" -ForegroundColor Cyan
        Write-Host "Entering Git repo: $($repoName)" -ForegroundColor Yellow
        Add-Content $LOG_FILE "[$TODAY $NOW] Entering Git repo: $($repoName)"

        Push-Location $dir

        $branch = git symbolic-ref --short HEAD 2>$null
        if (-not $branch) { $branch = "main" }

        try {
            # 1. 透過 Gitea API 檢查這個倉庫是否存在
            $checkUrl = "$GITEA_URL/api/v1/repos/$GITEA_USER/$repoName"
            $headers = @{ "Authorization" = "token $GITEA_TOKEN"; "Accept" = "application/json" }
            $repoExists = $false

            try {
                $response = Invoke-WebRequest -Uri $checkUrl -Headers $headers -Method Get -ErrorAction Stop
                $repoExists = $true
            } catch {
                # 如果回傳 404 代表倉庫不存在，準備自動建立
                if ($_.Exception.Response.StatusCode.value__ -eq 404) {
                    $repoExists = $false
                } else {
                    throw $_ # 其他網路或權限錯誤直接拋出
                }
            }

            # 2. 如果 Gitea 沒有這個倉庫，用 API 直接開創一個新空房間！
            if (-not $repoExists) {
                Write-Host "Gitea repository '$repoName' not found. Creating it via API..." -ForegroundColor Magenta
                Add-Content $LOG_FILE "[$TODAY $NOW] Creating Gitea repo via API: $repoName"
                
                $createUrl = "$GITEA_URL/api/v1/user/repos"
                $body = @{ name = $repoName; private = $true } | ConvertTo-Json # 預設建立私有倉庫
                
                Invoke-RestMethod -Uri $createUrl -Headers $headers -Method Post -ContentType "application/json" -Body $body | Out-Null
            }

            # 3. 確保本地 Git 已經綁定了雙向推送 (Gitea + GitHub)
            $oldUrl = git remote get-url origin 2>$null
            $pushUrls = git remote get-url --push origin 2>$null
            $targetGiteaUrl = "$GITEA_URL/$GITEA_USER/$repoName.git"

            if ($pushUrls -notcontains $targetGiteaUrl) {
                Write-Host "Configuring dual-push URL for $repoName..." -ForegroundColor Magenta
                git remote set-url --add --push origin $oldUrl 2>>$ERR_FILE
                git remote set-url --add --push origin $targetGiteaUrl 2>>$ERR_FILE
            }

            # 4. 執行標準 Git 上傳流程
            git add . 2>>$ERR_FILE

            # 判斷暫存區是否有變更
            git diff --cached --quiet
            if ($LASTEXITCODE -ne 0) {
                git commit -m $COMMIT_MSG 2>>$ERR_FILE
                git push origin $branch 2>>$ERR_FILE
                $status = "SUCCESS"
                Write-Host "Commit & Push: SUCCESS (Synced to GitHub & Gitea)" -ForegroundColor Green
            } else {
                # 就算本地沒新變更，也強制 push 一次，確保剛剛在 Gitea 新建的空倉庫能同步拿到完整的歷史紀錄！
                git push origin $branch 2>>$ERR_FILE
                $status = "NO CHANGE (FORCED SYNC)"
                Write-Host "No changes, but forced push to ensure sync." -ForegroundColor Gray
            }
        } catch {
            $status = "FAILED"
            Write-Host "Commit & Push: FAILED" -ForegroundColor Red
            Add-Content $ERR_FILE "[$TODAY $NOW] Repo: $repoName -> Error: $_"
        }

        # Discord embed 通知
        $TIME = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $fields = @(
            @{ name="Repository"; value=$repoName; inline=$true },
            @{ name="Branch";     value=$branch; inline=$true },
            @{ name="Status";     value=$status; inline=$true },
            @{ name="Time";       value=$TIME; inline=$false }
        )

        $color = switch ($status) {
            "SUCCESS"   { 3066993 }  # green
            "FAILED"    { 15158332 } # red
            default     { 3447003 }  # yellow
        }

        $embed = @{
            title       = "Git Auto Update & Backup"
            description = "Synced with local, GitHub, and Gitea"
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