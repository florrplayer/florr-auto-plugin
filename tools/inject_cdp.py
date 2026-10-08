# -*- coding: utf-8 -*-
"""CDP 注入器: 连 Edge 调试端口, 把 hook 注入到每次新文档, 刷新页面触发"""
import json, sys, time, urllib.request
import websocket

CDP = 'http://127.0.0.1:9222'
HOOK_PATH = r'C:\Users\intel\Downloads\florr-auto-pathing-main\hook_inject.js'


def get_pages():
    with urllib.request.urlopen(CDP + '/json', timeout=5) as r:
        return json.loads(r.read())


def main():
    hook = open(HOOK_PATH, encoding='utf-8').read()
    pages = get_pages()
    page = None
    for p in pages:
        if p.get('type') == 'page':
            page = p
            break
    if not page:
        print('ERROR: 无页面', file=sys.stderr)
        sys.exit(1)
    ws_url = page['webSocketDebuggerUrl']
    ws = websocket.create_connection(ws_url, timeout=15)
    _mid = [0]

    def cmd(method, params=None):
        _mid[0] += 1
        ws.send(json.dumps({'id': _mid[0], 'method': method, 'params': params or {}}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get('id') == _mid[0]:
                if 'error' in msg:
                    return {'error': msg['error']}
                return msg.get('result', {})
            if msg.get('method') == 'Page.loadEventFired':
                continue

    cmd('Page.enable')
    cmd('Runtime.enable')
    res = cmd('Page.addScriptToEvaluateOnNewDocument', {'source': hook})
    print('addScript:', json.dumps(res, ensure_ascii=False)[:200])
    # 若不在 florr.io 则导航过去(新文档自动注入hook)
    nav = cmd('Page.navigate', {'url': 'https://florr.io'})
    print('navigate:', json.dumps(nav, ensure_ascii=False)[:120])
    print('loading, waiting...')
    time.sleep(14)
    chk = cmd('Runtime.evaluate', {'expression': 'window.__fh ? "hooked" : "no"', 'returnByValue': True})
    print('check:', json.dumps(chk, ensure_ascii=False)[:200])
    ws.close()


if __name__ == '__main__':
    main()
