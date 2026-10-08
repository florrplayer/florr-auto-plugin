# -*- coding: utf-8 -*-
import io
p = r"C:\Users\intel\Downloads\florr-auto-pathing-main\live_capture.log"
t = io.open(p, encoding="gbk", errors="replace").read()
lines = t.splitlines()
with io.open(r"C:\Users\intel\Downloads\florr-auto-pathing-main\live_tail.txt", "w", encoding="utf-8") as f:
    f.write("LEN=%d\n" % len(t))
    f.write("\n".join(lines[-40:]))
