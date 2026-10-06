# -*- coding: utf-8 -*-
"""flee_planner.py v1.28.0 - 追逃逃跑规划 (双源最短路)
思路来源: greatluca666/florr-auto-farm flee_planner.py (GPLv3, 独立重写实现)
追逃问题标准做法: 以自己为中心跑两遍 8 邻接最短路(不许斜穿墙角),
  一遍从自己出发(D_me), 一遍从所有追兵出发(D_chaser)。
  D_chaser - D_me = 早到格数(lead); 在早到 >= SAFE_MARGIN 的格里挑最远的:
  死胡同跑不远自然落选, 最短路每格都满足"我先到"(三角不等式), 不会半路被截。
危险怪群身边的格对自己当墙(规划绕开), 追兵不受限。
纯函数: 不碰屏幕/IO; 坐标全是小地图像素(浮点, 北在上)。
"""
import heapq
import math

HORIZON = 20          # 格: 只在 ±20 格内规划(≈4300 世界单位)
SAFE_MARGIN = 1.0     # 格: 比追兵早到这么多才算安全 (1格≈217世界单位≈0.7s)
MARGIN_CAP = 4.0      # 早到再多不加分 (不因"更安全"放弃"跑得远")
MARGIN_WEIGHT = 0.5
CROWD_BLOCK_R = 0.8   # 格: 危险怪群身边这么近的格不走
WAYPOINT_MAX = 5      # 朝路径上最远直线可见的点走, 最多看这么远
BEYOND_STEPS = 10     # 窗口边的格往外再走这么多步才算"活路"
KEEP_R = 3.0          # 离上一拍目标这么近 = 原来那条路
KEEP_BONUS = 2.0      # 原来那条路加分, 安全线放宽一半
_LOS_STEP = 0.25

_SQRT2 = math.sqrt(2.0)
_STEPS = ((1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
          (1, 1, _SQRT2), (1, -1, _SQRT2), (-1, 1, _SQRT2), (-1, -1, _SQRT2))


def _free(bm, x, y):
    return 0 <= y < bm.shape[0] and 0 <= x < bm.shape[1] and bm[y, x] == 255


def _snap(bm, p, search=2):
    """浮点位置 -> 最近可走格 (人/怪常"站在墙上"因为地图墙比游戏厚一格)"""
    cx, cy = int(round(p[0])), int(round(p[1]))
    best = None
    for y in range(cy - search, cy + search + 1):
        for x in range(cx - search, cx + search + 1):
            if _free(bm, x, y):
                d = math.hypot(x - p[0], y - p[1])
                if best is None or d < best[0]:
                    best = (d, (x, y))
    return best


def _dijkstra(bm, seeds, box, blocked=frozenset()):
    """多源最短路. seeds: [(初始代价, (x,y))]. box 闭区间.
    斜走要求两个正交邻格都可走(花有体积挤不过墙角). 返回 (dist, parent)"""
    dist, parent = {}, {}
    heap = [(c, cell, None) for c, cell in seeds]
    heapq.heapify(heap)
    while heap:
        d, cell, par = heapq.heappop(heap)
        if cell in dist:
            continue
        dist[cell] = d
        parent[cell] = par
        x, y = cell
        for dx, dy, c in _STEPS:
            nx, ny = x + dx, y + dy
            nxt = (nx, ny)
            if (nxt in dist or nxt in blocked
                    or not (box[0] <= nx <= box[2] and box[1] <= ny <= box[3])
                    or not _free(bm, nx, ny)):
                continue
            if dx and dy and not (_free(bm, x + dx, y) and _free(bm, x, y + dy)):
                continue
            heapq.heappush(heap, (d + c, nxt, cell))
    return dist, parent


def _los(bm, a, b, blocked):
    """a->b 直线每 1/4 格采样, 全在可走且没被怪群占的格上"""
    n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / _LOS_STEP))
    for i in range(1, n + 1):
        x = int(round(a[0] + (b[0] - a[0]) * i / n))
        y = int(round(a[1] + (b[1] - a[1]) * i / n))
        if not _free(bm, x, y) or (x, y) in blocked:
            return False
    return True


