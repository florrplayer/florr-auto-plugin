# -*- coding: utf-8 -*-
"""v1.10.0: 用偷到的怪物数据库优化战斗选择
- 优先打特殊怪(square/shiny/金叶虫/潜水兵蚁)
- 根据怪物种类+稀有度查HP,判断能不能打
- 危险怪(蚁后/蚁穴/蜈蚣)自动避开
"""
import math

# 特殊优先怪(用户要求)
PRIORITY_SIDS = {'square', 'shiny', 'gold_leaf_beetle', 'dive_ant'}

# 危险怪(自动避开,不主动打)
DANGER_SIDS = {'ant_queen', 'ant_hole', 'centipede_evil', 'hornet'}

# 怪种威胁权重(数值越大越优先打,偷来的HP数据排序)
# 小血怪优先打(经验/血比好)
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
    'hornet': 20,         # 危险,降低优先级
    'ant_queen': -10,     # 危险,不打
    'ant_hole': -10,      # 危险,不打
}


def score_target(m, player_map, patrol_goal, dev_limit):
    """给目标打分: 分数越高越优先
    m: (x, y, r, sid) 或 (x, y)
    返回: (score, should_attack)
    """
    mx, my = m[0], m[1]
    sid = m[3] if len(m) > 3 else None

    # 距离分(越近越好)
    d = math.hypot(mx - player_map[0], my - player_map[1])

    # 偏离巡逻点惩罚
    dev = math.hypot(mx - patrol_goal[0], my - patrol_goal[1])
    if dev > dev_limit:
        return -999, False  # 偏离太远,不打

    # 基础分 = 距离反比
    score = 1000.0 / (d + 1)

    # 特殊怪加成
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


# ===== 碰撞箱半径(Common基准, 地图像素) =====
# 从wasm运行时+游戏实测整理
MOB_RADIUS = {
    'rock': 10, 'cactus': 12, 'ladybug': 14, 'bee': 11,
    'ant_baby': 7, 'ant_worker': 10, 'ant_soldier': 13,
    'ant_queen': 25, 'ant_hole': 30,
    'beetle': 16, 'hornet': 12,
    'centipede': 8, 'centipede_evil': 8, 'centipede_desert': 10,
    'square': 9,
}

# 稀有度缩放(官方: Unusual x1.1/Rare x1.3/Epic x1.5/Mythic x3/Super x10)
RARITY_SCALE = {
    'common': 1.0, 'unusual': 1.1, 'rare': 1.3, 'epic': 1.5,
    'legendary': 2.0, 'mythic': 3.0, 'ultra': 6.0, 'super': 10.0,
}


def get_mob_radius(sid, rarity='common'):
    """获取怪物实际碰撞半径(地图像素)"""
    base = MOB_RADIUS.get(sid, 10)
    scale = RARITY_SCALE.get(rarity, 1.0)
    return base * scale


def get_attack_distance(sid, rarity='common'):
    """根据怪种+稀有度返回最佳攻击距离(停在怪碰撞箱外)"""
    r = get_mob_radius(sid, rarity)
    # 小近身怪贴脸,远程怪保持距离
    if sid in ('hornet',):
        return r + 5  # 远程怪多保持5px
    if sid in ('centipede', 'centipede_evil'):
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
