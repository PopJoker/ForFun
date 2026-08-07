$wscript = New-Object -ComObject Wscript.Shell
while (1) {
  $wscript.SendKeys("{SCROLLLOCK}")
  Start-Sleep -Seconds 60
}