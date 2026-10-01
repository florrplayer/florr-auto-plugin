# -*- coding: utf-8 -*-
"""profile 插件每帧核心路径 (合成真实尺寸帧, 纯CPU热点)"""
import time, random, sys, os
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import combat, utils
from combat import RANK_HSV, detect_all, detect_projectiles, detect_drops
from utils import get_player_position

# 合成 1365x672 帧 (同真实窗口), 随机撒稀有度彩点模拟怪
random.seed(42)
H, W = 672, 1365
frame = np.full((H, W, 3), (200, 195, 190), np.uint8)  # 沙色背景
for _ in range(40):  # 40只怪
    x, y = random.randint(40, W-40), random.randint(60, H-40)
    r = random.randint(6, 18)
    # 稀有度颜色随机 (取 RANK_HSV 中心色)
    rng = random.choice(list(RANK_HSV.values()))
    color = np.array(rng[0]) + (np.array(rng[1]) - np.array(rng[0])) // 2
    cv2.circle(frame, (x, y), r, (int(color[2]*0.5), int(color[1]*0.5), int(color[0]*0.5)), -1)

def bench(name, fn, n=50):
    t0 = time.perf_counter()
    for _ in range(n):
        fn()
    dt = (time.perf_counter() - t0) / n * 1000
    line = f"{name:40s} {dt:7.2f} ms/次"
    print(line, flush=True)
    with open('_profile_result.txt', 'a', encoding='utf-8') as f:
        f.write(line + '\n')
    return dt

open('_profile_result.txt', 'w', encoding='utf-8').close()

hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
bench("cvtColor BGR2HSV", lambda: cv2.cvtColor(frame, cv2.COLOR_BGR2HSV))
bench("detect_all(with_size)", lambda: detect_all(frame, with_size=True, hsv=hsv))
bench("detect_all(with_sid)", lambda: detect_all(frame, with_size=True, with_sid=True, hsv=hsv))
bench("detect_projectiles", lambda: detect_projectiles(frame, hsv=hsv))
bench("detect_drops(with_rank)", lambda: detect_drops(frame, hsv=hsv, with_rank=True))
bench("detect_mobs (M/U)", lambda: combat.detect_mobs(frame))
# get_player_position 路径: 8色 inRange+findContours (合成帧直接传入)
utils.MAP = "desert"
bench("get_player_position (8色)", lambda: get_player_position(image=frame))
# 纯 findContours 次数对比: 8次(当前) vs 1次(合并)
def cc8x():
    for rng in RANK_HSV.values():
        m = cv2.inRange(hsv, np.array(rng[0]), np.array(rng[1]))
        cv2.findContours(m, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
bench("8次inRange+findContours", cc8x)
def cc1x():
    m = np.zeros((H, W), np.uint8)
    for rng in RANK_HSV.values():
        m |= cv2.inRange(hsv, np.array(rng[0]), np.array(rng[1]))
    cv2.findContours(m, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
bench("1次合并inRange+findContours", cc1x)
