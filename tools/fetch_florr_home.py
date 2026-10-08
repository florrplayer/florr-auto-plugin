# -*- coding: utf-8 -*-
"""B路替代: 抓 florr.io 首页 -> 解析官方资源清单(i18n/配置/wasm真实路径)"""
import json, urllib.request, ssl, re

ctx = ssl._create_unverified_context()
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'

def get(url, timeout=15):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*', 'Accept-Language': 'zh-CN,zh;q=0.9'})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read().decode('utf-8', 'ignore')
    except Exception as e:
        return None, 'ERR: ' + str(e)

st, html = get('https://florr.io/')
print('首页状态:', st)
if st and st == 200:
    print('HTML 大小:', len(html))
    # 1. 所有 script/link 资源
    scripts = re.findall(r'<script[^>]*src="([^"]+)"', html)
    links = re.findall(r'<link[^>]*href="([^"]+)"', html)
    print('\n=== 脚本资源 ===')
    for s in scripts: print(' ', s)
    print('=== 样式/其他资源 ===')
    for l in links: print(' ', l)
    # 2. 内联配置/关键线索
    for pat in ['i18n', 'locale', 'lang', 'config', 'cdn', 'static.florr', 'client.js', 'wasm', 'cloudflare', 'token', 'api']:
        for m in re.finditer(pat, html, re.I):
            s = max(0, m.start() - 80)
            seg = html[s:m.start() + 120].replace('\n', ' ')
            print('\n[%s] ...%s...' % (pat, seg[:260]))
            break
else:
    print(html if not st else '')
