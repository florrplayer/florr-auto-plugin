# -*- coding: utf-8 -*-
"""learn_shortcut.py v1.36 - 捷径自动录制 (移植自 zyliu1985/florr-autoplayer learn_shortcuts.py)

用法: 游戏开着并在地图里, 运行:
    py -3.12 learn_shortcut.py desert
然后手动沿着小地图上看不到的捷径走一遍, 插件会把走过的墙段精确刷成可走并保存,
寻路立刻就能用. Ctrl+C 退出.
"""
import os, sys, time

import cv2
import numpy as np

import utils

CARVE_RADIUS = 1          # 刷墙半径(px), 窄通道保持 1
MIN_WALL_DISTANCE = 2     # 离最近可走区超过这个距离才算"在墙里"
POLL_INTERVAL = 1.0


def _raw_player_position():
    """玩家标记在小地图上的原始中心(不吸附到可走格) - 判断在墙里必须用原始位置"""
    image = utils.get_map()
    binary_map = utils.load_binary_map()
    if image is None or binary_map is None:
        return None
    for color in ("f9dd64", "ffde3d", "ffd700", "fffacd", "f0e68c", "e6c200", "f5d76e", "f0c040"):
        pos = utils.get_player_location_on_map(image, color, binary_map, precise=True)
        if pos is not None:
            return round(pos[0]), round(pos[1])
    return None


def _dist_to_walkable(binary, cx, cy):
    """该像素到最近可走像素的步数(cv2 距离变换)"""
    fg = np.where(binary == 255, 0, 255).astype(np.uint8)
    dist = cv2.distanceTransform(fg, cv2.DIST_C, 3)
    h, w = fg.shape
    if not (0 <= cx < w and 0 <= cy < h):
        return 999
    return int(dist[cy, cx])


def _carve_disk(binary, cx, cy, radius):
    h, w = binary.shape
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx * dx + dy * dy <= radius * radius:
                x, y = cx + dx, cy + dy
                if 0 <= x < w and 0 <= y < h:
                    binary[y, x] = 255


def _bresenham(x0, y0, x1, y1):
    pts = []
    dx = abs(x1 - x0); dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1; sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy; x0 += sx
        if e2 <= dx:
            err += dx; y0 += sy
    return pts


def _carve_line(binary, p1, p2, radius):
    for x, y in _bresenham(p1[0], p1[1], p2[0], p2[1]):
        _carve_disk(binary, x, y, radius)


def main():
    map_name = sys.argv[1] if len(sys.argv) > 1 else "anthell"
    utils.apply_map(map_name)
    binary = utils.load_binary_map()
    if binary is None:
        print(f"[捷径] 读不到 {map_name}.png, 确认 maps/ 下有这张图")
        return
    print(f"[捷径] 已加载 {map_name} 地图(可走 {100*(binary == 255).mean():.0f}%). 手动沿着捷径走一遍, 工具会把走过的墙段刷成可走并保存. Ctrl+C 退出.")
    patched = 0
    last_wall = None
    while True:
        try:
            raw = _raw_player_position()
            if raw is None:
                last_wall = None
                time.sleep(POLL_INTERVAL)
                continue
            x, y = raw
            if binary[y, x] == 255:
                last_wall = None
                time.sleep(POLL_INTERVAL)
                continue
            d = _dist_to_walkable(binary, x, y)
            if d <= MIN_WALL_DISTANCE:
                last_wall = None
                time.sleep(POLL_INTERVAL)
                continue
            if last_wall is not None:
                _carve_line(binary, last_wall, raw, CARVE_RADIUS)
            else:
                _carve_disk(binary, x, y, CARVE_RADIUS)
            last_wall = raw
            patched += 1
            cv2.imwrite(os.path.join(utils.MAP_DIR, map_name + ".png"), binary)
            utils.apply_map(map_name)   # 清缓存, 主程序重读新地图
            print(f"[捷径] 刷墙 ({x},{y}) 离可走{d}px - 已保存(可走 {100*(binary == 255).mean():.0f}%, 采样{patched}次)")
        except KeyboardInterrupt:
            print(f"\n[捷径] 退出. 改动已保存到 maps/{map_name}.png")
            return
        except Exception as e:
            print(f"[捷径] {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
