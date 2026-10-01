# -*- coding: utf-8 -*-
"""v1.20.0: 地图数据层(florr_clone 官方刷怪区域+传送门, 世界坐标=memory模式坐标系)
- zones: 每张图刷怪区(中心坐标+难度档+怪种) -> 按秒杀等级推荐区域
- portals: 世界传送门坐标表 -> 捷径
难度档 diff -> 稀有度: 0=Common 15=Unusual 25~30=Rare 37~53=Epic 67=Legendary 80~85=Mythic 100=Ultra 105=Super
"""
import json, os, math

_BASE = os.path.dirname(os.path.abspath(__file__))

def _load(name):
    p = os.path.join(_BASE, 'data', name)
    try:
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

_ZONES = _load('florr_zones.json')
_PORTALS = _load('florr_portals.json')

# diff -> 稀有度档(对齐config秒杀等级)
DIFF_RARITY = [(0, 'common'), (15, 'unusual'), (30, 'rare'), (53, 'epic'),
               (67, 'legendary'), (80, 'mythic'), (100, 'ultra')]


def rarity_for_diff(diff):
    """难度档 -> 稀有度档名"""
    best = 'common'
    for d, r in DIFF_RARITY:
        if diff is not None and diff >= d:
            best = r
    return best


def map_zones(map_name):
    """某地图的刷怪区列表 [(x, y, diff, rarity, mobs, name), ...]"""
    m = (_ZONES.get('maps') or {}).get(map_name)
    if not m:
        return []
    out = []
    for z in m.get('zones', []):
        out.append((z['x'], z['y'], z.get('difficulty'),
                    rarity_for_diff(z.get('difficulty')), z.get('mobs'), z.get('name')))
    return out


def zones_for_rarity(map_name, rarity):
    """按稀有度档筛选刷怪区(用户kill_rank对应)"""
    return [z for z in map_zones(map_name) if z[3] == rarity]


def nearest_zone(map_name, x, y):
    """当前坐标最近的刷怪区"""
    best, bd = None, 1e18
    for z in map_zones(map_name):
        d = math.hypot(z[0] - x, z[1] - y)
        if d < bd:
            best, bd = z, d
    return best


def recommend_zone(map_name, kill_rank):
    """按秒杀等级推荐刷怪区(难度<=秒杀档里价值最高的)"""
    cands = [z for z in map_zones(map_name) if z[3] == kill_rank]
    if not cands:
        # 回退: 取低于或等于秒杀档的最高档
        idx = next((i for i, (d, r) in enumerate(DIFF_RARITY) if r == kill_rank), 1)
        cands = [z for z in map_zones(map_name)
                 if DIFF_RARITY.index((next((d for d, r in DIFF_RARITY if r == z[3]), 0), z[3])) <= idx]
        if not cands:
            cands = map_zones(map_name)
    if not cands:
        return None
    return max(cands, key=lambda z: z[2] if z[2] is not None else 0)


def all_portals():
    """世界传送门表 [(x, y, targetMap, targetSpawn, to), ...]"""
    return _PORTALS.get('portals', [])


def portal_near(x, y, radius=300):
    """当前位置附近(radius内)的传送门 -> 走捷径"""
    out = []
    for pt in all_portals():
        if math.hypot(pt['x'] - x, pt['y'] - y) <= radius:
            out.append(pt)
    return out


def map_names():
    return sorted((_ZONES.get('maps') or {}).keys())


if __name__ == '__main__':
    print('地图:', map_names())
    for mn in ('desert', 'anthell' if 'anthell' in map_names() else 'ant_hell'):
        zs = map_zones(mn)
        print(f'--- {mn} {len(zs)}区 ---')
        for z in zs[:6]:
            print('  %s diff=%s at(%d,%d) %s' % (z[5], z[2], z[0], z[1], z[4]))
        print('  推荐 mythic 区:', recommend_zone(mn, 'mythic'))
    print('--- 传送门 ---')
    for p in all_portals():
        print(' ', p)
