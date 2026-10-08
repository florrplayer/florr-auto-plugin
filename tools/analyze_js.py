import re

with open('wasm_dump/client.js', 'r', encoding='utf-8', errors='ignore') as f:
    js = f.read()

print(f"client.js 大小: {len(js)} chars")

# 找WebSocket相关
print("\n=== WebSocket/网络 ===")
for m in re.finditer(r'.{0,60}(websocket|WebSocket|wss?://|onmessage|onopen|binaryType|arraybuffer|blob).{0,60}', js, re.I):
    print(f"  {m.group()[:150]}")

# 找怪物相关
print("\n=== 怪物/HP/damage ===")
for m in re.finditer(r'.{0,40}(mob|enemy|hp|health|damage|spawn).{0,60}', js, re.I):
    s = m.group()
    if len(s) < 150:
        print(f"  {s}")

# 找聊天/消息
print("\n=== 聊天/消息 ===")
for m in re.finditer(r'.{0,30}(chat|message|recv|send|parse).{0,60}', js, re.I):
    s = m.group()
    if len(s) < 120 and 'function' in s.lower() or 'chat' in s.lower():
        print(f"  {s[:120]}")
