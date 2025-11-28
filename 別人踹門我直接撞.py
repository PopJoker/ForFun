import asyncio
import aiohttp
import time
from datetime import datetime

url = "https://webems.gustech.com.tw/api2/external/check-binding/GU282536000002"
headers = {
    "x-api-key": "9CVMphWOvZEBX2HuDJovEM1w"
}

async def poll_api(session):
    while True:
        start = time.time()
        try:
            async with session.get(url, headers=headers) as response:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # 精確到毫秒
                if response.status == 200:
                    data = await response.json()
                    print(f"[{now}] API 回傳:", data)
                else:
                    print(f"[{now}] 錯誤狀態碼: {response.status}")
        except Exception as e:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"[{now}] 請求失敗:", e)

        # 確保每 1ms 發一次請求
        elapsed = time.time() - start
        await asyncio.sleep(max(0, 0.001 - elapsed))

async def main():
    async with aiohttp.ClientSession() as session:
        await poll_api(session)

asyncio.run(main())
