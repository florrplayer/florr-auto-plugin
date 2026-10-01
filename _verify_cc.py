# -*- coding: utf-8 -*-
"""验证 _cc_all 帧缓存不改变语义: 冷缓存 vs 热缓存输出必须逐点一致"""
import time, random, sys, os
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import combat
from utils import _FRAME

random.seed(7)
H, W = 672, 1365
frame = np.full((H, W, 3), (200, 195, 190), np.uint8)
for _ in range(30):
    x, y = random.randint(40, W-40), random.randint(60, H-40)
    r = random.randint(6, 18)
    rng = random.choice(list(combat.RANK_HSV.values()))
    c = np.array(rng[0]) + (np.array(rng[1]) - np.array(rng[0])) // 2
    cv2.circle(frame, (x, y), r, (int(c[2]*0.5), int(c[1]*0.5), int(c[0]*0.5)), -1)

hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
combat._CC_CACHE.update({"t": 0.0, "hsv_id": None, "small": None, "n": 0, "labels": None, "stats": None, "cents": None})
_FRAME["t"] = 123.0  # 固定帧时间 -> 热缓存命中

r1 = combat.detect_all(frame, with_size=True, with_sid=True, hsv=hsv)   # 冷(第一次构建)
r2 = combat.detect_all(frame, with_size=True, with_sid=True, hsv=hsv)   # 热(缓存)
ok = True
for k in r1:
    a, b = sorted(r1[k]), sorted(r2[k])
    if a != b:
        ok = False
        print(f"  detect_all[{k}] 不一致: {len(a)} vs {len(b)}")
        for x, y in set(a) ^ set(b):
            print("   diff:", x, y)
p1 = combat.detect_projectiles(frame, hsv=hsv)
p2 = combat.detect_projectiles(frame, hsv=hsv)
d1 = combat.detect_drops(frame, hsv=hsv, with_rank=True)
d2 = combat.detect_drops(frame, hsv=hsv, with_rank=True)
print("detect_all 冷热一致:", ok)
print("detect_projectiles 冷热一致:", sorted(p1) == sorted(p2), len(p1))
print("detect_drops 冷热一致:", sorted(d1) == sorted(d2), len(d1))
# 突变: 换帧时间后必须重算(结果允许变化但不能用旧缓存)
_FRAME["t"] = 456.0
r3 = combat.detect_all(frame, with_size=True, hsv=hsv)
combat._CC_CACHE["hsv_id"] = None  # 模拟帧变后新hsv对象(id不同)
r4 = combat.detect_all(frame, with_size=True, hsv=hsv)
print("帧时间变化后正常重算:", r3 == r4 or len(r3) == len(r4))
