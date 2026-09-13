# -*- coding: utf-8 -*-
"""florr 官方 TMJ -> 插件二值小地图 (255=可走, 0=墙)

规则:
- 所有 tilelayer 按列表顺序从底到顶叠加(shortcut 层 collisions=false 跳过, 即捷径可走)
- tile 有 objectgroup -> 其矩形/多边形栅格化到 256x256 子网格(相对 tile)
- tile covers_everything + 全矩形碰撞 -> 整格不可走
- 结果 H*256 x W*256 世界栅格 -> 缩放到 300x300 二值图
"""
import json, gzip, base64, io, sys
import numpy as np
import cv2

BASE = r"C:\Users\intel\Downloads\florr-auto-pathing-main"

def load_tile_collision(ts_path):
    ts = json.load(open(ts_path, encoding="utf-8"))
    tile_info = {}
    for t in ts.get("tiles", []):
        tid = t["id"]
        og = t.get("objectgroup")
        rects, polys = [], []
        if og:
            for o in og.get("objects", []):
                pts = []
                if "polygon" in o:
                    pts = [(p["x"] + o.get("x", 0), p["y"] + o.get("y", 0)) for p in o["polygon"]]
                    polys.append(pts)
                elif "polyline" in o:
                    pts = [(p["x"] + o.get("x", 0), p["y"] + o.get("y", 0)) for p in o["polyline"]]
                    polys.append(pts)
                elif o.get("width") and o.get("height"):
                    rects.append((o["x"], o["y"], o["x"] + o["width"], o["y"] + o["height"]))
        tile_info[tid] = (rects, polys)
    return tile_info

FLIP_H = 0x80000000
FLIP_V = 0x40000000
FLIP_D = 0x20000000
ROT_H  = 0x10000000
ID_MASK = 0x0FFFFFFF  # 低 28 位是 tile id

def decode_layer(layer, w, h):
    raw = base64.b64decode(layer["data"])
    arr = np.frombuffer(gzip.decompress(raw), dtype=np.uint32).astype(np.int64)
    return arr.reshape(h, w)  # 行主序 [row, col]

def transform_flip(px, py, fl):
    """Tiled 翻转变换: 先对角(swap), 再水平(x=256-x), 再垂直(y=256-y)"""
    if fl & FLIP_D:
        px, py = py, px
    if fl & FLIP_H:
        px = 256 - px
    if fl & FLIP_V:
        py = 256 - py
    return px, py

