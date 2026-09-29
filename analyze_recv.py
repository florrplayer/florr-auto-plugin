import json, zlib

with open('data/recv_late.json', 'r') as f:
    packets = json.load(f)

d = packets[0]['d']
print(f'包大小: {len(d)}B')
print(f'前16字节: {d[:16]}')

# 试各种解压
print('\n--- zlib ---')
try:
    r = zlib.decompress(bytes(d))
    print(f'成功! {len(r)}B: {r[:100]}')
except Exception as e:
    print(f'失败: {e}')

print('\n--- zlib raw (wbits=-15) ---')
try:
    r = zlib.decompress(bytes(d), -15)
    print(f'成功! {len(r)}B: {r[:100]}')
except Exception as e:
    print(f'失败: {e}')

print('\n--- gzip ---')
try:
    r = zlib.decompress(bytes(d), 31)
    print(f'成功! {len(r)}B: {r[:100]}')
except Exception as e:
    print(f'失败: {e}')

# 试跳过前N字节zlib raw
for skip in range(0, 10):
    try:
        r = zlib.decompress(bytes(d[skip:]), -15)
        print(f'skip={skip}: 成功! {len(r)}B')
        print(r[:200])
        break
    except:
        pass
else:
    print('都失败')
