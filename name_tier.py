# -*- coding: utf-8 -*-
"""name_tier.py v1.28.0 - 怪名/稀有度词双信源识别 (截图/画布模式兜底信源)
数据与思路来源: greatluca666/florr-auto-farm (GPLv3, 取数据与识别逻辑独立实现)
- 怪名: 英文名/中文名/slug 三种写法归一 -> 本图物种 slug (画布名牌文本直接读)
- 稀有度: 名牌颜色(实测色表) 为主信源, 稀有度词(中/英文)为第二信源, 颜色优先
用途: bridge 协议字段缺失时(截图模式/画布文本), 用名牌文字兜底识别, 比纯颜色识别准一个量级
"""
import re

RARITY_ORDER = ["Common", "Unusual", "Rare", "Epic", "Legendary",
                "Mythic", "Ultra", "Super", "Eternal", "Unique"]

# 名牌稀有度词(中/英) -> 档位下标 (第二信源; 颜色认不出时兜底)
RANK_BY_RARITY_WORD = {
    "普通": 0, "罕见": 1, "稀有": 2, "史诗": 3, "传奇": 4,
    "神话": 5, "究极": 6, "超神": 7, "独特": 9,
    "common": 0, "unusual": 1, "rare": 2, "epic": 3, "legendary": 4,
    "mythic": 5, "ultra": 6, "super": 7, "eternal": 8, "unique": 9,
}

# 名牌稀有度颜色(#RRGGBB) -> 档位下标 (主信源, 实测)
RANK_BY_RARITY_COLOR = {
    "#7EEF6D": 0, "#FFE65D": 1, "#4D52E3": 2, "#861FDE": 3, "#DE1F1F": 4,
    "#1FDBDE": 5, "#FF2B75": 6, "#2BFFA3": 7, "#555555": 9,
}

# 46 物种: slug -> {en, zh} (游戏本地化表 + 实机确认)
SPECIES_NAMES = {
    "scorpion": {"en": "Scorpion", "zh": "蝎子"},
    "beetle": {"en": "Beetle", "zh": "甲虫"},
    "cactus": {"en": "Cactus", "zh": "仙人掌"},
    "sandstorm": {"en": "Sandstorm", "zh": "沙尘暴"},
    "sand_centipede": {"en": "Centipede", "zh": "蜈蚣"},
    "soldier_fire_ant": {"en": "Soldier Fire Ant", "zh": "火兵蚁"},
    "baby_ant": {"en": "Baby Ant", "zh": "幼蚁"},
    "worker_ant": {"en": "Worker Ant", "zh": "工蚁"},
    "soldier_ant": {"en": "Soldier Ant", "zh": "兵蚁"},
    "worm": {"en": "Worm", "zh": "蠕虫"},
    "queen_ant": {"en": "Queen Ant", "zh": "蚁后"},
    "ant_egg": {"en": "Ant Egg", "zh": "蚁卵"},
    "rock": {"en": "Rock", "zh": "岩石"},
    "ladybug": {"en": "Ladybug", "zh": "瓢虫"},
    "bee": {"en": "Bee", "zh": "蜜蜂"},
    "bumble_bee": {"en": "Bumble Bee", "zh": "熊蜂"},
    "ant_hole": {"en": "Ant Hole", "zh": "蚁穴"},
    "hornet": {"en": "Hornet", "zh": "黄蜂"},
    "spider": {"en": "Spider", "zh": "蜘蛛"},
    "centipede": {"en": "Centipede", "zh": "蜈蚣"},
    "dandelion": {"en": "Dandelion", "zh": "蒲公英"},
    "mecha_flower": {"en": "Mecha Flower", "zh": "机械花"},
    "wasp": {"en": "Wasp", "zh": "胡蜂"},
    "crab": {"en": "Crab", "zh": "螃蟹"},
    "bubble": {"en": "Bubble", "zh": "泡泡"},
    "shell": {"en": "Shell", "zh": "扇贝"},
    "jellyfish": {"en": "Jellyfish", "zh": "水母"},
    "starfish": {"en": "Starfish", "zh": "海星"},
    "sponge": {"en": "Sponge", "zh": "海绵"},
    "leech": {"en": "Leech", "zh": "水蛭"},
    "baby_termite": {"en": "Baby Termite", "zh": "幼白蚁"},
    "worker_termite": {"en": "Worker Termite", "zh": "工白蚁"},
    "soldier_termite": {"en": "Soldier Termite", "zh": "兵白蚁"},
    "termite_overmind": {"en": "Termite Overmind", "zh": "白蚁女王"},
    "termite_egg": {"en": "Termite Egg", "zh": "白蚁卵"},
    "termite_mound": {"en": "Termite Mound", "zh": "白蚁丘"},
    "bush": {"en": "Bush", "zh": "灌木"},
    "firefly": {"en": "Firefly", "zh": "萤火虫"},
    "leafbug": {"en": "Leafbug", "zh": "叶虫"},
    "mantis": {"en": "Mantis", "zh": "螳螂"},
    "roach": {"en": "Roach", "zh": "蟑螂"},
    "moth": {"en": "Moth", "zh": "蛾"},
    "fly": {"en": "Fly", "zh": "苍蝇"},
    "silverfish": {"en": "Silverfish", "zh": "银鱼"},
    "garbage": {"en": "Garbage", "zh": "垃圾"},
    "barrel": {"en": "Barrel", "zh": "桶"},
}

