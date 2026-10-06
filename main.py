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
from config import load_config, save_config, ask_config, ask_update, MODE_NAMES, RANK_NAMES, HEAL_TYPE_NAMES

MAX_STUCK = 5
PATH_STEP = 40
COMBAT_ENABLED = True
TRAIL_MAX = 800
MOVE_PROGRESS_TIMEOUT = 1.5
PATH_CACHE = {"goal": None, "path": None}
SHOW_MAP_WINDOW = True

HUMANIZE = False
HUMAN_BLINK_MIN = 6
HUMAN_BLINK_MAX = 15
HUMAN_PAUSE_CHANCE = 0.2
HUMAN_REACT_MIN = 0.2
HUMAN_REACT_MAX = 0.5
HUMAN_MOUSE_MIN = 4
HUMAN_MOUSE_MAX = 12
HUMAN_RELEASE_CHANCE = 0.02


def human_ticks(w, goal):
    r = random.random()
    if r < 0.18:
        k = random.choice(['a', 'd', 'w', 's'])
        w.key_down(ord(k)); time.sleep(0.08 + random.random() * 0.07); w.key_up(ord(k))
        if random.random() < 0.3:
            time.sleep(0.03); w.key_down(ord(k)); time.sleep(0.05); w.key_up(ord(k))
    elif r < 0.30:
        time.sleep(0.2 + random.random() * 0.4)


_last_log = {}
def throttle_print(key, msg, min_gap=3.0):
    import time as _t
    now = _t.monotonic()
    if now - _last_log.get(key, -999) > min_gap:
        _last_log[key] = now
        print(msg)


def set_title(s):
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW("florr 挂机 - " + s)
    except Exception:
        pass


_freeze_watch = {"count": 0, "last": None}
def freeze_watchdog():
    while True:
        time.sleep(4)
        try:
            f = get_frame()
            gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
            mean = float(gray.mean())
            abnormal = False
            if mean < 8:
                abnormal = True
            elif _freeze_watch["last"] is not None:
                if float(cv2.absdiff(gray, _freeze_watch["last"]).mean()) < 1.0:
                    abnormal = True
            _freeze_watch["last"] = gray
            if abnormal:
                _freeze_watch["count"] += 1
            else:
                _freeze_watch["count"] = 0
            if _freeze_watch["count"] >= 3:
                try:
                    stage = check_stage()
                except Exception:
                    stage = None
                if stage in ("in_menu", "in_game_dead"):
                    _freeze_watch["count"] = 0
                    continue
                print("[画面] 窗口不可见/渲染停止，自动恢复窗口...")
                get_window().restore_visible()
                set_title("已自动恢复窗口")
                _freeze_watch["count"] = 0
                _freeze_watch["last"] = None
                time.sleep(3)
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
    w = get_window()
    from movement import get_mover
    mover = get_mover()
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
                mover.stop()
                return True
            stage = check_stage()
            if stage in ("in_game_dead", "in_menu"):
                set_keys(set())
                mover.stop()
                return stage
            if mover.effective() == 'mouse':
                mover.move_towards(pos[0], pos[1], end[0], end[1])
                time.sleep(0.05)
                continue
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
            if not desired:
                set_keys(set())
            elif current_keys and desired.issubset(current_keys):
                pass
            elif current_keys and (current_keys & desired):
                set_keys(current_keys & desired)
            else:
                set_keys(desired)
            if HUMANIZE:
                if last_blink is None or time.monotonic() - last_blink > HUMAN_BLINK_MIN + random.random() * (HUMAN_BLINK_MAX - HUMAN_BLINK_MIN):
                    last_blink = time.monotonic()
                    set_keys(set())
                    time.sleep(0.08 + random.random() * 0.17)
            time.sleep(0.05)
    finally:
        set_keys(set())
        try: mover.stop()
        except: pass


def lazy_theta_execute_path(path):
    if not path:
        return True
    for i in range(len(path) - 1):
        stage = check_stage()
        if stage != "in_game":
            return stage
        move = go_direction(path[i], path[i + 1])
        throttle_print("move-seg", f"[移动] {i+1}/{len(path)-1}: {path[i]} -> {path[i+1]} ({'OK' if move==True else move})")
        if move == "stuck":
            reset_keyboard()
            return "stuck"
        if move in ("in_game_dead", "in_menu"):
            reset_keyboard()
            return move
        reset_keyboard()
        if HUMANIZE and random.random() < HUMAN_PAUSE_CHANCE:
            time.sleep(0.3 + random.random() * 0.7)
    return True


