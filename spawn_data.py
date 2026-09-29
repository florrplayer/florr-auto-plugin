# -*- coding: utf-8 -*-
# florr.io 怪物生成权重 + shiny怪 + 特殊区域数据 (从wasm偷的)

# shiny怪 (特殊稀有)
SHINY_MOBS = {
    "ladybug_shiny": {"name": "闪光瓢虫", "chance": 0.005, "note": "沙漠0.5%/花园2.5%"},
    "leafbug_shiny": {"name": "闪光叶虫", "chance": "稀有", "note": "丛林特殊颜色"},
}

# 各区域怪物生成权重 (从wasm字符串提取)
SPAWN_TABLE = {
    "garden_normal": "ant_baby:0.1, ladybug:1",
    "garden_spiral": "ant_worker:1, ant_soldier:2, worm:0.3, ant_hole:0.05, rock:0.5",
    "desert_normal": "cactus:1, fire_ant_burrow:0.01~0.025, beetle:0.5, sandstorm:0.5",
    "desert_shiny": "cactus:1, ladybug_shiny:0.005~0.025",
    "ocean_normal": "bubble:3, jellyfish:1, sponge:0.5",
    "ocean_jelly": "jellyfish:1",
    "jungle_normal": "firefly:0.1, leafbug:0.5, bush:0.3, wasp:0.5, centipede_evil:0.025",
    "jungle_firefly": "firefly:1, mantis:1",
    "anthell_normal": "ant_baby/worker/soldier递进, worm:0.3",
    "anthell_queen": "ant_queen:1, worm:0.3",
    "anthell_eggs": "ant_egg:1",
    "fireant_normal": "fire_ant系列递进",
    "fireant_queen": "fire_ant_queen:1, worm:0.3",
    "hel": "beetle_hel:3, wasp_hel:1, spider_hel:1, centipede_hel:0.1",
    "mecha": "mecha_flower:1, wasp_mecha:1, spider_mecha:1, crab_mecha:1",
}

# 特殊物体(障碍物/互动物)
SPECIAL_OBJECTS = [
    "rock", "bush", "bubble", "sponge", "ant_hole", "ant_egg",
    "fire_ant_burrow", "sandstorm", "beetle_mummy",
]

# 冥界(Hel)怪 - PvP区
HEL_MOBS = ["beetle_hel", "wasp_hel", "spider_hel", "centipede_hel"]

# 机械怪 - 特殊区域
MECHA_MOBS = ["mecha_flower", "wasp_mecha", "spider_mecha", "crab_mecha"]

# 高优先级目标 (优先打)
PRIORITY_TARGETS = {
    "ladybug_shiny": 100,  # shiny最高优先级
    "leafbug_shiny": 100,
    "ant_queen": 80,
    "fire_ant_queen": 80,
    "titan": 90,
    "mantis": 50,
    "firefly": 40,
    "centipede_evil": 45,
}

# 危险怪 (避开)
DANGEROUS_MOBS = {
    "beetle_hel": "PvP冥界",
    "wasp_hel": "PvP冥界",
    "spider_hel": "PvP冥界",
    "centipede_hel": "PvP冥界",
}

def get_target_priority(mob_id):
    """返回目标优先级,越大越优先"""
    return PRIORITY_TARGETS.get(mob_id, 10)

def is_shiny(mob_id):
    return mob_id in SHINY_MOBS

def is_dangerous(mob_id):
    return mob_id in DANGEROUS_MOBS
