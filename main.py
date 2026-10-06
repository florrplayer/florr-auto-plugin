import os
import sys
import time
import math
import random
import heapq
import win32con
from collections import deque
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")   # v1.32: 防GBK控制台打印 \u200b 等字符崩溃
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(errors="replace")
from utils import *
from window_ctrl import init_window, get_window
from config import load_config, save_config, ask_config, ask_update, MODE_NAMES, RANK_NAMES, HEAL_TYPE_NAMES

MAX_STUCK = 5   # 连续卡死/无路次数上限，超过则跳过当前巡逻点
PATH_STEP = 40  # 巡逻分段长度(地图像素)：每走完一段回主循环检查战斗
COMBAT_ENABLED = True  # 战斗模式总开关
TRAIL_MAX = 800        # 撤退轨迹缓存长度
MOVE_PROGRESS_TIMEOUT = 1.5  # 持续无有效进展多久才判定卡住
PATH_CACHE = {"goal": None, "path": None}
SHOW_MAP_WINDOW = True                  # 实时地图窗口: 红=路径 绿=玩家 蓝=巡逻点 黄=目标

# ===== 人性化模拟（让脚本玩得像真人）=====
# v1.20.1: 用户决定关闭——防挂机已有其他手段(AFK破解/聊天回复/随机巡逻), 延迟影响战斗效率
HUMANIZE = False           # 总开关(False=所有微转向/停顿/反应延迟/鼠标微动/手抖全停, 战斗即时响应)
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


# ===== 画面冻结监测: 窗口被最小化/遮挡导致画面全黑或静止时, 自动恢复窗口强制渲染 =====
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
                abnormal = True                       # 全黑: 窗口不可见(最小化/移出屏幕)
            elif _freeze_watch["last"] is not None:
                if float(cv2.absdiff(gray, _freeze_watch["last"]).mean()) < 1.0:
                    abnormal = True                   # 画面完全静止: 渲染被暂停(Edge后台节流)
            _freeze_watch["last"] = gray
            if abnormal:
                _freeze_watch["count"] += 1
            else:
                _freeze_watch["count"] = 0
            if _freeze_watch["count"] >= 3:           # 连续约12秒异常
                try:
                    stage = check_stage()
                except Exception:
                    stage = None
                if stage in ("in_menu", "in_game_dead"):
                    _freeze_watch["count"] = 0        # 菜单/死亡本来就静止, 不误判
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
    """朝 end 移动；带迟滞平滑走路，降低抖动和来回切键。
    v1.18.1: 支持鼠标模式(角色朝鼠标走, 原作者方式) / 键盘模式(后台WASD) / 自动"""
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

            # ===== 鼠标模式(v1.18.1): 角色朝鼠标位置走, 不需要键盘 =====
            if mover.effective() == 'mouse':
                mover.move_towards(pos[0], pos[1], end[0], end[1])
                time.sleep(0.05)
                continue

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

def screen_to_map(pt, pos):
    try:
        from combat import screen_to_map
        m = screen_to_map(pt, pos)
        return m if m is not None else None
    except Exception:
        return None


def screen_to_map_keep_r(p, pos):
    """屏幕点->地图点, 若带半径则一并换算成地图单位半径(碰撞箱); 返回 (x,y) 或 (x,y,r)"""
    m = screen_to_map(p, pos)
    if m is None:
        return None
    if len(p) >= 3:
        from combat import screen_r_to_map
        return (m[0], m[1], screen_r_to_map(p[2]))
    return m


def screen_to_map_keep_sid(p, pos):
    """屏幕点->地图点, 保留半径(地图单位)与怪种 sid(v1.5.0 怪种识别);
    返回 (x, y, r, sid) 或 None"""
    m = screen_to_map(p, pos)
    if m is None:
        return None
    if len(p) >= 3:
        from combat import screen_r_to_map
        return (m[0], m[1], screen_r_to_map(p[2]), p[3] if len(p) >= 4 else None)
    return m


