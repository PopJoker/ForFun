# 等待系統穩定
Start-Sleep -Seconds 10

# Chrome 路徑
$chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"

# 使用 Chrome 開啟網址，無痕模式，全螢幕
Start-Process -FilePath $chromePath -ArgumentList @("$url") -WindowStyle Normal

# 等待瀏覽器載入
Start-Sleep -Seconds 5

# 自動填入帳號密碼 (用 SendKeys 模擬)
Add-Type -AssemblyName System.Windows.Forms

# 模擬 Tab/Enter 填寫表單
[System.Windows.Forms.SendKeys]::SendWait("{F11}")
[System.Windows.Forms.SendKeys]::SendWait("{TAB}")
[System.Windows.Forms.SendKeys]::SendWait("GusOfficeTest@gus-tech.com.tw")
[System.Windows.Forms.SendKeys]::SendWait("{TAB}")
[System.Windows.Forms.SendKeys]::SendWait("Gus150211")
[System.Windows.Forms.SendKeys]::SendWait("{TAB}")
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
}
"@

$proc = Get-Process chrome | Sort-Object StartTime -Descending | Select-Object -First 1
[Win32]::SetForegroundWindow($proc.MainWindowHandle)

Start-Sleep -Milliseconds 500

[System.Windows.Forms.SendKeys]::SendWait(" ")
[System.Windows.Forms.SendKeys]::SendWait("{TAB}")
[System.Windows.Forms.SendKeys]::SendWait("{TAB}")
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
