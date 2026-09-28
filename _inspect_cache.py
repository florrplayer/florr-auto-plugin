# -*- coding: utf-8 -*-
"""检查命中的 SW 缓存文件内容, 提取 radius/hitbox/mob 定义上下文"""
import re

files = [
    (r"C:\Users\intel\AppData\Local\Microsoft\Edge\User Data\Default\Service Worker\CacheStorage\0ce936e7575206b1684492fbff34590eba411a5d\0fe395bd-8eaa-4eb3-bb44-75e0d6318cc0\55bc565ca9cf3d3c_0", "h5-283k"),
    (r"C:\Users\intel\AppData\Local\Microsoft\Edge\User Data\Default\Service Worker\CacheStorage\0ce936e7575206b1684492fbff34590eba411a5d\0fe395bd-8eaa-4eb3-bb44-75e0d6318cc0\bdd531f639464a1b_0", "h5-106k"),
    (r"C:\Users\intel\AppData\Local\Microsoft\Edge\User Data\Default\Service Worker\CacheStorage\0ce936e7575206b1684492fbff34590eba411a5d\0fe395bd-8eaa-4eb3-bb44-75e0d6318cc0\5e85287c601d4fd6_0", "h4-214k"),
]
for fp, tag in files:
    data = open(fp, "rb").read()
    print(f"\n=== {tag} {len(data)}B ===")
    head = data[:200]
    print("head:", head[:120])
    for kw in (b"radius", b"hitbox", b"mobs", b"size"):
        idxs = [m.start() for m in re.finditer(kw, data)]
        print(f"  '{kw.decode()}': {len(idxs)} hits")
        if idxs:
            i = idxs[0]
            seg = data[max(0, i - 80): i + 160]
            print("   ctx:", seg)
