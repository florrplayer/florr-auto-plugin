# -*- coding: utf-8 -*-
"""afk_solver.py v1.18.0 - 挂机检测拖动验证破解器
移植 florr-auto-afk v1.3.2 (Shiny-Ladybug) 的 OpenCV 算法, 纯CPU无torch依赖:
  找AFK窗口 -> 颜色归一化(浅灰路径->白, 深灰背景->黑, 彩色起点->白)
  -> 起点(8种稀有度色±40容差最大色块) / 终点(路径连通域最大孔洞中心)
  -> Dijkstra最宽瓶颈路径 -> RDP简化 -> 延长到终点 -> 拖动
支持后台窗口 PostMessage 拖动 (不抢焦点)。
"""
import time, math
import cv2
import numpy as np
from collections import deque

# 8种稀有度起点颜色 (BGR, 与游戏/维基一致)
RARITY_COLORS_BGR = [
    (109, 238, 126),  # common 绿 #7EEF6D
    (93, 230, 255),   # unusual 黄 #FFE65D
    (227, 82, 77),    # rare 蓝 #4d52e3
    (222, 31, 134),   # epic 紫 #861FDE
    (31, 31, 222),    # legendary 红 #DE1F1F
    (222, 219, 31),   # mythic 青 #1fdbde
    (117, 43, 255),   # ultra 粉 #ff2b75
    (163, 255, 43),   # super 绿 #2bffa3
]

# 灰色路径/背景阈值
GRAY_PATH_MIN = 40       # 灰度>40 且 R=G=B -> 白色路径
GRAY_BG_MAX = 40         # 灰度<=40 且 R=G=B -> 黑色背景
COLOR_TOL = 40           # 起点颜色容差
MIN_PATH_LEN = 20        # 路径最短长度(像素)
MAX_WINDOW_ATTR = 3      # 连续几次找不到就告警


def is_gray_px(b, g, r, tol=8):
    return abs(int(b) - int(g)) < tol and abs(int(g) - int(r)) < tol and abs(int(b) - int(r)) < tol


def normalize_afk(img):
    """颜色归一化: 浅灰路径->白(255), 深灰背景->黑(0), 彩色起点->白(255)
    返回单通道mask"""
    b, g, r = cv2.split(img.astype(np.int16))
    color_diff = np.abs(b - g) + np.abs(g - r) + np.abs(b - r)
    gray_mask = color_diff <= 24          # R≈G≈B 视为灰
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.int16)
    out = np.zeros(img.shape[:2], np.uint8)
    out[gray_mask & (gray > GRAY_PATH_MIN)] = 255   # 浅灰 -> 路径(白)
    out[gray_mask & (gray <= GRAY_BG_MAX)] = 0      # 深灰 -> 背景(黑)
    out[~gray_mask] = 255                            # 彩色(起点) -> 可走(白)
    return out


def find_largest_component(mask):
    """返回最大连通域的二值mask (路径主体)"""
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if n <= 1:
        return None, labels, 0
    idx = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    if stats[idx, cv2.CC_STAT_AREA] < 50:
        return None, labels, 0
    return (labels == idx).astype(np.uint8) * 255, labels, idx


