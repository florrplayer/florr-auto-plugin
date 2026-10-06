# -*- coding: utf-8 -*-
"""测试：同 byte0 连续帧是否共享密钥流（XOR 两帧前 N 字节看结构）"""
import json, os, math, collections
DATA = os.path.dirname(os.path.abspath(__file__))
def load(name):
    with open(os.path.join(DATA,name),'r',encoding='utf-8') as f: return json.load(f)
seq=[]
for m in load('recv_capture.json'): seq.append((m['t'],m['d']))
for m in load('recv_late.json'): seq.append((m['t'],m['d']))
for i,row in enumerate(load('ws_state_snapshots.json')): seq.append((('snap',i),row))

# 找连续两个大帧，同 byte0
big=[(t,d) for t,d in seq if len(d)>400]
print("大帧总数:", len(big))
# 按 byte0 分组
from collections import defaultdict
g=defaultdict(list)
for t,d in big: g[d[0]].append((t,d))
for b0,lst in sorted(g.items()):
    print(f"byte0=0x{b0:02X}: {len(lst)} 帧")

# 取 byte0=0x3B 的前两个大帧，XOR 其 payload
lst = g[0x3B]
if len(lst)>=2:
    (t1,d1),(t2,d2)=lst[0],lst[1]
    n=min(len(d1),len(d2))
    xor=[d1[i]^d2[i] for i in range(n)]
    print(f"\n帧1 t={t1} len={len(d1)} 帧2 t={t2} len={len(d2)}")
    print("XOR 前48字节:", [hex(b) for b in xor[:48]])
    # 若密钥流复用，xor=plaintext1^plaintext2，应含很多 0x00（相同字段）或结构
    zeros=sum(1 for b in xor if b==0)
    print(f"XOR 中 0x00 占比: {zeros}/{n} = {zeros/n:.3f} (随机应~0.004)")

# 再试：byte0=0x49
lst=g[0x49]
(t1,d1),(t2,d2)=lst[0],lst[1]
n=min(len(d1),len(d2))
xor=[d1[i]^d2[i] for i in range(n)]
zeros=sum(1 for b in xor if b==0)
print(f"\nbyte0=0x49 两帧 XOR 0x00占比: {zeros}/{n}={zeros/n:.3f}")
print("XOR前32:", [hex(b) for b in xor[:32]])

# 37B 帧：看它们之间 XOR
s37=[(t,d) for t,d in seq if len(d)==37]
print(f"\n37B 帧数: {len(s37)}")
if len(s37)>=3:
    d1,d2,d3=s37[0][1],s37[1][1],s37[2][1]
    x12=[a^b for a,b in zip(d1,d2)]
    print("帧1^帧2:", [hex(b) for b in x12])
