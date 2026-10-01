# -*- coding: utf-8 -*-
"""游戏数据桥接服务器 - 接收浏览器扩展发来的实时游戏数据
用法: 先启动这个,再启动游戏,插件就能读实时内存数据
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, threading, time

_latest = {}
_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        # 其他进程从这里拉最新数据
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(get_latest()).encode())

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
            with _lock:
                _latest.update(data)
                _latest['_recv_time'] = time.time()
        except:
            pass
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(b'ok')

    def log_message(self, *a): pass


def start_server(port=18899):
    srv = HTTPServer(('127.0.0.1', port), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    print(f"[桥接] 服务器启动 http://127.0.0.1:{port}")
    return srv


def get_latest():
    with _lock:
        return dict(_latest)


if __name__ == '__main__':
    start_server()
    print("等待浏览器数据... (Ctrl+C退出)")
    try:
        while True:
            time.sleep(2)
            d = get_latest()
            if d.get('_recv_time'):
                age = time.time() - d['_recv_time']
                mobs = d.get('mobs', [])
                mobdata = d.get('mobData', '')
                print(f"[桥接] 最近数据 {age:.1f}s前, mobs={len(mobs)}, mobData长度={len(mobdata)}")
            else:
                print("[桥接] 等待中... (浏览器还没发数据)")
    except KeyboardInterrupt:
        print("\n退出")
