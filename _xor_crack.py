# -*- coding: utf-8 -*-
"""破解WebSocket XOR加密"""
import json

with open(r"C:\Users\intel\Downloads\florr-auto-pathing-main\data\ws_state_snapshots.json","r") as f:
    snaps = json.load(f)

# Channel 59 - 收集所有消息
ch59 = [s for s in snaps if s[0] == 59]
print(f"Channel 59: {len(ch59)}条")

# 如果XOR密钥周期为N，那么msg0[i]^msg1[i] = data0[i]^data1[i]
# 对同一位置i%N，多条消息的XOR结果应该有共同特征
# 尝试不同周期
for period in [4, 6, 7, 8, 10, 12, 14, 16]:
    # 对每个周期位置，统计XOR结果
    xor_at_pos = [[] for _ in range(period)]
    for i in range(len(ch59)-1):
        a, b = ch59[i], ch59[i+1]
        minlen = min(len(a), len(b))
        for j in range(1, minlen):  # 跳过channel字节
            xor_at_pos[j % period].append(a[j] ^ b[j])
    
    # 对每个位置，找最常见的XOR值
    # 如果最常见值是0x00，说明这个位置数据通常不变
    score = 0
    for pos in range(period):
        if xor_at_pos[pos]:
            from collections import Counter
            c = Counter(xor_at_pos[pos])
            top = c.most_common(1)[0]
            if top[0] == 0:
                score += top[1]
    
    total = sum(len(x) for x in xor_at_pos)
    print(f"  周期{period}: 0x00出现率={score}/{total}={score/total*100:.1f}%")

# 试试周期8，推导密钥
# 如果假设很多位置数据是0x00（没变化），那么msg[i] ^ key[i%8] = 0
# 即 key[i%8] = msg[i]
print("\n=== 尝试周期8密钥推导 ===")
period = 8
# 收集所有消息在每个周期位置的值
vals_at_pos = [[] for _ in range(period)]
for s in ch59:
    for j in range(1, min(len(s), 200)):
        vals_at_pos[j % period].append(s[j])

# 对每个位置，找最常见的值（可能是XOR密钥的一部分）
for pos in range(period):
    from collections import Counter
    c = Counter(vals_at_pos[pos])
    top5 = c.most_common(5)
    print(f"  位置{pos}: top5={top5}")
