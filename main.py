import os
import sys
import time
import math
import random
import heapq
import win32con
from collections import deque
from utils import *
from window_ctrl import init_window, get_window
from config import load_config, save_config, ask_config, ask_update, MODE_NAMES, RANK_NAMES

MAX_STUCK = 5   # 连续卡死/无路次数上限，超过则跳过当前巡逻点
PATH_STEP = 40  # 巡逻分段长度(地图像素)：每走完一段回主循环检查战斗
COMBAT_ENABLED = True  # 战斗模式总开关
TRAIL_MAX = 800        # 撤退轨迹缓存长度
MOVE_PROGRESS_TIMEOUT = 1.5  # 持续无有效进展多久才判定卡住
PATH_CACHE = {"goal": None, "path": None}
SHOW_MAP_WINDOW = True                  # 实时地图窗口: 红=路径 绿=玩家 蓝=巡逻点 黄=目标

# ===== 人性化模拟（让脚本玩得像真人）=====
HUMANIZE = True            # 总开关
HUMAN_BLINK_MIN = 6        # 移动中"眨眼"停顿间隔范围(秒)
HUMAN_BLINK_MAX = 15
HUMAN_PAUSE_CHANCE = 0.2   # 每段巡逻后随机停顿概率
HUMAN_REACT_MIN = 0.2      # 发现M怪后的反应延迟范围(秒, 真人不会秒冲)
HUMAN_REACT_MAX = 0.5
HUMAN_MOUSE_MIN = 4        # 鼠标微动间隔范围(秒)
HUMAN_MOUSE_MAX = 12
HUMAN_RELEASE_CHANCE = 0.02  # 防御线程偶尔松手概率(模拟真人手抖)


def human_ticks(w, goal):
    '''人性化微操作(替代定时换卡防挂机):
    - 微转向: 随机朝一个方向轻按 0.08-0.15s(像人看旁边), 路径规划会自动修正, 不影响到达
    - 微停顿: 0.2-0.6s 随机犹豫
    - 微抖动: 偶尔同向再点一下(模拟按键不干脆)
    全部无副作用: 不切槽位、不丢输出、不打断战斗配置, 但制造不规则输入流抗挂机检测'''
    r = random.random()
    if r < 0.18:
        k = random.choice(['a', 'd', 'w', 's'])
        w.key_down(ord(k)); time.sleep(0.08 + random.random() * 0.07); w.key_up(ord(k))
        if random.random() < 0.3:   # 偶尔同向再点一下(像人按键不干脆)
            time.sleep(0.03); w.key_down(ord(k)); time.sleep(0.05); w.key_up(ord(k))
    elif r < 0.30:
        time.sleep(0.2 + random.random() * 0.4)


# ===== 日志节流: 同一条消息 min_gap 秒内只打印一次(防刷屏) =====
_last_log = {}
def throttle_print(key, msg, min_gap=3.0):
    import time as _t
    now = _t.monotonic()
    if now - _last_log.get(key, -999) > min_gap:
        _last_log[key] = now
        print(msg)


# ===== 控制台标题实时状态(黑窗口标题显示当前在干嘛) =====
def set_title(s):
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW("florr 挂机 - " + s)
    except Exception:
        pass


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
    last_blink = None
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
            # 人性化: 随机眨眼停顿(模拟真人手抖)
            if HUMANIZE:
                if last_blink is None or time.monotonic() - last_blink > HUMAN_BLINK_MIN + random.random() * (HUMAN_BLINK_MAX - HUMAN_BLINK_MIN):
                    last_blink = time.monotonic()
                    set_keys(set())
                    time.sleep(0.08 + random.random() * 0.17)
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
        # 人性化: 每段后随机停顿(像真人看看四周)
        if HUMANIZE and random.random() < HUMAN_PAUSE_CHANCE:
            time.sleep(0.3 + random.random() * 0.7)
    return True


def lazy_theta_pathing(location, area=[], step=0):
    """走到 location。step>0 时每次只走一段(长度≤step)后返回 'step_done'，让主循环检查战斗"""
    stuck_count = 0
    while True:
        pos = get_player_position()
        if pos is None:
            time.sleep(0.3)
            continue
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


