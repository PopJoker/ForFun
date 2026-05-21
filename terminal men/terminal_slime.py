import os
import sys
import random
import time
from datetime import datetime

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
import rich.box

# 如果是 Windows 系統，載入 Win32 API 用於移動視窗
if os.name == 'nt':
    import ctypes
    from ctypes import wintypes
    
    # 宣告 Win32 結構與函式
    class RECT(ctypes.Structure):
        _fields_ = [
            ('left', ctypes.c_long),
            ('top', ctypes.c_long),
            ('right', ctypes.c_long),
            ('bottom', ctypes.c_long)
        ]
    
    GetConsoleWindow = ctypes.windll.kernel32.GetConsoleWindow
    GetWindowRect = ctypes.windll.user32.GetWindowRect
    MoveWindow = ctypes.windll.user32.MoveWindow
else:
    GetConsoleWindow = None

try:
    from pynput import keyboard, mouse
except ImportError:
    print("請先安裝監聽庫: pip install pynput")
    sys.exit(1)

console = Console()

# ==========================================
# 📊 主人活動感知器 (背景線程)
# ==========================================
class MasterSensor:
    def __init__(self):
        self.activity_score = 0
        self.last_active_time = time.time()

    def touch(self):
        self.activity_score += 1
        self.last_active_time = time.time()

    def start_listening(self):
        def on_press(key): self.touch()
        def on_move(x, y): self.touch()
        def on_click(x, y, button, pressed): self.touch()
        
        k_listener = keyboard.Listener(on_press=on_press)
        m_listener = mouse.Listener(on_move=on_move, on_click=on_click)
        k_listener.start()
        m_listener.start()

sensor = MasterSensor()
sensor.start_listening()

# ==========================================
# 🕒 時間感應與多維度對白庫
# ==========================================
def get_time_period():
    hour = datetime.now().hour
    if 5 <= hour < 11:
        return "morning"
    elif 11 <= hour < 17:
        return "daytime"
    elif 17 <= hour < 22:
        return "evening"
    else:
        return "midnight"

TIMED_OBSERVATIONS = {
    "morning": {
        "watching": ["早安主人，今天也是充滿代碼的一天嗎？", "呼啊... 陪主人迎接第一道光。", "看著晨光照在終端機上..."],
        "bored": ["偷偷伸個懶腰...", "早晨的空氣有一點點甜呢。", "盯著螢幕邊框發呆..."],
        "sleep": ["揉眼睛... 史萊姆還想再瞇一下下。", "進入早晨微休眠..."]
    },
    "daytime": {
        "watching": ["盯著游標看... 主人正在認真呢。", "螢幕上的字跳得好快，手速真驚人！", "劈哩啪啦的鍵盤聲，聽起來好安心。", "主人，寫程式辛苦了，記得喝口水喔！"],
        "bored": ["默默等待下一個游標閃爍...", "發呆是史萊姆的特權...", "外面的陽光好像很溫暖。"],
        "sleep": ["（午後短暫的打瞌睡...）", "系統稍微節能運轉中..."]
    },
    "evening": {
        "watching": ["夕陽落山了，主人今天工作進行得順利嗎？", "靜靜陪著主人收拾今天的思緒。", "看著主人的終端機，像一盞深夜小燈。"],
        "bored": ["晚餐時間到了嗎？（歪頭）", "伸展一下圓滾滾的身體...", "盯著左邊的牆壁看..."],
        "sleep": ["呼... 累了一天，稍微閉上眼睛一會。", "晚間充電中..."]
    },
    "midnight": {
        "watching": ["深夜了... 主人還在努力啊，辛苦你了。", "太晚了，鍵盤聲聽起來特別溫柔呢。", "默默陪著熬夜的主人，守護這行代碼。"],
        "bored": ["已經是深夜的發呆時間了...", "四周好安靜，只剩下游標在閃爍。"],
        "sleep": ["呼... 主人也差不多該休息了吧？", "沉沉睡去... 正在下載數位甜甜圈的夢。", "進入深度深夜節能模式... Zzz"]
    }
}

