# -*- coding: utf-8 -*-
import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
base = r'C:\Users\intel\Downloads\florr-auto-pathing-main\wasm_dump'
funcs = json.load(open(base + r'\all_func_consts.json', encoding='utf-8'))

print(f'total funcs: {len(funcs)}')
big = [f for f in funcs if len(f['f64']) >= 6]
print(f'funcs with >=6 f64: {len(big)}')
big.sort(key=lambda f: -len(f['f64']))
for f in big[:60]:
    fs = [round(x, 4) if abs(x) >= 1e-3 else x for x in f['f64']]
    print(f"  func[{f['id']:5d}] n={len(fs):2d} calls={f['calls'][:8]} f64={fs}")
