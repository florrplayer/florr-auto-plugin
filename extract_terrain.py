# -*- coding: utf-8 -*-
"""提取 florr_clone maps/*.tmj 地形层 -> data/florr_terrain.json
每图: 瓦片网格(108x108等) -> 不可通行标记(water层) + 桥(bridge层)
瓦片256单位, 中心=游戏坐标 (与memory模式一致)"""
import json, os, glob

BASE = os.path.dirname(os.path.abspath(__file__))
maps_dir = os.path.join(BASE, 'reference-florr-tools', 'florr_clone', 'maps')

out = {}
for tmj in glob.glob(os.path.join(maps_dir, '*.tmj')):
    name = os.path.splitext(os.path.basename(tmj))[0]
    d = json.load(open(tmj, encoding='utf-8'))
    w, h = d.get('width'), d.get('height')
    tw = d.get('tilewidth', 256)
    layers = {}
    for layer in d.get('layers', []):
        if layer.get('type') == 'tilelayer' and layer.get('data'):
            layers[layer.get('name')] = layer['data']
    # 水层瓦片 != 0 => 不可通行; bridge 层瓦片 != 0 => 桥上可通行
    water = layers.get('water') or []
    bridge = layers.get('bridge') or []
    wall_cells = []
    bridge_cells = []
    for idx, t in enumerate(water):
        if t and t > 0:
            tx, ty = idx % w, idx // w
            wall_cells.append([tx, ty])
    for idx, t in enumerate(bridge):
        if t and t > 0:
            tx, ty = idx % w, idx // w
            bridge_cells.append([tx, ty])
    out[name] = {
        'tile_size': tw, 'grid': [w, h],
        'water_cells': len(wall_cells), 'bridge_cells': len(bridge_cells),
        'water': wall_cells, 'bridge': bridge_cells,
    }
    print('%-12s %dx%d瓦片 water=%d格 bridge=%d格 水占比=%.0f%%' % (
        name, w, h, len(wall_cells), len(bridge_cells),
        100.0 * len(wall_cells) / (w * h)))

out_path = os.path.join(BASE, 'data', 'florr_terrain.json')
json.dump({'source': 'florr_clone maps/*.tmj 地形层(瓦片256单位=游戏坐标)',
           'maps': out}, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False)
print('已存:', out_path)
