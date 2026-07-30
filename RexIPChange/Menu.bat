@echo off
:: 切換為 UTF-8 編碼
chcp 65001 >nul

:: 自動檢查並請求「系統管理員權限」提權
net session >nul 2>&1
if %errorLevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: 抓取第一個實體網卡名稱
for /f "tokens=*" %%A in ('powershell -NoProfile -Command "(Get-NetAdapter | Where-Object { $_.HardwareInterface -eq $true -and $_.Name -notlike '*vEthernet*' -and $_.Name -notlike '*Virtual*' -and $_.Name -notlike '*Tailscale*' } | Select-Object -First 1).Name"') do (
    set "ADAPTER=%%A"
)

if not defined ADAPTER (
    echo [ERROR] 找不到實體網路卡！
    pause
    exit /b
)

:MENU
cls
echo =========================================
echo        Network Switcher (Multi-IP)
echo =========================================
echo  目標網卡: [%ADAPTER%]
echo -----------------------------------------
echo  [1] Set Static IP: 192.168.0.166
echo  [2] Set Static IP: 192.168.1.166
echo  [3] Set Static IP: 192.168.0.155
echo  [4] Set Static IP: 192.168.1.155
echo  [5] Set Dynamic IP (DHCP)
echo  [6] Exit
echo =========================================
set /p option="請選擇操作選項 [1-6]: "

if "%option%"=="1" set "TARGET_IP=192.168.0.166" & set "GATEWAY=192.168.0.1" & goto SET_STATIC
if "%option%"=="2" set "TARGET_IP=192.168.1.166" & set "GATEWAY=192.168.1.1" & goto SET_STATIC
if "%option%"=="3" set "TARGET_IP=192.168.0.155" & set "GATEWAY=192.168.0.1" & goto SET_STATIC
if "%option%"=="4" set "TARGET_IP=192.168.1.155" & set "GATEWAY=192.168.1.1" & goto SET_STATIC
if "%option%"=="5" goto SET_DHCP
if "%option%"=="6" goto END
goto MENU

:SET_STATIC
echo.
echo 正在設定靜態 IP (%TARGET_IP%)...

powershell -NoProfile -Command ^
  "$alias = '%ADAPTER%';" ^
  "$targetIp = '%TARGET_IP%';" ^
  "$gateway = '%GATEWAY%';" ^
  "$adapter = Get-NetAdapter -Name $alias;" ^
  "$regPath = 'HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\' + $adapter.DeviceID;" ^
  "Set-ItemProperty -Path $regPath -Name 'EnableDHCP' -Value 0;" ^
  "Set-ItemProperty -Path $regPath -Name 'IPAddress' -Value @($targetIp);" ^
  "Set-ItemProperty -Path $regPath -Name 'SubnetMask' -Value @('255.255.255.0');" ^
  "Set-ItemProperty -Path $regPath -Name 'DefaultGateway' -Value @($gateway);" ^
  "Set-DnsClientServerAddress -InterfaceAlias $alias -ServerAddresses ($gateway) -ErrorAction SilentlyContinue;" ^
  "Disable-NetAdapter -Name $alias -Confirm:$false;" ^
  "Enable-NetAdapter -Name $alias -Confirm:$false;"

echo.
echo [驗證結果]：
powershell -NoProfile -Command ^
  "$alias = '%ADAPTER%';" ^
  "$adapter = Get-NetAdapter -Name $alias;" ^
  "$regPath = 'HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\' + $adapter.DeviceID;" ^
  "$dhcp = (Get-ItemProperty -Path $regPath).EnableDHCP;" ^
  "$ip = (Get-ItemProperty -Path $regPath).IPAddress;" ^
  "if ($dhcp -eq 0) { Write-Host '註冊表設定: 靜態 IP (Static)' -ForegroundColor Green; Write-Host ('設定 IP 位址: ' + $ip[0]) } else { Write-Host '註冊表設定: DHCP' -ForegroundColor Yellow };" ^
  "if ($adapter.Status -ne 'Up') { Write-Host '實體連線狀態: 網路線未連接（插上網路線後會自動載入此 IP）' -ForegroundColor Cyan } else { Get-NetIPAddress -InterfaceAlias $alias -AddressFamily IPv4 -ErrorAction SilentlyContinue | Select-Object IPAddress, PrefixLength }"

pause
goto MENU

:SET_DHCP
echo.
echo 正在切換回 DHCP...

powershell -NoProfile -Command ^
  "$alias = '%ADAPTER%';" ^
  "$adapter = Get-NetAdapter -Name $alias;" ^
  "$regPath = 'HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\' + $adapter.DeviceID;" ^
  "Set-ItemProperty -Path $regPath -Name 'EnableDHCP' -Value 1;" ^
  "Remove-ItemProperty -Path $regPath -Name 'IPAddress' -ErrorAction SilentlyContinue;" ^
  "Remove-ItemProperty -Path $regPath -Name 'SubnetMask' -ErrorAction SilentlyContinue;" ^
  "Remove-ItemProperty -Path $regPath -Name 'DefaultGateway' -ErrorAction SilentlyContinue;" ^
  "Set-DnsClientServerAddress -InterfaceAlias $alias -ResetServerAddresses -ErrorAction SilentlyContinue;" ^
  "Disable-NetAdapter -Name $alias -Confirm:$false;" ^
  "Enable-NetAdapter -Name $alias -Confirm:$false;"

echo.
echo [驗證結果]：
powershell -NoProfile -Command "Get-NetIPInterface -InterfaceAlias '%ADAPTER%' | Select-Object InterfaceAlias, Dhcp"

pause
goto MENU

:END
exit