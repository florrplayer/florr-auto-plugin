# -*- coding: utf-8 -*-
import urllib.request, json, threading, time, io
import config_web

log = []
def ask_thread():
    v = config_web.ask_web('测试问题？', [('a', '选项A'), ('b', '选项B')], '测试', multi=False)
    log.append('ANSWER=' + repr(v))

t = threading.Thread(target=ask_thread, daemon=True)
t.start()
time.sleep(0.6)
q = json.load(urllib.request.urlopen('http://127.0.0.1:18898/question'))
log.append('Q=' + repr((q['prompt'], q['options'])))
req = urllib.request.Request('http://127.0.0.1:18898/answer',
                             data=json.dumps({'v': ['b']}).encode(),
                             headers={'Content-Type': 'application/json'})
log.append('POST=' + urllib.request.urlopen(req).read().decode())
t.join(timeout=10)
q2 = json.load(urllib.request.urlopen('http://127.0.0.1:18898/question'))
log.append('DONE=' + repr(q2))
with io.open(r"C:\Users\intel\Downloads\florr-auto-pathing-main\web_test_out.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(log))
