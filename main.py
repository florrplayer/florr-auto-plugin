import os
import sys
import time
import math
import random
import heapq
import win32con
import utils
from collections import deque
from utils import *
from window_ctrl import init_window, get_window

MAX_STUCK = 5   # 连续卡死/无路次数上限，超过则跳过当前巡逻点
PATH_STEP = 40  # 巡逻分段长度(地图像素)：每走完一段回主循环检查战斗
COMBAT_ENABLED = True  # 战斗模式总开关
TRAIL_MAX = 800        # 撤退轨迹缓存长度
MOVE_PROGRESS_TIMEOUT = 1.5  # 持续无有效进展多久才判定卡住
PATH_CACHE = {"goal": None, "path": None}


def line_of_sight(map, n1, n2):
    x0, y0 = n1
    x1, y1 = n2
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx, sy = 1 if x0 < x1 else -1, 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        if map[y0, x0] == 0:
            return False
        if x0 == x1 and y0 == y1:
            return True
        e2 = err * 2
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def lazy_theta_star(map, start, goal):
    """Theta* 寻路（g 值字典版），保证最短路径，LOS 拉直"""
    rows, cols = map.shape
    h = lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1])
    g = {start: 0.0}
    parent = {start: start}
    open_list = [(h(start, goal), start)]
    closed = set()
    while open_list:
        _, cur = heapq.heappop(open_list)
        if cur in closed:
            continue
        if cur == goal:
            path = []
            while cur != start:
                path.append(cur)
                cur = parent[cur]
            path.append(start)
            return path[::-1]
        closed.add(cur)
        px, py = parent[cur]
        pg, gc = g[(px, py)], g[cur]
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)):
            nx, ny = cur[0] + dx, cur[1] + dy
            if not (0 <= nx < cols and 0 <= ny < rows) or map[ny, nx] != 255:
                continue
            nxt = (nx, ny)
            if nxt in closed:
                continue
            if parent[cur] != cur and line_of_sight(map, (px, py), nxt):
                ng = pg + h((px, py), nxt)
                new_parent = (px, py)
            else:
                ng = gc + h(cur, nxt)
                new_parent = cur
            if ng < g.get(nxt, math.inf):
                g[nxt] = ng
                parent[nxt] = new_parent
                heapq.heappush(open_list, (ng + h(nxt, goal), nxt))
    return None


def go_neighbor(type, count):
    assert type in ["x", "y", "xy"]
    if count == 0:
        return True
    now_position = get_player_position()
    if now_position is None:
        return "stuck"
    if type == "x":
        target = (now_position[0] + count, now_position[1])
    elif type == "y":
        target = (now_position[0], now_position[1] + count)
    else:
        target = (now_position[0] + count[0], now_position[1] + count[1])
    return go_direction(now_position, target)


def reset_keyboard():
    get_window().key_up(win32con.VK_SPACE)
    keyup("w")
    keyup("a")
    keyup("s")
    keyup("d")


def go_direction(start, end):
    """朝 end 移动，用 WASD 键盘控制；改为带迟滞的平滑走路，降低抖动和来回切键。"""
    w = get_window()
    last_dist, min_dist = 1e9, 1e9
    last_progress = time.monotonic()
    current_keys = set()
    def set_keys(keys):
        nonlocal current_keys
        for k in current_keys - keys:
            keyup(k)
        for k in keys - current_keys:
            keydown(k)
        current_keys = keys
    try:
        while True:
            pos = get_player_position()
            if pos is None:
                set_keys(set())
                return "stuck"
            d = distance(pos, end)
            if d <= ARRIVE:
                set_keys(set())
                return True

            stage = check_stage()
            if stage in ("in_game_dead", "in_menu"):
                set_keys(set())
                return stage

            # 只在“明显后退/明显无推进”时判定为卡住；允许 1~2px 误差，不要因抖动突然停止
            previous_min = min_dist
            min_dist = min(min_dist, d)
            if d < previous_min - 0.8 or d < last_dist - 0.8:
                last_progress = time.monotonic()
            if time.monotonic() - last_progress > MOVE_PROGRESS_TIMEOUT:
                set_keys(set())
                return "stuck"
            last_dist = d

            dx, dy = end[0] - pos[0], end[1] - pos[1]
            desired = set()
            if abs(dx) > 1.2:
                desired.add("d" if dx > 0 else "a")
            if abs(dy) > 1.2:
                desired.add("s" if dy > 0 else "w")

            # 平滑策略：保留当前方向，只有在明显偏离时才切换；防止 1px 级抖动引发来回按键
            if not desired:
                set_keys(set())
            elif current_keys and desired.issubset(current_keys):
                pass
            elif current_keys and (current_keys & desired):
                set_keys(current_keys & desired)
            else:
                set_keys(desired)
            time.sleep(0.05)
    finally:
        set_keys(set())


