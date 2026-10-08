# -*- coding: utf-8 -*-
"""继续反汇编 - 找投射物/子弹/飞行物数据
黄蜂导弹、蝎子螯针、花瓣投射物
"""
import struct

with open('wasm_dump/client.wasm', 'rb') as f:
    data = f.read()

# code段
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

# 解析所有函数,找含速度/子弹相关的浮点数
p = cp
nfuncs = 0; sh = 0
while True:
    b = data[p]; p += 1
    nfuncs |= (b & 0x7f) << sh
    if not (b & 0x80): break
    sh += 7

# 找含速度值(5-50)和伤害值的函数
projectile_funcs = []
for fi in range(nfuncs):
    body_size = 0; sh = 0
    while True:
        b = data[p]; p += 1
        body_size |= (b & 0x7f) << sh
        if not (b & 0x80): break
        sh += 7
    body_end = p + body_size

    # skip locals
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

    # 提取f64
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

    # 投射物特征: 速度(5-50) + 小半径(1-5)
    speeds = [v for v in f64s if 3 < v < 60]
    small_r = [v for v in f64s if 1 < v < 6]
    if speeds and small_r:
        projectile_funcs.append((fi, speeds[:5], small_r[:3], f64s[:10]))

    p = body_end

print(f"=== 投射物/子弹函数 ({len(projectile_funcs)}个) ===")
for fid, spds, rs, allv in projectile_funcs[:30]:
    print(f"func[{fid}]: 速度={[round(s,1) for s in spds]} 半径={[round(r,1) for r in rs]} 其他={[round(v,1) for v in allv if v not in spds+rs][:5]}")
