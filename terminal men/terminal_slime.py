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

# 初始化 Console
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

         r" /    ●      ▲      ●    \ ",

         r"|                         |",

         r"|                         |",

         r" \                       / ",

         r"  '---------------------'  "],



        [r"       .-----------.       ",

         r"    .-'             '-.    ",

         r"  .'   *             * '.  ",

         r" /    ●      ▲      ●    \ ",

         r"|                         |",

         r" \                       / ",

         r"  '---------------------'  ",

         r"                           "],



        [r"                           ",

         r"      .-------------.      ",

         r"   .-'               '-.   ",

         r" .'   *             *   '. ",

         r"/     ●      ▲      ●     \ ",

         r"|                         |",

         r" \                       / ",

         r"  '---------------------'  "],



        [r"                           ",

         r"      .-------------.      ",

         r"   .-'               '-.   ",

         r" .'   *             *   '. ",

         r"/     ●      ▲      ●     \ ",

         r"|                         |",

         r" \                       / ",

         r"  '---------------------'  "],



        [r"       .-----------.       ",

         r"    .-'             '-.    ",

         r"  .'   *             * '.  ",

         r" /    ●      ▲      ●    \ ",

         r"|                         |",

         r"|                         |",

         r" \                       / ",

         r"  '---------------------'  "],



        [r"      .-------------.      ",

         r"    .-'             '-.    ",

         r"  .'   *             * '.  ",

         r" /    ●      ▲      ●    \ ",

         r"|                         |",

         r"|                         |",

         r" \                       / ",

         r"  '---------------------'  "]

    ],

    "walk_right": [

        [r"       .-----------.       ",

         r"    .-'             '-.    ",

         r"  .'   *             * '.  ",

         r" /        ●    ▲    ●    \ ",

         r"|                         |---.",

         r"|                          \  >",

         r" \                         / ",

         r"  '-----------------------'    "],



        [r"         .-----------.     ",

         r"      .-'             '-.  ",

         r"    .' *             *   '.",

         r"   /    ●      ▲      ●    \ ",

         r"  |                         |",

         r"  |                         |",

         r"   \                       / ",

         r"    '---------------------'  "],



        [r"          .-----------.    ",

         r"       .-'             '-. ",

         r"     .'     *             *",

         r"    /      ●      ▲      ● ",

         r"   |                       ",

         r"   |                       ",

         r"    \                     /",

         r"     '-------------------' "],



        [r"           .-----------.   ",

         r"        .-'             '-.",

         r"      .'   *             * ",

         r"     /    ●      ▲      ●  ",

         r"    |                      ",

         r"    |                      ",

         r"     \                    /",

         r"      '------------------' "],



        [r"       .-----------.       ",

         r"    .-'             '-.    ",

         r"  .'   *             * '.  ",

         r" /    ●      ▲      ●    \ ",

         r"|                         |",

         r"|                         |",

         r" \                       / ",

         r"  '---------------------'  "]

    ],

    "walk_left": [

        [r"       .-----------.       ",

         r"    .-'             '-.    ",

         r"  .'   *             * '.  ",

         r" /    ●    ▲    ●        \ ",

         r".---|                         |",

         r"<  /                          |",

         r"    \                        / ",

         r"     '----------------------'  "],



        [r"     .-----------.         ",

         r"  .-'             '-.      ",

         r".'   *             * '.    ",

         r"/      ●      ▲      ●  \  ",

         r"|                       |  ",

         r"|                       |  ",

         r" \                     /   ",

         r"  '-------------------'    "],



        [r"    .-----------.          ",

         r" .-'             '-.       ",

         r"' *             *   '.     ",

         r"    ●      ▲      ●    \   ",

         r"                |   ",

         r"                |   ",

         r"\                     /    ",

         r" '-------------------'     "],



        [r"   .-----------.           ",

         r" .-'             '-.       ",

         r"   *             *  '.     ",

         r"  ●      ▲      ●     \    ",

         r"                      |    ",

         r"                      |    ",

         r"\                    /     ",

         r" '------------------'      "],



        [r"       .-----------.       ",

         r"    .-'             '-.    ",

         r"  .'   *             * '.  ",

         r" /    ●      ▲      ●    \ ",

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

         r" /    ●      ▲      ●    \ ",

         r"|                         |",

         r" \                       / ",

         r"  '---------------------'  "],



        [r"       .-----------.       ",

         r"    .-'             '-.    ",

         r"  .'   *             * '.  ",

         r" /    ●      ▲      ●    \ ",

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

         r" /    ●      ▲      ●    \ ",

         r"|                         |",

         r"|                         |",

         r" \                       / ",

         r"  '---------------------'  "],



        [r"       .-----------.       ",

         r"    .-'             '-.    ",

         r"  .'   *             * '.  ",

         r" /      ●    ▲      ●    \ ",

         r"|                         |",

         r"|                         |",

         r" \                       / ",

         r"  '---------------------'  "],



        [r"       .-----------.       ",

         r"    .-'             '-.    ",

         r"  .'   *             * '.  ",

         r" /        ●  .    ●      \ ",

         r"|                         |",

         r"|                         |",

         r" \                       / ",

         r"  '---------------------'  "],



        [r"       .-----------.       ",

         r"    .-'             '-.    ",

         r"  .'   *             * '.  ",

         r" /    ●      .  ●        \ ",

         r"|                         |",

         r"|                         |",

         r" \                       / ",

         r"  '---------------------'  "],



        [r"       .-----------.       ",

         r"    .-'             '-.    ",

         r"  .'   *             * '.  ",

         r" /    ●    .  ●          \ ",

         r"|                         |",

         r"|                         |",

         r" \                       / ",

         r"  '---------------------'  "]

    ]

}

    

