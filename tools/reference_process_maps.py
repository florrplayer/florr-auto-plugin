from PIL import Image
import cv2
import numpy as np
import os

def process_map_to_binary(input_path, output_path, target_size=300):
    img = Image.open(input_path)
    
    if img.mode == 'RGBA':
        img = img.convert('RGB')
    
    img_resized = img.resize((target_size, target_size), Image.LANCZOS)
    img_cv = cv2.cvtColor(np.array(img_resized), cv2.COLOR_RGB2BGR)
    
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    
    hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
    
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([30, 255, 255])
    yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
    binary[yellow_mask > 0] = 255
    
    cv2.imwrite(output_path, binary)
    print(f"已处理: {input_path} -> {output_path}")
    print(f"  尺寸: {target_size}x{target_size}")

maps = [
    ('factory.png', 'factory'),
    ('garden.png', 'garden'),
    ('sewers.png', 'sewers'),
    ("worm's inside.png", "worm's inside"),
]

print("处理地图文件...")
print("=" * 60)

for input_file, map_name in maps:
    if os.path.exists(input_file):
        output_file = f"./florr-auto-pathing/maps/{map_name}.png"
        process_map_to_binary(input_file, output_file)
    else:
        print(f"文件不存在: {input_file}")
