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
        def cb(hwnd, results):
            if win32gui.IsWindowVisible(hwnd):
                t = win32gui.GetWindowText(hwnd)
                if self.title_keyword.lower() in t.lower():
                    results.append((hwnd, t))
            return True
        results = []
        win32gui.EnumWindows(cb, results)
        if not results:
            print(f"[!] 未找到标题含 '{self.title_keyword}' 的窗口")
            return False
        self.hwnd = results[0][0]
        print(f"[+] 找到窗口: {results[0][1]}")
        return True

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

    def move_onscreen(self):
        """停止时把窗口移回前台给用户"""
        if not self.hwnd:
            return
        import win32con as wc
        win32gui.SetWindowPos(
            self.hwnd, wc.HWND_TOP,
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

    def capture(self, region=None):
        """截取窗口客户区，返回 BGR numpy 数组
        用 PIL ImageGrab 截全屏然后裁剪(PrintWindow对Edge截到旧缓存, BitBlt全黑)
        注意: florr窗口需在前台可见, 不要被其他窗口遮挡"""
        if not self.hwnd:
            raise RuntimeError("窗口未初始化")
        from PIL import ImageGrab
        l, t, r, b = win32gui.GetClientRect(self.hwnd)
        w, h = r - l, b - t
        # 客户区转屏幕坐标
        sl, st = win32gui.ClientToScreen(self.hwnd, (0, 0))
        screen = ImageGrab.grab()
        pil_img = screen.crop((sl, st, sl + w, st + h))
        img = np.array(pil_img)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        if region:
            x, y, rw, rh = region
            img = img[y:y + rh, x:x + rw]
        return img

    def get_pixel(self, x, y):
        p = self.capture(region=[x, y, 1, 1])[0, 0]
        return (int(p[2]), int(p[1]), int(p[0]))

    def mouse_move(self, x, y):
        if not self.hwnd:
            return
        lp = _lparam(x, y)
        win32api.PostMessage(self.hwnd, win32con.WM_MOUSEMOVE, 0, lp)

    def mouse_double_click(self, x, y):
        if not self.hwnd:
            return
        lp = _lparam(x, y)
        win32api.PostMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lp)
        win32api.PostMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lp)
        win32api.PostMessage(self.hwnd, win32con.WM_LBUTTONDBLCLK, win32con.MK_LBUTTON, lp)
        win32api.PostMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lp)

    def left_click(self, x, y):
        """左键单击（点复活按钮用）"""
        if not self.hwnd:
            return
        import time
        lp = _lparam(x, y)
        win32api.PostMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lp)
        time.sleep(0.08)
        win32api.PostMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lp)

    def right_button_down(self, x=960, y=540):
        """按住右键（防御）"""
        if not self.hwnd:
            return
        lp = _lparam(x, y)
        win32api.PostMessage(self.hwnd, win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, lp)

    def right_button_up(self, x=960, y=540):
        """松开右键"""
        if not self.hwnd:
            return
        lp = _lparam(x, y)
        win32api.PostMessage(self.hwnd, win32con.WM_RBUTTONUP, 0, lp)

    def key_down(self, vk):
        if not self.hwnd:
            return
        win32api.PostMessage(self.hwnd, win32con.WM_KEYDOWN, vk, 0)

    def key_up(self, vk):
        if not self.hwnd:
            return
        win32api.PostMessage(self.hwnd, win32con.WM_KEYUP, vk, 0)

    def press(self, vk, delay=0.05):
        import time
        self.key_down(vk)
        time.sleep(delay)
        self.key_up(vk)


_inst = None

def init_window(title_keyword="florr.io"):
    global _inst
    _inst = WindowController(title_keyword)
    ok = _inst.find_window()
    if not ok:
        # 自动打开 Edge 浏览器访问 florr.io
        import subprocess, time, os
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
        edge = None
        for p in edge_paths:
            if os.path.exists(p):
                edge = p
                break
        if edge:
            print(f"[+] 自动打开 Edge: {edge}")
            subprocess.Popen([edge, "https://florr.io"])
        else:
            print("[+] 用默认浏览器打开 florr.io")
            os.startfile("https://florr.io")
        print("[+] 等待浏览器窗口出现(5秒)...")
        time.sleep(5)
        # 找到浏览器窗口并移动到当前桌面(桌面2)
        def _cb(h, results):
            if win32gui.IsWindowVisible(h):
                t = win32gui.GetWindowText(h)
                if "florr.io" in t or "Edge" in t or "edge" in t:
                    results.append((h, t))
            return True
        br_results = []
        win32gui.EnumWindows(_cb, br_results)
        if br_results:
            print(f"[+] 找到浏览器窗口: {br_results[0][1]}")
            if move_window_to_desktop2(br_results[0][0]):
                print("[+] 浏览器窗口已移动到桌面2")
        print("[+] 等待页面加载(10秒)...")
        time.sleep(10)
        ok = _inst.find_window()
        if not ok:
            print("[!] 仍未找到 florr 窗口，请手动打开浏览器进入游戏")
    return ok

def get_window():
    global _inst
    return _inst