def _escapes_beyond(bm, cell, box, steps=BEYOND_STEPS):
    """窗口边上的格往窗外走还能走 steps 步吗 —— 窗口边切死湾中间时湾里格子也在边上"""
    def outside(x, y):
        return not (box[0] < x < box[2] and box[1] < y < box[3])
    seen = {cell}
    frontier = [cell]
    for _ in range(steps):
        nxt = []
        for x, y in frontier:
            for dx, dy, _c in _STEPS:
                n = (x + dx, y + dy)
                if n in seen or not outside(*n) or not _free(bm, *n):
                    continue
                if dx and dy and not (_free(bm, x + dx, y) and _free(bm, x, y + dy)):
                    continue
                seen.add(n)
                nxt.append(n)
        if not nxt:
            return False
        frontier = nxt
    return True


def plan_flee(bm, me, chasers, crowd=(), horizon=HORIZON, margin=SAFE_MARGIN, prefer=None):
    """返回 {"dir": 单位向量, "goal": 目标格, "lead": 早到格数, "safe": bool}
    规划不了(自己不在图/没追兵/一步都走不动)-> None, 调用方退回老办法。
    me/chasers/crowd: 小地图像素浮点坐标. crowd 是别撞进去的怪群.
    safe=False = 哪儿都不比追兵先到(被堵死), 挑早到最多的(亏最少)。"""
    start = _snap(bm, me)
    if start is None:
        return None
    sx, sy = start[1]
    box = (sx - horizon, sy - horizon, sx + horizon, sy + horizon)

    seeds_c = []
    for c in chasers:
        snapped = _snap(bm, c)
        if snapped is not None:
            seeds_c.append(snapped)
    if not seeds_c:
        return None

    blocked = set()
    r = int(math.ceil(CROWD_BLOCK_R))
    for mx, my in crowd:
        for y in range(int(round(my)) - r, int(round(my)) + r + 1):
            for x in range(int(round(mx)) - r, int(round(mx)) + r + 1):
                if math.hypot(x - mx, y - my) <= CROWD_BLOCK_R:
                    blocked.add((x, y))
    blocked.discard(start[1])

    d_me, parent = _dijkstra(bm, [start], box, frozenset(blocked))
    if len(d_me) <= 1 and blocked:
        # 怪群贴脸身边一圈全被当墙 -> 从怪群里挤出去也比站着强
        blocked = set()
        d_me, parent = _dijkstra(bm, [start], box)
    d_ch, _ = _dijkstra(bm, seeds_c, box)

    # 挑目标: 安全的活路(窗外走得出去) > 安全死路里最远 > 全不安全时早到最多(亏最少)
    ranked = []
    for cell, dm in d_me.items():
        if cell == start[1]:
            continue
        lead = d_ch.get(cell, math.inf) - dm
        kept = prefer is not None and math.hypot(cell[0] - prefer[0], cell[1] - prefer[1]) <= KEEP_R
        safe = lead >= (margin * 0.5 if kept else margin)
        if safe:
            score = (min(dm, horizon) + MARGIN_WEIGHT * min(lead, MARGIN_CAP)
                     + (KEEP_BONUS if kept else 0.0))
        else:
            score = lead
        on_edge = cell[0] in (box[0], box[2]) or cell[1] in (box[1], box[3])
        ranked.append((safe, score, on_edge, cell, lead))
    if not ranked:
        return None
    ranked.sort(key=lambda r: (r[0], r[1]), reverse=True)
    pick = None
    for safe, _score, on_edge, cell, lead in ranked:
        if not safe:
            break
        if on_edge and _escapes_beyond(bm, cell, box):
            pick = (cell, lead, safe)
            break
    if pick is None:
        _, _, _, cell, lead = ranked[0]
        pick = (cell, lead, ranked[0][0])
    goal, lead, safe = pick

    path = []
    cell = goal
    while cell is not None:
        path.append(cell)
        cell = parent[cell]
    path.reverse()

    origin = me if _free(bm, int(round(me[0])), int(round(me[1]))) else start[1]
    way = path[1] if len(path) > 1 else goal
    for cell in path[1:WAYPOINT_MAX + 1]:
        if _los(bm, origin, cell, blocked):
            way = cell
    dx, dy = way[0] - me[0], way[1] - me[1]
    n = math.hypot(dx, dy)
    if n < 1e-6:
        return None
    return {"dir": (dx / n, dy / n), "goal": goal, "lead": lead, "safe": safe}


