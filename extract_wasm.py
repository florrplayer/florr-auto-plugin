import re, json

with open('wasm_dump/client.wasm', 'rb') as f:
    data = f.read()

strings = re.findall(rb'[\x20-\x7e]{4,}', data)
strings = [s.decode('ascii', errors='ignore') for s in strings]

# 找所有传送门/坐标相关
print("=== 传送门/坐标 ===")
for s in strings:
    if ('portal' in s.lower() or 'teleport' in s.lower() or 'spawn' in s.lower() or 'warp' in s.lower()) and len(s) < 100:
        print(f"  {s}")

# 找所有配置/常量
print("\n=== 配置常量 ===")
for s in strings:
    if re.match(r'^[a-z_]+_[a-z_]+$', s) and any(k in s for k in ['speed','health','damage','radius','size','range','time','count','max','min','rate','cost','cd','cooldown']):
        print(f"  {s}")

# 找聊天命令
print("\n=== 聊天命令 ===")
for s in strings:
    if s.startswith('/') and len(s) < 50:
        print(f"  {s}")

# 找所有物品/掉落
print("\n=== 物品/drops ===")
for s in strings:
    if 'drop' in s.lower() and len(s) < 100 and 'Petal' not in s:
        print(f"  {s}")