def lazy_theta_execute_path(path):
    if not path:
        return True
    for i in range(len(path) - 1):
        stage = check_stage()
        if stage != "in_game":
            return stage
        move = go_direction(path[i], path[i + 1])
        print(f"[移动] {i+1}/{len(path)-1}: {path[i]} -> {path[i+1]} ({'OK' if move==True else move})")
        if move == "stuck":
            reset_keyboard()
            return "stuck"
        if move in ("in_game_dead", "in_menu"):
            reset_keyboard()
            return move
        reset_keyboard()
    return True


def lazy_theta_pathing(location, area=[], step=0):
    """走到 location。step>0 时每次只走一段(长度≤step)后返回 'step_done'，让主循环检查战斗"""
    stuck_count = 0
    missing_position_count = 0
    while True:
        pos = get_player_position()
        if pos is None:
            missing_position_count += 1
            if check_stage() != "in_game":
                return False
            if missing_position_count >= MAX_STUCK:
                return "stuck_loop"
            time.sleep(0.3)
            continue
        missing_position_count = 0
        binary = load_binary_map()
        goal = calibrate_player(binary, location)
        print(f"[路径] {pos} -> {goal}")
        path = None
        if step > 0 and PATH_CACHE["goal"] == goal and PATH_CACHE["path"]:
            cached = PATH_CACHE["path"]
            nearest_index, nearest_distance = min(
                ((i, distance(pos, point)) for i, point in enumerate(cached)),
                key=lambda item: item[1],
            )
            if nearest_distance <= ARRIVE * 2:
                path = cached[nearest_index:]
                print(f"[路径] 复用剩余路径，偏差 {nearest_distance:.1f}px")
        if path is None:
            t0 = time.time()
            path = lazy_theta_star(binary, pos, goal)
            print(f"[路径] 规划耗时 {time.time() - t0:.3f}s")
        if path is None:
            PATH_CACHE.update(goal=None, path=None)
            print("[路径] 无路可达，执行反卡死...")
            execute_anti_stuck()
            stuck_count += 1
            if stuck_count >= MAX_STUCK:
                return "stuck_loop"
            continue
        if step > 0:
            # 分段：只走前 step 距离的一段，然后交回主循环
            seg = [path[0]]
            for p in path[1:]:
                seg.append(p)
                if distance(p, path[0]) >= step:
                    break
            stat = lazy_theta_execute_path(seg)
            if stat == "stuck":
                PATH_CACHE.update(goal=None, path=None)
                execute_anti_stuck()
                stuck_count += 1
                if stuck_count >= MAX_STUCK:
                    return "stuck_loop"
                continue
            if stat in ("in_game_dead", "in_menu"):
                PATH_CACHE.update(goal=None, path=None)
                return False
            current_pos = get_player_position()
            if current_pos is not None and (
                    if_in_area(area, current_pos) or
                    distance(current_pos, goal) <= ARRIVE):
                PATH_CACHE.update(goal=None, path=None)
                return True
            segment_end = len(seg) - 1
            remaining = path[segment_end:]
            PATH_CACHE.update(goal=goal, path=remaining if len(remaining) > 1 else None)
            return "step_done"
        PATH_CACHE.update(goal=None, path=None)
        stat = lazy_theta_execute_path(path)
        pos = get_player_position()
        if pos is not None and (if_in_area(area, pos) or distance(pos, goal) <= ARRIVE):
            return True
        if stat == "stuck":
            stuck_count += 1
            print("[路径] 卡住，执行反卡死...")
            execute_anti_stuck()
            time.sleep(0.3)
            if stuck_count >= MAX_STUCK:
                return "stuck_loop"
        elif stat in ("in_game_dead", "in_menu"):
            return False
        else:
            stuck_count = 0


