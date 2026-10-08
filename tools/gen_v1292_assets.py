# -*- coding: utf-8 -*-
"""从克隆源数据重新生成 v1.29.2 资产: petal_colors.json / spawn_tuning.json"""
import json, os

DATA = r'C:\Users\intel\Downloads\florr-auto-pathing-main\data'

# 1. petal_colors.json: 从 clone_petals.json 提取每个花瓣的基础颜色/尺寸/伤害/血量/冷却
petals = json.load(open(os.path.join(DATA, 'clone_petals.json'), encoding='utf-8'))
if isinstance(petals, dict):
    # 可能是 {sid: {...}} 或 {'petals': [...]}
    items = petals.get('petals', []) if 'petals' in petals else list(petals.values())
else:
    items = petals
out = {}
for p in items:
    if not isinstance(p, dict):
        continue
    sid = p.get('sid') or p.get('id') or p.get('name')
    if not sid:
        continue
    color = p.get('color')
    if not color:
        # 尝试嵌套
        color = (p.get('render') or {}).get('color') or (p.get('base') or {}).get('color')
    if not color:
        continue
    out[sid] = {
        'cn': p.get('cn') or p.get('name'),
        'color': color,
        'size': p.get('size', 1),
        'damage': p.get('damage', 0),
        'health': p.get('health', 0),
        'cooldown': p.get('cooldown', 0),
    }
json.dump(out, open(os.path.join(DATA, 'petal_colors.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'petal_colors.json: {len(out)} 个花瓣')

# 2. spawn_tuning.json: 刷怪调优 + 官方刷怪数学(难度/幸运/稀有度)
tuning = {}
try:
    st = json.load(open(os.path.join(DATA, 'clone_spawning_tuning.json'), encoding='utf-8'))
    tuning = st.get('tuning', st) if isinstance(st, dict) else st
except Exception as e:
    print('spawning_tuning err', e)
difficulty = {}
try:
    sd = json.load(open(os.path.join(DATA, 'clone_spawn_difficulty.json'), encoding='utf-8'))
    difficulty = sd.get('difficulty', sd) if isinstance(sd, dict) else sd
except Exception as e:
    print('spawn_difficulty err', e)

def parse_vals(s):
    """把 '{0.40, 0.30, ...}' / '2.0 * 60.0 * 1000.0' 解析成数值/数组 (去C++注释)"""
    s = s.strip()
    # 去 // 注释
    lines = []
    for ln in s.split('\n'):
        i = ln.find('//')
        lines.append(ln[:i] if i >= 0 else ln)
    s = '\n'.join(lines)
    if s.startswith('{'):
        # 优先抓 '{-?\d+\.?\d*, -?\d+\.?\d*}' 锚点对
        pairs = re.findall(r'\{\s*([-0-9.eE]+)\s*,\s*([-0-9.eE]+)\s*\}', s)
        if pairs:
            return [[float(a), float(b)] for a, b in pairs]
        s = s.strip('{}')
        parts = []
        for tok in s.replace('\n', ' ').split(','):
            tok = tok.strip()
            if not tok:
                continue
            m2 = re.match(r'^\{\s*([-0-9.eE]+)\s*,\s*([-0-9.eE]+)\s*\}$', tok)
            if m2:
                parts.append([float(m2.group(1)), float(m2.group(2))])
            else:
                try:
                    parts.append(float(tok))
                except ValueError:
                    pass
        return parts
    # 简单算术表达式
    try:
        return eval(s.replace('static_cast<double>(kRarityCount - 1)', '8'))
    except Exception:
        return s

import re
D = {}
d = difficulty
D['kDifficultyAnchors'] = parse_vals(d.get('kDifficultyAnchors', ''))
D['kNaturalRaritySpread'] = parse_vals(d.get('kNaturalRaritySpread', ''))
D['kNeutralSpawnLuck'] = parse_vals(d.get('kNeutralSpawnLuck', '1.0'))
D['kTierValuePerLuckPoint'] = parse_vals(d.get('kTierValuePerLuckPoint', '0.01'))
D['kMaxTierValue'] = 8.0
D['_raw'] = {k: v for k, v in d.items() if k.startswith('k')}
spawn = {'source': 'florr_clone cpp (spawning.h/difficulty.h)', 'tuning': tuning, 'difficulty': D}
json.dump(spawn, open(os.path.join(DATA, 'spawn_tuning.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('spawn_tuning.json:')
print(json.dumps(D, ensure_ascii=False)[:500])