def find_endpoint(path_mask):
    """终点 = 路径连通域内的最大孔洞中心 (灰色空心圆)
    path_mask: 仅最大连通域=255 的二值图"""
    contours, hierarchy = cv2.findContours(path_mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return None
    best_area, best_center = 0, None
    for i, h in enumerate(hierarchy[0]):
        if h[3] != -1:  # 有父轮廓 = 孔洞
            area = cv2.contourArea(contours[i])
            M = cv2.moments(contours[i])
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                cx, cy = 0, 0
            if area > best_area:
                best_area, best_center = area, (cx, cy)
    return best_center


def find_startpoint(img, crop_offset=(0, 0)):
    """起点 = 8种稀有度颜色±容差匹配的最大色块中心 (彩色圆点)"""
    best_area, best_center, best_color = 0, None, None
    for color in RARITY_COLORS_BGR:
        lower = np.array([max(0, c - COLOR_TOL) for c in color], dtype=np.uint8)
        upper = np.array([min(255, c + COLOR_TOL) for c in color], dtype=np.uint8)
        m = cv2.inRange(img, lower, upper)
        n, labels, stats, centroids = cv2.connectedComponentsWithStats(m, connectivity=8)
        if n <= 1:
            continue
        idx = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        area = stats[idx, cv2.CC_STAT_AREA]
        if area > best_area:
            best_area = area
            best_center = (int(round(centroids[idx][0])), int(round(centroids[idx][1])))
            best_color = color
    if best_center is None:
        return None, None
    return best_center, best_color


def dijkstra_widest(path_mask, start, end):
    """Dijkstra变体: 最大化路径上的最小宽度(瓶颈) - 距离变换加权
    返回路径点列表(含start,end)或None"""
    h, w = path_mask.shape
    sx, sy = int(round(start[0])), int(round(start[1]))
    ex, ey = int(round(end[0])), int(round(end[1]))
    if not (0 <= sx < w and 0 <= sy < h and 0 <= ex < w and 0 <= ey < h):
        return None
    if path_mask[sy, sx] == 0 or path_mask[ey, ex] == 0:
        return None
    dt = cv2.distanceTransform(path_mask, cv2.DIST_L2, 5)
    dist_map = -np.ones((h, w), dtype=np.float32)
    dist_map[sy, sx] = dt[sy, sx]
    prev = {}
    import heapq
    pq = [(-dt[sy, sx], (sx, sy))]
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    while pq:
        neg, (x, y) = heapq.heappop(pq)
        cur = -neg
        if (x, y) == (ex, ey):
            break
        if cur < dist_map[y, x]:
            continue
        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and path_mask[ny, nx] == 255:
                nw = min(cur, dt[ny, nx])
                if nw > dist_map[ny, nx]:
                    dist_map[ny, nx] = nw
                    prev[(nx, ny)] = (x, y)
                    heapq.heappush(pq, (-nw, (nx, ny)))
    path = []
    cur = (ex, ey)
    if cur in prev or cur == (sx, sy):
        while cur != (sx, sy):
            path.append(cur)
            cur = prev[cur]
        path.append((sx, sy))
        path.reverse()
        return path
    return None


def rdp_simplify(points, epsilon=2.0):
    """Ramer-Douglas-Peucker 折线简化"""
    if len(points) < 3:
        return points
    dmax, idx = 0.0, 0
    x1, y1 = points[0]
    x2, y2 = points[-1]
    for i in range(1, len(points) - 1):
        xi, yi = points[i]
        d = abs((y2 - y1) * xi - (x2 - x1) * yi + x2 * y1 - y2 * x1) / (
            math.hypot(y2 - y1, x2 - x1) + 1e-9)
        if d > dmax:
            dmax, idx = d, i
    if dmax > epsilon:
        left = rdp_simplify(points[:idx + 1], epsilon)
        right = rdp_simplify(points[idx:], epsilon)
        return left[:-1] + right
    return [points[0], points[-1]]


def extend_to_end(path, end, length=10):
    """把路径终点延长到终点中心"""
    if not path:
        return path
    last = path[-1]
    if len(path) >= 2:
        prev_pt = path[-2]
        d = math.hypot(last[0] - prev_pt[0], last[1] - prev_pt[1])
        if d > 0.1:
            cosine = (last[0] - prev_pt[0]) / d
            sine = (last[1] - prev_pt[1]) / d
            ext = (int(round(last[0] + length * cosine)), int(round(last[1] + length * sine)))
            path.append(ext)
    path.append((int(round(end[0])), int(round(end[1]))))
    return path


def find_afk_window(frame):
    """定位AFK窗口: 找大块深灰矩形(背景)+内部浅灰路径
    返回 (x0,y0,x1,y1) 窗口边界 或 None"""
    h, w = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # 深灰背景 (游戏画面里AFK弹窗是深灰遮罩)
    dark = ((gray <= 55) & (gray >= 8)).astype(np.uint8) * 255
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(dark, connectivity=8)
    best = None
    if n > 1:
        for i in range(1, n):
            x, y, ww, hh, area = stats[i]
            if area < w * h * 0.01:
                continue
            ratio = ww / max(1, hh)
            # AFK窗口接近方形/横向矩形, 且内部应有白路径
            if 0.5 < ratio < 3.0 and ww > 120 and hh > 80:
                roi = frame[y:y + hh, x:x + ww]
                white = ((cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) > 60)).sum()
                if white / max(1, roi.size) > 0.01:
                    if best is None or area > best[0]:
                        best = (area, (x, y, x + ww, y + hh))
    if best:
        return best[1]
    # 兜底: 全屏中心60%当作窗口
    return (int(w * 0.2), int(h * 0.15), int(w * 0.8), int(h * 0.85))


