# -*- coding: utf-8 -*-
"""反汇编找网络协议解码函数 - WebSocket消息格式"""
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

# 找含channel ID(0x49=73, 0x3b=59, 0x5c=92)的函数
# 这些是WebSocket通道字节
channel_bytes = {73: '0x49', 59: '0x3b', 92: '0x5c'}
proto_funcs = []
for fi in range(nfuncs):
    body_size = 0; sh = 0
    while True:
        b = data[p]; p += 1
        body_size |= (b & 0x7f) << sh
        if not (b & 0x80): break
        sh += 7
    body_end = p + body_size

    # 扫描函数体找channel字节
    body = data[p:body_end]
    found_channels = []
    for ch_val, ch_name in channel_bytes.items():
        if bytes([ch_val]) in body[:200]:  # 函数开头附近
            found_channels.append(ch_name)

    if found_channels:
        # 提取函数里的整数常量
        ints = []
        q = p
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
            if op in (0x41, 0x42):  # i32.const
                v = 0; sh = 0
                while True:
                    b = data[q]; q += 1
                    v |= (b & 0x7f) << sh
                    if not (b & 0x80): break
                    sh += 7
                if 0 < v < 1000:
                    ints.append(v)
            elif op == 0x0b: break
            elif op in (0x20, 0x21, 0x22, 0x23):
                v = 0; sh = 0
                while True:
                    b = data[q]; q += 1
                    v |= (b & 0x7f) << sh
                    if not (b & 0x80): break
                    sh += 7

        proto_funcs.append((fi, found_channels, ints[:10]))
    p = body_end

print(f"=== 网络协议函数 ({len(proto_funcs)}个) ===")
for fid, chans, ints in proto_funcs:
    print(f"func[{fid}]: channels={chans} 整数常量={ints}")
