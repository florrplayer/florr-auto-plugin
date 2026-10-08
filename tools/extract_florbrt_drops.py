# -*- coding: utf-8 -*-
"""榨干 FlorrBt drop_rate.h (v2 括号平衡版):
1) RegisterDropRateTable(EMobType, EPetalType, {三元组列表}) 完整解析
2) RegisterDropRate(EMobType, ERarity, EPetalType, ERarity, prob) 单条
输出 -> data/florbrt_drops_full.json: {mob: {petal: [(mob_rar, drop_rar, prob)...]}}"""
import json, os, re

BASE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(BASE, 'reference-florr-tools', 'FlorrBt', 'src', 'Shared', 'drop_rate.h')
src = open(p, encoding='utf-8').read()

TRIPLE = re.compile(r'\{[^{}]*\}')
def parse_triples(text):
    """从三元组列表文本提取 [(mob_rar, drop_rar, prob)]"""
    out = []
    for t in TRIPLE.findall(text):
        m = re.match(r'\{\s*ERarity::(\w+)\s*,\s*ERarity::(\w+)\s*,\s*([\d.e+-]+)\s*\}', t)
        if m:
            out.append((m.group(1).lower(), m.group(2).lower(), float(m.group(3))))
    return out

def parse_balanced(start):
    depth = 0
    in_str = esc = False
    for k in range(start, len(src)):
        c = src[k]
        if in_str:
            if esc: esc = False
            elif c == '\\': esc = True
            elif c == '"': in_str = False
            continue
        if c == '"': in_str = True
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return k + 1
    return len(src)

# ---- 1) RegisterDropRateTable 大表 ----
agg = {}  # mob -> {petal: [(mr, dr, prob)]}
count_tables = 0
for m in re.finditer(r'RegisterDropRateTable\(\s*EMobType::(\w+)\s*,\s*EPetalType::(\w+)\s*,\s*\{', src):
    mob, petal = m.group(1), m.group(2)
    brace = m.end() - 1  # 定位 '{'
    end = parse_balanced(brace)
    triples = parse_triples(src[brace:end])
    agg.setdefault(mob, {}).setdefault(petal, []).extend(triples)
    count_tables += 1

# ---- 2) RegisterDropRate 单条 ----
count_singles = 0
for m in re.finditer(r'RegisterDropRate\(\s*EMobType::(\w+)\s*,\s*ERarity::(\w+)\s*,\s*EPetalType::(\w+)\s*,\s*ERarity::(\w+)\s*,\s*([\d.e+-]+)\)', src):
    mob, mr, petal, dr, prob = m.groups()
    agg.setdefault(mob, {}).setdefault(petal, []).append((mr.lower(), dr.lower(), float(prob)))
    count_singles += 1

print('大表:', count_tables, '| 单条:', count_singles, '| 怪数:', len(agg))
total = sum(len(rows) for petals in agg.values() for rows in petals.values())
print('总掉率行数:', total)

# 校验: 所有 mr 都是合法稀有度
bad = [(mob, petal, t) for mob, petals in agg.items() for petal, rows in petals.items()
       for t in rows if t[0] not in ('common','unusual','rare','epic','legendary','mythic','ultra','super','unique')]
print('异常行:', len(bad), bad[:3])

out = os.path.join(BASE, 'data', 'florbrt_drops_full.json')
json.dump({'source': 'FlorrBt drop_rate.h (括号平衡版)', 'mobs': agg},
          open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('已存:', out)