def chase_target(patrol_goal, trail, kill_rank, stop_dist=None):
    """追击 =秒杀等级的怪; 攻击模式停 2px, 防御模式贴 0.5px; >秒杀贴近返回 'danger'; 低血返回 'lowhp'"""
    from combat import (detect_all, choose_target, ultra_blocked, screen_to_map_safe,
                        RANK_ORDER, KILL_STOP, CHASE_WARN, KISS_SLOW,
                        get_hp_ratio, HP_FLEE)
    stop = KILL_STOP if stop_dist is None else stop_dist
    w = get_window()
    start_time = time.time()
    idx = RANK_ORDER.index(kill_rank) if kill_rank in RANK_ORDER else 5
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
            ranks_map = detect_all(frame)
            danger = []
            for r in RANK_ORDER[idx + 1:]:
                danger += [m for m in (screen_to_map_safe(p, pos) for p in (ranks_map.get(r) or [])) if m]
            if ultra_blocked(danger, pos, margin=CHASE_WARN):
                return "danger"
            hp = get_hp_ratio(frame)
            if hp is not None and hp < HP_FLEE:
                print("[低血] 追击中血量过低，中断逃跑")
                return "lowhp"
            from combat import detect_projectiles
            near_p = nearest_proj(detect_projectiles(frame))
            if near_p:
                print("[闪避] 打怪中闪避飞行物")
                dodge_proj(near_p)
            prey = [m for m in (screen_to_map_safe(p, pos) for p in (ranks_map.get(kill_rank) or [])) if m]
            t = choose_target(prey, patrol_goal, pos)
            if t is None:
                print("[战斗] 目标消失，结束追击")
                return "done"
            dx, dy = t[0] - pos[0], t[1] - pos[1]
            dist = math.hypot(dx, dy)
            keys = set()
            if dist > stop:
                if dist <= KISS_SLOW:
                    # 贴脸减速: 间歇点按, 像人小心翼翼试探靠近
                    if int(time.time() * 4) % 2 == 0:
                        if abs(dx) > 1.5:
                            keys.add("d" if dx > 0 else "a")
                        if abs(dy) > 1.5:
                            keys.add("s" if dy > 0 else "w")
                else:
                    if abs(dx) > 1.5:
                        keys.add("d" if dx > 0 else "a")
                    if abs(dy) > 1.5:
                        keys.add("s" if dy > 0 else "w")
            set_k(keys)
            if int(time.time() * 2) % 6 == 0:
                print(f"[战斗] 追击 {t}, 玩家 {pos}, dist={dist:.1f} {'(停住攻击)' if dist<=stop else ''}")
            time.sleep(0.05)
    finally:
        set_k(set())


def handle_danger(pos, near, ranks_map, trail, kill_rank):
    """>秒杀等级的危险怪: 先尝试绕开(5px设墙); 绕不开则往怪最少的方向跑, 直到脱离"""
    from combat import (build_avoid_map, detect_all, screen_to_map_safe,
                        RANK_ORDER, escape_direction)
    binary = load_binary_map()
    dx, dy = pos[0] - near[0], pos[1] - near[1]
    nd = math.hypot(dx, dy) or 1.0
    # 1) 尝试绕开
    avoid = build_avoid_map(binary, [near], pos)
    escape = calibrate_player(avoid, (pos[0] + dx / nd * 40, pos[1] + dy / nd * 40))
    p = lazy_theta_star(avoid, pos, escape)
    if p:
        print("[危险] 尝试绕开...")
        lazy_theta_execute_path(p)
        return True
    # 2) 绕不开：往怪最少的方向跑
    print("[危险] 绕不开，往怪最少的方向跑")
    ex, ey = escape_direction(ranks_map, pos, binary=binary)
    goal = calibrate_player(binary, (pos[0] + ex * 50, pos[1] + ey * 50))
    p2 = lazy_theta_star(binary, pos, goal)
    if p2:
        lazy_theta_execute_path(p2)
def draw_overlay_window(patrol_points, pos=None):
    """实时地图窗口: 红=寻路路径 绿=玩家 蓝=巡逻点 黄=当前目标(每0.3s刷新)"""
    try:
        import cv2
        from utils import load_binary_map
        binary = load_binary_map()
        disp = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
        for i, pt in enumerate(patrol_points, 1):
            cv2.circle(disp, (int(pt[0]), int(pt[1])), 3, (255, 128, 0), -1)
            cv2.putText(disp, str(i), (int(pt[0]) + 3, int(pt[1]) - 3),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 128, 0), 1)
        path = PATH_CACHE.get("path")
        if path:
            for a, b in zip(path, path[1:]):
                cv2.line(disp, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), (0, 0, 255), 1)
        goal = PATH_CACHE.get("goal")
        if goal:
            cv2.circle(disp, (int(goal[0]), int(goal[1])), 4, (0, 255, 255), -1)
        if pos is None:
            pos = get_player_position()
        if pos:
            cv2.circle(disp, (int(pos[0]), int(pos[1])), 4, (0, 255, 0), -1)
        big = cv2.resize(disp, (600, 600), interpolation=cv2.INTER_NEAREST)
        cv2.imshow("florr 地图 (红=路径 绿=玩家 蓝=巡逻点 黄=目标)", big)
        cv2.waitKey(1)
    except Exception:
        pass


