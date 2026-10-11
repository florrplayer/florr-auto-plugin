# -*- coding: utf-8 -*-
"""把 autoflorr 图标做成 C++ 风格圆角方形 .ico (透明四角)
用法: py -3.12 tools\_make_icon.py"""
from PIL import Image, ImageDraw
import os

SRC = r"C:\Users\intel\Desktop\备份图形1.jpg"
OUT_DIR = r"C:\Users\intel\Downloads\florr-auto-pathing-main\assets"
os.makedirs(OUT_DIR, exist_ok=True)

BASE = 1024
RADIUS = 220  # 圆角半径 (~21.5%, C++ 图标观感)

img = Image.open(SRC).convert("RGBA")
print(f"原图: {img.size}")

# 1. 等比缩放到 BASE (整幅覆盖, 内容居中不变)
img = img.resize((BASE, BASE), Image.LANCZOS)

# 2. 圆角 mask: 四角外透明
mask = Image.new("L", (BASE, BASE), 0)
d = ImageDraw.Draw(mask)
d.rounded_rectangle([0, 0, BASE - 1, BASE - 1], radius=RADIUS, fill=255)

out = Image.new("RGBA", (BASE, BASE), (0, 0, 0, 0))
out.paste(img, (0, 0), mask)
out.save(os.path.join(OUT_DIR, "icon_1024.png"))
print("保存 icon_1024.png (圆角方形, 透明四角)")

# 3. 多尺寸 .ico (16/24/32/48/64/128/256)
sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
icons = [out.resize(s, Image.LANCZOS) for s in sizes]
ico_path = os.path.join(OUT_DIR, "autoflorr.ico")
out.save(ico_path, format="ICO", sizes=sizes)
print(f"保存 {ico_path} (多尺寸 ico)")

# 4. 512 PNG (GitHub 仓库 logo 用)
out.resize((512, 512), Image.LANCZOS).save(os.path.join(OUT_DIR, "icon_512.png"))
print("保存 icon_512.png")

# 5. 小尺寸预览验证
small = out.resize((128, 128), Image.LANCZOS)
small.save(os.path.join(OUT_DIR, "_icon_preview.png"))
print("完成")
