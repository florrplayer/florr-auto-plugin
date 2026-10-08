# -*- coding: utf-8 -*-
"""提取 florr_clone maps/*.tmj 的刷怪区域(zone) + 出生点 + NPC -> data/florr_zones.json"""
import json, os, glob

BASE = os.path.dirname(os.path.abspath(__file__))
maps_dir = os.path.join(BASE, 'reference-florr-tools', 'florr_clone', 'maps')

out = {}
for tmj in glob.glob(os.path.join(maps_dir, '*.tmj')):
    name = os.path.splitext(os.path.basename(tmj))[0]
    d = json.load(open(tmj, encoding='utf-8'))
    zones, spawns, npcs = [], [], []
    for layer in d.get('layers', []):
        for o in layer.get('objects', []) or []:
            props = {p['name']: p.get('value') for p in o.get('properties', []) or []}
            rec = {'x': round(o.get('x', 0)), 'y': round(o.get('y', 0)),
                   'w': round(o.get('width', 0)), 'h': round(o.get('height', 0)),
                   'name': o.get('name', '')}
            if layer.get('name') == 'spawns':
                rec['difficulty'] = props.get('difficulty')
                rec['mobs'] = props.get('mobs')
                zones.append(rec)
            elif layer.get('name') == 'player_spawns':
                rec['biome'] = props.get('biome')
                rec['label'] = props.get('label')
                spawns.append(rec)
            elif layer.get('name') == 'npcs':
                rec['npc'] = props.get('npc')
                rec['rarity'] = props.get('rarity')
                npcs.append(rec)
    out[name] = {'size': [d.get('width'), d.get('height')],
                 'zones': zones, 'spawns': spawns, 'npcs': npcs}
    print('===', name, '| zones:', len(zones), '| spawns:', len(spawns), '| npcs:', len(npcs))
    for z in zones[:8]:
        print('   zone %s diff=%s at(%d,%d) mobs=%s' % (z['name'], z['difficulty'], z['x'], z['y'], z['mobs']))

out_path = os.path.join(BASE, 'data', 'florr_zones.json')
json.dump({'source': 'florr_clone maps/*.tmj (坐标=游戏单位, 与memory模式一致)', 'maps': out},
          open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('已存:', out_path)
