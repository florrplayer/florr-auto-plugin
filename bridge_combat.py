# -*- coding: utf-8 -*-
"""从wasm内存bridge读取怪物数据，替代OpenCV截图"""
import time, math
from bridge_server import get_latest

# 怪物类型ID映射 (从wasm偷的)
TYPE_NAMES = {
    1: "player", 2: "petal", 15: "scorpion", 21: "jelly",
    257: "mantis_shrimp", 262: "vulture", 264: "roadrunner",
    289: "buzzard", 292: "hawk", 513: "beetle",
    1066: "scarab", 3841: "boss", 3859: "ant_worker",
    3867: "ant_soldier", 7936: "projectile",
}

# 高优先级目标 (稀有怪)
PRIORITY_TYPES = {513, 1066, 3841, 7936}

# 危险怪 (需要避开)
DANGER_TYPES = {257, 262, 264, 289, 292, 15, 21}


def get_nearby_mobs(max_dist=3000):
    """从bridge获取附近怪物，返回列表"""
    d = get_latest()
    mobs = d.get('mobs', [])
    result = []
    for m in mobs:
        # 过滤掉花瓣/装饰物 (hp=7且x≈y的)
        if m['hp'] == 7 and abs(m['x'] - m['y']) < 100:
            continue
        # 过滤掉投射物
        if m['t'] == 7936:
            continue
        result.append({
            'x': m['x'], 'y': m['y'],
            'hp': m['hp'],
            'type': m['t'],
            'name': TYPE_NAMES.get(m['t'], f"type_{m['t']}"),
        })
    return result


def find_best_target(player_x, player_y, can_kill_hp=500):
    """找最近的能打的怪"""
    mobs = get_nearby_mobs()
    best = None
    best_score = -999
    for m in mobs:
        dist = math.hypot(m['x'] - player_x, m['y'] - player_y)
        # 只看3000范围内
        if dist > 3000:
            continue
        # HP判断: 能秒杀的优先
        if m['hp'] > can_kill_hp:
            continue  # 打不过跳过
        # 优先级: 稀有怪 > 普通怪 > 距离近
        score = -dist
        if m['type'] in PRIORITY_TYPES:
            score += 5000
        best_score = score
        best = m
    return best


def get_danger_mobs(player_x, player_y, radius=500):
    """获取附近危险怪"""
    mobs = get_nearby_mobs()
    danger = []
    for m in mobs:
        dist = math.hypot(m['x'] - player_x, m['y'] - player_y)
        if dist < radius and m['type'] in DANGER_TYPES:
            danger.append(m)
    return danger


if __name__ == '__main__':
    print("测试bridge数据...")
    for i in range(3):
        mobs = get_nearby_mobs()
        print(f"\n第{i+1}次扫描: {len(mobs)}只怪")
        for m in mobs[:5]:
            print(f"  {m['name']:20s} hp={m['hp']:6d} at ({m['x']},{m['y']})")
        time.sleep(1)
