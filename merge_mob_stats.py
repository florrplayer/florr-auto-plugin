# -*- coding: utf-8 -*-
"""补全 mob_stats_full.json: florr_clone mobs.json(63怪官方属性) 补 wasm反汇编缺的怪
输出: data/mob_stats_v2.json (73+缺 = 全量怪属性表)"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, 'data')

stats = json.load(open(os.path.join(DATA, 'mob_stats_full.json'), encoding='utf-8'))
clone = json.load(open(os.path.join(DATA, 'florr_mobs_clone.json'), encoding='utf-8'))['mobs']

stats_map = {x['sid']: x for x in stats}
missing = [sid for sid in clone if sid not in stats_map]

MULT = {'common': 1, 'uncommon': 3, 'rare': 9, 'epic': 27, 'legendary': 81,
        'mythic': 243, 'ultra': 729, 'super': 2187, 'unique': 6561}
TIER_NAME = {'common': 'Common', 'uncommon': 'Unusual', 'rare': 'Rare', 'epic': 'Epic',
             'legendary': 'Legendary', 'mythic': 'Mythic', 'ultra': 'Ultra',
             'super': 'Super', 'unique': 'Unique'}

added = 0
for sid in missing:
    m = clone[sid]
    rarities = []
    for rar, hp in (m.get('hp_table') or {}).items():
        dmg = m.get('damage') or 0
        rarities.append({
            'rarity': TIER_NAME.get(rar, rar), 'exp': (m.get('xp') or {}).get(rar, 0),
            'HealthRange': [hp, hp], 'Damage': dmg, 'Armor': 1,
            'source': 'florr_clone'
        })
    if rarities:
        stats_map[sid] = {'sid': sid, 'rarities': rarities,
                          'drops': [], 'cn': m.get('cn'), 'source': 'florr_clone'}
        added += 1

# 排序并输出
merged = sorted(stats_map.values(), key=lambda x: x['sid'])
out_path = os.path.join(DATA, 'mob_stats_v2.json')
json.dump(merged, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('wasm反汇编原73怪 + clone补缺 %d 怪 = %d 怪' % (added, len(merged)))
print('新增:', sorted(missing))
print('已存:', out_path)
