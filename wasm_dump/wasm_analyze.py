# -*- coding: utf-8 -*-
"""Minimal wasm static analyzer: sections, exports, data strings, code xrefs."""
import struct, json, re, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PATH = r'C:\Users\intel\Downloads\florr-auto-pathing-main\wasm_dump\client.wasm'
data = open(PATH, 'rb').read()
assert data[:4] == b'\x00asm'
version = struct.unpack('<I', data[4:8])[0]

def read_uleb(buf, pos):
    result = 0; shift = 0
    while True:
        b = buf[pos]; pos += 1
        result |= (b & 0x7f) << shift
        if not (b & 0x80): break
        shift += 7
    return result, pos

def read_sleb(buf, pos):
    result = 0; shift = 0
    while True:
        b = buf[pos]; pos += 1
        result |= (b & 0x7f) << shift
        shift += 1
        if not (b & 0x80):
            if (b & 0x40):
                result |= -(1 << shift)
            break
    return result, pos

# ---- walk sections ----
pos = 8
sections = {}
sec_list = []
while pos < len(data):
    sid = data[pos]; pos += 1
    size, pos = read_uleb(data, pos)
    payload_start = pos
    sec_list.append((sid, payload_start, size))
    sections.setdefault(sid, []).append((payload_start, size))
    pos += size

SEC_NAMES = {0:'custom',1:'type',2:'import',3:'function',4:'table',5:'memory',
             6:'global',7:'export',8:'start',9:'elem',10:'code',11:'data',12:'datacount'}
print('=== SECTIONS ===')
for sid, off, size in sec_list:
    print(f'id={sid:2d} {SEC_NAMES.get(sid,"?"):8s} off=0x{off:06x} size={size}')

# ---- imports ----
imports = []
if 2 in sections:
    off, size = sections[2][0]
    end = off + size
    n, pos = read_uleb(data, off)
    for i in range(n):
        nm_len, pos = read_uleb(data, pos)
        mod = data[pos:pos+nm_len].decode('utf-8','replace'); pos += nm_len
        fn_len, pos = read_uleb(data, pos)
        fn = data[pos:pos+fn_len].decode('utf-8','replace'); pos += fn_len
        kind = data[pos]; pos += 1
        if kind == 0:  # func
            tid, pos = read_uleb(data, pos)
        elif kind == 1:  # table
            pos += 1  # elemtype
            flags, pos = read_uleb(data, pos)
            _, pos = read_uleb(data, pos)
            if flags & 1:
                _, pos = read_uleb(data, pos)
        elif kind == 2:  # memory
            flags, pos = read_uleb(data, pos)
            _, pos = read_uleb(data, pos)
            if flags & 1:
                _, pos = read_uleb(data, pos)
        elif kind == 3:  # global
            pos += 2  # valtype + mut
        imports.append((mod, fn, kind))
print(f'\n=== IMPORTS ({len(imports)}) ===')
for m,f,k in imports:
    print(f'  [{k}] {m}.{f}')

# ---- exports ----
exports = []
if 7 in sections:
    off, size = sections[7][0]
    end = off + size
    pos = off
    n, pos = read_uleb(data, pos)
    KIND = {0:'func',1:'table',2:'mem',3:'global'}
    for i in range(n):
        nl, pos = read_uleb(data, pos)
        nm = data[pos:pos+nl].decode('utf-8','replace'); pos += nl
        kind = data[pos]; pos += 1
        idx, pos = read_uleb(data, pos)
        exports.append((nm, KIND.get(kind,kind), idx))
print(f'\n=== EXPORTS ({len(exports)}) ===')
for nm,k,idx in exports:
    print(f'  {k:6s} [{idx:5d}] {nm}')

# ---- function section count ----
num_funcs = 0
if 3 in sections:
    off, size = sections[3][0]
    num_funcs, _ = read_uleb(data, off)
print(f'\nfunction section: {num_funcs} internal funcs')

# ---- data segments ----
segments = []  # (vaddr, bytes)
if 11 in sections:
    off, size = sections[11][0]
    end = off + size
    pos = off
    n, pos = read_uleb(data, pos)
    for i in range(n):
        flag = data[pos]; pos += 1
        if flag == 0:
            # offset expr: i32.const .. end
            assert data[pos] == 0x41
            vaddr, pos = read_sleb(data, pos+1)
            assert data[pos] == 0x0b
            pos += 1
        elif flag == 1:
            vaddr = 0
        elif flag == 2:
            memidx, pos = read_uleb(data, pos)
            assert data[pos] == 0x41
            vaddr, pos = read_sleb(data, pos+1)
            assert data[pos] == 0x0b
            pos += 1
        else:
            raise ValueError(f'bad data flag {flag}')
        sz, pos = read_uleb(data, pos)
        segments.append((vaddr, data[pos:pos+sz]))
        pos += sz