def plan_flee_light(me, chasers, crowd=(), horizon=HORIZON, margin=SAFE_MARGIN, prefer=None, obstacles=()):
    """无位图轻量版: 不需要 bm 二值图, 用世界坐标直接算。
    obstacles: ((x,y,r),...) 墙/障碍圆 (中心+半径), 用于不穿墙启发。
    返回同 plan_flee: {"dir","goal","lead","safe"} 或 None。"""
    if not chasers:
        return None
    # 网格采样: 自己周围 ±horizon, 步长1 (世界单位)
    mx, my = me
    grid = []
    for gx in range(int(mx) - horizon, int(mx) + horizon + 1, 1):
        for gy in range(int(my) - horizon, int(my) + horizon + 1, 1):
            cell = (gx, gy)
            if math.hypot(gx - mx, gy - my) > horizon:
                continue
            if any(math.hypot(gx - ox, gy - oy) < r for ox, oy, r in obstacles):
                continue
            dm = math.hypot(gx - mx, gy - my)
            if dm < 0.5:
                continue  # 排除自己所在格 (dm=0 时 lead 最大会被误选)
            d_ch = min(math.hypot(gx - cx, gy - cy) for cx, cy in chasers)
            lead = d_ch - dm
            grid.append((cell, dm, lead))
    if not grid:
        return None
    # 危险怪群当障碍 (crowd 中心周围 CROWD_BLOCK_R 不算)
    def crowd_near(cell):
        return any(math.hypot(cell[0] - cx, cell[1] - cy) <= CROWD_BLOCK_R for cx, cy in crowd)
    safe_cells = [g for g in grid if g[2] >= margin and not crowd_near(g[0])]
    pool = safe_cells if safe_cells else grid
    # 安全格: 挑"跑得最远 + 早到加权"; 全不安全: 挑早到最多(亏最少)
    if safe_cells:
        best = max(pool, key=lambda g: (g[1] + MARGIN_WEIGHT * min(g[2], MARGIN_CAP)))
    else:
        best = max(pool, key=lambda g: g[2])
    goal, dm, lead = best
    dx, dy = goal[0] - mx, goal[1] - my
    n = math.hypot(dx, dy)
    if n < 1e-6:
        return None
    return {"dir": (dx / n, dy / n), "goal": goal, "lead": lead,
            "safe": lead >= margin and not crowd_near(goal)}


if __name__ == '__main__':
    print('=== flee_planner 测试 ===')
    try:
        import numpy as np
        bm = np.full((120, 120), 255, dtype=np.uint8)
        bm[50:70, 60:70] = 0   # 一道墙
        res = plan_flee(bm, (60, 30), [(58, 90)], crowd=[(60, 45)])
        print(f'  位图版: {res}')
    except ImportError:
        print('  无numpy, 跳位图测试')
    res2 = plan_flee_light((60, 30), [(58, 90)], crowd=[(60, 45)])
    print(f'  轻量版: {res2}')
    res3 = plan_flee_light((60, 30), [(58, 90)])
    print(f'  轻量版(无怪群): {res3}')
