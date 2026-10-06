# -*- coding: utf-8 -*-
"""transcribe_assets.py v1.27.1 - 扫荡报告24项资产转录器 (参考仓扫荡报告.md §3)
把 reference-florr-tools 里挖到的数据资产转录进插件 data/
用法: py -3.12 tools/transcribe_assets.py
覆盖: 数据层(#1-17数据文件 + #22 MAP_MOBS) + 工具归档; 图片/权重(#18-21)本地复制不入git
"""
import json, os, re, sys, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 插件根
SRC = os.path.join(ROOT, 'reference-florr-tools')
DATA = os.path.join(ROOT, 'data')
TOOLS = os.path.join(ROOT, 'tools')
os.makedirs(DATA, exist_ok=True)
os.makedirs(TOOLS, exist_ok=True)

report = []


def read_text(path):
    """编码探测读取: utf-8 → utf-8-sig → shift_jis → cp932 → gb18030"""
    raw = open(path, 'rb').read()
    for enc in ('utf-8-sig', 'utf-8', 'shift_jis', 'cp932', 'gb18030'):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode('utf-8', errors='replace')


def jwrite(name, obj):
    p = os.path.join(DATA, name)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    report.append(('json', name, os.path.getsize(p)))


def copyfile(src_rel, dst_name):
    s = os.path.join(SRC, src_rel)
    d = os.path.join(DATA, dst_name)
    shutil.copy2(s, d)
    report.append(('copy', dst_name, os.path.getsize(d)))


# ===== A. 直接复制 JSON =====
print("[A] 复制JSON...")
copyfile('florr_clone\\mob_stats.json', 'real_florr_mob_stats.json')
copyfile('florr_clone\\src\\petals.json', 'clone_petals.json')
copyfile('florr_clone\\maps\\maps.json', 'clone_map_manifest.json')


def parse_header(rel):
    """解析 C++ 头文件: inline constexpr 常量/array 数组(带注释) + enum class + 数据函数"""
    p = os.path.join(SRC, rel)
    txt = open(p, encoding='utf-8', errors='replace').read()
    out = {'_file': rel}
    # 1) inline constexpr std::array<...> kX = { ... };  → 数组
    for m in re.finditer(r'inline\s+constexpr\s+std::array<[^>]*>\s+(\w+)\s*=\s*\{(.*?)\};', txt, re.S):
        body = m.group(2)
        elems = []
        # 去掉注释分隔, 按逗号切, 保留注释
        for seg in re.split(r',\s*(?=[^/]|$)', body):
            seg = seg.strip()
            if not seg:
                continue
            cm = re.search(r'//\s*(.*)$', seg)
            val = re.sub(r'//.*$', '', seg).strip().strip('"').strip("'")
            elems.append({'v': val, 'note': cm.group(1).strip() if cm else ''})
        out[m.group(1)] = elems
    # 2) inline constexpr TYPE kX = value;
    for m in re.finditer(r'inline\s+constexpr\s+(?:std::)?\w+(?:<[^>]*>)?\s+(\w+)\s*=\s*([^;]+);', txt):
        out[m.group(1)] = m.group(2).strip()
    # 3) enum class NAME : TYPE { ... };
    for m in re.finditer(r'enum\s+class\s+(\w+)\s*:\s*\w+\s*\{([^}]*)\}', txt, re.S):
        vals = {}
        i = 0
        for e in re.findall(r'(\w+)\s*(?:=\s*(\d+))?', m.group(2)):
            if e[0] and not e[0].startswith('//'):
                vals[e[0]] = int(e[1]) if e[1] else i
                i += 1
        out['_enum_' + m.group(1)] = vals
    # 4) 数据函数 (实现即数据: 价格/难度/冷却公式)
    for m in re.finditer(r'inline\s+\w+(?:\s+\w+)*\s+(\w+)\s*\(([^)]*)\)\s*\{([^}]{0,400})\}', txt, re.S):
        out.setdefault('_functions', []).append({
            'name': m.group(1),
            'params': re.sub(r'\s+', ' ', m.group(2)).strip(),
            'body': re.sub(r'\s+', ' ', m.group(3)).strip()[:200],
        })
    return out


