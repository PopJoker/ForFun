#!/bin/bash
# sudo rm -f /tmp/vps_disk_history.log 清除重新計算
# sudo crontab -e 排程表
# * * * * * /home/gus-server/disk_check.sh > /dev/null 2>&1 測試用 每分鐘一次
# 0 9 * * * /home/gus-server/disk_check.sh > /dev/null 2>&1 正式用 每天早上 9 點跑一次
# grep CRON /var/log/syslog | tail -n 20 確認排程有沒有跑

# ================= 配置區域 =================
TEAMS_WEBHOOK_URL="https://defaultc63a7fd16c87438a919d542b2eabd4.1d.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/25f780cc121b490cb677be1fff08ee68/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=z4ZDkWbv2x-0Thr2BxAkA6u9D6TVIkYvMrw4gD6PyIw"
# ============================================

# 1. 獲取當前整體硬碟數據 (精確到小數點後三位)
# 使用 df -k 獲取原始 KB 數據，再透過 awk 精確換算為 GB 並限制格式為 %.3f
DISK_TOTAL=$(df -k / | awk 'NR==2 {printf "%.3fG", $2/1024/1024}')
DISK_USED=$(df -k / | awk 'NR==2 {printf "%.3fG", $3/1024/1024}')
DISK_AVAIL=$(df -k / | awk 'NR==2 {printf "%.3fG", $4/1024/1024}')

# 進度條維持使用整數百分比
DISK_USAGE_PERC=$(df -k / | awk 'NR==2 {printf "%d", $3/$2*100}')

CURRENT_USED_MB=$(df -m / | awk 'NR==2 {print $3}')
CURRENT_TOTAL_MB=$(df -m / | awk 'NR==2 {print $2}')
CURRENT_DATE=$(date '+%Y-%m-%d %H:%M:%S')

# 計算 85% 與 100% 的容量是多少 MB，以及各自還剩多少空間
THRESHOLD_85_MB=$(( CURRENT_TOTAL_MB * 85 / 100 ))
REMAINING_TO_85_MB=$(( THRESHOLD_85_MB - CURRENT_USED_MB ))
REMAINING_TO_100_MB=$(( CURRENT_TOTAL_MB - CURRENT_USED_MB ))

# 2. 製作動態文字進度條圖表 (10格)
BAR_COUNT=$(( DISK_USAGE_PERC / 10 ))
BAR_TEXT=""
for ((i=0; i<10; i++)); do
    if [ $i -lt $BAR_COUNT ]; then
        BAR_TEXT="${BAR_TEXT}█"
    else
        BAR_TEXT="${BAR_TEXT}░"
    fi
done
PROGRESS_CHART="\`${BAR_TEXT} ${DISK_USAGE_PERC}%\`"

# 3. 多日歷史增長率與預估爆碟時間邏輯
CACHE_FILE="/tmp/vps_disk_history.log"
GROWTH_TEXT="今日增長: 數據累積中..."
FORECAST_TEXT="預估預警: 正在收集每日數據..."

# 將今日數據寫入紀錄檔 (格式: 時間戳_已用MB)
echo "$(date +%s)_${CURRENT_USED_MB}" >> "$CACHE_FILE"

# 只保留最後 7 天的紀錄，避免檔案無限增長
tail -n 7 "$CACHE_FILE" > "${CACHE_FILE}.tmp" && mv "${CACHE_FILE}.tmp" "$CACHE_FILE"

RECORD_COUNT=$(wc -l < "$CACHE_FILE")

