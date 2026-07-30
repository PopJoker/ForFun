# 1. Auto-elevate Administrator privileges
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

# Load Windows Forms
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

# 2. Auto-detect Physical Network Adapter
$adapter = Get-NetAdapter -ErrorAction SilentlyContinue | Where-Object { 
    $_.HardwareInterface -eq $true -and 
    $_.Name -notlike '*vEthernet*' -and 
    $_.Name -notlike '*Virtual*' -and 
    $_.Name -notlike '*Tailscale*' 
} | Select-Object -First 1

if (-not $adapter) {
    [System.Windows.Forms.MessageBox]::Show("Physical Network Adapter NOT found!", "Error", "OK", "Error")
    exit
}

$alias = $adapter.Name
$ifIndex = $adapter.InterfaceIndex

# Core: Set Static IP (極速 + 100% 正確寫入 Gateway)
function Set-StaticIP ($ip, $gateway) {
    # 關閉 DHCP 模式
    Set-NetIPInterface -InterfaceIndex $ifIndex -Dhcp Disabled -ErrorAction SilentlyContinue
    
    # 清除舊的 IP 及預設閘道
    Get-NetIPAddress -InterfaceIndex $ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue | Remove-NetIPAddress -Confirm:$false -ErrorAction SilentlyContinue
    Remove-NetRoute -InterfaceIndex $ifIndex -AddressFamily IPv4 -Confirm:$false -ErrorAction SilentlyContinue

    # 新建 IP 與 Gateway
    New-NetIPAddress -InterfaceIndex $ifIndex -IPAddress $ip -PrefixLength 24 -DefaultGateway $gateway -ErrorAction SilentlyContinue | Out-Null
    
    # 設定 DNS
    Set-DnsClientServerAddress -InterfaceIndex $ifIndex -ServerAddresses $gateway -ErrorAction SilentlyContinue

    [System.Windows.Forms.MessageBox]::Show("Switched to:`nIP: $ip`nGW: $gateway", "Success", "OK", "Information")
}

# Core: Set DHCP
function Set-DHCP {
    # 清除靜態 IP 與閘道路由
    Remove-NetRoute -InterfaceIndex $ifIndex -AddressFamily IPv4 -Confirm:$false -ErrorAction SilentlyContinue
    Get-NetIPAddress -InterfaceIndex $ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.PrefixOrigin -eq 'Manual' } | Remove-NetIPAddress -Confirm:$false -ErrorAction SilentlyContinue

    # 啟用 DHCP
    Set-NetIPInterface -InterfaceIndex $ifIndex -Dhcp Enabled -ErrorAction SilentlyContinue
    Set-DnsClientServerAddress -InterfaceIndex $ifIndex -ResetServerAddresses -ErrorAction SilentlyContinue

    [System.Windows.Forms.MessageBox]::Show("Switched to DHCP (Dynamic IP)", "Success", "OK", "Information")
}

# --- GUI Window ---
$form = New-Object System.Windows.Forms.Form
$form.Text = "Network Switcher"
$form.Size = New-Object System.Drawing.Size(350, 360)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false

# Label
$label = New-Object System.Windows.Forms.Label
$label.Location = New-Object System.Drawing.Point(20, 15)
$label.Size = New-Object System.Drawing.Size(300, 20)
$label.Text = "Target Adapter: [$alias]"
$label.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$form.Controls.Add($label)

# Button Helper
function Add-Button ($text, $top, $scriptBlock) {
    $btn = New-Object System.Windows.Forms.Button
    $btn.Location = New-Object System.Drawing.Point(20, $top)
    $btn.Size = New-Object System.Drawing.Size(295, 38)
    $btn.Text = $text
    $btn.Font = New-Object System.Drawing.Font("Segoe UI", 9.5)
    $btn.Add_Click($scriptBlock)
    $form.Controls.Add($btn)
}

# Add Buttons
Add-Button "192.168.0.166 (GW: 192.168.0.1)" 45  { Set-StaticIP "192.168.0.166" "192.168.0.1" }
Add-Button "192.168.1.166 (GW: 192.168.1.1)" 90  { Set-StaticIP "192.168.1.166" "192.168.1.1" }
Add-Button "192.168.0.155 (GW: 192.168.0.1)" 135 { Set-StaticIP "192.168.0.155" "192.168.0.1" }
Add-Button "192.168.1.155 (GW: 192.168.1.1)" 180 { Set-StaticIP "192.168.1.155" "192.168.1.1" }
Add-Button "Switch to DHCP"                 235 { Set-DHCP }

# Show Window
[void]$form.ShowDialog()