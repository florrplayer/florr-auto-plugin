# -*- coding: utf-8 -*-
"""dropchance_v2 完整性核对 + mob_db.drop_rates 接口一致性验证
结论口径: 私服drop_rate.h=静态wiki表(真源), gardn=旧版公式(机制参考, 数值已过期)
"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mob_db

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'florr_dropchance_v2.json')
d = json.load(open(DATA, encoding='utf-8'))

print('=== 1. 数据规模 ===')
mobs = list(d.keys())
print('怪数:', len(mobs), mobs)
tiers = set()
entries = 0
for m, t in d.items():
    tiers.update(t.keys())
    for k, v in t.items():
        entries += len(v)
print('稀有度档数:', len(tiers), sorted(tiers))
print('掉落条目总数:', entries)

print('\n=== 2. 完整性: 同一花瓣各档概率聚合 ≤1.0? (每花瓣独立roll机制) ===')
bad = 0
petal_agg = {}
for m, t in d.items():
    for tier, drops in t.items():
        for x in drops:
            key = (m, x['petal'])
            petal_agg.setdefault(key, []).append((tier, x['rate']))
for (m, petal), rates in petal_agg.items():
    for tier, rate in rates:
        if rate > 1.0001:
            bad += 1
            print('  [单条超1] %s/%s rate=%.4f' % (m, petal, rate))
print('单条越界数:', bad, '(0=每花瓣独立roll, 聚合>1正常=期望掉落数)')

print('\n=== 2b. 每档期望掉落花瓣数(聚合值, 供drop_value校准) ===')
for m in ['ant_soldier', 'rock', 'bee', 'ladybug']:
    for tier in ['Common', 'Unusual', 'Rare', 'Legendary', 'Mythic', 'Ultra']:
        drops = d[m].get(tier, [])
        s = sum(x['rate'] for x in drops)
        print('  %-12s %-10s 期望掉落=%.2f (%d种花瓣)' % (m, tier, s, len(drops)))

print('\n=== 3. rate 范围 ===')
bad2 = [x['rate'] for m, t in d.items() for k, v in t.items() for x in v if not (0 < x['rate'] <= 1)]
print('越界条目:', len(bad2))

print('\n=== 4. mob_db.drop_rates() 接口一致性 ===')
from mob_db import drop_rates, drop_hint
sample = ['ant_soldier', 'ladybug', 'scorpion', 'square']
for s in sample:
    r = drop_rates(s)
    h = drop_hint(s, 'Mythic')
    print('  %-12s drop_rates=%s | hint=%s' % (s, len(r) if isinstance(r, list) else r, str(h)[:60]))

print('\n=== 5. mob_db 里 drop_rates 返回的怪名是否都在 v2 表 ===')
all_sids = set(mobs)
missing = [s for s in mob_db.TYPE_ID_TO_SID.values() if s not in all_sids and s not in ('none',)]
print('mob_db 83怪中不在 v2 掉率表的:', len(missing), missing[:15])

print('\n=== 6. 数值抽样(与 wiki 静态表核对 ant_soldier Common) ===')
for x in d['ant_soldier']['Common']:
    print('  ant_soldier/Common -> %s(%s) rate=%.4f' % (x['petal'], x['rarity'], x['rate']))
print('  说明: 0.333+0.667=1.0(glass 2档拆), 0.125+0.875=1.0(wing 2档拆) —— 每花瓣按稀有度档拆分')