# ==========================================
# 🎨 高清細節點陣動畫庫
# ==========================================
SLIME_ANIMATIONS = {
    "idle": [
        [r"       .-----------.       ",
         r"    .-'             '-.    ",
         r"  .'   *             * '.  ",
         r" /   [●]     ▲     [●]   \ ",
         r"|                         |",
         r"|                         |",
         r" \                       / ",
         r"  '---------------------'  "],

        [r"       .-----------.       ",
         r"    .-'             '-.    ",
         r"  .'   *             * '.  ",
         r" /   [●]     ▲     [●]   \ ",
         r"|                         |",
         r" \                       / ",
         r"  '---------------------'  ",
         r"                           "],

        [r"                           ",
         r"      .-------------.      ",
         r"   .-'               '-.   ",
         r" .'   *             *   '. ",
         r"/    [●]     ▲     [●]    \ ",
         r"|                         |",
         r" \                       / ",
         r"  '---------------------'  "],

        [r"                           ",
         r"      .-------------.      ",
         r"   .-'               '-.   ",
         r" .'   *             *   '. ",
         r"/    [●]     ▲     [●]    \ ",
         r"|                         |",
         r" \                       / ",
         r"  '---------------------'  "],

        [r"       .-----------.       ",
         r"    .-'             '-.    ",
         r"  .'   *             * '.  ",
         r" /   [●]     ▲     [●]   \ ",
         r"|                         |",
         r"|                         |",
         r" \                       / ",
         r"  '---------------------'  "],

        [r"      .-------------.      ",
         r"    .-'             '-.    ",
         r"  .'   *             * '.  ",
         r" /   [●]     ▲     [●]   \ ",
         r"|                         |",
         r"|                         |",
         r" \                       / ",
         r"  '---------------------'  "]
    ],
    "walk_right": [
        [r"       .-----------.       ",
         r"    .-'             '-.    ",
         r"  .'   *             * '.  ",
         r" /       [●]   ▲   [●]   \ ",
         r"|                         |---.",
         r"|                          \  >",
         r" \                         / ",
         r"  '-----------------------'    "],

        [r"         .-----------.     ",
         r"      .-'             '-.  ",
         r"    .' *             *   '.",
         r"   /   [●]     ▲     [●]   \ ",
         r"  |                         |",
         r"  |                         |",
         r"   \                       / ",
         r"    '---------------------'  "],

        [r"          .-----------.    ",
         r"       .-'             '-. ",
         r"     .'     *             *",
         r"    /     [●]     ▲     [●]",
         r"   |                       ",
         r"   |                       ",
         r"    \                     /",
         r"     '-------------------' "],

        [r"           .-----------.   ",
         r"        .-'             '-.",
         r"      .'   *             * ",
         r"     /   [●]     ▲     [●] ",
         r"    |                      ",
         r"    |                      ",
         r"     \                    /",
         r"      '------------------' "],

        [r"       .-----------.       ",
         r"    .-'             '-.    ",
         r"  .'   *             * '.  ",
         r" /   [●]     ▲     [●]   \ ",
         r"|                         |",
         r"|                         |",
         r" \                       / ",
         r"  '---------------------'  "]
    ],
    "walk_left": [
        [r"       .-----------.       ",
         r"    .-'             '-.    ",
         r"  .'   *             * '.  ",
         r" /   [●]   ▲   [●]       \ ",
         r".---|                         |",
         r"<  /                          |",
         r"    \                        / ",
         r"     '----------------------'  "],

        [r"     .-----------.         ",
         r"  .-'             '-.      ",
         r".'   *             * '.    ",
         r"/     [●]     ▲     [●] \  ",
         r"|                       |  ",
         r"|                       |  ",
         r" \                     /   ",
         r"  '-------------------'    "],

        [r"    .-----------.          ",
         r" .-'             '-.       ",
         r"' *             *   '.     ",
         r"   [●]     ▲     [●]   \   ",
         r"                |   ",
         r"                |   ",
         r"\                     /    ",
         r" '-------------------'     "],

        [r"   .-----------.           ",
         r" .-'             '-.       ",
         r"   *             *  '.     ",
         r" [●]     ▲     [●]    \    ",
         r"                      |    ",
         r"                      |    ",
         r"\                    /     ",
         r" '------------------'      "],

        [r"       .-----------.       ",
         r"    .-'             '-.    ",
         r"  .'   *             * '.  ",
         r" /   [●]     ▲     [●]   \ ",
         r"|                         |",
         r"|                         |",
         r" \                       / ",
         r"  '---------------------'  "]
    ],
    "happy": [
        [r"                           ",
         r"                           ",
         r"     .---------------.     ",
         r"  .-'                 '-.  ",
         r" /   [^]     ▲     [^]   \ ",
         r"|                         |",
         r" \                       / ",
         r"  '---------------------'  "],

        [r"       .-----------.       ",
         r"    .-'             '-.    ",
         r"  .'   ^             ^ '.  ",
         r" /   [^]     ▲     [^]   \ ",
         r"|                         |",
         r"|                         |",
         r" \                       / ",
         r"  '---------------------'  "],

        [r"         .-------.         ",
         r"       .-'       '-.       ",
         r"      /             \      ",
         r"     |   ^       ^   |     ",
         r"     |  [^]  ▲  [^]  |     ",
         r"     |               |     ",
         r"      \             /      ",
         r"       '-----------'       "],

        [r"       .-----------.       ",
         r"    .-'             '-.    ",
         r"  .'   ^             ^ '.  ",
         r" /   [^]     ▲     [^]   \ ",
         r"|                         |",
         r"|                         |",
         r" \                       / ",
         r"  '---------------------'  "],

        [r"                           ",
         r"                           ",
         r"     .---------------.     ",
         r"  .-'                 '-.  ",
         r" /   [●]     ▲     [●]   \ ",
         r"|                         |",
         r" \                       / ",
         r"  '---------------------'  "],

        [r"       .-----------.       ",
         r"    .-'             '-.    ",
         r"  .'   *             * '.  ",
         r" /   [●]     ▲     [●]   \ ",
         r"|                         |",
         r"|                         |",
         r" \                       / ",
         r"  '---------------------'  "]
    ],
    "sleep": [
        [r"                           ",
         r"       .-----------.       ",
         r"    .-'             '-.    ",
         r"  .'                 '.    ",
         r" /   [=]     ▲     [=]   \ ",
         r"|                         |",
         r" \                       / ",
         r"  '---------------------'  "],

        [r"                           ",
         r"      .-------------.      ",
         r"   .-'               '-.   ",
         r" .'                     '. ",
         r"/    [=]     ▲     [=]    \ ",
         r"|                         |",
         r" \                       / ",
         r"  '---------------------'  "],

        [r"                           ",
         r"      .-------------.      ",
         r"   .-'               '-.   ",
         r" .'                     '. ",
         r"/    [=]     ▲     [=]    \ ",
         r"|                         |",
         r" \                       / ",
         r"  '---------------------'  "],

        [r"                           ",
         r"       .-----------.       ",
         r"    .-'             '-.    ",
         r"  .'                 '.    ",
         r" /   [=]     ▲     [=]   \ ",
         r"|                         |",
         r" \                       / ",
         r"  '---------------------'  "]
    ],
    "bored": [
        [r"       .-----------.       ",
         r"    .-'             '-.    ",
         r"  .'   *             * '.  ",
         r" /   [●]     ▲     [●]   \ ",
         r"|                         |",
         r"|                         |",
         r" \                       / ",
         r"  '---------------------'  "],

        [r"       .-----------.       ",
         r"    .-'             '-.    ",
         r"  .'   *             * '.  ",
         r" /     [●]   ▲     [●]   \ ",
         r"|                         |",
         r"|                         |",
         r" \                       / ",
         r"  '---------------------'  "],

        [r"       .-----------.       ",
         r"    .-'             '-.    ",
         r"  .'   *             * '.  ",
         r" /       [●] .   [●]     \ ",
         r"|                         |",
         r"|                         |",
         r" \                       / ",
         r"  '---------------------'  "],

        [r"       .-----------.       ",
         r"    .-'             '-.    ",
         r"  .'   *             * '.  ",
         r" /   [●]     . [●]       \ ",
         r"|                         |",
         r"|                         |",
         r" \                       / ",
         r"  '---------------------'  "],

        [r"       .-----------.       ",
         r"    .-'             '-.    ",
         r"  .'   *             * '.  ",
         r" /   [●]   . [●]         \ ",
         r"|                         |",
         r"|                         |",
         r" \                       / ",
         r"  '---------------------'  "]
    ]
}

