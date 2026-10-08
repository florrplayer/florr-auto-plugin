# -*- coding: utf-8 -*-
"""提取 florr_clone map_bundle.ts 的传送门表 -> data/florr_portals.json (括号计数版)"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(BASE, 'reference-florr-tools', 'florr_clone', 'src', 'map_bundle.ts')
src = open(p, encoding='utf-8').read()

def parse_balanced(start):
    """从 src[start]('{') 开始括号计数解析一个JSON对象, 返回(obj, end_index)"""
    depth = 0
    in_str = False
    esc = False
    for k in range(start, len(src)):
        c = src[k]
        if in_str:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return json.loads(src[start:k+1]), k + 1
    return None, len(src)

portals = []
idx = 0
marker = '"type": "teleporter"'
while True:
    i = src.find(marker, idx)
    if i < 0:
        break
    start = src.rfind('{', 0, i)
    obj, end = parse_balanced(start)
    if obj and obj.get('type') == 'teleporter':
        props = obj.get('properties', {})
        tt = props.get('teleportTo')
        portals.append({
            'x': round(obj.get('x', 0)), 'y': round(obj.get('y', 0)),
            'targetMap': props.get('targetMap'),
            'targetSpawn': props.get('targetSpawn'),
            'to': [round(tt['x']), round(tt['y'])] if tt else None,
        })
    idx = end

print('传送门总数:', len(portals))
for pt in portals:
    print(pt)

out = os.path.join(BASE, 'data', 'florr_portals.json')
json.dump({'source': 'florr_clone map_bundle.ts (世界坐标=插件memory模式坐标系)',
           'portals': portals}, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('已存:', out)
