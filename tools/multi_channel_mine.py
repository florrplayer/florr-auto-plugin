# -*- coding: utf-8 -*-
"""多渠道挖掘: Gitee / Greasy Fork / GitHub code search / fandom wiki API"""
import json, urllib.request, ssl, re, os

ctx = ssl._create_unverified_context()

def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) florr-research'})
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            return r.read().decode('utf-8', 'ignore')
    except Exception as e:
        return 'ERR: ' + str(e)

# 1. Gitee 仓库搜索
print('=== Gitee 搜索 florr ===')
raw = get('https://gitee.com/api/v5/search/repositories?q=florr&per_page=20')
if raw.startswith('ERR'):
    print(' ', raw)
else:
    try:
        for r in json.loads(raw)[:15]:
            fn = r.get('full_name', '?')
            st = r.get('stargazers_count', 0)
            ds = str(r.get('description') or '')[:60]
            print('  %-40s %d星 %s' % (fn, st, ds))
    except Exception as e:
        print('  解析失败', e, raw[:200])

# 2. Greasy Fork 油猴脚本
print()
print('=== Greasy Fork florr 脚本 ===')
html = get('https://greasyfork.org/zh-CN/scripts?q=florr')
if html.startswith('ERR'):
    print(' ', html)
else:
    titles = re.findall(r'<a[^>]*class="script-link"[^>]*>([^<]+)</a>', html)
    links = re.findall(r'<a[^>]*class="script-link"[^>]*href="([^"]+)"', html)
    print('  找到 %d 个脚本:' % len(titles))
    for t, l in list(zip(titles, links))[:15]:
        print('  %-50s https://greasyfork.org%s' % (t.strip(), l))

# 3. GitHub code search (限流可能恢复, 试一次)
print()
print('=== GitHub code search: florr drop_rate ===')
code = get('https://api.github.com/search/code?q=florr+drop_rate+in:file&per_page=10',
           {'User-Agent': 'florr-research', 'Accept': 'application/vnd.github+json'})
if code.startswith('ERR'):
    print(' ', code)
else:
    try:
        for it in json.loads(code).get('items', [])[:10]:
            print('  %-50s %s' % (it.get('name'), it.get('html_url')))
    except Exception as e:
        print('  解析失败', e)

# 4. fandom 英文维基 API
print()
print('=== florr fandom 维基 ===')
w = get('https://florr.fandom.com/api.php?action=query&titles=Rose&prop=revisions&rvprop=content&rvslots=main&format=json&formatversion=2')
if w.startswith('ERR'):
    print(' ', w)
else:
    try:
        d = json.loads(w)
        page = d.get('query', {}).get('pages', [{}])[0]
        rev = page.get('revisions', [{}])[0]
        content = rev.get('slots', {}).get('main', {}).get('content', '')
        print('  Rose 页面存在, 内容 %d 字符' % len(content))
        print('  摘要:', content[:150].replace('\n', ' '))
    except Exception as e:
        print('  解析失败', e, w[:200])
