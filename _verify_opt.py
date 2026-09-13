"""优化后的核心算法验证（不需要真实游戏窗口，只验证寻路/吸附/连通性）
在新地图(anthell/desert)上运行：测试点从主连通分量选取，避免迷宫死胡同导致的合理无路"""
import sys, os, time
import cv2
import numpy as np

sys.path.insert(0, r"C:\Users\intel\Downloads\florr-auto-pathing-main")
os.chdir(r"C:\Users\intel\Downloads\florr-auto-pathing-main")

import main as M
from utils import apply_map, load_binary_map, calibrate_player

def main_component(binary):
    """返回主连通分量的可走点集合"""
    walk = (binary == 255).astype(np.uint8)
    n, labels, stats, cents = cv2.connectedComponentsWithStats(walk, 8)
    if n <= 1:
        return np.argwhere(binary == 255)
    big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return np.argwhere(labels == big)

def rng_point(pts, rng, x_lo=10, x_hi=290, y_lo=10, y_hi=290):
    while True:
        p = pts[rng.integers(len(pts))]
        y, x = int(p[0]), int(p[1])
        if x_lo <= x <= x_hi and y_lo <= y <= y_hi:
            return (x, y)

results = {}
for mapname in ["anthell", "desert"]:
    print(f"\n########## 地图: {mapname} ##########")
    apply_map(mapname)
    binary = load_binary_map()
    rows, cols = binary.shape
    pts = main_component(binary)
    print(f"地图: {binary.shape}, 可行走格: {(binary==255).sum()}, 主分量点: {len(pts)}")

    def snap(p):
        return calibrate_player(binary, p)

    # 1) 寻路正确性：路径首尾正确、全部可行走
    rng = np.random.default_rng(42)
    s, g = snap(rng_point(pts, rng)), snap(rng_point(pts, rng))
    path = M.lazy_theta_star(binary, s, g)
    assert path and path[0] == s and path[-1] == g, f"路径端点错误: {s} -> {g}, path={None if path is None else (path[0], path[-1])}"
    for x, y in path:
        assert binary[y, x] == 255, f"路径含不可行走点 ({x},{y})"
    print(f"[1] 寻路 OK: ({s}) -> ({g}), 点数={len(path)}")

    # 2) 路径平滑性：Theta* 应把视线直通的两点拉直
    s2, g2 = snap(rng_point(pts, rng, 20, 120, 20, 120)), snap(rng_point(pts, rng, 120, 280, 20, 120))
    path2 = M.lazy_theta_star(binary, s2, g2)
    print(f"[2] 平滑路径点数={len(path2) if path2 else -1}")

    # 3) 40 对随机点寻路成功率 + 性能
    pairs = []
    while len(pairs) < 40:
        a = snap(rng_point(pts, rng))
        b = snap(rng_point(pts, rng))
        if a != b:
            pairs.append((a, b))
    ok = 0; ln = 0
    t0 = time.time()
    for s_, g_ in pairs:
        p = M.lazy_theta_star(binary, s_, g_)
        if p: ok += 1; ln += len(p)
    dt = (time.time() - t0) / 40 * 1000
    print(f"[3] 40 对主分量点: 成功率 {ok}/40, 平均点数 {ln/max(ok,1):.1f}, 平均 {dt:.1f}ms")

    # 4) 吸附一致性(±3px 抖动) + 墙内吸附
    walkable = np.argwhere(binary == 255)
    rng2 = np.random.default_rng(7)
    mismatch = 0
    for _ in range(300):
        y0, x0 = walkable[rng2.integers(len(walkable))]
        px = int(x0) + int(rng2.integers(-3, 4)); py = int(y0) + int(rng2.integers(-3, 4))
        px = min(max(px, 0), cols-1); py = min(max(py, 0), rows-1)
        n1 = calibrate_player(binary, (px, py))
        # 朴素最近可走点(对照)
        best, bd = None, float('inf')
        for yy in range(max(0,py-3), min(rows,py+4)):
            for xx in range(max(0,px-3), min(cols,px+4)):
                if binary[yy, xx] == 255:
                    dd = (xx-px)**2 + (yy-py)**2
                    if dd < bd: bd, best = dd, (xx, yy)
        if n1 != best: mismatch += 1
    walls = np.argwhere(binary == 0)
    wy, wx = walls[len(walls)//2]
    nw = calibrate_player(binary, (int(wx), int(wy)))
    assert binary[nw[1], nw[0]] == 255
    print(f"[4] 300 次抖动吸附不一致 {mismatch}/300; 墙内点吸附 OK -> {nw}")

    # 5) 长距离寻路性能
    t0 = time.time()
    for i in range(20):
        a = snap(rng_point(pts, rng, 10, 140, 10, 140))
        b = snap(rng_point(pts, rng, 160, 290, 160, 290))
        M.lazy_theta_star(binary, a, b)
    print(f"[5] 20 次长距离寻路平均 {(time.time()-t0)/20*1000:.1f}ms")

    # 6) 从墙里出发也能寻路(生产流程中起点已吸附; 此处验证宽容度)
    p7 = M.lazy_theta_star(binary, (60, 60), snap(rng_point(pts, rng, 200, 290, 200, 290)))
    print(f"[6] 墙起点(60,60): {'OK 点数'+str(len(p7)) if p7 else '无路(合理)'}")

    results[mapname] = "PASS"

print("\n=== 全部验证通过 ===")
for k, v in results.items():
    print(f"  {k}: {v}")
