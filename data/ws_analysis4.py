# -*- coding: utf-8 -*-
"""Kasiski / 重合指数找 XOR 周期；若周期短则逐列求最优 key 还原 f64"""
import json, os, struct, collections

DATA = os.path.dirname(os.path.abspath(__file__))
def load(name):
    with open(os.path.join(DATA, name), 'r', encoding='utf-8') as f:
        return json.load(f)

msgs = []
for name in ['recv_capture.json', 'recv_late.json']:
    for m in load(name):
        msgs.append(m['d'])
for row in load('ws_state_snapshots.json'):
    msgs.append(row)

big = [d for d in msgs if len(d)==1376][0]
payload = big[1:]  # 去掉 byte0
n = len(payload)

# 重合指数：对周期 P，把字节按 i%P 分列，列内 IC 应高（若明文有结构）
def ic(seq):
    if len(seq)<2: return 0
    c = collections.Counter(seq)
    N=len(seq)
    return sum(v*(v-1) for v in c.values())/(N*(N-1))

print("=== 周期候选的平均重合指数 IC ===")
for P in range(1, 65):
    cols = [payload[i::P] for i in range(P)]
    avg = sum(ic(c) for c in cols)/P
    if avg > 0.012:  # 随机文本IC~0.004；英文~0.066
        print(f"  P={P:3d}: avgIC={avg:.4f}")

# 也直接在多个大帧拼接后做（更多样本）
print("\n=== 用所有 >400B 帧拼接后 IC ===")
blob = b''
for d in msgs:
    if len(d)>400:
        blob += bytes(d[1:])
nb = len(blob)
bestP=[]
for P in range(1, 97):
    cols = [blob[i::P] for i in range(P)]
    avg = sum(ic(c) for c in cols)/P
    bestP.append((avg,P))
for avg,P in sorted(bestP, reverse=True)[:12]:
    print(f"  P={P:3d}: avgIC={avg:.4f}")
