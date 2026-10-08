import base64, os

os.makedirs('data/mob_icons', exist_ok=True)

with open('data/mob_icons.txt', 'r') as f:
    lines = f.read().strip().split('\n')

count = 0
for line in lines:
    if '|' not in line:
        continue
    mid, data_url = line.split('|', 1)
    if 'base64,' in data_url:
        b64 = data_url.split('base64,')[1]
        try:
            img = base64.b64decode(b64)
            path = f'data/mob_icons/mob_{mid}.png'
            with open(path, 'wb') as out:
                out.write(img)
            count += 1
        except:
            pass

print(f"解码了 {count} 个PNG到 data/mob_icons/")
# 列一下
files = os.listdir('data/mob_icons')
print(f"目录里有 {len(files)} 个文件")
for f in sorted(files)[:5]:
    sz = os.path.getsize(f'data/mob_icons/{f}')
    print(f"  {f}: {sz} bytes")
