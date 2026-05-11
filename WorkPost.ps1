Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# 強制啟用 TLS 1.2
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$today = Get-Date
$dayOfWeek = $today.DayOfWeek

# --- 設定區 ---
$targetDay = "Monday" # 正式請改回 Monday

if ($dayOfWeek -eq $targetDay) {
    $reportDate = $today.AddDays(-3).ToString("yyyy/MM/dd")
    
    # 1. 先開啟捷徑 (避免之後搶焦點)
    if (Test-Path "C:\Users\G11407007\Desktop\公司網站\SW.lnk") {
        Start-Process "C:\Users\G11407007\Desktop\公司網站\SW.lnk"
    }

    # 2. 抓取隨機梗圖 URL
    $memeUrl = "https://i.imgflip.com/30zz5g.jpg"
    try {
        $response = Invoke-RestMethod -Uri "https://api.imgflip.com/get_memes" -Method Get -TimeoutSec 5
        if ($response.success) {
            $randomMeme = $response.data.memes | Get-Random
            $memeUrl = $randomMeme.url
        }
    } catch {}

    # 3. 下載並轉換圖片 (修正關鍵點)
    $img = $null
    try {
        $webClient = New-Object System.Net.WebClient
        $webClient.Headers.Add("User-Agent", "Mozilla/5.0")
        
        # 這裡必須明確指定為 [byte[]] 型別
        [byte[]]$imgBytes = $webClient.DownloadData($memeUrl)
        $ms = New-Object System.IO.MemoryStream(,$imgBytes) # 注意這裡的小逗號，它是 PS 傳入陣列的技巧
        $img = [Drawing.Image]::FromStream($ms)
    } catch {
        Write-Host "圖片轉換失敗: $($_.Exception.Message)" -ForegroundColor Red
    }

    # 4. 建立視窗
    $form = New-Object Windows.Forms.Form
    $form.Text = "早安！週一提醒"
    $form.Size = New-Object Drawing.Size(500, 620)
    $form.StartPosition = "CenterScreen"
    $form.BackColor = "White"
    $form.ShowIcon = $false
    $form.MaximizeBox = $false
    $form.FormBorderStyle = "FixedDialog"
    $form.TopMost = $true # 核心需求：置頂

    # 圖片框
    if ($img -ne $null) {
        $pictureBox = New-Object Windows.Forms.PictureBox
        $pictureBox.Image = $img
        $pictureBox.Size = New-Object Drawing.Size(440, 380)
        $pictureBox.SizeMode = "Zoom"
        $pictureBox.Location = New-Object Drawing.Point(30, 20)
        $form.Controls.Add($pictureBox)
    }

    # 文字
    $label = New-Object Windows.Forms.Label
    $label.Text = "開心快樂的禮拜一啊！`n記得要更新 Source Code 喔！"
    $label.Size = New-Object Drawing.Size(450, 70)
    $label.Location = New-Object Drawing.Point(25, 420)
    $label.Font = New-Object Drawing.Font("Microsoft JhengHei", 14, [Drawing.FontStyle]::Bold)
    $label.TextAlign = "MiddleCenter"
    $form.Controls.Add($label)

    # 按鈕
    $btn = New-Object Windows.Forms.Button
    $btn.Text = "OK"
    $btn.Size = New-Object Drawing.Size(120, 40)
    $btn.Location = New-Object Drawing.Point(190, 510)
    $btn.DialogResult = [Windows.Forms.DialogResult]::OK
    $form.Controls.Add($btn)

    # 強制視窗奪取焦點
    $form.Add_Shown({ 
        $form.Activate()
        $form.BringToFront() 
    })

    $form.ShowDialog() | Out-Null
}
else {
    $reportDate = $today.AddDays(-1).ToString("yyyy/MM/dd")
}

# 執行複製與開啟網址
Set-Clipboard -Value $reportDate
Start-Process "https://forms.cloud.microsoft/Pages/ResponsePage.aspx?id=0X86xodsikORnVQrLqvUHReY-1fn5eFHt6qb0FuFbqdUMVM0S1QyUzk1R0dBMkFEVDVQNTFVNjhYVy4u"

Write-Host "Done! Report Date: $reportDate" -ForegroundColor Green
Pause