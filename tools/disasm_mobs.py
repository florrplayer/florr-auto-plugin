# -*- coding: utf-8 -*-
"""深入分析怪物构造函数 - 提取碰撞箱/速度/HP"""
import struct, json

with open('wasm_dump/client.wasm', 'rb') as f:
    data = f.read()

# 找code段
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
        cp = pos; cs = sz; break
    pos += sz

# 解析函数
p = cp
nfuncs = 0; sh = 0
while True:
    b = data[p]; p += 1
    nfuncs |= (b & 0x7f) << sh
    if not (b & 0x80): break
    sh += 7

# 找6400-6500范围的函数(怪物构造函数群)
target_range = range(6390, 6500)
func_data = {}
for fi in range(nfuncs):
    body_size = 0; sh = 0
    while True:
        b = data[p]; p += 1
        body_size |= (b & 0x7f) << sh
        if not (b & 0x80): break
        sh += 7
    body_start = p
    body_end = p + body_size

    if fi in target_range:
        # 提取所有f64常量
        f64s = []
        q = p
        # skip locals
        lc = 0; sh = 0
        while True:
            b = data[q]; q += 1
            lc |= (b & 0x7f) << sh
            if not (b & 0x80): break
            sh += 7
        for _ in range(lc):
            cnt = 0; sh = 0
            while True:
                b = data[q]; q += 1
                cnt |= (b & 0x7f) << sh
                if not (b & 0x80): break
                sh += 7
            q += 1

        while q < body_end:
            op = data[q]; q += 1
            if op == 0x44:  # f64.const
                val = struct.unpack('<d', data[q:q+8])[0]
                f64s.append(val)
                q += 8
            elif op == 0x43:  # f32.const
                val = struct.unpack('<f', data[q:q+4])[0]
                f64s.append(('f32', val))
                q += 4
            elif op == 0x0b:
                break
            elif op in (0x41, 0x42, 0x20, 0x21, 0x22, 0x23):
                v = 0; sh = 0
                while True:
                    b = data[q]; q += 1
                    v |= (b & 0x7f) << sh
                    if not (b & 0x80): break
                    sh += 7
        func_data[fi] = f64s

    p = body_end

# 打印
print("=== 怪物构造函数群 (6390-6500) ===")
for fid in sorted(func_data.keys()):
    vals = func_data[fid]
    interesting = [v for v in vals if isinstance(v, float) and 0.1 < abs(v) < 1000]
    if interesting:
        print(f"func[{fid}]: {[round(v,2) for v in interesting[:15]]}")
