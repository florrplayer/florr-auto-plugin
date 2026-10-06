# -*- coding: utf-8 -*-
"""movement.py - 统一移动模块: 鼠标/键盘/自动
v1.33: auto/默认一律键盘(PostMessage 后台按键), 不碰真实鼠标
"""
import math
from window_ctrl import get_window

VK_W = 0x57; VK_A = 0x41; VK_S = 0x53; VK_D = 0x44
_VK = {'w': VK_W, 'a': VK_A, 's': VK_S, 'd': VK_D}

MAX_OFFSET_FRAC = 0.30
MIN_OFFSET = 18
STOP_EPS = 1e-6


class Mover:
    def __init__(self):
        self.mode = 'auto'
        self._keys_down = set()
        self._mouse_at = None

    def set_mode(self, mode):
        self.stop()
        if mode in ('mouse', 'keyboard', 'auto'):
            self.mode = mode
        else:
            self.mode = 'auto'

    def effective(self):
        if self.mode == 'mouse':
            return 'mouse'
        return 'keyboard'

    def move_towards(self, px, py, tx, ty):
        dx, dy = tx - px, ty - py
        dist = math.hypot(dx, dy)
        if dist < STOP_EPS:
            self.stop()
            return
        mode = self.effective()
        if mode == 'mouse':
            self._mouse(dx / dist, dy / dist, min(1.0, dist / 200.0))
        else:
            self._keys(dx / dist, dy / dist)

    def move_dir(self, ux, uy, speed=1.0):
        mode = self.effective()
        if mode == 'mouse':
            self._mouse(ux, uy, max(0.05, min(1.0, speed)))
        else:
            self._keys(ux, uy)

    def stop(self):
        w = get_window()
        if self._mouse_at is not None and w:
            c = w.client_center()
            if c:
                w.mouse_to_screen(c[0], c[1])
            self._mouse_at = None
        for k in list(self._keys_down):
            w.key_up(_VK[k])
        self._keys_down.clear()

    def _mouse(self, ux, uy, speed):
        w = get_window()
        if not w:
            return
        c = w.client_center()
        if not c:
            return
        cx, cy, cw, ch = c
        if not w.is_foreground():
            self._keys(ux, uy)
            return
        max_off = max(MIN_OFFSET, min(cw, ch) * MAX_OFFSET_FRAC)
        off = max(MIN_OFFSET, max_off * speed)
        sx, sy = cx + ux * off, cy + uy * off
        w.mouse_to_screen(sx, sy)
        self._mouse_at = (sx, sy)

    def _keys(self, ux, uy):
        w = get_window()
        if not w:
            return
        if abs(ux) > abs(uy):
            primary = 'd' if ux > 0 else 'a'
            secondary = 's' if uy > 0 else ('w' if uy < 0 else None)
        else:
            primary = 's' if uy > 0 else 'w'
            secondary = 'd' if ux > 0 else ('a' if ux < 0 else None)
        want = {primary}
        if secondary and abs(uy) > 0.4 and abs(ux) > 0.4:
            want.add(secondary)
        for k in list(self._keys_down - want):
            w.key_up(_VK[k])
            self._keys_down.discard(k)
        for k in want - self._keys_down:
            w.key_down(_VK[k])
            self._keys_down.add(k)


_mover = None


def get_mover():
    global _mover
    if _mover is None:
        _mover = Mover()
    return _mover
