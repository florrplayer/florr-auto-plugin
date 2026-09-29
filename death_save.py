"""
死亡自救逻辑:
- 检测死亡画面("You were destroyed by:")
- 如果在远处, 每10秒发 "ygg" 求复活
- 等2分钟没被复活就点Continue复活回家
- 如果身上有mark(黑暗标记)就不自动复活
"""
import time, re
from combat import get_frame, click
import numpy as np, cv2

death_state = {
    'dead': False,
    'dead_time': 0,
    'last_ygg': 0,
    'has_mark': False,
    'revived': False
}

def check_death(frame=None):
    """检测是否死亡画面, 返回True/False"""
    if frame is None:
        frame = get_frame()
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    # 死亡画面是暗色半透明覆盖层 + 红色/白色文字
    # 检测中央是否有 "Continue" 按钮区域
    h, w = frame.shape[:2]
    center = frame[h//3:2*h//3, w//3:2*w//3]
    gray = cv2.cvtColor(center, cv2.COLOR_BGR2GRAY)
    # 死亡画面整体偏暗
    mean = np.mean(gray)
    if mean < 40:  # 很暗
        return True
    return False

def send_chat(msg):
    """在游戏聊天发消息"""
    try:
        import keyboard
        keyboard.write(msg, delay=0.02)
        keyboard.press_and_release('enter')
        time.sleep(0.1)
    except:
        pass

def death_self_save():
    """死亡自救主逻辑,每帧调用"""
    now = time.time()
    frame = get_frame()
    dead = check_death(frame)

    if dead and not death_state['dead']:
        death_state['dead'] = True
        death_state['dead_time'] = now
        death_state['last_ygg'] = 0
        death_state['revived'] = False
        print('[死亡] 检测到死亡画面,开始自救...')

    if not dead and death_state['dead']:
        # 复活了
        print('[死亡] 已复活!')
        death_state['dead'] = False
        return

    if not death_state['dead']:
        return

    elapsed = now - death_state['dead_time']

    # 每10秒发ygg求复活
    if now - death_state['last_ygg'] > 10:
        send_chat('ygg')
        death_state['last_ygg'] = now
        print(f'[死亡] 发ygg求复活 ({elapsed:.0f}s)')

    # 2分钟没复活就点Continue
    if elapsed > 120:
        print('[死亡] 2分钟没人复活,点Continue回家')
        # Continue按钮在屏幕中央偏下
        h, w = frame.shape[:2]
        click(w//2, int(h*0.65))
        time.sleep(1)
        death_state['dead'] = False
