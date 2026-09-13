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
import numpy as np
import cv2
from utils import get_frame, get_player_position, ARRIVE, set_screen_center

# ===== 参数(可调) =====
# HSV 阈值(OpenCV 尺度: H 0-179 = 度数/2, S/V 0-255)
# Mythic 青 #1FDBDE: 真H 181° -> OpenCV H 90, S 222, V 222
# Ultra  粉 #FF2B75: 真H 339° -> OpenCV H 170, S 212, V 255
# (Legendary 红 H=0, 与粉/青均不冲突)
MYTHIC_HSV = ((85, 100, 100), (100, 255, 255))   # M 怪 青色
ULTRA_HSV = ((162, 100, 100), (178, 255, 255))   # U 怪 粉色
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


def _detect_color(frame, hsv_range, exclude_center=True):
    """按 HSV 区间找色块, 返回中心点列表(屏幕坐标)"""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(hsv_range[0]), np.array(hsv_range[1]))
    if exclude_center:
        cx, cy = get_screen_center()
        cv2.circle(mask, (cx, cy), EXCLUDE_CENTER_R, 0, -1)
    # 降采样检测(统一960宽, 提速), 标定后自动适配实际分辨率
    det_w = 960
    det_h = int(frame.shape[0] / _downscale)
    small = cv2.resize(mask, (det_w, det_h), interpolation=cv2.INTER_NEAREST)
    n, labels, stats, cents = cv2.connectedComponentsWithStats(small, 8)
    pts = []
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA]
        w, h = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
        if not (MIN_MOB_PX * MIN_MOB_PX / 4 <= area <= MAX_MOB_PX * MAX_MOB_PX):
            continue
        if w > MAX_MOB_PX * 1.5 or h > MAX_MOB_PX * 1.5:
            continue
        cx_s, cy_s = cents[i]
        pts.append((int(cx_s * _downscale), int(cy_s * _downscale)))   # 还原全分辨率坐标
    return pts


def detect_mobs(frame=None):
    """检测 M/U 怪, 返回 (mythics, ultras) 屏幕坐标列表"""
    if frame is None:
        frame = get_frame()
    mythics = _detect_color(frame, MYTHIC_HSV)
    ultras = _detect_color(frame, ULTRA_HSV)
    return mythics, ultras


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


def choose_target(mythics_map, patrol_goal, player_map=None):
    """从 M 怪里挑: 距离最近 且 不偏离巡逻点

    偏离容忍 = DEVIATION + 玩家到巡逻点的距离(走路途中顺路打, 快到了不乱跑)
    patrol_goal: 当前巡逻目标点(地图坐标)。返回目标地图坐标或 None
    """
    if player_map is None:
        player_map = get_player_position()
    if player_map is None or not mythics_map:
        return None
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
