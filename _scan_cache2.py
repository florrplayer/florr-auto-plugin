# -*- coding: utf-8 -*-
"""增强版: 读缓存全文件, 用 florr 游戏特有词命中"""
import os

roots = [
    r"C:\Users\intel\AppData\Local\Microsoft\Edge\User Data\Default\Cache\Cache_Data",
    r"C:\Users\intel\AppData\Local\Microsoft\Edge\User Data\Default\Code Cache\js",
    r"C:\Users\intel\AppData\Local\Microsoft\Edge\User Data\Default\Service Worker\CacheStorage",
]
keys = [b"hitbox", b"florr", b"mythic", b"MINIMAP", b"petal", b"garden", b"bee", b"centipede", b"ladybug"]
hits = []
scanned = 0
for root in roots:
    if not os.path.isdir(root):
        print("skip:", root); continue
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            try:
                sz = os.path.getsize(fp)
            except OSError:
                continue
            if sz < 1024 or sz > 60 * 1024 * 1024:
                continue
            scanned += 1
            try:
                with open(fp, "rb") as f:
                    data = f.read()
            except OSError:
                continue
            score = sum(1 for k in keys if k in data)
            if score >= 3:
                hits.append((score, sz, fp))
print("scanned:", scanned)
for score, sz, fp in sorted(hits, reverse=True)[:30]:
    print(score, sz, fp)