pet = {
    "x": 6,
    "y_offset": 0,
    "direction": 1,
    "status_text": "巨型高精細史萊姆載入成功！在終端裡沉甸甸地待命中。",
    "ticks_in_state": 0,
    "state_duration": 80, 
    "accumulated_activity": 0,
    
    "session_start_time": time.time(),
    "last_reminder_time": time.time(),
    "has_cleared_terminal": False,
    "trigger_clear_cmd": False
}

current_state = "idle"
frame_index = 0

# ==========================================
# 🪟 Windows 視窗拖動輔助函式
# ==========================================
def shift_terminal_window(pixels_x):
    """將目前的終端機視窗在畫面上水平移動指定的像素量"""
    if GetConsoleWindow is None:
        return
    
    hwnd = GetConsoleWindow()
    if hwnd:
        rect = RECT()
        if GetWindowRect(hwnd, ctypes.byref(rect)):
            width = rect.right - rect.left
            height = rect.bottom - rect.top
            # 新的桌面座標
            new_left = rect.left + pixels_x
            new_top = rect.top
            # 移動視窗 (最後一個參數 True 代表重繪視窗)
            MoveWindow(hwnd, new_left, new_top, width, height, True)

# ==========================================
# 🧠 狀態機
# ==========================================
# def update_companion():
#     global current_state, frame_index, pet
    
