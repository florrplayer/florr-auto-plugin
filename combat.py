# -*- coding: utf-8 -*-
"""战斗模式: 只打 M 怪(Mythic 青), 避 U 怪(Ultra 粉) 5px, 贴脸 0.5px 后沿原路撤退

识别原理: florr 怪物本体颜色 = 稀有度颜色
  Mythic 青 #1FDBDE -> HSV ~(175, 87%, 87%)
  Ultra  粉 #FF2B75 -> HSV ~(340, 83%, 100%)
主画面截图 -> HSV 过滤 -> 连通块(排除玩家中心/花瓣小物件) -> 屏幕坐标
屏幕坐标 -> 地图坐标(玩家屏幕固定中心 + 标定缩放系数)
"""
import time
import math
import os
import json
import numpy as np
import cv2
from utils import get_frame, get_player_position, ARRIVE, set_screen_center
from mob_table import MOB_CN
from drop_table import mob_id2sid, petal_id2sid

# ===== v1.5.0 怪种识别 =====
RARITY_SIZE_FACTOR = {
    "common": 1.0, "unusual": 1.1, "rare": 1.3, "epic": 1.5,
    "legendary": 2.0,
    "mythic": 3.0, "ultra": 6.0,
    "super": 10.0,
}


def classify_mob(r_common, aspect, rect):
    """怪种识别 v1: 官方体型缩放把屏幕半径换算回 Common 基准, 按大小+形状分类"""
    aspect = max(aspect, 1.0)
    if aspect > 2.4:
        return "centipede" if r_common < 60 else "centipede_desert"
    if rect > 0.86 and aspect < 1.3:
        return "square"
    if aspect <= 1.35:
        if r_common < 11:
            return "rock"
        if r_common < 19:
            return "bee"
        if r_common < 30:
            return "ladybug"
        if r_common < 48:
            return "beetle"
        return "ant_hole"
    else:
        if r_common < 13:
            return "ant_baby"
        if r_common < 24:
            return "ant_worker"
        if r_common < 38:
            return "ant_soldier"
        if r_common < 60:
            return "hornet"
        return "ant_queen"


def mob_name(sid):
    if not sid:
        return "未知"
    return MOB_CN.get(sid, sid)

def mob_name_en(sid):
    if not sid:
        return ""
    try:
        from mob_db import mob_en_name
        n = mob_en_name(sid)
        return n if n and n != sid else ""
    except Exception:
        return ""


_DROP_CACHE = {"raw": None, "idx": None}

def _load_drops():
    if _DROP_CACHE["raw"] is not None:
        return _DROP_CACHE
    import json, os
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "florr_dropchance.json")
    try:
        raw = json.loads(open(p, encoding="utf-8").read())
    except Exception:
        raw = {}
    idx = {}
    for k, v in raw.items():
        mid, pid, r = k.split("|")
        psid = petal_id2sid.get(int(pid), "?")
        idx.setdefault((int(mid), int(r)), []).append((v, psid))
    for g in idx.values():
        g.sort(reverse=True)
    _DROP_CACHE["raw"] = raw
    _DROP_CACHE["idx"] = idx
    return _DROP_CACHE


_HP_CACHE = {"data": None}

def _fmt_hp(v):
    if v >= 100000000:
        return "%.2f亿" % (v / 100000000.0)
    if v >= 10000:
        return "%.1f万" % (v / 10000.0)
    return str(int(v))


def mob_hp(sid, rarity=5):
    if not sid:
        return None
    if _HP_CACHE["data"] is None:
        import json, os
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "mob_hp.json")
        try:
            _HP_CACHE["data"] = json.loads(open(p, encoding="utf-8").read())
        except Exception:
            _HP_CACHE["data"] = {}
    hp = _HP_CACHE["data"].get(sid, {}).get(str(rarity))
    if not hp:
        return None
    lo, hi = hp
    if lo == hi:
        return _fmt_hp(lo)
    return f"{_fmt_hp(lo)}-{_fmt_hp(hi)}"


def drop_hint(sid, rarity=5):
    if not sid:
        return ""
    mid = None
    for k, v in mob_id2sid.items():
        if v == sid:
            mid = k
            break
    if mid is None:
        return ""
    idx = _load_drops()["idx"]
    items = idx.get((int(mid), int(rarity)))
    if not items:
        return ""
    parts = []
    for c, psid in items[:4]:
        if c <= 0 or c < 0.0005:
            parts.append(f"{mob_name(psid)}<0.1%")
        else:
            parts.append(f"{mob_name(psid)} {c*100:.1f}%")
    return " ".join(parts)

