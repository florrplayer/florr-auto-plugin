# -*- coding: utf-8 -*-
"""combat_strategy.py v1.27.0 - 战斗策略表 (移植 florr-auto-farm enemy_detect.py 实测策略, 映射到本地sid体系)
来源: reference-florr-tools/florr-auto-farm/enemy_detect.py
  - classify_action: ENGAGE(正常接战)/CAUTIOUS(可打但保持距离)/AVOID(不打)
    Mythic及以下全ENGAGE; Ultra蝎子/甲虫AVOID; Ultra沙尘暴/仙人掌/沙蜈蚣/火蚁CAUTIOUS
  - priority_score: (稀有度档, 物种档) 元组 - 稀有度碾压, 物种只做同档平手规则
  - MYTHIC_KITE: Mythic怪走位表 (strafe垂直环绕/ram直接撞/hold站桩保持距离)
  - MYTHIC_TARGET_RANK: 多个Mythic在场先打谁
"""
# 稀有度档序 (与 mob_db 13档同向, 这里取 combat 需要的 10 档)
RARITY_ORDER = ['Common', 'Unusual', 'Rare', 'Epic', 'Legendary',
                'Mythic', 'Ultra', 'Super', 'Eternal', 'Unique']
RARITY_RANK = {name: i for i, name in enumerate(RARITY_ORDER)}

# 物种优先级 (数值越大越优先; 只做同稀有度平手规则) - 沙漠+蚁狱实测表映射到sid
SPECIES_RANK = {
    'sandstorm': 5,          # 沙暴: 刷怪目标本身, 最高
    'cactus': 4,             # 仙人掌: 站桩带刺
    'beetle': 3,             # 甲虫
    'scorpion': 2,           # 蝎子
    'centipede_desert': 1,   # 沙蜈蚣
    'fire_ant_soldier': 1,   # 火兵蚁
    'ant_baby': 1, 'ant_worker': 1, 'ant_soldier': 1, 'ant_queen': 1,
    'ant_egg': 1,
    # 稀有怪并入高权重 (配合 mob_db.PRIORITY_SIDS 的5000倍加成)
    'square': 5, 'ladybug_shiny': 5, 'leafbug': 5,
    'gambler': 5, 'dandelion': 5, 'termite_overmind': 5,
}

# Ultra档危险对 (实测: 不打, 触发规避)
AVOID_PAIRS = {
    ('scorpion', 'Ultra'), ('beetle', 'Ultra'),
}
# Ultra档谨慎对 (可打但保持距离)
CAUTIOUS_PAIRS = {
    ('sandstorm', 'Ultra'), ('cactus', 'Ultra'),
    ('centipede_desert', 'Ultra'), ('fire_ant_soldier', 'Ultra'),
}

# Mythic怪走位策略 (sid -> 走位): strafe垂直环绕打空/ram直接撞/hold站桩保持距离
MYTHIC_KITE_SIDS = {
    'beetle': 'strafe',           # 直冲型, 垂直环绕让它打空
    'fire_ant_soldier': 'strafe',
    'scorpion': 'ram',            # 直接撞
    'centipede_desert': 'ram',
    'cactus': 'hold',             # 站桩带刺, 保持距离在旁边
    # 扩展: 蟑螂/螃蟹已有打带跑横移(v1.25.2), 这里统一归类
    'roach': 'strafe',
    'crab': 'strafe',
    'shell': 'hold',
}

# 多个Mythic同时在场先打谁 (只用于Mythic锁定)
MYTHIC_TARGET_RANK = {
    'beetle': 5,
    'fire_ant_soldier': 4,
    'scorpion': 3,
    'centipede_desert': 2,
    'cactus': 1,
}


def classify_action(sid, rarity):
    """(sid, 稀有度) -> ENGAGE/CAUTIOUS/AVOID
    Mythic及以下全ENGAGE; Ultra蝎子/甲虫AVOID; Ultra沙尘暴/仙人掌/沙蜈蚣/火蚁CAUTIOUS;
    比Ultra还稀有没规则覆盖 -> AVOID(失败方向选"别惹") """
    if RARITY_RANK.get(rarity, 9) < RARITY_RANK['Ultra']:
        return 'ENGAGE'
    if (sid, rarity) in AVOID_PAIRS:
        return 'AVOID'
    if (sid, rarity) in CAUTIOUS_PAIRS:
        return 'CAUTIOUS'
    return 'AVOID'


def priority_score(sid, rarity):
    """排序键: (稀有度档, 物种档) - 数值越大越优先"""
    return (RARITY_RANK.get(rarity, 0), SPECIES_RANK.get(sid, 0))


def mythic_kite(sid):
    """Mythic怪走位策略名 (strafe/ram/hold), 不在表内返回None"""
    return MYTHIC_KITE_SIDS.get(sid)


def mythic_priority(sid):
    """Mythic锁定顺序 (越大越先), 不在表内0"""
    return MYTHIC_TARGET_RANK.get(sid, 0)


if __name__ == '__main__':
    print("=== combat_strategy 测试 ===")
    cases = [
        ('beetle', 'Legendary'), ('beetle', 'Mythic'), ('beetle', 'Ultra'),
        ('scorpion', 'Ultra'), ('sandstorm', 'Ultra'), ('cactus', 'Ultra'),
        ('centipede_desert', 'Ultra'), ('fire_ant_soldier', 'Ultra'),
        ('ant_soldier', 'Mythic'), ('square', 'Mythic'), ('starfish', 'Super'),
    ]
    for sid, r in cases:
        print(f"  {sid:20s} {r:9s} -> {classify_action(sid, r):8s} score={priority_score(sid, r)} kite={mythic_kite(sid)}")
    print(f"  MYTHIC_TARGET_RANK: {MYTHIC_TARGET_RANK}")