def lazy_theta_pathing(location, area=[], step=0):
    stuck_count = 0
    while True:
        pos = get_player_position()
        if pos is None:
            time.sleep(0.3)
            continue
        binary = load_binary_map()
        goal = calibrate_player(binary, location)
        throttle_print("path-goal", f"[路径] {pos} -> {goal}")
        path = None
        if step > 0 and PATH_CACHE["goal"] == goal and PATH_CACHE["path"]:
            cached = PATH_CACHE["path"]
            nearest_index, nearest_distance = min(
                ((i, distance(pos, point)) for i, point in enumerate(cached)),
                key=lambda item: item[1],
            )
            if nearest_distance <= ARRIVE * 2:
                path = cached[nearest_index:]
                throttle_print("path-reuse", f"[路径] 复用剩余路径，偏差 {nearest_distance:.1f}px")
        if path is None:
            t0 = time.time()
            path = lazy_theta_star(binary, pos, goal)
            throttle_print("path-plan", f"[路径] 规划耗时 {time.time() - t0:.3f}s")
        if path is None:
            PATH_CACHE.update(goal=None, path=None)
            print("[路径] 无路可达，执行反卡死...")
            execute_anti_stuck()
            stuck_count += 1
            if stuck_count >= MAX_STUCK:
                return "stuck_loop"
            continue
        if step > 0:
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


def screen_to_map_safe(pt, pos):
    try:
        from combat import screen_to_map
        m = screen_to_map(pt, pos)
        return m if m is not None else None
    except Exception:
        return None


def screen_to_map_keep_r(p, pos):
    m = screen_to_map_safe(p, pos)
    if m is None:
        return None
    if len(p) >= 3:
        from combat import screen_r_to_map
        return (m[0], m[1], screen_r_to_map(p[2]))
    return m


def screen_to_map_keep_sid(p, pos):
    m = screen_to_map_safe(p, pos)
    if m is None:
        return None
    if len(p) >= 3:
        from combat import screen_r_to_map
        return (m[0], m[1], screen_r_to_map(p[2]), p[3] if len(p) >= 4 else None)
    return m


def chase_target(patrol_goal, trail, kill_rank, stop_dist=None, fixed_target=None):
    from combat import (detect_all, choose_target, ultra_blocked, screen_to_map_safe,
                        RANK_ORDER, KILL_STOP, CHASE_WARN, KISS_SLOW,
                        get_hp_ratio, HP_FLEE)
    from smart_combat import choose_target_smart, get_attack_distance
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
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            ranks_map = detect_all(frame, with_size=True, hsv=hsv)
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
            near_p = nearest_proj(detect_projectiles(frame, hsv=hsv))
            if near_p:
                print("[闪避] 打怪中闪避飞行物")
                dodge_proj(near_p)
            if fixed_target is not None:
                t = fixed_target
            elif kill_rank == "random":
                prey = [m for m in (screen_to_map_keep_r(p, pos) for r in RANK_ORDER[:-1] for p in (ranks_map.get(r) or [])) if m]
                t = random.choice(prey) if prey else None
            else:
                prey = [m for m in (screen_to_map_keep_r(p, pos) for p in (ranks_map.get(kill_rank) or [])) if m]
                t = choose_target_smart(prey, patrol_goal, pos)
            if t is None:
                print("[战斗] 目标消失，结束追击")
                return "done"
            if len(t) >= 3 and t[2]:
                from combat import BODY_CLEAR
                sid = t[3] if len(t) > 3 else None
                _extra = get_attack_distance(sid)
                _d = math.hypot(t[0] - pos[0], t[1] - pos[1]) or 1.0
                _off = float(t[2]) + BODY_CLEAR + _extra
                t = (t[0] - (t[0] - pos[0]) / _d * _off, t[1] - (t[1] - pos[1]) / _d * _off)
            dx, dy = t[0] - pos[0], t[1] - pos[1]
            dist = math.hypot(dx, dy)
            keys = set()
            if dist > stop:
                if abs(dx) > 1.5:
                    keys.add("d" if dx > 0 else "a")
                if abs(dy) > 1.5:
                    keys.add("s" if dy > 0 else "w")
            set_k(keys)
            if dist > stop:
                sid_name = t[3] if len(t)>3 else '?'
                throttle_print("move-chase", f"[移动] ->{sid_name} d={dist:.0f} keys={''.join(sorted(keys)) or '停'}", min_gap=2.0)
            time.sleep(0.04 + random.random() * 0.03)
    finally:
        set_k(set())


LEECH_RANGE = 25.0
LEECH_APPROACH = 5.0
LEECH_TIME = 4.0
PICKUP_DROPS = False
PICKUP_MIN_RANK = 3
PICKUP_ARRIVE = 4.0
PICKUP_RANGE = 60.0


