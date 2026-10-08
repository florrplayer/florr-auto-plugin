# -*- coding: utf-8 -*-
"""提取 florr_clone mob_drops.json -> data/florr_clone_drops.json (规范格式)
格式: {怪sid: {花瓣sid: {稀有度: 概率}}} (概率为掉落期望/聚合值)"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(BASE, 'reference-florr-tools', 'florr_clone', 'src', 'mob_drops.json')
d = json.load(open(p, encoding='utf-8'))

out = {}
for mob, v in d.items():
    agg = {}
    for dr in v.get('drops', []):
        petal = dr.get('itemType')
        rar = dr.get('rarity', 'common')
        prob = dr.get('probability', 0)
        agg.setdefault(petal, {})[rar] = prob
    out[mob] = {'guaranteed': v.get('guaranteed', False), 'drops': agg}

out_path = os.path.join(BASE, 'data', 'florr_clone_drops.json')
json.dump({'source': 'florr_clone src/mob_drops.json (53怪)',
           'mobs': out}, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

print('怪数:', len(out))
for mob in sorted(out.keys()):
    petals = len(out[mob]['drops'])
    print('  %-22s %d种掉落' % (mob, petals))
print('已存:', out_path)
