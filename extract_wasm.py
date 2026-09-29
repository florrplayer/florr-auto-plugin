import re, json

with open('wasm_dump/client.wasm', 'rb') as f:
    data = f.read()

# 提取所有字符串(>=3字符)
all_strings = re.findall(rb'[\x20-\x7e]{3,}', data)
all_strings = [s.decode('ascii', errors='ignore') for s in all_strings]

# 去重
all_strings = sorted(set(all_strings))
print(f'总唯一字符串: {len(all_strings)}')

# 分类输出
categories = {
    'chat_commands': [],
    'i18n_keys': [],
    'petal_names': [],
    'mob_names': [],
    'map_tiles': [],
    'achievements': [],
    'talents': [],
    'errors': [],
    'changelog': [],
    'urls': [],
    'colors': [],
    'other_useful': []
}

for s in all_strings:
    sl = s.lower()
    if s.startswith('/') and len(s) < 40:
        categories['chat_commands'].append(s)
    elif s.startswith('UI/') or s.startswith('Chat/') or s.startswith('Mobs/') or s.startswith('Petals/') or s.startswith('Talents/'):
        categories['i18n_keys'].append(s)
    elif s.startswith('Petals/') and '/Name' in s:
        categories['petal_names'].append(s)
    elif s.startswith('Mobs/') and '/Name' in s:
        categories['mob_names'].append(s)
    elif s.startswith('tiles/') or '.svg' in s:
        categories['map_tiles'].append(s)
    elif s.startswith('Achievements/'):
        categories['achievements'].append(s)
    elif s.startswith('Talents/'):
        categories['talents'].append(s)
    elif 'error' in sl or 'invalid' in sl or 'missing' in sl:
        categories['errors'].append(s)
    elif s.startswith('- ') and any(k in s for k in ['fix','add','change','buff','nerf','new','update','balance']):
        categories['changelog'].append(s)
    elif s.startswith('http'):
        categories['urls'].append(s)
    elif s.startswith('#') and len(s) < 10:
        categories['colors'].append(s)

# 输出
for cat, items in categories.items():
    print(f'\n=== {cat} ({len(items)}) ===')
    for s in items[:30]:
        print(f'  {s[:120]}')

# 保存完整
with open('wasm_dump/all_strings.txt', 'w', encoding='utf-8') as f:
    for s in all_strings:
        f.write(s + '\n')
print(f'\n完整字符串已保存到 wasm_dump/all_strings.txt')
