import re

with open('wasm_dump/client.wasm', 'rb') as f:
    data = f.read()

strings = re.findall(rb'[\x20-\x7e]{3,}', data)
strings = [s.decode('ascii', errors='ignore') for s in strings]

# 找 ygg, mark, death, revive, spawn 相关
print("=== ygg/mark/death/revive ===")
for s in strings:
    sl = s.lower()
    if any(k in sl for k in ['ygg', 'mark', 'revive', 'death', 'dead', 'respawn', 'corpse', 'graveyard', 'ghost']):
        if len(s) < 150:
            print(f"  {s}")

# 找聊天命令
print("\n=== 聊天/命令 ===")
for s in strings:
    if s.startswith('/') and len(s) < 60:
        print(f"  {s}")

# 找出生点/spawn点
print("\n=== spawn点 ===")
for s in strings:
    if 'spawn' in s.lower() and len(s) < 80 and ('point' in s.lower() or 'location' in s.lower() or 'pos' in s.lower() or 'zone' in s.lower()):
        print(f"  {s}")