def walk_to_pickup(t, trail):
    from combat import HP_FLEE, get_hp_ratio
    t0 = time.time()
    current_keys = set()
    def set_k(keys):
        nonlocal current_keys
        for k in current_keys - keys:
            keyup(k)
        for k in keys - current_keys:
            keydown(k)
        current_keys = keys
    try:
        while time.time() - t0 < 10:
            pos = get_player_position()
            if pos is None:
                set_k(set()); time.sleep(0.3); continue
            trail.append(pos)
            dx, dy = t[0] - pos[0], t[1] - pos[1]
            dist = math.hypot(dx, dy)
            if dist <= PICKUP_ARRIVE:
                set_k(set())
                time.sleep(1.5)
                return True
            keys = set()
            if abs(dx) > 1.5:
                keys.add("d" if dx > 0 else "a")
            if abs(dy) > 1.5:
                keys.add("s" if dy > 0 else "w")
            set_k(keys)
            hp = get_hp_ratio(frame)
            if hp is not None and hp < HP_FLEE:
                print("[拾取] 走位中血量过低，中断")
                return "lowhp"
            time.sleep(0.05)
        return True
    finally:
        set_k(set())


def leech_target(t, trail):
    from combat import HP_FLEE, get_hp_ratio
    w = get_window()
    t0 = time.time()
    current_keys = set()
    def set_k(keys):
        nonlocal current_keys
        for k in current_keys - keys:
            keyup(k)
        for k in keys - current_keys:
            keydown(k)
        current_keys = keys
    try:
        while time.time() - t0 < 8:
            pos = get_player_position()
            if pos is None:
                set_k(set()); time.sleep(0.3); continue
            if len(t) >= 3 and t[2]:
                from combat import LEECH_CLEAR
                _d = math.hypot(t[0] - pos[0], t[1] - pos[1]) or 1.0
                _off = float(t[2]) + LEECH_CLEAR
                t = (t[0] - (t[0] - pos[0]) / _d * _off, t[1] - (t[1] - pos[1]) / _d * _off)
            dx, dy = t[0] - pos[0], t[1] - pos[1]
            dist = math.hypot(dx, dy)
            if dist <= LEECH_APPROACH:
                break
            keys = set()
            if abs(dx) > 1.5:
                keys.add("d" if dx > 0 else "a")
            if abs(dy) > 1.5:
                keys.add("s" if dy > 0 else "w")
            set_k(keys)
            frame = get_frame()
            hp = get_hp_ratio(frame)
            if hp is not None and hp < HP_FLEE:
                print("[蹭掉落] 接近中血量过低，中断")
                return
            time.sleep(0.05)
        print(f"[蹭掉落] 到位, 站定输出 {LEECH_TIME}s 混掉落...")
        end = time.time() + LEECH_TIME
        while time.time() < end:
            frame = get_frame()
            hp = get_hp_ratio(frame)
            if hp is not None and hp < HP_FLEE:
                print("[蹭掉落] 输出中血量过低，中断")
                return
            time.sleep(0.2)
        print("[蹭掉落] 输出完成，撤退")
    finally:
        set_k(set())


def draw_overlay_window(patrol_points, pos=None):
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
    from combat import get_screen_center, PROJ_DODGE_R
    if not projs:
        return None
    cx, cy = get_screen_center()
    near = min(projs, key=lambda q: math.hypot(q[0] - cx, q[1] - cy))
    return near if math.hypot(near[0] - cx, near[1] - cy) <= PROJ_DODGE_R else None


def _slot_key(slot):
    return ord("0") if slot == 10 else ord(str(slot))


def flee_low_hp(trail, heal_slots=None):
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
        for k in keys:
            w.key_down(k); time.sleep(0.06); w.key_up(k); time.sleep(0.06)
        w.right_button_up()


