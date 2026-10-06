# -*- coding: utf-8 -*-
"""HTML 问卷星风格配置界面 (替换 tkinter 弹窗)
本地 http server (127.0.0.1:18898) + 浏览器问卷
"""
import json
import queue
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 18898
HOST = "127.0.0.1"

PAGE_HTML = """<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><title>florr 挂机设置</title>
<style>
body{margin:0;background:#f4f3ee;font-family:'Microsoft YaHei UI','Segoe UI',sans-serif;display:flex;justify-content:center;padding:48px 16px}
.card{background:#fff;border-radius:14px;box-shadow:0 2px 18px rgba(0,0,0,.08);max-width:520px;width:100%;padding:28px 30px;box-sizing:border-box}
h1{font-size:17px;color:#1a1b1c;margin:0 0 6px;font-weight:600}
.step{font-size:12px;color:#8a8f98;margin-bottom:18px}
.prompt{font-size:14px;color:#1a1b1c;line-height:1.6;white-space:pre-wrap;background:#f8f7f4;border-radius:10px;padding:14px 16px;margin-bottom:16px}
.opt{display:block;padding:11px 14px;margin:7px 0;background:#fff;border:1px solid #e4e3dd;border-radius:10px;font-size:13.5px;color:#1a1b1c;cursor:pointer}
.opt:hover{border-color:#9eace9;background:#fbfcff}
.opt.sel{background:#d6e4ff;border-color:#5b7cf0;color:#123;font-weight:600}
.next{display:block;width:100%;margin-top:20px;padding:12px;background:#5b7cf0;color:#fff;border:none;border-radius:10px;font-size:14px;font-weight:600;cursor:pointer}
.next:hover{background:#4a6ae0}
.done{text-align:center;color:#52c41a;font-size:15px;font-weight:600;padding:40px 0}
</style></head><body>
<div class="card">
<h1 id="title">florr 挂机设置</h1>
<div class="step" id="step"></div>
<div class="prompt" id="prompt"></div>
<div id="opts"></div>
<button class="next" id="next" onclick="submit()">下一步</button>
</div>
<script>
var MULTI=false;
function loadQ(){
  fetch('/question?t='+Date.now()).then(function(r){return r.json()}).then(function(q){
    if(q.done){ document.querySelector('.card').innerHTML='<div class="done">配置完成，开始挂机</div>'; return; }
    document.getElementById('title').textContent=q.title||'florr 挂机设置';
    document.getElementById('step').textContent=q.step||'';
    document.getElementById('prompt').textContent=q.prompt||'';
    MULTI=!!q.multi;
    var o=document.getElementById('opts'); o.innerHTML='';
    (q.options||[]).forEach(function(op){
      var d=document.createElement('div'); d.className='opt'; d.textContent=op.label;
      d.onclick=function(){ if(MULTI){ d.classList.toggle('sel'); } else { document.querySelectorAll('.opt').forEach(function(x){x.classList.remove('sel')}); d.classList.add('sel'); } };
      d.dataset.key=op.key; o.appendChild(d);
    });
  });
}
function submit(){
  var picked=[].map.call(document.querySelectorAll('.opt.sel'),function(d){return d.dataset.key});
  if(!MULTI){ if(picked.length===0){return} picked=picked[0]; }
  fetch('/answer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({v:picked})})
    .then(function(){ loadQ(); });
}
loadQ();
</script></body></html>"""


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/question"):
            self._json(_server.current_question())
        else:
            body = PAGE_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            data = {}
        _server.answer(data.get("v"))
        self._json({"ok": True})

    def _json(self, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class _WebServer:
    def __init__(self):
        self._queue = queue.Queue()
        self._answers = {}
        self._server = HTTPServer((HOST, PORT), _Handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def current_question(self):
        if self._queue.empty():
            return {"done": True}
        item = self._queue.queue[0]
        return {
            "title": item["title"], "step": item["step"], "prompt": item["prompt"],
            "multi": item["multi"], "options": item["options"],
        }

    def answer(self, v):
        if self._queue.empty():
            return
        item = self._queue.get_nowait()
        self._answers[item["key"]] = v


_server = _WebServer()


def ask_web(prompt, options, title="florr 挂机设置", multi=False, step=""):
    """阻塞等待一题答案; 返回 key(单选)/列表(多选); 超时返回 None/[]"""
    key = "q%d" % len(_server._queue.queue)
    _server._queue.put({
        "key": key, "title": title, "step": step, "prompt": prompt,
        "multi": multi, "options": [{"key": k, "label": lb} for k, lb in options],
    })
    webbrowser.open("http://%s:%d/" % (HOST, PORT))
    for _ in range(600):
        if key in _server._answers:
            v = _server._answers.pop(key)
            return v if multi else (v[0] if isinstance(v, list) and v else v)
        import time
        time.sleep(0.2)
    return [] if multi else None
