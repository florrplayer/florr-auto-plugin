# -*- coding: utf-8 -*-
"""smoke: 模拟主循环战斗分支函数链(合成帧+假窗口), 验证 v1.18.3 改动后核心路径无异常"""
import sys, os, random, time
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import utils, combat, mob_db
from utils import get_player_position, get_frame, check_stage, load_binary_map, apply_map
from combat import detect_all, detect_projectiles, detect_super, detect_special, detect_drops, detect_bossbar, get_hp_ratio, ultra_blocked, choose_target, RANK_ORDER, WARN_MARGIN

# screen_to_map_safe (main.py 实现内联): 屏幕坐标 -> 地图坐标
from combat import _downscale
def screen_to_map_safe(p, pos):
    px = pos[0] + (p[0] - W//2) / _downscale
    py = pos[1] + (p[1] - H//2) / _downscale
    return (px, py) if 2 <= px <= 297 and 2 <= py <= 297 else None

# 假窗口: capture 返回合成帧(玩家黄点+4只M怪+1只U怪+1个导弹)
H, W = 672, 1365
def make_frame(t):
    f = np.full((H, W, 3), (200, 195, 190), np.uint8)
    cv2.circle(f, (W//2, H//2), 5, (0x64, 0xDD, 0xF9), -1)      # 玩家黄点(左上角UI点用)
    cv2.circle(f, (300, 300), 12, (0xDE, 0x1F, 0x1F), -1)       # 传奇怪(红)
    cv2.circle(f, (900, 250), 10, (0xDB, 0xDE, 0x1F), -1)       # Mythic(青)
    cv2.circle(f, (1050, 500), 14, (0x2B, 0x75, 0xFF), -1)      # Ultra(粉)
    cv2.circle(f, (200, 550), 6, (0x1F, 0xDB, 0xDE), -1)        # 另一只M
    cv2.circle(f, (500, 400), 4, (0x2B, 0xFF, 0xA3), -1)        # Super薄荷绿(小=会被过滤)
    cv2.circle(f, (W//2+150, H//2+80), 3, (0xDE, 0x1F, 0x1F), -1)  # 飞行物(红小点)
    return f

class FakeWin:
    def __init__(self): self.hwnd = 1
    def capture(self, region=None): return make_frame(time.time())
    def client_center(self): return (W//2, H//2, W, H)
    def is_foreground(self): return True

import window_ctrl
window_ctrl._inst = FakeWin()
utils._FRAME.update({"t": 0.0, "img": None})
utils._CAPTURE_ON = False  # 同步模式(单帧smoke)

apply_map("desert")
frame = get_frame(force=True)
hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
pos = get_player_position(image=frame)
print("玩家定位:", pos)
rmap = detect_all(frame, with_size=True, with_sid=True, hsv=hsv)
print("detect_all 档位:", {k: len(v) for k, v in rmap.items()})
proj = detect_projectiles(frame, hsv=hsv)
print("projectiles:", proj)
sup = detect_super(frame, with_size=True, hsv=hsv)
print("super:", sup)
sp = detect_special(frame, "desert", with_size=True, hsv=hsv)
print("special:", {k: len(v) for k, v in sp.items()})
print("bossbar:", detect_bossbar(frame))
print("hp:", get_hp_ratio(frame))
print("stage:", check_stage(frame))
if pos:
    danger = [m for m in (screen_to_map_safe(p, pos) for r in RANK_ORDER[6:] for p in (rmap.get(r) or [])) if m]
    print("danger:", danger)
    near = ultra_blocked(danger, pos, margin=WARN_MARGIN)
    print("ultra_blocked:", near)
    prey = [m for m in (screen_to_map_safe(p, pos) for p in (rmap.get("mythic") or [])) if m]
    t = choose_target(prey, (100, 100), pos) if prey else None
    print("choose_target:", t)
print("=== SMOKE OK ===")
