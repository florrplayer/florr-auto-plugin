# -*- coding: utf-8 -*-
"""统一游戏数据库 - 一次性加载所有偷来的数据,内存中快速查询
v1.11.0: 合并 all_mobs/all_petals/all_talents/mob_threat/map_data 为单例
"""
import json, os, threading

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
_lock = threading.Lock()
_cache = {}

RARITY_ORDER = ['Common','Rare','Super','Epic','Legendary','Mythic','Ultra','Super','Unique']
RARITY_COLOR_HEX = {
    'Common': '#cccccc', 'Rare': '#4488ff', 'Super': '#44dd44',
    'Epic': '#aa44ff', 'Legendary': '#ff8800', 'Mythic': '#1fdbde',
    'Ultra': '#ff2b75', 'Unique': '#ffd700',
}


def _load(name):
    if name in _cache:
        return _cache[name]
    path = os.path.join(_DATA_DIR, name)
    if not os.path.exists(path):
        _cache[name] = {}
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        _cache[name] = json.load(f)
    return _cache[name]


# ===== 怪物 =====
def mobs():
    """返回 {sid: mob_data} 字典"""
    raw = _load('mob_stats_full.json')
    if isinstance(raw, list):
        return {m['sid']: m for m in raw}
    return raw

def mob(sid):
    return mobs().get(sid)

def mob_hp(sid, rarity):
    m = mob(sid)
    if not m: return None
    for r in m.get('rarities', []):
        if r.get('rarity') == rarity:
            return r.get('HealthRange', r.get('Health'))
    return None

def mob_damage(sid, rarity):
    m = mob(sid)
    if not m: return None
    for r in m.get('rarities', []):
        if r.get('rarity') == rarity:
            return r.get('Damage')
    return None

def mob_exp(sid, rarity):
    m = mob(sid)
    if not m: return None
    for r in m.get('rarities', []):
        if r.get('rarity') == rarity:
            return r.get('exp', 0)
    return 0


# ===== 花瓣 =====
def petals():
    raw = _load('all_petals.json')
    # all_petals是多个JSON对象连在一起,解析过的在mob_stats里没有,直接用原始
    return raw


# ===== 地图 =====
def map_data():
    return _load('wasm_map_data.json')


# ===== 威胁等级 =====
def threat(sid, rarity):
    """返回威胁等级 1-9"""
    if rarity in RARITY_ORDER:
        return RARITY_ORDER.index(rarity) + 1
    return 5


# ===== 查询接口 =====
def can_fight(sid, rarity, player_dps):
    """根据玩家DPS判断: 'oneshot'/'fight'/'flee'/'unknown'"""
    hp = mob_hp(sid, rarity)
    if hp is None: return 'unknown'
    max_hp = hp[1] if isinstance(hp, list) else hp
    if player_dps <= 0: return 'unknown'
    if max_hp <= player_dps: return 'oneshot'
    if max_hp <= player_dps * 3: return 'fight'
    return 'flee'


def summary():
    """打印数据库摘要"""
    m = mobs()
    print(f"怪物数据库: {len(m)}个怪物")
    print(f"地图数据: {len(map_data())}条")
    return f"mobs={len(m)}"


if __name__ == '__main__':
    summary()
    print(f"square Mythic HP: {mob_hp('square','Mythic')}")
    print(f"bee Common HP: {mob_hp('bee','Common')}")
    print(f"能打测试(玩家DPS=10000): {can_fight('rock','Legendary',10000)}")
