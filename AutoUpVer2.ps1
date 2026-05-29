# 強制讓 PowerShell 認得 Git 的中文輸出，解決亂碼問題
#記得要設定UTF-8 with BOM不然會亂碼或錯誤
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Add-Type -AssemblyName System.Windows.Forms

# 紀錄整個腳本開始執行時間
$SCRIPT_START_TIME = Get-Date

# 【優化：先問關機】在最開頭就詢問，放著就能安心離開
$shutdownAfterDone = $false
$result = [System.Windows.Forms.MessageBox]::Show(
    "Ready to process Git repositories.`nDo you want to SHUT DOWN the system automatically after complete?",
    "Auto Update Config",
    [System.Windows.Forms.MessageBoxButtons]::YesNo,
    [System.Windows.Forms.MessageBoxIcon]::Question
)

if ($result -eq [System.Windows.Forms.DialogResult]::Yes) {
    $shutdownAfterDone = $true
    Write-Host "System WILL SHUT DOWN automatically after processing all repos." -ForegroundColor Red
}
else {
    Write-Host "System will REMAIN ON after processing all repos." -ForegroundColor Green
}

$ROOT_DIR = $PSScriptRoot
$DISCORD_WEBHOOK = "https://discordapp.com/api/webhooks/1443135453837529098/apii1DGNJeeGhew3GiIatGEBCanLcR2wfMRI-8UyNCRbJeyxaHCOPUqinbNu_lfVnRvk"
$LOG_DIR = Join-Path $ROOT_DIR "logs"
if (-not (Test-Path $LOG_DIR)) { New-Item -ItemType Directory -Path $LOG_DIR | Out-Null }

$TODAY = Get-Date -Format "yyyy-MM-dd"
$NOW = Get-Date -Format "HH:mm:ss"
$LOG_FILE = Join-Path $LOG_DIR "$TODAY.log"
$ERR_FILE = Join-Path $LOG_DIR "$TODAY-error.log"
$COMMIT_MSG = $TODAY

# 用來統計最後報告的陣列
$updatedRepos = @()
$failedRepos = @()
$totalRepoCount = 0

# ================= Gitea 自動化連線設定 =================
$GITEA_URL = "http://gusmodule-gittea"     # Gitea 的網址
$GITEA_USER = "PopJoker"                    # 你的 Gitea 帳號
$GITEA_TOKEN = "62114a3b3e60386552fea158728bf0e7d81e82dd"
# ==========================================================

Add-Content $LOG_FILE "[$TODAY $NOW] ================= START Git Batch ================="
Add-Content $LOG_FILE ""

