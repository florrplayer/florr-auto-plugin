import re, json

with open('wasm_dump/client.wasm', 'rb') as f:
    data = f.read()

# 提取所有JSON片段(怪物定义)
# 找 "name":"xxx" 后面跟着数值的模式
strings = re.findall(rb'[\x20-\x7e]{10,}', data)
strings = [s.decode('ascii', errors='ignore') for s in strings]

# 找怪物定义(含hp/damage/speed的JSON)
mob_defs = []
for s in strings:
    if ('"hp"' in s or '"health"' in s or '"damage"' in s) and len(s) < 500:
        mob_defs.append(s)

print(f'=== 含hp/damage的定义 ({len(mob_defs)}个) ===')
for s in mob_defs[:50]:
    print(f'  {s[:200]}')

# 找所有怪物名
print('\n=== 所有怪物ID ===')
mob_ids = set()
for s in strings:
    # 匹配 "ant_soldier", "fire_ant_queen" 等
    m = re.findall(r'"([a-z_]+(?:ant|bee|beetle|scorpion|spider|worm|crab|jelly|shark|fish|eel|squid|moth|fly|ladybug|cactus|rock|sandstorm|spider|wasp|hornet|mantis|firefly|leafbug|termite|bush|shell|sponge|bubble|garbage|silverfish|titan|queen|soldier|worker|baby|egg|mummy|overmind))"', s)
    for x in m:
        mob_ids.add(x)

for m in sorted(mob_ids):
    print(f'  {m}')
