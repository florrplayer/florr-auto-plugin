# -*- coding: utf-8 -*-
"""chat_solver.py v1.18.0 - 聊天挑战自动回复 (防封号)
M28 会随机发"玩家消息挑战": 只解AFK检测但不回复消息可能封号
(来源: florr-auto-afk README CAUTION + 洛谷florr文章: 红色=管理员消息)
策略(人类化):
  1. 持续截屏左下角聊天区, 检测新消息(区域像素变化) 和 红色管理员消息
  2. 检测到后随机延迟 8-25s (人类反应), 概率 70% 回复一条
  3. 按 Enter 打开聊天输入框 -> 输入随机短语 -> Enter 发送
  4. 限流: 每 6 分钟最多 1 条, 避免刷屏被盯
"""
import time, random, threading, json, os, re

# v1.36: 官方屏蔽词表 (AstRatJP wasm 提取 banned_words.txt) - 回复前过滤防封
_BANNED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'florr_banned_words.json')
_BANNED_PATTERNS = []
try:
    with open(_BANNED_FILE, encoding='utf-8') as f:
        _BANNED_PATTERNS = [re.compile(p, re.I) for p in json.load(f)]
except Exception:
    pass

def _safe_pick(pool, **fmt):
    """从短语池随机选一条不含官方屏蔽词的短语"""
    cands = list(pool)
    random.shuffle(cands)
    for t in cands:
        s = t.format(**fmt)
        if not any(p.search(s) for p in _BANNED_PATTERNS):
            return s
    return cands[0].format(**fmt) if cands else ''
import cv2
import numpy as np

# 聊天区相对位置(窗口客户区): 左下角 [x0,y0,x1,y1]
CHAT_REGION = (0.12, 0.72, 0.48, 0.99)

# 管理员红色消息 HSV 范围
ADMIN_RED_LOW1 = (0, 100, 100)
ADMIN_RED_HIGH1 = (10, 255, 255)
ADMIN_RED_LOW2 = (170, 100, 100)
ADMIN_RED_HIGH2 = (180, 255, 255)

# 随机回复短语池 (florr 社区常用, 中英混合)
REPLIES = [
    "gg", "nice", "lol", "?", "wow", "hi", "ok", "ty", "gl",
    "nb", "w", "fr", "lmao", "xd", "k", "cool", "same", "yep",
    "哈哈", "好", "牛", "？", "哦", "在的", "嗯嗯",
    "ggwp", "bro", "damn", "pog", "nice one", "glhf",
]

# 限流: 两次回复最小间隔(秒)
MIN_INTERVAL = 360
# 检测到新消息后回复概率
REPLY_CHANCE = 0.7

# v1.23.3: Boss喊话模板(偷自 florr_clone cpp/server/bot_ai.cpp 真人闲聊池)
# 小写+不一致标点 = 融入玩家聊天; {tier}=super/unique, {mob}=怪英文名
BOSS_SHOUTS_SUPER = [
    "{tier} {mob}", "{tier} {mob} come", "{tier} {mob} lets go",
    "who wants {tier} {mob}", "need help {tier} {mob}", "{tier} {mob} anyone",
    "{mob} {tier} here", "{tier} {mob} spawn", "{tier} {mob} free",
    "{tier} {mob} free mzone", "{tier} {mob} free lzone", "super shiny",
    "free {tier} {mob}", "{tier} {mob} deep", "{tier} {mob} lured",
    "s{mob}", "s{mob} unfree", "less than 20 ppl at {tier} {mob}",
    "{tier} {mob} free carry", "pls carry",
]
BOSS_SHOUTS_UNIQUE = [
    "q{mob}", "how {tier} {mob}", "{tier} {mob} come", "{tier} {mob} lets go",
    "who wants {tier} {mob}", "{tier} {mob} anyone", "{mob} {tier} here",
    "{tier} {mob} so free", "WHAT {tier} {mob}", "q{mob} pls loot",
    "q{mob} pls carry", "{tier} {mob} pls carry", "{tier} {mob} pls loot",
    "q{mob} so free",
]


