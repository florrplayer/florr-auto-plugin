import json

with open('data/all_mobs.json', 'r', encoding='utf-8') as f:
    raw = f.read()

# 数据是多个JSON对象连在一起(不是数组),需要分割
# 每个对象以 { 开头, } 结尾, 用换行分隔
mobs = []
depth = 0
start = 0
for i, c in enumerate(raw):
    if c == '{':
        if depth == 0:
            start = i
        depth += 1
    elif c == '}':
        depth -= 1
        if depth == 0:
            try:
                obj = json.loads(raw[start:i+1])
                mobs.append(obj)
            except:
                pass

print(f"解析到 {len(mobs)} 个怪物")

# 提取关键数据
RARITY_NAMES = ['Common','Rare','Super','Epic','Legendary','Mythic','Ultra','Super','Unique']
parsed = []
for m in mobs:
    sid = m.get('sid', '?')
    drops = m.get('drops', [])
    rarities = m.get('rarities', [])
    info = {'sid': sid, 'drops': drops, 'rarities': []}
    for idx, r in enumerate(rarities[:8]):
        tooltip = r.get('tooltip', [])
        exp = r.get('exp', 0)
        row = {'rarity': RARITY_NAMES[idx] if idx < len(RARITY_NAMES) else f'R{idx}', 'exp': exp}
        for t in tooltip:
            if len(t) >= 2:
                key = t[0].split('/')[-1]
                row[key] = t[1:] if len(t) > 2 else t[1]
        info['rarities'].append(row)
    parsed.append(info)

# 打印摘要
for p in parsed[:15]:
    r0 = p['rarities'][0] if p['rarities'] else {}
    r7 = p['rarities'][7] if len(p['rarities']) > 7 else {}
    hp0 = r0.get('HealthRange', r0.get('Health', '?'))
    hp7 = r7.get('HealthRange', r7.get('Health', '?'))
    print(f"  {p['sid']:20s} Common HP={hp0}  Ultra HP={hp7}")

# 保存解析后的数据
with open('data/mob_stats_full.json', 'w', encoding='utf-8') as f:
    json.dump(parsed, f, ensure_ascii=False, indent=2)
print(f"\n已保存 data/mob_stats_full.json ({len(parsed)}怪物)")
