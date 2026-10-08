# -*- coding: utf-8 -*-
"""v1.23.1: 提取 florr_clone src/mobs.json 全字段(含AI配置: aggro range/web/stinger/volley/poison/evasion)
-> data/florr_mobs_ai.json (63怪完整AI参数)"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(BASE, 'reference-florr-tools', 'florr_clone', 'src', 'mobs.json')
d = json.load(open(p, encoding='utf-8'))

AI_FIELDS = ['ai_type', 'range', 'speed', 'cruiseSpeed', 'chaseSpeed', 'cooldown',
             'web', 'stinger', 'projectile', 'dropProjectile', 'poison', 'poisonDuration',
             'lightning', 'petal_ring', 'evasion', 'armor', 'groups', 'spawn_weight',
             'periodic_spawn', 'spawn_waves', 'initial_spawns', 'min_rarity', 'npc',
             'hole', 'no_mob_collision', 'reversed', 'hideRotation', 'bee_ai', 'gardn_ai']

out = {}
for sid, m in d.items():
    out[sid] = {k: m.get(k) for k in AI_FIELDS if k in m}
    out[sid]['name'] = m.get('name')

out_path = os.path.join(BASE, 'data', 'florr_mobs_ai.json')
json.dump({'source': 'florr_clone src/mobs.json (63怪全AI配置)',
           'mobs': out}, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('怪数:', len(out))
# 有AI机制字段的怪统计
for k in ['web', 'stinger', 'projectile', 'poison', 'lightning', 'petal_ring', 'evasion', 'range']:
    n = sum(1 for m in out.values() if m.get(k))
    print('  %-12s: %d 怪' % (k, n))
print('已存:', out_path)
