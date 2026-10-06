# -*- coding: utf-8 -*-
"""skill_db.py v1.25.1 - 天赋倍率真源查询 (florr_clone/src/skill_multipliers.ts, 服务端权威)
STAT 曲线: 玩家自身属性(最大血量/身体伤害/花瓣血量) - server/playerManager.ts 用此算真实 HP/伤害
EFFECT 曲线: 花瓣效果(回血输出/花瓣伤害), 更陡
用法: from skill_db import skill_multiplier, skill_tiers
"""
import json, os

_DATA = None

def _load():
    global _DATA
    if _DATA is not None:
        return _DATA
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'skill_multipliers.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            _DATA = json.load(f)
    except Exception:
        _DATA = {}
    return _DATA

def skill_multiplier(tier, kind='stat'):
    """按天赋稀有度档查倍率: kind='stat'(玩家属性/血/身伤) 或 'effect'(花瓣效果/回血/花伤)
    例: skill_multiplier('mythic') -> 1.5; skill_multiplier('mythic','effect') -> 2.0
    未知档/缺数据返回 1.0 (中性)"""
    d = _load()
    table = d.get('STAT_SKILL_MULTIPLIERS' if kind == 'stat' else 'EFFECT_SKILL_MULTIPLIERS', {})
    return float(table.get(tier, 1.0))

def skill_tiers():
    """10 个天赋稀有度档 (弱到强)"""
    m = _load()
    return m.get('_meta', {}).get('tiers', [])

if __name__ == '__main__':
    print('tiers:', skill_tiers())
    for t in skill_tiers():
        print(f"  {t:10s} stat={skill_multiplier(t):.2f} effect={skill_multiplier(t,'effect'):.2f}")