def solve_afk_drag_v2(frame=None, crop_margin=0.05):
    """完整AFK拖动破解
    返回 (ok, start_xy, path_points, end_xy) 窗口像素坐标
    """
    try:
        if frame is None:
            from combat import get_frame
            frame = get_frame()
        h, w = frame.shape[:2]
        # 1. 定位窗口
        win = find_afk_window(frame)
        if win is None:
            return False, (0, 0), [], (0, 0)
        x0, y0, x1, y1 = win
        # 留边裁剪(去掉窗口边缘)
        mx = int((x1 - x0) * crop_margin)
        my = int((y1 - y0) * crop_margin)
        roi = frame[y0 + my:y1 - my, x0 + mx:x1 - mx]
        if roi.size == 0:
            return False, (0, 0), [], (0, 0)
        # 2. 归一化
        mask = normalize_afk(roi)
        # 3. 最大连通域 = 路径主体
        path_mask, labels, idx = find_largest_component(mask)
        if path_mask is None:
            return False, (0, 0), [], (0, 0)
        # 4. 终点 = 孔洞中心
        end = find_endpoint(path_mask)
        # 5. 起点 = 稀有度色
        start, s_color = find_startpoint(roi)
        if start is None:
            return False, (0, 0), [], (0, 0)
        # 6. Dijkstra最宽路径
        path = dijkstra_widest(path_mask, start, end) if end else None
        if not path:
            # 没终点: 从起点BFS到最远可达点
            from collections import deque
            q = deque([start])
            visited = {start}
            far = start
            while q:
                p = q.popleft()
                if math.hypot(p[0] - start[0], p[1] - start[1]) > math.hypot(far[0] - start[0], far[1] - start[1]):
                    far = p
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    np_ = (p[0] + dx, p[1] + dy)
                    if 0 <= np_[1] < path_mask.shape[0] and 0 <= np_[0] < path_mask.shape[1] \
                       and path_mask[np_[1], np_[0]] == 255 and np_ not in visited:
                        visited.add(np_)
                        q.append(np_)
            end = far
            path = dijkstra_widest(path_mask, start, end)
        if not path or len(path) < MIN_PATH_LEN:
            return False, (0, 0), [], (0, 0)
        # 7. RDP简化 + 延长
        path = rdp_simplify(path, epsilon=3.0)
        path = extend_to_end(path, end, length=8)
        # 8. 坐标还原到窗口
        off = (x0 + mx, y0 + my)
        start_abs = (start[0] + off[0], start[1] + off[1])
        end_abs = (end[0] + off[0], end[1] + off[1])
        path_abs = [(p[0] + off[0], p[1] + off[1]) for p in path]
        return True, start_abs, path_abs, end_abs
    except Exception as e:
        print(f"[AFK-v2] 异常: {e}")
        return False, (0, 0), [], (0, 0)


def drag_path(window, path_points, speed=60.0, hold_ms=150):
    """后台拖动: PostMessage 到窗口 (不抢焦点, 最小化也行)
    path_points: 窗口客户区坐标列表"""
    import win32api, win32con
    hwnd = window.hwnd
    def _lp(x, y):
        return (int(y) << 16) | (int(x) & 0xFFFF)
    sx, sy = path_points[0]
    ex, ey = path_points[-1]
    # 移到起点
    win32api.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, _lp(sx, sy))
    time.sleep(0.1)
    win32api.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, _lp(sx, sy))
    time.sleep(hold_ms / 1000.0)
    for i in range(1, len(path_points)):
        px, py = path_points[i]
        d = math.hypot(px - path_points[i - 1][0], py - path_points[i - 1][1])
        win32api.PostMessage(hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, _lp(px, py))
        time.sleep(max(0.01, d / speed))
    time.sleep(hold_ms / 1000.0)
    win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, _lp(ex, ey))


