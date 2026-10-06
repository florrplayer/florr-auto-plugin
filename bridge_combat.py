# -*- coding: utf-8 -*-
"""v3: 从wasm内存bridge读取怪物数据 (玩家=camera固定地址, 怪=静态type id 1-83)
用法: 先跑 bridge_server.py + 浏览器注入v4脚本, 然后 main.py 地图 --memory
v1.18.0: 决策改用 mob_db 统一数据层(稀有度反推/真实碰撞箱/追击范围/掉落价值)
v1.25.2: find_best_target 加 sticky_sid 目标粘滞(AI研究§8.1-2)
"""
import time, math, json, urllib.request

import mob_db

BRIDGE_URL = "http://127.0.0.1:18899"

# ===== 怪物type ID -> 名字 (从wasm偷的all_mobs_full.json, id=静态怪id) =====
TYPE_NAMES = {
    1: "rock", 2: "cactus", 3: "ladybug", 4: "bee", 5: "ant_baby",
    6: "ant_worker", 7: "ant_soldier", 8: "ant_queen", 9: "ant_hole",
    10: "beetle", 11: "hornet", 12: "centipede", 14: "centipede_evil",
    16: "centipede_desert", 18: "square", 19: "ladybug_dark",
    20: "ladybug_shiny", 21: "spider", 22: "scorpion", 23: "fire_ant_soldier",
    24: "fire_ant_burrow", 25: "sandstorm", 26: "bubble", 27: "bumble_bee",
    28: "shell", 29: "starfish", 30: "crab", 31: "jellyfish", 32: "digger",
    33: "sponge", 34: "leech", 36: "dandelion", 37: "fire_ant_baby",
    38: "fire_ant_worker", 39: "fire_ant_queen", 40: "ant_egg",
    41: "fire_ant_egg", 42: "fly", 43: "leafbug", 44: "mantis",
    45: "termite_baby", 46: "termite_worker", 47: "termite_soldier",
    48: "termite_overmind", 49: "termite_mound", 50: "termite_egg",
    51: "bush", 52: "roach", 53: "moth", 54: "firefly",
    55: "beetle_hel", 56: "wasp", 58: "spider_hel", 59: "centipede_hel",
    61: "wasp_hel", 63: "gambler", 65: "firefly_magic", 67: "beetle_nazar",
    68: "worm", 70: "mecha_flower", 71: "wasp_mecha", 72: "spider_mecha",
    73: "leafbug_shiny", 74: "crab_mecha", 75: "assembler", 76: "barrel",
    77: "beetle_mummy", 78: "beetle_pharaoh", 79: "tomb", 80: "silverfish",
    81: "garbage", 82: "ant_soldier_diver", 83: "ghost",
}

# 稀有怪 (高价值目标) - 统一走 mob_db.PRIORITY_SIDS
PRIORITY_TYPES = {18, 20, 39, 44, 47, 63, 73, 75, 78, 82, 83}

# 危险怪 (需要避开) - 统一走 mob_db.DANGER_SIDS
DANGER_TYPES = {8, 9, 11, 12, 14, 16, 21, 22, 24, 25, 26, 31, 32, 34, 48, 52, 53, 55, 56, 58, 59, 61, 63, 70, 71, 72, 74, 75, 77, 78, 83}

# 过滤: 太弱的怪不打 (hp < 10)
MIN_MOB_HP = 10

# AI研究报告战斗规则 (怪物AI机制研究报告.md §8):
# - 打蚁卵会引蚂蚁 -> 不打卵(卵只在打破时刷怪)
# - 苍蝇90%闪避 -> 别浪费DPS
# - 沙尘暴穿透掩体且会吸人 -> 不打
NO_FIGHT_SIDS = {'ant_egg', 'fire_ant_egg', 'termite_egg', 'fly', 'sandstorm'}

# 玩家DPS估算(内存模式无花瓣扫描时): 由调用方传入, 默认200
DEFAULT_PLAYER_DPS = 200


def _fetch_latest():
    """从bridge_server拉最新数据 (跨进程)"""
    try:
        with urllib.request.urlopen(BRIDGE_URL, timeout=1) as r:
            return json.loads(r.read().decode())
    except:
        return {}


def get_player():
    """读camera固定地址 = 玩家世界坐标 (100%准确)"""
    d = _fetch_latest()
    px, py = d.get('px'), d.get('py')
    if px and py:
        return {'x': px, 'y': py, 'hp': None}
    return None


def get_nearby_mobs(max_dist=3000):
    """获取玩家附近怪物, 返回 (怪物列表, 玩家)
    附: sid/稀有度(HP反推)/真实碰撞箱/追击范围
    v1.19.7: 协议实体带 team 字段时只认野怪(team==WILD_TEAM), 玩家召唤物/友方(其他team)跳过不追
    内存模式(无team字段)保持原逻辑"""
    d = _fetch_latest()
    mobs = d.get('mobs', [])
    player = None
    px, py = d.get('px'), d.get('py')
    if px and py:
        player = {'x': px, 'y': py, 'hp': None}
    result = []
    for m in mobs:
        t = m.get('t', 0)
        # 只认真怪 (t 1-83), 排除玩家(t=1)
        if t < 1 or t > 83 or t == 1:
            continue
        # v1.19.7: team 过滤 - 有 team 字段且非野怪(召唤物/友方)不追
        tm = m.get('team')
        if tm is not None and tm != mob_db.WILD_TEAM:
            continue
        hp = m.get('hp', 0)
        # 排除太弱的噪音
        if hp < MIN_MOB_HP:
            continue
        x, y = m.get('x', 0), m.get('y', 0)
        # 边界检查
        if x < 1000 or y < 1000 or x > 64000 or y > 64000:
            continue
        # 距离过滤
        if player:
            dist = math.hypot(x - px, y - py)
            if dist > max_dist:
                continue
        sid = mob_db.type_id_to_sid(t) or TYPE_NAMES.get(t, f"mob_{t}")
        rarity = mob_db.rarity_infer(sid, hp)
        result.append({
            'x': x, 'y': y,
            'hp': hp,
            'type': t,
            'sid': sid,
            'rarity': rarity,
            'radius': mob_db.get_radius(sid, rarity),
            'aggro': mob_db.get_aggro(sid),
            'cn': mob_db.cn(sid),
        })
    return result, player