#     pet["accumulated_activity"] += sensor.activity_score
#     sensor.activity_score = 0
#     pet["ticks_in_state"] += 1
    
#     frames = SLIME_ANIMATIONS[current_state]
#     frame_index = (frame_index + 1) % len(frames)
    
#     # --- 平滑物理位移與邊界撞擊拖動視窗處理 ---
#     # 每個字元在畫布大約等同 8~14 像素，這裡設定每次推動視窗 12 像素，帶來的肉感最剛好
#     WINDOW_SHIFT_PIXELS = 12 

#     if current_state == "walk_right":
#         if pet["x"] >= 16:
#             pet["x"] = 16
#             # 碰右壁！不增加內部 X 座標，改為把整個終端機視窗往右拖
#             shift_terminal_window(WINDOW_SHIFT_PIXELS)
#             pet["status_text"] = "（咚！大史萊姆用肥肉抵住邊緣，把整個終端機往右邊推過去了！）"
#         else:
#             pet["x"] += 0.3

#     elif current_state == "walk_left":
#         if pet["x"] <= 0:
#             pet["x"] = 0
#             # 碰左壁！不減少內部 X 座標，改為把整個終端機視窗往左拖
#             shift_terminal_window(-WINDOW_SHIFT_PIXELS)
#             pet["status_text"] = "（哼嗯——！大史萊姆用力抓著左側邊框，把視窗往左邊拽！）"
#         else:
#             pet["x"] -= 0.3

#     elif current_state == "happy":
#         jump_heights = [0, -1, -3, -3, -1, 0]
#         if frame_index < len(jump_heights):
#             pet["y_offset"] = jump_heights[frame_index]
#         else:
#             pet["y_offset"] = 0
#     else:
#         pet["y_offset"] = 0

