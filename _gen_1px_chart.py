# -*- coding: utf-8 -*-
"""生成 florr 插件 "1px" 换算信息图"""
from PIL import Image, ImageDraw, ImageFont
import os

W, H = 1800, 1400
img = Image.new("RGB", (W, H), "#FFFFFF")
d = ImageDraw.Draw(img)

# 字体(Windows 微软雅黑)
F = "C:/Windows/Fonts/msyh.ttc"
FB = "C:/Windows/Fonts/msyhbd.ttc"
def f(sz, bold=False):
    return ImageFont.truetype(FB if bold else F, sz)

def text(x, y, s, font, fill="#1A1B1C", anchor="la"):
    d.text((x, y), s, font=font, fill=fill, anchor=anchor)

def rect(x, y, w, h, fill, outline, lw=2):
    d.rectangle([x, y, x+w, y+h], fill=fill, outline=outline, width=lw)

def arrow(x1, y, x2, color="#94A3B8"):
    d.line([(x1, y), (x2-12, y)], fill=color, width=3)
    d.polygon([(x2, y), (x2-14, y-7), (x2-14, y+7)], fill=color)

# ===== 标题 =====
text(W//2, 45, "florr 插件坐标系统 · \"1px\" 换算全图", f(34, True), anchor="ma")
text(W//2, 92, "屏幕像素 ↔ 世界单位 ↔ 地图像素  |  战斗参数实际大小  |  100寸 4K 屏物理尺寸", f(17), fill="#6B7280", anchor="ma")

# ===== 换算链: 三个方框 ===
box_y, box_h = 140, 280
bw = 440
gap = 60
x1 = 60
x2 = x1 + bw + gap
x3 = x2 + bw + gap

# 方框1: 1 屏幕
rect(x1, box_y, bw, box_h, "#FFF0F3", "#E07A90", 3)
text(x1+bw//2, box_y+28, "1 屏幕像素", f(24, True), anchor="ma")
text(x1+bw//2, box_y+68, "Screen Pixel", f(15), fill="#6B7280", anchor="ma")
d.line([(x1+40, box_y+100), (x1+bw-40, box_y+100)], fill="#E4E3DD", width=1)
text(x1+30, box_y+120, "= 5 世界单位", f(20))
text(x1+30, box_y+158, "= 0.0242 地图像素", f(20))
text(x1+30, box_y+200, "100寸 4K 屏 = 0.55 mm", f(18), fill="#E07A90")
text(x1+30, box_y+236, "（玩家屏幕中心 = 画面中心）", f(14), fill="#6B7280")

# 箭头1
arrow(x1+bw+5, box_y+box_h//2, x2-5)

# 方框2: 1 世界单位
rect(x2, box_y, bw, box_h, "#F0F9FF", "#3B82F6", 3)
text(x2+bw//2, box_y+28, "1 世界单位", f(24, True), anchor="ma")
text(x2+bw//2, box_y+68, "World Unit（游戏内部坐标）", f(15), fill="#6B7280", anchor="ma")
d.line([(x2+40, box_y+100), (x2+bw-40, box_y+100)], fill="#E4E3DD", width=1)
text(x2+30, box_y+120, "= 0.2 屏幕像素", f(20))
text(x2+30, box_y+158, "= 0.00484 地图像素", f(20))
text(x2+30, box_y+200, "100寸 4K 屏 = 0.11 mm", f(18), fill="#3B82F6")
text(x2+30, box_y+236, "（florr 怪物/玩家碰撞半径≈100单位）", f(14), fill="#6B7280")

# 箭头2
arrow(x2+bw+5, box_y+box_h//2, x3-5)

# 方框3: 1 地图像素
rect(x3, box_y, bw, box_h, "#F0FFF4", "#22C55E", 3)
text(x3+bw//2, box_y+28, "1 地图像素", f(24, True), anchor="ma")
text(x3+bw//2, box_y+68, "Map Pixel（300×300 缩略图）", f(15), fill="#6B7280", anchor="ma")
d.line([(x3+40, box_y+100), (x3+bw-40, box_y+100)], fill="#E4E3DD", width=1)
text(x3+30, box_y+120, "= 206.5 世界单位", f(20))
text(x3+30, box_y+158, "= 41.3 屏幕像素", f(20))
text(x3+30, box_y+200, "100寸 4K 屏 = 22.7 mm", f(18), fill="#22C55E")
text(x3+30, box_y+236, "（战斗参数 ULTRA_AVOID 等的单位）", f(14), fill="#6B7280")

# ===== 战斗参数换算表 =====
table_y = 480
text(W//2, table_y, "战斗参数 · 实际大小换算", f(24, True), anchor="ma")

cols = [("参数", 320), ("地图像素", 200), ("世界单位", 260), ("屏幕像素", 260), ("物理mm(100寸4K)", 300)]
table_w = sum(c[1] for c in cols)
tx = (W - table_w) // 2
ty = table_y + 40
row_h = 64

# 表头
rect(tx, ty, table_w, row_h, "#F4F3EE", "#E4E3DD", 1)
cx = tx
for name, cw in cols:
    text(cx+cw//2, ty+row_h//2, name, f(18, True), anchor="mm")
    cx += cw

# 数据行
rows = [
    ("ULTRA_AVOID  避U圈", "5", "1032.5", "206.5", "113.3 mm"),
    ("ULTRA_KISS  贴脸距离", "0.5", "103.3", "20.7", "11.3 mm"),
    ("DEVIATION  打M偏离容忍", "30", "6195", "1239", "679.6 mm"),
    ("PATH_STEP  巡逻分段", "40", "8260", "1652", "906.1 mm"),
]
for i, row in enumerate(rows):
    ry = ty + row_h * (i+1)
    bg = "#FFFFFF" if i % 2 == 0 else "#FAFAF8"
    rect(tx, ry, table_w, row_h, bg, "#E4E3DD", 1)
    cx = tx
    for j, (val, (_, cw)) in enumerate(zip(row, cols)):
        color = "#1A1B1C"
        if j == 0:
            color = "#E07A90" if "ULTRA" in val else "#1F7A3D" if "DEVIATION" in val else "#1A1B1C"
        text(cx+cw//2, ry+row_h//2, val, f(18), fill=color, anchor="mm")
        cx += cw

# ===== 注意事项 =====
note_y = ty + row_h * 5 + 40
text(60, note_y, "注意事项", f(22, True))
notes = [
    "1. SCALE_PX_PER_UNIT = 5.0（屏幕像素↔世界单位换算）为经验值，需在游戏内实测标定；追怪方向不准时只调这一个数。",
    "2. 物理尺寸按 100 寸 / 4096×2160 计算（1px=0.5485mm）；其他分辨率或屏幕尺寸下物理mm不同，但软件像素换算不变。",
    "3. 插件里的 \"1px\" 默认指地图像素（战斗参数 ULTRA_AVOID / ULTRA_KISS / DEVIATION 等），不是屏幕像素也不是物理毫米。",
    "4. 玩家恒在屏幕中心，怪物屏幕坐标 → 地图坐标靠 \"玩家屏幕中心 + 标定缩放系数\" 换算；小地图不显示怪物，只能从主画面识别。",
]
for i, n in enumerate(notes):
    text(60, note_y + 40 + i*36, n, f(16), fill="#4B5563")

# 底部来源
text(W//2, H-30, "数据来源: combat.py / utils.py 常量  |  物理尺寸: 100寸 4096×2160 对角线2540mm", f(13), fill="#9CA3AF", anchor="ma")

out = r"C:\Users\intel\Downloads\florr-auto-pathing-main\florr_1px_cheatsheet.png"
img.save(out, "PNG")
print(f"saved: {out}")
print(f"size: {os.path.getsize(out)} bytes")
