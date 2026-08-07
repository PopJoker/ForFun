# 強制讓 PowerShell 認得 Git 的中文輸出，解決亂碼問題
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Add-Type -AssemblyName System.Windows.Forms

# 紀錄整個腳本開始執行時間
$SCRIPT_START_TIME = Get-Date

# 1. 詢問是否自動關機
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
} else {
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

# ================= Gitea 自動化連線設定 =================
$GITEA_URL = "http://gusmodule-gittea"
$GITEA_USER = "PopJoker"
$GITEA_TOKEN = "62114a3b3e60386552fea158728bf0e7d81e82dd"
# ==========================================================

Add-Content $LOG_FILE "[$TODAY $NOW] ================= START Git Batch (Parallel Non-blocking) ================="

# 設定同時執行的最大數量
$MAX_THROTTLE = 5

$targetDirs = Get-ChildItem -Path $ROOT_DIR -Directory | Where-Object { Test-Path (Join-Path $_.FullName ".git") }
$totalRepoCount = $targetDirs.Count

Write-Host "Found $totalRepoCount repositories. Starting parallel execution with $MAX_THROTTLE threads..." -ForegroundColor Cyan

# 建立線程池 (RunspacePool)
$RunspacePool = [runspacefactory]::CreateRunspacePool(1, $MAX_THROTTLE)
$RunspacePool.Open()

# 任務 ScriptBlock
$ScriptBlock = {
    param(
        [string]$dir,
        [string]$repoName,
        [string]$GITEA_URL,
        [string]$GITEA_USER,
        [string]$GITEA_TOKEN,
        [string]$DISCORD_WEBHOOK,
        [string]$COMMIT_MSG,
        [string]$TODAY,
        [string]$NOW
    )

    # 避免 Git STDERR 在多線程環境下搶占句柄造成卡死
    $env:GIT_REDIRECT_STDERR = '2>&1'

    $status = "NO CHANGE"
    $branch = "main"
    $errorMsg = ""

    $giteaRepoName = $repoName -replace "\s+", "-"
    $giteaRepoName = $giteaRepoName -replace "[^a-zA-Z0-9_\-\.]", "_"
    if ([string]::IsNullOrWhiteSpace($giteaRepoName) -or $giteaRepoName -eq "____") {
        $giteaRepoName = "converted-repo-" + (Get-Random -Min 1000 -Max 9999)
    }

    Push-Location $dir
    try {
        $branch = git symbolic-ref --short HEAD 2>$null
        if (-not $branch) { $branch = "main" }

        # 自動清理殘留鎖定檔
        $lockFile = Join-Path $dir ".git\index.lock"
        if (Test-Path $lockFile) {
            Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
        }

        # Add & Status Check
        git add . 2>$null
        $hasUncommitted = (git status --porcelain)

        $hasUnpushed = $false
        git rev-parse --abbrev-ref '@{u}' 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $unpushedCommits = git log '@{u}..HEAD' --oneline 2>$null
            if ($unpushedCommits) { $hasUnpushed = $true }
        } else {
            $hasUnpushed = $true
        }

        if ($hasUncommitted -or $hasUnpushed) {
            # 檢查 Gitea 倉庫是否存在 (加上 Timeout 避免死卡)
            $checkUrl = "$GITEA_URL/api/v1/repos/$GITEA_USER/$giteaRepoName"
            $headers = @{ "Authorization" = "token $GITEA_TOKEN"; "Accept" = "application/json" }
            $repoExists = $false

            try {
                $null = Invoke-WebRequest -Uri $checkUrl -Headers $headers -Method Get -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
                $repoExists = $true
            } catch {
                if ($_.Exception.Response.StatusCode.value__ -ne 404) { throw $_ }
            }

            if (-not $repoExists) {
                $createUrl = "$GITEA_URL/api/v1/user/repos"
                $body = @{ name = $giteaRepoName; private = $true } | ConvertTo-Json
                $null = Invoke-RestMethod -Uri $createUrl -Headers $headers -Method Post -ContentType "application/json" -Body $body -TimeoutSec 10
            }

            # 設定 Dual-Push
            $oldUrl = git remote get-url origin 2>$null | Select-Object -First 1
            $pushUrls = git remote get-url --push origin 2>$null
            $pureUrl = $GITEA_URL -replace "^https?://", ""
            $targetGiteaUrl = "http://$GITEA_USER`:$GITEA_TOKEN@$pureUrl/$GITEA_USER/$giteaRepoName.git"

            if (-not $oldUrl) {
                git remote add origin $targetGiteaUrl 2>$null
            } else {
                if ($pushUrls -contains "$GITEA_URL/$GITEA_USER/$giteaRepoName.git") {
                    git remote set-url --delete --push origin "$GITEA_URL/$GITEA_USER/$giteaRepoName.git" 2>$null
                    $pushUrls = git remote get-url --push origin 2>$null 
                }
                if ($pushUrls -notcontains $targetGiteaUrl) {
                    git remote set-url --add --push origin $oldUrl 2>$null
                    git remote set-url --add --push origin $targetGiteaUrl 2>$null
                }
            }

            if ($hasUncommitted) {
                git commit -m $COMMIT_MSG 2>$null
            }

            git push origin --all 2>$null
            git push origin $branch -u 2>$null
            $status = "SUCCESS"
        }
    } catch {
        $status = "FAILED"
        $errorMsg = $_.ToString()
    } finally {
        Pop-Location
    }

    # 發送單一專案 Discord 通知 (有異動才發送)
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
            $null = Invoke-RestMethod -Uri $DISCORD_WEBHOOK -Method Post -ContentType "application/json" -Body ($payload | ConvertTo-Json -Compress -Depth 4) -TimeoutSec 10
        } catch { }
    }

    return [PSCustomObject]@{
        RepoName = $repoName
        Status   = $status
        Error    = $errorMsg
    }
}

