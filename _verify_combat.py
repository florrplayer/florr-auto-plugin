# -*- coding: utf-8 -*-
"""战斗模块离线验证: 颜色检测/坐标映射/目标选择/U避让/贴脸判定"""
import sys, os, math
import numpy as np
import cv2

sys.path.insert(0, r"C:\Users\intel\Downloads\florr-auto-pathing-main")
os.chdir(r"C:\Users\intel\Downloads\florr-auto-pathing-main")

import combat
from combat import (detect_mobs, screen_to_map, map_to_screen, choose_target,
                    ultra_blocked, build_avoid_map, is_kiss_point,
                    ULTRA_AVOID, ULTRA_KISS, DEVIATION, SCALE_PX_PER_UNIT)

# ---------- 1) 颜色检测: 合成 1920x1080 测试帧 ----------
frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
# M 怪(青 #1FDBDE = BGR(222,219,31))
cv2.rectangle(frame, (470, 370), (530, 430), (222, 219, 31), -1)
# U 怪(粉 #FF2B75 = BGR(117,43,255))
cv2.rectangle(frame, (1370, 670), (1420, 720), (117, 43, 255), -1)
# 玩家中心区域的小青块(应被排除)
cv2.rectangle(frame, (950, 530), (970, 550), (222, 219, 31), -1)
# 远处小青色点 6x6(应被面积过滤)
cv2.rectangle(frame, (200, 200), (206, 206), (222, 219, 31), -1)

mythics, ultras = detect_mobs(frame)
print(f"[1] 颜色检测: M={sorted(mythics)} (期望 [(500,400)]), U={sorted(ultras)} (期望 [(1395,695)])")
assert mythics == [(500, 400)], f"M 检测错误: {mythics}"
assert ultras == [(1395, 695)], f"U 检测错误: {ultras}"
print("    通过 ✓ (中心玩家色块与小花瓣已正确排除)")

# ---------- 2) 坐标映射往返 ----------
player = (150.0, 150.0)
s = map_to_screen(player, player)   # 玩家在屏幕中心
assert s == (960, 540), f"玩家应映射到屏幕中心: {s}"
s2 = map_to_screen((160.0, 150.0), player)
m2 = screen_to_map(s2, player)
err = math.hypot(m2[0]-160.0, m2[1]-150.0)
print(f"[2] 坐标映射: 地图(160,150) -> 屏幕{s2} -> 地图({m2[0]:.2f},{m2[1]:.2f}) 误差={err:.3f}px")
assert err < 0.5, "映射往返误差过大"
s3 = map_to_screen((150.0, 165.0), player)
m3 = screen_to_map(s3, player)
assert abs(m3[1]-165.0) < 0.5
print("    通过 ✓ (屏幕中心=玩家, 往返误差<0.5)")

# ---------- 3) 目标选择: 最近 + 不偏离巡逻点 ----------
# 玩家(100,100), 巡逻点(150,150): M1(120,110)近且偏离小; M2(200,300)偏离大; M3(250,120)远
t = choose_target([(250, 120), (200, 300), (120, 110)], (150, 150), (100, 100))
print(f"[3] 目标选择: 选 {t} (期望 (120,110) 附近)")
assert t is not None and abs(t[0]-120) < 1 and abs(t[1]-110) < 1
# 全部偏离巡逻点 -> None
t2 = choose_target([(200, 300)], (150, 150), (100, 100))
assert t2 is None, f"偏离巡逻点的怪不应被选: {t2}"
print("    通过 ✓ (最近优先, 偏离巡逻点>阈值的不打)")

# ---------- 4) U 贴脸判定 + 避让图 ----------
p = (150.0, 150.0)
near = ultra_blocked([(150.0, 153.0)], p)   # 距离3 < 5 -> 贴脸
far = ultra_blocked([(150.0, 160.0)], p)    # 距离10 > 5
print(f"[4] U贴脸判定: 距离3 -> {near} (期望检测到), 距离10 -> {far} (期望None)")
assert near == (150.0, 153.0) and far is None
binary = np.full((300, 300), 255, np.uint8)
avoid = build_avoid_map(binary, [(150.0, 150.0)], p)
assert avoid[150, 150] == 0 and avoid[145, 150] == 0 and avoid[150, 145] == 0
assert avoid[140, 150] == 255, "5px 外不应被堵"
print("    通过 ✓ (U 周围 5px 已设为障碍)")

# ---------- 5) 贴脸点判定 ----------
u = (150.0, 150.0)
kiss = (150.5, 150.0)
assert is_kiss_point(u, kiss, ULTRA_KISS)
assert not is_kiss_point(u, (160.0, 150.0), ULTRA_KISS)
print(f"[5] 贴脸点判定: 距U {ULTRA_KISS}px 判为贴脸 ✓")

print("\n=== 战斗模块离线验证全部通过 ===")
print(f"参数: SCALE_PX_PER_UNIT={SCALE_PX_PER_UNIT}(需游戏内微调) ULTRA_AVOID={ULTRA_AVOID} ULTRA_KISS={ULTRA_KISS} DEVIATION={DEVIATION}")
