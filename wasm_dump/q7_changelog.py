# -*- coding: utf-8 -*-
import io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
base = r'C:\Users\intel\Downloads\florr-auto-pathing-main\wasm_dump'
lines = open(base + r'\all_strings.txt', encoding='utf-8', errors='replace').read().splitlines()

chg = [l.strip() for l in lines if l.strip().startswith('- ') or l.strip().startswith('* ')]
print(f'changelog-ish lines: {len(chg)}')
KW = ['mob','Mob','aggro','Aggro','spawn','Spawn','damage','Damage','armor','Armor',
      'speed','Speed','knockback','collision','bullet','projectile','boss','AI',
      'desert','ant','scorpion','centipede','wasp','hornet','bee','ladybug','spider',
      'crab','jelly','leech','starfish','worm','ghost','assembler','gambler','titan',
      'termite','mantis','firefly','mecha','hel','ocean','jungle','sewer','poison',
      'stun','slow','debuff','ranged','melee','charge','dash','bounce','pierce',
      'crit','health','HP','hp','xp','XP','rarity','density','lag','tick']
seen = set()
for l in chg:
    if any(k in l for k in KW) and l not in seen:
        seen.add(l)
        print(' ', l[:200])
