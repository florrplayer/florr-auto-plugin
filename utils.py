import os
import time
import math
import heapq
import traceback
import cv2
import numpy as np
from collections import deque
from window_ctrl import get_window

MAP = ""
MAP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "maps")
_MAP_CACHE = {}
_NEAREST_CACHE = {}
_FRAME = {"t": 0.0, "img": None}
_STAGE_CACHE = {"image": None, "stage": None}
ARRIVE = 5.0        # 到达判定阈值（地图像素）
FRAME_TTL = 0.05    # 帧缓存有效期（秒）
_screen_center = [960, 540]   # 实际窗口客户区中心(启动时标定, 兼容4K/DPI缩放)


def set_screen_center(w, h):
    """标定实际窗口中心(由 combat.calibrate_screen 调用)"""
    global _screen_center
    _screen_center = [int(w // 2), int(h // 2)]


def get_screen_center():
    return _screen_center[0], _screen_center[1]


def apply_map(name):
    global MAP
    assert name in [p[:-4] for p in os.listdir(MAP_DIR) if p.lower().endswith(".png")]
    MAP = name
    _MAP_CACHE.clear()
    _NEAREST_CACHE.clear()


def load_binary_map():
    """地图缓存：只读一次磁盘（原实现每次调用都 imread）"""
    if MAP not in _MAP_CACHE:
        _MAP_CACHE[MAP] = cv2.imread(os.path.join(MAP_DIR, MAP + ".png"), cv2.IMREAD_GRAYSCALE)
    return _MAP_CACHE[MAP]


def get_frame(force=False):
    """共享帧缓存：一次 PrintWindow 截图供同帧多次读取复用。

    原实现每次 get_pixel / get_map 都做一次全窗口 PrintWindow 截图
    （单次可达 30~200ms），运动循环每 50ms 就要截 2~3 次，是最大瓶颈。
    """
    now = time.time()
    img = _FRAME["img"]
    if force or img is None or now - _FRAME["t"] > FRAME_TTL:
        _FRAME["t"] = now
        _FRAME["img"] = img = get_window().capture()
    return img


def check_stage(img=None):
    """判断当前界面状态: in_game(游戏中) / in_game_dead(死亡) / in_menu(菜单/装备/加载)
    改进: 不用单像素纯白色(装备界面UI也是白色, 会误判死亡), 改用:
      1. 右上角有小地图 -> 游戏中
      2. 中央偏下有绿色复活按钮 -> 死亡
      3. 其他 -> 菜单/装备/加载"""
    if img is None:
        img = get_frame()
    if _STAGE_CACHE["image"] is img:
        return _STAGE_CACHE["stage"]
    h, w = img.shape[:2]
    off = _canvas_y_offset
    game_h = max(h - off, 1)

    # 1. 检测小地图(游戏中特征): 强制刷新缓存, 避免菜单时缓存了None
    rect = _detect_minimap(img)
    if rect is not None:
        _MINIMAP_CACHE.update(rect=rect, t=time.time())
        _STAGE_CACHE.update(image=img, stage="in_game")
        return "in_game"

    # 1b. fallback: 用get_map()截取小地图区域(新位置), 检测黑白迷宫特征(黑色像素>10%)
    gmap = get_map(img)
    if gmap is not None and gmap.shape[0] > 30 and gmap.shape[1] > 30:
        mm_gray = cv2.cvtColor(gmap, cv2.COLOR_BGR2GRAY)
        black_ratio = np.sum(mm_gray < 60) / (mm_gray.shape[0] * mm_gray.shape[1])
        if black_ratio > 0.1:
            _STAGE_CACHE.update(image=img, stage="in_game")
            return "in_game"

    # 1c. 玩家定位辅助判断: 如果能在小地图上定位到玩家点, 说明在游戏中
    try:
        p = get_player_position(image=img)
        if p is not None:
            _STAGE_CACHE.update(image=img, stage="in_game")
            return "in_game"
    except Exception:
        pass

    # 2. 检测死亡界面: 画面中央偏下的绿色复活按钮(取区域平均色)
    rx = int(960 * w / 1920)
    ry = off + int(620 * game_h / 1080)
    ry = min(ry, h - 1)
    y0, y1 = max(0, ry - 8), min(h, ry + 8)
    x0, x1 = max(0, rx - 20), min(w, rx + 20)
    if y1 > y0 and x1 > x0:
        btn_mean = np.mean(img[y0:y1, x0:x1], axis=(0, 1))
        # 绿色按钮: G通道显著高于B和R
        if btn_mean[1] > 100 and btn_mean[1] > btn_mean[0] + 25 and btn_mean[1] > btn_mean[2] + 25:
            _STAGE_CACHE.update(image=img, stage="in_game_dead")
            return "in_game_dead"

    # 3. 其他(菜单/装备界面/加载中)
    _STAGE_CACHE.update(image=img, stage="in_menu")
    return "in_menu"


_MINIMAP_CACHE = {"rect": None, "t": 0.0}
_MINIMAP_TTL = 2.0   # 小地图位置缓存2秒(窗口大小不变时不用每帧检测)
_canvas_y_offset = 0  # 游戏画布在客户区中的y偏移(浏览器UI高度, 最大化非全屏时>0)


def detect_canvas_offset(frame=None):
    """检测游戏画布起始行(浏览器标签栏+地址栏高度), 兼容最大化非全屏
    从顶部往下扫描, 浏览器UI是纯色(白/灰)方差小, 游戏画面内容丰富方差大"""
    global _canvas_y_offset
    if frame is None:
        frame = get_frame()
    h, w = frame.shape[:2]
    for y in range(0, min(h, 300), 2):
        row = frame[y, int(w * 0.1):int(w * 0.9)]
        if np.std(row) > 25:
            _canvas_y_offset = y
            print(f"[标定] 游戏画布起始行 y={y} (浏览器UI高度 {y}px)")
            return y
    _canvas_y_offset = 0
    print("[标定] 未检测到浏览器UI偏移(假设全屏)")
    return 0


def _detect_minimap(frame):
    """检测小地图位置: 在右上角区域滑动窗口, 找黑色像素最多的方形区域
    小地图是黑白迷宫(黑色背景+白色路径), 黑色像素比例>15%"""
    h, w = frame.shape[:2]
    off = _canvas_y_offset
    game_h = max(h - off, 1)
    rx0 = int(w * 0.5)
    ry0 = off + int(game_h * 0.03)
    rx1, ry1 = w, off + int(game_h * 0.6)
    roi = frame[ry0:ry1, rx0:rx1]
    roi_h, roi_w = roi.shape[:2]
    if roi_h < 50 or roi_w < 50:
        return None
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    black = (gray < 60).astype(np.uint8)
    s = int(min(h, w) * 0.40)
    if s > roi_h or s > roi_w:
        s = min(roi_h, roi_w)
    if s < 50:
        return None
    integral = cv2.integral(black)
    best_x, best_y, best_count = 0, 0, 0
    step = max(s // 8, 5)
    for y in range(0, roi_h - s, step):
        for x in range(0, roi_w - s, step):
            count = integral[y + s, x + s] - integral[y, x + s] - integral[y + s, x] + integral[y, x]
            if count > best_count:
                best_count = count
                best_x, best_y = x, y
    black_ratio = best_count / (s * s)
    if black_ratio > 0.15:
        return (rx0 + best_x, ry0 + best_y, s)
    return None


def get_map(frame=None):
    """截取小地图(动态检测位置, 兼容全屏/最大化/4K)"""
    if frame is None:
        frame = get_frame()
    h, w = frame.shape[:2]
    now = time.time()
    rect = _MINIMAP_CACHE["rect"]
    if rect is None or now - _MINIMAP_CACHE["t"] > _MINIMAP_TTL:
        rect = _detect_minimap(frame)
        _MINIMAP_CACHE["rect"] = rect
        _MINIMAP_CACHE["t"] = now
    if rect is not None:
        x, y, s = rect
        if 0 <= x < w and 0 <= y < h and x + s <= w and y + s <= h and s > 20:
            return frame[y:y + s, x:x + s]
    # fallback: 按比例估算(小地图在游戏画面右上角, 更大更靠下)
    s = int(min(h, w) * 0.42)
    x = max(0, w - s - int(w * 0.015))
    y = _canvas_y_offset + int((h - _canvas_y_offset) * 0.08)
    if y + s > h:
        s = h - y
    if x + s > w:
        s = w - x
    return frame[y:y + s, x:x + s]


def if_in_area(areas, point):
    for area in areas:
        if area[0][0] <= point[0] <= area[1][0] and area[0][1] <= point[1] <= area[1][1]:
            return True
    return False


def distance(pos1, pos2):
    return math.hypot(pos1[0] - pos2[0], pos1[1] - pos2[1])


def check_map_border(opencv_img):
    target_color = "4c4950" if MAP == "ocean" else "4f3422"
    target_color_bgr = tuple(int(target_color[i:i + 2], 16) for i in (4, 2, 0))
    lower_bound = np.array([max(0, c - 3) for c in target_color_bgr])
    upper_bound = np.array([min(255, c + 3) for c in target_color_bgr])
    mask = cv2.inRange(opencv_img, lower_bound, upper_bound)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    points = []
    for contour in contours:
        for i in range(0, len(contour), 5):
            cv2.circle(opencv_img, tuple(contour[i][0]), 1, (0, 255, 0), -1)
            points.append(tuple(contour[i][0]))
    return points


def toggle_map():
    pos = get_player_position()
    if pos is not None and distance(pos, (250, 50)) <= 2.5:
        get_window().press(ord('M'))
        time.sleep(1)


def calc_anti_stuck(borders, weight=1.0):
    frame = get_frame()
    h, w = frame.shape[:2]
    screen_center = np.array(get_screen_center(), dtype=np.float64)
    total_force = np.array([0.0, 0.0], dtype=np.float64)
    for point in borders:
        point_vector = np.array(point, dtype=np.float64)
        distance_vec = np.linalg.norm(screen_center - point_vector)
        if distance_vec == 0:
            continue
        total_force += (screen_center - point_vector) / distance_vec
    final_position = screen_center + total_force * weight
    final_position[0] = np.clip(final_position[0], 0, w)
    final_position[1] = np.clip(final_position[1], 0, h)
    toggle_map()
    return final_position[0], final_position[1]


def execute_anti_stuck(duration=1.5):
    """卡住时朝远离地图边界的方向走一段（修复原实现 pathing_log 未定义的 NameError）"""
    opencv_img = get_frame()
    borders = check_map_border(opencv_img)
    suggested_position = calc_anti_stuck(borders)
    screen_center = np.array(get_screen_center(), dtype=np.float64)
    delta = np.array(suggested_position, dtype=np.float64) - screen_center
    max_delta = np.max(np.abs(delta))
    if max_delta == 0:
        return
    direction = ""
    if abs(delta[0]) > 1:
        direction += "d" if delta[0] > 0 else "a"
    if abs(delta[1]) > 1:
        direction += "s" if delta[1] > 0 else "w"
    if not direction:
        return
    try:
        keydown(direction)
        time.sleep(duration)
    finally:
        keyup(direction)


def keydown(direction, delta=500):
    """真正的键盘按键(WASD), delta参数保留兼容但不使用"""
    w = get_window()
    vk_map = {"w": 0x57, "a": 0x41, "s": 0x53, "d": 0x44,
              "wa": (0x57, 0x41), "wd": (0x57, 0x44),
              "sa": (0x53, 0x41), "sd": (0x53, 0x44)}
    keys = vk_map.get(direction)
    if keys is None:
        return
    if isinstance(keys, tuple):
        for k in keys:
            w.key_down(k)
    else:
        w.key_down(keys)


def keyup(direction):
    """松开键盘按键"""
    w = get_window()
    vk_map = {"w": 0x57, "a": 0x41, "s": 0x53, "d": 0x44,
              "wa": (0x57, 0x41), "wd": (0x57, 0x44),
              "sa": (0x53, 0x41), "sd": (0x53, 0x44)}
    keys = vk_map.get(direction)
    if keys is None:
        return
    if isinstance(keys, tuple):
        for k in keys:
            w.key_up(k)
    else:
        w.key_up(keys)


def get_player_position(precise=False, image=None):
    image = get_map(image)
    binary_map = load_binary_map()
    for color in ("f9dd64", "ffde3d", "ffd700", "fffacd", "f0e68c", "e6c200", "f5d76e", "f0c040"):
        position = get_player_location_on_map(image, color, binary_map, precise)
        if position is not None:
            return position
    return None


def abandon_game():
    w = get_window()
    for _ in range(3):
        w.mouse_double_click(307, 32)


def respawn():
    """死亡后按Enter复活(全键盘操作, 不用鼠标)"""
    w = get_window()
    print("[+] 等待死亡动画...")
    time.sleep(2.5)
    w.key_down(0x0D); time.sleep(0.1); w.key_up(0x0D)   # Enter 复活
    time.sleep(1.5)
    w.key_down(0x0D); time.sleep(0.1); w.key_up(0x0D)   # 再按一次(保险)
    print("[+] 已按Enter复活，等待加载...")
    time.sleep(5)


def preprocess_map(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    yellow_mask = cv2.inRange(hsv, np.array([20, 100, 100]), np.array([30, 255, 255]))
    binary[yellow_mask > 0] = 255
    cv2.imwrite(os.path.join(MAP_DIR, MAP + ".png"), binary)
    _MAP_CACHE.pop(MAP, None)
    _NEAREST_CACHE.pop(MAP, None)
    return binary


def get_player_location_on_map(opencv_img, target_color, map, precise=False):
    target_color_bgr = tuple(int(target_color[i:i + 2], 16) for i in (4, 2, 0))
    lower_bound = np.array([max(0, c - 30) for c in target_color_bgr])
    upper_bound = np.array([min(255, c + 30) for c in target_color_bgr])
    mask = cv2.inRange(opencv_img, lower_bound, upper_bound)
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        ((x, y), radius) = cv2.minEnclosingCircle(contour)
        if radius > 2:
            if precise:
                return (x, y)
            return calibrate_player(map, (round(x), round(y)))
    return None


def _nearest_grid(binary):
    """预计算每个像素的最近可行走格（多源 BFS），O(N*M) 一次，查询 O(1)"""
    rows, cols = binary.shape
    dist = np.full((rows, cols), -1, dtype=np.int32)
    nxt = np.zeros((rows, cols, 2), dtype=np.int32)
    q = deque()
    ys, xs = np.nonzero(binary == 255)
    if not ys.size:
        return None
    for y, x in zip(ys.tolist(), xs.tolist()):
        dist[y, x] = 0
        nxt[y, x] = (x, y)
        q.append((x, y))
    while q:
        x, y = q.popleft()
        nd = dist[y, x] + 1
        nearest = nxt[y, x]
        for dx, dy in ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < cols and 0 <= ny < rows and dist[ny, nx] == -1:
                dist[ny, nx] = nd
                nxt[ny, nx] = nearest
                q.append((nx, ny))
    return nxt


def calibrate_player(map, player_position):
    """把玩家坐标吸附到最近可行走格（局部精确欧氏搜索 + 全局 BFS 兜底）。

    原实现每次全图扫描 O(N*M)（实测单次 ~9.5ms，运动循环每次读位置都调）；
    玩家检测抖动只有 1~3px，局部半径 6 内搜索即可拿到与全图扫描一致的精确结果。
    """
    rows, cols = map.shape
    x = min(max(int(round(player_position[0])), 0), cols - 1)
    y = min(max(int(round(player_position[1])), 0), rows - 1)
    r = 6
    x0, x1 = max(0, x - r), min(cols, x + r + 1)
    y0, y1 = max(0, y - r), min(rows, y + r + 1)
    region = map[y0:y1, x0:x1]
    ys, xs = np.nonzero(region == 255)
    if ys.size:
        ds = (xs - (x - x0)) ** 2 + (ys - (y - y0)) ** 2
        i = int(np.argmin(ds))
        return (int(x0 + xs[i]), int(y0 + ys[i]))
    # 兜底：附近无可行走格时用全局 BFS 网格
    if MAP not in _NEAREST_CACHE:
        _NEAREST_CACHE[MAP] = _nearest_grid(map)
    grid = _NEAREST_CACHE[MAP]
    if grid is None:
        return (x, y)
    return (int(grid[y, x, 0]), int(grid[y, x, 1]))
