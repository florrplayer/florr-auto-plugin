# -*- coding: utf-8 -*-
"""CDP 状态检查"""
import json, sys, urllib.request
import websocket

def get_pages():
    with urllib.request.urlopen('http://127.0.0.1:9222/json', timeout=5) as r:
        return json.loads(r.read())

pages = get_pages()
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
res = cmd('Runtime.evaluate', {'expression': 'document.title + " | " + location.href + " | fh=" + (window.__fh?"1":"0")', 'returnByValue': True})
print('page:', res.get('result', {}).get('value'))
res2 = cmd('Runtime.evaluate', {'expression': 'document.body ? document.body.innerText.slice(0,300) : "no body"', 'returnByValue': True})
print('body:', res2.get('result', {}).get('value', '')[:300])
ws.close()
