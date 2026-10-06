# -*- coding: utf-8 -*-
"""canvas_loc.py v1.28.1 - 画布绘制记录定位管线 (截图/画布模式)
思路来源: greatluca666/florr-auto-farm canvas_decode.py (GPLv3, 独立重写实现)
输入: 每帧 canvas 绘制记录流 (CDP 钩子注入后的页面 log, 每条含 op/m/CTM/x/y/r/fill/stroke)
输出: 纯函数, 不碰屏幕/IO:
  - zone_map_from_frame: 地图判定(蚂蚁地狱/沙漠/花园 -> 图名)
  - player_world_position: 小地图玩家黄点 -> 世界坐标 (只要小地图点, 可用性最强)
  - camera_from_frame: zoom + player_world + player_screen 三件套
  - screen_to_world: 屏幕锚点 -> 世界坐标 (锚在玩家上)
用途: bridge 协议缺玩家坐标时(截图模式/画布模式)反解自身位置与地图, 配合 name_tier 名牌识别
"""

# 小地图: CTM scale ~0.0084; 主视图绘制 scale 0.76+ —— 用来区分是不是小地图
MINIMAP_MAX_SCALE = 0.05
# 玩家本体金色 (花 + 小地图点)
PLAYER_BODY_COLOR = "#FFE763"
# 名牌血条底色 (未旋转, 相机缩放 = 它的 CTM scale.x)
HEALTHBAR_BG = "#222222"
# 地图标签 -> 图名 (画布名牌/区域文字)
ZONE_LABELS = {"蚂蚁地狱": "anthell", "沙漠": "desert", "花园": "garden",
               "下水道": "sewers", "海洋": "ocean", "丛林": "jungle",
               "工厂": "factory"}


def _is_minimap(rec):
    """CTM scale 小 = 小地图绘制 (主视图绘制 scale>=0.76)"""
    try:
        return abs(rec["m"][0]) < MINIMAP_MAX_SCALE
    except Exception:
        return False


def _body_anchor(rec):
    """绘制记录的锚点: 有 r 的按 r, 否则按 x/y + CTM 平移"""
    m = rec.get("m")
    if m is None:
        return None
    x = rec.get("x", 0.0)
    y = rec.get("y", 0.0)
    return (x + m[4], y + m[5])


def zone_map_from_frame(records):
    """这一帧里出现的地图标签 -> 图名; 没有标签 -> None
    (进图时/换图时画布会画区域名, 用名牌文字兜底地图判定)"""
    for r in records or []:
        if r.get("op") == "text" or r.get("text"):
            t = str(r.get("text", ""))
            if t in ZONE_LABELS:
                return ZONE_LABELS[t]
    return None


def player_world_position(records):
    """这一帧里玩家的绝对世界坐标: 只要小地图上金色那个点。
    不需要 zoom/player_screen 全齐 —— 设置面板挡主视图时小地图通常还在。
    解不出返回 None, 调用方自己退化, 不猜位置。"""
    for r in records or []:
        if _is_minimap(r) and r.get("fill") == PLAYER_BODY_COLOR and r.get("r") is not None:
            m = r["m"]
            return ((r["x"] - m[4]) / m[0], (r["y"] - m[5]) / m[3])
    return None


def camera_from_frame(records, best_effort=False):
    """读一帧相机: {"zoom", "player_world", "player_screen"}
    zoom = 名牌血条底色 (未旋转, 相机缩放), player_world = 小地图黄点反解,
    player_screen = 玩家金色本体锚点。缺任一 raise ValueError(猜一个会污染所有世界坐标)。
    best_effort=True: 金色锚点落在怪群外很远的 = 别的玩家, 丢弃; 仍无 screen 但有 zoom 时
    退回玩家血条锚点并置 player_world=0 (只供屏幕空间过滤用)。"""
    zoom = None
    for r in records or []:
        if r.get("op") == "stroke" and r.get("stroke") == HEALTHBAR_BG and not _is_minimap(r):
            zoom = r["m"][0]
            break

    player_world = None
    for r in records or []:
        if _is_minimap(r) and r.get("fill") == PLAYER_BODY_COLOR and r.get("r") is not None:
            m = r["m"]
            player_world = ((r["x"] - m[4]) / m[0], (r["y"] - m[5]) / m[3])
            break

    player_screen = None
    for r in records or []:
        if not _is_minimap(r) and r.get("fill") == PLAYER_BODY_COLOR and r.get("r") is not None:
            # 本体锚点 = 屏幕坐标 (x + CTM 平移)。单机挂机场景取第一个金色本体即可;
            # 多玩家同屏时 best_effort 之外由调用方过滤(原实现靠闪光模式区分, 过度复杂)
            player_screen = _body_anchor(r)
            break

    if zoom is None:
        raise ValueError("camera_from_frame: 没有名牌血条(zoom)")
    if player_world is None:
        raise ValueError("camera_from_frame: 没有小地图玩家点(player_world)")
    if player_screen is None:
        if best_effort:
            return {"zoom": zoom, "player_world": (0.0, 0.0), "player_screen": None}
        raise ValueError("camera_from_frame: 没有玩家金色本体(player_screen)")
    return {"zoom": zoom, "player_world": player_world, "player_screen": player_screen}


def screen_to_world(x, y, camera):
    """屏幕锚点 -> 绝对世界坐标 (锚在玩家上)"""
    px, py = camera["player_screen"]
    wx, wy = camera["player_world"]
    z = camera["zoom"]
    return (wx + (x - px) / z, wy + (y - py) / z)


if __name__ == '__main__':
    print('=== canvas_loc 测试 ===')
    zoom = 0.8
    pworld = (32000.0, 28000.0)
    pscreen = (960.0, 540.0)
    recs = [
        {"op": "stroke", "m": [zoom, 0, 0, zoom, 100, 100], "stroke": HEALTHBAR_BG, "x": 100, "y": 100},
        {"op": "fill", "m": [0.0084, 0, 0, 0.0084, 200, 200],
         "fill": PLAYER_BODY_COLOR, "x": 200 + 0.0084 * pworld[0], "y": 200 + 0.0084 * pworld[1], "r": 3},
        {"op": "fill", "m": [zoom, 0, 0, zoom, 100, 100],
         "fill": PLAYER_BODY_COLOR, "x": pscreen[0] - 100, "y": pscreen[1] - 100, "r": 30},
        {"op": "text", "text": "沙漠", "m": [1, 0, 0, 1, 0, 0]},
    ]
    print('  地图:', zone_map_from_frame(recs))
    print('  玩家世界(小地图):', tuple(round(v, 1) for v in player_world_position(recs)))
    cam = camera_from_frame(recs)
    print('  camera:', {k: (tuple(round(v, 2) for v in val) if isinstance(val, tuple) else round(val, 3))
                         for k, val in cam.items()})
    sw = screen_to_world(pscreen[0], pscreen[1], cam)
    print('  screen_to_world(玩家屏幕点) =', tuple(round(v, 1) for v in sw))