class ChatSolver:
    def __init__(self, window, get_frame):
        self.w = window
        self.get_frame = get_frame
        self.last_frame = None      # 上一帧聊天区灰度
        self.last_reply = 0.0       # 上次回复时间戳
        self.running = False
        self._lock = threading.Lock()
        self._stats = {'detected': 0, 'replied': 0}

    # ---------- 检测 ----------
    def _chat_roi(self, frame):
        h, w = frame.shape[:2]
        x0 = int(w * CHAT_REGION[0]); y0 = int(h * CHAT_REGION[1])
        x1 = int(w * CHAT_REGION[2]); y1 = int(h * CHAT_REGION[3])
        return frame[y0:y1, x0:x1]

    def has_new_message(self, frame):
        """聊天区像素变化超过阈值 = 有新消息"""
        roi = self._chat_roi(frame)
        if roi.size == 0:
            return False
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        if self.last_frame is None:
            self.last_frame = gray.copy()
            return False
        if gray.shape != self.last_frame.shape:   # 窗口尺寸变化 -> 重置基线, 防 sizes mismatch
            self.last_frame = gray.copy()
            return False
        diff = cv2.absdiff(gray, self.last_frame)
        change = float((diff > 25).sum()) / max(1, gray.size)
        self.last_frame = gray.copy()
        return change > 0.012

    def has_admin_message(self, frame):
        """红色文字(管理员/M28消息)"""
        roi = self._chat_roi(frame)
        if roi.size == 0:
            return False
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        m1 = cv2.inRange(hsv, ADMIN_RED_LOW1, ADMIN_RED_HIGH1)
        m2 = cv2.inRange(hsv, ADMIN_RED_LOW2, ADMIN_RED_HIGH2)
        red = (m1 | m2)
        red = cv2.morphologyEx(red, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        # 红色像素足够多 = 有管理员红字
        return float((red > 0).sum()) > 40

    # ---------- 发送 ----------
    def _send_chat(self, text):
        """打开聊天输入框 -> 输入 -> 发送 (全键盘, 不依赖鼠标焦点)"""
        try:
            # 1. 打开聊天: 按 Enter (florr 聊天默认 Enter 打开输入框)
            self.w.key_down(0x0D)   # VK_RETURN
            time.sleep(0.05)
            self.w.key_up(0x0D)
            time.sleep(0.3)
            # 2. 输入文字 (逐字符, 人类化节奏)
            for ch in text:
                self._type_char(ch)
                time.sleep(random.uniform(0.03, 0.09))
            time.sleep(random.uniform(0.1, 0.3))
            # 3. 发送
            self.w.key_down(0x0D)
            time.sleep(0.05)
            self.w.key_up(0x0D)
            return True
        except Exception as e:
            print(f"[聊天] 发送失败: {e}")
            return False

    def _type_char(self, ch):
        """输入单个字符 (兼容中文: 中文用剪贴板粘贴)"""
        import win32api, win32con
        if ord(ch) < 128:
            vk = ord(ch.upper())
            win32api.keybd_event(vk, 0, 0, 0)
            win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
        else:
            # 非ASCII: 用剪贴板粘贴整段
            import win32clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(ch, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            self.w.key_down(0x11)   # Ctrl
            self.w.key_down(0x56)   # V
            time.sleep(0.05)
            self.w.key_up(0x56)
            self.w.key_up(0x11)
            time.sleep(0.1)

    # ---------- Boss喊话 (v1.23.3) ----------
    def shout_boss(self, mob_sid, tier='super'):
        """发现Super/Unique时真人喊话(模板来自florr_clone bot_ai.cpp闲聊池)
        tier: 'super'/'unique'; 限流复用全局360s, 防止刷屏"""
        with self._lock:
            if time.time() - self.last_reply < MIN_INTERVAL:
                return False
        pool = BOSS_SHOUTS_UNIQUE if tier == 'unique' else BOSS_SHOUTS_SUPER
        text = _safe_pick(pool, tier=tier, mob=mob_sid)
        if self._send_chat(text):
            with self._lock:
                self.last_reply = time.time()
            self._stats['replied'] += 1
            print(f"[Boss喊话] {tier} {mob_sid}: {text}")
            return True
        return False

    # ---------- 主循环 ----------
    def loop(self):
        """持续监控聊天区: 检测->随机延迟->回复"""
        quiet = 0
        while self.running:
            try:
                frame = self.get_frame()
                if frame is None:
                    time.sleep(0.5)
                    continue
                new_msg = self.has_new_message(frame)
                admin = self.has_admin_message(frame)
                if new_msg or admin:
                    self._stats['detected'] += 1
                    # 人类化: 随机延迟 8-25s
                    delay = random.uniform(8, 25)
                    time.sleep(delay)
                    # 限流 + 概率
                    with self._lock:
                        if time.time() - self.last_reply < MIN_INTERVAL:
                            quiet += 1
                            continue
                    if random.random() > REPLY_CHANCE:
                        continue
                    reply = _safe_pick(REPLIES)
                    if self._send_chat(reply):
                        self._stats['replied'] += 1
                        self.last_reply = time.time()
                        print(f"[聊天] 已回复: {reply} (累计{self._stats['replied']}条)")
                    # 冷却几秒再继续检测
                    time.sleep(10)
            except Exception as e:
                print(f"[聊天] 循环异常: {e}")
                time.sleep(1)

    def start(self):
        if self.running:
            return
        self.running = True
        t = threading.Thread(target=self.loop, daemon=True)
        t.start()
        print(f"[聊天] 聊天挑战监控已启动 (限流{MIN_INTERVAL//60}分钟/条)")

    def stop(self):
        self.running = False

    def stats(self):
        return dict(self._stats)


if __name__ == '__main__':
    print("=== 聊天求解器测试 ===")
    try:
        from combat import get_frame
        from window_ctrl import get_window
        w = get_window()
        cs = ChatSolver(w, get_frame)
        frame = get_frame()
        print(f"聊天区新消息: {cs.has_new_message(frame)}")
        print(f"管理员红字: {cs.has_admin_message(frame)}")
    except Exception as e:
        print(f"测试异常(可能没开游戏): {e}")