print("[B] 解析C++头文件...")
for rel, name in [
    ('florr_clone\\cpp\\shared\\game\\rarity.h', 'clone_rarity_system.json'),
    ('florr_clone\\cpp\\shared\\game\\constants.h', 'clone_game_constants.json'),
    ('florr_clone\\cpp\\shared\\game\\difficulty.h', 'clone_spawn_difficulty.json'),
    ('florr_clone\\cpp\\server\\systems\\spawning.h', 'clone_spawning_tuning.json'),
    ('florr_clone\\cpp\\shared\\game\\shop.h', 'clone_shop_economy.json'),
    ('florr_clone\\cpp\\shared\\game\\realm.h', 'clone_realms.json'),
    ('florr_clone\\cpp\\shared\\game\\skills.h', 'clone_skill_tree.json'),
    ('florr_clone\\cpp\\shared\\net\\protocol.h', 'clone_protocol_ops.json'),
    ('florr_clone\\cpp\\server\\systems\\loot.h', 'clone_loot_tuning.json'),
]:
    jwrite(name, parse_header(rel))


# ===== C. gardn StaticData =====
print("[C] gardn StaticData...")
gd = {}
try:
    cc = open(os.path.join(SRC, 'gardn\\Shared\\StaticData.cc'), encoding='utf-8', errors='replace').read()
    hh = open(os.path.join(SRC, 'gardn\\Shared\\StaticData.hh'), encoding='utf-8', errors='replace').read()
    # 关键公式/常量 (等级曲线/难度)
    for pat in [r'(pow\(1\.06.*?\)\s*[\+\*]\s*\w+)', r'difficulty_at_level[^;]*', r'level[^;]{0,60}pow[^;]{0,80}']:
        ms = re.findall(pat, cc, re.I)
        if ms:
            gd.setdefault('formulas', []).extend(ms[:3])
    jwrite('reference_gardn_staticdata.json', {'formulas': gd.get('formulas', []),
                                               '_note': '原文已归档为 reference_gardn_staticdata.cc/.hh (GPL, 取数据思路不整段抄)'})
    copyfile('gardn\\Shared\\StaticData.cc', 'reference_gardn_staticdata.cc')
    copyfile('gardn\\Shared\\StaticData.hh', 'reference_gardn_staticdata.hh')
except Exception as e:
    print('  gardn err', e)


# ===== D. wiki data.js 机制常数 =====
print("[D] wiki data.js...")
try:
    js = read_text(os.path.join(SRC, 'wiki\\scripts\\data.js'))

    def extract_braced(src, start):
        """从 start 的 { 开始做括号深度匹配, 返回 (块文本, 结束索引)"""
        depth = 0
        for i in range(start, len(src)):
            c = src[i]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return src[start:i + 1], i + 1
        return None, len(src)

    blocks = {}
    for m in re.finditer(r'(?:florr|dataObj)\.(\w+)\s*=\s*\{', js):
        name = m.group(1)
        if name in blocks:
            continue
        blk, _ = extract_braced(js, m.start() + m.group(0).rindex('{'))
        if blk:
            blocks[name] = blk
    # 独立 const 对象 (无 florr. 前缀)
    for m in re.finditer(r'const\s+(\w+)\s*=\s*\{', js):
        name = m.group(1)
        if name in blocks:
            continue
        blk, _ = extract_braced(js, m.start() + m.group(0).rindex('{'))
        if blk:
            blocks[name] = blk
    # 尝试 json 化: 去掉单引号/注释/尾逗号
    parsed = {}
    for name, blk in blocks.items():
        b = re.sub(r'//[^\n]*', '', blk)
        b = re.sub(r"'", '"', b)
        b = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', b)
        b = re.sub(r',\s*}', '}', b)
        try:
            parsed[name] = json.loads(b)
        except Exception:
            parsed[name] = {'_raw_len': len(b), '_head': b[:1500]}
    if parsed:
        jwrite('florr_mechanics_jp.json', parsed)
    else:
        jwrite('florr_mechanics_jp.json', {'_raw': js[:20000], '_note': '未匹配对象块'})
except Exception as e:
    print('  wiki err', e)


# ===== E. florr-maps-browser 地图源 =====
print("[E] florr-maps-browser...")
try:
    src = {'MAPS_LIST_URL': None, 'MAPS_BASE_URL': None, 'MAP_ORDER': [], 'warp_rules': []}
    t = open(os.path.join(SRC, 'florr-maps-browser\\src\\lib\\maplist.js'), encoding='utf-8', errors='replace').read()
    m = re.search(r'MAPS_LIST_URL\s*=\s*"([^"]+)"', t)
    if m:
        src['MAPS_LIST_URL'] = m.group(1)
    m = re.search(r'MAP_ORDER\s*=\s*\[(.*?)\]', t, re.S)
    if m:
        src['MAP_ORDER'] = [x.strip().strip('"') for x in re.findall(r'"([^"]+)"', m.group(1))]
    for r in re.findall(r'if\s*\(id\s*===\s*"([^"]+)"\)\s*return\s*"([^"]+)"', t):
        src['warp_rules'].append({'id': r[0], 'name': r[1]})
    t2 = open(os.path.join(SRC, 'florr-maps-browser\\src\\lib\\maploader.js'), encoding='utf-8', errors='replace').read()
    m = re.search(r'MAPS_BASE_URL\s*=\s*"([^"]+)"', t2)
    if m:
        src['MAPS_BASE_URL'] = m.group(1)
    src['tmj_url_template'] = (src['MAPS_BASE_URL'] or '') + '/{id}.tmj'
    jwrite('map_sources.json', src)