#     # --- 健康護眼通知 ---
#     now = time.time()
#     if now - pet["last_reminder_time"] > 2700: 
#         pet["last_reminder_time"] = now
#         current_state = "happy"
#         pet["status_text"] = "主人，大史萊姆提醒您：動一動、喝杯水，眼睛需要休息一下囉！"
#         pet["state_duration"] = 60
        
#         try:
#             if os.name == 'nt':
#                 cmd = "PowerShell -Command \"Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show(' (○´∀`)b \n\n主人，工作辛苦了！\n大史萊姆提醒您記得喝口水、動一動。', '史萊姆護眼小助手')\""
#                 os.system(f"start /B {cmd}")
#             else:
#                 if sys.platform == 'darwin':
#                     os.system("osascript -e 'display notification \"(○´∀`)b  記得喝口水、動一動喔！\" with title \"史萊姆護眼小助手 \"'")
#                 else:
#                     os.system("notify-send '史萊姆護眼小助手 ' '(○´∀`)b 記得喝口水、動一動喔！'")
#         except Exception:
#             pass
#         return

#     # --- 決策核心 ---
#     if pet["ticks_in_state"] >= pet["state_duration"]:
#         activity_result = pet["accumulated_activity"]
#         pet["accumulated_activity"] = 0
#         pet["ticks_in_state"] = 0
        
#         period = get_time_period()
#         dialogues = TIMED_OBSERVATIONS[period]
        
#         # 主人活躍
#         if activity_result > 15:
#             current_state = "happy"
#             pet["state_duration"] = 15
#             pet["status_text"] = random.choice(dialogues["watching"])
#             pet["has_cleared_terminal"] = False 
#             frame_index = 0
#             return
            
#         # 主人閒置
#         if activity_result == 0:
#             if current_state == "bored" and not pet["has_cleared_terminal"]:
#                 pet["trigger_clear_cmd"] = True
#                 pet["has_cleared_terminal"] = True
#                 current_state = "sleep"
#                 pet["status_text"] = "[SYSTEM] 檢測到主人閒置，巨型史萊姆用肥胖的身體壓住並清理了終端。"
#                 pet["state_duration"] = 200
#                 return

#             if period == "midnight":
#                 current_state = "sleep"
#                 pet["status_text"] = random.choice(dialogues["sleep"])
#                 pet["state_duration"] = random.randint(150, 250)
#             else:
#                 if current_state in ["idle", "walk_right", "walk_left"]:
#                     current_state = "bored"
#                     pet["status_text"] = random.choice(dialogues["bored"])
#                     pet["state_duration"] = random.randint(100, 150)
#                 else:
#                     current_state = "sleep"
#                     pet["status_text"] = random.choice(dialogues["sleep"])
#                     pet["state_duration"] = random.randint(100, 150)
            
#         else:
#             if current_state == "sleep":
#                 current_state = "idle"
#                 pet["status_text"] = "大史萊姆抖了抖身上的肉，醒過來繼續陪著主人。"
#             else:
#                 if period in ["morning", "daytime"]:
#                     current_state = random.choice(["idle", "walk_right", "walk_left", "idle"])
#                 else:
#                     current_state = random.choice(["idle", "bored", "idle"])
                    
#                 pet["status_text"] = random.choice(dialogues["watching"])
                
#             pet["state_duration"] = random.randint(80, 120)

