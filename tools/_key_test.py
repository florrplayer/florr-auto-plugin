# -*- coding: utf-8 -*-
"""实测: PostMessage 键盘是否真的让 florr 角色移动
方法: 连续 PrintWindow 截图, 发 WASD 方向键, 再截图, 对比玩家像素/画面差异
跨虚拟桌面: 当前桌面找不到窗口时自动切到桌面2找, 找到后立刻切回原桌面"""
import sys, os, time, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 上级目录=插件根
import numpy as np, cv2
import win32gui, win32api, win32con
from window_ctrl import get_window

w = get_window()
if not w:
    print("当前桌面没窗口, 临时切到桌面2找...")
    # 切到桌面2 (Win+Ctrl+Right)
    win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
    win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
    win32api.keybd_event(win32con.VK_RIGHT, 0, 0, 0)
    time.sleep(0.15)
    win32api.keybd_event(win32con.VK_RIGHT, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)
    time.sleep(1.2)
    # 重建 WindowController (内部会重新枚举)
    import importlib, window_ctrl
    importlib.reload(window_ctrl)
    w = get_window()
    if not w:
        print("!! 桌面2也没有窗口")
        sys.exit(1)
    # 已找到 -> 切回原桌面 (Win+Ctrl+Left)
    print("找到窗口, 切回原桌面...")
    win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
    win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
    win32api.keybd_event(win32con.VK_LEFT, 0, 0, 0)
    time.sleep(0.15)
    win32api.keybd_event(win32con.VK_LEFT, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)
    time.sleep(0.8)
else:
    print("当前桌面直接找到窗口")
print(f"窗口: hwnd={w.hwnd} 标题={w.title}")

def grab(tag):
    img = w.capture()  # PrintWindow
    if img is None:
        print(f"  {tag}: 截图失败")
        return None
    h, ww = img.shape[:2]
    print(f"  {tag}: {ww}x{h}")
    return img

def diff_ratio(a, b):
    if a is None or b is None: return -1
    if a.shape != b.shape:
        b = cv2.resize(b, (a.shape[1], a.shape[0]))
    d = cv2.absdiff(a, b)
    return float((d > 30).sum()) / d.size

# 基线
t0 = grab("before")
time.sleep(1.0)
t1 = grab("before2")
print(f"自然差异(1s): {diff_ratio(t0, t1)*100:.2f}%")

# 发 'd' 按住 1.5 秒
print("按 d 1.5s...")
w.key_down(0x44)
time.sleep(1.5)
w.key_up(0x44)
t2 = grab("after_d")
print(f"按d后差异: {diff_ratio(t1, t2)*100:.2f}%")

# 发 'w' 按住 1.5 秒
print("按 w 1.5s...")
w.key_down(0x57)
time.sleep(1.5)
w.key_up(0x57)
t3 = grab("after_w")
print(f"按w后差异: {diff_ratio(t2, t3)*100:.2f}%")

# 对比: 如果差异远大于自然差异 -> 画面在动 -> 键盘生效
# 保存截图供人工核验
os.makedirs("tools/_keytest", exist_ok=True)
for tag, img in [("t0", t0), ("t1", t1), ("td", t2), ("tw", t3)]:
    if img is not None:
        cv2.imwrite(f"tools/_keytest/{tag}.png", img)
print("截图已存 tools/_keytest/")