# 每张图的物种白名单 (本图识别的 slug 集合)
MAP_SPECIES = {
    "desert": frozenset({"scorpion", "beetle", "cactus", "sandstorm",
                         "sand_centipede", "soldier_fire_ant"}),
    "anthell": frozenset({"baby_ant", "worker_ant", "soldier_ant", "worm", "queen_ant", "ant_egg"}),
    "garden": frozenset({"rock", "ladybug", "bee", "bumble_bee", "baby_ant", "worker_ant",
                         "soldier_ant", "queen_ant", "ant_egg", "ant_hole", "hornet", "spider",
                         "centipede", "dandelion", "mecha_flower", "wasp", "crab"}),
    "ocean": frozenset({"bubble", "shell", "crab", "jellyfish", "starfish", "sponge", "leech", "soldier_ant"}),
    "jungle": frozenset({"baby_termite", "worker_termite", "soldier_termite", "termite_overmind",
                         "termite_egg", "termite_mound", "bush", "centipede", "firefly",
                         "ladybug", "leafbug", "mantis", "wasp", "crab"}),
    "sewers": frozenset({"spider", "roach", "moth", "fly", "silverfish", "garbage"}),
    "factory": frozenset({"mecha_flower", "spider", "wasp", "crab", "barrel"}),
}

# 插件 sid 与本模块 slug 的别名映射 (沙漠蜈蚣 = centipede_desert; 火兵蚁 = fire_ant_soldier)
SID_BY_SLUG = {
    "sand_centipede": "centipede_desert",
    "soldier_fire_ant": "fire_ant_soldier",
    "baby_ant": "ant_baby",
    "worker_ant": "ant_worker",
    "soldier_ant": "ant_soldier",
    "queen_ant": "ant_queen",
    "ant_egg": "ant_egg",
    "baby_termite": "termite_baby",
    "worker_termite": "termite_worker",
    "soldier_termite": "termite_soldier",
    "termite_overmind": "termite_overmind",
    "termite_egg": "termite_egg",
    "termite_mound": "termite_mound",
    "leafbug": "leafbug",
}

_name_index_cache = {}


def _norm_name(name):
    return str(name).strip().lower().replace(" ", "_")


def _name_index(known):
    """frozenset(known) -> {归一化名字: slug} (英文/中文/slug 三写法)"""
    key = frozenset(known)
    if key in _name_index_cache:
        return _name_index_cache[key]
    index = {}
    for slug in key:
        names = SPECIES_NAMES.get(slug, {})
        for n in (names.get("en"), names.get("zh"), slug):
            if n:
                index[_norm_name(n)] = slug
    _name_index_cache[key] = index
    return index


def species_from_name(name, map_name=None):
    """怪物名牌文本 -> 本图物种 slug; 不是本图/未识别 -> None
    查找顺序: 本图物种表的中/英/slug 写法; 再查别名(沙漠蜈蚣等)"""
    if not name:
        return None
    known = MAP_SPECIES.get(map_name or "", frozenset())
    if not known:
        return None
    key = _norm_name(name)
    slug = _name_index(known).get(key)
    if slug is not None:
        return slug
    for s, sid in SID_BY_SLUG.items():
        if _norm_name(SPECIES_NAMES.get(s, {}).get("en", "")) == key or \
           _norm_name(SPECIES_NAMES.get(s, {}).get("zh", "")) == key or key == s:
            if sid in known or s in known:
                return s if s in known else sid
    return None


def tier_from_color(rarity_color=None, rarity_word=None):
    """名牌稀有度 -> RARITY_ORDER 档名; 颜色为主信源, 词兜底, 都认不出 -> Common"""
    rank = RANK_BY_RARITY_COLOR.get(rarity_color) if rarity_color else None
    if rank is None and rarity_word is not None:
        rank = RANK_BY_RARITY_WORD.get(str(rarity_word).strip().lower())
    return RARITY_ORDER[rank] if rank is not None else "Common"


def tier_rank(tier):
    try:
        return RARITY_ORDER.index(tier)
    except ValueError:
        return 0


if __name__ == '__main__':
    print('=== name_tier 测试 ===')
    cases = [("Scorpion", "desert"), ("蝎子", "desert"), ("Soldier Fire Ant", "desert"),
             ("兵蚁", "anthell"), ("Ant Egg", "anthell"), ("蜈蚣", "garden"),
             ("Centipede", "desert"), ("蜘蛛", "sewers")]
    for name, mp in cases:
        print(f'  {name:20s} {mp:8s} -> {species_from_name(name, mp)}')
    print()
    for color, word in [("#1FDBDE", "神话"), ("#FF2B75", "究极"), ("#DE1F1F", "传奇"),
                        (None, "mythic"), (None, "究极"), (None, "???")]:
        print(f'  色={color or "无":10s} 词={word:6s} -> {tier_from_color(color, word)}')
    print(f'  物种总数: {len(SPECIES_NAMES)}, 图数: {len(MAP_SPECIES)}')