# 史萊姆本體的資料結構（寬度約 28-30 字元，高度 8 字元）
pet = {
    "x": 2,                 # 會在 update_companion 中根據視窗寬度動態調整
    "y_offset": 0,
    "direction": 1,
    "status_text": "無限制動態大史萊姆載入成功！正在探索你的整個終端機...",
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
    if GetConsoleWindow is None:
        return
    hwnd = GetConsoleWindow()
    if hwnd:
        rect = RECT()
        if GetWindowRect(hwnd, ctypes.byref(rect)):
            width = rect.right - rect.left
            height = rect.bottom - rect.top
            new_left = rect.left + pixels_x
            new_top = rect.top
            MoveWindow(hwnd, new_left, new_top, width, height, True)

# ==========================================
# 🧠 狀態與邊界機（全螢幕適配版）
# ==========================================
def update_companion():
    global current_state, frame_index, pet
    
    # 獲取當前真實的終端機寬度
    term_width, _ = console.size
    # 扣掉 Panel 邊框(大約4個字元)與史萊姆本身點陣寬度(最大約30個字元)，得到最大可移動 X 軸界線
    max_x = max(1, term_width - 34)
    
    pet["accumulated_activity"] += sensor.activity_score
    sensor.activity_score = 0
    pet["ticks_in_state"] += 1
    
    frames = SLIME_ANIMATIONS[current_state]
    frame_index = (frame_index + 1) % len(frames)
    
    WINDOW_SHIFT_PIXELS = 12 

    # --- 走動與動態邊界撞擊處理 ---
    if current_state == "walk_right":
        if pet["x"] >= max_x:
            pet["x"] = max_x
            shift_terminal_window(WINDOW_SHIFT_PIXELS)
            pet["status_text"] = f"（咚！大史萊姆用肥肉抵住右側邊框！把整個終端機往右推！）"
            if random.random() < 0.3:
                pet["ticks_in_state"] = pet["state_duration"]
        else:
            pet["x"] += 0.6  # 畫布變大，稍微加快一點點步伐

    elif current_state == "walk_left":
        if pet["x"] <= 0:
            pet["x"] = 0
            shift_terminal_window(-WINDOW_SHIFT_PIXELS)
            pet["status_text"] = "（哼嗯——！大史萊姆用力抓著左側邊框，把視窗往左邊拽！）"
            if random.random() < 0.3:
                pet["ticks_in_state"] = pet["state_duration"]
        else:
            pet["x"] -= 0.6

    elif current_state == "happy":
        jump_heights = [0, -1, -2, -2, -1, 0]
        if frame_index < len(jump_heights):
            pet["y_offset"] = jump_heights[frame_index]
        else:
            pet["y_offset"] = 0
    else:
        pet["y_offset"] = 0

    # --- 健康護眼通知 ---
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

    # --- 決策核心 ---
    if pet["ticks_in_state"] >= pet["state_duration"]:
        activity_result = pet["accumulated_activity"]
        pet["accumulated_activity"] = 0
        pet["ticks_in_state"] = 0
        
        period = get_time_period()
        dialogues = TIMED_OBSERVATIONS[period]
        
        # 主人活躍
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
                    pet["state_duration"] = random.randint(60, 100)
                else:
                    current_state = "sleep"
                    pet["status_text"] = random.choice(dialogues["sleep"])
                    pet["state_duration"] = random.randint(60, 100)
            
        # 主人工作（好動）
        else:
            if current_state == "sleep":
                current_state = "idle"
                pet["status_text"] = "大史萊姆抖了抖身上的肉，醒過來繼續陪著主人。"
                pet["state_duration"] = random.randint(30, 60)
            else:
                if period in ["morning", "daytime"]:
                    current_state = random.choice(["walk_right", "walk_left", "walk_right", "walk_left", "idle"])
                else: 
                    current_state = random.choice(["idle", "walk_right", "walk_left", "bored"])
                    
                pet["status_text"] = random.choice(dialogues["watching"])
                
            pet["state_duration"] = random.randint(20, 50)

# ==========================================
# 📺 動態畫布渲染引擎 (完美適配視窗大小)
# ==========================================
def render_canvas(width, height):
    # 建立動態大小的 Canvas 二維陣列
    canvas = [[" " for _ in range(width)] for _ in range(height)]
    
    frames = SLIME_ANIMATIONS.get(current_state, SLIME_ANIMATIONS["idle"])
    actual_frame = frames[frame_index % len(frames)]
    
    # 史萊姆垂直居中靠下
    base_y = max(0, height - 9)
    start_x = int(pet["x"])
    start_y = max(0, base_y + pet["y_offset"])
    
    # 繪製史萊姆本體
    for row_idx, line in enumerate(actual_frame):
        for col_idx, char in enumerate(line):
            if char == " " or char == "\xa0": 
                continue
            target_x = start_x + col_idx
            target_y = start_y + row_idx
            if 0 <= target_x < width and 0 <= target_y < height:
                canvas[target_y][target_x] = char

    # 繪製 Zzz 睡覺特效
    if current_state == "sleep":
        z_cycle = (frame_index // 2) % 3
        z_char = "z" if z_cycle == 0 else ("Z" if z_cycle == 1 else "💤")
        zx, zy = start_x + 22 + z_cycle, start_y - z_cycle
        if 0 <= zx < width and 0 <= zy < height:
            canvas[zy][zx] = z_char

    return "\n".join("".join(row) for row in canvas)

def build_pet_world():
    # 1. 動態獲取當前終端機的大小
    term_width, term_height = console.size
    
    # 2. 計算 Panel 內部的可用寬高 (扣掉邊框與底部狀態欄)
    panel_width = max(40, term_width - 2)
    panel_height = max(12, term_height - 1)  # 利用幾乎所有垂直空間
    
    canvas_w = panel_width - 4
    canvas_h = panel_height - 5  # 留空間給分界線和文字
    
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
    
    # 生成對應此大小的畫布
    canvas_str = render_canvas(canvas_w, canvas_h)
    
    display_text = Text()
    display_text.append(f"{canvas_str}\n", style=f"bold {theme_color}")
    
    # 動態畫出跟視窗同寬的分隔線
    divider = "─" * (canvas_w)
    display_text.append(f"{divider}\n", style="bright_black")
    display_text.append(f"   {pet['status_text']}", style="italic white")

    companion_panel = Panel(
        display_text,
        title="Slime Companion (Dynamic) ",
        title_align="center",
        border_style="bright_black",
        box=rich.box.ROUNDED,
        width=panel_width,  
        height=panel_height  
    )
    return companion_panel

# ==========================================
# 🚀 主運行線程
# ==========================================
if __name__ == "__main__":
    try:
        # 使用 screen=True 啟用全螢幕替代緩衝區
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