def update_companion():
    global current_state, frame_index, pet
    
    pet["accumulated_activity"] += sensor.activity_score
    sensor.activity_score = 0
    pet["ticks_in_state"] += 1
    
    frames = SLIME_ANIMATIONS[current_state]
    frame_index = (frame_index + 1) % len(frames)
    
    # 每個字元在畫布大約等同 8~14 像素，這裡設定每次推動視窗 12 像素
    WINDOW_SHIFT_PIXELS = 12 

    if current_state == "walk_right":
        if pet["x"] >= 16:
            pet["x"] = 16
            shift_terminal_window(WINDOW_SHIFT_PIXELS)
            pet["status_text"] = "（咚！大史萊姆用肥肉抵住邊緣，把整個終端機往右邊推過去了！）"
            # 【優化】撞牆時有 30% 機率提早結束這個狀態，讓牠不會卡太久
            if random.random() < 0.3:
                pet["ticks_in_state"] = pet["state_duration"]
        else:
            pet["x"] += 0.4  # 【優化】稍微加快一點點步伐 (原為 0.3)

    elif current_state == "walk_left":
        if pet["x"] <= 0:
            pet["x"] = 0
            shift_terminal_window(-WINDOW_SHIFT_PIXELS)
            pet["status_text"] = "（哼嗯——！大史萊姆用力抓著左側邊框，把視窗往左邊拽！）"
            # 【優化】撞牆時有 30% 機率提早結束
            if random.random() < 0.3:
                pet["ticks_in_state"] = pet["state_duration"]
        else:
            pet["x"] -= 0.4  # 【優化】稍微加快一點點步伐 (原為 0.3)

    elif current_state == "happy":
        jump_heights = [0, -1, -3, -3, -1, 0]
        if frame_index < len(jump_heights):
            pet["y_offset"] = jump_heights[frame_index]
        else:
            pet["y_offset"] = 0
    else:
        pet["y_offset"] = 0

    # --- 健康護眼通知 (保持原樣) ---
    now = time.time()
    if now - pet["last_reminder_time"] > 2700: 
        pet["last_reminder_time"] = now
        current_state = "happy"
        pet["status_text"] = "主人，大史萊姆提醒您：動一動、喝杯水，眼睛需要休息一下囉！"
        pet["state_duration"] = 60
        
        try:
            if os.name == 'nt':
                cmd = "PowerShell -Command \"Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show(' (○´∀`)b \n\n主人，工作辛苦了！\n大史萊姆提醒您記得喝口水、動一動。', '史萊姆護眼小助手')\""
                os.system(f"start /B {cmd}")
            else:
                if sys.platform == 'darwin':
                    os.system("osascript -e 'display notification \"(○´∀`)b  記得喝口水、動一動喔！\" with title \"史萊姆護眼小助手 \"'")
                else:
                    os.system("notify-send '史萊姆護眼小助手 ' '(○´∀`)b 記得喝口水、動一動喔！'")
        except Exception:
            pass
        return

    # --- 決策核心 (活潑化改造) ---
    if pet["ticks_in_state"] >= pet["state_duration"]:
        activity_result = pet["accumulated_activity"]
        pet["accumulated_activity"] = 0
        pet["ticks_in_state"] = 0
        
        period = get_time_period()
        dialogues = TIMED_OBSERVATIONS[period]
        
        # 主人活躍 (打字或動滑鼠)
        if activity_result > 15:
            current_state = "happy"
            pet["state_duration"] = 15
            pet["status_text"] = random.choice(dialogues["watching"])
            pet["has_cleared_terminal"] = False 
            frame_index = 0
            return
            
        # 主人閒置
        if activity_result == 0:
            if current_state == "bored" and not pet["has_cleared_terminal"]:
                pet["trigger_clear_cmd"] = True
                pet["has_cleared_terminal"] = True
                current_state = "sleep"
                pet["status_text"] = "[SYSTEM] 檢測到主人閒置，巨型史萊姆用肥胖的身體壓住並清理了終端。"
                pet["state_duration"] = 200
                return

            if period == "midnight":
                current_state = "sleep"
                pet["status_text"] = random.choice(dialogues["sleep"])
                pet["state_duration"] = random.randint(150, 250)
            else:
                if current_state in ["idle", "walk_right", "walk_left"]:
                    current_state = "bored"
                    pet["status_text"] = random.choice(dialogues["bored"])
                    pet["state_duration"] = random.randint(60, 100) # 【優化】發呆時間縮短 (原 100~150)
                else:
                    current_state = "sleep"
                    pet["status_text"] = random.choice(dialogues["sleep"])
                    pet["state_duration"] = random.randint(60, 100)
            
        # 主人正常工作狀態下 (大幅提升史萊姆的好動度)
        else:
            if current_state == "sleep":
                current_state = "idle"
                pet["status_text"] = "大史萊姆抖了抖身上的肉，醒過來繼續陪著主人。"
                pet["state_duration"] = random.randint(30, 60)
            else:
                if period in ["morning", "daytime"]:
                    # 【優化】將走動機率大幅提升！walk_right 與 walk_left 各佔 37.5%，發呆只剩 25%
                    current_state = random.choice(["walk_right", "walk_left", "walk_right", "walk_left", "idle"])
                else: # 傍晚
                    current_state = random.choice(["idle", "walk_right", "walk_left", "bored"])
                    
                pet["status_text"] = random.choice(dialogues["watching"])
                
            # 【優化】單次動作持續時間大幅縮短 (從 8-12 秒縮短到 2-5 秒)，這樣看起來會非常靈活！
            pet["state_duration"] = random.randint(20, 50)
