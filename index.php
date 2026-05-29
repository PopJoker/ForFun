<?php
// 設定網頁編碼
header('Content-Type: text/html; charset=utf-8');

// ⚠️ 請在這裡貼上你的 Discord Webhook 網址 (這放在後端，別人永遠看不到，非常安全)
$webhook_url = "YOUR_DISCORD_WEBHOOK_URL_HERE";

// 1. 獲取使用者的公網 IP (透過 PHP 後端獲取)
$client_ip = $_SERVER['REMOTE_ADDR'];

// 如果伺服器前方有 CDN 或 Proxy (例如 Cloudflare)，改用以下方式獲取真實 IP
if (!empty($_SERVER['HTTP_CF_CONNECTING_IP'])) {
    $client_ip = $_SERVER['HTTP_CF_CONNECTING_IP'];
} elseif (!empty($_SERVER['HTTP_X_FORWARDED_FOR'])) {
    $client_ip = explode(',', $_SERVER['HTTP_X_FORWARDED_FOR'])[0];
}

$status_message = "尚未觸發傳送。";
$report_text = "";

// 2. 當使用者點擊網頁上的按鈕時，觸發傳送邏輯
if (isset($_POST['trigger_collect'])) {
    
    // 3. 在 PHP 後端呼叫地理位置 API 查詢該 IP 的詳細資訊
    // 使用 curl 或 file_get_contents，完全不經過客戶端電腦
    $api_url = "http://ip-api.com/json/" . $client_ip . "?lang=zh-TW";
    $api_response = @file_get_contents($api_url);
    
    if ($api_response) {
        $obj = json_decode($api_response, true);
        
        if ($obj && $obj['status'] === "success") {
            // 組合詳細報表
            $info = "========= 終端詳細報告 (純 PHP 版) =========\n";
            $info .= "實體公網 IP : " . $obj['query'] . "\n";
            $info .= "所在國家    : " . $obj['country'] . " (" . $obj['countryCode'] . ")\n";
            $info .= "城市區域    : " . $obj['regionName'] . " / " . $obj['city'] . "\n";
            $info .= "郵遞區號    : " . $obj['zip'] . "\n";
            $info .= "經緯度座標  : " . $obj['lat'] . ", " . $obj['lon'] . "\n";
            $info .= "網際網路 ISP: " . $obj['isp'] . "\n";
            $info .= "自治系統 ASN: " . $obj['as'] . "\n";
            $info .= "系統時區    : " . $obj['timezone'] . "\n";
            $info .= "=========================================";
            $report_text = $info;

            // 4. 由 PHP 後端直接發送至 Discord Webhook
            if (strpos($webhook_url, "http") === 0) {
                $discord_content = "```\n" . $report_text . "\n```";
                $payload = json_encode(["content" => $discord_content]);

                $ch = curl_init($webhook_url);
                curl_setopt($ch, CURLOPT_CUSTOMREQUEST, "POST");
                curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
                curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
                curl_setopt($ch, CURLOPT_HTTPHEADER, [
                    'Content-Type: application/json'
                ]);
                
                $response = curl_exec($ch);
                $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
                curl_close($ch);

                if ($http_code === 200 || $http_code === 204) {
                    $status_message = "🚀 【回傳成功】詳細資料已由 PHP 後端同步發射至 Discord 頻道！";
                } else {
                    $status_message = "❌ Discord 拒絕接收，狀態碼: " . $http_code;
                }
            } else {
                $status_message = "⚠️ 伺服器未設定有效的 Discord Webhook 網址。";
            }
        } else {
            $report_text = "API 回傳錯誤，無法撈取詳細資料。原始回應：" . $api_response;
        }
    } else {
        $report_text = "【錯誤】PHP 後端無法連線到 IP 查詢伺服器。";
    }
}
?>
<!DOCTYPE html>
<html>
<head>
    <title>終端公網 IP 資訊收集器 (純 PHP 雲端版)</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: "Microsoft JhengHei", Arial, sans-serif; background-color: #f4f6f9; color: #333; padding: 20px; margin: 0; }
        .container { max-width: 500px; margin: 40px auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        h2 { color: #2c3e50; text-align: center; margin-top: 0; }
        .btn { display: block; width: 100%; padding: 12px; background: #2ecc71; color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; font-weight: bold; }
        .btn:hover { background: #27ae60; }
        #result { margin-top: 20px; padding: 15px; background: #2c3e50; color: #ecf0f1; border-left: 5px solid #2ecc71; white-space: pre-wrap; font-family: Consolas, monospace; font-size: 14px; border-radius: 4px; min-height: 100px; }
        .status { text-align: center; font-weight: bold; color: #e74c3c; margin-top: 15px; font-size: 15px; }
    </style>
</head>
<body>

<div class="container">
    <h2>終端資訊收集器 (純 PHP 版)</h2>
    <p style="text-align:left; color:#7f8c8d; font-size: 14px; line-height: 1.5;">
        當前檢測到您的來訪公網 IP 為：<strong><?php echo htmlspecialchars($client_ip); ?></strong><br>
        點擊下方按鈕後，將由雲端伺服器直接發起分析並同步至 Webhook，本地無任何腳本執行。
    </p>
    
    <form method="POST">
        <button type="submit" name="trigger_collect" class="btn">一鍵分析並同步 Webhook</button>
    </form>
    
    <div id="status" class="status" style="color: <?php echo (strpos($status_message, '🚀') !== false) ? '#27ae60' : '#e74c3c'; ?>;">
        <?php echo $status_message; ?>
    </div>
    
    <div id="result"><?php echo !empty($report_text) ? htmlspecialchars($report_text) : "尚未獲取詳細資料。點擊上方按鈕開始。"; ?></div>
</div>

</body>
</html>