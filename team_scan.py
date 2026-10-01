# -*- coding: utf-8 -*-
"""team 字段实测: 统计真实游戏流里实体的 team 值分布, 判断能否区分野怪/玩家召唤物
用法: 1) 桌面2 florr 窗口进游戏  2) py -3.12 bridge_server.py  3) py -3.12 team_scan.py
bridge 收到浏览器端 hook 发来的 mobs(结构化) 或 mobData(原始协议字节) 后统计
"""
import json, time, urllib.request, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from net_protocol import parse_entity, ENTITY_SNAPSHOT_COMPACT, ENTITY_SNAPSHOT_FULL

BRIDGE = 'http://127.0.0.1:18899'

def pull():
    try:
        d = json.loads(urllib.request.urlopen(BRIDGE, timeout=3).read().decode())
        return d
    except Exception:
        return {}

def decode_mobdata(raw):
    """mobData 若为协议字节(base64或hex), 逐条解析实体"""
    import base64
    try:
        b = base64.b64decode(raw) if isinstance(raw, str) else bytes(raw)
    except Exception:
        return []
    # 试探: 逐实体解析(compact需要origin, full自带坐标)
    ents = []
    o = 0
    while o + 2 <= len(b):
        try:
            e = parse_entity(BytesReader(b, o)) if False else None
        except Exception:
            pass
        break
    return ents

class BytesReader:
    def __init__(self, b, off=0):
        self.b = b; self.o = off
    def u8(self):
        v = self.b[self.o]; self.o += 1; return v
    def u16(self):
        v = int.from_bytes(self.b[self.o:self.o+2], 'little'); self.o += 2; return v
    def u32(self):
        v = int.from_bytes(self.b[self.o:self.o+4], 'little'); self.o += 4; return v
    def i16(self):
        v = int.from_bytes(self.b[self.o:self.o+2], 'little', signed=True); self.o += 2; return v
    def i32(self):
        v = int.from_bytes(self.b[self.o:self.o+4], 'little', signed=True); self.o += 4; return v
    def u64(self):
        v = int.from_bytes(self.b[self.o:self.o+8], 'little'); self.o += 8; return v
    def string(self, length):
        v = self.b[self.o:self.o+length].decode('utf-8', 'replace'); self.o += length; return v
    def has(self, n):
        return self.o + n <= len(self.b)

def main():
    print('[team_scan] 等待 bridge 数据... 5s内采样')
    samples = {'mobs_teams': {}, 'entities': []}
    t0 = time.time()
    while time.time() - t0 < 5:
        d = pull()
        mobs = d.get('mobs', [])
        if isinstance(mobs, list) and mobs:
            for m in mobs:
                if isinstance(m, dict) and 'team' in m:
                    t = m['team']
                    samples['mobs_teams'][t] = samples['mobs_teams'].get(t, 0) + 1
                elif isinstance(m, dict):
                    samples['entities'].append(m)
        md = d.get('mobData', '')
        if md:
            print('[team_scan] mobData长度=%d (二进制协议待按消息类型解析)' % len(md))
        time.sleep(0.5)
    print('=== team 值分布(结构化mobs) ===')
    for k, v in sorted(samples['mobs_teams'].items(), key=lambda x: -x[1]):
        print('  team=%s: %d 个实体' % (k, v))
    if not samples['mobs_teams'] and not samples['entities']:
        print('  (无数据: 确认浏览器hook已把数据POST到18899, 且已在游戏内)')
        print('  提示: 若hook发的是原始消息, 观察 bridge_server 的 mobData长度>0')
    print('=== 实体样本字段(前3条) ===')
    for e in samples['entities'][:3]:
        print(' ', {k: e.get(k) for k in ('entityId','entityType','team','rarity','name') if k in e})
    if samples['entities']:
        teams = {}
        for e in samples['entities']:
            teams[e.get('team')] = teams.get(e.get('team'), 0) + 1
        print('  全部实体 team 分布:', teams)

if __name__ == '__main__':
    main()
