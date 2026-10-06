# -*- coding: utf-8 -*-
"""real_stats.py v1.27.1 - 真实官方数值校准层 (数据源: data/real_florr_mob_stats.json)
从 florr_clone 偷到的真实官方 82 怪转储: 每怪 base_health × 9 稀有度 + damage/armor/lightning_damage
用途: 秒杀判定/威胁评估用真实 HP 而非自平衡估算; 补全插件缺失的 10 个部件/NPC 怪
"""
import json, os

_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'real_florr_mob_stats.json')

# 插件稀有度名 -> 真实表键
RARITY_KEY = {
    'Common': 'common', 'Unusual': 'unusual', 'Rare': 'rare', 'Epic': 'epic',
    'Legendary': 'legendary', 'Mythic': 'mythic', 'Ultra': 'ultra',
    'Super': 'super', 'Unique': 'unique',
}

_cache = None


def _load():
    global _cache
    if _cache is None:
        with open(_DATA, encoding='utf-8') as f:
            raw = json.load(f)
        _cache = {'scale': raw['health_scale_by_rarity'],
                  'by_sid': {m['name']: m for m in raw['mobs']}}
    return _cache


def real_health(sid, rarity='Common'):
    """真实官方 HP; 未知稀有度回退 scale*base; 未知怪返回 None"""
    d = _load()
    m = d['by_sid'].get(sid)
    if not m:
        return None
    key = RARITY_KEY.get(rarity)
    if key and key in m.get('health_by_rarity', {}):
        return m['health_by_rarity'][key]
    base = m.get('base_health', 0)
    return base * d['scale'].get(key or 'common', 1.0)


def real_damage(sid):
    m = _load()['by_sid'].get(sid)
    return m.get('damage', 0) if m else 0


def real_armor(sid):
    m = _load()['by_sid'].get(sid)
    return m.get('armor', 0) if m else 0


def real_lightning(sid):
    m = _load()['by_sid'].get(sid)
    return bool(m.get('lightning_damage')) if m else False


def kill_time(sid, rarity, dps):
    """真实秒杀所需秒数; dps<=0 或未知怪返回 None (表示无法秒)"""
    if dps <= 0:
        return None
    hp = real_health(sid, rarity)
    if hp is None:
        return None
    return hp / dps


def can_kill(sid, rarity, dps, max_sec=2.0):
    """是否能在 max_sec 内秒杀 (真实官方 HP)"""
    t = kill_time(sid, rarity, dps)
    return t is not None and t <= max_sec


def calibrate_mob_db():
    """把真实数值写回 mob_db 模块级缓存 (不落盘, 运行时校准)"""
    try:
        import mob_db
    except ImportError:
        return False
    d = _load()
    for sid, m in d['by_sid'].items():
        setattr(mob_db, 'REAL_' + sid.upper().replace('-', '_'), {
            'damage': m.get('damage'), 'armor': m.get('armor'),
            'lightning': bool(m.get('lightning_damage')),
        })
    return True


def missing_sids():
    """真实表有而插件没有的怪 (补全用)"""
    try:
        from mob_db import MOB_CN
    except ImportError:
        return []
    return sorted(set(_load()['by_sid'].keys()) - set(MOB_CN.keys()))


if __name__ == '__main__':
    print('=== real_stats 测试 ===')
    cases = [('rock', 'Common'), ('beetle', 'Mythic'), ('scorpion', 'Ultra'),
             ('ant_soldier', 'Legendary'), ('sandstorm', 'Epic'), ('centipede_desert', 'Mythic')]
    for sid, r in cases:
        print(f'  {sid:20s} {r:9s} HP={real_health(sid, r):>12,.0f}  dmg={real_damage(sid):>8}  '
              f'armor={real_armor(sid)}  500dps秒杀={kill_time(sid, r, 500):.2f}s')
    print(f'  缺失怪补全: {missing_sids()}')
    print(f'  calibrate_mob_db: {calibrate_mob_db()}')