# ==========================================
# 📺 畫布渲染引擎 (升級相容大型畫布)
# ==========================================
def render_canvas():
    canvas = [[" " for _ in range(50)] for _ in range(12)]
    frames = SLIME_ANIMATIONS.get(current_state, SLIME_ANIMATIONS["idle"])
    actual_frame = frames[frame_index % len(frames)]
    
    base_y = 4 
    start_x = int(pet["x"])
    start_y = base_y + pet["y_offset"]
    
    for row_idx, line in enumerate(actual_frame):
        for col_idx, char in enumerate(line):
            if char == " " or char == "\xa0": 
                continue
            target_x = start_x + col_idx
            target_y = start_y + row_idx
            if 0 <= target_x < 50 and 0 <= target_y < 12:
                canvas[target_y][target_x] = char

    if current_state == "sleep":
        z_cycle = (frame_index // 2) % 3
        z_char = "z" if z_cycle == 0 else ("Z" if z_cycle == 1 else "💤")
        zx, zy = start_x + 22 + z_cycle, start_y - z_cycle
        if 0 <= zx < 50 and 0 <= zy < 12:
            canvas[zy][zx] = z_char

    return "\n".join("".join(row) for row in canvas)

def build_pet_world():
    period = get_time_period()
    color_map = {
        "idle": "bright_cyan" if period != "midnight" else "cyan",
        "walk_right": "bright_blue",
        "walk_left": "bright_blue",
        "sleep": "bright_black",
        "happy": "bright_green",
        "bored": "bright_yellow"
    }
    theme_color = color_map.get(current_state, "bright_cyan")
    canvas_str = render_canvas()
    
    display_text = Text()
    display_text.append(f"{canvas_str}\n", style=f"bold {theme_color}")
    display_text.append(" ───────────────────────────────────────────\n", style="bright_black")
    display_text.append(f"   {pet['status_text']}", style="italic white")

    companion_panel = Panel(
        display_text,
        title="Slime Companion ",
        title_align="center",
        border_style="bright_black",
        box=rich.box.ROUNDED,
        width=54,  
        height=16  
    )
    return companion_panel

# ==========================================
# 🚀 主運行線程
# ==========================================
if __name__ == "__main__":
    try:
        while True:
            with Live(build_pet_world(), refresh_per_second=10, screen=True) as live:
                while True:
                    update_companion()
                    
                    if pet["trigger_clear_cmd"]:
                        pet["trigger_clear_cmd"] = False
                        break 
                        
                    live.update(build_pet_world())
                    time.sleep(0.1) 
            
            os.system('cls' if os.name == 'nt' else 'clear')

    except KeyboardInterrupt:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print("[green]>>>[/green] [white]大史萊姆回歸數位海洋，下次見！[/white]")
        sys.exit(0)