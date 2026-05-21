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
# 🎨 逐幀點陣動畫庫 (已排除所有 \xa0 雜質)
# ==========================================
SLIME_ANIMATIONS = {
    "idle": [
        ["   .-------.   ", "  /  ●   ●  \\  ", "  \\_________/  "],
        ["   .-------.   ", "  /  ●   ●  \\  ", "  \\_________/  "],
        ["  .---------.  ", " /   ●   ●   \\ ", " \\___________/ "],
        ["  .---------.  ", " /   ●   ●   \\ ", " \\___________/ "]
    ],
    "walk_right": [
        ["   .-------.   ", "  /  .   ●  \\> ", "  \\_________/  "],
        ["    .-------.  ", "   / .   ●   \\>", "   \\_________/ "],
        ["     .-------.", "    /  .   ●  \\>", "    \\_________/"]
    ],
    "walk_left": [
        ["   .-------.   ", " </  ●   .  \\  ", "  \\_________/  "],
        ["    .-------.  ", "  </  ●   .  \\ ", "   \\_________/ "],
        ["     .-------.", "   </   ●   . \\", "    \\_________/"]
    ],
    "happy": [
        ["               ", "  .---------.  ", " /   ^   ^   \\ ", " \\___________/ "],
        ["   .-------.   ", "  /  ^   ^  \\  ", "  \\_________/  ", "               "],
        ["   .---.       ", "  / ^ ^ \\      ", "  |     |      ", "  \\_____/      "],
        ["   .-------.   ", "  /  ^   ^  \\  ", "  \\_________/  ", "               "],
        ["               ", "  .---------.  ", " /   ^   ^   \\ ", " \\___________/ "]
    ],
    "sleep": [
        ["   .-------.   ", "  /  =   =  \\  ", "  \\_________/  "],
        ["  .---------.  ", " /   =   =   \\ ", " \\___________/ "]
    ],
    "bored": [
        ["   .-------.   ", "  /  ●   ●  \\  ", "  \\_________/  "],
        ["   .-------.   ", "  / .   .   \\  ", "  \\_________/  "],
        ["   .-------.   ", "  /     ●   ●\\ ", "  \\_________/  "]
    ]
}

pet = {
    "x": 12,
    "y_offset": 0,
    "direction": 1,
    "status_text": "系統載入完成，史萊姆在角落待命。",
    "ticks_in_state": 0,
    "state_duration": 60,
    "accumulated_activity": 0,
    
    "session_start_time": time.time(),
    "last_reminder_time": time.time(),
    "has_cleared_terminal": False,
    "trigger_clear_cmd": False
}

current_state = "idle"
frame_index = 0

