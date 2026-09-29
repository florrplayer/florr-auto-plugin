import re, json

with open('wasm_dump/client.wasm', 'rb') as f:
    data = f.read()

# 提取所有可读字符串
strings = re.findall(rb'[\x20-\x7e]{3,}', data)
strings = [s.decode('ascii', errors='ignore') for s in strings]

# 找花瓣名
petals = set()
for s in strings:
    # 花瓣名模式
    if re.match(r'^[a-z_]+$', s) and len(s) > 3 and len(s) < 30:
        petals.add(s)

# 找怪物名(从掉落表反推)
mob_names = set()
for s in strings:
    # "ant_soldier:10;worm:0.3" 这种
    m = re.findall(r'([a-z_]+):[\d.]+', s)
    for x in m:
        if len(x) > 3 and '_' in x or x in ['worm','rock','shell','bush','cactus','spider']:
            mob_names.add(x)

# 找地图区域
regions = set()
for s in strings:
    m = re.findall(r'(desert_[a-z]_\d|ocean_[a-z]_\d|garden_[a-z]_\d|jungle_[a-z]_\d|anthell_[a-z]_\d)', s)
    for x in m:
        regions.add(x)

# 找稀有度
rarities = set()
for s in strings:
    if s.lower() in ['common','rare','super','epic','legendary','mythic','ultra','unique']:
        rarities.add(s)

print('=== 怪物名(从掉落表) ===')
for m in sorted(mob_names):
    print(f'  {m}')

print(f'\n=== 地图区域块 ===')
for r in sorted(regions):
    print(f'  {r}')

print(f'\n=== 稀有度 ===')
for r in sorted(rarities):
    print(f'  {r}')

# 找所有SVG图片名
svgs = set()
for s in strings:
    if s.endswith('.svg'):
        svgs.add(s)
print(f'\n=== SVG图片 ({len(svgs)}个) ===')
for s in sorted(svgs)[:50]:
    print(f'  {s}')
