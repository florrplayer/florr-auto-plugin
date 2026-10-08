# -*- coding: utf-8 -*-
"""提取 florr_clone src/map_bundle.ts MAP_ELEMENTS (刷怪区/传送门/地图瓦片)
-> data/florr_map_bundle.json 对照已有 florr_zones.json/florr_portals.json"""
import json, os, re

BASE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(BASE, 'reference-florr-tools', 'florr_clone', 'src', 'map_bundle.ts')
src = open(p, encoding='utf-8').read()

# 切出 MAP_ELEMENTS 数组
m = re.search(r'export const MAP_ELEMENTS: MapElement\[\] = (\[.*?\]);', src, re.S)
if not m:
    raise SystemExit('MAP_ELEMENTS not found')
arr_txt = m.group(1)

# 逐对象解析 ({} 内属性名带引号, 转成dict)
objs = []
depth = 0
cur = ''
in_str = False
for ch in arr_txt:
    if ch == '"' and not in_str:
        in_str = True; cur += ch; continue
    if ch == '"' and in_str:
        in_str = False; cur += ch; continue
    if in_str:
        cur += ch; continue
    if ch == '{':
        depth += 1
        if depth == 1:
            cur = '{'
            continue
    if ch == '}':
        depth -= 1
        if depth == 0:
            cur += '}'
            objs.append(cur)
            cur = ''
            continue
    if depth >= 1:
        cur += ch

# 转JSON (属性名引号已带, 值转类型)
def parse_obj(txt):
    txt = re.sub(r'//.*', '', txt)
    try:
        return json.loads(txt)
    except Exception:
        return None

elements = []
for t in objs:
    o = parse_obj(t)
    if o:
        elements.append(o)

print('地图元素总数:', len(elements))
types = {}
for e in elements:
    types[e.get('type')] = types.get(e.get('type'), 0) + 1
print('类型分布:', types)

out_path = os.path.join(BASE, 'data', 'florr_map_bundle.json')
json.dump({'source': 'florr_clone src/map_bundle.ts (200x200瓦片=40000格, 8bit/格)',
           'elements': elements}, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)

# 对照已有 zones
try:
    zones = json.load(open(os.path.join(BASE, 'data', 'florr_zones.json'), encoding='utf-8'))
    zn = zones.get('zones', zones) if isinstance(zones, dict) else zones
    print('已有 zones 数:', len(zn) if hasattr(zn, '__len__') else '?')
except Exception as e:
    print('zones对照失败:', e)
print('已存:', out_path)
