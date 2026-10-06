# -*- coding: utf-8 -*-
"""CDP 网络抓包: Network.enable 抓全部 m28 API 请求/响应(浏览器层, 页面卡死也能抓)"""
import json, sys, time, urllib.request
import websocket

with urllib.request.urlopen('http://127.0.0.1:9222/json', timeout=5) as r:
    pages = json.loads(r.read())
page = next((p for p in pages if p.get('type') == 'page'), None)
if not page:
    print('无页面'); sys.exit(1)
ws = websocket.create_connection(page['webSocketDebuggerUrl'], timeout=20)
mid = [0]
reqs = {}

def cmd(m, params=None):
    mid[0] += 1
    ws.send(json.dumps({'id': mid[0], 'method': m, 'params': params or {}}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get('id') == mid[0]:
            return msg.get('result', msg.get('error'))

cmd('Page.enable')
cmd('Runtime.enable')
cmd('Network.enable')
print('Network 抓包启动, 收集60秒...')
start = time.time()
count = 0
while time.time() - start < 60:
    try:
        msg = json.loads(ws.recv())
    except Exception:
        continue
    m = msg.get('method', '')
    if m == 'Network.requestWillBeSent':
        p = msg.get('params', {})
        url = p.get('request', {}).get('url', '')
        rid = p.get('requestId', '')
        reqs[rid] = url
        if 'm28' in url or 'florr' in url.lower():
            count += 1
            print(f"[req] {url[:130]}")
    elif m == 'Network.responseReceived':
        p = msg.get('params', {})
        rid = p.get('requestId', '')
        url = reqs.get(rid, '')
        status = p.get('response', {}).get('status', '')
        if 'm28' in url or 'florr' in url.lower():
            print(f"[resp] {status} {url[:130]}")
            # 抓响应体(仅文本型)
            try:
                r2 = cmd('Network.getResponseBody', {'requestId': rid})
                body = (r2.get('body') or '')[:200]
                print(f"        body: {body}")
            except Exception:
                pass
ws.close()
print(f"完成, 共{count}条m28/florr请求")