# 派發所有 Job
$jobs = [System.Collections.Generic.List[PSCustomObject]]::new()
foreach ($target in $targetDirs) {
    $powershell = [powershell]::Create().AddScript($ScriptBlock).AddArgument($target.FullName).AddArgument($target.Name).AddArgument($GITEA_URL).AddArgument($GITEA_USER).AddArgument($GITEA_TOKEN).AddArgument($DISCORD_WEBHOOK).AddArgument($COMMIT_MSG).AddArgument($TODAY).AddArgument($NOW)
    $powershell.RunspacePool = $RunspacePool
    
    $jobs.Add([PSCustomObject]@{
        RepoName = $target.Name
        Pipe     = $powershell
        Result   = $powershell.BeginInvoke()
    })
}

# 💡 非阻塞式動態回收（哪個先完成就先處理哪個）
$updatedRepos = @()
$failedRepos = @()

while ($jobs.Count -gt 0) {
    for ($i = $jobs.Count - 1; $i -ge 0; $i--) {
        $job = $jobs[$i]
        
        # 檢查該線程是否執行完畢
        if ($job.Result.IsCompleted) {
            $jobResult = $job.Pipe.EndInvoke($job.Result)
            $job.Pipe.Dispose()

            if ($jobResult) {
                switch ($jobResult.Status) {
                    "SUCCESS" {
                        Write-Host "[$($jobResult.RepoName)] Sync: SUCCESS" -ForegroundColor Green
                        $updatedRepos += $jobResult.RepoName
                        Add-Content $LOG_FILE "[$TODAY $NOW] Repo: $($jobResult.RepoName) -> SUCCESS"
                    }
                    "FAILED" {
                        Write-Host "[$($jobResult.RepoName)] Commit & Push: FAILED" -ForegroundColor Red
                        $failedRepos += $jobResult.RepoName
                        Add-Content $ERR_FILE "[$TODAY $NOW] Repo: $($jobResult.RepoName) -> Error: $($jobResult.Error)"
                    }
                    "NO CHANGE" {
                        Write-Host "[$($jobResult.RepoName)] No local changes. Skipping." -ForegroundColor Gray
                    }
                }
            }
            
            # 移除已完成的 Job
            $jobs.RemoveAt($i)
        }
    }
    # 避免 CPU 空轉，短暫休息 200ms
    Start-Sleep -Milliseconds 200
}

# 關閉線程池
$RunspacePool.Close()
$RunspacePool.Dispose()

# ==================== 🏁 結束與總結報告處理 ====================
$SCRIPT_END_TIME = Get-Date
$duration = $SCRIPT_END_TIME - $SCRIPT_START_TIME
$durationString = "$($duration.Minutes) 分 $($duration.Seconds) 秒"

$updatedSummary = if ($updatedRepos.Count -gt 0) { ($updatedRepos -join ", ") } else { "無專案更新" }
$failedSummary = if ($failedRepos.Count -gt 0) { ($failedRepos -join ", ") } else { "無" }

$systemStatusString = if ($shutdownAfterDone) {
    "System will shut down in 10 seconds."
} else {
    "Task completed. System remains on."
}

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

$summaryColor = if ($failedRepos.Count -gt 0) { 16753920 } else { 2123412 }

$summaryEmbed = @{
    title       = "Git Auto Update Summary Report (Parallel)"
    description = "All repositories processed."
    color       = $summaryColor
    fields      = $summaryFields
    timestamp   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
}

$summaryPayload = @{
    username = "AutoUp Monitor"
    embeds   = @($summaryEmbed)
}

try {
    Invoke-RestMethod -Uri $DISCORD_WEBHOOK -Method Post -ContentType "application/json" `
        -Body ($summaryPayload | ConvertTo-Json -Compress -Depth 4) -TimeoutSec 10
} catch {
    Add-Content $ERR_FILE "Discord Summary webhook error: $_"
}

Add-Content $LOG_FILE "[$TODAY $NOW] ================= All repos completed ================="
Write-Host "All repos processed in $durationString." -ForegroundColor Cyan

# 執行關機判定
if ($shutdownAfterDone) {
    Write-Host "Executing scheduled auto shutdown..." -ForegroundColor Red
    Shutdown /s /f /t 10
} else {
    Write-Host "Done. System remains on." -ForegroundColor Green
}