# ==========================================
# 🧠 慢節奏時間感知 + 系統特權狀態機
# ==========================================
def update_companion():
    global current_state, frame_index, pet
    
    pet["accumulated_activity"] += sensor.activity_score
    sensor.activity_score = 0
    pet["ticks_in_state"] += 1
    
    frames = SLIME_ANIMATIONS[current_state]
    frame_index = (frame_index + 1) % len(frames)
    
    # --- 物理位移 ---
    if current_state == "walk_right":
        pet["x"] += 0.4
        if pet["x"] >= 24:
            pet["x"] = 24
            current_state = "idle"
    elif current_state == "walk_left":
        pet["x"] -= 0.4
        if pet["x"] <= 0:
            pet["x"] = 0
            current_state = "idle"
    elif current_state == "happy":
        jump_heights = [0, -1, -2, -1, 0]
        if frame_index < len(jump_heights):
            pet["y_offset"] = jump_heights[frame_index]
        if frame_index == len(jump_heights) - 1:
            pet["y_offset"] = 0
    else:
        pet["y_offset"] = 0

    # --- 特權 1：無聲健康護眼桌面通知 ---
    now = time.time()
    if now - pet["last_reminder_time"] > 2700: 
        pet["last_reminder_time"] = now
        current_state = "happy"
        pet["status_text"] = "主人你已經連續工作很久了，建議稍微休息、喝杯水。"
        pet["state_duration"] = 50 
        
        try:
            if os.name == 'nt':

                cmd = "PowerShell -Command \"Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show(' (○´∀`)b \n\n主人，工作辛苦了！\n記得喝口水、伸展一下動一動喔。', '史萊姆護眼小助手')\""
                os.system(f"start /B {cmd}")
            else:
                if sys.platform == 'darwin':
                    # macOS Notification: 標題和內容都加上比讚
                    os.system("osascript -e 'display notification \"(○´∀`)b  記得喝口水、動一動喔！\" with title \"史萊姆護眼小助手 \"'")
                else:
                    # Linux notify-send
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
        
        # 主人回來了
        if activity_result > 15:
            current_state = "happy"
            pet["state_duration"] = 5
            pet["status_text"] = random.choice(dialogues["watching"])
            pet["has_cleared_terminal"] = False 
            frame_index = 0
            return
            
        # 主人不在
        if activity_result == 0:
            # 發動實質自動打掃
            if current_state == "bored" and not pet["has_cleared_terminal"]:
                pet["trigger_clear_cmd"] = True
                pet["has_cleared_terminal"] = True
                current_state = "sleep"
                pet["status_text"] = "[SYSTEM] 檢測到主人閒置，已成功調用系統權限清理終端。"
                pet["state_duration"] = 150
                return

            if period == "midnight":
                current_state = "sleep"
                pet["status_text"] = random.choice(dialogues["sleep"])
                pet["state_duration"] = random.randint(120, 180)
            else:
                if current_state in ["idle", "walk_right", "walk_left"]:
                    current_state = "bored"
                    pet["status_text"] = random.choice(dialogues["bored"])
                    pet["state_duration"] = random.randint(80, 120)
                else:
                    current_state = "sleep"
                    pet["status_text"] = random.choice(dialogues["sleep"])
                    pet["state_duration"] = random.randint(80, 120)
            
        else:
            if current_state == "sleep":
                current_state = "idle"
                pet["status_text"] = "史萊姆揉了揉眼睛，繼續陪著主人。"
            else:
                if period in ["morning", "daytime"]:
                    current_state = random.choice(["idle", "walk_right", "walk_left", "idle"])
                else:
                    current_state = random.choice(["idle", "bored", "idle"])
                    
                pet["status_text"] = random.choice(dialogues["watching"])
                
            pet["state_duration"] = random.randint(60, 90)

# ==========================================
# 📺 畫布渲染引擎
# ==========================================
def render_canvas():
    canvas = [[" " for _ in range(40)] for _ in range(8)]
    frames = SLIME_ANIMATIONS.get(current_state, SLIME_ANIMATIONS["idle"])
    actual_frame = frames[frame_index % len(frames)]
    
    base_y = 4
    start_x = int(pet["x"])
    start_y = base_y + pet["y_offset"]
    
    for row_idx, line in enumerate(actual_frame):
        for col_idx, char in enumerate(line):
            # 同時判定並過濾標準空格與不中斷空格 \xa0
            if char == " " or char == "\xa0": 
                continue
            target_x = start_x + col_idx
            target_y = start_y + row_idx
            if 0 <= target_x < 40 and 0 <= target_y < 8:
                canvas[target_y][target_x] = char

    if current_state == "sleep":
        z_cycle = (frame_index // 2) % 3
        z_char = "z" if z_cycle == 0 else ("Z" if z_cycle == 1 else "O")
        zx, zy = start_x + 12 + z_cycle, start_y - 1 - z_cycle
        if 0 <= zx < 40 and 0 <= zy < 8:
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
    display_text.append(" ──────────────────────────────────────\n", style="bright_black")
    display_text.append(f"   {pet['status_text']}", style="italic white")

    companion_panel = Panel(
        display_text,
        title=" Slime Companion ",
        title_align="center",
        border_style="bright_black",
        box=rich.box.ROUNDED,
        width=44,
        height=12
    )
    return companion_panel

# ==========================================
# 🚀 主運行線程
# ==========================================
if __name__ == "__main__":
    try:
        while True:
            with Live(build_pet_world(), refresh_per_second=5, screen=True) as live:
                while True:
                    update_companion()
                    
                    if pet["trigger_clear_cmd"]:
                        pet["trigger_clear_cmd"] = False
                        break 
                        
                    live.update(build_pet_world())
                    time.sleep(0.2)
            
            os.system('cls' if os.name == 'nt' else 'clear')

    except KeyboardInterrupt:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print("[green]>>>[/green] [white]Companion process terminated safely.[/white]")
        sys.exit(0)