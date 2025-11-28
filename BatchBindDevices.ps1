# ===============================
# 設定區
# ===============================
$api_bind     = "https://webems.gustech.com.tw/api2/devices/bind"
$token        = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjQsImVtYWlsIjoiZ3VzQGd1cy5jb20iLCJpYXQiOjE3NjAzNDczMDYsImV4cCI6MTc2MDQzMzcwNn0.BxdhJXneyt6rcjB5pYoiJIHQ9o7N0jNDFTOLg7u2_ok"

# 可調整序號範圍
$start_serial = 21
$end_serial   = 80

# 可選填資訊（若不填就留空或移除）
$default_name      = "測試"
$default_latitude  = 25.0330
$default_longitude = 121.5654
$default_area      = "Taipei"

# ===============================
# 迴圈綁定
# ===============================
for ($i=$start_serial; $i -le $end_serial; $i++) {
    $serial = "MD062500$i"

    # 建立要送的 body
    $bind_body = @{
        serial_number = $serial
        name          = $default_name
        latitude      = $default_latitude
        longitude     = $default_longitude
        area          = $default_area
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod $api_bind -Method POST -Headers @{
            "Authorization" = "Bearer $token"
            "Content-Type"  = "application/json"
        } -Body $bind_body

        Write-Output "$serial -> 綁定成功: $($response.message)"
    } catch {
        Write-Warning "$serial -> 綁定失敗: $($_.Exception.Response.StatusCode) $($_.Exception.Message)"
    }

    Write-Output "------------------------------"
}
