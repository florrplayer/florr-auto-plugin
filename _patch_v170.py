# -*- coding: utf-8 -*-
"""v1.7.0: 掉落价值筛选(只捡Epic以上) + 官方伤害威胁提示"""
import io, sys

def patch_one(path, old, new, tag):
    s = io.open(path, encoding="utf-8").read()
    if old not in s:
        print(f"!! [{tag}] 未找到锚点"); sys.exit(1)
    s = s.replace(old, new, 1)
    io.open(path, "w", encoding="utf-8", newline="").write(s)
    print(f"ok [{tag}]")

combat = r"C:\Users\intel\Downloads\florr-auto-pathing-main\combat.py"
main = r"C:\Users\intel\Downloads\florr-auto-pathing-main\main.py"

# ---------- combat.py ----------
# 1) import 补 os/json
patch_one(combat,
'''import time
import math
import numpy as np''',
'''import time
import math
import os
import json
import numpy as np''',
"combat:import_os_json")

# 2) detect_drops 加 with_rank
patch_one(combat,
'''def detect_drops(frame=None, exclude_center=True, hsv=None):
    """检测掉落花瓣: 小尺寸(3-11px)的稀有度彩色块(怪最小12px, 互补不冲突)
    排除中心玩家本体区域; 返回屏幕坐标列表; hsv 可传入已转换HSV图"""
    if frame is None:
        frame = get_frame()
    if hsv is None:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = np.zeros(hsv.shape[:2], np.uint8)
    for rng in RANK_HSV.values():
        m = cv2.inRange(hsv, np.array(rng[0]), np.array(rng[1]))
        mask = cv2.bitwise_or(mask, m)
    if exclude_center:
        cx, cy = get_screen_center()
        cv2.circle(mask, (cx, cy), EXCLUDE_CENTER_R, 0, -1)
    det_w = 960
    det_h = int(hsv.shape[0] / _downscale)
    small = cv2.resize(mask, (det_w, det_h), interpolation=cv2.INTER_NEAREST)
    n, labels, stats, cents = cv2.connectedComponentsWithStats(small, 8)
    pts = []
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA]
        w, h = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
        if not (DROP_MIN_PX * DROP_MIN_PX / 4 <= area <= DROP_MAX_PX * DROP_MAX_PX):
            continue
        if w * 4 < h or h * 4 < w:
            continue
        pts.append((int(cents[i][0] * _downscale), int(cents[i][1] * _downscale)))
    return pts''',
'''def detect_drops(frame=None, exclude_center=True, hsv=None, with_rank=False):
    """检测掉落花瓣: 小尺寸(3-11px)的稀有度彩色块(怪最小12px, 互补不冲突)
    排除中心玩家本体区域; 返回屏幕坐标列表; with_rank=True 时每点为 (x, y, rank)
    v1.7.0: 连通域中心像素判稀有度(掉落价值筛选用); hsv 可传入已转换HSV图"""
    if frame is None:
        frame = get_frame()
    if hsv is None:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = np.zeros(hsv.shape[:2], np.uint8)
    for rng in RANK_HSV.values():
        m = cv2.inRange(hsv, np.array(rng[0]), np.array(rng[1]))
        mask = cv2.bitwise_or(mask, m)
    if exclude_center:
        cx, cy = get_screen_center()
        cv2.circle(mask, (cx, cy), EXCLUDE_CENTER_R, 0, -1)
    det_w = 960
    det_h = int(hsv.shape[0] / _downscale)
    small = cv2.resize(mask, (det_w, det_h), interpolation=cv2.INTER_NEAREST)
    n, labels, stats, cents = cv2.connectedComponentsWithStats(small, 8)
    sh, sw = hsv.shape[:2]
    pts = []
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA]
        w, h = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
        if not (DROP_MIN_PX * DROP_MIN_PX / 4 <= area <= DROP_MAX_PX * DROP_MAX_PX):
            continue
        if w * 4 < h or h * 4 < w:
            continue
        px = int(cents[i][0] * _downscale)
        py = int(cents[i][1] * _downscale)
        if with_rank:
            if py >= sh or px >= sw:
                continue
            hh, ss, vv = hsv[min(py, sh - 1), min(px, sw - 1)]
            rank = None
            for rk, (lo, hi) in RANK_HSV.items():
                if lo[0] <= hh <= hi[0] and lo[1] <= ss <= hi[1] and lo[2] <= vv <= hi[2]:
                    rank = rk
                    break
            pts.append((px, py, rank))
        else:
            pts.append((px, py))
    return pts''',
"combat:detect_drops_with_rank")