if [ "$RECORD_COUNT" -gt 1 ]; then
    # 抓取第一筆和最後一筆紀錄來算平均值
    FIRST_RECORD=$(head -n 1 "$CACHE_FILE")
    LAST_RECORD=$(tail -n 1 "$CACHE_FILE")
    
    FIRST_TIME=$(echo "$FIRST_RECORD" | cut -d'_' -f1)
    FIRST_MB=$(echo "$FIRST_RECORD" | cut -d'_' -f2)
    
    LAST_TIME=$(echo "$LAST_RECORD" | cut -d'_' -f1)
    LAST_MB=$(echo "$LAST_RECORD" | cut -d'_' -f2)
    
    # 計算時間差（秒）與空間差（MB）
    SEC_DIFF=$(( LAST_TIME - FIRST_TIME ))
    MB_DIFF=$(( LAST_MB - FIRST_MB ))
    
    # 算今日單日增長
    PREV_RECORD=$(tail -n 2 "$CACHE_FILE" | head -n 1)
    PREV_MB=$(echo "$PREV_RECORD" | cut -d'_' -f2)
    DAILY_GROWTH=$(( CURRENT_USED_MB - PREV_MB ))
    
    if [ $DAILY_GROWTH -lt 0 ]; then
        GROWTH_TEXT="今日增長: 空間釋放了 $((DAILY_GROWTH * -1)) MB"
    else
        GROWTH_TEXT="今日增長: +${DAILY_GROWTH} MB"
    fi

    # 如果有空間增長，開始推算時間 (以平均每秒增長率換算成天)
    if [ $MB_DIFF -gt 0 ] && [ $SEC_DIFF -gt 0 ]; then
        # 每秒增加的 KB 數 (放大計算避免整數除法歸零)
        KB_PER_SEC=$(( MB_DIFF * 1024 / SEC_DIFF ))
        
        if [ $KB_PER_SEC -gt 0 ]; then
            # 每天增加多少 MB = KB_PER_SEC * 86400 / 1024
            AVG_GROWTH_PER_DAY=$(( KB_PER_SEC * 86400 / 1024 ))
            
            # --- 預估 85% 警戒線 ---
            if [ $REMAINING_TO_85_MB -gt 0 ]; then
                DAYS_TO_85=$(( REMAINING_TO_85_MB / AVG_GROWTH_PER_DAY ))
                X_DATE_85=$(date -d "+${DAYS_TO_85} days" '+%Y-%m-%d')
                LINE_85="預估 **${DAYS_TO_85} 天** 後（**${X_DATE_85}**）達到 **85%** 警戒線。"
            else
                LINE_85="注意：硬碟目前已超越 85% 警戒線！"
            fi
            
            # --- 預估 100% 爆滿線 ---
            if [ $REMAINING_TO_100_MB -gt 0 ]; then
                DAYS_TO_100=$(( REMAINING_TO_100_MB / AVG_GROWTH_PER_DAY ))
                X_DATE_100=$(date -d "+${DAYS_TO_100} days" '+%Y-%m-%d')
                LINE_100="預估 **${DAYS_TO_100} 天** 後（**${X_DATE_100}**）硬碟將完全 **100%** 填滿。"
            else
                LINE_100="警告：硬碟空間已達 100% 臨界值！"
            fi
            
            # 組合最終顯示文字
            FORECAST_TEXT="${LINE_85}\n\n${LINE_100}"
        fi
    elif [ $DAILY_GROWTH -eq 0 ]; then
        FORECAST_TEXT="數據無明顯增長，硬碟空間非常安全。"
    else
        FORECAST_TEXT="數據正在減少或清理中，硬碟空間正在釋放。"
    fi
fi

# 4. 根據狀態決定顏色與標題
if [ "$DISK_USAGE_PERC" -gt 85 ]; then
    COLOR="Attention" # 紅色
    TITLE="【緊急警告】整個 VPS 硬碟空間不足！"
else
    COLOR="Accent"    # 藍色
    TITLE="VPS 數據櫃儲存空間每日報告"
fi

# 5. 建立新版 Adaptive Card JSON 格式
JSON_PAYLOAD=$(cat <<EOF
{
    "type": "message",
    "attachments": [
        {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "${TITLE}",
                        "weight": "Bolder",
                        "size": "Large",
                        "color": "${COLOR}"
                    },
                    {
                        "type": "TextBlock",
                        "text": "報告時間: ${CURRENT_DATE}",
                        "isSubtle": true,
                        "spacing": "None"
                    },
                    {
                        "type": "TextBlock",
                        "text": "當前硬碟容量佔用圖表:",
                        "weight": "Bolder",
                        "spacing": "Medium"
                    },
                    {
                        "type": "TextBlock",
                        "text": "${PROGRESS_CHART}",
                        "size": "Medium",
                        "spacing": "None"
                    },
                    {
                        "type": "FactSet",
                        "facts": [
                            { "title": "硬碟總容量:", "value": "${DISK_TOTAL}" },
                            { "title": "已使用空間:", "value": "${DISK_USED}" },
                            { "title": "剩餘可用:", "value": "${DISK_AVAIL}" },
                            { "title": "儲存增長動態:", "value": "${GROWTH_TEXT}" }
                        ],
                        "spacing": "Medium"
                    },
                    {
                        "type": "Container",
                        "style": "emphasis",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": "智能容量填滿預測 (基於歷史數據趨勢):",
                                "weight": "Bolder"
                            },
                            {
                                "type": "TextBlock",
                                "text": "${FORECAST_TEXT}",
                                "wrap": true
                            }
                        ],
                        "spacing": "Large"
                    }
                ],
                "\$schema": "http://adaptivecards.io/schemas/adaptive-card.json"
            }
        }
    ]
}
EOF
)

# 6. 發送 Webhook
echo "正在發送雙重預測通知到 Teams..."
RESPONSE=$(curl -s -w "\nHTTP_STATUS: %{http_code}\n" -H "Content-Type: application/json" -d "$JSON_PAYLOAD" "$TEAMS_WEBHOOK_URL")

echo "================ Teams 回應 ================"
echo "$RESPONSE"
echo "============================================"