# -*- coding: utf-8 -*-
"""一键综合诊断: 窗口/截图/小地图/玩家位置稳定性/键盘有效性/MU检测/移动链路
用法: 游戏开着时运行 -> py -3.12 tools\_diag.py
跨虚拟桌面: 当前桌面找不到窗口自动切桌面2找, 找到后切回"""
import sys, os, time, math, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, cv2
import win32gui, win32api, win32con

OK, BAD = "[OK] ", "[BAD] "
print("=" * 56)
print("florr 插件一键综合诊断")
print("=" * 56)

# ---------- 0. 找窗口 (跨桌面) ----------
from window_ctrl import get_window
w = get_window()
switched = False
if not w:
    print("当前桌面没窗口 -> 临时切桌面2...")
    win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
    win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
    win32api.keybd_event(win32con.VK_RIGHT, 0, 0, 0)
    time.sleep(0.15)
    win32api.keybd_event(win32con.VK_RIGHT, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)
    time.sleep(1.2)
    import importlib, window_ctrl
    importlib.reload(window_ctrl)
    w = get_window()
    switched = True
if not w:
    print("!! 两个桌面都没有 florr 窗口。请先打开游戏。")
    sys.exit(1)
print(f"{OK}窗口: {w.title}")
print(f"   hwnd={w.hwnd}")

# ---------- 1. 截图能力 ----------
from utils import get_frame, get_map, get_player_position
frame = get_frame()
if frame is None:
    print(f"{BAD}PrintWindow 截图失败!")
    sys.exit(1)
fh, fw = frame.shape[:2]
black = float((frame.sum(axis=2) < 60).mean())
print(f"{OK}截图 {fw}x{fh}, 黑色占比 {black*100:.1f}%" + ("" if black < 0.5 else f"  <- 画面可能黑屏/未渲染!"))

# ---------- 2. 小地图 ----------
try:
    from utils import _detect_minimap
    rect = _detect_minimap(frame)
    if rect:
        x, y, s = rect
        print(f"{OK}小地图 位置=({x},{y}) 边长={s}")
    else:
        print(f"{BAD}小地图未检测到(将用 fallback 估算)")
except Exception as e:
    print(f"   小地图检测异常: {e}")

# ---------- 3. 玩家位置稳定性 (10次采样) ----------
print("\n--- 玩家位置稳定性 (采样10次, 间隔0.4s) ---")
positions = []
for i in range(10):
    p = get_player_position()
    positions.append(p)
    time.sleep(0.4)
valid = [p for p in positions if p is not None]
if not valid:
    print(f"{BAD}10次采样全部 None -> 玩家点识别失败!")
else:
    xs = [p[0] for p in valid]; ys = [p[1] for p in valid]
    spread = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
    print(f"   采样 {len(valid)}/10 有效, 位置范围: X[{min(xs):.0f},{max(xs):.0f}] Y[{min(ys):.0f},{max(ys):.0f}]")
    print(f"   离散度: {spread:.1f} 地图单位" + (OK if spread < 5 else f" <- 位置漂移严重! 离散步={spread:.1f}"))
    print(f"   最近5个: {[(round(p[0]), round(p[1])) for p in valid[-5:]]}")

# ---------- 4. 键盘有效性 (发d键1.5s对比截图) ----------
print("\n--- 键盘有效性 (发 d 1.5s, 对比画面) ---")
if not switched:
    w.mouse_to_screen  # noop
def snap():
    return get_frame()
a = snap(); time.sleep(0.8); b = snap()
nat = float((cv2.absdiff(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), cv2.cvtColor(b, cv2.COLOR_BGR2GRAY)) > 30).mean())
w.key_down(0x44); time.sleep(1.5); w.key_up(0x44)
c = snap()
moved = float((cv2.absdiff(cv2.cvtColor(b, cv2.COLOR_BGR2GRAY), cv2.cvtColor(c, cv2.COLOR_BGR2GRAY)) > 30).mean())
print(f"   自然差异(0.8s): {nat*100:.2f}%")
print(f"   按d后差异(1.5s): {moved*100:.2f}%")
if moved > nat * 1.5 + 0.01:
    print(f"{OK}键盘 PostMessage 有效 (画面动了)")
elif moved < 0.02:
    print(f"{BAD}画面几乎没变 -> PostMessage 键盘没进游戏!")
    print("   -> 需换 SendInput/CDP 方案")
else:
    print(f"{BAD}差异太小/不稳定 -> 疑似键盘无效, 建议换方案")

# ---------- 5. M/U 检测 ----------
print("\n--- M/U 怪检测 ---")
try:
    from combat import detect_mobs
    m, u = detect_mobs(frame)
    print(f"   M(青) {len(m)} 个, U(粉) {len(u)} 个")
    for p in m[:5]:
        print(f"     M 屏幕({p[0]},{p[1]})")
except Exception as e:
    print(f"   detect_mobs 异常: {e}")

# ---------- 6. 切回原桌面 ----------
if switched:
    print("\n切回原桌面...")
    win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
    win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
    win32api.keybd_event(win32con.VK_LEFT, 0, 0, 0)
    time.sleep(0.15)
    win32api.keybd_event(win32con.VK_LEFT, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)
    time.sleep(0.6)
print("\n===== 诊断结束 =====")
