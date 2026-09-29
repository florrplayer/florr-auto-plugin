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
# 官方体型缩放表(相对 Common, Unofficial Florr Data Spreadsheet): Unusual x1.1 / Rare x1.3 / Epic x1.5 / Mythic x3 / Super x10
# Legendary(表未列, 按趋势插值~x2) / Ultra(表未列, Mythic~Super 之间估 x6) -> 标注估算
RARITY_SIZE_FACTOR = {
    "common": 1.0, "unusual": 1.1, "rare": 1.3, "epic": 1.5,
    "legendary": 2.0,   # 估算
    "mythic": 3.0, "ultra": 6.0,   # ultra 估算(官方表未列)
    "super": 10.0,
}
# 形状分类树(按 Common 基准半径 + 宽高比 + 矩形度 -> 怪种 sid)
# 阈值基于官方图形知识初版, 实测误判可截图校准(同玩家点校准法)


def classify_mob(r_common, aspect, rect):
    """怪种识别 v1: 用官方体型缩放把屏幕半径换算回 Common 基准, 按大小+形状分类
    返回 sid(未识别返回 None)"""
    aspect = max(aspect, 1.0)
    if aspect > 2.4:
        # 长条 -> 蜈蚣系
        return "centipede" if r_common < 60 else "centipede_desert"
    if rect > 0.86 and aspect < 1.3:
        return "square"                     # 方方正正 -> 正方形
    if aspect <= 1.35:
        # 圆形系
        if r_common < 11:
            return "rock"                   # 最小圆 -> 岩石
        if r_common < 19:
            return "bee"                    # 小圆 -> 蜜蜂
        if r_common < 30:
            return "ladybug"                # 中圆 -> 瓢虫
        if r_common < 48:
            return "beetle"                 # 大圆 -> 甲虫
        return "ant_hole"                   # 超大圆 -> 蚁穴
    else:
        # 椭圆系
        if r_common < 13:
            return "ant_baby"               # 极小椭圆 -> 幼蚁
        if r_common < 24:
            return "ant_worker"             # 小椭圆 -> 工蚁
        if r_common < 38:
            return "ant_soldier"            # 中椭圆 -> 兵蚁
        if r_common < 60:
            return "hornet"                 # 大椭圆 -> 黄蜂
        return "ant_queen"                  # 超大椭圆 -> 蚁后


def mob_name(sid):
    """怪种 sid -> 中文名(官方 73 sid 映射, 未收录显示原 sid)"""
    if not sid:
        return "未知"
    return MOB_CN.get(sid, sid)


_DROP_CACHE = {"raw": None, "idx": None}


def _load_drops():
    """懒加载官方掉率表(florr_dropchance.json, _Util_CalculateDropChance 实测 332 条)
    -> idx[(mob_id, rarity)] = [(chance, petal_sid)...]"""
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
    """数字 -> 中文缩写显示: 157950 -> 15.8万, 218700000 -> 2.19亿"""
    if v >= 100000000:
        return "%.2f亿" % (v / 100000000.0)
    if v >= 10000:
        return "%.1f万" % (v / 10000.0)
    return str(int(v))


