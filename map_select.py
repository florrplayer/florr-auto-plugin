import sys
import os
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import MAP_DIR

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
