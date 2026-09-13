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


def on_mouse_click(event, x, y, flags, param):
    global map_image
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"Map position: ({x}, {y})")
        map_image = map_image_copy.copy()
        cv2.circle(map_image, (x, y), radius=2,
                   color=(0, 0, 255), thickness=-1)
        cv2.putText(map_image, f"({x}, {y})", (x + 5, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (4, 250, 4), 1)
        cv2.imshow("Map", map_image)


cv2.imshow("Map", map_image)
cv2.setMouseCallback("Map", on_mouse_click)
cv2.waitKey(0)
cv2.destroyAllWindows()
