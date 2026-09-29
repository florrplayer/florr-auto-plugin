import re, json

with open('wasm_dump/client.wasm', 'rb') as f:
    data = f.read()

strings = re.findall(rb'[\x20-\x7e]{4,}', data)
strings = [s.decode('ascii', errors='ignore') for s in strings]

# 找花瓣相关
petal_data = {}
for s in strings:
    # 花瓣名: rose, dahlia, yucca, leaf, glass, etc
    if 'petal' in s.lower() and len(s) < 100:
        print(f'[PETAL] {s}')

# 找UI key
ui_keys = set()
for s in strings:
    if s.startswith('UI/') and len(s) < 60:
        ui_keys.add(s)

print(f'\n=== UI keys ({len(ui_keys)}个) ===')
for k in sorted(ui_keys)[:80]:
    print(f'  {k}')

# 找掉落表完整
print('\n=== 完整掉落表 ===')
for s in strings:
    if ';:' in s or (':' in s and ';' in s and len(s) < 200 and any(x in s for x in ['ant','bee','crab','spider','jelly','worm','beetle','cactus','ladybug','wasp','hornet','mantis','firefly','leafbug','termite','sandstorm','shell','sponge','bubble','garbage','silverfish','rock','bush'])):
        print(f'  {s}')
