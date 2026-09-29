# -*- coding: utf-8 -*-
"""深入分析低熵channel消息"""
import json

with open(r"C:\Users\intel\Downloads\florr-auto-pathing-main\data\ws_state_snapshots.json","r") as f:
    snaps = json.load(f)

# 看低熵channel的完整内容
for ch in [22, 66, 48]:
    group = [s for s in snaps if s[0] == ch]
    print(f"\n=== Channel {ch} ({len(group)}条, 完整hex) ===")
    for i, s in enumerate(group[:3]):
        hexstr = ' '.join(f'{b:02x}' for b in s[:40])
        print(f"  消息{i} ({len(s)}字节): {hexstr}")
        # 尝试ASCII
        asc = ''.join(chr(b) if 32<=b<127 else '.' for b in s[:40])
        print(f"    ASCII: {asc}")

# 对比同一channel的两条消息，找XOR密钥
print("\n=== Channel 59 XOR分析 ===")
ch59 = [s for s in snaps if s[0] == 59]
if len(ch59) >= 2:
    s1, s2 = ch59[0], ch59[1]
    minlen = min(len(s1), len(s2))
    xor = [s1[i] ^ s2[i] for i in range(minlen)]
    print(f"  XOR of msg0 ^ msg1 (first 40 bytes):")
    print(f"  {' '.join(f'{b:02x}' for b in xor[:40])}")
    # 找重复模式
    print(f"  字节频率: ", end="")
    from collections import Counter
    c = Counter(xor)
    print(c.most_common(10))

# Channel 73 XOR分析
print("\n=== Channel 73 XOR分析 ===")
ch73 = [s for s in snaps if s[0] == 73]
if len(ch73) >= 2:
    s1, s2 = ch73[0], ch73[1]
    minlen = min(len(s1), len(s2))
    xor = [s1[i] ^ s2[i] for i in range(minlen)]
    print(f"  XOR first 40: {' '.join(f'{b:02x}' for b in xor[:40])}")
    # 如果XOR结果有0x00，说明相同位置数据没变
    zeros = xor.count(0)
    print(f"  0x00字节数: {zeros}/{minlen}")
