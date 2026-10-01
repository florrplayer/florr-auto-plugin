# -*- coding: utf-8 -*-
"""v1.18.0: 用统一数据层(mob_db)优化战斗选择
- 优先打特殊怪(正方形/闪亮瓢虫/金叶虫/潜水兵蚁) - 官方sid, 真正生效
- 真实碰撞箱(wasm反汇编73怪)决定攻击距离
- 危险怪自动避开 + 掉落价值加权
"""
import math
import mob_db

# 特殊优先怪(用户要求, 官方sid - 与combat.py返回格式一致)
PRIORITY_SIDS = {'square', 'ladybug_shiny', 'leafbug_shiny', 'ant_soldier_diver'}
# 兼容旧简写(旧配置/旧代码)
_LEGACY_PRIORITY = {'shiny': 'ladybug_shiny', 'gold_leaf_beetle': 'leafbug_shiny',
                    'dive_ant': 'ant_soldier_diver'}

# 危险怪(自动避开,不主动打) - 统一走 mob_db.DANGER_SIDS
DANGER_SIDS = mob_db.DANGER_SIDS

# 怪种威胁权重(数值越大越优先打, 来自HP数据排序)
THREAT_PRIORITY = {
    'square': 100,        # 最优先,35血秒秒
    'rock': 90,           # 50-100血
    'cactus': 85,
    'bee': 80,
    'ladybug': 75,
    'ant_baby': 70,
    'ant_worker': 65,
    'ant_soldier': 60,
    'beetle': 50,
    'centipede': 40,
    'ladybug_shiny': 150,   # 特殊怪(闪亮瓢虫)
    'leafbug_shiny': 150,   # 特殊怪(金叶虫)
    'ant_soldier_diver': 150,  # 特殊怪(潜水兵蚁)
    'hornet': 20,         # 危险,降低优先级
    'ant_queen': -10,     # 危险,不打
    'ant_hole': -10,      # 危险,不打
}


def _norm_sid(sid):
    """旧简写 -> 官方sid"""
    if sid is None:
        return None
    return _LEGACY_PRIORITY.get(sid, sid)


def score_target(m, player_map, patrol_goal, dev_limit):
    """给目标打分: 分数越高越优先
    m: (x, y, r, sid) 或 (x, y)
    返回: (score, should_attack)
    """
    mx, my = m[0], m[1]
    sid = _norm_sid(m[3] if len(m) > 3 else None)

    # 距离分(越近越好)
    d = math.hypot(mx - player_map[0], my - player_map[1])

    # 偏离巡逻点惩罚
    dev = math.hypot(mx - patrol_goal[0], my - patrol_goal[1])
    if dev > dev_limit:
        return -999, False  # 偏离太远,不打

    # 基础分 = 距离反比
    score = 1000.0 / (d + 1)

    # 特殊怪加成(官方sid生效)
    if sid in PRIORITY_SIDS:
        score *= 5.0  # 特殊怪5倍优先

    # 危险怪惩罚
    if sid in DANGER_SIDS:
        return -999, False  # 危险怪不打

    # 怪种优先级
    if sid and sid in THREAT_PRIORITY:
        score += THREAT_PRIORITY[sid]

    return score, True


def choose_target_smart(mobs_map, patrol_goal, player_map=None, dev_limit=None):
    """智能选目标: 优先特殊怪 + 距离最近 + 不偏离巡逻点
    mobs_map: [(x, y, r, sid), ...] 地图坐标
    """
    if player_map is None or not mobs_map:
        return None

    if dev_limit is None:
        from combat import DEVIATION
        dev_limit = DEVIATION + math.hypot(player_map[0] - patrol_goal[0],
                                           player_map[1] - patrol_goal[1])

    best, best_score = None, -999
    for m in mobs_map:
        score, ok = score_target(m, player_map, patrol_goal, dev_limit)
        if ok and score > best_score:
            best, best_score = m, score

    return best


# ===== 战斗距离优化 =====
# 根据怪种调整攻击距离(不用统一距离0.5px)
# 小近身怪贴脸打,远程怪保持距离
ATTACK_DISTANCE = {
    'square': 2,          # 正方形,保持2px
    'rock': 3,
    'cactus': 3,
    'bee': 2,
    'ladybug': 2,
    'ant_baby': 1,
    'ant_worker': 2,
    'ant_soldier': 2,
    'beetle': 3,
    'centipede': 3,
    'hornet': 5,         # 黄蜂远程,保持距离
    'ant_queen': 0,       # 不打
    'ant_hole': 0,        # 不打
}

DEFAULT_ATTACK_DIST = 2  # 默认2px


def get_mob_radius(sid, rarity='Common'):
    """真实碰撞箱(地图像素) - wasm反汇编73怪表(mob_db), 官方稀有度缩放"""
    return mob_db.get_radius(_norm_sid(sid), rarity)


def get_attack_distance(sid, rarity='Common'):
    """根据怪种+稀有度+追击速度+突破点战术返回最佳攻击距离(停在怪真实碰撞箱外)
    v1.19.8: 追得上的怪(aggro_speed>=1.0, 蝎子/蜘蛛/沙漠蜈蚣)保持更大距离防接触伤害
    v1.20.1: BREAKTHROUGH 突破点 - 水母/萤火虫/冥界甲虫贴脸(电波中心安全/传送前秒掉),
              岩石/仙人掌/赌徒远程, 黄蜂/胡蜂打带跑"""
    r = get_mob_radius(sid, rarity)
    bt = mob_db.BREAKTHROUGH.get(_norm_sid(sid))
    if bt:
        mode = bt['dist_mode']
        if mode == 'close':
            return r + 1   # 贴脸: 水母电波中心安全, 冥界甲虫传送前快速输出
        if mode == 'kite':
            return r + 6   # 打带跑: 黄蜂/胡蜂预判导弹, 保持距离+折返
        return r + 6       # far: 岩石反击弹幕/赌徒花瓣圈, 保持距离
    spd = mob_db.get_aggro_speed(_norm_sid(sid))
    # 追得上的高威胁怪: 保持距离(远程/冲撞都别贴脸)
    if spd >= 1.0:
        return r + 6  # 追击速度≥1.0(追得上玩家) - 保持6px, 蹭完就撤
    if sid in ('hornet', 'wasp', 'scorpion'):
        return r + 5  # 远程怪多保持5px
    if sid in ('centipede', 'centipede_evil', 'centipede_desert', 'centipede_hel'):
        return r + 3  # 长条怪保持3px
    return r + 1  # 其他贴脸1px


if __name__ == '__main__':
    # 测试
    player = (100, 100)
    goal = (150, 100)
    targets = [
        (120, 100, 5, 'square'),      # 正方形,近
        (130, 100, 10, 'rock'),       # 石头
        (200, 100, 15, 'ant_queen'),  # 蚁后,远
        (110, 110, 8, 'ladybug'),     # 瓢虫
    ]
    result = choose_target_smart(targets, goal, player, 50)
    print(f"选中目标: {result}")