# ===== 参数(可调) =====
MYTHIC_HSV = ((85, 100, 100), (100, 255, 255))
ULTRA_HSV = ((162, 100, 100), (178, 255, 255))
LEGENDARY_HSV = ((0, 100, 100), (8, 255, 255))
KILL_STOP = 0.5
BODY_CLEAR = 2.5
LEECH_CLEAR = 5.5
WARN_MARGIN = 10.0
CHASE_WARN = 8.0
KISS_SLOW = 3.0
PROJ_MIN_PX = 4
PROJ_MAX_PX = 24
PROJ_DODGE_R = 120
HP_BAR_Y = 30
HP_BAR_H = 4
HP_BAR_W = 50
HP_FLEE = 0.20
HP_RECOVER = 0.35
HEAL_TRIGGER = {"rose": 0.20, "dahlia": 0.30, "yucca": 0.20, "starfish": 0.40, "leaf": 0.25}
RANK_ORDER = ["common", "unusual", "rare", "epic", "legendary", "mythic", "ultra"]
RANK_HSV = {
    "common":    ((52, 120, 160), (60, 255, 255)),
    "unusual":   ((22, 140, 180), (28, 255, 255)),
    "rare":      ((116, 140, 180), (122, 255, 255)),
    "epic":      ((132, 140, 150), (140, 255, 255)),
    "legendary": ((0, 150, 150), (6, 255, 255)),
    "mythic":    MYTHIC_HSV,
    "ultra":     ULTRA_HSV,
}
_screen_center = [960, 540]
_downscale = 2.0
SCALE_PX_PER_UNIT = 5.0
WORLD_PER_MAPUNIT = 206.5
MIN_MOB_PX = 12
MAX_MOB_PX = 260
EXCLUDE_CENTER_R = 40
ULTRA_AVOID = 5.0
ULTRA_KISS = 0.5
DEVIATION = 30.0
SPECIAL_MOBS = [
    ("golden_leafbug",  ((18, 140, 130), (30, 255, 255)), ("jungle",), "nonround"),
    ("shiny_ladybug",   ((22, 140, 180), (28, 255, 255)), ("desert",), None),
    ("shiny",           ((0, 0, 190),    (180, 70, 255)), None,       None),
    ("diver_ant",       ((95, 60, 80),   (135, 255, 255)), ("ocean",), None),
    ("square",          ((20, 140, 150), (36, 255, 255)), None,       "square"),
]
SPECIAL_PRIORITY_ORDER = ["golden_leafbug", "shiny_ladybug", "shiny", "diver_ant", "square"]
SPECIAL_DEVIATION = 60.0
SPECIAL_MIN_PX = 10
SPECIAL_MAX_PX = 260


def _rectangularity(area, w, h):
    if w <= 0 or h <= 0:
        return 0.0
    return area / float(w * h)


def detect_special(frame=None, map_name=None, exclude_center=True, with_size=False, hsv=None):
    if frame is None:
        frame = get_frame()
    if hsv is None:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    det_w = 960
    det_h = int(hsv.shape[0] / _downscale)
    cx, cy = get_screen_center()
    out = {}
    for name, (lo, hi), maps, shape in SPECIAL_MOBS:
        if maps and (map_name is None or map_name not in maps):
            continue
        mask = cv2.inRange(hsv, np.array(lo), np.array(hi))
        if exclude_center:
            cv2.circle(mask, (cx, cy), EXCLUDE_CENTER_R, 0, -1)
        small = cv2.resize(mask, (det_w, det_h), interpolation=cv2.INTER_NEAREST)
        n, labels, stats, cents = cv2.connectedComponentsWithStats(small, 8)
        pts = []
        for i in range(1, n):
            area = stats[i, cv2.CC_STAT_AREA]
            w, h = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
            if not (SPECIAL_MIN_PX * SPECIAL_MIN_PX / 4 <= area <= SPECIAL_MAX_PX * SPECIAL_MAX_PX):
                continue
            if w > SPECIAL_MAX_PX * 1.5 or h > SPECIAL_MAX_PX * 1.5:
                continue
            if w * 4 < h or h * 4 < w:
                continue
            if shape == "square":
                if _rectangularity(area, w, h) < 0.85:
                    continue
            elif shape == "nonround":
                if area <= 0:
                    continue
                r2 = (max(w, h) / 2.0) ** 2
                if area / (3.14159265 * r2) > 0.9:
                    continue
            if with_size:
                ys, xs = np.nonzero(labels == i)
                if len(xs) >= 3:
                    (_, _), r_c = cv2.minEnclosingCircle(
                        np.column_stack((xs, ys)).astype(np.float32))
                    r_screen = round(float(r_c) * _downscale, 2)
                else:
                    r_screen = round(0.25 * (w + h) * _downscale, 2)
                pts.append((int(cents[i][0] * _downscale), int(cents[i][1] * _downscale), r_screen))
            else:
                pts.append((int(cents[i][0] * _downscale), int(cents[i][1] * _downscale)))
        if pts:
            out[name] = pts
    return out




def get_screen_center():
    return _screen_center[0], _screen_center[1]


