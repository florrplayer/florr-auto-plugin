# -*- coding: utf-8 -*-
"""扫 wasm UTF-16 中文串 (i18n 内嵌检测)"""
import re

data = open(r'C:\Users\intel\Downloads\florr-auto-pathing-main\data\current_client.wasm', 'rb').read()
ALLOW = set('，。！？：；、()"%+-*/. 0123456789')

cn16 = []
i = 0
n = len(data)
while i < n - 1:
    try:
        ch = data[i:i + 2].decode('utf-16-le')
    except Exception:
        i += 1
        continue
    if '\u4e00' <= ch <= '\u9fff':
        j = i
        buf = []
        while j < n - 1:
            try:
                c = data[j:j + 2].decode('utf-16-le')
            except Exception:
                break
            if '\u4e00' <= c <= '\u9fff' or c in ALLOW:
                buf.append(c)
                j += 2
            else:
                break
        t = ''.join(buf)
        if len(t) >= 3 and re.search(r'[\u4e00-\u9fff]', t):
            cn16.append(t)
            i = j
            continue
    i += 1

print('UTF-16 中文串: %d' % len(cn16))
for t in cn16[:80]:
    print(' ', t[:70])
