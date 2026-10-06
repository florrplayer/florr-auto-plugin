# -*- coding: utf-8 -*-
import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
base = r'C:\Users\intel\Downloads\florr-auto-pathing-main\wasm_dump'
s = json.load(open(base + r'\wasm_struct.json', encoding='utf-8'))
print('=== 46 EXPORTS ===')
for nm, k, idx in s['exports']:
    print(f'  {k:6s} [{idx:5d}] {nm}')
