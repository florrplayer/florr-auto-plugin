# -*- coding: utf-8 -*-
"""wasm code段反汇编器 - 提取函数中的浮点数常量和调用关系"""
import struct, os, json

with open('wasm_dump/client.wasm', 'rb') as f:
    data = f.read()

# 解析section
pos = 8
sections = {}
while pos < len(data):
    sid = data[pos]; pos += 1
    sz = 0; sh = 0
    while True:
        b = data[pos]; pos += 1
        sz |= (b & 0x7f) << sh
        if not (b & 0x80): break
        sh += 7
    sections[sid] = (pos, sz)
    pos += sz

# type section
types = []
if 1 in sections:
    tp, ts = sections[1]
    p = tp
    n = 0; sh = 0
    while True:
        b = data[p]; p += 1
        n |= (b & 0x7f) << sh
        if not (b & 0x80): break
        sh += 7
    for _ in range(n):
        assert data[p] == 0x60; p += 1
        # params
        np = 0; sh = 0
        while True:
            b = data[p]; p += 1
            np |= (b & 0x7f) << sh
            if not (b & 0x80): break
            sh += 7
        p += np  # skip param types
        nr = 0; sh = 0
        while True:
            b = data[p]; p += 1
            nr |= (b & 0x7f) << sh
            if not (b & 0x80): break
            sh += 7
        p += nr  # skip return types
        types.append((np, nr))

print(f"类型: {len(types)}个")

# function section - 函数索引到type
func_types = []
if 3 in sections:
    fp, fs = sections[3]
    p = fp
    n = 0; sh = 0
    while True:
        b = data[p]; p += 1
        n |= (b & 0x7f) << sh
        if not (b & 0x80): break
        sh += 7
    for _ in range(n):
        t = 0; sh = 0
        while True:
            b = data[p]; p += 1
            t |= (b & 0x7f) << sh
            if not (b & 0x80): break
            sh += 7
        func_types.append(t)
print(f"函数: {len(func_types)}个")

# code section - 函数体
cp, cs = sections[10]
print(f"code段: {cs/1024/1024:.1f}MB")

# 反汇编每个函数,提取f64.const
functions = []
p = cp
nfuncs = 0; sh = 0
while True:
    b = data[p]; p += 1
    nfuncs |= (b & 0x7f) << sh
    if not (b & 0x80): break
    sh += 7

print(f"反汇编 {nfuncs} 个函数...")

for fi in range(nfuncs):
    body_size = 0; sh = 0
    while True:
        b = data[p]; p += 1
        body_size |= (b & 0x7f) << sh
        if not (b & 0x80): break
        sh += 7
    body_start = p
    body_end = p + body_size

    # locals count
    local_count = 0; sh = 0
    while True:
        b = data[p]; p += 1
        local_count |= (b & 0x7f) << sh
        if not (b & 0x80): break
        sh += 7
    for _ in range(local_count):
        # local type
        cnt = 0; sh = 0
        while True:
            b = data[p]; p += 1
            cnt |= (b & 0x7f) << sh
            if not (b & 0x80): break
            sh += 7
        p += 1  # type byte

    # 扫描函数体找f64.const (0x44) 和 call (0x10)
    f64s = []
    calls = []
    q = p
    while q < body_end:
        op = data[q]; q += 1
        if op == 0x44:  # f64.const
            val = struct.unpack('<d', data[q:q+8])[0]
            f64s.append(val)
            q += 8
        elif op == 0x10:  # call
            idx = 0; sh = 0
            while True:
                b = data[q]; q += 1
                idx |= (b & 0x7f) << sh
                if not (b & 0x80): break
                sh += 7
            calls.append(idx)
        elif op == 0x0b:  # end
            break
        else:
            # 简单跳过: 大部分op是1字节,但有些有操作数
            # 粗略处理: 只处理已知的有立即数的op
            if op in (0x41, 0x42):  # i32.const/i64.const
                v = 0; sh = 0
                while True:
                    b = data[q]; q += 1
                    v |= (b & 0x7f) << sh
                    if not (b & 0x80): break
                    sh += 7
            elif op == 0x43:  # f32.const
                q += 4
            elif op == 0x20 or op == 0x21 or op == 0x22 or op == 0x23:  # local.get/set/tee
                v = 0; sh = 0
                while True:
                    b = data[q]; q += 1
                    v |= (b & 0x7f) << sh
                    if not (b & 0x80): break
                    sh += 7
            elif op == 0x10:  # call already handled
                pass
            # 其他op默认无操作数,继续

    if f64s or calls:
        functions.append({
            'id': fi,
            'f64s': f64s,
            'calls': calls,
        })
    p = body_end

print(f"提取到 {len(functions)} 个含浮点数/调用的函数")

# 找含碰撞箱半径(5-100)的函数
radius_funcs = []
for f in functions:
    for v in f['f64s']:
        if 3 < v < 80 and abs(v - round(v)) < 0.1:
            radius_funcs.append((f['id'], round(v, 1), f['calls'][:5]))
            break

print(f"\n含可能碰撞箱半径(3-80)的函数: {len(radius_funcs)}个")
for fid, r, calls in radius_funcs[:20]:
    print(f"  func[{fid}] radius~{r}, calls={calls}")

# 保存
with open('wasm_dump/disasm.json', 'w') as out:
    json.dump(functions[:500], out)
print(f"\n已保存前500个函数到 wasm_dump/disasm.json")
