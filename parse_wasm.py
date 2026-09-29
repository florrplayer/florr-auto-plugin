"""解析wasm二进制,提取函数名/导入导出/数据段"""
import struct, os

with open('wasm_dump/client.wasm', 'rb') as f:
    data = f.read()

print(f"wasm大小: {len(data)/1024/1024:.1f}MB")

# wasm头: magic + version
magic = data[:4]
version = struct.unpack('<I', data[4:8])[0]
print(f"magic: {magic}, version: {version}")

# 遍历section
pos = 8
sections = {}
while pos < len(data):
    sec_id = data[pos]; pos += 1
    # LEB128读取长度
    size = 0; shift = 0
    while True:
        b = data[pos]; pos += 1
        size |= (b & 0x7f) << shift
        if not (b & 0x80): break
        shift += 7
    sec_names = {0:'custom',1:'type',2:'import',3:'function',4:'table',5:'memory',6:'global',7:'export',8:'start',9:'elem',10:'code',11:'data',12:'datacount'}
    name = sec_names.get(sec_id, f'sec_{sec_id}')
    sections[name] = size
    print(f"  section {sec_id:2d} {name:12s}: {size:>10,} bytes")
    pos += size

# 解析export section找有用函数
print("\n=== 解析导出函数 ===")
pos = 8
while pos < len(data):
    sec_id = data[pos]; pos += 1
    size = 0; shift = 0
    while True:
        b = data[pos]; pos += 1
        size |= (b & 0x7f) << shift
        if not (b & 0x80): break
        shift += 7
    if sec_id == 7:  # export
        end = pos + size
        count = 0; shift = 0
        while True:
            b = data[pos]; pos += 1
            count |= (b & 0x7f) << shift
            if not (b & 0x80): break
            shift += 7
        print(f"导出数量: {count}")
        for _ in range(count):
            nlen = 0; shift = 0
            while True:
                b = data[pos]; pos += 1
                nlen |= (b & 0x7f) << shift
                if not (b & 0x80): break
                shift += 7
            name = data[pos:pos+nlen].decode('utf-8', errors='ignore')
            pos += nlen
            kind = data[pos]; pos += 1
            idx = 0; shift = 0
            while True:
                b = data[pos]; pos += 1
                idx |= (b & 0x7f) << shift
                if not (b & 0x80): break
                shift += 7
            if kind == 0 and name.startswith('_Util'):
                print(f"  {name} (func idx={idx})")
        break
    pos += size

print("\n=== 解析自定义段(函数名映射) ===")
pos = 8
while pos < len(data):
    sec_id = data[pos]; pos += 1
    size = 0; shift = 0
    while True:
        b = data[pos]; pos += 1
        size |= (b & 0x7f) << shift
        if not (b & 0x80): break
        shift += 7
    if sec_id == 0:  # custom
        end = pos + size
        nlen = 0; shift = 0
        p = pos
        while True:
            b = data[p]; p += 1
            nlen |= (b & 0x7f) << shift
            if not (b & 0x80): break
            shift += 7
        secname = data[p:p+nlen].decode('utf-8', errors='ignore')
        print(f"  自定义段: {secname} ({size} bytes)")
        if secname == 'name':
            # 提取函数名
            rest = data[p+nlen:end]
            # 找name sub-section
            pp = 0
            while pp < len(rest):
                sub_id = rest[pp]; pp += 1
                sub_size = 0; shift = 0
                while True:
                    b = rest[pp]; pp += 1
                    sub_size |= (b & 0x7f) << shift
                    if not (b & 0x80): break
                    shift += 7
                if sub_id == 1:  # function names
                    names_data = rest[pp:pp+sub_size]
                    # 读函数名映射
                    np = 0
                    cnt = 0; shift = 0
                    while True:
                        b = names_data[np]; np += 1
                        cnt |= (b & 0x7f) << shift
                        if not (b & 0x80): break
                        shift += 7
                    print(f"  函数名映射: {cnt}个函数")
                    util_funcs = []
                    for _ in range(cnt):
                        fid = 0; shift = 0
                        while True:
                            b = names_data[np]; np += 1
                            fid |= (b & 0x7f) << shift
                            if not (b & 0x80): break
                            shift += 7
                        nl = 0; shift = 0
                        while True:
                            b = names_data[np]; np += 1
                            nl |= (b & 0x7f) << shift
                            if not (b & 0x80): break
                            shift += 7
                        fname = names_data[np:np+nl].decode('utf-8', errors='ignore')
                        np += nl
                        if 'Util' in fname or 'Mob' in fname or 'Petal' in fname:
                            util_funcs.append((fid, fname))
                    print(f"  含Util/Mob/Petal的函数:")
                    for fid, fname in sorted(util_funcs):
                        print(f"    [{fid}] {fname}")
                pp += sub_size
        break
    pos += size
