# -*- coding: utf-8 -*-
"""游戏数据桥接服务器 - 接收浏览器扩展发来的实时游戏数据
用法: 先启动这个,再启动游戏,插件就能读实时内存数据
v1.29.2: 新增 /ws WebSocket 增量推送(延迟~200ms→<10ms), 向后兼容 HTTP 轮询
"""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json, threading, time, base64, hashlib, struct, socket

_latest = {}
_lock = threading.Lock()
_ws_clients = set()
_ws_lock = threading.Lock()

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def _ws_accept(key):
    return base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest()).decode()


def _ws_send(conn, payload):
    data = payload.encode() if isinstance(payload, str) else payload
    hdr = bytearray([0x81])
    n = len(data)
    if n < 126:
        hdr.append(n)
    elif n < 65536:
        hdr.append(126)
        hdr += struct.pack('>H', n)
    else:
        hdr.append(127)
        hdr += struct.pack('>Q', n)
    try:
        conn.sendall(bytes(hdr) + data)
        return True
    except Exception:
        return False


def _ws_read(conn):
    try:
        conn.settimeout(0.5)
        b0 = conn.recv(1)
        if not b0:
            return 'close'
        b1 = conn.recv(1)
        if not b1:
            return 'close'
        ln = b1[0] & 0x7F
        if ln == 126:
            ln = struct.unpack('>H', conn.recv(2))[0]
        elif ln == 127:
            ln = struct.unpack('>Q', conn.recv(8))[0]
        if b1[0] & 0x80:
            mask = conn.recv(4)
        else:
            mask = None
        payload = b''
        while len(payload) < ln:
            chunk = conn.recv(ln - len(payload))
            if not chunk:
                return 'close'
            payload += chunk
        if mask:
            payload = bytes(c ^ mask[i % 4] for i, c in enumerate(payload))
        opcode = b0[0] & 0x0F
        if opcode == 0x8:
            return 'close'
        if opcode == 0x9:
            _ws_send(conn, payload)
            return 'keep'
        if opcode == 0xA:
            return 'keep'
        return payload.decode('utf-8', 'replace')
    except socket.timeout:
        return 'keep'
    except Exception:
        return 'close'


def _ws_broadcast():
    with _lock:
        payload = json.dumps(_latest)
    with _ws_lock:
        dead = []
        for conn in list(_ws_clients):
            if not _ws_send(conn, payload):
                dead.append(conn)
        for conn in dead:
            _ws_clients.discard(conn)
            try:
                conn.close()
            except Exception:
                pass


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        if self.headers.get('Upgrade', '').lower() == 'websocket':
            key = self.headers.get('Sec-WebSocket-Key', '')
            self.send_response(101)
            self.send_header('Upgrade', 'websocket')
            self.send_header('Connection', 'Upgrade')
            self.send_header('Sec-WebSocket-Accept', _ws_accept(key))
            self.end_headers()
            conn = self.connection
            with _ws_lock:
                _ws_clients.add(conn)
            try:
                while True:
                    r = _ws_read(conn)
                    if r == 'close':
                        break
            finally:
                with _ws_lock:
                    _ws_clients.discard(conn)
                try:
                    conn.close()
                except Exception:
                    pass
            return
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(json.dumps(get_latest()).encode())))
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
            threading.Thread(target=_ws_broadcast, daemon=True).start()
        except Exception:
            pass
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', '2')
        self.end_headers()
        self.wfile.write(b'ok')

    def log_message(self, *a): pass


def start_server(port=18899):
    srv = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    print(f"[桥接] 服务器启动 http://127.0.0.1:{port}  (ws://127.0.0.1:{port}/ws 增量推送)")
    return srv


def get_latest():
    with _lock:
        return dict(_latest)


def get_ws_client_count():
    with _ws_lock:
        return len(_ws_clients)


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
                print(f"[桥接] 最近数据 {age:.1f}s前, mobs={len(mobs)}, mobData长度={len(mobdata)}, ws客户端={get_ws_client_count()}")
            else:
                print("[桥接] 等待中... (浏览器还没发数据)")
    except KeyboardInterrupt:
        print("\n退出")
