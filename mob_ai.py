# -*- coding: utf-8 -*-
"""从wasm反汇编提取的怪物AI数据 - 追击/巡逻范围"""

import mob_db


def _rule_number(name, fallback):
    value = mob_db.ai_rule(name, fallback)
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0 else fallback


LOSE_RANGE_MULT = _rule_number('detection_lose_multiplier', 1.5)
PATROL_CYCLE_SEC = _rule_number(
    'patrol_cycle_sec', _rule_number('idle_move_duration_ticks', 2.5))
HOMING_RADIUS = _rule_number('homing_radius', 300)

# 怪物追击范围(地图像素)
# 怪物在这个距离内会主动追玩家
AGGRO_RANGE = {
    'default': 255,       # 大部分怪
    'aggressive': 360,    # 攻击性强的(蜈蚣/黄蜂)
    'very_aggressive': 380,
    'passive': 60,        # 被动怪(石头/仙人掌)
    'turret': 100,        # 远程炮台
    'boss': 250,          # Boss
}

# 怪物巡逻范围(离开出生点多远)
PATROL_RANGE = {
    'default': 130,
    'drifter': 280,       # 到处走的
    'stationary': 0,       # 不动的(蚁穴)
}

# 攻击频率(秒)
ATTACK_COOLDOWN = {
    'fast': 0.5,
    'normal': 1.0,
    'slow': 2.0,
}


def get_aggro_range(mob_type='default'):
    if mob_type not in AGGRO_RANGE:
        import mob_db
        if mob_db.get_mob(mob_type):
            return mob_db.aggro_radius(mob_type)
    return AGGRO_RANGE.get(mob_type, 255)


def is_dangerous_to_approach(distance, mob_type='default'):
    """离怪物多近会被追"""
    return distance < get_aggro_range(mob_type)


def is_detached(distance, detection_radius):
    """目标距离超过发现半径的丢失倍率时，怪物会放弃追击。"""
    return distance > LOSE_RANGE_MULT * detection_radius


def is_turning_soon(moving_seconds, lead_time=0.35):
    """判断当前移动段是否临近随机转向点。"""
    if moving_seconds < 0 or lead_time < 0:
        return False
    remaining = PATROL_CYCLE_SEC - (moving_seconds % PATROL_CYCLE_SEC)
    return remaining <= lead_time


if __name__ == '__main__':
    print("=== 怪物AI范围 ===")
    for name, r in AGGRO_RANGE.items():
        print(f"  {name:20s} 追击范围={r}px")
    print(f"\n安全距离: 保持 {max(AGGRO_RANGE.values())}px 外不被追")
