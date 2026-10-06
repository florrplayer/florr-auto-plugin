# -*- coding: utf-8 -*-
import json, io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
base = r'C:\Users\intel\Downloads\florr-auto-pathing-main\wasm_dump'
lines = open(base + r'\all_strings.txt', encoding='utf-8', errors='replace').read().splitlines()

# 1) spawn weight tables: "value":"a:1;b:0.5;..."
print('=== SPAWN WEIGHT TABLES ("value" with mob:x; syntax) ===')
spawn_tables = [l for l in lines if re.search(r'"value":"[a-z_]+:\d', l) and ';' in l]
for l in spawn_tables[:80]:
    print(' ', l.strip())
print(f'  ... total {len(spawn_tables)} spawn table strings')

# 2) mob internal names: lines like "name":"xxx" or bare known tokens
print('\n=== "name":"..." config keys (sample) ===')
names = sorted(set(re.findall(r'"name":"([^"]+)"', '\n'.join(lines))))
print(f'  {len(names)} distinct "name" values')
for n in names:
    print('   ', n)