def rasterize_objects(rects, polys, flags=0):
    """把 tile 内对象画到 256x256 掩码, 返回 0/1(1=墙); flags 为 gid 翻转标志"""
    mask = np.zeros((256, 256), dtype=np.uint8)
    allp = []
    for x0, y0, x1, y1 in rects:
        allp.append([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    allp.extend(polys)
    for pts in allp:
        arr = np.array([transform_flip(x, y, flags) for x, y in pts], dtype=np.float32)
        arr[:, 0] = np.clip(arr[:, 0], 0, 256)
        arr[:, 1] = np.clip(arr[:, 1], 0, 256)
        if len(arr) >= 3:
            cv2.fillPoly(mask, [arr.astype(np.int32)], 1)
    return mask

def tmj_to_binary(tmj_path, ts_path, out_path, out_size=300):
    d = json.load(open(tmj_path, encoding="utf-8"))
    W, H = d["width"], d["height"]
    tile_info = load_tile_collision(ts_path)
    firstgid = d["tilesets"][0].get("firstgid", 1)
    wall = np.zeros((H * 256, W * 256), dtype=np.uint8)
    for layer in d.get("layers", []):
        if layer.get("type") != "tilelayer" or "data" not in layer:
            # objectgroup 层: 只处理显式 'collision' 层(世界坐标矩形/多边形)
            if layer.get("type") == "objectgroup" and layer.get("name") == "collision":
                for o in layer.get("objects", []):
                    x, y = o.get("x", 0), o.get("y", 0)
                    w, h = o.get("width", 0), o.get("height", 0)
                    if w <= 0 or h <= 0:
                        continue
                    # 世界坐标 -> 子像素: 世界 = tile*512, 子像素 = tile*256
                    sx0, sy0 = int(x * 0.5), int(y * 0.5)
                    sx1, sy1 = int((x + w) * 0.5), int((y + h) * 0.5)
                    sx0 = max(0, min(wall.shape[1], sx0)); sx1 = max(0, min(wall.shape[1], sx1))
                    sy0 = max(0, min(wall.shape[0], sy0)); sy1 = max(0, min(wall.shape[0], sy1))
                    if sx1 > sx0 and sy1 > sy0:
                        wall[sy0:sy1, sx0:sx1] = 1
                print(f"  [obj] layer 'collision': 显式碰撞矩形已栅格化")
            continue
        name = layer.get("name", "")
        # shortcut 层 collisions=false -> 清除该区域的墙(捷径可走, 覆盖下面的碰撞层)
        props = {p.get("name"): p.get("value") for p in layer.get("properties", [])}
        if props.get("collisions") is False:
            grid = decode_layer(layer, W, H)
            n_clear = 0
            for ty in range(H):
                for tx in range(W):
                    if grid[ty, tx] != 0:
                        block = wall[ty*256:(ty+1)*256, tx*256:(tx+1)*256]
                        n_clear += int(block.sum())
                        block[:] = 0
            print(f"  [shortcut] layer '{name}': 清除墙像素={n_clear}")
            continue
        grid = decode_layer(layer, W, H)
        n_tiles = int((grid != 0).sum())
        if n_tiles == 0:
            print(f"  [empty] layer '{name}'")
            continue
        n_wall = 0
        for ty in range(H):
            for tx in range(W):
                gid = grid[ty, tx]
                if gid == 0:
                    continue
                flags = gid & (FLIP_H | FLIP_V | FLIP_D)
                tid = (gid & ID_MASK) - firstgid  # 去掉翻转标志
                if tid < 0 or tid not in tile_info:
                    continue
                rects, polys = tile_info[tid]
                if not rects and not polys:
                    continue  # 无碰撞装饰/地面
                sub = rasterize_objects(rects, polys, flags)
                if sub.all():
                    n_wall += 1
                wall[ty*256:(ty+1)*256, tx*256:(tx+1)*256] |= sub
        print(f"  layer '{name}': tiles={n_tiles} wall_tiles={n_wall}")
    # 缩放到 300x300: 多数投票(每个输出像素 = 对应输入块的多数), 最接近游戏小地图采样
    img = (255 - wall * 255).astype(np.uint8)  # 255=可走 0=墙
    H_in, W_in = img.shape
    rows = (np.arange(out_size) * H_in // out_size)
    row_e = np.clip(rows + H_in // out_size + 1, 0, H_in)
    cols = (np.arange(out_size) * W_in // out_size)
    col_e = np.clip(cols + W_in // out_size + 1, 0, W_in)
    small = np.zeros((out_size, out_size), dtype=np.uint8)
    for i in range(out_size):
        block = img[rows[i]:row_e[i], :]
        # 每行取对应列块的均值
        for j in range(out_size):
            sub = block[:, cols[j]:col_e[j]]
            small[i, j] = 255 if sub.mean() > 0.5 else 0
    cv2.imwrite(out_path, small)
    return small

if __name__ == "__main__":
    ts = BASE + r"\tileset.tsj"
    for tmj, out in [(r"\ant_hell.tmj", r"\maps\anthell.png"), (r"\desert.tmj", r"\maps\desert.png")]:
        print("==>", tmj)
        img = tmj_to_binary(BASE + tmj, ts, BASE + out)
        print(f"    saved {out}: {img.shape}, walkable={int((img == 255).sum())}")
