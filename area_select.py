import sys
import os
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import MAP_DIR

map_name = sys.argv[1] if len(sys.argv) > 1 else "desert"
map_path = os.path.join(MAP_DIR, map_name + ".png")
assert os.path.exists(map_path), f"找不到地图文件: {map_path}，可选: {[p[:-4] for p in os.listdir(MAP_DIR) if p.lower().endswith('.png')]}"
map_image = cv2.imread(map_path)

map_image_copy = map_image.copy()

areas = []
current_area = []


def on_mouse_click(event, x, y, flags, param):
    global map_image, current_area, areas
    if event == cv2.EVENT_LBUTTONDOWN:
        current_area.append((x, y))
        cv2.circle(map_image, (x, y), radius=2,
                   color=(0, 0, 255), thickness=-1)
        cv2.putText(map_image, f"({x}, {y})", (x + 5, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (4, 250, 4), 1)
        if len(current_area) == 2:
            areas.append(current_area)
            print(f"Area added: {current_area}")
            current_area = []

        redraw_map()

    elif event == cv2.EVENT_RBUTTONDOWN:
        if current_area:
            removed_point = current_area.pop()
            print(f"Removed point: {removed_point}")
        elif areas:
            removed_area = areas.pop()
            print(f"Removed area: {removed_area}")
        else:
            print("No points or areas to undo.")

        redraw_map()


def redraw_map():
    global map_image, map_image_copy, areas
    map_image = map_image_copy.copy()
    for area in areas:
        cv2.rectangle(map_image, area[0], area[1],
                      color=(0, 0, 255), thickness=1)
        cv2.putText(map_image, f"{area}", (area[0][0], area[0][1] - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (4, 250, 4), 1)
    cv2.imshow("Map", map_image)


cv2.imshow("Map", map_image)
cv2.setMouseCallback("Map", on_mouse_click)
cv2.waitKey(0)
cv2.destroyAllWindows()

print("Final areas:", areas)