def dodge_proj(proj_screen):
    """飞行物来袭: 向远离它的垂直方向横向闪避 0.25s(像人走位躲导弹)"""
    from combat import get_screen_center
    cx, cy = get_screen_center()
    dx, dy = proj_screen[0] - cx, proj_screen[1] - cy
    nd = math.hypot(dx, dy) or 1.0
    vx, vy = -dy / nd, dx / nd
    ax, ay = cx + vx * 40, cy + vy * 40
    bx, by = cx - vx * 40, cy - vy * 40
    far = (ax, ay) if math.hypot(ax - proj_screen[0], ay - proj_screen[1]) > \
          math.hypot(bx - proj_screen[0], by - proj_screen[1]) else (bx, by)
    mvx, mvy = far[0] - cx, far[1] - cy
    keys = set()
    if abs(mvx) > 5:
        keys.add("d" if mvx > 0 else "a")
    if abs(mvy) > 5:
        keys.add("s" if mvy > 0 else "w")
    for k in keys:
        keydown(k)
    time.sleep(0.25)
    for k in keys:
        keyup(k)


def nearest_proj(projs):
    """玩家周围 PROJ_DODGE_R 内最近的飞行物(屏幕坐标)或 None"""
    from combat import get_screen_center, PROJ_DODGE_R
    if not projs:
        return None
    cx, cy = get_screen_center()
    near = min(projs, key=lambda q: math.hypot(q[0] - cx, q[1] - cy))
    return near if math.hypot(near[0] - cx, near[1] - cy) <= PROJ_DODGE_R else None


def _slot_key(slot):
    """副槽位号 -> 数字键虚拟键码(1-9直接数字, 10用0键)"""
    return ord("0") if slot == 10 else ord(str(slot))


def flee_low_hp(trail, heal_slots=None):
    """血量<10%: 数字键把副槽回血花瓣槽位逐个切到主槽 + 右键防御 + 往怪少处跑; 恢复后再按切回"""
    from combat import detect_all, escape_direction, get_hp_ratio, HP_RECOVER
    w = get_window()
    slots = [int(s) for s in (heal_slots or []) if 1 <= int(s) <= 10]
    keys = [_slot_key(s) for s in slots]
    for k in keys:
        w.key_down(k); time.sleep(0.06); w.key_up(k); time.sleep(0.06)
    if slots:
        print(f"[低血] 切回血槽位{slots}到主槽, 防御跑路")
    w.right_button_down()
    try:
        binary = load_binary_map()
        while True:
            pos = get_player_position()
            if pos is None:
                time.sleep(0.3)
                continue
            stage = check_stage()
            if stage != "in_game":
                return stage
            rmap = detect_all()
            ex, ey = escape_direction(rmap, pos, binary=binary)
            goal = calibrate_player(binary, (pos[0] + ex * 60, pos[1] + ey * 60))
            p = lazy_theta_star(binary, pos, goal)
            if p:
                lazy_theta_execute_path(p)
            hp = get_hp_ratio()
            if hp is not None and hp > HP_RECOVER:
                print(f"[低血] 血量恢复到 {hp*100:.0f}%，切回原花瓣，回去继续")
                return True
            time.sleep(0.3)
    finally:
        # 无论恢复/死亡/回菜单, 都再按一次数字键切回玩家原花瓣并松开右键
        for k in keys:
            w.key_down(k); time.sleep(0.06); w.key_up(k); time.sleep(0.06)
        w.right_button_up()


