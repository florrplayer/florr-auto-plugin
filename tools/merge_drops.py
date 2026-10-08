# -*- coding: utf-8 -*-
"""合并全部真源掉率 -> data/florr_dropchance_v3.json (统一格式)
源1: FlorrBt drop_rate.h (19怪 稀有度矩阵, 每档期望) - 精度最高
源2: florr_clone mob_drops.json (53怪 花瓣概率) - 补缺口
格式: {sid: {稀有度档: [{petal, rarity, rate}]}}
sid 归一化: FlorrBt EMobType 与 mob_db sid 的映射"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, 'data')

# FlorrBt EMobType -> mob_db sid (官方sid)
MOB_MAP = {
    'NormalLadybug': 'ladybug', 'ShinyLadybug': 'ladybug_shiny', 'SoldierAnt': 'ant_soldier',
    'WorkerAnt': 'ant_worker', 'BabyAnt': 'ant_baby', 'QueenAnt': 'ant_queen',
    'FireQueenAnt': 'fire_ant_queen', 'AntHole': 'ant_hole', 'FireAntHole': 'fire_ant_hole',
    'SoldierFireAnt': 'fire_ant_soldier', 'WorkerFireAnt': 'fire_ant_worker',
    'Bee': 'bee', 'BumbleBee': 'bee_bumble', 'Hornet': 'hornet', 'Wasp': 'wasp',
    'Rock': 'rock', 'Cactus': 'cactus', 'Beetle': 'beetle', 'BandageBeetle': 'beetle_pharaoh',
    'HelBeetle': 'beetle_hel', 'Centipede': 'centipede', 'DesertCentipede': 'centipede_desert',
    'EvilCentipede': 'centipede_evil', 'Spider': 'spider', 'Jellyfish': 'jellyfish',
    'Starfish': 'starfish', 'Shell': 'shell', 'Crab': 'crab', 'Leech': 'leech',
    'Dandelion': 'dandelion', 'Scorpion': 'scorpion', 'Firefly': 'firefly',
    'LeafPiece': 'leafbug', 'GoldenLeafbug': 'leafbug_shiny', 'Bush': 'bush',
    'Mantis': 'mantis', 'TermiteOvermind': 'termite_overmind', 'WorkerTermite': 'worker_termite',
    'TermiteEgg': 'termite_egg', 'QueenTermite': 'termite_queen', 'Sandstorm': 'sandstorm',
    'Roach': 'roach', 'Moth': 'moth', 'Fly': 'fly', 'Garbage': 'garbage',
    'Dust': 'dust', 'Glitch': 'glitch', 'Ghost': 'ghost', 'MechaFlower': 'mecha_flower',
}

# 1) FlorrBt full (19怪)
full = json.load(open(os.path.join(DATA, 'florbrt_drops_full.json'), encoding='utf-8'))['mobs']
# 2) clone (53怪)
clone = json.load(open(os.path.join(DATA, 'florr_clone_drops.json'), encoding='utf-8'))['mobs']

TIER_KEY = {'common': 'Common', 'unusual': 'Unusual', 'rare': 'Rare', 'epic': 'Epic',
            'legendary': 'Legendary', 'mythic': 'Mythic', 'ultra': 'Ultra', 'super': 'Super',
            'unique': 'Unique'}

v3 = {}

# --- 源1: FlorrBt ---
src1_n = 0
for mob, petals in full.items():
    sid = MOB_MAP.get(mob)
    if not sid:
        print('  跳过FlorrBt怪(无sid映射):', mob)
        continue
    # {mob_rar: [(petal, drop_rar, prob)]}
    by_tier = {}
    for petal, rows in petals.items():
        for mr, dr, prob in rows:
            by_tier.setdefault(TIER_KEY[mr], []).append({'petal': petal, 'rarity': TIER_KEY[dr], 'rate': prob})
    if by_tier:
        v3[sid] = by_tier
        src1_n += 1

# --- 源2: clone (只补 v3 没有的怪) ---
src2_n = 0
for mob, v in clone.items():
    if mob in v3:
        continue
    # clone 概率是简单概率, 按稀有度档聚合(当作该档期望)
    by_tier = {'Common': []}
    for petal, rars in v.get('drops', {}).items():
        for rar, prob in rars.items():
            tier = TIER_KEY.get(rar, 'Common')
            by_tier.setdefault(tier, []).append({'petal': petal, 'rarity': tier, 'rate': prob})
    if by_tier:
        v3[mob] = by_tier
        src2_n += 1

out = os.path.join(DATA, 'florr_dropchance_v3.json')
json.dump({'source': 'FlorrBt(19怪矩阵) + florr_clone(53怪补缺)', 'mobs': v3},
          open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)

old = json.load(open(os.path.join(DATA, 'florr_dropchance_v2.json'), encoding='utf-8'))
print('旧v2怪数:', len(old), '| 新v3怪数:', len(v3), '| FlorrBt贡献:', src1_n, '| clone贡献:', src2_n)
print('新增怪:', sorted(set(v3) - set(old)))
print('仍缺怪(对照clone全表):', sorted(set(clone) - set(v3)))
print('已存:', out)
