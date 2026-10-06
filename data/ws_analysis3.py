# -*- coding: utf-8 -*-
"""检测 XOR 混淆 / 流密码：在 1376B 全量帧上找 f64 结构"""
import json, os, struct, collections

DATA = os.path.dirname(os.path.abspath(__file__))
def load(name):
    with open(os.path.join(DATA, name), 'r', encoding='utf-8') as f:
        return json.load(f)

msgs = []
for name in ['recv_capture.json', 'recv_late.json']:
    for m in load(name):
        msgs.append((name, m.get('t'), m['d']))
for i, row in enumerate(load('ws_state_snapshots.json')):
    msgs.append(('snap', i, row))

big = [m for m in msgs if len(m[2])==1376][0]
d = big[2]
print("1376 frame, byte0 =", d[0], "len", len(d))

# 假设：去掉 byte0 后，payload 是 XOR 加密的 f64 序列。
# f64 小端：正数坐标在 [1, 2048) 时，第7字节(offset+7) 通常为 0x3F/0x40/0x41/0x42/0x43。
# 试：对 payload 整体 XOR 单字节 k，统计每个 8 字节对齐处 offset7 落在 {0x3F..0x43} 的数量。
payload = d[1:]
def score_xor(k, align=0):
    cnt = 0
    for i in range(align, len(payload)-7, 8):
        b7 = payload[i+7] ^ k
        if 0x3F <= b7 <= 0x43:
            cnt += 1
    return cnt

print("\n=== 单字节 XOR，payload 按 8B 对齐，offset7=符号/指数高位 ===")
best = sorted(range(256), key=lambda k:-score_xor(k))[:8]
for k in best:
    print(f"  k=0x{k:02X}: score={score_xor(k)}")

# 也试 offset6（f64 第二高字节）
def score_xor6(k, align=0):
    cnt=0
    for i in range(align, len(payload)-7, 8):
        b6 = payload[i+6] ^ k
        # 指数第二字节：0x00..0x1F 常见
        if b6 < 0x20:
            cnt+=1
    return cnt
print("\n=== 单字节 XOR，offset6 高字节 <0x20 计数 ===")
best6 = sorted(range(256), key=lambda k:-score_xor6(k))[:8]
for k in best6:
    print(f"  k=0x{k:02X}: score={score_xor6(k)}")

# 也许是逐字节位置密钥（周期 P）。先看不同对齐 offset 下原始字节分布
print("\n=== payload 各 8B 位置上的字节取值分布 (找恒定高字节) ===")
for pos in range(8):
    vals = collections.Counter(payload[i+pos] for i in range(0, len(payload)-7, 8))
    common = vals.most_common(3)
    print(f"  pos{pos}: top={[(hex(v),c) for v,c in common]}")
