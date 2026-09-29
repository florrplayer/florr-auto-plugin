"""从wasm运行时偷到的完整怪物/花瓣数据库
插件根据怪物HP判断能不能秒杀，自动选择打/逃/无视
"""
import json, os

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

# 稀有度顺序(从低到高)
RARITY_ORDER = ['Common', 'Rare', 'Super', 'Epic', 'Legendary', 'Mythic', 'Ultra', 'Super', 'Unique']

# 颜色→稀有度(截图识别用)
COLOR_TO_RARITY = {
    'common': 'Common',
    'rare': 'Rare',
    'super': 'Super',
    'epic': 'Epic',
    'legendary': 'Legendary',
    'mythic': 'Mythic',   # 青 #1fdbde
    'ultra': 'Ultra',     # 粉 #ff2b75
}

_mob_cache = None

def load_mobs():
    global _mob_cache
    if _mob_cache:
        return _mob_cache
    path = os.path.join(DATA_DIR, 'mob_stats_full.json')
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        mobs = json.load(f)
    _mob_cache = {m['sid']: m for m in mobs}
    return _mob_cache

def get_mob_hp(sid, rarity_name):
    """获取某怪物某稀有度的HP范围"""
    mobs = load_mobs()
    m = mobs.get(sid)
    if not m:
        return None
    for r in m['rarities']:
        if r.get('rarity') == rarity_name:
            hp = r.get('HealthRange', r.get('Health', None))
            return hp
    return None

def get_mob_damage(sid, rarity_name):
    mobs = load_mobs()
    m = mobs.get(sid)
    if not m:
        return None
    for r in m['rarities']:
        if r.get('rarity') == rarity_name:
            return r.get('Damage', None)
    return None

def can_one_shot(sid, rarity_name, player_dps):
    """根据玩家DPS判断能不能秒杀
    返回: 'oneshot'=能秒, 'fight'=能打, 'flee'=打不过
    """
    hp = get_mob_hp(sid, rarity_name)
    if hp is None:
        return 'unknown'
    if isinstance(hp, list):
        max_hp = hp[1]  # 取最高HP
    else:
        max_hp = hp
    if player_dps <= 0:
        return 'unknown'
    # 假设1秒内打死=秒杀
    if max_hp <= player_dps:
        return 'oneshot'
    # 3秒内能打死=能打
    if max_hp <= player_dps * 3:
        return 'fight'
    return 'flee'

def get_threat_level(sid, rarity_name):
    """威胁等级: 1=最弱, 9=最强"""
    mobs = load_mobs()
    m = mobs.get(sid)
    if not m:
        return 5
    for i, r in enumerate(m['rarities']):
        if r.get('rarity') == rarity_name:
            return i + 1
    return 5

# 特殊优先怪物(用户要求优先打)
PRIORITY_MOBS = ['square', 'shiny', 'gold_leaf_beetle', 'dive_ant']

# 危险怪物(需要避开)
DANGEROUS_MOBS = ['ant_queen', 'ant_hole', 'hornet', 'centipede_evil']

if __name__ == '__main__':
    mobs = load_mobs()
    print(f"已加载 {len(mobs)} 个怪物数据")
    for sid in ['rock', 'square', 'ant_soldier', 'ladybug']:
        if sid in mobs:
            for r in mobs[sid]['rarities'][:6]:
                hp = r.get('HealthRange', r.get('Health', '?'))
                print(f"  {sid:15s} {r['rarity']:12s} HP={hp}")