# ================= 战斗模式（只打M怪/避U怪/贴脸撤退） =================

def screen_to_map_safe(pt, pos):
    try:
        from combat import screen_to_map
        m = screen_to_map(pt, pos)
        return m if m is not None else None
    except Exception:
        return None


def chase_target(patrol_goal, trail):
    """追击最近的 M 怪（右键由防御线程持续按住=自动攻击）。
    每帧刷新最近目标；U 贴脸返回 'ultra' 交主循环；怪没了/超时返回 'done'
    用 WASD 键盘移动"""
    from combat import detect_mobs, choose_target, ultra_blocked, map_to_screen
    w = get_window()
    start_time = time.time()
    current_keys = set()
    def set_k(keys):
        nonlocal current_keys
        for k in current_keys - keys:
            keyup(k)
        for k in keys - current_keys:
            keydown(k)
        current_keys = keys
    try:
        while True:
            if time.time() - start_time > 15:
                print("[战斗] 追击超时，放弃")
                return "done"
            pos = get_player_position()
            if pos is None:
                set_k(set())
                time.sleep(0.3)
                continue
            trail.append(pos)
            frame = get_frame()
            mythics, ultras = detect_mobs(frame)
            ultras_map = [m for m in (screen_to_map_safe(u, pos) for u in ultras) if m]
            if ultra_blocked(ultras_map, pos):
                return "ultra"
            mythics_map = [m for m in (screen_to_map_safe(m, pos) for m in mythics) if m]
            t = choose_target(mythics_map, patrol_goal, pos)
            if t is None:
                print("[战斗] M 怪消失，结束追击")
                return "done"
            # 攻击态保持目标距离1-2地图像素, 右键攻击不受影响
            dx, dy = t[0] - pos[0], t[1] - pos[1]
            dist = math.hypot(dx, dy)
            from combat import _attack_movement_keys
            keys = _attack_movement_keys(dx, dy)
            set_k(keys)
            if int(time.time() * 2) % 6 == 0:
                print(f"[战斗] 追击 M 怪 {t}, 玩家 {pos}, dist={dist:.1f} "
                      f"{'(停住攻击)' if 1.0 <= dist <= 2.0 else ''}")
            time.sleep(0.05)
    finally:
        set_k(set())


def handle_ultra(pos, near_u, trail, chasers=None):
    """U 怪贴脸：先尝试绕开（U 周围 5px 设墙重规划）；
    绕不开则贴到距 U 0.5px 处，再沿原路撤退直到 U 消失"""
    from combat import (build_avoid_map, ULTRA_KISS, ULTRA_AVOID,
                        detect_mobs, screen_to_map)
    from flee_planner import plan_flee
    binary = load_binary_map()
    snapped_pos = calibrate_player(binary, pos)
    plan = plan_flee(binary, snapped_pos, chasers or [near_u])
    if plan:
        escape = plan["goal"]
        path = lazy_theta_star(binary, snapped_pos, escape)
        if path and len(path) > 1:
            segment = [path[0]]
            for point in path[1:]:
                segment.append(point)
                if distance(point, path[0]) >= PATH_STEP:
                    break
            print(f"[U] 追逃规划: goal={escape}, lead={plan['lead']:.1f}, "
                  f"{'安全' if plan['safe'] else '无安全路线'}")
            result = lazy_theta_execute_path(segment)
            if result is True or result in ("in_game_dead", "in_menu"):
                return result
    dx, dy = pos[0] - near_u[0], pos[1] - near_u[1]
    nd = math.hypot(dx, dy) or 1.0
    # 1) 尝试绕开
    avoid = build_avoid_map(binary, [near_u], pos)
    escape = calibrate_player(avoid, (pos[0] + dx / nd * 40, pos[1] + dy / nd * 40))
    p = lazy_theta_star(avoid, pos, escape)
    if p:
        print("[U] 尝试绕开...")
        lazy_theta_execute_path(p)
        return True
    # 2) 绕不开：贴脸 0.5px
    print("[U] 无法绕开，贴脸 0.5px 后沿原路撤退")
    kiss = calibrate_player(binary, (near_u[0] + dx / nd * ULTRA_KISS,
                                     near_u[1] + dy / nd * ULTRA_KISS))
    go_direction(pos, kiss)
    # 3) 沿原路撤退直到 U 检测不到
    while True:
        pos = get_player_position()
        if pos is None:
            time.sleep(0.3)
            continue
        stage = check_stage()
        if stage != "in_game":
            return stage
        _, ultras = detect_mobs()
        if not ultras:
            print("[U] U 已消失，恢复正常巡逻")
            return True
        if trail:
            goal = trail.pop()
        else:
            nd = math.hypot(pos[0] - near_u[0], pos[1] - near_u[1]) or 1.0
            goal = calibrate_player(binary,
                (pos[0] + (pos[0] - near_u[0]) / nd * 50,
                 pos[1] + (pos[1] - near_u[1]) / nd * 50))
        go_direction(pos, goal)