print(f'\ndata segments: {len(segments)}, total bytes: {sum(len(s) for _,s in segments)}')

# build string map: scan each segment for ascii runs >=4
string_map = {}  # vaddr -> str
for vaddr, s in segments:
    i = 0
    while i < len(s):
        if 32 <= s[i] < 127:
            j = i
            while j < len(s) and 32 <= s[j] < 127:
                j += 1
            if j - i >= 4:
                string_map[vaddr + i] = s[i:j].decode('ascii')
            i = j
        else:
            i += 1
print(f'ascii strings(>=4) extracted: {len(string_map)}')

# ---- code section walker ----
# map internal func index (imports N first) -> body info
IMPORT_COUNT = sum(1 for _,_,k in imports if k == 0)
print(f'imported funcs: {IMPORT_COUNT}')

funcs = []  # per internal func: dict(i32refs=set, f64=[], f32=[], calls=set)
if 10 in sections:
    off, size = sections[10][0]
    end = off + size
    pos = off
    count, pos = read_uleb(data, pos)
    print(f'code bodies: {count}')
    for fi in range(count):
        bsize, pos = read_uleb(data, pos)
        bstart = pos
        bend = pos + bsize
        # locals
        ngroups, p = read_uleb(data, bstart)
        for _ in range(ngroups):
            cnt, p = read_uleb(data, p)
            p += 1
        info = {'i32': [], 'f64': [], 'f32': [], 'calls': []}
        depth = 0
        while p < bend:
            op = data[p]; p += 1
            if op == 0x0b:  # end
                depth -= 1
                continue
            if op in (0x02, 0x03, 0x04):  # block/loop/if
                depth += 1
                p += 1  # blocktype byte
                continue
            if op == 0x05:  # else
                continue
            if op in (0x08, 0x09):  # br / br_if
                _, p = read_uleb(data, p); continue
            if op == 0x0a:  # br_table
                nt, p = read_uleb(data, p)
                for _ in range(nt + 1):
                    _, p = read_uleb(data, p)
                continue
            if op == 0x0f:  # return
                continue
            if op == 0x10:  # call
                idx, p = read_uleb(data, p)
                info['calls'].append(idx)
                continue
            if op == 0x11:  # call_indirect
                _, p = read_uleb(data, p)
                p += 1
                continue
            if op in (0x20, 0x21, 0x22, 0x23, 0x24):
                _, p = read_uleb(data, p); continue
            if 0x28 <= op <= 0x3e:  # loads/stores with memarg
                _, p = read_uleb(data, p)
                _, p = read_uleb(data, p)
                continue
            if op == 0x3f or op == 0x40:
                p += 1; continue
            if op == 0x41:
                v, p = read_sleb(data, p)
                info['i32'].append(v)
                continue
            if op == 0x42:
                _, p = read_sleb(data, p); continue
            if op == 0x43:
                v = struct.unpack('<f', data[p:p+4])[0]; p += 4
                info['f32'].append(v)
                continue
            if op == 0x44:
                v = struct.unpack('<d', data[p:p+8])[0]; p += 8
                info['f64'].append(v)
                continue
            if op == 0xfc:
                sub, p = read_uleb(data, p)
                if sub in (0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07):
                    _, p = read_uleb(data, p)
                elif sub in (0x08,0x09):
                    _, p = read_uleb(data, p); _, p = read_uleb(data, p)
                continue
            if op == 0xfd:
                p += 17  # skip simd lane + 16 bytes
                continue
            # all others: no immediates
        pos = bend
        info['calls'] = sorted(set(info['calls']))
        funcs.append(info)

print(f'parsed bodies: {len(funcs)}')

# ---- string xref: which functions reference which string addresses ----
# index strings by address; for each func i32.const value, check if it matches a string start
str_addrs = sorted(string_map.keys())
import bisect

def strings_at(addr):
    hits = []
    if addr in string_map:
        hits.append(string_map[addr])
    return hits

xref = {}  # string -> [internal func indices]
for fi, info in enumerate(funcs):
    for v in info['i32']:
        if v in string_map:
            xref.setdefault(string_map[v], []).append(fi)

# ---- save full results ----
out = {
    'version': version,
    'exports': exports,
    'imports': imports,
    'num_funcs': num_funcs,
    'xref': xref,
}
json.dump(out, open(r'C:\Users\intel\Downloads\florr-auto-pathing-main\wasm_dump\wasm_struct.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)

# also dump per-func constants
consts = []
for fi, info in enumerate(funcs):
    consts.append({'id': fi, 'f64': info['f64'], 'f32': info['f32'],
                    'calls': info['calls'], 'i32': [v for v in info['i32'] if 0 < v < 2000000]})
json.dump(consts, open(r'C:\Users\intel\Downloads\florr-auto-pathing-main\wasm_dump\all_func_consts.json','w',encoding='utf-8'))
print('saved wasm_struct.json + all_func_consts.json')
