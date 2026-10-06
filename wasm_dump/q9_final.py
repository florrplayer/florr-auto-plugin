# -*- coding: utf-8 -*-
import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
base = r'C:\Users\intel\Downloads\florr-auto-pathing-main\wasm_dump'
s = json.load(open(base + r'\wasm_struct.json', encoding='utf-8'))
xref = s['xref']
funcs = json.load(open(base + r'\all_func_consts.json', encoding='utf-8'))
byid = {f['id']: f for f in funcs}

# which funcs reference aggro/armor/movement tooltip strings
for key in ['Petal/Attribute/MobAggroRange','Petal/Attribute/MovementSpeed',
            'Petal/Attribute/ArmorDebuff','Petal/Attribute/Bounces',
            'Petal/Attribute/CollisionDamageResistance','Petal/Attribute/FlowerKnockback',
            'Petals/bulb/Description','Mob Aggro Range:']:
    for st, fs in xref.items():
        if st.startswith(key):
            print(f'{st[:70]!r}\n    -> funcs {sorted(fs)[:8]}')

# strings referenced by the biggest constructors
print('\n=== strings referenced by big constructors ===')
str_by_func = {}
for st, fs in xref.items():
    for fi in fs:
        str_by_func.setdefault(fi, []).append(st)
for fid in [3552, 1641, 1603, 1597, 4247, 1596, 4330, 5341]:
    ss = str_by_func.get(fid, [])
    print(f'func[{fid}] refs strings: {ss[:15]}')