def handle_danger(pos, near, ranks_map, trail, kill_rank):
    """>秒杀等级的危险怪: 先尝试绕开(5px设墙); 绕不开则往怪最少的方向跑, 直到脱离"""
    from combat import (build_avoid_map, detect_all, screen_to_map_safe,
                        RANK_ORDER, escape_direction)
    binary = load_binary_map()
    dx, dy = pos[0] - near[0], pos[1] - near[1]
    nd = math.hypot(dx, dy) or 1.0
    # 1) 尝试绕开
    avoid = build_avoid_map(binary, [near], pos)
    escape = calibrate_player(avoid, (pos[0] + dx / nd * 40, pos[1] + dy / nd * 40))
    p = lazy_theta_star(avoid, pos, escape)
    if p:
        print("[危险] 尝试绕开...")
        lazy_theta_execute_path(p)
        return True
    # 2) 绕不开：往怪最少的方向跑
    print("[危险] 绕不开，往怪最少的方向跑")
    ex, ey = escape_direction(ranks_map, pos, binary=binary)
    goal = calibrate_player(binary, (pos[0] + ex * 50, pos[1] + ey * 50))
    p2 = lazy_theta_star(binary, pos, goal)
    if p2:
        lazy_theta_execute_path(p2)
    # 3) 直到危险怪脱离(每0.6s重新看路变向, 像人边跑边躲)
    idx = RANK_ORDER.index(kill_rank) if kill_rank in RANK_ORDER else 5
    last_escape = time.time()
    while True:
        pos = get_player_position()
        if pos is None:
            time.sleep(0.3)
            continue
        stage = check_stage()
        if stage != "in_game":
            return stage
        rmap = detect_all()
        danger_now = []
        for r in RANK_ORDER[idx + 1:]:
            danger_now += [m for m in (screen_to_map_safe(p, pos) for p in (rmap.get(r) or [])) if m]
        if not ultra_blocked(danger_now, pos):
            print("[危险] 已脱离，恢复正常巡逻")
            return True
        if time.time() - last_escape > 0.6:
            ex, ey = escape_direction(rmap, pos, binary=binary)
            goal = calibrate_player(binary, (pos[0] + ex * 50, pos[1] + ey * 50))
            p = lazy_theta_star(binary, pos, goal)
            if p:
                lazy_theta_execute_path(p)
            last_escape = time.time()
        time.sleep(0.3)


