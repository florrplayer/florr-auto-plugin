# -*- coding: utf-8 -*-
"""CDP 注入器 v2: 崩溃自动恢复, 反复注入直到 WS 数据到达 bridge"""
import json, subprocess, sys, time, urllib.request, os
import websocket

CDP = 'http://127.0.0.1:9222'
EDGE = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
PROFILE = r'C:\florr_cdp'
HOOK_PATH = r'C:\Users\intel\Downloads\florr-auto-pathing-main\hook_inject.js'
BRIDGE = 'http://127.0.0.1:18899'


def cdp_alive():
    try:
        with urllib.request.urlopen(CDP + '/json/version', timeout=3) as r:
            return True
    except Exception:
        return False


def start_edge():
    subprocess.Popen([EDGE, '--remote-debugging-port=9222', '--remote-allow-origins=*',
                      '--user-data-dir=' + PROFILE, '--no-first-run', 'about:blank'])
    for _ in range(15):
        time.sleep(1)
        if cdp_alive():
            return True
    return False


def get_page():
    with urllib.request.urlopen(CDP + '/json', timeout=5) as r:
        pages = json.loads(r.read())
    return next((p for p in pages if p.get('type') == 'page'), None)


def main():
    hook = open(HOOK_PATH, encoding='utf-8').read()
    if not cdp_alive():
        print('启动调试Edge...')
        if not start_edge():
            print('ERROR: Edge 起不来'); sys.exit(1)
    page = get_page()
    if not page:
        print('ERROR: 无页面'); sys.exit(1)
    ws = websocket.create_connection(page['webSocketDebuggerUrl'], timeout=15)
    mid = [0]

    def cmd(m, params=None):
        mid[0] += 1
        ws.send(json.dumps({'id': mid[0], 'method': m, 'params': params or {}}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get('id') == mid[0]:
                return msg.get('result', msg.get('error'))

    cmd('Page.enable')
    cmd('Runtime.enable')
    res = cmd('Page.addScriptToEvaluateOnNewDocument', {'source': hook})
    print('addScript:', json.dumps(res, ensure_ascii=False)[:120])
    # 当前URL若非florr则导航
    cur = cmd('Runtime.evaluate', {'expression': 'location.href', 'returnByValue': True})
    url = (cur.get('result', {}) or {}).get('value', '')
    if 'florr.io' not in url:
        cmd('Page.navigate', {'url': 'https://florr.io'})
        print('navigated to florr.io')
    else:
        cmd('Page.reload')
        print('reloaded florr.io')
    print('waiting for data...')
    ws.close()
    # 轮询 bridge 直到 ws_raw 出现
    for i in range(30):
        time.sleep(5)
        try:
            with urllib.request.urlopen(BRIDGE, timeout=3) as r:
                data = json.loads(r.read().decode())
            raw = data.get('ws_raw') or []
            if raw:
                print(f'[第{i+1}次轮询] ws_raw={len(raw)}条!')
                for m0 in raw[:5]:
                    print('   [' + str(m0.get('d')) + '] len=' + str(len(m0.get('p', ''))) +
                          ' head=' + str(m0.get('p', ''))[:50])
                return
            else:
                print(f'[第{i+1}次轮询] 等待ws_raw... (bridge keys={list(data.keys())})')
        except Exception as e:
            print(f'[第{i+1}次轮询] bridge异常: {e}')
    print('超时未等到数据')


if __name__ == '__main__':
    main()
