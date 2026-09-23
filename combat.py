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
LEGENDARY_HSV = ((0, 100, 100), (8, 255, 255))     # 传奇 红 #DE1F1F (OpenCV H 0-4, 与青/粉不冲突)
KILL_STOP = 0.5                          # 追击贴脸距离(地图像素, 用户要求 0.5)
WARN_MARGIN = 10.0                       # 危险怪预警距离: 进入10px内提前绕开(人先躲远)
CHASE_WARN = 8.0                         # 打怪中危险怪进入8px内停手逃跑
KISS_SLOW = 3.0                          # 贴脸减速区: 3px内放慢试探(人犹豫贴脸)
PROJ_MIN_PX = 4                            # 飞行物最小尺寸(导弹/螯针比怪小)
PROJ_MAX_PX = 24                           # 飞行物最大尺寸(含Mythic+大导弹, 降采样960宽基准)
PROJ_DODGE_R = 120                         # 飞行物进入玩家周围120px内才闪避
HP_BAR_Y = 30                            # 玩家脚下血条位置: 中心下方30px(屏幕px, 默认HUD)
HP_BAR_H = 4                             # 血条半高(px)
HP_BAR_W = 50                            # 血条半宽(px)
HP_FLEE = 0.10                           # 血量低于10% 跑路
HP_RECOVER = 0.35                        # 血量恢复到35% 才回去继续
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


def _detect_color(hsv, hsv_range, exclude_center=True, min_px=None, max_px=None):
    """按 HSV 区间找色块, 返回中心点列表(屏幕坐标); min_px/max_px 可覆盖怪尺寸范围"""
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
        pts.append((int(cx_s * _downscale), int(cy_s * _downscale)))   # 还原全分辨率坐标
    return pts


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


def detect_all(frame=None):
    """检测所有稀有度等级的怪, 返回 {rank: [屏幕坐标]}"""
    if frame is None:
        frame = get_frame()
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    out = {}
    for rank, rng in RANK_HSV.items():
        out[rank] = _detect_color(hsv, rng)
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


def detect_projectiles(frame=None):
    """检测飞行物(黄蜂/胡蜂导弹, 蝎子螯针等):
    全稀有度色 + 小尺寸(4-16px) + 帧间差分(运动物体才算)"""
    global _PROJ_PREV
    if frame is None:
        frame = get_frame()
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