def mob_hp(sid, rarity=5):
    """目标怪官方血量(v1.5.2, data/mob_hp.json): 返回 "15.8万" 或 None"""
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
    """目标怪掉落提示(v1.5.1): 返回 "rose 8.9% / stinger 94.1%" 之类短句
    rarity: 5=Mythic 6=Ultra; 无数据返回空串"""
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
# HSV 阈值(OpenCV 尺度: H 0-179 = 度数/2, S/V 0-255)
# Mythic 青 #1FDBDE: 真H 181° -> OpenCV H 90, S 222, V 222
# Ultra  粉 #FF2B75: 真H 339° -> OpenCV H 170, S 212, V 255
# (Legendary 红 H=0, 与粉/青均不冲突)
MYTHIC_HSV = ((85, 100, 100), (100, 255, 255))   # M 怪 青色
ULTRA_HSV = ((162, 100, 100), (178, 255, 255))   # U 怪 粉色
LEGENDARY_HSV = ((0, 100, 100), (8, 255, 255))     # 传奇 红 #DE1F1F (OpenCV H 0-4, 与青/粉不冲突)
KILL_STOP = 0.5                          # 追击贴脸距离(地图像素, 用户要求 0.5)
BODY_CLEAR = 2.5                         # 打怪: 目标点外移到 怪半径+2.5 地图单位(停在碰撞箱外, 不撞上去)
LEECH_CLEAR = 5.5                        # 蹭掉落: 站定点外移到 怪半径+5.5 (高稀有度大怪更远站定, 不撞身体)
WARN_MARGIN = 10.0                       # 危险怪预警距离: 进入10px内提前绕开(人先躲远)
CHASE_WARN = 8.0                         # 打怪中危险怪进入8px内停手逃跑
KISS_SLOW = 3.0                          # 贴脸减速区: 3px内放慢试探(人犹豫贴脸)
PROJ_MIN_PX = 4                            # 飞行物最小尺寸(导弹/螯针比怪小)
PROJ_MAX_PX = 24                           # 飞行物最大尺寸(含Mythic+大导弹, 降采样960宽基准)
PROJ_DODGE_R = 120                         # 飞行物进入玩家周围120px内才闪避
HP_BAR_Y = 30                            # 玩家脚下血条位置: 中心下方30px(屏幕px, 默认HUD)
HP_BAR_H = 4                             # 血条半高(px)
HP_BAR_W = 50                            # 血条半宽(px)
HP_FLEE = 0.20                           # 血量低于20% 跑路(维基攻略建议提前切回血, 防秒杀)
HP_RECOVER = 0.35                        # 血量恢复到35% 才回去继续
# 回血花瓣种类 -> 低血触发线(研究落地: 玫瑰爆发20%救急/大丽花稳定30%/丝兰防御20%/海星被动40%提前切)
HEAL_TRIGGER = {"rose": 0.20, "dahlia": 0.30, "yucca": 0.20, "starfish": 0.40, "leaf": 0.25}
# 全稀有度颜色(怪本体色=稀有度色): 普通绿/罕见黄/稀有蓝/史诗紫/传奇红/神话青/究极粉
RANK_ORDER = ["common", "unusual", "rare", "epic", "legendary", "mythic", "ultra"]
# 精确色相(OpenCV H=真角度/2) + 高S/V防背景误检; 绿/黄/蓝按实测收紧(M/U已校准不动)
RANK_HSV = {
    "common":    ((52, 120, 160), (60, 255, 255)),
    "unusual":   ((22, 140, 180), (28, 255, 255)),
    "rare":      ((116, 140, 180), (122, 255, 255)),
    "epic":      ((132, 140, 150), (140, 255, 255)),
    "legendary": ((0, 150, 150), (6, 255, 255)),
    "mythic":    MYTHIC_HSV,
    "ultra":     ULTRA_HSV,
}
_screen_center = [960, 540]                       # 实际窗口中心(启动时标定, 兼容4K)
_downscale = 2.0                                   # 降采样比例(实际宽/检测宽, 标定后自动设)
SCALE_PX_PER_UNIT = 5.0                          # 世界单位/像素(1px=5世界单位, 经验值需标定)
WORLD_PER_MAPUNIT = 206.5                        # 世界单位/地图像素(desert 61952/300)
MIN_MOB_PX = 12                                  # 怪物最小屏幕尺寸(过滤花瓣/粒子)
MAX_MOB_PX = 260                                 # 怪物最大屏幕尺寸(过滤大色块)
EXCLUDE_CENTER_R = 40                            # 排除玩家自身区域半径(屏幕px)
ULTRA_AVOID = 5.0                                # 避开 U 距离(地图像素)
ULTRA_KISS = 0.5                                 # 贴脸距离(地图像素)
DEVIATION = 30.0                                 # 打 M 不偏离巡逻点超过该距离(地图像素)
# ===== 特殊稀有生物优先打(用户点名) =====
# 正方形(亮黄方形/10血100%掉正方形花瓣) / shiny闪亮(白亮高光, 如闪亮瓢虫掉Yggdrasil)
# 金叶虫(金黄, 仅丛林, Ultra+才掉黄金之叶) / 潜水兵蚁(蓝灰, 仅海洋)
# 颜色为初版估计(依据维基外观描述), 地图/形状过滤防误检; 实测误检漏检截图后可精调(同玩家点#F9DD64校准)
SPECIAL_MOBS = [
    # (名称, HSV区间, 地图白名单(仅这些图检测), 形状判定)
    # 形状: "square"=矩形度>0.85(方) / "nonround"=矩形度<0.85(非圆, 叶虫形) / None=不限
    ("golden_leafbug",  ((18, 140, 130), (30, 255, 255)), ("jungle",), "nonround"),
    ("shiny_ladybug",   ((22, 140, 180), (28, 255, 255)), ("desert",), None),
    ("shiny",           ((0, 0, 190),    (180, 70, 255)), None,       None),
    ("diver_ant",       ((95, 60, 80),   (135, 255, 255)), ("ocean",), None),
    ("square",          ((20, 140, 150), (36, 255, 255)), None,       "square"),
]
# 优先级按挂机价值: 金叶虫(黄金之叶) > 黄瓢虫(Yggdrasil) > shiny(白亮) > 潜水兵蚁 > 正方形(0.0001%几乎遇不到)
# ⚠️ 黄瓢虫与罕见黄怪同黄色段, 初版仅靠"沙漠+尺寸"过滤, 实测误检可截图精调(同玩家点校准)
SPECIAL_PRIORITY_ORDER = ["golden_leafbug", "shiny_ladybug", "shiny", "diver_ant", "square"]
SPECIAL_DEVIATION = 60.0          # 特殊怪放宽偏离巡逻点限制(稀有生物值得追)
SPECIAL_MIN_PX = 10
SPECIAL_MAX_PX = 260


