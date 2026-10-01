# -*- coding: utf-8 -*-
"""super_ping.py v1.21.2 - Super 出生公告雷达 (抢 Super)
数据源: florr-auto-afk superping 扩展 (官方 $system 聊天公告格式)
  1. 通用公告: "A Super X has spawned" (X=怪名英文)
  2. 特殊公告: 8 条关键词 (Cactus/Gambler/Jellyfish/Rock/Firefly/Hornet/Fly/Hel)
  3. chat_ping.content.userPosition: 公告若带来源位置可直接导航
触发: 收到公告 -> 设置 super_hunt 标记(全图扫N秒找Super), 抢 Super 收益巨大(掉Ultra/Super花瓣)
"""
import time, re, json, os

_BASE = os.path.dirname(os.path.abspath(__file__))

# 公告模板: "A Super X has spawned"
PAT_SUPER = re.compile(r'A Super (\w+) has spawned', re.I)

# 特殊公告关键词 -> (怪sid, 中文名)
KEYWORD_SIDS = {
    "A tower of thorns rises from the sands...": "cactus",
    'You hear someone whisper faintly...just... one more game...': "gambler",
    "You hear lightning strikes coming from a far distance...": "jellyfish",
    "Something mountain-like appears in the distance...": "rock",
    "There's a bright light in the horizon": "firefly",
    "A big yellow spot shows up in the distance...": "hornet",
    "A buzzing noise echoes through the sewer tunnels": "fly",
    "You sense ominous vibrations coming from a different realm...": None,  # Hel传送门事件
}

# Super 怪 -> 中文名 (公告用)
_SUPER_CN = {
    "cactus": "仙人掌", "gambler": "赌徒", "jellyfish": "水母", "rock": "岩石",
    "firefly": "萤火虫", "hornet": "黄蜂", "fly": "苍蝇", "spider": "蜘蛛",
    "scorpion": "蝎子", "bee": "蜜蜂", "ladybug": "瓢虫", "centipede": "蜈蚣",
    "beetle": "甲虫", "starfish": "海星", "shell": "贝壳", "crab": "螃蟹",
    "wasp": "胡蜂", "mantis": "螳螂", "sandstorm": "沙暴", "leech": "水蛭",
}

class SuperPing:
    def __init__(self):
        self._lock = None
        self.super_hunt_until = 0.0   # 全图扫Super截止时间
        self.super_hunt_sid = None    # 公告给的怪(可能None=未知)
        self.last_ping = 0.0
        self._stats = {'pings': 0, 'hunts': 0}

    def parse(self, chat_ping):
        """解析一条聊天消息 -> (mob_sid|None, userPosition|None)
        chat_ping: {'content': {'area': str, 'message': str, 'userPosition': {x,y}|None, 'user': str}}"""
        try:
            content = chat_ping.get('content') or {}
            area = content.get('area') or ''
            msg = (content.get('message') or '').strip()
        except Exception:
            return None, None
        if area != '$system' and not msg.startswith('A Super'):
            return None, None
        m = PAT_SUPER.search(msg)
        if m:
            return m.group(1).lower(), content.get('userPosition')
        k = KEYWORD_SIDS.get(msg)
        if k:
            return k, content.get('userPosition')
        return None, None

    def feed(self, chat_ping):
        """喂一条聊天消息, 命中公告则开启 Super 猎杀模式
        返回 (sid, cn, pos) 或 None"""
        sid, pos = self.parse(chat_ping)
        if not sid:
            return None
        now = time.time()
        self._stats['pings'] += 1
        self.super_hunt_sid = sid
        self.super_hunt_until = now + 120.0   # 公告后120s内全图扫
        self.last_ping = now
        self._stats['hunts'] += 1
        return sid, _SUPER_CN.get(sid, sid), pos

    def is_hunting(self, now=None):
        return (now or time.time()) < self.super_hunt_until

    def stats(self):
        return dict(self._stats)

if __name__ == '__main__':
    sp = SuperPing()
    tests = [
        {'content': {'area': '$system', 'message': 'A Super Cactus has spawned', 'userPosition': None}},
        {'content': {'area': '$system', 'message': 'There\'s a bright light in the horizon', 'userPosition': {'x': 100, 'y': 200}}},
        {'content': {'area': '$system', 'message': 'A Super Jellyfish has spawned', 'userPosition': {'x': 50, 'y': 60}}},
        {'content': {'area': '$guild', 'message': 'hi', 'userPosition': None}},
    ]
    for t in tests:
        print(sp.feed(t) or ('忽略:', t['content']['message'][:40]))
    print('猎杀中:', sp.is_hunting(), '| 统计:', sp.stats())
