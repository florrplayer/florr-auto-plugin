import json, lz4.block, zlib

with open('data/recv_late.json', 'r') as f:
    packets = json.load(f)

d = packets[0]['d']
print(f'包0: {len(d)}B, 首字节=0x{d[0]:02x}')

# 试跳过前1字节(LZ4 block)
for skip in [0, 1, 2, 3, 4]:
    for usize in [2000, 5000, 10000, 50000]:
        try:
            r = lz4.block.decompress(bytes(d[skip:]), uncompressed_size=usize)
            print(f'LZ4 skip={skip} usize={usize}: 成功! {len(r)}B')
            print('前200字节:', r[:200])
            break
        except Exception as e:
            pass
    else:
        continue
    break
else:
    print('LZ4 都失败')

# 试 zstd
try:
    import zstandard as zstd
    print('\n试zstd...')
    for skip in range(5):
        try:
            dctx = zstd.ZstdDecompressor()
            r = dctx.decompress(bytes(d[skip:]), max_output_size=100000)
            print(f'zstd skip={skip}: {len(r)}B: {r[:200]}')
            break
        except:
            pass
except ImportError:
    print('无zstd')

# 试 brotli
try:
    import brotli
    print('\n试brotli...')
    for skip in range(5):
        try:
            r = brotli.decompress(bytes(d[skip:]))
            print(f'brotli skip={skip}: {len(r)}B: {r[:200]}')
            break
        except:
            pass
except ImportError:
    print('无brotli')