def _rectangularity(area, w, h):
    """矩形度(连通域面积/外接矩形面积): 正方形≈1.0, 圆形≈0.785, 长条≈0.5"""
    if w <= 0 or h <= 0:
        return 0.0
    return area / float(w * h)


def detect_special(frame=None, map_name=None, exclude_center=True, with_size=False, hsv=None):
    """检测特殊稀有生物, 返回 {名称: [屏幕坐标]}; with_size=True 时每点为 (x, y, r)
    square=亮黄方形(矩形度>0.88), shiny=白亮高光, golden_leafbug=金黄(仅丛林), diver_ant=蓝灰(仅海洋)
    hsv 可传入已转换的HSV图(主循环共享一次cvtColor, 提速)"""
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
                # 方形判定: 面积/外接矩形≈1.0 是方形, 圆形≈0.785, 排除圆形怪
                if _rectangularity(area, w, h) < 0.85:
                    continue
            elif shape == "nonround":
                # 非圆判定: 圆度=面积/外接圆面积(圆≈0.98, 椭圆≈0.5-0.8, 方>1)
                # 金叶虫=金色叶虫形(非圆), 罕见黄怪=圆形 -> 圆度>0.9 排除
                if area <= 0:
                    continue
                r2 = (max(w, h) / 2.0) ** 2
                if area / (3.14159265 * r2) > 0.9:
                    continue
            if with_size:
                # 实际碰撞箱: 轮廓最小外接圆半径(圆形怪=真实图形半径)
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
    """标定实际窗口客户区尺寸, 设置屏幕中心和降采样比例(兼容4K/DPI缩放)
    返回 (实际宽, 实际高)"""
    global _screen_center, _downscale
    if frame is None:
        frame = get_frame()
    h, w = frame.shape[:2]
    _screen_center = [w // 2, h // 2]
    # 检测图统一缩到 960 宽(保持比例), 降采样比例 = 实际宽/960
    _downscale = w / 960.0
    set_screen_center(w, h)
    print(f"[标定] 实际窗口 {w}x{h}, 中心 {_screen_center}, 降采样 x{_downscale:.2f}")
    return w, h


def _detect_color(hsv, hsv_range, exclude_center=True, min_px=None, max_px=None, with_size=False,
                    with_sid=False, rank=None):
    """按 HSV 区间找色块, 返回中心点列表(屏幕坐标); min_px/max_px 可覆盖怪尺寸范围
    with_size=True 时每点加近似半径(屏幕像素, 怪碰撞箱参考): (x, y, r)
    with_sid=True 时每点为 (x, y, r, sid): 按官方体型缩放表换算 Common 基准半径 + 形状特征分类怪种
      (rank='mythic' 等稀有度键, 决定体型缩放系数)"""
    lo = MIN_MOB_PX if min_px is None else min_px
    hi = MAX_MOB_PX if max_px is None else max_px
    mask = cv2.inRange(hsv, np.array(hsv_range[0]), np.array(hsv_range[1]))
    if exclude_center:
        cx, cy = get_screen_center()
        cv2.circle(mask, (cx, cy), EXCLUDE_CENTER_R, 0, -1)
    # 降采样检测(统一960宽, 提速), 标定后自动适配实际分辨率
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
        # 怪近似圆形, 长条色块(草丛/水纹/墙影)滤掉
        cx_s, cy_s = cents[i]
        if with_size:
            # 实际碰撞箱: florr 碰撞检测=圆形hitbox, 半径=轮廓最小外接圆(圆形怪=真实图形半径)
            ys, xs = np.nonzero(labels == i)
            if len(xs) >= 3:
                (_, _), r_c = cv2.minEnclosingCircle(
                    np.column_stack((xs, ys)).astype(np.float32))
                r_screen = round(float(r_c) * _downscale, 2)
            else:
                r_screen = round(0.25 * (w + h) * _downscale, 2)
            if with_sid:
                # 怪种识别: 基准半径 = 屏幕半径 / 官方体型缩放; 形状特征(宽高比/矩形度)用降采样图统计
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
            pts.append((int(cx_s * _downscale), int(cy_s * _downscale)))   # 还原全分辨率坐标
    return pts


DROP_MIN_PX = 3          # 掉落花瓣最小屏幕尺寸(px)
DROP_MAX_PX = 11         # 掉落最大尺寸: 怪最小MIN_MOB_PX=12, 两者互补
PICKUP_RANGE = 30.0      # 掉落距玩家地图像素<=该值才去捡(只顺路捡近的)


def detect_drops(frame=None, exclude_center=True, hsv=None, with_rank=False):
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
    return pts


# Super 超级怪: 薄荷绿描边 #2BFFA3(UI色, 博客园配色表2023-04-05); 精确身体色需游戏截图实测
SUPER_HSV = ((72, 120, 150), (82, 255, 255))   # 实测 #2BFFA3 -> HSV(77,212,255)
# 官方体型缩放表(Unofficial Florr Data Spreadsheet, 游戏数据): 怪体型相对 Common
#   Unusual x1.1 / Rare x1.3 / Epic x1.5 / Mythic x3 / Super x10
# Super 怪 = 普通怪 10 倍体型(比 M 怪大 3.3 倍) -> 用最小半径过滤薄荷绿小色块误检
# SUPER_MIN_R_PX: 960宽基准下的最小半径(自动乘降采样还原), Super 至少 M 怪最小尺寸的 3 倍
SUPER_MIN_R_PX = 18.0
AFK_DARK_MEAN = 70      # AFK弹窗: 屏幕中心区域灰度均值低于该值视为暗遮罩


def detect_super(frame=None, with_size=False, hsv=None):
    """检测 Super 级怪(薄荷绿), 返回屏幕坐标列表; with_size=True 时每点为 (x, y, r)
    官方体型: Super=Common x10 -> 薄荷绿小色块(半径<下限)直接忽略, 防误检; hsv 可传入已转换HSV图"""
    if frame is None:
        frame = get_frame()
    if hsv is None:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    pts = _detect_color(hsv, SUPER_HSV, with_size=with_size)
    if with_size:
        return [p for p in pts if p[2] >= SUPER_MIN_R_PX * _downscale]
    return pts


def screen_r_to_map(r_screen):
    """屏幕像素半径 -> 地图单位半径(怪碰撞箱在追停点里用的单位)"""
    return r_screen * SCALE_PX_PER_UNIT / WORLD_PER_MAPUNIT


def detect_afk_check(frame, prev_gray_center=None):
    """检测 AFK Check 弹窗("Are you here?", 60秒不点踢下线):
    特征=屏幕中心大区域暗色遮罩(mean<AFK_DARK_MEAN)且画面静止(与上帧中心均值差<5)
    返回 (中心是否暗, 画面是否静止, 中心灰度均值)"""
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
    """自动解决挂机检测拖动验证(支持直线/L形/曲线/Z形任意路径):
    找亮绿色圆点(起点) -> BFS沿灰色路径走到最远点 -> 分段拖动
    返回 (True, sx, sy, path_points) 或 (False,...)"""
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
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        pathmask = cv2.inRange(gray, 50, 190)
        pathmask[:h//5, :] = 0; pathmask[4*h//5:, :] = 0
        pathmask[:, :w//5] = 0; pathmask[:, 4*w//5:] = 0
        from collections import deque
        visited = np.zeros((h, w), dtype=bool)
        q = deque([(sx, sy)]); visited[sy, sx] = True
        end = (sx, sy); maxd = 0
        while q:
            x, y = q.popleft()
            d = ((x-sx)**2 + (y-sy)**2)**0.5
            if d > maxd: maxd = d; end = (x, y)
            for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                nx, ny = x+dx, y+dy
                if 0<=nx<w and 0<=ny<h and not visited[ny,nx] and pathmask[ny,nx]>0:
                    visited[ny,nx] = True; q.append((nx,ny))
        path_points = []
        for t in range(11):
            path_points.append((int(sx+(end[0]-sx)*t/10), int(sy+(end[1]-sy)*t/10)))
        print(f"[AFK-DRAG] 绿点({sx},{sy})->终点({end[0]},{end[1]}) 路径{len(path_points)}点")
        return True, sx, sy, path_points
    except Exception as e:
        print(f"[AFK-DRAG] 异常: {e}")
        return False, 0, 0, []


def detect_mobs(frame=None):
    """检测 M/U 怪, 返回 (mythics, ultras) 屏幕坐标列表"""
    if frame is None:
        frame = get_frame()
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mythics = _detect_color(hsv, MYTHIC_HSV)
    ultras = _detect_color(hsv, ULTRA_HSV)
    return mythics, ultras


def detect_legendary(frame=None):
    """检测传奇怪(红色 #DE1F1F), 返回屏幕坐标列表"""
    if frame is None:
        frame = get_frame()
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    return _detect_color(hsv, LEGENDARY_HSV)


def detect_all(frame=None, with_size=False, with_sid=False, hsv=None):
    """检测所有稀有度等级的怪, 返回 {rank: [屏幕坐标]}; with_size=True 时每点为 (x, y, r)
    with_sid=True 时每点为 (x, y, r, sid): 怪种识别(按官方体型缩放+形状分类, 稀有度缩放系数内置)
    hsv 可传入已转换HSV图(主循环共享一次cvtColor, 提速)
    v1.6.0: 7档合并为1次连通域分析, 连通域中心单像素判档(原每档各跑一次全图CC, 快~3倍)"""
    if frame is None:
        frame = get_frame()
    if hsv is None:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    h, w = hsv.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    for rng in RANK_HSV.values():
        mask |= cv2.inRange(hsv, np.array(rng[0]), np.array(rng[1]))
    cx, cy = get_screen_center()
    cv2.circle(mask, (cx, cy), EXCLUDE_CENTER_R, 0, -1)
    det_w = 960
    det_h = int(h / _downscale)
    small = cv2.resize(mask, (det_w, det_h), interpolation=cv2.INTER_NEAREST)
    n, labels, stats, cents = cv2.connectedComponentsWithStats(small, 8)
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
    """检测 M/U/Super 怪并识别怪种, 返回 dict:
    {"mythic": [(x, y, r, sid)...], "ultra": [...], "super": [...]}
    主循环战斗日志用, 显示怪种中文名"""
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
    """分 8 个扇区, 返回"怪少且前方开阔"的扇区方向(单位向量); binary=地图灰度图(255可走/0墙)"""
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
            counts[int(ang / (360 / sectors)) % sectors] += 1.0 / max(d, 2.0)   # 近怪权重大, 人逃命躲近的
    if binary is not None:
        h, w = binary.shape
        for s in range(sectors):
            ang = math.radians((s + 0.5) * (360 / sectors))
            tx = int(player_map[0] + math.cos(ang) * look_ahead)
            ty = int(player_map[1] + math.sin(ang) * look_ahead)
            x0, x1 = max(0, tx - wall_radius), min(w - 1, tx + wall_radius)
            y0, y1 = max(0, ty - wall_radius), min(h - 1, ty + wall_radius)
            region = binary[y0:y1 + 1, x0:x1 + 1]
            walls[s] = 1.0 - float(region.mean()) / 255.0   # 1=全墙 0=全开阔
    # 综合评分: 怪少优先, 前方墙多扣分(不往墙角跑)
    best = min(range(sectors), key=lambda k: counts[k] + walls[k] * 2.5)
    ang = math.radians((best + 0.5) * (360 / sectors))
    return math.cos(ang), math.sin(ang)


_PROJ_PREV = {"mask": None}


def detect_projectiles(frame=None, hsv=None):
    """检测飞行物(黄蜂/胡蜂导弹, 蝎子螯针等):
    全稀有度色 + 小尺寸(4-16px) + 帧间差分(运动物体才算); hsv 可传入已转换HSV图"""
    global _PROJ_PREV
    if frame is None:
        frame = get_frame()
    if hsv is None:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask_all = np.zeros((hsv.shape[0], hsv.shape[1]), np.uint8)
    for rng in RANK_HSV.values():
        mask_all |= cv2.inRange(hsv, np.array(rng[0]), np.array(rng[1]))
    cx, cy = get_screen_center()
    cv2.circle(mask_all, (cx, cy), EXCLUDE_CENTER_R, 0, -1)
    det_w = 960
    det_h = int(hsv.shape[0] / _downscale)
    small = cv2.resize(mask_all, (det_w, det_h), interpolation=cv2.INTER_NEAREST)
    moving = []
    if _PROJ_PREV["mask"] is not None and _PROJ_PREV["mask"].shape == small.shape:
        diff = cv2.absdiff(small, _PROJ_PREV["mask"])
        n, labels, stats, cents = cv2.connectedComponentsWithStats(diff, 8)
        for i in range(1, n):
            area = stats[i, cv2.CC_STAT_AREA]
            w_, h_ = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
            if not (PROJ_MIN_PX * PROJ_MIN_PX / 4 <= area <= PROJ_MAX_PX * PROJ_MAX_PX):
                continue
            if w_ > PROJ_MAX_PX * 1.5 or h_ > PROJ_MAX_PX * 1.5:
                continue
            moving.append((int(cents[i][0] * _downscale), int(cents[i][1] * _downscale)))
    _PROJ_PREV["mask"] = small.copy()
    return moving


_HP_MAX = {"v": 0}


_THREAT = None
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
    """目标怪威胁提示: 官方伤害/血量/经验 + 掉落花瓣名(v1.7.1 全数据驱动)"""
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
            # 只标特殊花瓣(回血/功能), 普通伤/血花瓣不标(每片都有, 噪音)
            tag = f"({kd})" if kd in ("回血",) else ""
            names.append(f"{nm}{tag}{ch*100:.1f}%")
        if names:
            parts.append("掉:" + "/".join(names))
    except Exception:
        pass
    return " ".join(parts)


RANK_W = {"common": 0, "unusual": 1, "rare": 2, "epic": 3,
          "legendary": 4, "mythic": 5, "ultra": 6}

# 花瓣 id -> 功能分类(从官方 petals tooltip 自动提取, v1.7.3)
PETAL_KIND = {"1":"伤/血","2":"伤/血","3":"伤/血","4":"功能","5":"回血","6":"伤/血","7":"伤/血","8":"伤/血","9":"伤/血","10":"伤/血","11":"伤/血","12":"伤/血","13":"血","14":"伤/血","15":"伤/血","16":"血","17":"功能","18":"伤/血","19":"伤/血","20":"伤/血","21":"血","22":"回血","23":"伤/血","24":"伤/血","25":"伤/血","26":"伤/血","27":"伤/血","28":"回血","29":"伤/血","30":"回血","31":"回血","32":"伤/血","33":"伤/血","34":"伤/血","35":"伤/血","36":"伤/血","37":"伤","38":"回血","39":"伤/血","40":"功能","41":"伤/血","42":"回血","43":"功能","44":"伤/血","45":"功能","46":"伤/血","47":"血","48":"功能","49":"回血","50":"伤/血","51":"血","52":"伤/血","53":"血","54":"功能","55":"伤/血","56":"血","57":"伤/血","58":"伤/血","59":"伤/血","60":"血","61":"血","62":"伤/血","63":"伤/血","64":"伤/血","65":"功能","66":"血","67":"伤/血","68":"伤/血","69":"伤","70":"回血","71":"伤/血","72":"功能","73":"功能","74":"伤/血","75":"伤/血","76":"功能","77":"伤/血","78":"伤","79":"伤","80":"功能","81":"血","82":"伤/血","83":"功能","84":"伤/血","85":"伤/血","86":"伤/血","87":"功能","88":"伤/血","89":"功能","90":"伤/血","91":"功能","92":"功能","93":"功能","94":"伤/血","95":"伤/血","96":"血","97":"伤/血","98":"伤/血","99":"回血","100":"功能","101":"伤/血","102":"血","103":"功能","104":"功能","105":"回血","106":"血","107":"伤/血","108":"功能","109":"伤/血","110":"血","111":"伤/血","112":"伤/血","113":"伤/血","114":"伤/血","115":"功能","116":"功能","117":"血","118":"功能"}


# 花瓣 id -> 中文名(中文维基常用名, v1.7.1 全数据驱动战斗日志)
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
    """检测玩家脚下血条(红色填充), 返回 0-1 血量比例(自适应标定满血); 检测不到返回 None"""
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
        return None  # 没检测到血条(可能关闭了"显示个人资源")
    if filled > _HP_MAX["v"]:
        _HP_MAX["v"] = filled
    return min(filled / max(_HP_MAX["v"], 1), 1.0)


def screen_to_map(screen_pt, player_map=None):
    """屏幕坐标 -> 地图坐标(0-300 地图像素)"""
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
    """地图坐标 -> 屏幕坐标(用于朝怪移动)"""
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
    """从候选目标里挑: 距离最近 且 不偏离巡逻点

    偏离容忍 = DEVIATION + 玩家到巡逻点的距离(走路途中顺路打, 快到了不乱跑)
    dev_limit 可覆盖(特殊稀有生物放宽限制)
    patrol_goal: 当前巡逻目标点(地图坐标)。返回目标地图坐标或 None
    """
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
    """U 怪是否贴着玩家(进入 margin 地图像素内) -> 返回最近的 U 地图坐标或 None"""
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
    """把 U 怪周围 margin 地图像素设为墙, 返回 (新图, 是否与巡逻路径冲突)

    若 U 圈住了必经通道(玩家与目标间所有路径都穿过 U 圈) -> 冲突
    """
    avoid = binary.copy()
    for u in ultras_map:
        if player_map is not None:
            # 太远的 U 不影响局部避让(只处理玩家周围 2*margin 内)
            if math.hypot(u[0] - player_map[0], u[1] - player_map[1]) > margin * 4:
                continue
        cx, cy = int(u[0]), int(u[1])
        cv2.circle(avoid, (cx, cy), int(margin), 0, -1)
    return avoid


def is_kiss_point(u_map, p, kiss=ULTRA_KISS):
    """p 是否在 U 的 kiss 距离上(贴脸点判定)"""
    return math.hypot(p[0] - u_map[0], p[1] - u_map[1]) <= kiss + 0.3


# ===== 回血花瓣自动扫描(副槽识别) =====
# 回血花瓣(维基查证): 玫瑰/大丽花=粉色, 叶子/丝兰=绿色, 海星=橙色
HEAL_HSV = [
    ("rose/dahlia", (150, 60, 120), (180, 255, 255)),   # 粉: 玫瑰/大丽花
    ("leaf/yucca",  (35, 80, 100),  (85, 255, 255)),     # 绿: 叶子/丝兰
    ("starfish",    (5, 80, 100),   (22, 255, 255)),     # 橙: 海星
]
SLOT_BAND_TOP = 0.80          # 槽位条带顶部(画布偏移之下, 窗口高比例)
SLOT_BAND_BOT = 0.995         # 槽位条带底部
SLOT_ROWS = 2                 # 主槽/副槽两行
SLOT_COLS = 10                # 最多10个槽(数字键1-9, 0=10)


def scan_heal_slots(img=None):
    """自动扫描屏幕底部槽位区, 检测回血花瓣候选
    返回 [(行号0/1, 槽位1-10, 命中颜色名), ...] 按行从上到下、槽位从左到右
    注意: 颜色只是候选(U级花瓣也粉/Common级也绿/传奇也偏红), 需人工确认"""
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
    """在原图上标出槽位行(ROW0绿/ROW1蓝)和检出候选槽位(黄框+编号+颜色名), 存图供玩家确认"""
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



# ===== 花瓣稀有度扫描(底部槽位两行) + 推荐可秒等级(按稀有度估算) =====
RANK_SCORE = {"common": 1, "unusual": 2, "rare": 4, "epic": 8,
              "legendary": 16, "mythic": 32, "ultra": 64}

def scan_petal_ranks(img=None):
    """扫描底部槽位区每格花瓣的稀有度颜色, 返回 (counts, per_slot)
    counts: {rank: 数量}; per_slot: {(行,槽位): rank}
    注意: 颜色只能判稀有度, 不能判花瓣种类(输出/防御/回血); U级粉色/普通绿在槽位里可能误判"""
    if img is None:
        img = get_frame()
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
    """按稀有度估算推荐可秒等级:
    稳定档=主力同级(必秒必拿掉落, 首选); 降档=打不动时的备选
    维基生物表: 高一级血量 x3.6~46(神话->究极x46), 经验只多约x4~9 -> 秒不了的高一级绝对不划算
    注: 按稀有度估算, 未考虑花瓣种类/怪种, 实际以能3秒内秒杀为准"""
    if not any(counts.values()):
        return None
    main = max((r for r, c in counts.items() if c), key=lambda r: (RANK_SCORE[r], counts[r]))
    order = list(RANK_HSV.keys())
    idx = order.index(main)
    rec = order[max(0, idx - 1)] if idx > 0 else order[0]
    return main, rec


# ===== Bossbar 检测(研究落地: Super/Eternal/Unique 专属, 顶部中央大血条) =====
def detect_bossbar(frame=None):
    """检测屏幕顶部中央的 Boss 血条(Super+ 才有; Ultra 自2024-04-07起不显示)
    原理: 画布偏移之下的顶部区域, 中央 30%-70% 宽度内找横向连续红色长条(填充血)
    返回 True/False。Bossbar 比聊天播报可靠: 进屏即显示, 不依赖设置开聊天"""
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
    return best > w * 0.10   # 连续红色段 > 屏宽10% 视为 Boss 血条
