# -*- coding: utf-8 -*-
"""深入分析：熵、37B帧、大帧结构"""
import json, os, struct, collections, math

DATA = os.path.dirname(os.path.abspath(__file__))
def load(name):
    with open(os.path.join(DATA, name), 'r', encoding='utf-8') as f:
        return json.load(f)

msgs = []
for name in ['recv_capture.json', 'recv_late.json']:
    for m in load(name):
        msgs.append((name, m.get('t'), m['d']))
snap = load('ws_state_snapshots.json')
for i, row in enumerate(snap):
    msgs.append(('snap', i, row))

def entropy(b):
    if not b: return 0
    c = collections.Counter(b)
    n = len(b)
    return -sum((v/n)*math.log2(v/n) for v in c.values())

# 37 字节帧
print("=== 37B 帧样本 (前5个) ===")
f37 = [m for m in msgs if len(m[2])==37]
for s,t,d in f37[:5]:
    print(f"  [{s} t={t}] {list(d)}")

# 46B 帧
print("\n=== 46B / 10B 帧 ===")
for s,t,d in msgs:
    if len(d) in (46,10):
        print(f"  len={len(d)} [{s} t={t}] {list(d)}")

# 熵分析
print("\n=== 帧熵 (按长度簇) ===")
ent_by_b0 = collections.defaultdict(list)
for s,t,d in msgs:
    if len(d)>50:
        ent_by_b0[d[0]].append((entropy(d), len(d), s, t))
for b0, lst in sorted(ent_by_b0.items()):
    ents = [e for e,_,_,_ in lst]
    print(f"  byte0=0x{b0:02X}: n={len(lst)} entropy min/mean/max = {min(ents):.2f}/{sum(ents)/len(ents):.2f}/{max(ents):.2f}")

# 1376B 全量帧
print("\n=== 1376B 帧 ===")
for s,t,d in msgs:
    if len(d)==1376:
        print(f"  src={s} t={t} byte0={d[0]}")
        print(f"  hex[:64]: {bytes(d[:64]).hex()}")
        print(f"  hex[64:128]: {bytes(d[64:128]).hex()}")

# 同 byte0 大帧逐字节对比（看是否有固定头）
print("\n=== 同 byte0=0x3B 大帧前16字节对比 (前5个) ===")
g = [m for m in msgs if m[2] and m[2][0]==0x3B and len(m[2])>100]
for s,t,d in g[:5]:
    print(f"  len={len(d)} t={t} head={list(d[:16])}")

# 检查大帧是否有重复的固定步长记录
print("\n=== 大帧内部字节自相关（找实体记录步长）===")
for s,t,d in g[:3]:
    L = len(d)
    print(f"  --- len={L} t={t} ---")
    # 统计相邻 4/8 字节对齐位置的重复模式太复杂，先看能不能整除
    for step in [4,8,16,20,24,28,32,36,40,44,48,52]:
        rem = (L-1) % step
        if rem == 0:
            print(f"    (len-1) % {step} == 0  -> 记录数 {(L-1)//step}")
