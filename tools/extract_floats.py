"""从wasm data段提取所有浮点数和字符串"""
import struct

with open('wasm_dump/client.wasm', 'rb') as f:
    data = f.read()

# 找data段
pos = 8
while pos < len(data):
    sec_id = data[pos]; pos += 1
    size = 0; shift = 0
    while True:
        b = data[pos]; pos += 1
        size |= (b & 0x7f) << shift
        if not (b & 0x80): break
        shift += 7
    if sec_id == 11:  # data
        data_start = pos
        data_end = pos + size
        print(f"data段: offset={data_start}, size={size} bytes")
        break
    pos += size

# 提取所有F64浮点数(怪物HP/伤害应该是F64)
print("\n=== 提取data段中的F64浮点数(可能的怪物数值) ===")
floats = []
for i in range(data_start, data_end - 8, 8):
    val = struct.unpack('<d', data[i:i+8])[0]
    # 过滤合理的游戏数值(0.001 ~ 1e10)
    if 0.001 < abs(val) < 1e10 and val == val:  # not NaN
        floats.append((i, val))

print(f"找到 {len(floats)} 个F64浮点数")
# 打印一些有趣的数值
interesting = [(off, v) for off, v in floats if 1 < v < 1e8]
print(f"其中 1~1e8 范围内的: {len(interesting)} 个")
for off, v in interesting[:30]:
    print(f"  offset 0x{off:06x}: {v:.4f}")

# 保存所有浮点数
with open('wasm_dump/wasm_floats.txt', 'w') as f:
    for off, v in floats:
        f.write(f"0x{off:06x}\t{v}\n")
print(f"\n已保存 wasm_floats.txt ({len(floats)}个数值)")