except Exception as e:
    print('  maps err', e)


# ===== F. Legacy wasm 字符串 =====
print("[F] Legacy wasm strings...")
try:
    import glob
    wasms = glob.glob(os.path.join(SRC, 'Legacy-florr.io\\**\\*.wasm'), recursive=True)
    legacy = {}
    for w in wasms:
        name = os.path.basename(w)
        data = open(w, 'rb').read()
        strs = re.findall(rb'[ -~]{5,}', data)
        s = [x.decode('ascii', 'replace') for x in strs]
        # 怪/花瓣/机制关键词
        mobs = sorted({x for x in s if any(k in x.lower() for k in
                     ['triplet', 'yinyang', 'boulder', 'centipede', 'ant', 'beetle', 'ladybug', 'queen', 'egg', 'worm'])})
        petals = sorted({x for x in s if any(k in x.lower() for k in
                      ['petal', 'rose', 'leaf', 'stinger', 'missile', 'triangle', 'square', 'coin'])})
        legacy[name] = {'strings_total': len(s), 'mob_hits': mobs[:80], 'petal_hits': petals[:80]}
    jwrite('legacy_wasm_strings.json', legacy)
except Exception as e:
    print('  legacy err', e)


# ===== G. local-florr 官方客户端情报 =====
print("[G] local-florr client info...")
try:
    exe = open(os.path.join(SRC, 'local-florr\\client.exe'), 'rb').read()
    strs = re.findall(rb'[ -~]{12,}', exe)
    s = [x.decode('ascii', 'replace') for x in strs]
    flor = [x for x in s if 'florrio' in x.lower() or 'florr.io' in x.lower()]
    jwrite('real_florr_changelog.json', {
        '_note': 'client.exe(8.5MB, SDL2+OpenGL+Skia原生客户端)字符串提取; 无patch notes(仅GL/Skia), 得到官方控制开关清单',
        'official_switches': flor,
        'total_strings': len(s),
        'gl_strings': sum(1 for x in s if x.startswith('GL_')),
    })
except Exception as e:
    print('  changelog err', e)


# ===== H. MAP_MOBS 分区怪物册 =====
print("[H] MAP_MOBS...")
try:
    gp = os.path.join(SRC, 'florr_powerful_tools\\upload_package\\~\\generate_data.py')
    if not os.path.exists(gp):
        import glob as _g
        hits = _g.glob(os.path.join(SRC, 'florr_powerful_tools\\**\\generate_data.py'), recursive=True)
        gp = hits[0] if hits else gp
    t = read_text(gp)

    def extract_braced(src, start):
        depth = 0
        for i in range(start, len(src)):
            c = src[i]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return src[start:i + 1]
        return None

    m = re.search(r'MAP_MOBS\s*=\s*\{', t)
    if m:
        body = extract_braced(t, m.end() - 1)
        if body:
            body = re.sub(r"'", '"', body)
            body = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', body)
            body = re.sub(r',\s*}', '}', body)
            try:
                jwrite('zone_mob_roster.json', json.loads(body))
            except Exception as e:
                jwrite('zone_mob_roster.json', {'_raw': body[:8000], '_note': f'解析失败: {e}'})
    else:
        jwrite('zone_mob_roster.json', {'_raw': t[:8000], '_note': '未匹配MAP_MOBS'})
except Exception as e:
    print('  MAP_MOBS err', e)


# ===== I. 工具归档(思路重写参考) =====
print("[I] 工具归档...")
try:
    shutil.copy2(os.path.join(SRC, 'florr_powerful_tools\\florr_assistant\\modules\\pathing\\navigator.py'),
                 os.path.join(TOOLS, 'reference_navigator.py'))
    shutil.copy2(os.path.join(SRC, 'florr_powerful_tools\\scripts\\process_maps.py'),
                 os.path.join(TOOLS, 'reference_process_maps.py'))
    report.append(('tool', 'reference_navigator.py / reference_process_maps.py', 0))
except Exception as e:
    print('  tools err', e)

print("\n=== 转录完成 ===")
for kind, name, sz in report:
    print(f"  [{kind}] {name} ({sz} bytes)")
print(f"\n共 {len(report)} 项, 输出到 data/ + tools/")