Get-ChildItem -Path $ROOT_DIR -Directory | ForEach-Object {
    $dir = $_.FullName
    $repoName = $_.Name

    # ======= 新增：修正 Gitea 不接受的特殊字元與中文 =======
    # 將空格替換為連字號
    $giteaRepoName = $repoName -replace "\s+", "-"

    # 將所有非字母、數字、底線、連字號、點的字元（包含中文、特殊符號）替換為底線
    $giteaRepoName = $giteaRepoName -replace "[^a-zA-Z0-9_\-\.]", "_"

    # 如果清洗後變成空字串（例如全中文專案名），給予一個安全預設名
    if ([string]::IsNullOrWhiteSpace($giteaRepoName) -or $giteaRepoName -eq "____") {
        $giteaRepoName = "converted-repo-" + (Get-Random -Min 1000 -Max 9999)
    }
    # =======================================================
    if (Test-Path (Join-Path $dir ".git")) {
        $totalRepoCount++
        Write-Host "------------------------------" -ForegroundColor Cyan
        Write-Host "Entering Git repo: $($repoName)" -ForegroundColor Yellow
        Add-Content $LOG_FILE "[$TODAY $NOW] Entering Git repo: $($repoName)"

        Push-Location $dir

        $branch = git symbolic-ref --short HEAD 2>$null
        if (-not $branch) { $branch = "main" }

        # ================= [自動清理殘留鎖定檔] =================
        $lockFile = Join-Path $dir ".git\index.lock"
        if (Test-Path $lockFile) {
            Write-Host "[WARN] Detected residual index.lock in $repoName. Automatically cleaning it..." -ForegroundColor Yellow
            Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
        }

        try {
            # 1. 預先將變更加入暫存
            git add . 2>>$ERR_FILE

            # 2. 檢查本地是否有「尚未 Commit 的變更」
            $hasUncommitted = (git status --porcelain)

            # 3. 檢查本地是否有「已 Commit 但尚未 Push 的進度」
            $hasUnpushed = $false
            git rev-parse --abbrev-ref '@{u}' 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) {
                $unpushedCommits = git log '@{u}..HEAD' --oneline 2>$null
                if ($unpushedCommits) { $hasUnpushed = $true }
            }
            else {
                # 如果遠端完全沒有這個分支，直接判定需要推送
                $hasUnpushed = $true
            }

            # 只要有未提交或未推送的進度，才進入網路連線與同步流程
            if ($hasUncommitted -or $hasUnpushed) {
                
                # 透過 Gitea API 檢查這個倉庫是否存在
                $checkUrl = "$GITEA_URL/api/v1/repos/$GITEA_USER/$giteaRepoName"
                $headers = @{ "Authorization" = "token $GITEA_TOKEN"; "Accept" = "application/json" }
                $repoExists = $false

                try {
                    $response = Invoke-WebRequest -Uri $checkUrl -Headers $headers -Method Get -UseBasicParsing -ErrorAction Stop
                    $repoExists = $true
                }
                catch {
                    if ($_.Exception.Response.StatusCode.value__ -eq 404) { $repoExists = $false }
                    else { throw $_ }
                }

                # 如果 Gitea 沒有這個倉庫，用 API 建立
                if (-not $repoExists) {
                    Write-Host "Gitea repository '$repoName' not found. Creating it via API..." -ForegroundColor Magenta
                    $createUrl = "$GITEA_URL/api/v1/user/repos"
                    $body = @{ name = $giteaRepoName; private = $true } | ConvertTo-Json
                    Invoke-RestMethod -Uri $createUrl -Headers $headers -Method Post -ContentType "application/json" -Body $body | Out-Null
                }

                # 確保本地 Git 綁定了雙向推送
                $oldUrl = git remote get-url origin 2>$null | Select-Object -First 1
                $pushUrls = git remote get-url --push origin 2>$null
                $pureUrl = $GITEA_URL -replace "^https?://", ""
                $targetGiteaUrl = "http://$GITEA_USER`:$GITEA_TOKEN@$pureUrl/$GITEA_USER/$giteaRepoName.git"

                if (-not $oldUrl) {
                    # 如果是純本地專案，直接將 Gitea 設為主要 origin
                    Write-Host "Pure local repo detected. Initializing Gitea as origin..." -ForegroundColor Magenta
                    git remote add origin $targetGiteaUrl 2>>$ERR_FILE
                }
                else {
                    if ($pushUrls -contains "$GITEA_URL/$GITEA_USER/$giteaRepoName.git") {
                        git remote set-url --delete --push origin "$GITEA_URL/$GITEA_USER/$giteaRepoName.git" 2>$null
                        $pushUrls = git remote get-url --push origin 2>$null 
                    }
                    
                    if ($pushUrls -notcontains $targetGiteaUrl) {
                        Write-Host "Configuring dual-push URL with Token for $repoName..." -ForegroundColor Magenta
                        git remote set-url --add --push origin $oldUrl 2>>$ERR_FILE
                        git remote set-url --add --push origin $targetGiteaUrl 2>>$ERR_FILE
                    }
                }

                # 只有在真的有未 Commit 東西時才做 Commit
                if ($hasUncommitted) {
                    git commit -m $COMMIT_MSG 2>>$ERR_FILE
                    Write-Host "Committed local changes." -ForegroundColor Gray
                }

                Write-Host "Pushing updates to remotes..." -ForegroundColor Gray
                git push origin --all
                git push origin $branch -u
                $status = "SUCCESS"
                Write-Host "Sync: SUCCESS (GitHub & Gitea updated)" -ForegroundColor Green
                $updatedRepos += $repoName
            }
            else {
                $status = "NO CHANGE"
                Write-Host "No local changes and everything is up-to-date. Skipping." -ForegroundColor Gray
            }
        }
        catch {
            $status = "FAILED"
            Write-Host "Commit & Push: FAILED" -ForegroundColor Red
            $failedRepos += $repoName
            Add-Content $ERR_FILE "[$TODAY $NOW] Repo: $repoName -> Error: $_"
        }

        # 過程通知：只有當有真正更新或失敗時，才發送單一專案的 Discord 通知
        if ($status -ne "NO CHANGE") {
            $TIME = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            $fields = @(
                @{ name = "Repository"; value = $repoName; inline = $true },
                @{ name = "Branch"; value = $branch; inline = $true },
                @{ name = "Status"; value = $status; inline = $true },
                @{ name = "Time"; value = $TIME; inline = $false }
            )

            $color = if ($status -eq "SUCCESS") { 3066993 } else { 15158332 }
            $embed = @{
                title       = "Git Auto Update & Backup"
                description = "Synced with local, GitHub, and Gitea"
                color       = $color
                fields      = $fields
            }
            $payload = @{ username = "AutoUp"; embeds = @($embed) }

            try {
                Invoke-RestMethod -Uri $DISCORD_WEBHOOK -Method Post -ContentType "application/json" `
                    -Body ($payload | ConvertTo-Json -Compress -Depth 4)
            }
            catch {
                Add-Content $ERR_FILE "Discord webhook error: $_"
            }
        }

        Pop-Location
        Add-Content $LOG_FILE ""
    }
}

# ==================== 🏁 結束與總結報告處理 ====================
$SCRIPT_END_TIME = Get-Date
$duration = $SCRIPT_END_TIME - $SCRIPT_START_TIME
$durationString = "$($duration.Minutes) 分 $($duration.Seconds) 秒"

# 整理更新清單的文字顯示
$updatedSummary = if ($updatedRepos.Count -gt 0) { ($updatedRepos -join ", ") } else { "無專案更新" }
$failedSummary = if ($failedRepos.Count -gt 0) { ($failedRepos -join ", ") } else { "無" }

# 計算關機描述
$systemStatusString = ""
if ($shutdownAfterDone) {
    $shutdownTime = (Get-Date).AddSeconds(10).Format("HH:mm:ss")
    $systemStatusString = "System will shut down in 10 seconds. (Estimated time: $shutdownTime)"
}
else {
    $systemStatusString = "Task completed. System remains on."
}

# 建立總結報告的 Discord Embed 訊息
$summaryFields = @(
    @{ name = "Total Repositories"; value = "$totalRepoCount"; inline = $true },
    @{ name = "Updated Count"; value = "$($updatedRepos.Count)"; inline = $true },
    @{ name = "Execution Duration"; value = $durationString; inline = $true },
    @{ name = "Updated Repositories"; value = $updatedSummary; inline = $false }
)

if ($failedRepos.Count -gt 0) {
    $summaryFields += @{ name = "Failed Repositories"; value = $failedSummary; inline = $false }
}

$summaryFields += @{ name = "System Status"; value = $systemStatusString; inline = $false }

# 決定大框框的顏色 (有失敗就亮黃橘色，全過就亮深藍色)
$summaryColor = if ($failedRepos.Count -gt 0) { 16753920 } else { 2123412 }

$summaryEmbed = @{
    title       = "Git Auto Update Summary Report"
    description = "All repositories processed successfully."
    color       = $summaryColor
    fields      = $summaryFields
    timestamp   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
}

$summaryPayload = @{
    username = "AutoUp Monitor"
    embeds   = @($summaryEmbed)
}

# 發送終點總結報告
try {
    Invoke-RestMethod -Uri $DISCORD_WEBHOOK -Method Post -ContentType "application/json" `
        -Body ($summaryPayload | ConvertTo-Json -Compress -Depth 4)
}
catch {
    Add-Content $ERR_FILE "Discord Summary webhook error: $_"
}

Add-Content $LOG_FILE "[$TODAY $NOW] ================= All repos completed ================="
Write-Host "All repos processed." -ForegroundColor Cyan

# 【執行關機判定】
if ($shutdownAfterDone) {
    Write-Host "Executing scheduled auto shutdown..." -ForegroundColor Red
    Shutdown /s /f /t 10
}
else {
    Write-Host "Done. System remains on." -ForegroundColor Green
}