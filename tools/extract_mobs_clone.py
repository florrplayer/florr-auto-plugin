# -*- coding: utf-8 -*-
"""提取 florr_clone src/mobs.json (63怪官方属性) -> data/florr_mobs_clone.json
含: damage/health/size/speed/cooldown/xp表/visual_scale/color
用途: 对照 mob_db (碰撞箱/血量档位/追击速度/威胁伤害) 补缺口"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(BASE, 'reference-florr-tools', 'florr_clone', 'src', 'mobs.json')
d = json.load(open(p, encoding='utf-8'))

# 稀有度倍率 (官方: 每档 x3, Common=1)
MULT = {'common': 1, 'uncommon': 3, 'rare': 9, 'epic': 27, 'legendary': 81,
        'mythic': 243, 'ultra': 729, 'super': 2187, 'unique': 6561}

out = {}
for sid, m in d.items():
    hp = m.get('health', 0)
    hp_table = {}
    for rar, xp in (m.get('xp') or {}).items():
        # 血量 = health x 稀有度倍率 (与xp同缩放)
        hp_table[rar] = round(hp * MULT.get(rar, 1))
    out[sid] = {
        'cn': m.get('name'), 'damage': m.get('damage'), 'health': m.get('health'),
        'size': m.get('size'), 'speed': m.get('speed'), 'cooldown': m.get('cooldown'),
        'visual_scale': m.get('visual_scale'), 'color': m.get('color'),
        'hp_table': hp_table, 'xp': m.get('xp'),
    }

out_path = os.path.join(BASE, 'data', 'florr_mobs_clone.json')
json.dump({'source': 'florr_clone src/mobs.json (63怪)',
           'mobs': out}, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('怪数:', len(out))
for sid in ['bee', 'rock', 'scorpion', 'jellyfish', 'shiny_ladybug', 'square', 'hornet']:
    m = out.get(sid)
    if m:
        print('%-16s 伤害=%-4s 血=%-4s size=%-3s 速=%-4s 冷却=%s' % (
            sid, m['damage'], m['health'], m['size'], m['speed'], m['cooldown']))
        print('   hp表:', m['hp_table'])
print('已存:', out_path)