if __name__ == "__main__":
    import threading

    # ===== 内存模式接入(WebSocket hook 数据桥, 截图识别自动回退) =====
    # v1.38.2: 之前 bridge_combat/afk_solver 等模块从未接入主循环, 现接入:
    #   玩家位置/游戏状态优先用内存真实数据(世界坐标/206.5=地图坐标), 无hook时回退截图
    MEMORY_OK = False
    memory_api = None
    try:
        import ws_client
        ws_client.start()
        import bridge_combat as memory_api
        MEMORY_OK = True
        print("[+] 内存模式: 桥接已启动(hook数据可用时优先真实玩家/怪数据)")
    except Exception as _e:
        print(f"[!] 内存模式不可用(自动回退截图识别): {_e}")

    WORLD_TO_MAP = 206.5  # 世界单位/地图像素

    def check_stage_smart():
        """状态检测: 内存模式有玩家数据=游戏中(绕开小地图缺失/菜单误判); 否则回退截图"""
        if MEMORY_OK:
            try:
                if memory_api.get_player() is not None:
                    return "in_game"
            except Exception:
                pass
        return check_stage()

    def get_pos_smart(image=None):
        """玩家位置: 内存(世界坐标)优先, 回退截图小地图识别"""
        if MEMORY_OK:
            try:
                p = memory_api.get_player()
                if p and p.get('x') is not None:
                    return (p['x'] / WORLD_TO_MAP, p['y'] / WORLD_TO_MAP)
            except Exception:
                pass
        return get_player_position(image=image)

    # ===== 地图选择：python main.py [地图名]（自动忽略注释等无效参数）=====
    available = [p[:-4] for p in os.listdir(MAP_DIR) if p.lower().endswith(".png")]
    map_name = None
    for a in sys.argv[1:]:
        if a.startswith("--map="):
            a = a.split("=", 1)[1]
        if a in available:
            map_name = a
            break
    if map_name is None:
        real_args = [a.split("=", 1)[1] if a.startswith("--map=") else a
                     for a in sys.argv[1:] if not a.startswith("::")]
        if real_args:
            print(f"[!] 未知地图 '{real_args[0]}'，可选: {available}")
            exit(1)
        map_name = None  # 不传参数 -> init窗口后自动识别, 失败默认anthell

    from config import load_config
    settings = load_config() or {}
    control_mode = settings.get("mode", "defense")
    if control_mode not in ("attack", "defense", "none"):
        control_mode = "defense"

    # ===== 初始化后台窗口 =====
    if not init_window("florr.io"):
        print("[!] 请先打开浏览器，进入 florr.io，最大化窗口后再运行(无需F11全屏)")
        exit(1)
    get_window().move_offscreen()
    get_window().right_button_up()
    get_window().key_up(win32con.VK_SPACE)
    print("[+] 脚本运行中... 按 Ctrl+C 停止（停止后窗口自动移回）")

    # ===== 地图自动识别 (没传参数时用截图模板匹配当前地图) =====
    if map_name is None:
        try:
            from map_auto_detect import detect_map
            from utils import get_frame, detect_canvas_offset
            detect_canvas_offset()
            auto = detect_map(get_frame())
            if auto in available:
                map_name = auto
                print(f"[+] 自动识别地图: {map_name}")
        except Exception as _e:
            print(f"[!] 地图自动识别失败: {_e}")
        if map_name is None:
            map_name = "anthell"
            print(f"[+] 默认地图: {map_name}")

    # ===== 后台攻击/防御控制 =====
    control_running = True
    def control_loop():
        while control_running:
            if control_mode == "defense":
                get_window().right_button_down()
            elif control_mode == "attack":
                get_window().key_down(win32con.VK_SPACE)
            time.sleep(0.5)
    control_thread = threading.Thread(target=control_loop, daemon=True)
    control_thread.start()
    mode_text = {"attack": "空格攻击", "defense": "右键防御", "none": "手动控制"}[control_mode]
    print(f"[+] 控制模式: {mode_text}")

    try:
        apply_map(map_name)
        print(f"[+] 地图: {map_name}")
        from map_select import (generate_patrol_points, generate_random_patrol_point,
                    select_patrol_points)
        from config import REGION_TABLE, region_patrol_points
        patrol_region = None
        region_label = None
        if map_name in REGION_TABLE:
            configured_region = settings.get("region", "")
            if settings.get("region_map") != map_name:
                configured_region = "auto"
            allowed_regions = {row[0] for row in REGION_TABLE[map_name]}
            if configured_region not in allowed_regions and configured_region != "auto":
                configured_region = "auto"
            region_label, _, patrol_region = region_patrol_points(
                map_name, configured_region or "auto", settings.get("kill_rank", "mythic"))
            if patrol_region:
                print(f"[区域] {region_label} 中心={patrol_region[:2]} 半径={patrol_region[2]}px")
        patrol_spacing = max(6, min(35, patrol_region[2] // 3)) if patrol_region else 35
        patrol_points = generate_patrol_points(
            map_name, min_distance=patrol_spacing, region=patrol_region)
        if not patrol_points and patrol_region:
            print("[!] 推荐区域内可走点不足，改为整图自动巡逻")
            patrol_region = None
            patrol_points = generate_patrol_points(map_name)
        if patrol_points:
            print(f"[巡逻点] 自动巡逻区域已就绪，初始候选 {len(patrol_points)} 个")
            random_patrol = True
            patrol_points = [random.choice(patrol_points)]
        else:
            print("[!] 自动生成巡逻点失败，回退到手动选择")
            patrol_points = select_patrol_points(map_name)
            random_patrol = False

        def choose_next_patrol_point(previous):
            point = generate_random_patrol_point(map_name, region=patrol_region, avoid=previous)
            if point is None and patrol_region:
                print("[!] 区域内没有可用点，改为整图随机巡逻")
                point = generate_random_patrol_point(map_name, avoid=previous)
            return point
        # 标定实际窗口客户区尺寸(兼容4K显示器/DPI缩放, 不再硬编码1920x1080)
        from combat import calibrate_screen
        try:
            calibrate_screen()
        except Exception as e:
            print(f"[!] 屏幕标定失败(使用默认1080p): {e}")
        # 检测游戏画布偏移(浏览器标签栏+地址栏高度, 最大化非全屏时需要)
        from utils import detect_canvas_offset
        try:
            detect_canvas_offset()
        except Exception as e:
            print(f"[!] 画布偏移检测失败: {e}")
        if COMBAT_ENABLED:
            print("[+] 战斗模式: 只打 M 怪(青)，避开 U 怪(粉) 5px，贴脸 0.5px 沿原路撤退")

        dedicated_area = []   # 可选：[[左上], [右下]]，进入该区域即算到达
        patrol_index = 0
        trail = deque(maxlen=TRAIL_MAX)
        heal_active = False
        heal_slot = None
        heal_path = []
        heal_path_index = -1
        heal_warned = False
        heal_slots = settings.get("heal_slots", [])
        heal_type = settings.get("heal_type", "rose")

        def tap_slot(slot_number):
            key = "0" if slot_number == 10 else str(slot_number)
            vk = ord(key)
            w = get_window()
            w.key_down(vk)
            try:
                time.sleep(0.05)
            finally:
                w.key_up(vk)

        def release_move_keys():
            for key in ("w", "a", "s", "d"):
                keyup(key)

        def direction_keys(dx, dy):
            keys = set()
            if abs(dx) > 0.2:
                keys.add("d" if dx > 0 else "a")
            if abs(dy) > 0.2:
                keys.add("s" if dy > 0 else "w")
            if len(keys) == 2 and abs(dx) < abs(dy):
                keys.discard("d" if dx > 0 else "a")
            elif len(keys) == 2:
                keys.discard("s" if dy > 0 else "w")
            return keys

        print(f"[巡逻模式] 共 {len(patrol_points)} 个巡逻点，循环移动中...")

        # ===== 防挂机后台线程: 验证弹窗自动破解(截图/内存战斗都生效) =====
        _afk_running = True
        def _afk_loop():
            while _afk_running:
                try:
                    from afk_solver import try_solve_and_drag
                    if try_solve_and_drag(get_window(), get_frame()):
                        print("[防挂机] 检测到验证弹窗并已自动破解")
                except Exception:
                    pass
                time.sleep(12)
        threading.Thread(target=_afk_loop, daemon=True).start()

        # ===== 死亡自救(ygg求复活, PostMessage打字不抢焦点) + 聊天挑战监控(防封号) =====
        _death_start = 0.0   # 死亡时刻, 0=未死
        _last_ygg = 0.0      # 上次发ygg时间
        chat_solver_obj = None
        try:
            from chat_solver import ChatSolver
            chat_solver_obj = ChatSolver(get_window(), get_frame)
            chat_solver_obj.start()
            print("[+] 聊天挑战监控已启动(防封号: 检测新消息/管理员红字自动回复)")
        except Exception as _e:
            print(f"[!] 聊天监控不可用: {_e}")

        def _send_ygg():
            try:
                w = get_window()
                w.key_down(0x0D); time.sleep(0.05); w.key_up(0x0D)
                time.sleep(0.3)
                for ch in "ygg":
                    vk = ord(ch.upper())
                    w.key_down(vk); time.sleep(0.04); w.key_up(vk)
                time.sleep(0.2)
                w.key_down(0x0D); time.sleep(0.05); w.key_up(0x0D)
                print("[死亡] 发 ygg 求复活")
            except Exception as _e:
                print(f"[死亡] ygg发送失败: {_e}")

        # ===== 内存战斗优先: 有hook数据时跑完整内存战斗(真实玩家/怪/弹道/Super雷达/低血回血/危险躲避), 无数据15s自动回退截图 =====
        if MEMORY_OK:
            try:
                from memory_battle import MemoryBattle
                print("[内存模式] 启动完整内存战斗(每200ms读真实游戏内存)")
                _mb = MemoryBattle(get_window())
                _mb.no_data_timeout = 15.0
                _mb.battle_loop()
                print("[内存模式] 内存战斗退出(无hook数据), 回退截图巡逻模式")
            except KeyboardInterrupt:
                raise
            except Exception as _e:
                print(f"[!] 内存战斗异常, 回退截图巡逻: {_e}")

        # 主循环需要的 combat 函数(一次性import, 避免作用域内NameError)
        from combat import detect_mobs, screen_to_map, ultra_blocked, choose_target

        # 防挂机: 定时切换花瓣槽位(slot)
        last_slot_switch = time.time()
        next_slot_interval = 60 + random.random() * 30  # 60-90秒

        while True:
            now = time.time()
            # 防挂机: 定时切换槽位
            if not heal_active and now - last_slot_switch > next_slot_interval:
                slot_key = random.choice(['1','2','3','4','5','6','7','8','9','0'])
                print(f"[防挂机] 切换槽位 {slot_key}")
                w = get_window()
                vk = ord(slot_key)
                w.key_down(vk)
                time.sleep(0.05 + random.random() * 0.1)
                w.key_up(vk)
                time.sleep(0.05 + random.random() * 0.1)
                w.key_down(vk)
                time.sleep(0.05 + random.random() * 0.1)
                w.key_up(vk)
                last_slot_switch = now
                next_slot_interval = 60 + random.random() * 30

            # 先检查状态 (内存模式优先: 有玩家数据=游戏中, 绕开小地图/菜单误判)
            stage = check_stage_smart()
            if stage == "in_game_dead":
                # 死亡自救: 先每10s发ygg求复活, 2分钟没人救再点Continue回家
                if _death_start == 0.0:
                    _death_start = time.time()
                    print("[!] 死亡，开始自救(每10s发ygg求复活, 2分钟没救就回家)")
                if time.time() - _death_start < 120:
                    if time.time() - _last_ygg > 10:
                        _send_ygg()
                        _last_ygg = time.time()
                else:
                    _death_start = 0.0
                    print("[!] 2分钟没人复活, 点Continue回家")
                    respawn()
                continue
            elif stage == "in_menu":
                print("[!] 在菜单，自动点击开始...")
                # 自动点击"开始"按钮(屏幕中央偏下, 按比例)
                w = get_window()
                frame = get_frame()
                fh, fw = frame.shape[:2]
                off = utils._canvas_y_offset
                game_h = max(fh - off, 1)
                bx, by = int(960 * fw / 1920), off + int(650 * game_h / 1080)
                by = min(by, fh - 1)
                w.left_click(bx, by)
                print(f"[!] 已点击开始({bx},{by})，等待加载...")
                time.sleep(5)
                continue

            pos = get_pos_smart()
            if pos is not None:
                trail.append(pos)

            protocol_player = None
            if MEMORY_OK:
                try:
                    protocol_player = memory_api.get_player()
                except Exception:
                    pass
            hp_percent = protocol_player.get("hp_percent") if protocol_player else None

            if (not heal_active and hp_percent is not None and hp_percent < 0.10
                    and protocol_player is not None):
                heal_active = True
                heal_path = list(trail)
                heal_path_index = len(heal_path) - 2
                try:
                    from memory_battle import find_heal_slot
                    heal_slot = find_heal_slot(
                        memory_api.get_secondary_slots(), heal_slots, heal_type)
                except Exception:
                    heal_slot = None
                if heal_slot is not None:
                    tap_slot(heal_slot)
                    print(f"[回血] HP低于10%，切换副槽{heal_slot} ({heal_type})")
                elif not heal_warned:
                    print(f"[回血] HP低于10%，配置副槽中没有核验到 {heal_type}，只撤退")
                    heal_warned = True
                if control_mode != "defense":
                    get_window().right_button_down()

            if heal_active:
                if hp_percent is not None and hp_percent > 0.70:
                    if heal_slot is not None:
                        tap_slot(heal_slot)
                        print("[回血] HP恢复超过70%，切回原副槽状态")
                    if control_mode != "defense":
                        get_window().right_button_up()
                    heal_active = False
                    heal_slot = None
                    heal_path = []
                    heal_path_index = -1
                else:
                    while heal_path_index >= 0:
                        retreat_target = heal_path[heal_path_index]
                        current = get_pos_smart()
                        if current is None:
                            release_move_keys()
                            break
                        if distance(current, retreat_target) <= ARRIVE:
                            heal_path_index -= 1
                            continue
                        dx = retreat_target[0] - current[0]
                        dy = retreat_target[1] - current[1]
                        retreat_keys = direction_keys(dx, dy)
                        release_move_keys()
                        for key in retreat_keys:
                            keydown(key)
                        try:
                            time.sleep(0.10)
                        finally:
                            for key in retreat_keys:
                                keyup(key)
                        break
                    if heal_path_index < 0:
                        release_move_keys()
                    time.sleep(0.05)
                    continue

            if MEMORY_OK and protocol_player is not None:
                try:
                    from flee_planner import plan_projectile_dodge
                    incoming = plan_projectile_dodge(
                        (protocol_player["x"], protocol_player["y"]),
                        memory_api.get_projectiles(),
                        player_radius=protocol_player.get("radius") or 0.0)
                except Exception:
                    incoming = None
                if incoming is not None:
                    dodge_keys = direction_keys(*incoming["dir"])
                    release_move_keys()
                    for key in dodge_keys:
                        keydown(key)
                    try:
                        time.sleep(0.12)
                    finally:
                        for key in dodge_keys:
                            keyup(key)
                    print(f"[弹道闪避] {incoming['type']} ETA={incoming['eta']:.2f}s，垂直闪避")
                    continue

            goal_pt = patrol_points[patrol_index]

            # ===== 战斗检测（仅巡逻间隙/分段间执行）=====
            if COMBAT_ENABLED:
                frame = get_frame()
                mythics, ultras = detect_mobs(frame)
                pos = get_pos_smart(image=frame)
                if pos is not None:
                    ultras_map = [m for m in (screen_to_map_safe(u, pos) for u in ultras) if m]
                    near_u = None
                    from combat import ultra_blocked
                    near_u = ultra_blocked(ultras_map, pos)
                    if near_u:
                        r = handle_ultra(pos, near_u, trail, ultras_map)
                        if r in ("in_game_dead", "in_menu"):
                            continue
                        continue
                    mythics_map = [m for m in (screen_to_map_safe(m, pos) for m in mythics) if m]
                    from combat import choose_target
                    target = choose_target(mythics_map, goal_pt, pos)
                    if target is not None:
                        print(f"[战斗] 发现 M 怪 {target}，追击...")
                        r = chase_target(goal_pt, trail)
                        if r == "ultra":
                            continue
                        print("[战斗] 结束，继续巡逻")
                        continue

            # ===== 正常巡逻（分段走，走一段回来看怪）=====
            result = lazy_theta_pathing(goal_pt, dedicated_area, step=PATH_STEP if COMBAT_ENABLED else 0)
            if result is True:
                if random_patrol:
                    next_point = choose_next_patrol_point(goal_pt)
                    if next_point is not None:
                        patrol_points[0] = next_point
                        print(f"[巡逻] 到达目标，随机新目标 {next_point}")
                    else:
                        print("[!] 无法生成新巡逻点，保持当前目标")
                else:
                    print(f"[巡逻] 到达点 {patrol_index+1}，前往下一个点")
                    patrol_index = (patrol_index + 1) % len(patrol_points)
                PATH_CACHE.update(goal=None, path=None)
                # 防挂机: 到达巡逻点后随机停顿 0.5-2.5 秒
                pause = 0.5 + random.random() * 2.0
                print(f"[防挂机] 随机停顿 {pause:.1f}s")
                time.sleep(pause)
            elif result == "step_done":
                continue
            elif result == "stuck_loop":
                if random_patrol:
                    next_point = choose_next_patrol_point(goal_pt)
                    if next_point is not None:
                        patrol_points[0] = next_point
                        PATH_CACHE.update(goal=None, path=None)
                        print(f"[巡逻] 当前目标卡住，改走随机点 {next_point}")
                else:
                    print(f"[巡逻] 点 {patrol_index+1} 反复卡住，跳过该点")
                    patrol_index = (patrol_index + 1) % len(patrol_points)
            # result 为 False 说明死了或回菜单，循环回去处理
    except KeyboardInterrupt:
        print("\n[!] 用户中断")
    finally:
        control_running = False
        control_thread.join(timeout=1.0)
        try:
            _afk_running = False
        except Exception:
            pass
        if 'chat_solver_obj' in dir() and chat_solver_obj is not None:
            try:
                chat_solver_obj.stop()
            except Exception:
                pass
        reset_keyboard()
        get_window().right_button_up()
        print("[+] 右键防御已关闭")
        get_window().move_onscreen()
        print("[+] 窗口已移回屏幕")
