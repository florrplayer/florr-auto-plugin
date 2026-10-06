# -*- coding: utf-8 -*-
"""试解压 + 看 wasm 接收相关线索"""
import json, os, struct, zlib, collections

DATA = os.path.dirname(os.path.abspath(__file__))
def load(name):
    with open(os.path.join(DATA, name), 'r', encoding='utf-8') as f:
        return json.load(f)
msgs=[]
for name in ['recv_capture.json','recv_late.json']:
    for m in load(name): msgs.append(m['d'])
for row in load('ws_state_snapshots.json'): msgs.append(row)

big=[d for d in msgs if len(d)==1376][0]
tests = {
  'whole': bytes(big),
  'skip1': bytes(big[1:]),
  'skip2': bytes(big[2:]),
}
for label, b in tests.items():
    for name, fn in [('zlib', zlib.decompress), ('raw-deflate', lambda x: zlib.decompress(x,-15))]:
        try:
            out=fn(b)
            print(f"[OK] {label} via {name}: {len(out)} bytes, head={list(out[:32])}")
        except Exception as e:
            pass

# brotli?
try:
    import brotli
    for label,b in tests.items():
        try:
            out=brotli.decompress(b)
            print(f"[OK] {label} via brotli: {len(out)} bytes")
        except Exception as e:
            pass
except ImportError:
    print("brotli not installed")

# 看看 byte0=0 的 [0] 心跳和大帧的字节分布差异
print("\n=== 大帧字节直方图前8 vs 均匀分布(每值应~500/256=2) ===")
c = collections.Counter(big)
print("distinct bytes:", len(c), "of 256")
print("most common:", [(hex(k),v) for k,v in c.most_common(8)])
print("least common:", [(hex(k),v) for k,v in c.most_common()[-8:]])
