# -*- coding: utf-8 -*-
"""FlorrBt 私服怪属性真源提取: game_config.h 常量 + RegisterMobs 结构 -> JSON
用法: py -3.12 extract_florbrt_stats.py
输出: reference-florr-tools/FlorrBt/ 提取结果 stats_private_server.json (口径: 私服, 仅校准参考)
"""
import re, os, json

BT = r"C:\Users\intel\Downloads\florr-auto-pathing-main\reference-florr-tools\FlorrBt\src"
CFG = os.path.join(BT, "Shared", "game_config.h")
BEH = os.path.join(BT, "Server", "Game", "entities", "mob_behavior.cpp")
OUT = r"C:\Users\intel\Downloads\florr-auto-pathing-main\reference-florr-tools\FlorrBt\stats_private_server.json"

def read(p):
    with open(p, encoding='utf-8', errors='ignore') as f:
        return f.read()

cfg = read(CFG)
# 1. 常量表: inline float mob_xxx = value;
consts = {}
for m in re.finditer(r'inline float (mob_([a-z0-9_]+)_(max_health|armor|damage|radius|mass|max_velocity|acceleration|team|missile_speed|missile_speed_level_step|horizon))\s*=\s*([\w.()]+);', cfg):
    name, mob, field, val = m.group(1), m.group(2), m.group(3), m.group(4)
    try:
        consts.setdefault(mob, {})[field] = float(val)
    except ValueError:
        consts.setdefault(mob, {})[field] = val

# 2. RegisterMobs 里的 controller_factory -> 近战/远程分类
beh = read(BEH)
rm = re.search(r'bool RegisterMobs\(std::string& error\)\s*\{', beh)
reg_body = beh[rm.end():] if rm else beh
ctrl_map = {}
matches = list(re.finditer(r'RegisterMobPrototype<EMobType::(\w+),\s*(\w+)>\(std::move\(proto\)\);', beh))
starts = [m.start() for m in matches]
for idx, m in enumerate(matches):
    mob_name = m.group(1)
    s = starts[idx - 1] if idx > 0 else max(0, m.start() - 4000)
    seg = beh[s:m.start()]
    ctls = set(re.findall(r'make_unique<C(\w+)Controller>\(\)', seg))
    # 合并: 有远程 -> ranged; 有特殊近战 -> melee_special; 有中性 -> melee_neutral; 纯近战 -> melee
    if 'HornetRanged' in ctls or 'MechaFlowerRanged' in ctls or 'Ranged' in ctls:
        ctrl = 'ranged'
    elif 'SpecialHornet' in ctls:
        ctrl = 'ranged'  # 条件: Super 及以上才变远程
    elif 'TermiteOvermind' in ctls:
        ctrl = 'ranged_special'
    elif 'Spider' in ctls or 'QueenAnt' in ctls:
        ctrl = 'melee_special'
    elif 'NeutralMelee' in ctls:
        ctrl = 'melee_neutral'
    elif 'RandomWander' in ctls:
        ctrl = 'wander'
    elif 'RockAttackOnDamaged' in ctls:
        ctrl = 'passive_retaliate'
    elif 'Player' in ctls:
        ctrl = 'player'
    elif 'Melee' in ctls or 'BumbleBee' in ctls or 'Leafcutter' in ctls:
        ctrl = 'melee'
    elif ctls:
        ctrl = '+'.join(sorted(ctls))
    else:
        ctrl = '?'
    # PascalCase -> snake_case (BandageBeetle -> bandage_beetle)
    import re as _re
    ctrl_map[_re.sub(r'(?<!^)(?=[A-Z])', '_', mob_name).lower()] = ctrl

# 3. 组装
out = {}
for mob, fields in consts.items():
    out[mob] = fields
    out[mob]['controller'] = ctrl_map.get(mob, '?')

# 4. 缩放公式常量(官方同源参考)
scale = {}
for key in ['mob_damage_scale_base', 'mob_horizon_scale_exp', 'default_max_velocity',
            'default_acceleration', 'default_horizon', 'mob_hornet_missile_speed',
            'mob_hornet_missile_speed_level_step', 'mob_fire_ant_damage_multiplier',
            'mob_termite_health_multiplier', 'mob_summoned_rarity_linear_scale']:
    m = re.search(rf'inline float {key}\s*=\s*([\w.()]+);', cfg)
    if m:
        scale[key] = m.group(1)

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump({'mobs': out, 'scale': scale}, f, ensure_ascii=False, indent=1)
print(f"输出 {OUT}: {len(out)} 种怪 + {len(scale)} 缩放常量")
for mob in sorted(out)[:40]:
    s = out[mob]
    print(f"  {mob:22s} hp={s.get('max_health')} dmg={s.get('damage')} r={s.get('radius')} v={s.get('max_velocity')} ctrl={s.get('controller')}")