def get_danger_mobs(player_x, player_y, radius=400):
    """获取附近危险怪 (含追击范围判断: 危险怪在追击范围内才会主动来)
    v1.24.2: 危险 = DANGER集 OR hostile攻击性档(ai_type) - hostile怪进仇恨圈就会追你"""
    mobs, _ = get_nearby_mobs()
    danger = []
    for m in mobs:
        dist = math.hypot(m['x'] - player_x, m['y'] - player_y)
        if dist >= radius:
            continue
        sid = m.get('sid')
        if m['type'] in DANGER_TYPES or (sid and mob_db.is_hostile(sid)):
            danger.append(m)
    return danger


def get_attack_distance(sid, rarity='Common'):
    """贴脸攻击距离: 怪真实碰撞箱 + 贴脸余量0.5px"""
    r = mob_db.get_radius(sid, rarity)
    return r + 1.5


def find_best_target(player_x, player_y, can_kill_hp=500, max_dist=15000, force_sid=None, sticky_sid=None):
    """综合评分找最佳目标 (mob_db决策 + AI研究报告规则):
    秒杀优先(能秒的贴脸追) > 特殊稀有怪5倍 > 掉落价值 > 距离近
    危险怪/打不动的/不打清单(NO_FIGHT)自动跳过
    海星半血会逃 -> 一旦发现立即秒
    v1.21.2: force_sid=Super雷达猎杀目标(公告给怪名时只追它, 哪怕打不动也冲过去蹭)
    v1.25.2: sticky_sid=当前粘滞目标(AI研究§8.1-2 仇恨随时间增长 -> 单目标速杀防拉扯),
      同目标 +8000 分粘滞, 除非出现评分高一大截的新目标(如Super/海星半血/更高稀有度)才换"""
    mobs, _ = get_nearby_mobs(max_dist=max_dist)
    best = None
    best_score = -999
    for m in mobs:
        dist = math.hypot(m['x'] - player_x, m['y'] - player_y)
        if dist > max_dist:
            continue
        sid, hp = m.get('sid'), m.get('hp', 0)
        # Super雷达: 只追公告的怪
        if force_sid and sid != force_sid:
            continue
        # AI规则: 不打卵/苍蝇/沙尘暴
        if sid in NO_FIGHT_SIDS:
            continue
        action, score, rarity, _ = mob_db.assess_mob(sid, hp, can_kill_hp, dist)
        if action in ('danger', 'ignore'):
            continue
        # Super雷达猎杀: 目标怪权重拉满(抢Super)
        if force_sid and sid == force_sid:
            score += 500000.0
        # 海星半血逃跑 -> 权重拉满必须秒
        if sid == 'starfish':
            hi = mob_db.hp_range(sid, rarity)
            max_hp = hi[1] if hi else hp
            if hp < max_hp * 0.5:
                score += 100000.0
        # v1.25.2 目标粘滞: 正在打的目标继续打(不频繁换目标拉扯引怪)
        if sticky_sid and sid == sticky_sid:
            score += 8000.0
        # v1.23.4: 官方bot评分公式(florr_clone bot_ai.cpp) - 稀有度胃口-距离
        # 单位都是"值得走这么远": Rare 460/Legendary 920/Mythic 1150/Super 6000
        score += mob_db.tier_appetite(rarity) - dist
        if score > best_score:
            best_score = score
            m['score'] = score
            best = m
    return best


def wave_end_count(max_dist=2500):
    """波末检测: 同屏怪物数量<=4只时全体怪会冲玩家(AI研究报告)
    返回同屏怪数量(用于battle_loop决定是否停手接怪)"""
    mobs, _ = get_nearby_mobs(max_dist=max_dist)
    return len(mobs)


if __name__ == '__main__':
    print("测试bridge v3数据...")
    player = get_player()
    if player:
        print(f"玩家: ({player['x']}, {player['y']})")
    mobs, _ = get_nearby_mobs()
    print(f"附近怪: {len(mobs)}只")
    for m in sorted(mobs, key=lambda m: math.hypot(m['x'] - player['x'], m['y'] - player['y']))[:15]:
        d0 = math.hypot(m['x'] - player['x'], m['y'] - player['y'])
        print(f"  {m['cn']:8s}({m['sid']}) {m['rarity']:8s} hp={m['hp']:6d} r={m['radius']:.0f} 距离{int(d0):5d}")
    bt = find_best_target(player['x'], player['y'], can_kill_hp=500)
    if bt:
        print(f"最佳目标: {bt['cn']}({bt['sid']}) {bt['rarity']} hp={bt['hp']} 评分{bt.get('score',0):.0f}")
