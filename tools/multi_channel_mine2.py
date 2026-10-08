# -*- coding: utf-8 -*-
"""渠道挖掘 round2: florr.wiki.gg官方wiki / Gitee网页 / Codeberg / PyPI / npm"""
import json, urllib.request, ssl, re

ctx = ssl._create_unverified_context()
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'

def get(url, headers=None, timeout=15):
    req = urllib.request.Request(url, headers=headers or {'User-Agent': UA, 'Accept': '*/*'})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.read().decode('utf-8', 'ignore')
    except Exception as e:
        return 'ERR: ' + str(e)

# 1. florr.wiki.gg 官方 wiki API
print('=== florr.wiki.gg 官方wiki ===')
w = get('https://florr.wiki.gg/api.php?action=query&meta=siteinfo&siprop=general&format=json')
if w.startswith('ERR'):
    print(' ', w)
else:
    try:
        g = json.loads(w).get('query', {}).get('general', {})
        print('  wiki名: %s | 条目数: %s' % (g.get('sitename'), g.get('articles')))
    except Exception as e:
        print('  解析失败', e)

# 2. Gitee 网页搜索 (HTML)
print()
print('=== Gitee 网页搜索 florr ===')
h = get('https://gitee.com/search?q=florr&type=repository')
if h.startswith('ERR'):
    print(' ', h)
else:
    names = re.findall(r'data-full-name="([^"]+)"', h)
    if not names:
        names = re.findall(r'href="/([A-Za-z0-9_\-\.]+/[A-Za-z0-9_\-\.]+)"[^>]*class="[^"]*repo', h)
    print('  找到 %d 个:' % len(names))
    for n in names[:20]:
        print('  https://gitee.com/' + n)

# 3. Codeberg 搜索 (API)
print()
print('=== Codeberg florr ===')
c = get('https://codeberg.org/api/v1/repos/search?q=florr&limit=20')
if c.startswith('ERR'):
    print(' ', c)
else:
    try:
        for r in json.loads(c).get('data', [])[:15]:
            print('  %-45s %d星 %s' % (r.get('full_name'), r.get('stars_count', 0), str(r.get('description') or '')[:50]))
    except Exception as e:
        print('  解析失败', e)

# 4. PyPI florr 包
print()
print('=== PyPI florr 包 ===')
p = get('https://pypi.org/pypi/florr-autofarm/json', timeout=8)
if p.startswith('ERR'):
    print('  无 florr-autofarm 包:', p[:80])
else:
    print('  florr-autofarm 存在!')

# 5. npm florr
print()
print('=== npm florr ===')
n = get('https://registry.npmjs.org/-/v1/search?text=florr&size=10')
if n.startswith('ERR'):
    print(' ', n)
else:
    try:
        for o in json.loads(n).get('objects', [])[:10]:
            pkg = o.get('package', {})
            print('  %-40s %s' % (pkg.get('name'), str(pkg.get('description') or '')[:55]))
    except Exception as e:
        print('  解析失败', e)
