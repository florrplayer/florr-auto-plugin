# -*- coding: utf-8 -*-
import json, io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
base = r'C:\Users\intel\Downloads\florr-auto-pathing-main\wasm_dump'
s = json.load(open(base + r'\wasm_struct.json', encoding='utf-8'))
xref = s['xref']
lines = open(base + r'\all_strings.txt', encoding='utf-8', errors='replace').read().splitlines()

# 1) all i18n mob keys
mob_keys = sorted(set(re.findall(r'Mobs/([a-z_0-9]+)/[A-Za-z]+', '\n'.join(lines))))
print('=== distinct mobs referenced by i18n keys:', len(mob_keys))
print(mob_keys)

# 2) xref of mob-name strings (bare lowercase tokens)
print('\n=== bare mob-name strings in xref (functions referencing them) ===')
want = set(mob_keys) | {'assembler','gambler','titan','ghost','overmind','sandstorm',
                        'fire_ant_queen','termite_overmind','mecha_flower'}
for st, fs in sorted(xref.items()):
    # exact-ish match: string is a bare mob token
    if re.fullmatch(r'[a-z_0-9]+', st) and st in want:
        print(f'  {st:24s} -> {sorted(fs)[:10]}')

# 3) strings describing behavior
print('\n=== behavior-ish strings ===')
for kw in ['Wander','wander','chase','Chase','flee','Flee','aggressive','passive',
           'shoot','Shoot','melee','Melee','orbit','patrol','wander','despawn',
           'lifetime','spawn_delay','tick','Tick','update','Update','aggro','Aggro']:
    hits = [l.strip() for l in lines if kw in l]
    hits = [h for h in hits if 4 < len(h) < 120]
    if hits:
        print(f'-- {kw}: {hits[:6]}')
