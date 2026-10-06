"""
窗口后台控制模块
PrintWindow 截图 + PostMessage 鼠标键盘，支持窗口在屏幕外/跨虚拟桌面运行
依赖: pip install pywin32 opencv-python numpy
"""
import win32gui
import win32ui
import win32con
import win32api
import numpy as np
import cv2
import time
from ctypes import windll
import ctypes
from ctypes import wintypes, POINTER, byref, c_void_p


class _GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD), ("Data4", wintypes.BYTE * 8)]
    def __init__(self, l=0, w1=0, w2=0, b=None):
        self.Data1, self.Data2, self.Data3 = l, w1, w2
        for i in range(8):
            self.Data4[i] = (b or [0]*8)[i]


def get_desktop2_id():
    """获取桌面2的ID: 切换到右边桌面(Win+Ctrl+Right)获取ID, 再切回来"""
    try:
        # 先获取当前桌面ID
        console = windll.kernel32.GetConsoleWindow()
        clsid = _GUID(0xAA509086, 0x5CA9, 0x4C25, [0x8F,0x95,0x58,0x9D,0x3C,0x07,0xB4,0x8A])
        iid = _GUID(0xA5CD92FF, 0x29BE, 0x454C, [0x8D,0x04,0xD8,0x28,0x79,0xFB,0x3F,0x1B])
        ptr = c_void_p()
        windll.ole32.CoCreateInstance(byref(clsid), None, 1, byref(iid), byref(ptr))
        if not ptr:
            return None
        vtbl = ctypes.cast(ptr, POINTER(POINTER(c_void_p))).contents
        get_id = ctypes.cast(vtbl[4], ctypes.WINFUNCTYPE(ctypes.c_int, c_void_p, wintypes.HWND, POINTER(_GUID)))
        cur_id = _GUID()
        get_id(ptr, console, byref(cur_id))
        # 切换到右边桌面 (Win+Ctrl+Right)
        win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(win32con.VK_RIGHT, 0, 0, 0)
        time.sleep(0.1)
        win32api.keybd_event(win32con.VK_RIGHT, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.8)
        # 获取右边桌面ID(桌面2)
        d2_id = _GUID()
        get_id(ptr, console, byref(d2_id))
        # 切回原桌面 (Win+Ctrl+Left)
        win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(win32con.VK_LEFT, 0, 0, 0)
        time.sleep(0.1)
        win32api.keybd_event(win32con.VK_LEFT, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.5)
        # 如果右边桌面和当前桌面ID一样(只有一个桌面), 返回None
        if (d2_id.Data1 == cur_id.Data1 and d2_id.Data2 == cur_id.Data2 and
            d2_id.Data3 == cur_id.Data3 and list(d2_id.Data4) == list(cur_id.Data4)):
            return None
        return d2_id
    except Exception as e:
        print(f"[!] 获取桌面2 ID失败: {e}")
        return None


def move_window_to_desktop2(hwnd):
    """把窗口移动到桌面2"""
    d2_id = get_desktop2_id()
    if d2_id is None:
        return False
    try:
        clsid = _GUID(0xAA509086, 0x5CA9, 0x4C25, [0x8F,0x95,0x58,0x9D,0x3C,0x07,0xB4,0x8A])
        iid = _GUID(0xA5CD92FF, 0x29BE, 0x454C, [0x8D,0x04,0xD8,0x28,0x79,0xFB,0x3F,0x1B])
        ptr = c_void_p()
        windll.ole32.CoCreateInstance(byref(clsid), None, 1, byref(iid), byref(ptr))
        if not ptr:
            return False
        vtbl = ctypes.cast(ptr, POINTER(POINTER(c_void_p))).contents
        move = ctypes.cast(vtbl[5], ctypes.WINFUNCTYPE(ctypes.c_int, c_void_p, wintypes.HWND, POINTER(_GUID)))
        move(ptr, hwnd, byref(d2_id))
        return True
    except Exception as e:
        print(f"[!] 移动窗口到桌面2失败: {e}")
        return False


def _lparam(x, y):
    """构造 WM_* 消息的 LPARAM（不依赖 win32api.MAKELPARAM，兼容新版 pywin32）"""
    return (int(y) << 16) | (int(x) & 0xFFFF)


