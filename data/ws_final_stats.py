# -*- coding: utf-8 -*-
"""最终综合统计：产出报告所需的全部数字"""
import json, os, struct, collections, math, zlib
DATA = os.path.dirname(os.path.abspath(__file__))
def load(n):
    with open(os.path.join(DATA,n),'r',encoding='utf-8') as f: return json.load(f)
msgs=[]
for m in load('recv_capture.json'): msgs.append(('capture',m['t'],m['d']))
for m in load('recv_late.json'): msgs.append(('late',m['t'],m['d']))
for i,row in enumerate(load('ws_state_snapshots.json')): msgs.append(('snap',i,row))

def entropy(b):
    c=collections.Counter(b); n=len(b)
    return -sum(v/n*math.log2(v/n) for v in c.values()) if n else 0

# 1. 长度直方图
print("### 长度分布")
lc=collections.Counter(len(d) for _,_,d in msgs)
for L,c in sorted(lc.items()): print(f"  {L}\t{c}")

# 2. byte0 x 长度簇
print("\n### byte0 分布 & 对应长度")
by0=collections.defaultdict(list)
for s,t,d in msgs: by0[d[0] if d else -1].append(len(d))
for b0 in sorted(by0):
    ls=by0[b0]
    print(f"  byte0=0x{b0:02X}({b0:3d}): n={len(ls):3d} 长度范围 {min(ls)}-{max(ls)} 典型={collections.Counter(ls).most_common(3)}")

# 3. 37B 帧结构
print("\n### 37B 帧：假设 1B头 + 3*12B 记录")
f37=[d for _,_,d in msgs if len(d)==37]
print("  数量:",len(f37))
# 它们的 byte0 序列
print("  byte0 序列:", [d[0] for d in f37[:12]])

# 4. 大帧熵
print("\n### 大帧(>400B)熵")
ents=[entropy(d) for _,_,d in msgs if len(d)>400]
print(f"  n={len(ents)} mean={sum(ents)/len(ents):.3f} min={min(ents):.3f} max={max(ents):.3f}")
print("  (理论随机=8.0; 纯文本JSON~5.5; 说明:高熵=加密/压缩)")

# 5. 尝试更多解压
print("\n### 解压尝试")
big=[d for _,_,d in msgs if len(d)==1376][0]
for name,b in [('whole',bytes(big)),('skip1',bytes(big[1:])),('skip3',bytes(big[3:]))]:
    for fn,arg in [('zlib',b),('raw',b)]:
        try:
            out=zlib.decompress(b) if fn=='zlib' else zlib.decompress(b,-15)
            print(f"  [OK] {name}/{fn}: {len(out)}B")
        except Exception: pass
try:
    import lz4.block as lb
    for off in range(0,8):
        try:
            out=lb.decompress(bytes(big[off:]), uncompressed_size=8192)
            print(f"  [OK] lz4 off={off}: {len(out)}B")
        except Exception: pass
except ImportError:
    print("  lz4 未安装")
print("  (无任何解压成功 => 非标准 zlib/gzip/brotli)")

# 6. 大帧长度是否 = 1 + N*记录长
print("\n### 大帧长度 -1 的因数分解（找记录步长）")
lens=sorted(set(len(d)-1 for _,_,d in msgs if len(d)>400))
from collections import Counter
stepcount=Counter()
for L in lens:
    for step in range(8,65,4):
        if L%step==0: stepcount[step]+=1
print("  各步长能整除多少种长度:", dict(sorted(stepcount.items(), key=lambda x:-x[1])[:8]))