if __name__ == "__main__":
    import threading

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
        map_name = "anthell"

    # ===== 初始化后台窗口 =====
    if not init_window("florr.io"):
        print("[!] 请先打开浏览器，进入 florr.io，最大化窗口后再运行(无需F11全屏)")
        exit(1)
    get_window().move_offscreen()
    set_title("运行中")
    print("[+] 脚本运行中... 按 Ctrl+C 停止（停止后窗口自动移回）")

    # ===== 后台防御线程：一直按住右键 =====
    # ===== 交互配置(弹窗让玩家选, 存档后只问要不要更新) =====
    cfg = load_config()
    if cfg is None or ask_update(cfg):
        cfg = ask_config()
        save_config(cfg)
    mode, kill_rank = cfg["mode"], cfg["kill_rank"]
    print("[配置] 模式=" + MODE_NAMES.get(mode, mode) + ", 打怪=" + RANK_NAMES.get(kill_rank, kill_rank))

    # ===== 攻防线程(按玩家选择) =====
    defense_running = True
    def defense_loop():
        while defense_running:
            get_window().right_button_down()
            if HUMANIZE and random.random() < HUMAN_RELEASE_CHANCE:
                get_window().right_button_up()
                time.sleep(0.1 + random.random() * 0.2)
                get_window().right_button_down()
            time.sleep(0.5)
    def attack_loop():
        while defense_running:
            get_window().key_down(win32con.VK_SPACE)
            if HUMANIZE and random.random() < HUMAN_RELEASE_CHANCE:
                get_window().key_up(win32con.VK_SPACE)
                time.sleep(0.1 + random.random() * 0.2)
                get_window().key_down(win32con.VK_SPACE)
            time.sleep(0.5)
    defense_thread = None
    if mode == "attack":
        defense_thread = threading.Thread(target=attack_loop, daemon=True)
        defense_thread.start()
        print("[+] 全程攻击模式已开启（持续按空格发射）")
    elif mode == "defense":
        defense_thread = threading.Thread(target=defense_loop, daemon=True)
        defense_thread.start()
        print("[+] 右键防御已开启（持续按住）")
    else:
        print("[+] 未开启自动攻防（手动操作）")

    # ===== 人性化: 鼠标微动线程(模拟真人动鼠标调花瓣方向) =====
    if HUMANIZE:
        mouse_running = True
        def human_mouse_loop():
            import win32api, win32gui
            w = get_window()
            while mouse_running:
                try:
                    l, t, r, b = win32gui.GetClientRect(w.hwnd)
                    cw, ch = r - l, b - t
                    sl, st = win32gui.ClientToScreen(w.hwnd, (0, 0))
                    mx = sl + random.randint(int(cw * 0.2), int(cw * 0.8))
                    my = st + random.randint(int(ch * 0.2), int(ch * 0.8))
                    win32api.SetCursorPos((mx, my))
                except Exception:
                    pass
                time.sleep(HUMAN_MOUSE_MIN + random.random() * (HUMAN_MOUSE_MAX - HUMAN_MOUSE_MIN))
        mouse_thread = threading.Thread(target=human_mouse_loop, daemon=True)
        mouse_thread.start()
        print("[+] 人性化模拟已开启（鼠标微动/眨眼/停顿/反应延迟）")

    try:
        apply_map(map_name)
        print(f"[+] 地图: {map_name}")
        from map_select import select_patrol_points
        if cfg.get("patrol_points") and cfg.get("patrol_points_map") == map_name:
            from config import _ask
            reuse = _ask("上次的巡逻点还在（这张地图），直接用吗？", [("y", "用上次的"), ("n", "重新设置")], "巡逻点")
            if reuse == "y":
                patrol_points = [tuple(p) for p in cfg["patrol_points"]]
                print(f"[巡逻点] 使用上次设置: {patrol_points}")
            else:
                patrol_points = select_patrol_points(map_name)
        else:
            patrol_points = select_patrol_points(map_name)
        cfg["patrol_points"] = [list(p) for p in patrol_points]
        cfg["patrol_points_map"] = map_name
        save_config(cfg)
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
            print("[+] 战斗策略: =秒杀等级自动追(贴0.5px), 更高避开(往怪少处跑), 更低不管")
        print("[!] 提醒: 请把回血花瓣(玫瑰/叶子)放在副槽(配置时勾选的槽位)——血量<10%%时插件自动切到主槽+防御跑路, 恢复后自动切回")
        # 自动扫描回血花瓣槽位候选(颜色只是候选, 弹窗人工确认防误检); 已确认过则跳过
        if cfg.get("heal_slots"):
            print(f"[扫描] 已确认回血槽位 {cfg['heal_slots']}，跳过扫描（如需重新扫描请删除 config.json）")
        else:
            try:
                from combat import scan_heal_slots, draw_heal_slots_mark
                _cand = scan_heal_slots()
                if _cand:
                    _desc = "  ".join(f"ROW{r}槽{s}({c})" for r, s, c in _cand)
                    print(f"[扫描] 回血花瓣候选: {_desc}")
                    draw_heal_slots_mark(get_frame(), _cand, "_heal_slots.png")
                    print("[扫描] 已保存 _heal_slots.png 供核对")
                    from config import ask_heal_confirm, save_config
                    _picked = ask_heal_confirm(_cand)
                    if _picked:
                        cfg["heal_slots"] = _picked
                        save_config(cfg)
                        print(f"[扫描] 已确认回血槽位: {_picked}（低血时自动切换）")
                    else:
                        print("[扫描] 未确认，使用原配置")
                else:
                    print("[扫描] 未检测到回血花瓣候选（如副槽有玫瑰请截图反馈）")
            except Exception as e:
                print(f"[扫描] 失败: {e}")

        dedicated_area = []   # 可选：[[左上], [右下]]，进入该区域即算到达
        patrol_index = 0
        trail = deque(maxlen=TRAIL_MAX)
        last_map_win = 0

        print(f"[巡逻模式] 共 {len(patrol_points)} 个巡逻点，循环移动中...")

        # 主循环需要的 combat 函数(一次性import, 避免作用域内NameError)
        from combat import detect_mobs, screen_to_map, ultra_blocked, choose_target

        while True:
            # 先检查状态
            stage = check_stage()
            if stage == "in_game_dead":
                set_title("死亡复活中")
                throttle_print("dead", "[!] 死亡，正在自动复活...", 2.0)
                respawn()
                continue
            elif stage == "in_menu":
                set_title("菜单等待")
                throttle_print("menu", "[!] 在菜单，按Enter开始(全键盘)...", 3.0)
                w = get_window()
                w.key_down(0x0D); time.sleep(0.1); w.key_up(0x0D)   # Enter 开始
                time.sleep(1.5)
                w.key_down(0x0D); time.sleep(0.1); w.key_up(0x0D)   # 再按一次(进选图/确认)
                time.sleep(5)
                continue

            pos = get_player_position()
            if pos is not None:
                trail.append(pos)

            goal_pt = patrol_points[patrol_index]

            # ===== 人性化微操作(防挂机, 无副作用): 微转向/微停顿/微抖动 =====
            if HUMANIZE and pos is not None and random.random() < 0.35:
                human_ticks(get_window(), goal_pt)

            # ===== 实时地图窗口(红线路径), 每0.3s刷新 =====
            if SHOW_MAP_WINDOW and time.time() - last_map_win > 0.3:
                draw_overlay_window(patrol_points, pos)
                last_map_win = time.time()

            # ===== 低血量保命(任何模式, 最高优先级) =====
            from combat import get_hp_ratio, HP_FLEE
            hp = get_hp_ratio(get_frame())
            if hp is not None and hp < HP_FLEE:
                set_title(f"低血逃跑! {hp*100:.0f}%")
                print(f"[低血] 血量 {hp*100:.0f}%，跑路...")
                r = flee_low_hp(trail, heal_slots=cfg.get("heal_slots", []))
                if r in ("in_game_dead", "in_menu"):
                    continue
                continue

            # ===== 战斗检测（仅巡逻间隙/分段间执行）=====
            # 策略: =秒杀等级自动追(贴0.5px), >秒杀等级避开(往怪少处跑), <秒杀等级不管
            if COMBAT_ENABLED and kill_rank != "none":
                frame = get_frame()
                pos = get_player_position(image=frame)
                if pos is not None:
                    from combat import (detect_all, ultra_blocked, choose_target,
                                        screen_to_map_safe, RANK_ORDER, WARN_MARGIN)
                    ranks_map = detect_all(frame)
                    idx = RANK_ORDER.index(kill_rank) if kill_rank in RANK_ORDER else 5
                    danger = []
                    for r in RANK_ORDER[idx + 1:]:
                        danger += [m for m in (screen_to_map_safe(p, pos) for p in (ranks_map.get(r) or [])) if m]
                    near = ultra_blocked(danger, pos, margin=WARN_MARGIN)
                    if near:
                        r = handle_danger(pos, near, ranks_map, trail, kill_rank)
                        if r in ("in_game_dead", "in_menu"):
                            continue
                        continue
                    # 飞行物(导弹/螯针等): 靠近就横向闪避
                    from combat import detect_projectiles
                    near_p = nearest_proj(detect_projectiles(frame))
                    if near_p:
                        print("[闪避] 飞行物来袭，横向闪避")
                        dodge_proj(near_p)
                        continue
                    prey = [m for m in (screen_to_map_safe(p, pos) for p in (ranks_map.get(kill_rank) or [])) if m]
                    target = choose_target(prey, goal_pt, pos)
                    if target is not None:
                        if HUMANIZE:
                            time.sleep(HUMAN_REACT_MIN + random.random() * (HUMAN_REACT_MAX - HUMAN_REACT_MIN))
                        set_title("战斗中")
                        print(f"[战斗] 发现目标 {target}，追击...")
                        stop_dist = 2.0 if mode == "attack" else 0.5
                        r = chase_target(goal_pt, trail, kill_rank, stop_dist=stop_dist)
                        if r in ("danger", "lowhp"):
                            continue
                        print("[战斗] 结束，继续巡逻")
                        continue

            # ===== 正常巡逻（分段走，走一段回来看怪）=====
            set_title(f"巡逻中 点{patrol_index+1}/{len(patrol_points)}")
            result = lazy_theta_pathing(goal_pt, dedicated_area, step=PATH_STEP if COMBAT_ENABLED else 0)
            if result is True:
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
                print(f"[巡逻] 点 {patrol_index+1} 反复卡住，跳过该点")
                patrol_index = (patrol_index + 1) % len(patrol_points)
            # result 为 False 说明死了或回菜单，循环回去处理
    except KeyboardInterrupt:
        print("\n[!] 用户中断")
    finally:
        defense_running = False
        if HUMANIZE and 'mouse_running' in dir():
            mouse_running = False
        if 'defense_thread' in dir() and defense_thread:
            defense_thread.join(timeout=1.0)
        try:
            import cv2
            cv2.destroyAllWindows()
        except Exception:
            pass
        reset_keyboard()
        get_window().right_button_up()
        print("[+] 右键防御已关闭")
        get_window().move_onscreen()
        print("[+] 窗口已移回屏幕")