def calibrate_screen(frame=None):
    global _screen_center, _downscale
    if frame is None:
        frame = get_frame()
    h, w = frame.shape[:2]
    _screen_center = [w // 2, h // 2]
    _downscale = w / 960.0
    set_screen_center(w, h)
    print(f"[标定] 实际窗口 {w}x{h}, 中心 {_screen_center}, 降采样 x{_downscale:.2f}")
    return w, h


def _detect_color(hsv, hsv_range, exclude_center=True, min_px=None, max_px=None, with_size=False,
                    with_sid=False, rank=None):
    lo = MIN_MOB_PX if min_px is None else min_px
    hi = MAX_MOB_PX if max_px is None else max_px
    mask = cv2.inRange(hsv, np.array(hsv_range[0]), np.array(hsv_range[1]))
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
        if not (lo * lo / 4 <= area <= hi * hi):
            continue
        if w > MAX_MOB_PX * 1.5 or h > MAX_MOB_PX * 1.5:
            continue
        if w * 4 < h or h * 4 < w:
            continue
        cx_s, cy_s = cents[i]
        if with_size:
            ys, xs = np.nonzero(labels == i)
            if len(xs) >= 3:
                (_, _), r_c = cv2.minEnclosingCircle(
                    np.column_stack((xs, ys)).astype(np.float32))
                r_screen = round(float(r_c) * _downscale, 2)
            else:
                r_screen = round(0.25 * (w + h) * _downscale, 2)
            if with_sid:
                factor = RARITY_SIZE_FACTOR.get(rank or "", 1.0)
                r_common = r_screen / factor if factor else r_screen
                rw, rh = float(w), float(h)
                aspect = max(rw, rh) / max(min(rw, rh), 1e-6)
                rect = area / float(w * h) if w * h > 0 else 0.0
                pts.append((int(cx_s * _downscale), int(cy_s * _downscale),
                            r_screen, classify_mob(r_common, aspect, rect)))
            else:
                pts.append((int(cx_s * _downscale), int(cy_s * _downscale), r_screen))
        else:
            pts.append((int(cx_s * _downscale), int(cy_s * _downscale)))
    return pts


DROP_MIN_PX = 3
DROP_MAX_PX = 11
PICKUP_RANGE = 60.0


def detect_drops(frame=None, exclude_center=True, hsv=None, with_rank=False):
    if frame is None:
        frame = get_frame()
    if hsv is None:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    small, n, labels, stats, cents = _cc_all(hsv)
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
    return pts


SUPER_HSV = ((72, 120, 150), (82, 255, 255))
SUPER_MIN_R_PX = 18.0
AFK_DARK_MEAN = 70


def detect_super(frame=None, with_size=False, hsv=None):
    if frame is None:
        frame = get_frame()
    if hsv is None:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    pts = _detect_color(hsv, SUPER_HSV, with_size=with_size)
    if with_size:
        return [p for p in pts if p[2] >= SUPER_MIN_R_PX * _downscale]
    return pts


def screen_r_to_map(r_screen):
    return r_screen * SCALE_PX_PER_UNIT / WORLD_PER_MAPUNIT


def detect_afk_check(frame, prev_gray_center=None):
    try:
        h, w = frame.shape[:2]
        cx, cy = get_screen_center()
        rw, rh = int(w * 0.30), int(h * 0.30)
        x0, x1 = max(0, cx - rw), min(w, cx + rw)
        y0, y1 = max(0, cy - rh), min(h, cy + rh)
        gray = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
        m = float(gray.mean())
        static = prev_gray_center is not None and abs(m - prev_gray_center) < 5
        return m < AFK_DARK_MEAN, static, m
    except Exception:
        return False, False, 999.0


def solve_afk_drag(frame=None):
    try:
        if frame is None:
            frame = get_frame()
        h, w = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        gmask = cv2.inRange(hsv, (45, 150, 150), (85, 255, 255))
        gmask[:h//5, :] = 0; gmask[4*h//5:, :] = 0
        gmask[:, :w//5] = 0; gmask[:, 4*w//5:] = 0
        n, labels, stats, _ = cv2.connectedComponentsWithStats(gmask)
        if n < 2:
            return False, 0, 0, []
        best = max(range(1, n), key=lambda i: stats[i, cv2.CC_STAT_AREA])
        sx = int(stats[best, cv2.CC_STAT_LEFT] + stats[best, cv2.CC_STAT_WIDTH] / 2)
        sy = int(stats[best, cv2.CC_STAT_TOP] + stats[best, cv2.CC_STAT_HEIGHT] / 2)
        pathmask = cv2.inRange(hsv, (0, 50, 100), (180, 255, 255))
        pathmask = pathmask & (~gmask)
        pathmask[:h//5, :] = 0; pathmask[4*h//5:, :] = 0
        pathmask[:, :w//5] = 0; pathmask[:, 4*w//5:] = 0
        pathmask = cv2.dilate(pathmask, np.ones((5,5), np.uint8), iterations=1)
        from collections import deque
        visited = np.zeros((h, w), dtype=bool)
        parent = {}
        q = deque([(sx, sy)]); visited[sy, sx] = True
        end = (sx, sy); maxd = 0
        while q:
            x, y = q.popleft()
            d = ((x-sx)**2 + (y-sy)**2)**0.5
            if d > maxd: maxd = d; end = (x, y)
            for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                nx, ny = x+dx, y+dy
                if 0<=nx<w and 0<=ny<h and not visited[ny,nx] and pathmask[ny,nx]>0:
                    visited[ny,nx] = True
                    parent[(nx,ny)] = (x,y)
                    q.append((nx,ny))
        if maxd < 20:
            return False, 0, 0, []
        rev = []
        cur = end
        while cur in parent:
            rev.append(cur)
            cur = parent[cur]
        rev.append((sx, sy))
        rev.reverse()
        path_points = rev[::5]
        if path_points[-1] != end:
            path_points.append(end)
        print(f"[AFK-DRAG] 绿点({sx},{sy})->终点({end[0]},{end[1]}) 迷宫路径{len(path_points)}点")
        return True, sx, sy, path_points
    except Exception as e:
        print(f"[AFK-DRAG] 异常: {e}")
        return False, 0, 0, []


def detect_mobs(frame=None):
    """检测 M/U 怪, 返回 (mythics, ultras) 屏幕坐标列表
    v1.34: M/U 两个 mask 合并成一次降采样+连通域(2次CC->1次), 逐连通域按中心5x5平均HSV分拣"""
    if frame is None:
        frame = get_frame()
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(MYTHIC_HSV[0]), np.array(MYTHIC_HSV[1]))
    mask |= cv2.inRange(hsv, np.array(ULTRA_HSV[0]), np.array(ULTRA_HSV[1]))
    cx, cy = get_screen_center()
    cv2.circle(mask, (cx, cy), EXCLUDE_CENTER_R, 0, -1)
    det_w = 960
    det_h = int(hsv.shape[0] / _downscale)
    small = cv2.resize(mask, (det_w, det_h), interpolation=cv2.INTER_NEAREST)
    n, _, stats, cents = cv2.connectedComponentsWithStats(small, 8)
    mythics, ultras = [], []
    m_lo, m_hi = np.array(MYTHIC_HSV[0]), np.array(MYTHIC_HSV[1])
    u_lo, u_hi = np.array(ULTRA_HSV[0]), np.array(ULTRA_HSV[1])
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA]
        w, h = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
        if not (MIN_MOB_PX * MIN_MOB_PX / 4 <= area <= MAX_MOB_PX * MAX_MOB_PX):
            continue
        if w > MAX_MOB_PX * 1.5 or h > MAX_MOB_PX * 1.5:
            continue
        if w * 4 < h or h * 4 < w:
            continue
        cxs, cys = cents[i]
        sx = int(cxs * _downscale)
        sy = int(cys * _downscale)
        sy = max(0, min(sy, hsv.shape[0] - 1))
        sx = max(0, min(sx, hsv.shape[1] - 1))
        y0, y1 = max(0, sy - 2), min(hsv.shape[0] - 1, sy + 2)
        x0, x1 = max(0, sx - 2), min(hsv.shape[1] - 1, sx + 2)
        patch = hsv[y0:y1 + 1, x0:x1 + 1].reshape(-1, 3).astype(int)
        h_mean = int(patch[:, 0].mean())
        s_mean = int(patch[:, 1].mean())
        v_mean = int(patch[:, 2].mean())
        if m_lo[0] <= h_mean <= m_hi[0] and m_lo[1] <= s_mean <= m_hi[1] and m_lo[2] <= v_mean <= m_hi[2]:
            mythics.append((sx, sy))
        elif u_lo[0] <= h_mean <= u_hi[0] and u_lo[1] <= s_mean <= u_hi[1] and u_lo[2] <= v_mean <= u_hi[2]:
            ultras.append((sx, sy))
    return mythics, ultras


def detect_legendary(frame=None):
    if frame is None:
        frame = get_frame()
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    return _detect_color(hsv, LEGENDARY_HSV)


_CC_CACHE = {"t": 0.0, "hsv_id": None, "small": None, "n": 0, "labels": None, "stats": None, "cents": None}
def _cc_all(hsv):
    from utils import _FRAME
    t = _FRAME["t"]
    if _CC_CACHE["t"] == t and _CC_CACHE["hsv_id"] == id(hsv) and _CC_CACHE["small"] is not None:
        return (_CC_CACHE["small"], _CC_CACHE["n"], _CC_CACHE["labels"],
                _CC_CACHE["stats"], _CC_CACHE["cents"])
    mask = np.zeros((hsv.shape[0], hsv.shape[1]), np.uint8)
    for rng in RANK_HSV.values():
        mask |= cv2.inRange(hsv, np.array(rng[0]), np.array(rng[1]))
    cx, cy = get_screen_center()
    cv2.circle(mask, (cx, cy), EXCLUDE_CENTER_R, 0, -1)
    det_w = 960
    det_h = int(hsv.shape[0] / _downscale)
    small = cv2.resize(mask, (det_w, det_h), interpolation=cv2.INTER_NEAREST)
    n, labels, stats, cents = cv2.connectedComponentsWithStats(small, 8)
    _CC_CACHE.update({"t": t, "hsv_id": id(hsv), "small": small, "n": n,
                      "labels": labels, "stats": stats, "cents": cents})
    return small, n, labels, stats, cents


def detect_all(frame=None, with_size=False, with_sid=False, hsv=None):
    if frame is None:
        frame = get_frame()
    if hsv is None:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    small, n, labels, stats, cents = _cc_all(hsv)
    h, w = hsv.shape[:2]
    out = {rk: [] for rk in RANK_HSV}
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA]
        cw, ch = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
        if not (MIN_MOB_PX * MIN_MOB_PX / 4 <= area <= MAX_MOB_PX * MAX_MOB_PX):
            continue
        if cw > MAX_MOB_PX * 1.5 or ch > MAX_MOB_PX * 1.5:
            continue
        if cw * 4 < ch or ch * 4 < cw:
            continue
        px = int(cents[i][0] * _downscale)
        py = int(cents[i][1] * _downscale)
        if py >= h or px >= w:
            continue
        hh, ss, vv = hsv[min(py, h - 1), min(px, w - 1)]
        rank = None
        for rk, (lo, hi) in RANK_HSV.items():
            if lo[0] <= hh <= hi[0] and lo[1] <= ss <= hi[1] and lo[2] <= vv <= hi[2]:
                rank = rk
                break
        if rank is None:
            continue
        if with_size or with_sid:
            ys, xs = np.nonzero(labels == i)
            if len(xs) >= 3:
                (_, _), r_c = cv2.minEnclosingCircle(
                    np.column_stack((xs, ys)).astype(np.float32))
                r_screen = round(float(r_c) * _downscale, 2)
            else:
                r_screen = round(0.25 * (cw + ch) * _downscale, 2)
            if with_sid:
                factor = RARITY_SIZE_FACTOR.get(rank or "", 1.0)
                r_common = r_screen / factor if factor else r_screen
                rw, rh = float(cw), float(ch)
                aspect = max(rw, rh) / max(min(rw, rh), 1e-6)
                rect = area / float(cw * ch) if cw * ch > 0 else 0.0
                out[rank].append((px, py, r_screen, classify_mob(r_common, aspect, rect)))
            else:
                out[rank].append((px, py, r_screen))
        else:
            out[rank].append((px, py))
    return out


def detect_mobs_classified(frame=None):
    if frame is None:
        frame = get_frame()
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    out = {}
    out["mythic"] = _detect_color(hsv, MYTHIC_HSV, with_size=True, with_sid=True, rank="mythic")
    out["ultra"] = _detect_color(hsv, ULTRA_HSV, with_size=True, with_sid=True, rank="ultra")
    out["super"] = [p for p in _detect_color(hsv, SUPER_HSV, with_size=True, with_sid=True, rank="super")
                    if p[2] >= SUPER_MIN_R_PX * _downscale]
    return out


def escape_direction(ranks_map, player_map=None, sectors=8, binary=None,
                    look_ahead=15, wall_radius=3):
    if player_map is None:
        player_map = get_player_position()
    counts = [0.0] * sectors
    walls = [0.0] * sectors
    for pts in ranks_map.values():
        for p in (pts or []):
            m = screen_to_map(p, player_map)
            if not m:
                continue
            ang = math.degrees(math.atan2(m[1] - player_map[1], m[0] - player_map[0])) % 360
            d = math.hypot(m[0] - player_map[0], m[1] - player_map[1])
            counts[int(ang / (360 / sectors)) % sectors] += 1.0 / max(d, 2.0)
    if binary is not None:
        h, w = binary.shape
        for s in range(sectors):
            ang = math.radians((s + 0.5) * (360 / sectors))
            tx = int(player_map[0] + math.cos(ang) * look_ahead)
            ty = int(player_map[1] + math.sin(ang) * look_ahead)
            x0, x1 = max(0, tx - wall_radius), min(w - 1, tx + wall_radius)
            y0, y1 = max(0, ty - wall_radius), min(h - 1, ty + wall_radius)
            region = binary[y0:y1 + 1, x0:x1 + 1]
            walls[s] = 1.0 - float(region.mean()) / 255.0
    best = min(range(sectors), key=lambda k: counts[k] + walls[k] * 2.5)
    ang = math.radians((best + 0.5) * (360 / sectors))
    return math.cos(ang), math.sin(ang)


_PROJ_PREV = {"mask": None}


def detect_projectiles(frame=None, hsv=None):
    global _PROJ_PREV
    if frame is None:
        frame = get_frame()
    if hsv is None:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    small, n, labels, stats, cents = _cc_all(hsv)
    moving = []
    if _PROJ_PREV["mask"] is not None and _PROJ_PREV["mask"].shape == small.shape:
        diff = cv2.absdiff(small, _PROJ_PREV["mask"])
        n2, labels2, stats2, cents2 = cv2.connectedComponentsWithStats(diff, 8)
        for i in range(1, n2):
            area = stats2[i, cv2.CC_STAT_AREA]
            w_, h_ = stats2[i, cv2.CC_STAT_WIDTH], stats2[i, cv2.CC_STAT_HEIGHT]
            if not (PROJ_MIN_PX * PROJ_MIN_PX / 4 <= area <= PROJ_MAX_PX * PROJ_MAX_PX):
                continue
            if w_ > PROJ_MAX_PX * 1.5 or h_ > PROJ_MAX_PX * 1.5:
                continue
            moving.append((int(cents2[i][0] * _downscale), int(cents2[i][1] * _downscale)))
    _PROJ_PREV["mask"] = small.copy()
    return moving


_HP_MAX = {"v": 0}


_THREAT = None
_RANK_ORDER7 = ["common", "unusual", "rare", "epic", "legendary", "mythic", "ultra"]


def threat_load():
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
    t = threat_load().get(sid)
    if not t:
        return ""
    parts = []
    try:
        parts.append(f"伤害{t['dmg'][rank_idx]}/血{t['hp'][rank_idx]}")
    except Exception:
        pass
    try:
        e = t["exp"][rank_idx]
        if e:
            parts.append(f"经验{e}")
    except Exception:
        pass
    try:
        names = []
        for pid, ch in t.get("drops", [])[:3]:
            nm = PETAL_CN.get(pid) or petal_id2sid.get(pid, f"花瓣{pid}")
            kd = PETAL_KIND.get(str(pid)) or PETAL_KIND.get(pid, "")
            tag = f"({kd})" if kd in ("回血",) else ""
            names.append(f"{nm}{tag}{ch*100:.1f}%")
        if names:
            parts.append("掉:" + "/".join(names))
    except Exception:
        pass
    return " ".join(parts)


RANK_W = {"common": 0, "unusual": 1, "rare": 2, "epic": 3,
          "legendary": 4, "mythic": 5, "ultra": 6}

PETAL_KIND = {"1":"伤/血","2":"伤/血","3":"伤/血","4":"功能","5":"回血","6":"伤/血","7":"伤/血","8":"伤/血","9":"伤/血","10":"伤/血","11":"伤/血","12":"伤/血","13":"血","14":"伤/血","15":"伤/血","16":"血","17":"功能","18":"伤/血","19":"伤/血","20":"伤/血","21":"血","22":"回血","23":"伤/血","24":"伤/血","25":"伤/血","26":"伤/血","27":"伤/血","28":"回血","29":"伤/血","30":"回血","31":"回血","32":"伤/血","33":"伤/血","34":"伤/血","35":"伤/血","36":"伤/血","37":"伤","38":"回血","39":"伤/血","40":"功能","41":"伤/血","42":"回血","43":"功能","44":"伤/血","45":"功能","46":"伤/血","47":"血","48":"功能","49":"回血","50":"伤/血","51":"血","52":"伤/血","53":"血","54":"功能","55":"伤/血","56":"血","57":"伤/血","58":"伤/血","59":"伤/血","60":"血","61":"血","62":"伤/血","63":"伤/血","64":"伤/血","65":"功能","66":"血","67":"伤/血","68":"伤/血","69":"伤","70":"回血","71":"伤/血","72":"功能","73":"功能","74":"伤/血","75":"伤/血","76":"功能","77":"伤/血","78":"伤","79":"伤","80":"功能","81":"血","82":"伤/血","83":"功能","84":"伤/血","85":"伤/血","86":"伤/血","87":"功能","88":"伤/血","89":"功能","90":"伤/血","91":"功能","92":"功能","93":"功能","94":"伤/血","95":"伤/血","96":"血","97":"伤/血","98":"伤/血","99":"回血","100":"功能","101":"伤/血","102":"血","103":"功能","104":"功能","105":"回血","106":"血","107":"伤/血","108":"功能","109":"伤/血","110":"血","111":"伤/血","112":"伤/血","113":"伤/血","114":"伤/血","115":"功能","116":"功能","117":"血","118":"功能"}


PETAL_CN = {
    1: "基础", 2: "轻", 3: "岩石", 4: "正方形", 5: "玫瑰", 6: "刺针",
    7: "鸢尾", 8: "翅膀", 9: "导弹", 10: "葡萄", 11: "仙人掌", 12: "加速",
    13: "泡泡", 14: "花粉", 15: "蒲公英", 16: "甲虫卵", 17: "触角", 18: "重石",
    19: "阴阳", 20: "网", 21: "蜂蜜", 22: "叶子", 23: "盐", 24: "米",
    25: "玉米", 26: "沙子", 27: "蟹钳", 28: "丝兰", 29: "磁铁", 30: "世界树",
    31: "海星", 32: "珍珠", 33: "闪电", 34: "果冻", 35: "钳", 36: "贝壳",
    37: "切割", 38: "大丽花", 39: "铀", 40: "海绵", 41: "土", 42: "牙",
    43: "第三只眼", 44: "豌豆", 45: "棍", 46: "幸运草", 47: "粉", 48: "空气",
    49: "罗勒", 50: "橙子", 51: "蚁卵", 52: "便便", 53: "遗迹", 54: "莲花",
    55: "球茎", 56: "棉花", 57: "胡萝卜", 58: "骨头", 59: "木板", 60: "番茄",
    61: "标记", 62: "橡胶", 63: "血刺", 64: "苍耳", 65: "根", 66: "安卡",
    67: "骰子", 68: "护符", 69: "电池", 70: "护身符", 71: "罗盘", 72: "圆盘",
    73: "铲", 75: "筹码", 76: "卡", 77: "月亮", 78: "女贞", 79: "玻璃", 80: "腐化",
    81: "法球", 90: "珊瑚", 92: "邪眼", 93: "拟态", 94: "雷神锤", 95: "机甲导弹",
    96: "蜂蜡", 97: "金叶", 98: "齿轮", 99: "龟背竹", 100: "机甲触角", 101: "激光",
    102: "多米诺", 103: "绷带", 104: "法老王冠", 105: "图腾", 106: "三角",
    107: "电网", 110: "黏土", 111: "灰尘", 112: "西兰花", 113: "扁豆", 114: "枯叶",
    116: "护目镜", 117: "豆",
}


def get_hp_ratio(frame=None):
    global _HP_MAX
    if frame is None:
        frame = get_frame()
    h, w = frame.shape[:2]
    cx, cy = get_screen_center()
    x0, x1 = max(0, cx - HP_BAR_W), min(w - 1, cx + HP_BAR_W)
    y0, y1 = max(0, cy + HP_BAR_Y - HP_BAR_H), min(h - 1, cy + HP_BAR_Y + HP_BAR_H)
    if y1 <= y0 or x1 <= x0:
        return None
    reg = frame[y0:y1 + 1, x0:x1 + 1].astype(int)
    r, g, b = reg[:, :, 2], reg[:, :, 1], reg[:, :, 0]
    red = (r > 140) & (r - g > 60) & (r - b > 60)
    filled = int(red.sum())
    if filled <= 0:
        return None
    if filled > _HP_MAX["v"]:
        _HP_MAX["v"] = filled
    return min(filled / max(_HP_MAX["v"], 1), 1.0)


def screen_to_map(screen_pt, player_map=None):
    if player_map is None:
        player_map = get_player_position()
    if player_map is None:
        return None
    cx, cy = get_screen_center()
    dx_world = (screen_pt[0] - cx) * SCALE_PX_PER_UNIT
    dy_world = (screen_pt[1] - cy) * SCALE_PX_PER_UNIT
    return (player_map[0] + dx_world / WORLD_PER_MAPUNIT,
            player_map[1] + dy_world / WORLD_PER_MAPUNIT)


def map_to_screen(map_pt, player_map=None):
    if player_map is None:
        player_map = get_player_position()
    if player_map is None:
        return None
    cx, cy = get_screen_center()
    dx_map = map_pt[0] - player_map[0]
    dy_map = map_pt[1] - player_map[1]
    return (int(cx + dx_map * WORLD_PER_MAPUNIT / SCALE_PX_PER_UNIT),
            int(cy + dy_map * WORLD_PER_MAPUNIT / SCALE_PX_PER_UNIT))


def choose_target(mythics_map, patrol_goal, player_map=None, dev_limit=None):
    if player_map is None:
        player_map = get_player_position()
    if player_map is None or not mythics_map:
        return None
    if dev_limit is None:
        dev_limit = DEVIATION + math.hypot(player_map[0] - patrol_goal[0],
                                           player_map[1] - patrol_goal[1])
    best, best_d = None, float("inf")
    for m in mythics_map:
        d = math.hypot(m[0] - player_map[0], m[1] - player_map[1])
        dev = math.hypot(m[0] - patrol_goal[0], m[1] - patrol_goal[1])
        if d < best_d and dev <= dev_limit:
            best, best_d = m, d
    return best


def ultra_blocked(ultras_map, player_map=None, margin=ULTRA_AVOID):
    if player_map is None:
        player_map = get_player_position()
    if player_map is None:
        return None
    nearest, nd = None, float("inf")
    for u in ultras_map:
        d = math.hypot(u[0] - player_map[0], u[1] - player_map[1])
        if d < nd:
            nearest, nd = u, d
    return nearest if nd <= margin else None


def build_avoid_map(binary, ultras_map, player_map=None, margin=ULTRA_AVOID):
    avoid = binary.copy()
    for u in ultras_map:
        if player_map is not None:
            if math.hypot(u[0] - player_map[0], u[1] - player_map[1]) > margin * 4:
                continue
        cx, cy = int(u[0]), int(u[1])
        cv2.circle(avoid, (cx, cy), int(margin), 0, -1)
    return avoid


def is_kiss_point(u_map, p, kiss=ULTRA_KISS):
    return math.hypot(p[0] - u_map[0], p[1] - u_map[1]) <= kiss + 0.3


HEAL_HSV = [
    ("rose/dahlia", (150, 60, 120), (180, 255, 255)),
    ("leaf/yucca",  (35, 80, 100),  (85, 255, 255)),
    ("starfish",    (5, 80, 100),   (22, 255, 255)),
]
SLOT_BAND_TOP = 0.80
SLOT_BAND_BOT = 0.995
SLOT_ROWS = 2
SLOT_COLS = 10


def scan_heal_slots(img=None):
    if img is None:
        img = get_frame()
    from utils import _canvas_y_offset
    h, w = img.shape[:2]
    off = _canvas_y_offset
    top = off + int((h - off) * SLOT_BAND_TOP)
    bot = off + int((h - off) * SLOT_BAND_BOT)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    found = []
    row_h = (bot - top) / SLOT_ROWS
    col_w = w / SLOT_COLS
    for r in range(SLOT_ROWS):
        y0 = int(top + r * row_h); y1 = int(top + (r + 1) * row_h)
        for i in range(SLOT_COLS):
            x0 = int(i * col_w); x1 = int((i + 1) * col_w)
            names = []
            for name, lo, hi in HEAL_HSV:
                m = cv2.inRange(hsv[y0:y1, x0:x1], np.array(lo), np.array(hi))
                if cv2.countNonZero(m) > 25:
                    names.append(name)
            if names:
                found.append((r, i + 1, "/".join(names)))
    return found


def draw_heal_slots_mark(img, found, out_path):
    from utils import _canvas_y_offset
    h, w = img.shape[:2]
    off = _canvas_y_offset
    top = off + int((h - off) * SLOT_BAND_TOP)
    bot = off + int((h - off) * SLOT_BAND_BOT)
    mark = img.copy()
    row_h = (bot - top) / SLOT_ROWS
    col_w = w / SLOT_COLS
    for r in (0, 1):
        y0 = int(top + r * row_h); y1 = int(top + (r + 1) * row_h)
        color = (0, 255, 0) if r == 0 else (255, 0, 0)
        cv2.rectangle(mark, (0, y0), (w - 1, y1), color, 2)
        cv2.putText(mark, f"ROW{r}", (10, y0 + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    for r, s, names in found:
        y0 = int(top + r * row_h); y1 = int(top + (r + 1) * row_h)
        x0 = int((s - 1) * col_w); x1 = int(s * col_w)
        cv2.rectangle(mark, (x0, y0), (x1, y1), (0, 255, 255), 2)
        cv2.putText(mark, f"{s}:{names}", (x0 + 6, y0 + 32), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.imwrite(out_path, mark)
    return mark



RANK_SCORE = {"common": 1, "unusual": 2, "rare": 4, "epic": 8,
              "legendary": 16, "mythic": 32, "ultra": 64}

def scan_petal_ranks(img=None):
    if img is None:
        img = get_frame()
    if img is None or img.size == 0 or img.shape[0] < 50 or img.shape[1] < 50:
        return {}, {}
    from utils import _canvas_y_offset
    h, w = img.shape[:2]
    off = _canvas_y_offset
    top = off + int((h - off) * SLOT_BAND_TOP)
    bot = off + int((h - off) * SLOT_BAND_BOT)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    row_h = (bot - top) / SLOT_ROWS
    col_w = w / SLOT_COLS
    counts = {r: 0 for r in RANK_HSV}
    per_slot = {}
    for r in range(SLOT_ROWS):
        y0 = int(top + r * row_h); y1 = int(top + (r + 1) * row_h)
        for i in range(SLOT_COLS):
            x0 = int(i * col_w); x1 = int((i + 1) * col_w)
            region = hsv[y0:y1, x0:x1]
            best = None; best_n = 0
            for rank, (lo, hi) in RANK_HSV.items():
                n = cv2.countNonZero(cv2.inRange(region, np.array(lo), np.array(hi)))
                if n > best_n:
                    best_n, best = n, rank
            if best and best_n > 25:
                counts[best] += 1
                per_slot[(r, i + 1)] = best
    return counts, per_slot


def rank_recommend(counts):
    if not any(counts.values()):
        return None
    main = max((r for r, c in counts.items() if c), key=lambda r: (RANK_SCORE[r], counts[r]))
    order = list(RANK_HSV.keys())
    idx = order.index(main)
    rec = order[max(0, idx - 1)] if idx > 0 else order[0]
    return main, rec


def detect_bossbar(frame=None):
    if frame is None:
        frame = get_frame()
    try:
        from utils import _canvas_y_offset
    except Exception:
        _canvas_y_offset = 0
    h, w = frame.shape[:2]
    off = _canvas_y_offset
    y0 = off + int((h - off) * 0.005)
    y1 = off + int((h - off) * 0.075)
    if y1 <= y0 + 2 or w < 200:
        return False
    reg = frame[y0:y1 + 1, :, :].astype(int)
    r, g, b = reg[:, :, 2], reg[:, :, 1], reg[:, :, 0]
    red = (r > 120) & (r - g > 50) & (r - b > 50)
    xc0, xc1 = int(w * 0.30), int(w * 0.70)
    col_red = red[:, xc0:xc1].sum(axis=0)
    seg = 0; best = 0
    for v in col_red:
        if v > 2:
            seg += 1; best = max(best, seg)
        else:
            seg = 0
    return best > w * 0.10
