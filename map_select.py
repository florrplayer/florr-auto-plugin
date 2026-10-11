import sys
import os
import random
import math
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import MAP_DIR


def generate_patrol_points(map_name, count=8, min_distance=35, margin=4, region=None):
    """从最大连通可走区选取分散巡逻点，可限制在 (cx, cy, radius) 圆区内。"""
    map_path = os.path.join(MAP_DIR, map_name + ".png")
    map_image = cv2.imread(map_path, cv2.IMREAD_GRAYSCALE)
    if map_image is None:
        return []

    walkable = (map_image == 255).astype(np.uint8)
    component_count, labels, stats, _ = cv2.connectedComponentsWithStats(walkable, 8)
    if component_count <= 1:
        return []
    component = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    ys, xs = np.where(labels == component)
    interior = ((xs >= margin) & (xs < map_image.shape[1] - margin)
                & (ys >= margin) & (ys < map_image.shape[0] - margin))
    if region:
        center_x, center_y, radius = region
        interior &= (xs - center_x) ** 2 + (ys - center_y) ** 2 <= radius ** 2
    candidates = np.column_stack((xs[interior], ys[interior]))
    if not len(candidates):
        return []

    chosen = [random.randrange(len(candidates))]
    nearest_sq = np.full(len(candidates), np.inf)
    min_distance_sq = min_distance * min_distance
    while len(chosen) < count:
        point = candidates[chosen[-1]]
        delta = candidates - point
        nearest_sq = np.minimum(nearest_sq, np.sum(delta * delta, axis=1))
        nearest_sq[chosen] = -1
        next_index = int(np.argmax(nearest_sq))
        if nearest_sq[next_index] < min_distance_sq:
            break
        chosen.append(next_index)
    return [tuple(map(int, candidates[index])) for index in chosen]


def generate_random_patrol_point(map_name, region=None, avoid=None, min_distance=12, attempts=8):
    """在可走区域内重新抽取一个巡逻点，尽量避开上一目标。"""
    candidate = None
    for _ in range(max(1, attempts)):
        points = generate_patrol_points(map_name, count=1, region=region)
        if not points:
            return None
        candidate = points[0]
        if avoid is None or math.hypot(candidate[0] - avoid[0], candidate[1] - avoid[1]) >= min_distance:
            return candidate
    return candidate


def select_patrol_points(map_name):
    map_path = os.path.join(MAP_DIR, map_name + ".png")
    available = [p[:-4] for p in os.listdir(MAP_DIR) if p.lower().endswith('.png')]
    assert os.path.exists(map_path), f"找不到地图文件: {map_path}，可选: {available}"
    map_image_copy = cv2.imread(map_path)
    patrol_points = []

    def redraw_map():
        map_image = map_image_copy.copy()
        for index, point in enumerate(patrol_points, 1):
            cv2.circle(map_image, point, radius=2, color=(0, 0, 255), thickness=-1)
            cv2.putText(map_image, f"{index}: {point}", (point[0] + 5, point[1] - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (4, 250, 4), 1)
        cv2.imshow("Select patrol points - Enter to confirm, right-click to undo", map_image)

    def on_mouse_click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            patrol_points.append((x, y))
            print(f"Map position: ({x}, {y})")
            redraw_map()
        elif event == cv2.EVENT_RBUTTONDOWN and patrol_points:
            removed = patrol_points.pop()
            print(f"Removed point: {removed}")
            redraw_map()

    redraw_map()
    cv2.setMouseCallback("Select patrol points - Enter to confirm, right-click to undo", on_mouse_click)
    print(f"[巡逻点] 当前地图: {map_name}，左键添加，右键撤销，按 Enter 确认")
    while True:
        key = cv2.waitKey(50) & 0xFF
        if key in (13, 10):
            break
        if key == 27:
            cv2.destroyAllWindows()
            raise RuntimeError("已取消巡逻点选择")
    cv2.destroyAllWindows()
    if not patrol_points:
        raise RuntimeError("至少选择一个巡逻点")
    print(f"[巡逻点] 已确认: {patrol_points}")
    return patrol_points


if __name__ == "__main__":
    map_name = sys.argv[1] if len(sys.argv) > 1 else "desert"
    select_patrol_points(map_name)