class WindowController:
    def __init__(self, title_keyword="florr.io"):
        self.title_keyword = title_keyword
        self.hwnd = None

    def find_window(self):
        """严格匹配: 类名=Chrome窗口 + 标题含 florr.io + 客户区>200px
        v1.31: 排除 florr-mine 资源管理器/空标题残留小窗(52x52)/DevTools
        v1.32: 不检查 IsWindowVisible —— 跨虚拟桌面(插件桌面1/游戏桌面2)也能枚举,
               PrintWindow+PostMessage 对非当前虚拟桌面窗口仍有效
        v1.33: Edge 更新后窗口标题带 [AIEP:...] 前缀, 改"标题含 florr.io"匹配;
               找不到时自动 Win+Ctrl+Right 切到桌面2 再找(虚拟桌面隔离: EnumWindows 只枚举当前虚拟桌面)"""
        def good(hwnd):
            try:
                cls = win32gui.GetClassName(hwnd)
                # v1.34: Edge AIEP 模式类名带前缀(如 _AIEP_165722:Chrome_WidgetWin_1), 用包含匹配
                if "Chrome_WidgetWin" not in cls:
                    return False
                t = win32gui.GetWindowText(hwnd)
                tl = t.lower()
                if "florr.io" not in tl:
                    return False
                if "devtools" in tl or "新标签页" in t or "new tab" in tl:
                    return False
                # v1.33: 排除维基/首页等非游戏页面(标题"首页 — Florr.io中文维基"也含 florr.io)
                if "维基" in t or "wiki" in tl or "首页" in t or "home" in tl:
                    return False
                l, tt, r, b = win32gui.GetClientRect(hwnd)
                return (r - l) > 200 and (b - tt) > 200
            except Exception:
                return False
        results = []
        def cb_enum(hwnd, r):
            if good(hwnd):
                r.append(hwnd)
            return True
        win32gui.EnumWindows(cb_enum, results)
        if not results:
            # v1.34: 去掉 keybd_event 自动切桌面(实测无效+扰民) 与自动开 Edge(用户要求完全去桌面2)
            # 插件须与游戏同桌面启动(cmd/bat 在桌面2运行), 找不到时仅提示
            print("[!] 当前桌面未找到 florr 窗口(插件必须与游戏同虚拟桌面启动)")
        if not results:
            # 退回: 标题任意位置含 florr.io 的浏览器主窗口
            def cb2(hwnd, results2):
                try:
                    cls = win32gui.GetClassName(hwnd)
                    if "Chrome_WidgetWin" in cls:
                        t = win32gui.GetWindowText(hwnd)
                        tl = t.lower()
                        if self.title_keyword.lower() in tl and "维基" not in t and "wiki" not in tl and "首页" not in t:
                            l, tt, r, b = win32gui.GetClientRect(hwnd)
                            if (r - l) > 200 and (b - tt) > 200:
                                results2.append(hwnd)
                except Exception:
                    pass
                return True
            win32gui.EnumWindows(cb2, results)
        if not results:
            print(f"[!] 未找到标题含 '{self.title_keyword}' 的窗口")
            return False
        # 取客户区面积最大的窗口(主游戏窗口)
        results.sort(key=lambda h: (win32gui.GetClientRect(h)[2] - win32gui.GetClientRect(h)[0]) * (win32gui.GetClientRect(h)[3] - win32gui.GetClientRect(h)[1]), reverse=True)
        self.hwnd = results[0]
        print(f"[+] 找到窗口: {win32gui.GetWindowText(self.hwnd)}")
        return True

    def alive(self):
        """窗口句柄是否仍有效(v1.31: 窗口中途被关时的保护)"""
        return bool(self.hwnd) and win32gui.IsWindow(self.hwnd)

    def move_offscreen(self):
        """后台运行: 强制最大化 -> 保持在前台(不抢焦点)渲染
        注意: 不能放最底层(HWND_BOTTOM), 否则Windows停止渲染, PrintWindow截到旧缓存"""
        if not self.hwnd:
            return
        import win32con as wc
        import time
        win32gui.ShowWindow(self.hwnd, wc.SW_MAXIMIZE)  # 强制最大化
        time.sleep(0.5)
        # 保持在顶层(不激活不抢焦点), 确保Windows持续渲染
        win32gui.SetWindowPos(
            self.hwnd, wc.HWND_TOP,
            0, 0, 0, 0,
            wc.SWP_NOACTIVATE | wc.SWP_NOSIZE | wc.SWP_NOMOVE | wc.SWP_SHOWWINDOW,
        )
        print("[+] 窗口已最大化并保持前台渲染(不抢焦点)")

    def move_onscreen(self, bring_front=True):
        """停止时把窗口移回可见区域; bring_front=False 时沉底不打扰(用户忙时不弹前台)"""
        if not self.hwnd:
            return
        import win32con as wc
        zorder = wc.HWND_TOP if bring_front else wc.HWND_BOTTOM
        win32gui.SetWindowPos(
            self.hwnd, zorder,
            0, 0, 0, 0,
            wc.SWP_NOACTIVATE | wc.SWP_NOSIZE | wc.SWP_SHOWWINDOW,
        )

    def restore_visible(self):
        """最小化/不可见时恢复: 还原+最大化+置顶(强制恢复渲染, 防画面冻结卡死)"""
        if not self.hwnd:
            return
        import win32con as wc
        import time
        win32gui.ShowWindow(self.hwnd, wc.SW_RESTORE)
        time.sleep(0.3)
        win32gui.ShowWindow(self.hwnd, wc.SW_MAXIMIZE)
        time.sleep(0.3)
        win32gui.SetWindowPos(
            self.hwnd, wc.HWND_TOP,
            0, 0, 0, 0,
            wc.SWP_NOACTIVATE | wc.SWP_NOSIZE | wc.SWP_NOMOVE | wc.SWP_SHOWWINDOW,
        )

    def _printwindow_capture(self):
        """PrintWindow + PW_RENDERFULLCONTENT 快速截客户区(绕过屏幕合成器, 后台也能截)
        实测 ImageGrab 抓屏固定 ~100ms(与区域大小无关); PrintWindow 只渲染目标窗口, 快 5-20x
        现代 Chromium Edge 支持 PW_RENDERFULLCONTENT(2); 失败/全黑返回 None 由调用方回退"""
        try:
            from ctypes import windll
            hwnd = self.hwnd
            l, t, r, b = win32gui.GetClientRect(hwnd)
            w, h = r - l, b - t
            if w <= 0 or h <= 0:
                return None
            hdc_win = win32gui.GetDC(hwnd)
            hdc_mem = win32ui.CreateDCFromHandle(hdc_win)
            hbmp = win32ui.CreateBitmap()
            hbmp.CreateCompatibleBitmap(hdc_win, w, h)
            hdc_mem.SelectObject(hbmp)
            PW_RENDERFULLCONTENT = 2
            ok = windll.user32.PrintWindow(hwnd, hdc_mem.GetSafeHdc(), PW_RENDERFULLCONTENT)
            hdc_mem.DeleteDC()
            win32gui.ReleaseDC(hwnd, hdc_win)
            if not ok:
                return None
            bits = hbmp.GetBitmapBits(True)
            img = np.frombuffer(bits, dtype=np.uint8).reshape((h, w, 4))
            img = img[:, :, [2, 1, 0]]  # BGRA -> BGR
            if not img.any():
                return None
            return np.ascontiguousarray(img)
        except Exception:
            return None

    def capture(self, region=None):
        """截取窗口客户区，返回 BGR numpy 数组
        v1.18.3: 优先 PrintWindow(快速, 后台可截); 失败/全黑回退 ImageGrab bbox
        注意: ImageGrab 路径要求 florr窗口在前台可见"""
        if not self.hwnd:
            raise RuntimeError("窗口未初始化")
        img = self._printwindow_capture()
        if img is None:
            from PIL import ImageGrab
            l, t, r, b = win32gui.GetClientRect(self.hwnd)
            w, h = r - l, b - t
            sl, st = win32gui.ClientToScreen(self.hwnd, (0, 0))
            pil_img = ImageGrab.grab(bbox=(sl, st, sl + w, st + h))
            img = np.array(pil_img)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        if region:
            x, y, rw, rh = region
            img = img[y:y + rh, x:x + rw]
        return img

    def get_pixel(self, x, y):
        p = self.capture(region=[x, y, 1, 1])[0, 0]
        return (int(p[2]), int(p[1]), int(p[0]))

    def _post(self, msg, wp, lp):
        """v1.31: PostMessage 包装, 窗口中途销毁时静默返回不崩溃"""
        if not self.hwnd:
            return
        try:
            win32api.PostMessage(self.hwnd, msg, wp, lp)
        except Exception:
            pass

    def mouse_move(self, x, y):
        if not self.hwnd:
            return
        lp = _lparam(x, y)
        self._post(win32con.WM_MOUSEMOVE, 0, lp)

    def mouse_double_click(self, x, y):
        if not self.hwnd:
            return
        lp = _lparam(x, y)
        self._post(win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lp)
        self._post(win32con.WM_LBUTTONUP, 0, lp)
        self._post(win32con.WM_LBUTTONDBLCLK, win32con.MK_LBUTTON, lp)
        self._post(win32con.WM_LBUTTONUP, 0, lp)

    def left_click(self, x, y):
        """左键单击（点复活按钮用）"""
        if not self.hwnd:
            return
        import time
        lp = _lparam(x, y)
        self._post(win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lp)
        time.sleep(0.08)
        self._post(win32con.WM_LBUTTONUP, 0, lp)

    def right_button_down(self, x=960, y=540):
        """按住右键（防御）"""
        if not self.hwnd:
            return
        lp = _lparam(x, y)
        self._post(win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, lp)

    def right_button_up(self, x=960, y=540):
        """松开右键"""
        if not self.hwnd:
            return
        lp = _lparam(x, y)
        self._post(win32con.WM_RBUTTONUP, 0, lp)

    def key_down(self, vk):
        if not self.hwnd:
            return
        # 完整lParam: 重复计数1 + 扫描码(16-23位), 否则游戏可能解析错键
        scan = win32api.MapVirtualKey(vk, 0)
        lparam = (1) | (scan << 16)
        self._post(win32con.WM_KEYDOWN, vk, lparam)

    def key_up(self, vk):
        if not self.hwnd:
            return
        scan = win32api.MapVirtualKey(vk, 0)
        lparam = (1) | (scan << 16) | (1 << 30)  # 先前按下 + 释放
        self._post(win32con.WM_KEYUP, vk, lparam)

    def press(self, vk, delay=0.05):
        import time
        self.key_down(vk)
        time.sleep(delay)
        self.key_up(vk)

    # ===== 移动方式支持 (v1.18.1): 鼠标模式/键盘模式都能动 =====
    def is_foreground(self):
        """窗口是否前台(鼠标模式要求前台可见; 键盘模式后台也行)"""
        if not self.hwnd:
            return False
        try:
            return win32gui.GetForegroundWindow() == self.hwnd
        except Exception:
            return False

    def client_center(self):
        """窗口客户区中心(屏幕坐标) - 鼠标模式控制方向用"""
        if not self.hwnd:
            return None
        try:
            l, t, r, b = win32gui.GetClientRect(self.hwnd)
            sl, st = win32gui.ClientToScreen(self.hwnd, (0, 0))
            return (sl + (r - l) // 2, st + (b - t) // 2,
                    max(1, r - l), max(1, b - t))
        except Exception:
            return None

    def mouse_to_screen(self, sx, sy):
        """把真实鼠标移到屏幕坐标(游戏读鼠标相对窗口位置 -> 角色朝鼠标走)"""
        try:
            win32api.SetCursorPos((int(sx), int(sy)))
        except Exception:
            pass


_inst = None

def init_window(title_keyword="florr.io"):
    global _inst
    _inst = WindowController(title_keyword)
    ok = _inst.find_window()
    if not ok:
        # v1.34: 不再自动打开 Edge(用户要求插件完全去桌面2、不打扰)
        # 插件与游戏须同虚拟桌面: 请在桌面2 用 start_plugin.bat 启动本插件
        print("[!] 请确保浏览器 florr.io 游戏已打开，并用与游戏同桌面的方式启动插件")
    return ok

def get_window():
    global _inst
    return _inst
