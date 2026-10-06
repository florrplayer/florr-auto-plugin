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
_TERRAIN = _load('florr_terrain.json')
# v1.23.0: 具体怪种刷怪区(florr_clone map_bundle.ts 247区中96个精确怪种区)
_SPAWN_ZONES = _load('florr_mob_spawn_zones.json')

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


# ===== v1.23.0: 具体怪种刷怪区 (map_bundle.ts 精确怪种区) =====
def spawn_zones_for(mobs_spec):
    """按怪种规格查刷怪区: 传入 'bee'/'ladybug'/'soldier_fire_ant' 或完整规格串
    返回 [(x, y, w, h), ...] (世界坐标, 与memory模式一致)"""
    z = (_SPAWN_ZONES.get('spawn_zones') or {})
    if mobs_spec in z:
        return z[mobs_spec]
    # 模糊匹配: 规格串包含怪名 (如 'soldier_fire_ant 60% worker_fire_ant 30%...')
    for spec, zs in z.items():
        if mobs_spec in spec:
            return zs
    return []


def nearest_spawn_zone(mobs_spec, x, y):
    """当前坐标最近的指定怪种刷怪区 (定向刷花瓣: 想要什么花瓣->去什么怪区)"""
    best, bd = None, 1e18
    for z in spawn_zones_for(mobs_spec):
        d = math.hypot(z['x'] - x, z['y'] - y)
        if d < bd:
            best, bd = z, d
    return best


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


# ===== 地形 (florr_clone tmj 地形层, v1.21.0) =====
def terrain_cell(map_name, x, y):
    """游戏坐标 -> (瓦片x, 瓦片y, 是否水域)"""
    t = (_TERRAIN.get('maps') or {}).get(map_name)
    if not t:
        return None
    ts = t['tile_size']
    w = t['grid'][0]
    tx, ty = int(x // ts), int(y // ts)
    water = (tx, ty) in t.get('_water_set', set())
    return (tx, ty, water)


def is_water(map_name, x, y, margin=0):
    """该坐标是否水域(不可通行区), margin=瓦片数缓冲"""
    t = (_TERRAIN.get('maps') or {}).get(map_name)
    if not t:
        return False
    ws = t.get('_water_set')
    if ws is None:
        ws = set((c[0], c[1]) for c in t.get('water', []))
        t['_water_set'] = ws
    ts = t['tile_size']
    tx, ty = int(x // ts), int(y // ts)
    if (tx, ty) in ws:
        return True
    if margin:
        for dx in range(-margin, margin + 1):
            for dy in range(-margin, margin + 1):
                if (tx + dx, ty + dy) in ws:
                    return True
    return False


def water_summary():
    """各图水域占比"""
    return {k: {'water_cells': v.get('water_cells'), 'pct': round(100.0 * v['water_cells'] / (v['grid'][0] * v['grid'][1]), 1)}
            for k, v in (_TERRAIN.get('maps') or {}).items()}


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