# 3) 威胁数据加载 + 提示 (追加到文件尾)
patch_one(combat,
'''def get_hp_ratio(frame=None):''',
'''_THREAT = None
_RANK_ORDER7 = ["common", "unusual", "rare", "epic", "legendary", "mythic", "ultra"]


def threat_load():
    """懒加载官方怪威胁表 data/mob_threat.json (73怪 7档 伤害/血量/护甲/exp/掉落)"""
    global _THREAT
    if _THREAT is None:
        try:
            _p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "data", "mob_threat.json")
            _THREAT = json.load(open(_p, encoding="utf-8"))
        except Exception:
            _THREAT = {}
    return _THREAT


def threat_hint(sid, rank_idx=5):
    """目标怪威胁提示: 官方伤害/血量, rank_idx 对应 RANK_ORDER7 下标(默认5=Mythic)"""
    t = threat_load().get(sid)
    if not t:
        return ""
    try:
        return f"伤害{t['dmg'][rank_idx]}/血{t['hp'][rank_idx]}"
    except Exception:
        return ""


RANK_W = {"common": 0, "unusual": 1, "rare": 2, "epic": 3,
          "legendary": 4, "mythic": 5, "ultra": 6}


def get_hp_ratio(frame=None):''',
"combat:threat_table")

# ---------- main.py ----------
# 4) 配置: 只捡 Epic 以上掉落
patch_one(main,
'''PICKUP_DROPS = True     # 掉落自动拾取(顺路捡: 只捡距玩家<=PICKUP_RANGE的掉落)''',
'''PICKUP_DROPS = True     # 掉落自动拾取(顺路捡: 只捡距玩家<=PICKUP_RANGE的掉落)
PICKUP_MIN_RANK = 3      # v1.7.0 掉落价值筛选: 只捡稀有度权重>=此值的掉落(3=Epic, 垃圾掉落不浪费时间)''',
"main:pickup_min_rank")

# 5) 掉落段: with_rank 过滤
patch_one(main,
'''                    if time.time() - _last_drops > 0.3:
                        _drops_px = detect_drops(frame, hsv=hsv)
                        _last_drops = time.time()
                    drops = [m for m in (screen_to_map_safe(p, pos) for p in _drops_px) if m]''',
'''                    if time.time() - _last_drops > 0.3:
                        _drops_px = detect_drops(frame, hsv=hsv, with_rank=True)
                        _last_drops = time.time()
                    # v1.7.0 只捡值钱的掉落(稀有度权重>=PICKUP_MIN_RANK)
                    drops = [m for m in (screen_to_map_safe(p, pos) for p in _drops_px
                                         if p[2] and RANK_W.get(p[2], 0) >= PICKUP_MIN_RANK) if m]''',
"main:掉落价值筛选")

# 6) 战斗日志威胁提示
patch_one(main,
'''                        print(f"[战斗] 发现目标 {_tname}({kill_rank}) HP {_hp or '?'} {target}," + (f"  | M档掉落: {_drop}" if _drop else ""))''',
'''                        _thr = threat_hint(target[3], RANK_ORDER.index(kill_rank)) if len(target) > 3 else ""
                        print(f"[战斗] 发现目标 {_tname}({kill_rank}) HP {_hp or '?'} {target}" +
                              (f"  | {_thr}" if _thr else "") +
                              (f"  | M档掉落: {_drop}" if _drop else ""))''',
"main:威胁提示")

# 7) main 里引入 RANK_ORDER 与 threat_hint
patch_one(main,
'''                    from combat import (detect_all, ultra_blocked, choose_target,
                                        screen_to_map_safe, RANK_ORDER, WARN_MARGIN)''',
'''                    from combat import (detect_all, ultra_blocked, choose_target,
                                        screen_to_map_safe, RANK_ORDER, WARN_MARGIN,
                                        threat_hint, RANK_W)''',
"main:import_threat")

print("PATCHED_V170")
