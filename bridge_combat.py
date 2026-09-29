# -*- coding: utf-8 -*-
"""从wasm内存bridge读取怪物数据，替代OpenCV截图"""
import time, math, json, urllib.request

BRIDGE_URL = "http://127.0.0.1:18899"


def _fetch_latest():
    """从bridge_server拉最新数据 (跨进程)"""
    try:
        with urllib.request.urlopen(BRIDGE_URL, timeout=1) as r:
            return json.loads(r.read().decode())
    except:
        return {}

# 怪物类型ID映射 (从wasm偷的)
TYPE_NAMES = {
    1: "player", 2: "petal", 15: "scorpion", 21: "jelly",
    257: "mantis_shrimp", 262: "vulture", 264: "roadrunner",
    289: "buzzard", 292: "hawk", 513: "beetle",
    1066: "scarab", 3841: "boss", 3859: "ant_worker",
    3867: "ant_soldier", 7936: "projectile",
}

# 垃圾type ID (内存噪音, 不是怪物)
JUNK_TYPES = {0, 48, 75, 16, 139, 10, 9, 8, 12, 147, 2}

# 高优先级目标 (稀有怪)
PRIORITY_TYPES = {513, 1066, 3841}

# 危险怪 (需要避开)
DANGER_TYPES = {257, 262, 264, 289, 292, 15, 21}


def get_player():
    """从bridge找玩家位置 (t=1, hp>10)"""
    d = _fetch_latest()
    for m in d.get('mobs', []):
        if m['t'] == 1 and m['hp'] > 10:
            return {'x': m['x'], 'y': m['y'], 'hp': m['hp']}
    return None


def get_nearby_mobs(max_dist=3000):
    """从bridge获取附近怪物，返回 (怪物列表, 玩家)"""
    d = _fetch_latest()
    mobs = d.get('mobs', [])
    player = None
    result = []
    for m in mobs:
        # 找玩家
        if m['t'] == 1 and m['hp'] > 10:
            player = {'x': m['x'], 'y': m['y'], 'hp': m['hp']}
            continue
        # 过滤垃圾type
        if m['t'] in JUNK_TYPES:
            continue
        # 过滤边界垃圾
        if m['x'] < 1000 or m['y'] < 1000 or m['x'] > 64000 or m['y'] > 64000:
            continue
        # 过滤花瓣 (hp=7且x≈y)
        if m['hp'] == 7 and abs(m['x'] - m['y']) < 100:
            continue
        result.append({
            'x': m['x'], 'y': m['y'],
            'hp': m['hp'],
            'type': m['t'],
            'name': TYPE_NAMES.get(m['t'], f"type_{m['t']}"),
        })
    return result, player


def find_best_target(player_x, player_y, can_kill_hp=500):
    """找最近的能打的怪"""
    mobs, _ = get_nearby_mobs()
    best = None
    best_score = -999
    for m in mobs:
        dist = math.hypot(m['x'] - player_x, m['y'] - player_y)
        if dist > 3000:
            continue
        if m['hp'] > can_kill_hp:
            continue
        score = -dist
        if m['type'] in PRIORITY_TYPES:
            score += 5000
        if score > best_score:
            best_score = score
            best = m
    return best


def get_danger_mobs(player_x, player_y, radius=500):
    """获取附近危险怪"""
    mobs, _ = get_nearby_mobs()
    danger = []
    for m in mobs:
        dist = math.hypot(m['x'] - player_x, m['y'] - player_y)
        if dist < radius and m['type'] in DANGER_TYPES:
            danger.append(m)
    return danger


if __name__ == '__main__':
    print("测试bridge数据...")
    player = get_player()
    if player:
        print(f"玩家: ({player['x']:.0f}, {player['y']:.0f}) hp={player['hp']:.0f}")
    for i in range(3):
        mobs, _ = get_nearby_mobs()
        print(f"\n第{i+1}次扫描: {len(mobs)}只怪")
        for m in mobs[:8]:
            print(f"  {m['name']:20s} hp={m['hp']:6d} at ({m['x']},{m['y']})")
        time.sleep(1)
