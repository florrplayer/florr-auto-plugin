# -*- coding: utf-8 -*-
"""florr.io WS recv 消息逆向分析脚本"""
import json, os, struct, collections, math

DATA = os.path.dirname(os.path.abspath(__file__))

def load(name):
    with open(os.path.join(DATA, name), 'r', encoding='utf-8') as f:
        return json.load(f)

# ---------- 载入所有消息 ----------
msgs = []  # (source, t_or_idx, bytes list)
for name in ['recv_capture.json', 'recv_late.json']:
    d = load(name)
    for m in d:
        msgs.append((name, m.get('t'), m['d']))

snap = load('ws_state_snapshots.json')
for i, row in enumerate(snap):
    # 外层每个元素是一条消息的字节列表
    if isinstance(row, list) and row and isinstance(row[0], int):
        msgs.append(('ws_state_snapshots.json', i, row))
    elif isinstance(row, list):
        # 可能嵌套：row 本身是多条消息
        msgs.append(('ws_state_snapshots.json[%d](nested)' % i, 0, row))

print("=== 总消息数:", len(msgs))

# ---------- 1. 长度分布 ----------
lens = [len(m[2]) for m in msgs]
lc = collections.Counter(lens)
print("\n=== 长度分布 (top 30) ===")
for L, c in sorted(lc.items(), key=lambda x: -x[1])[:30]:
    print(f"  len={L:6d}  count={c}")
print("min,max,mean =", min(lens), max(lens), sum(lens)/len(lens))

# 长度直方图分桶
buckets = collections.Counter()
for L in lens:
    if L <= 8: b='1-8'
    elif L<=32: b='9-32'
    elif L<=64: b='33-64'
    elif L<=128: b='65-128'
    elif L<=256: b='129-256'
    elif L<=512: b='257-512'
    elif L<=1024: b='513-1024'
    elif L<=2048: b='1025-2048'
    else: b='>2048'
    buckets[b]+=1
print("\n=== 长度分桶 ===")
for b in ['1-8','9-32','33-64','65-128','129-256','257-512','513-1024','1025-2048','>2048']:
    print(f"  {b:>10}: {buckets[b]}")

# ---------- 2. byte0 分布 ----------
b0 = collections.Counter()
for s,t,d in msgs:
    if d: b0[d[0]] += 1
print("\n=== byte0 取值分布 (top 30) ===")
for v,c in sorted(b0.items(), key=lambda x:-x[1])[:30]:
    print(f"  byte0=0x{v:02X}({v:3d}) count={c}")

# 按长度簇看 byte0
print("\n=== 短帧(len<=8) 的完整内容 ===")
short = [m for m in msgs if len(m[2])<=8]
sc = collections.Counter(tuple(m[2]) for m in short)
for v,c in sc.most_common(20):
    print(f"  {list(v)}  x{c}")