def solve_afk_flap_v2(frame=None, crop_margin=0.05):
    """AFK Flap(飞行)类型破解 - v1.29.3 新机制(wasm: UI/AFKCheck/Flap/Instructions="操控圆球飞行到终点")
    与Drag不同: 无彩色起点色块(圆球=玩家自己, 在路径一端), 用键盘WASD飞行到终点
    复用窗口定位/归一化/终点检测; 起点=路径端点(离屏幕中心近的那端)
    返回 (ok, path_abs, end_abs)
    """
    try:
        if frame is None:
            from combat import get_frame
            frame = get_frame()
        h, w = frame.shape[:2]
        win = find_afk_window(frame)
        if win is None:
            return False, [], (0, 0)
        x0, y0, x1, y1 = win
        mx = int((x1 - x0) * crop_margin)
        my = int((y1 - y0) * crop_margin)
        roi = frame[y0 + my:y1 - my, x0 + mx:x1 - mx]
        if roi.size == 0:
            return False, [], (0, 0)
        mask = normalize_afk(roi)
        path_mask, labels, idx = find_largest_component(mask)
        if path_mask is None:
            return False, [], (0, 0)
        end = find_endpoint(path_mask)
        if end is None:
            return False, [], (0, 0)
        # 起点 = 路径上与屏幕中心最近的点 (玩家圆球)
        cy, cx = roi.shape[0] // 2, roi.shape[1] // 2
        ys, xs = np.where(path_mask > 0)
        if len(xs) < 10:
            return False, [], (0, 0)
        dists = (xs - cx) ** 2 + (ys - cy) ** 2
        i = int(np.argmin(dists))
        start = (int(xs[i]), int(ys[i]))
        path = dijkstra_widest(path_mask, start, end)
        if not path or len(path) < MIN_PATH_LEN:
            return False, [], (0, 0)
        path = rdp_simplify(path, epsilon=3.0)
        path = extend_to_end(path, end, length=8)
        off = (x0 + mx, y0 + my)
        end_abs = (end[0] + off[0], end[1] + off[1])
        path_abs = [(p[0] + off[0], p[1] + off[1]) for p in path]
        return True, path_abs, end_abs
    except Exception as e:
        print(f"[AFK-Flap] 异常: {e}")
        return False, [], (0, 0)


def flap_path(window, path, speed_px_per_s=95.0, min_hold=0.05):
    """Flap 飞行执行: 键盘 WASD 沿路径逐段飞 (非拖动!)
    每段按方向键, 按(段长/速度)秒后换向; 最后一小段多飞0.3s保证到终点"""
    import win32api, win32con
    hwnd = window.hwnd
    def _key(vk):
        win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, 1)
        win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk, 1)
    VK = {'w': 0x57, 'a': 0x41, 's': 0x53, 'd': 0x44}
    for i in range(1, len(path)):
        px, py = path[i]
        qx, qy = path[i - 1]
        d = math.hypot(px - qx, py - qy)
        if d < 1:
            continue
        keys = []
        if abs(px - qx) > 2:
            keys.append('d' if px > qx else 'a')
        if abs(py - qy) > 2:
            keys.append('s' if py > qy else 'w')
        hold = max(min_hold, d / speed_px_per_s)
        if i == len(path) - 1:
            hold += 0.35  # 终点多飞一程
        for k in keys:
            win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, VK[k], 1)
        time.sleep(hold)
        for k in keys:
            win32api.PostMessage(hwnd, win32con.WM_KEYUP, VK[k], 1)
        time.sleep(0.03)


def try_solve_and_drag(window, frame=None):
    """一键: 检测+求解+执行. 自动判别 Drag(彩色起点) / Flap(飞行)
    返回是否成功"""
    ok, start, path, end = solve_afk_drag_v2(frame)
    if ok and len(path) >= 2:
        print(f"[AFK-v2] 拖动型: 起点{start} -> 终点{end} 路径{len(path)}点")
        drag_path(window, path)
        time.sleep(1.5)
        return True
    # 拖动失败 -> 可能是 Flap 飞行型(无彩色起点): 键盘飞行破解
    ok2, path2, end2 = solve_afk_flap_v2(frame)
    if ok2 and len(path2) >= 2:
        print(f"[AFK-v2] 飞行型(Flap): 终点{end2} 路径{len(path2)}点, 键盘飞行破解")
        flap_path(window, path2)
        time.sleep(1.5)
        return True
    return False


if __name__ == '__main__':
    import sys
    sys.path.insert(0, '.')
    print("=== AFK求解器测试 ===")
    try:
        from combat import get_frame
        frame = get_frame()
        ok, s, p, e = solve_afk_drag_v2(frame)
        print(f"求解: ok={ok} start={s} end={e} path={len(p)}点")
    except Exception as ex:
        print(f"无窗口/截图失败: {ex}")
