# -*- coding: utf-8 -*-
"""CDP targets 诊断"""
import json, sys, urllib.request
import websocket

with urllib.request.urlopen('http://127.0.0.1:9222/json', timeout=5) as r:
    pages = json.loads(r.read())
page = next((p for p in pages if p.get('type') == 'page'), None)
if not page:
    print('无页面'); sys.exit(1)
ws = websocket.create_connection(page['webSocketDebuggerUrl'], timeout=15)
mid = [0]
def cmd(m, params=None):
    mid[0] += 1
    ws.send(json.dumps({'id': mid[0], 'method': m, 'params': params or {}}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get('id') == mid[0]:
            return msg.get('result', msg.get('error'))
res = cmd('Target.getTargets')
for t in res.get('targetInfos', []):
    print(f"target: type={t.get('type')} title={t.get('title','')[:40]} url={t.get('url','')[:80]}")
ws.close()
