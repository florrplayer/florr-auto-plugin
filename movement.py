# -*- coding: utf-8 -*-
"""movement.py v1.18.1 - 统一移动模块: 鼠标模式/键盘模式/自动
florr 角色朝鼠标位置移动(速度=鼠标距角色距离, 越远越快)
- 鼠标模式: SetCursorPos 到窗口客户区中心+方向偏移 (原作者florr-auto-pathing方式, 已适配任意分辨率/窗口位置)
- 键盘模式: WASD PostMessage (后台/最小化也能用)
- 自动模式: 窗口前台用鼠标, 否则键盘
用法: mover = get_mover(); mover.mode='auto'
      mover.move_towards(px,py,tx,ty)   # 朝目标走
      mover.stop()
"""
import math
from window_ctrl import get_window

# 键盘虚拟码
VK_W = 0x57; VK_A = 0x41; VK_S = 0x53; VK_D = 0x44
_VK = {'w': VK_W, 'a': VK_A, 's': VK_S, 'd': VK_D}

# 鼠标模式速度参数: 偏移量=满速偏移*速度分数
# florr: 鼠标离角色越远走得越快(约200px外基本满速)
MAX_OFFSET_FRAC = 0.30   # 满速 = 客户区短边*30% (原作者硬编码500/1080≈46%, 30%更稳)
MIN_OFFSET = 18          # 最小偏移(太小=贴脸=停)
STOP_EPS = 1e-6


class Mover:
    def __init__(self):
        self.mode = 'auto'       # 'mouse' / 'keyboard' / 'auto'
        self._keys_down = set()
        self._mouse_at = None    # 上次鼠标目标位置

    # ---- 模式 ----
    def set_mode(self, mode):
        self.stop()
        if mode in ('mouse', 'keyboard', 'auto'):
            self.mode = mode
        else:
            self.mode = 'auto'

    def effective(self):
        """当前实际生效模式: auto -> 后台键盘(PostMessage, 跨虚拟桌面有效)
        v1.33: 用户反馈鼠标乱动(游戏在前台时 auto 误判鼠标模式, SetCursorPos 真实鼠标乱飞)。
        键盘模式全程后台 PostMessage, 不碰真实鼠标, 任何窗口状态都能移动。"""
        if self.mode == 'mouse':
            return 'mouse'   # 仅用户显式配置才用鼠标模式
        return 'keyboard'    # auto/默认一律键盘

    # ---- 主接口 ----
    def move_towards(self, px, py, tx, ty):
        """朝目标点移动(方向+速度), 自动按模式分派"""
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
        """按单位方向移动(战斗/躲避用), speed 0..1"""
        mode = self.effective()
        if mode == 'mouse':
            self._mouse(ux, uy, max(0.05, min(1.0, speed)))
        else:
            self._keys(ux, uy)

    def stop(self):
        """停止: 鼠标回中心 / 松所有键"""
        w = get_window()
        if self._mouse_at is not None and w:
            c = w.client_center()
            if c:
                w.mouse_to_screen(c[0], c[1])
            self._mouse_at = None
        for k in list(self._keys_down):
            w.key_up(_VK[k])
        self._keys_down.clear()

    # ---- 实现 ----
    def _mouse(self, ux, uy, speed):
        """鼠标模式: 窗口中心 + 方向*偏移(偏移=速度*满速)"""
        w = get_window()
        if not w:
            return
        c = w.client_center()
        if not c:
            return
        cx, cy, cw, ch = c
        if not w.is_foreground():
            # 窗口不在前台, 鼠标模式失效 -> 退回键盘
            self._keys(ux, uy)
            return
        max_off = max(MIN_OFFSET, min(cw, ch) * MAX_OFFSET_FRAC)
        off = max(MIN_OFFSET, max_off * speed)
        sx, sy = cx + ux * off, cy + uy * off
        w.mouse_to_screen(sx, sy)
        self._mouse_at = (sx, sy)

    def _keys(self, ux, uy):
        """键盘模式: 主方向键+必要时对角"""
        w = get_window()
        if not w:
            return
        # 主方向(绝对值大的轴)
        if abs(ux) > abs(uy):
            primary = 'd' if ux > 0 else 'a'
            secondary = 's' if uy > 0 else ('w' if uy < 0 else None)
        else:
            primary = 's' if uy > 0 else 'w'
            secondary = 'd' if ux > 0 else ('a' if ux < 0 else None)
        want = {primary}
        if secondary and abs(uy) > 0.4 and abs(ux) > 0.4:
            want.add(secondary)
        # 切换按键
        for k in list(self._keys_down - want):
            w.key_up(_VK[k])
            self._keys_down.discard(k)
        for k in want - self._keys_down:
            w.key_down(_VK[k])
            self._keys_down.add(k)


_mover = None


def get_mover():
    """全局单例"""
    global _mover
    if _mover is None:
        _mover = Mover()
    return _mover


if __name__ == '__main__':
    m = get_mover()
    print('movement 模块测试:')
    for mode in ('keyboard', 'mouse', 'auto'):
        m.set_mode(mode)
        print(f'  mode={mode} effective={m.effective()}')
    m.stop()
    print('OK')
