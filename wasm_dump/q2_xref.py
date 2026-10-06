# -*- coding: utf-8 -*-
import json, io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
base = r'C:\Users\intel\Downloads\florr-auto-pathing-main\wasm_dump'
s = json.load(open(base + r'\wasm_struct.json', encoding='utf-8'))
xref = s['xref']

KEYS = ['ggro','Armor','Spawn','Bounce','Collision','Knockback','Movement','Speed',
        'Damage','Attack','Projectile','Bullet','Mob','Wander','Chase','Follow',
        'extra_spawn','force_','Petal/Attribute','Mob/','Health','Crit','crit',
        'Resist','Slow','Stun','Poison','Burn','Freeze','Size','Radius','Regen',
        'Desert','Scorpion','Centipede','Ant','Ghost','Assembler','Spike','Turret',
        'Spawner','Minion','Summon','Ranged','Melee','AI','ai_','Patrol','Target',
        'aggressive','passive','neutral','XP','Drop','Loot','Despawn','Lifetime',
        'AggroRange','AggroRangeMultiplier']

hits = {}
for st, funcs in xref.items():
    for k in KEYS:
        if k.lower() in st.lower():
            hits.setdefault(st, set()).update(funcs)
            break

print(f'strings with AI-ish keyword + xref func count: {len(hits)}')
for st in sorted(hits):
    fs = sorted(hits[st])
    if len(fs) <= 12:
        print(f'  [{len(fs):2d} funcs] {st!r:60s} -> {fs}')
    else:
        print(f'  [{len(fs):2d} funcs] {st!r:60s} -> {fs[:12]} ...')
