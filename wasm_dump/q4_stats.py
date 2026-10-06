# -*- coding: utf-8 -*-
import json, io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
base = r'C:\Users\intel\Downloads\florr-auto-pathing-main\wasm_dump'
text = open(base + r'\all_strings.txt', encoding='utf-8', errors='replace').read()
lines = text.splitlines()

print('=== JSON stat keys present ===')
for k in ['"hp"','"damage"','"speed"','"armor"','"radius"','"aggro"','"knockback"','"xp"',
          '"health"','"movement"','"attack"','"defense"','"crit"','"range"','"cooldown"',
          '"projectile"','"pierce"','"bounce"','"mass"','"friction"','"accel"']:
    hits = [l for l in lines if k in l]
    print(f'  {k:14s}: {len(hits)} lines')

print('\n=== lines containing "hp" as key sample ===')
for l in lines:
    if '"hp"' in l:
        print(' ', l.strip()[:200])
