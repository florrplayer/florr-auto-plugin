# -*- coding: utf-8 -*-
"""bridge WebSocket 增量订阅客户端 (v1.29.2)
- 后台线程连 ws://127.0.0.1:18899/ws, 收到帧即缓存最新状态
- get_latest() 本地读缓存, 零网络 IO (延迟<10ms)
- 断线自动重连(指数退避), 从未连上时返回 None (调用方回退 HTTP 轮询)
"""
import json, socket, threading, time, base64, hashlib, struct, os

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_cache = {}
_lock = threading.Lock()
_alive = False
_stop = False


def _handshake(host, port):
    s = socket.create_connection((host, port), timeout=3)
    key = base64.b64encode(os.urandom(16)).decode()
    req = (f"GET /ws HTTP/1.1\r\n"
           f"Host: {host}:{port}\r\n"
           f"Upgrade: websocket\r\n"
           f"Connection: Upgrade\r\n"
           f"Sec-WebSocket-Key: {key}\r\n"
           f"Sec-WebSocket-Version: 13\r\n\r\n")
    s.sendall(req.encode())
    resp = b''
    while b'\r\n\r\n' not in resp:
        chunk = s.recv(4096)
        if not chunk:
            raise ConnectionError("握手失败: 连接关闭")
        resp += chunk
    if b'101' not in resp.split(b'\r\n', 1)[0]:
        raise ConnectionError(f"握手被拒: {resp.split(chr(10).encode())[0].decode(errors='replace')}")
    return s


def _recv_frame(s):
    h = s.recv(2)
    if not h or len(h) < 2:
        raise ConnectionError("帧头缺失")
    b0, b1 = h[0], h[1]
    ln = b1 & 0x7F
    if ln == 126:
        ln = struct.unpack('>H', s.recv(2))[0]
    elif ln == 127:
        ln = struct.unpack('>Q', s.recv(8))[0]
    payload = b''
    while len(payload) < ln:
        chunk = s.recv(ln - len(payload))
        if not chunk:
            raise ConnectionError("帧体中断")
        payload += chunk
    opcode = b0 & 0x0F
    if opcode == 0x8:
        raise ConnectionError("服务端关闭")
    return payload


def _pump(host, port):
    global _cache, _alive
    backoff = 0.5
    while not _stop:
        try:
            s = _handshake(host, port)
            backoff = 0.5
            with _lock:
                _alive = True
            s.settimeout(10)
            while not _stop:
                payload = _recv_frame(s)
                try:
                    d = json.loads(payload.decode('utf-8', 'replace'))
                    if isinstance(d, dict):
                        with _lock:
                            _cache.update(d)
                except Exception:
                    pass
        except Exception:
            with _lock:
                _alive = False
            if _stop:
                break
            time.sleep(backoff)
            backoff = min(backoff * 2, 4.0)
        finally:
            try:
                s.close()
            except Exception:
                pass


def start(host='127.0.0.1', port=18899):
    global _stop
    if _thread_started():
        return
    _stop = False
    threading.Thread(target=_pump, args=(host, port), daemon=True).start()


def _thread_started():
    return any(t.name == 'ws-pump' for t in threading.enumerate())


def stop():
    global _stop
    _stop = True


def get_latest():
    with _lock:
        if not _alive:
            return None
        return dict(_cache)


def is_alive():
    with _lock:
        return _alive


if __name__ == '__main__':
    start()
    print("测试 ws 订阅, Ctrl+C 退出")
    try:
        while True:
            d = get_latest()
            if d:
                print(f"[ws] alive={is_alive()} 最近={d.get('_recv_time')} mobs={len(d.get('mobs', []))}")
            else:
                print(f"[ws] 等待... alive={is_alive()}")
            time.sleep(1)
    except KeyboardInterrupt:
        stop()
