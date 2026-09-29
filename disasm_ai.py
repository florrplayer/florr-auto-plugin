# -*- coding: utf-8 -*-
"""反汇编找怪物AI逻辑 - 追击范围/逃跑范围/攻击频率"""
import struct

with open('wasm_dump/client.wasm', 'rb') as f:
    data = f.read()

pos = 8
while pos < len(data):
    sid = data[pos]; pos += 1
    sz = 0; sh = 0
    while True:
        b = data[pos]; pos += 1
        sz |= (b & 0x7f) << sh
        if not (b & 0x80): break
        sh += 7
    if sid == 10:
        cp = pos; break
    pos += sz

p = cp
nfuncs = 0; sh = 0
while True:
    b = data[p]; p += 1
    nfuncs |= (b & 0x7f) << sh
    if not (b & 0x80): break
    sh += 7

# 找含追击范围(100-500)和攻击频率的函数
ai_funcs = []
for fi in range(nfuncs):
    body_size = 0; sh = 0
    while True:
        b = data[p]; p += 1
        body_size |= (b & 0x7f) << sh
        if not (b & 0x80): break
        sh += 7
    body_end = p + body_size
    lc = 0; sh = 0
    while True:
        b = data[p]; p += 1
        lc |= (b & 0x7f) << sh
        if not (b & 0x80): break
        sh += 7
    for _ in range(lc):
        cnt = 0; sh = 0
        while True:
            b = data[p]; p += 1
            cnt |= (b & 0x7f) << sh
            if not (b & 0x80): break
            sh += 7
        p += 1

    f64s = []
    q = p
    while q < body_end:
        op = data[q]; q += 1
        if op == 0x44:
            v = struct.unpack('<d', data[q:q+8])[0]
            f64s.append(v)
            q += 8
        elif op == 0x43:
            v = struct.unpack('<f', data[q:q+4])[0]
            f64s.append(v)
            q += 4
        elif op == 0x0b: break
        elif op in (0x41, 0x42, 0x20, 0x21, 0x22, 0x23):
            v = 0; sh = 0
            while True:
                b = data[q]; q += 1
                v |= (b & 0x7f) << sh
                if not (b & 0x80): break
                sh += 7

    # AI特征: 100-500的范围值(追击距离)
    ranges = [v for v in f64s if 50 < v < 500]
    if ranges:
        ai_funcs.append((fi, ranges[:5], f64s[:10]))
    p = body_end

print(f"=== 怪物AI函数 ({len(ai_funcs)}个) ===")
for fid, ranges, allv in ai_funcs[:30]:
    print(f"func[{fid}]: 范围={[round(r,0) for r in ranges]} 其他={[round(v,1) for v in allv if v not in ranges][:5]}")
