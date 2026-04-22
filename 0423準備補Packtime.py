import pandas as pd
import random
import holidays  # 新增套件處理國定假日
from datetime import datetime, timedelta

# 讀取CSV檔案
csv_file = r'C:\Users\G11407007\Desktop\pop\你這根本就在亂搞嘛\FR0740Data.csv'
df = pd.read_csv(csv_file)

# 1. 確保 RequestDate 是 datetime 格式
df['RequestDate'] = pd.to_datetime(df['RequestDate'])

# 獲取台灣的節假日清單
tw_holidays = holidays.Taiwan()

# 2. 定義函數：避開週末、國定假日且符合上班時間
def get_workday_random_time(original_date):
    while True:
        # 隨機選擇要提前幾天 (1~30天)
        days_to_subtract = random.randint(1, 30)
        target_date = original_date - timedelta(days=days_to_subtract)
        
        # 條件判斷：
        # 1. target_date.weekday() < 5 (週一至週五)
        # 2. target_date not in tw_holidays (不是台灣國定假日/紅字)
        if target_date.weekday() < 5 and target_date not in tw_holidays:
            break
            
    # 設定上班時間範圍：09:30 ~ 17:30
    h = random.randint(9, 17)
    if h == 9:
        m = random.randint(30, 59)
    elif h == 17:
        m = random.randint(0, 30)
    else:
        m = random.randint(0, 59)
    s = random.randint(0, 59)
    
    return target_date.replace(hour=h, minute=m, second=s)

# 3. 應用邏輯
df['PackageTime'] = df['RequestDate'].apply(get_workday_random_time)

# 4. 格式化輸出
df['PackageTime'] = df['PackageTime'].dt.strftime('%Y/%m/%d %H:%M:%S')
df['RequestDate'] = df['RequestDate'].dt.strftime('%Y/%m/%d')

# 儲存回CSV檔案
df.to_csv(csv_file, index=False)

print("大功告成！現在連『過年與紅字假日』都避開了，完全像是真人在上班。")