# -*- coding: utf-8 -*-
import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
base = r'C:\Users\intel\Downloads\florr-auto-pathing-main\wasm_dump'
funcs = json.load(open(base + r'\all_func_consts.json', encoding='utf-8'))
byid = {f['id']: f for f in funcs}

print('=== core utility funcs (called everywhere) ===')
for fid in [32,33,34,55,65,361,362,363,364,365,366,367,368,369,371,372,373,375,376,378,385,402,415,425,433]:
    f = byid.get(fid)
    if not f: continue
    fs = [round(x,6) if abs(x)>=1e-4 else x for x in f['f64'][:14]]
    print(f"  func[{fid:4d}] f64={fs} calls={f['calls'][:10]}")

# who calls Util_GetMobs (hg global 5672 -> internal 5311) and Util_GenerateMobImage (gg 5674 -> internal 5313)?
print('\n=== callers of exported internal funcs ===')
for target in [5311, 5313]:
    callers = [f['id'] for f in funcs if target in f['calls']]
    print(f'  func[{target}] called by: {callers[:20]}')

# functions with moderate f64 values typical of aggro/movement ranges (100..2000)
print('\n=== f64 constants in 150..1500 range histogram (constructor-ish) ===')
from collections import Counter
c = Counter()
for f in funcs:
    for x in f['f64']:
        if 150 <= x <= 1500 and x == int(x) or 150 <= x <= 1500:
            c[round(x)] += 1
for v, n in c.most_common(30):
    print(f'  {v:8.1f}  x{n}')