def handle_danger(pos, near, ranks_map, trail, kill_rank):
    from combat import (build_avoid_map, detect_all, screen_to_map_safe,
                        RANK_ORDER, escape_direction)
    binary = load_binary_map()
    dx, dy = pos[0] - near[0], pos[1] - near[1]
    nd = math.hypot(dx, dy) or 1.0
    avoid = build_avoid_map(binary, [near], pos)
    escape = calibrate_player(avoid, (pos[0] + dx / nd * 40, pos[1] + dy / nd * 40))
    p = lazy_theta_star(avoid, pos, escape)
    if p:
        print("[危险] 尝试绕开...")
        lazy_theta_execute_path(p)
        return True
    print("[危险] 绕不开，往怪最少的方向跑")
    ex, ey = escape_direction(ranks_map, pos, binary=binary)
    goal = calibrate_player(binary, (pos[0] + ex * 50, pos[1] + ey * 50))
    p2 = lazy_theta_star(binary, pos, goal)
    if p2:
        lazy_theta_execute_path(p2)
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
    if not init_window("florr.io"):
        print("[!] 请先打开浏览器，进入 florr.io，最大化窗口后再运行(无需F11全屏)")
        exit(1)
    if "--memory" in sys.argv:
        import memory_battle
        print("[+] 内存战斗模式: 直接读游戏内存(玩家坐标/怪物HP/类型ID)")
        print("[+] 无需截图, 窗口最小化/后台都行! 但必须开着bridge_server(先跑 py bridge_server.py)")
        try:
            memory_battle.run_memory_battle(get_window())
        except KeyboardInterrupt:
            pass
        get_window().move_onscreen()
        exit(0)
    get_window().move_offscreen()
    set_title("运行中")
    print("[+] 脚本运行中... 按 Ctrl+C 停止（停止后窗口自动移回）")
    threading.Thread(target=freeze_watchdog, daemon=True).start()
    print("[+] 画面冻结监测已开启（窗口被最小化/遮挡会自动恢复）")
    from utils import start_capture_thread
    start_capture_thread()
    print("[+] 异步抓帧线程已启动（截图不阻塞主循环）")
    cfg = load_config()
    if cfg is None or ask_update(cfg):
        cfg = ask_config(map_name)
        save_config(cfg)
    mode, kill_rank = cfg["mode"], cfg["kill_rank"]
    from movement import get_mover
    get_mover().set_mode(cfg.get("move_mode", "auto"))
    if get_mover().mode != 'auto':
        print(f"[移动] 移动方式: {get_mover().mode} (auto=前台鼠标/后台键盘)")
    else:
        print("[移动] 移动方式: 自动(前台鼠标控制方向, 后台/最小化自动切键盘)")
    if map_name == 'ocean':
        get_mover().water_factor = 0.55
        print("[海洋] 移动速度×0.55(官方海水减速 kWaterSpeedScale=0.55, 鼠标模式生效)")
    EFFICIENT = cfg.get("efficiency", False)
    if EFFICIENT:
        print("[效率] 效率模式已开启：少停顿少延迟，刷怪更快")
    LEECH = cfg.get("leech", False) and mode != "none"
    if LEECH:
        print("[蹭掉落] 已开启：打不动的M/U怪在附近时打2.5s混掉落")
    import combat
    heal_type = cfg.get("heal_type", "rose")
    _trigger = combat.HEAL_TRIGGER.get(heal_type, 0.20)
    combat.HP_FLEE = _trigger
    combat.HP_RECOVER = min(0.70, _trigger + 0.15)
    print(f"[回血] 回血花瓣: {HEAL_TYPE_NAMES.get(heal_type, heal_type)} → 低血触发 {_trigger*100:.0f}%, 恢复 {combat.HP_RECOVER*100:.0f}%")
    print("[配置] 模式=" + MODE_NAMES.get(mode, mode) + ", 打怪=" + RANK_NAMES.get(kill_rank, kill_rank))
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
        print("[天赋] 挂机加点推荐(每级1TP, 2024-06起洗点免费):")
        print("         1. Loadout 槽位点满10槽  (共45TP)")
        print("         2. Reload 到 Mythic     (reload6, -58%冷却, 共66TP, 提升最大)")
        print("         3. Health 到 Epic       (health4, 血x2.86)")
        print("         4. Medic 到 Legendary   (medic5, 回血x2.01)")
        print("         5. Magnetism            (+1000拾取, 省磁铁槽, 需先点满Loadout)")
        print("         6. 剩余点 Luck          (2025-10起影响刷怪稀有度)")
        from map_select import select_patrol_points
        from config import region_patrol_points, region_options, map_roster, map_roster_cn, ROSTER_DANGER_HINT
        _roster_cn = map_roster_cn(map_name)
        print(f"[刷怪表] {map_name} 官方刷怪: {_roster_cn}")
        _dangers = ROSTER_DANGER_HINT.get(map_name)
        if _dangers:
            print(f"[刷怪表] ⚠ 本图威胁: {'; '.join(_dangers)}（插件会自动避开）")
        try:
            from mob_db import rarity_spread
            if rarity_spread():
                print("[刷怪表] 自然稀有度: 普通40% 罕见30% 稀有15% 史诗10% 传奇4% 神话M1% (Super=Ultra的1%替换, 官方)")
        except Exception:
            pass
        region_box = None
        region_key = cfg.get("region", "") if cfg.get("region_map") == map_name else ""
        if region_key in [k for k, _ in region_options(map_name)]:
            region_label, patrol_points, region_box = region_patrol_points(map_name, region_key, kill_rank)
            print(f"[区域] {region_label} 中心{region_box[:2]} 半径{region_box[2]} -> 区域内随机游走（坐标为估算，实测不对可截图校准）")
        elif cfg.get("patrol_points") and cfg.get("patrol_points_map") == map_name:
            from config import _ask
            reuse = _ask("上次的巡逻点还在（这张地图），直接用吗？\n（新：想用刷怪区域就选“重新设置”）", [("y", "用上次的"), ("n", "重新设置")], "巡逻点")
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
        from combat import calibrate_screen
        try:
            calibrate_screen()
        except Exception as e:
            print(f"[!] 屏幕标定失败(使用默认1080p): {e}")
        from utils import detect_canvas_offset
        try:
            detect_canvas_offset()
        except Exception as e:
            print(f"[!] 画布偏移检测失败: {e}")
        try:
            from map_auto_detect import detect_map, get_map_label
            _m = detect_map(get_frame())
            if _m:
                if _m['map'] != map_name:
                    print(f"[地图识别] 当前地图疑似「{get_map_label(_m['map'])}」(conf={_m['confidence']:.2f})，与参数 {map_name} 不一致！")
                    print(f"[地图识别] 若进错图请 Ctrl+C 后用: py -3.12 main.py {_m['map']}")
                else:
                    print(f"[地图识别] 地图确认「{get_map_label(_m['map'])}」 conf={_m['confidence']:.2f} ✓")
            else:
                print("[地图识别] 未能识别(小地图被遮挡?), 按参数继续")
        except Exception as _me:
            print(f"[地图识别] 跳过: {_me}")
        if COMBAT_ENABLED:
            print("[+] 战斗策略: =秒杀等级自动追(贴0.5px), 更高避开(往怪少处跑), 更低不管")
        print("[!] 提醒: 请把回血花瓣(玫瑰/叶子)放在副槽(配置时勾选的槽位)——血量<10%%时插件自动切到主槽+防御跑路, 恢复后自动切回")
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
        try:
            from combat import scan_petal_ranks, rank_recommend
            from config import RANK_NAMES as _RN
            _cnt, _slots = scan_petal_ranks()
            if any(_cnt.values()):
                _desc = "  ".join(f"{_RN.get(r, r)}{n}" for r, n in _cnt.items() if n)
                print(f"[配置] 花瓣扫描: {_desc}")
                _rec = rank_recommend(_cnt)
                if _rec:
                    _main, _low = _rec
                    print(f"[配置] 主力={_RN.get(_main, _main)}级 → 推荐打 {_RN.get(_main, _main)}（必秒必拿掉落）")
                    print(f"[配置] 若打不动可降到 {_RN.get(_low, _low)}；别打高一档（血量x3.6~46, 经验只多x4~9, 秒不了不划算）")
            else:
                print("[配置] 未扫到花瓣（窗口需在游戏中且可见）")
        except Exception as e:
            print(f"[配置] 花瓣扫描失败: {e}")
        dedicated_area = []
        patrol_index = 0
        trail = deque(maxlen=TRAIL_MAX)
        _last_special = 0.0
        _last_drops = 0.0
        _HP_ETA = []
        _afk_hits = 0
        _afk_last_mean = None
        last_map_win = 0
        _boss_pause_until = 0.0
        print(f"[巡逻模式] 共 {len(patrol_points)} 个巡逻点，循环移动中...")
        try:
            from chat_solver import ChatSolver
            _chat = ChatSolver(get_window(), get_frame)
            _chat.start()
        except Exception as e:
            print(f"[聊天] 监控启动失败(忽略): {e}")
        from combat import detect_mobs, screen_to_map, ultra_blocked, choose_target
        while True:
            if time.time() - _STATS["report"] > 300:
                _STATS["report"] = time.time()
                print(f"[统计] 已运行 {int((time.time() - _STATS['t0']) / 60)} 分钟 | 战斗 {_STATS['fights']} 次 | 拾取掉落 {_STATS['pickups']} 次")
            target = None
            ranks_map = {}
            from combat import detect_afk_check
            _cdf = get_frame()
            _cdark, _cstatic, _cmean = detect_afk_check(_cdf, _afk_last_mean)
            _afk_last_mean = _cmean
            if _cdark and _cstatic:
                _afk_hits += 1
            else:
                _afk_hits = 0
            if _afk_hits >= 4:
                from afk_solver import try_solve_and_drag
                _solved = try_solve_and_drag(get_window(), _cdf)
                if not _solved:
                    from combat import solve_afk_drag
                    ok, sx, sy, path_pts = solve_afk_drag(_cdf)
                    if ok:
                        ex, ey = path_pts[-1]
                        print(f"[AFK] 拖动验证(v1): 绿点({sx},{sy})->终点({ex},{ey})")
                        import win32api, win32con
                        def _lp(x, y): return (y << 16) | (x & 0xFFFF)
                        win32api.PostMessage(get_window().hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, _lp(sx, sy))
                        time.sleep(0.2)
                        for i, (ix, iy) in enumerate(path_pts):
                            win32api.PostMessage(get_window().hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, _lp(ix, iy))
                            time.sleep(0.06)
                        time.sleep(0.2)
                        win32api.PostMessage(get_window().hwnd, win32con.WM_LBUTTONUP, 0, _lp(ex, ey))
                        time.sleep(1.5)
                    else:
                        print(f"[AFK] 检测到 AFK Check 弹窗(中心灰度{_cmean:.0f})，点击 Yes 按钮...")
                        from utils import get_screen_center
                        _ccx, _ccy = get_screen_center()
                        get_window().left_click(_ccx, _ccy + 60)
                        time.sleep(2)
                _afk_hits = 0
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
                w.key_down(0x0D); time.sleep(0.1); w.key_up(0x0D)
                time.sleep(1.5)
                w.key_down(0x0D); time.sleep(0.1); w.key_up(0x0D)
                time.sleep(5)
                continue
            pos = get_player_position()
            if pos is not None:
                trail.append(pos)
            frame = get_frame()
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            if region_box is not None:
                _ang = random.random() * 2 * math.pi
                _rr = region_box[2] * math.sqrt(random.random())
                goal_pt = (int(region_box[0] + _rr * math.cos(_ang)),
                           int(region_box[1] + _rr * math.sin(_ang)))
                goal_pt = (min(297, max(2, goal_pt[0])), min(297, max(2, goal_pt[1])))
            else:
                goal_pt = patrol_points[patrol_index]
            if HUMANIZE and pos is not None and random.random() < (0.15 if EFFICIENT else 0.35):
                human_ticks(get_window(), goal_pt)
            if SHOW_MAP_WINDOW and time.time() - last_map_win > 0.3:
                draw_overlay_window(patrol_points, pos)
                last_map_win = time.time()
            try:
                from combat import detect_bossbar, detect_all, screen_to_map_safe, choose_target
                if detect_bossbar(get_frame()):
                    if LEECH:
                        if _boss_pause_until < time.time():
                            print("[Boss] Super+级Boss在场！蹭1%掉落(leech模式, 2.5s就走)...")
                        _pb = pos or get_player_position()
                        if _pb is not None:
                            _rm = detect_all(frame, hsv=hsv)
                            _sup = [m for m in (screen_to_map_safe(p, _pb) for p in (_rm.get("ultra") or []))
                                    if m and math.hypot(m[0] - _pb[0], m[1] - _pb[1]) <= LEECH_RANGE]
                            _t = choose_target(_sup, goal_pt, _pb) if _sup else None
                            if _t is not None:
                                set_title("抢Boss蹭掉落")
                                leech_target(_t, trail)
                                _boss_pause_until = time.time() + 8
                                continue
                        _boss_pause_until = time.time() + 5
                        continue
                    if _boss_pause_until < time.time():
                        print("[Boss] 检测到Super+级Boss血条！75级前别蹲Super——暂停追怪10s，先回避")
                    _boss_pause_until = time.time() + 10
            except Exception:
                pass
            from combat import get_hp_ratio, HP_FLEE
            hp = get_hp_ratio(get_frame())
            _eta_now = time.time()
            _HP_ETA.append((_eta_now, hp))
            _HP_ETA[:] = [(t, h) for t, h in _HP_ETA if _eta_now - t < 3.0]
            if hp is not None and hp < HP_FLEE:
                set_title(f"低血逃跑! {hp*100:.0f}%")
                print(f"[低血] 血量 {hp*100:.0f}%，跑路...")
                r = flee_low_hp(trail, heal_slots=cfg.get("heal_slots", []))
                if r in ("in_game_dead", "in_menu"):
                    continue
                continue
            if hp is not None and len(_HP_ETA) >= 2:
                _t0, _h0 = _HP_ETA[0]
                _dt = _eta_now - _t0
                if hp < 0.35 and _h0 - hp >= 0.25 and _dt >= 0.5:
                    _drop = (_h0 - hp) / max(_dt, 0.001)
                    print(f"[低血ETA] 血速{-_drop*100:.0f}%/s 当前{hp*100:.0f}%, 提前跑路(海绵机制)")
                    r = flee_low_hp(trail, heal_slots=cfg.get("heal_slots", []))
                    if r in ("in_game_dead", "in_menu"):
                        continue
                    continue
            if time.time() < _boss_pause_until:
                pass
            elif COMBAT_ENABLED and kill_rank != "none":
                pos = get_player_position(image=frame)
                if pos is not None:
                    from combat import (detect_all, ultra_blocked, choose_target,
                                        screen_to_map_safe, RANK_ORDER, WARN_MARGIN)
                    ranks_map = detect_all(frame, with_size=True, with_sid=True, hsv=hsv)
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
                    from combat import detect_super
                    sup = detect_super(frame, with_size=True, hsv=hsv)
                    if sup:
                        sup_m = [m for m in (screen_to_map_keep_r(p, pos) for p in sup) if m]
                        near_s = ultra_blocked(sup_m, pos, margin=WARN_MARGIN)
                        if near_s:
                            if LEECH:
                                _st = choose_target(sup_m, goal_pt, pos)
                                if _st is not None and math.hypot(_st[0] - pos[0], _st[1] - pos[1]) <= LEECH_RANGE:
                                    set_title("蹭Super")
                                    leech_target(_st, trail)
                                    continue
                            print("[Super] 薄荷绿Super级怪在场，避开(75级前杀Super只掉究极档)")
                            r = handle_danger(pos, near_s, ranks_map, trail, kill_rank)
                            if r in ("in_game_dead", "in_menu"):
                                continue
                            continue
                    from combat import detect_projectiles
                    near_p = nearest_proj(detect_projectiles(frame, hsv=hsv))
                    if near_p:
                        print("[闪避] 飞行物来袭，横向闪避")
                        dodge_proj(near_p)
                        continue
                    from combat import detect_special, SPECIAL_PRIORITY_ORDER, SPECIAL_DEVIATION
                    if time.time() - _last_special > 0.4:
                        sp_map = detect_special(frame, map_name, with_size=True, hsv=hsv)
                        _last_special = time.time()
                    else:
                        sp_map = {}
                    sp_target, sp_name = None, None
                    if sp_map:
                        for sname in SPECIAL_PRIORITY_ORDER:
                            cand = [m for m in (screen_to_map_keep_r(p, pos) for p in (sp_map.get(sname) or [])) if m]
                            t = choose_target(cand, goal_pt, pos, dev_limit=SPECIAL_DEVIATION)
                            if t is not None:
                                sp_target, sp_name = t, sname
                                break
                    if sp_target is not None:
                        set_title("战斗中(稀有)")
                        if sp_name == "golden_leafbug":
                            print("[稀有] ⚠️ 金叶虫: 请确保未装备魔法球再打(否则不掉黄金之叶)!")
                        print(f"[稀有] 优先打 {sp_name} {sp_target}...")
                        stop_dist = 2.0 if mode == "attack" else 0.5
                        r = chase_target(goal_pt, trail, kill_rank, stop_dist=stop_dist, fixed_target=sp_target)
                        if r in ("danger", "lowhp"):
                            continue
                        print(f"[稀有] {sp_name} 结束，继续巡逻")
                        continue
                    if LEECH:
                        far = []
                        for r in RANK_ORDER[idx + 1:]:
                            far += [m for m in (screen_to_map_keep_r(p, pos) for p in (ranks_map.get(r) or [])) if m]
                        leech_t = choose_target(far, goal_pt, pos)
                        if leech_t is not None:
                            d = math.hypot(leech_t[0] - pos[0], leech_t[1] - pos[1])
                            if d <= LEECH_RANGE:
                                set_title("蹭掉落")
                                leech_target(leech_t, trail)
                                continue
                    if kill_rank == "random":
                        prey_all = [m for m in (screen_to_map_keep_sid(p, pos) for r in RANK_ORDER[:-1] for p in (ranks_map.get(r) or [])) if m]
                        target = random.choice(prey_all) if prey_all else None
                    else:
                        prey = [m for m in (screen_to_map_keep_sid(p, pos) for p in (ranks_map.get(kill_rank) or [])) if m]
                        target = choose_target(prey, goal_pt, pos)
                    if target is not None:
                        if HUMANIZE:
                            if EFFICIENT:
                                time.sleep(0.05 + random.random() * 0.1)
                            else:
                                time.sleep(HUMAN_REACT_MIN + random.random() * (HUMAN_REACT_MAX - HUMAN_REACT_MIN))
                        set_title("战斗中")
                        from combat import mob_name, drop_hint, mob_hp, threat_hint
                        _tname = mob_name(target[3]) if len(target) >= 4 and target[3] else "未知"
                        _drop = drop_hint(target[3], rarity=5) if len(target) >= 4 and target[3] else ""
                        _kidx = RANK_ORDER.index(kill_rank) if kill_rank in RANK_ORDER else 5
                        _hp = mob_hp(target[3], _kidx) if len(target) >= 4 and target[3] else None
                        _thr = threat_hint(target[3], RANK_ORDER.index(kill_rank)) if len(target) >= 4 and target[3] else ""
                        print(f"[战斗] 发现目标 {_tname}({kill_rank}) HP {_hp or '?'} {target}，追击..." +
                              (f"  | {_thr}" if _thr else "") +
                              (f"  | M档掉落: {_drop}" if _drop else ""))
                        _t0 = time.time()
                        stop_dist = 2.0 if mode == "attack" else 0.5
                        r = chase_target(goal_pt, trail, kill_rank, stop_dist=stop_dist)
                        if r in ("danger", "lowhp"):
                            continue
                        _el = time.time() - _t0
                        _warn = ""
                        if _el > 10:
                            _warn = f"  ⚠️ 击杀耗时{_el:.0f}s>10s, 打得慢! 建议降档打更低的怪(目标HP {_hp or '?'})"
                        print(f"[战斗] 结束(耗时{_el:.0f}s)，继续巡逻{_warn}")
                        _STATS["fights"] += 1
                        continue
            if SWARM_WARN and target is None:
                total_mobs = sum(len(v) for v in ranks_map.values())
                if total_mobs > SWARM_COUNT:
                    swarm_c = [m for m in (screen_to_map_safe(p, pos) for v in ranks_map.values() for p in v) if m]
                    if swarm_c:
                        avgx = sum(m[0] for m in swarm_c) / len(swarm_c)
                        avgy = sum(m[1] for m in swarm_c) / len(swarm_c)
                        if math.hypot(avgx - pos[0], avgy - pos[1]) < SWARM_RADIUS:
                            dx, dy = pos[0] - avgx, pos[1] - avgy
                            keys = set()
                            if abs(dx) > 1.5:
                                keys.add("d" if dx > 0 else "a")
                            if abs(dy) > 1.5:
                                keys.add("s" if dy > 0 else "w")
                            print(f"[怪潮] 屏幕 {total_mobs} 只怪围住，往怪少处走...")
                            set_title("怪潮躲避")
                            for k in keys:
                                keydown(k)
                            time.sleep(1.2)
                            for k in keys:
                                keyup(k)
                            continue
            if PICKUP_DROPS:
                frame = get_frame()
                pos = get_player_position(image=frame)
                if pos is not None:
                    from combat import detect_drops
                    if time.time() - _last_drops > 0.3:
                        _drops_px = detect_drops(frame, hsv=hsv, with_rank=True)
                        _last_drops = time.time()
                    drops = [m for m in (screen_to_map_safe(p, pos) for p in _drops_px
                                         if p[2] and RANK_W.get(p[2], 0) >= PICKUP_MIN_RANK) if m]
                    drops = [d for d in drops if math.hypot(d[0] - pos[0], d[1] - pos[1]) <= PICKUP_RANGE]
                    dtarget = choose_target(drops, goal_pt, pos) if drops else None
                    if dtarget is not None:
                        set_title("捡掉落")
                        print(f"[拾取] 发现掉落 {dtarget}，走过去捡...")
                        r = walk_to_pickup(dtarget, trail)
                        if r in ("in_game_dead", "in_menu"):
                            continue
                        print("[拾取] 结束，继续巡逻")
                        continue
            set_title(f"巡逻中 点{patrol_index+1}/{len(patrol_points)}")
            result = lazy_theta_pathing(goal_pt, dedicated_area, step=PATH_STEP if COMBAT_ENABLED else 0)
            if result is True:
                if region_box is not None:
                    print("[区域] 到达随机点，区域内继续游走")
                else:
                    print(f"[巡逻] 到达点 {patrol_index+1}，前往下一个点")
                    patrol_index = random.choice([i for i in range(len(patrol_points)) if i != patrol_index])
                PATH_CACHE.update(goal=None, path=None)
                pause = (0.15 + random.random() * 0.4) if EFFICIENT else (0.5 + random.random() * 2.0)
                print(f"[防挂机] 随机停顿 {pause:.1f}s")
                time.sleep(pause)
            elif result == "step_done":
                continue
            elif result == "stuck_loop":
                if region_box is not None:
                    print("[区域] 目标点反复卡住，换个随机点再走")
                else:
                    print(f"[巡逻] 点 {patrol_index+1} 反复卡住，绕路失败换点")
                    patrol_index = random.choice([i for i in range(len(patrol_points)) if i != patrol_index])
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
