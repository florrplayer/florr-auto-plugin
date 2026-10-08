# -*- coding: utf-8 -*-
import ctypes, io
import ctypes.wintypes
u = ctypes.windll.user32
out = []
def get_text(h):
    b = ctypes.create_unicode_buffer(512)
    u.GetWindowTextW(h, b, 512)
    return b.value
def get_cls(h):
    b = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(h, b, 256)
    return b.value
def cb(h, l):
    t = get_text(h)
    if 'florr' in t.lower():
        cr = ctypes.wintypes.RECT()
        ctypes.windll.user32.GetClientRect(h, ctypes.byref(cr))
        vis = u.IsWindowVisible(h)
        out.append("hwnd=%s cls=%s vis=%d client=%dx%d title=%r" % (hex(h), get_cls(h), vis, cr.right-cr.left, cr.bottom-cr.top, t[:100]))
    return True
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
u.EnumWindows(WNDENUMPROC(cb), 0)
with io.open(r"C:\Users\intel\Downloads\florr-auto-pathing-main\check_windows.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out) if out else "NONE")
print("done", len(out))