def chase_target(patrol_goal, trail, kill_rank, stop_dist=None, fixed_target=None):
    """追击 =秒杀等级的怪; 攻击模式停 2px, 防御模式贴 0.5px; >秒杀贴近返回 'danger'; 低血返回 'lowhp'"""
    from combat import (detect_all, choose_target, ultra_blocked, screen_to_map,
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
                danger += [m for m in (screen_to_map(p, pos) for p in (ranks_map.get(r) or [])) if m]
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
                # 固定目标模式(特殊稀有生物): 不按颜色重新选, 一路追到它消失/超时
                t = fixed_target
            elif kill_rank == "random":
                # 随机打怪: 追击中每次随机挑一只非U怪(目标消失就换一只)
                prey = [m for m in (screen_to_map_keep_r(p, pos) for r in RANK_ORDER[:-1] for p in (ranks_map.get(r) or [])) if m]
                t = random.choice(prey) if prey else None
            else:
                prey = [m for m in (screen_to_map_keep_r(p, pos) for p in (ranks_map.get(kill_rank) or [])) if m]
                t = choose_target_smart(prey, patrol_goal, pos)
            if t is None:
                print("[战斗] 目标消失，结束追击")
                return "done"
            # 碰撞箱: 目标点外移到 怪半径+怪种专属距离 外
            if len(t) >= 3 and t[2]:
                from combat import BODY_CLEAR
                sid = t[3] if len(t) > 3 else None
                _extra = get_attack_distance(sid)  # v1.10: 怪种专属距离
                _d = math.hypot(t[0] - pos[0], t[1] - pos[1]) or 1.0
                _off = float(t[2]) + BODY_CLEAR + _extra
                t = (t[0] - (t[0] - pos[0]) / _d * _off, t[1] - (t[1] - pos[1]) / _d * _off)
            dx, dy = t[0] - pos[0], t[1] - pos[1]
            dist = math.hypot(dx, dy)
            keys = set()
            if dist > stop:
                if dist <= KISS_SLOW:
                    # v1.6.0 不要犹豫: 贴脸直接连续走(停在怪碰撞箱外, 不会撞上)
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
            # v1.10.2: 每步打印+人类化随机延迟
            if dist > stop:
                sid_name = t[3] if len(t)>3 else '?'
                print(f"[移动] ->{sid_name} d={dist:.0f} keys={''.join(sorted(keys)) or '停'}")
            time.sleep(0.04 + random.random() * 0.03)  # 40-70ms随机,像人
    finally:
        set_k(set())


LEECH_RANGE = 25.0      # 蹭掉落触发范围(地图像素): 高等级怪距玩家10-25px时
LEECH_APPROACH = 5.0    # 蹭掉落贴近距离: 走到5px内站定输出
LEECH_TIME = 4.0        # v1.24.3: 站定输出秒数 - 官方最新机制需伤害≥5%+屏幕距离内才能分掉落(changelog), 2.5s不足, 提到4s
PICKUP_DROPS = False   # 掉落自动拾取(顺路捡: 只捡距玩家<=PICKUP_RANGE的掉落); 装了磁铁花瓣建议关(磁铁自动吸附近掉落, 跑过去捡反而浪费时间)
PICKUP_MIN_RANK = 3      # v1.7.0 掉落价值筛选: 只捡稀有度权重>=此值的掉落(3=Epic, 垃圾掉落不浪费时间)
PICKUP_ARRIVE = 4.0     # 走到多近算"碰到"(玩家本体碰撞即拾取)
PICKUP_RANGE = 60.0     # v1.23.8: 掉落物在死点±50随机散布(loot.cpp), 30太小会漏捡, 提到60全覆盖


def walk_to_pickup(t, trail):
    """直线走向掉落(本体碰撞即拾取), 最多走10s; 低血中断; 到达停1.5s等拾取动画"""
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
    """朝高等级怪走到5px内, 站定输出LEECH_TIME秒(攻击/防御线程自动输出≥5%伤害混掉落), 期间低血/危险中断
    v1.24.3: 官方机制需≥5%伤害+屏幕距离内才分掉落(changelog), 站定时间已提到4s"""
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
        # 接近阶段(最多8秒)
        while time.time() - t0 < 8:
            pos = get_player_position()
            if pos is None:
                set_k(set()); time.sleep(0.3); continue
            # 碰撞箱: 站定点外移到 怪半径+安全距 外(高稀有度大怪不撞身体)
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
        # 站定输出阶段
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


_MAPWIN = {"disp": None, "th": None}   # v1.32: 地图窗口独立线程, 防主循环阻塞导致"未响应"
_MAPWIN_TITLE = "florr auto map (red=path green=player blue=patrol)"

def _mapwin_thread():
    import cv2
    try:
        cv2.namedWindow(_MAPWIN_TITLE, cv2.WINDOW_NORMAL)
    except Exception:
        pass
    while True:
        try:
            disp = _MAPWIN.get("disp")
            if disp is not None:
                cv2.imshow(_MAPWIN_TITLE, disp)
                _MAPWIN["disp"] = None
            k = cv2.waitKey(30)
            if k in (27, ord('q')):   # Esc/Q 关闭地图窗口
                break
        except Exception:
            try:
                cv2.waitKey(30)
            except Exception:
                pass
    try:
        cv2.destroyWindow(_MAPWIN_TITLE)
    except Exception:
        pass

def _ensure_mapwin():
    if _MAPWIN["th"] is None or not _MAPWIN["th"].is_alive():
        import threading
        _MAPWIN["th"] = threading.Thread(target=_mapwin_thread, daemon=True)
        _MAPWIN["th"].start()

def draw_overlay_window(patrol_points, pos=None):
    """实时地图窗口: 红=寻路路径 绿=玩家 蓝=巡逻点 黄=当前目标(每0.3s刷新)
    v1.32: 只渲染帧交给独立线程, 主循环不再碰 imshow/waitKey(防窗口未响应)"""
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
        _MAPWIN["disp"] = big
        _ensure_mapwin()
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
    from combat import (build_avoid_map, detect_all, screen_to_map,
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
            danger_now += [m for m in (screen_to_map(p, pos) for p in (rmap.get(r) or [])) if m]
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

    # ===== 内存战斗模式（v1.35 默认自动开启）=====
    # 直读游戏内存(玩家坐标/怪HP/类型ID): 免截图、最快最准、窗口最小化/后台都能跑
    # 自动: 探测 bridge(18899) -> 没起就自动拉起 bridge_server.py -> 有数据进内存模式
    #       连不上/无数据(浏览器没注入hook) -> 打印提示后回退截图模式, 小白零配置
    # 参数: --screenshot 强制截图模式; --memory 强制内存模式(连不上也回退)
    force_screenshot = "--screenshot" in sys.argv
    if not force_screenshot:
        import urllib.request, json
        def _bridge_has_data(timeout):
            t0 = time.time()
            while time.time() - t0 < timeout:
                try:
                    with urllib.request.urlopen("http://127.0.0.1:18899", timeout=0.8) as r:
                        d = json.loads(r.read().decode())
                        if d.get("px") and d.get("py"):
                            return True
                except Exception:
                    pass
                time.sleep(0.4)
            return False
        if not _bridge_has_data(1.5):
            import subprocess
            base = os.path.dirname(os.path.abspath(__file__))
            # v1.35: 优先同目录 bridge_server.exe (小白版免Python), 否则 bridge_server.py
            bpy = os.path.join(base, "bridge_server.exe")
            if not os.path.exists(bpy):
                bpy = os.path.join(base, "bridge_server.py")
            if os.path.exists(bpy):
                try:
                    cmd = [bpy] if bpy.endswith(".exe") else [sys.executable, bpy]
                    subprocess.Popen(cmd, creationflags=0x08000000)  # CREATE_NO_WINDOW
                    print("[内存] 自动启动 bridge_server(127.0.0.1:18899)...")
                except Exception:
                    pass
        if _bridge_has_data(8.0 if "--memory" in sys.argv else 6.0):
            import memory_battle
            print("[+] 内存战斗模式: 直读游戏内存(玩家坐标/怪HP/类型ID), 免截图, 最小化/后台也能跑")
            try:
                b = memory_battle.run_memory_battle(get_window(), no_data_timeout=12.0)
                if not getattr(b, "had_data", True):
                    print("[!] 内存模式12s无数据(浏览器未注入hook?), 回退截图模式")
                else:
                    get_window().move_onscreen()
                    exit(0)
            except KeyboardInterrupt:
                get_window().move_onscreen()
                exit(0)
        print("[内存] 未连上 bridge(需浏览器注入), 使用截图模式")

    get_window().move_offscreen()
    set_title("运行中")
    print("[+] 脚本运行中... 按 Ctrl+C 停止（停止后窗口自动移回）")

    # 画面冻结监测: 最小化/遮挡时自动恢复窗口(Edge最小化会暂停渲染, 截图会失明)
    threading.Thread(target=freeze_watchdog, daemon=True).start()
    print("[+] 画面冻结监测已开启（窗口被最小化/遮挡会自动恢复）")
    # v1.18.3: 异步抓帧线程(ImageGrab固定~100ms/次, 主循环不再被截图阻塞, 决策帧率~10fps -> 不阻塞)
    from utils import start_capture_thread
    start_capture_thread()
    print("[+] 异步抓帧线程已启动（截图不阻塞主循环）")

    # ===== 后台防御线程：一直按住右键 =====
    # ===== 交互配置(弹窗让玩家选, 存档后只问要不要更新) =====
    cfg = load_config()
    if cfg is None or ask_update(cfg):
        cfg = ask_config(map_name)
        save_config(cfg)
    mode, kill_rank = cfg["mode"], cfg["kill_rank"]
    # 移动方式 (v1.18.1): 鼠标/键盘/自动 -> movement 模块
    from movement import get_mover
    get_mover().set_mode(cfg.get("move_mode", "keyboard"))   # v1.33: 默认键盘(后台PostMessage不碰真实鼠标)
    if get_mover().mode != 'keyboard':
        print(f"[移动] 移动方式: {get_mover().mode} (默认keyboard=后台键盘不碰鼠标)")
    else:
        print("[移动] 移动方式: 键盘(后台PostMessage, 跨桌面有效, 不碰真实鼠标)")
    EFFICIENT = cfg.get("efficiency", False)
    if EFFICIENT:
        print("[效率] 效率模式已开启：少停顿少延迟，刷怪更快")
    LEECH = cfg.get("leech", False) and mode != "none"
    if LEECH:
        print("[蹭掉落] 已开启：打不动的M/U怪在附近时打2.5s混掉落")
    # 回血花瓣种类 -> 低血触发线(研究落地): 玫瑰20%爆发救急/大丽花30%/丝兰20%防御回/海星40%提前切
    import combat
    heal_type = cfg.get("heal_type", "rose")
    _trigger = combat.HEAL_TRIGGER.get(heal_type, 0.20)
    combat.HP_FLEE = _trigger
    combat.HP_RECOVER = min(0.70, _trigger + 0.15)
    print(f"[回血] 回血花瓣: {HEAL_TYPE_NAMES.get(heal_type, heal_type)} → 低血触发 {_trigger*100:.0f}%, 恢复 {combat.HP_RECOVER*100:.0f}%")
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
        # v1.7.2 天赋推荐(官方 cost 数据, 洗点免费随便试)
        print("[天赋] 挂机加点推荐(每级1TP, 2024-06起洗点免费):")
        print("         1. Loadout 槽位点满10槽  (共45TP)")
        print("         2. Reload 到 Mythic     (reload6, -58%冷却, 共66TP, 提升最大)")
        print("         3. Health 到 Epic       (health4, 血x2.86)")
        print("         4. Medic 到 Legendary   (medic5, 回血x2.01)")
        print("         5. Magnetism            (+1000拾取, 省磁铁槽, 需先点满Loadout)")
        print("         6. 剩余点 Luck          (2025-10起影响刷怪稀有度)")
        from map_select import select_patrol_points
        from config import region_patrol_points, region_options
        # 新: 区域系统(按秒杀等级推荐/手动选区域) -> 区域内随机游走, 不用点选
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
        # v1.25.0 地图自动识别(移植 florr_assistant 模板匹配): 防进错图跑错巡逻点/掉落表
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

        # 扫描花瓣稀有度 -> 推荐可秒等级(按稀有度估算, 未考虑花瓣种类/怪种, 供参考)
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

        dedicated_area = []   # 可选：[[左上], [右下]]，进入该区域即算到达
        patrol_index = 0
        trail = deque(maxlen=TRAIL_MAX)
        _last_special = 0.0
        _last_drops = 0.0
        _HP_ETA = []          # v1.22.1: 血量ETA预测历史 [(t, hp), ...] 3s窗口
        _afk_hits = 0          # AFK弹窗连续命中计数(>=4触发点击)
        _afk_last_mean = None  # 上一帧中心灰度均值(判静止)
        last_map_win = 0
        _boss_pause_until = 0.0   # Bossbar 检测到 Super+ 后暂停追怪的时间戳(别送死)
        _STATS = {"report": 0.0, "t0": time.time(), "fights": 0, "pickups": 0}  # 运行统计(v1.30: 修复未初始化NameError)
        _menu_hits = 0          # v1.31: 连续确认菜单次数(>=5才按Enter, 防游戏内误判开聊天)
        SWARM_WARN, SWARM_COUNT, SWARM_RADIUS = True, 8, 30   # v1.31: 怪潮预警常量(原缺失NameError)

        print(f"[巡逻模式] 共 {len(patrol_points)} 个巡逻点，循环移动中...")

        # ===== 聊天挑战监控(防封号: M28会发消息挑战, 只解AFK不回消息可能封号) =====
        try:
            from chat_solver import ChatSolver
            _chat = ChatSolver(get_window(), get_frame)
            _chat.start()
        except Exception as e:
            print(f"[聊天] 监控启动失败(忽略): {e}")

        # 主循环需要的 combat 函数(一次性import, 避免作用域内NameError)
        from combat import detect_mobs, screen_to_map, ultra_blocked, choose_target

        while True:
            # ===== v1.31: 窗口存活检查(用户关窗/Edge崩溃 -> 重新查找, 找不到则等待) =====
            if not get_window().alive():
                throttle_print("winlost", "[!] 游戏窗口已关闭，重新查找窗口...", 3.0)
                if get_window().find_window():
                    get_window().move_offscreen()
                    time.sleep(2)
                else:
                    time.sleep(5)
                    continue
            # ===== 运行统计(每5分钟打印一次) =====
            if time.time() - _STATS["report"] > 300:
                _STATS["report"] = time.time()
                print(f"[统计] 已运行 {int((time.time() - _STATS['t0']) / 60)} 分钟 | 战斗 {_STATS['fights']} 次 | 拾取掉落 {_STATS['pickups']} 次")
            target = None   # v1.18.3: 循环顶部初始化(否则Boss暂停/首圈/不打怪模式 1264 引用未定义变量 NameError)
            ranks_map = {}
            # ===== AFK Check 弹窗("Are you here?", 60秒不点踢下线): 中心暗+静止连续4帧 -> 点Yes =====
            from combat import detect_afk_check
            _cdf = get_frame()
            _cdark, _cstatic, _cmean = detect_afk_check(_cdf, _afk_last_mean)
            _afk_last_mean = _cmean
            if _cdark and _cstatic:
                _afk_hits += 1
            else:
                _afk_hits = 0
            if _afk_hits >= 4:
                # 先尝试挂机检测拖动验证(v2完整版: 8色起点+灰色路径+Dijkstra最宽路径)
                from afk_solver import try_solve_and_drag
                _solved = try_solve_and_drag(get_window(), _cdf)
                if not _solved:
                    # 兜底: 简版(绿点BFS)再试一次
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
            # 先检查状态
            stage = check_stage()
            if stage == "in_game_dead":
                set_title("死亡复活中")
                throttle_print("dead", "[!] 死亡，正在自动复活...", 2.0)
                respawn()
                continue
            elif stage == "in_menu":
                _menu_hits += 1
                set_title("菜单等待")
                if _menu_hits < 5:   # 连续5次(约15秒)才确认是菜单, 防误判按Enter开聊天
                    throttle_print("menu", f"[!] 疑似菜单(第{_menu_hits}/5次, 确认中)...", 3.0)
                    time.sleep(3)
                    continue
                _menu_hits = 0
                throttle_print("menu", "[!] 确认在菜单，按Enter开始(全键盘)...", 3.0)
                w = get_window()
                w.key_down(0x0D); time.sleep(0.1); w.key_up(0x0D)   # Enter 开始
                time.sleep(1.5)
                w.key_down(0x0D); time.sleep(0.1); w.key_up(0x0D)   # 再按一次(进选图/确认)
                time.sleep(5)
                continue

            pos = get_player_position()
            if pos is not None:
                trail.append(pos)

            # v1.6.0 性能: 本圈共享一次 frame + HSV 转换(原每检测函数各转一次全图, 每圈4-5次cvtColor)
            frame = get_frame()
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # 区域模式: 每次在区域内随机取一个点(随机游走, 覆盖全区域); 旧巡逻点模式: 按点循环
            if region_box is not None:
                _ang = random.random() * 2 * math.pi
                _rr = region_box[2] * math.sqrt(random.random())
                goal_pt = (int(region_box[0] + _rr * math.cos(_ang)),
                           int(region_box[1] + _rr * math.sin(_ang)))
                goal_pt = (min(297, max(2, goal_pt[0])), min(297, max(2, goal_pt[1])))
            else:
                goal_pt = patrol_points[patrol_index]

            # ===== 人性化微操作(防挂机, 无副作用): 微转向/微停顿/微抖动 =====
            if HUMANIZE and pos is not None and random.random() < (0.15 if EFFICIENT else 0.35):
                human_ticks(get_window(), goal_pt)

            # ===== 实时地图窗口(红线路径), 每0.3s刷新 =====
            if SHOW_MAP_WINDOW and time.time() - last_map_win > 0.3:
                draw_overlay_window(patrol_points, pos)
                last_map_win = time.time()

            # ===== Bossbar 检测(研究落地): Super/Eternal/Unique 专属顶部血条 =====
            # 抢Super正确姿势(维基掉落机制): Super+分25人, 伤害>1%有资格 -> 开leech时蹭2.5s拿参与奖就走
            # 别追着打(血量x28秒不掉, 死=清零掉落资格+掉花瓣); 75级前杀Super只掉Ultra档但仍白捡
            try:
                from combat import detect_bossbar, detect_all, screen_to_map, choose_target
                if detect_bossbar(get_frame()):
                    if LEECH:
                        if _boss_pause_until < time.time():
                            print("[Boss] Super+级Boss在场！蹭1%掉落(leech模式, 2.5s就走)...")
                        _pb = pos or get_player_position()
                        if _pb is not None:
                            _rm = detect_all(frame, hsv=hsv)
                            _sup = [m for m in (screen_to_map(p, _pb) for p in (_rm.get("ultra") or []))
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

            # ===== 低血量保命(任何模式, 最高优先级) =====
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
            # v1.22.1: 血量ETA预测(sponge扩展机制) - 血量快速下降(3s内掉>=25%且当前<35%)提前跑路
            if hp is not None and len(_HP_ETA) >= 2:
                _t0, _h0 = _HP_ETA[0]
                _dt = _eta_now - _t0
                if hp < 0.35 and _h0 - hp >= 0.25 and _dt >= 0.5:
                    _drop = (_h0 - hp) / max(_dt, 0.001)  # 每秒掉血
                    print(f"[低血ETA] 血速{-_drop*100:.0f}%/s 当前{hp*100:.0f}%, 提前跑路(海绵机制)")
                    r = flee_low_hp(trail, heal_slots=cfg.get("heal_slots", []))
                    if r in ("in_game_dead", "in_menu"):
                        continue
                    continue

            # ===== 战斗检测（仅巡逻间隙/分段间执行）=====
            # 策略: =秒杀等级自动追(贴0.5px), >秒杀等级避开(往怪少处跑), <秒杀等级不管
            if time.time() < _boss_pause_until:
                pass  # Boss在场: 本圈只巡逻不追怪
            elif COMBAT_ENABLED and kill_rank != "none":
                pos = get_player_position(image=frame)
                if pos is not None:
                    from combat import (detect_all, ultra_blocked, choose_target,
                                        screen_to_map, RANK_ORDER, WARN_MARGIN)
                    ranks_map = detect_all(frame, with_size=True, with_sid=True, hsv=hsv)
                    idx = RANK_ORDER.index(kill_rank) if kill_rank in RANK_ORDER else 5
                    danger = []
                    for r in RANK_ORDER[idx + 1:]:
                        danger += [m for m in (screen_to_map(p, pos) for p in (ranks_map.get(r) or [])) if m]
                    near = ultra_blocked(danger, pos, margin=WARN_MARGIN)
                    if near:
                        r = handle_danger(pos, near, ranks_map, trail, kill_rank)
                        if r in ("in_game_dead", "in_menu"):
                            continue
                        continue
                    # Super 薄荷绿怪: leech开则蹭1%掉落(Super分25人), 否则避开(75级前杀Super只掉究极档)
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
                    # 飞行物(导弹/螯针等): 靠近就横向闪避
                    from combat import detect_projectiles
                    near_p = nearest_proj(detect_projectiles(frame, hsv=hsv))
                    if near_p:
                        print("[闪避] 飞行物来袭，横向闪避")
                        dodge_proj(near_p)
                        continue
                    # 特殊稀有生物最优先(正方形>shiny>金叶虫>潜水兵蚁): 放宽巡逻偏离限制追
                    # v1.6.0 降频: 特殊怪极稀有, 每0.4s才检测一次(省一次全图5色inRange)
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
                    # 蹭掉落: 打不动的更高等级怪在10-25px内 -> 打LEECH_TIME秒混掉落(总伤害≥5%即可分掉落, v1.24.3)
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
                        # 随机打怪模式: 屏幕内任意非U怪随机挑一只打(避开U级, 防止送死循环)
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
                        from combat import mob_name, drop_hint, mob_hp, threat_hint, mob_name_en
                        _tname = mob_name(target[3]) if len(target) >= 4 and target[3] else "未知"
                        _tname_en = mob_name_en(target[3]) if len(target) >= 4 and target[3] else ""
                        _drop = drop_hint(target[3], rarity=5) if len(target) >= 4 and target[3] else ""
                        _kidx = RANK_ORDER.index(kill_rank) if kill_rank in RANK_ORDER else 5
                        _hp = mob_hp(target[3], _kidx) if len(target) >= 4 and target[3] else None
                        _thr = threat_hint(target[3], RANK_ORDER.index(kill_rank)) if len(target) >= 4 and target[3] else ""
                        print(f"[战斗] 发现目标 {_tname}{('/' + _tname_en) if _tname_en and _tname_en != _tname else ''}({kill_rank}) HP {_hp or '?'} {target}，追击..." +
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

            # ===== 怪潮预警: 屏幕怪太多且无目标可打(被围) -> 往怪群反方向走 =====
            if SWARM_WARN and target is None:
                total_mobs = sum(len(v) for v in ranks_map.values())
                if total_mobs > SWARM_COUNT:
                    swarm_c = [m for m in (screen_to_map(p, pos) for v in ranks_map.values() for p in v) if m]
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

            # ===== 掉落自动拾取（顺路捡，战斗/危险优先；只捡近的，不影响巡逻主线）=====
            if PICKUP_DROPS:
                frame = get_frame()
                pos = get_player_position(image=frame)
                if pos is not None:
                    from combat import detect_drops
                    if time.time() - _last_drops > 0.3:
                        _drops_px = detect_drops(frame, hsv=hsv, with_rank=True)
                        _last_drops = time.time()
                    # v1.7.0 只捡值钱的掉落(稀有度权重>=PICKUP_MIN_RANK)
                    drops = [m for m in (screen_to_map(p, pos) for p in _drops_px
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

            # ===== 正常巡逻（分段走，走一段回来看怪）=====
            set_title(f"巡逻中 点{patrol_index+1}/{len(patrol_points)}")
            result = lazy_theta_pathing(goal_pt, dedicated_area, step=PATH_STEP if COMBAT_ENABLED else 0)
            if result is True:
                if region_box is not None:
                    print("[区域] 到达随机点，区域内继续游走")
                else:
                    print(f"[巡逻] 到达点 {patrol_index+1}，前往下一个点")
                    # 巡逻顺序随机化(像人不固定路线, 兼防挂机): 随机选非当前点
                    patrol_index = random.choice([i for i in range(len(patrol_points)) if i != patrol_index])
                PATH_CACHE.update(goal=None, path=None)
                # 防挂机: 到达后随机停顿(效率模式更短)
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
        get_window().move_onscreen(bring_front=False)   # v1.31: 退出沉底不弹前台(用户忙)
        print("[+] 窗口已移回屏幕(保持后台)")
