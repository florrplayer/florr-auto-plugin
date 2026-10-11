# -*- coding: utf-8 -*-
"""一次性合并脚本: 把 stolen/ 里分散的数据合成 data/game_data.json
运行: py -3.12 tools/build_game_data.py
输出: data/game_data.json (VSCode AI 读这一个文件就够)
"""
import csv, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOLEN = os.path.join(ROOT, "stolen")
OUT = os.path.join(ROOT, "data", "game_data.json")

def norm(name):
    """规范化怪名用于匹配: Ant Egg -> ant_egg"""
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')

# 别名映射: 不同数据源对同一怪的命名不同 -> 统一到游戏内习惯名
ALIAS = {
    'shiny_ladybug': 'ladybug_shiny',      # flowrix vs 行为表
    'beetle_normal': 'beetle',
    'fire_ant_hole': 'fire_ant_burrow',
    'evil_centipede': 'centipede_evil',
    'desert_centipede': 'centipede_desert',
    'centipede_green': 'centipede',        # 行为表绿蜈蚣 = 普通蜈蚣
    'cube': 'square',                       # flowrix 方块 = 游戏内 square
}
def canon(k):
    """应用别名 -> 统一 key"""
    return ALIAS.get(k, k)

# ---------- 1. flowrix mobs ----------
with open(os.path.join(STOLEN, "clone_refs", "flowrix_mobs.json"), encoding="utf-8") as f:
    fx_mobs_raw = json.load(f)
fx_mobs = {}
for key, m in fx_mobs_raw.items():
    fx_mobs[canon(norm(m.get("name", key)))] = {
        "name": m.get("name", key),
        "hp": m.get("health"),
        "damage": m.get("damage"),
        "speed": m.get("speed"),
        "size": m.get("size"),
        "ai_type": m.get("ai_type"),       # passive / aggressive
        "aggro_range": m.get("range"),
        "color_hex": m.get("color"),
        "cooldown_ms": m.get("cooldown"),
    }

# ---------- 2. mob_datasheet.csv (行为表) ----------
behaviors = {}
with open(os.path.join(STOLEN, "misc_data", "mob_datasheet.csv"), encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row.get("Mob", "").strip()
        if not name:
            continue
        behaviors[canon(norm(name))] = {
            "name": name,
            "rarity": row.get("Rarity", ""),
            "region": row.get("Region", ""),
            "max_hp": row.get("Max Health", ""),
            "body_damage": row.get("Body Damage", ""),
            "passive": row.get("Passive Behavior", ""),
            "aggro_trigger": row.get("Aggressive Trigger", ""),
            "aggro_behavior": row.get("Aggressive Behavior", ""),
            "defensive_trigger": row.get("Defensive Trigger", ""),
            "defensive_behavior": row.get("Defensive Behavior", ""),
            "ultra_behavior": row.get("Ultra Behavior", ""),
            "special": row.get("Special", ""),
            "drops": row.get("Petal Drops", ""),
        }

# ---------- 3. 合并 mobs ----------
all_keys = set(fx_mobs) | set(behaviors)
mobs = {}
for k in all_keys:
    m = {}
    src = []
    if k in fx_mobs:
        m.update(fx_mobs[k])
        src.append("flowrix")
    if k in behaviors:
        b = behaviors[k]
        for bk, bv in b.items():
            if bv and bk not in m:
                m[bk] = bv
            elif bv and bk == "name":
                m["name"] = bv
        src.append("datasheet")
    m["source"] = "+".join(src)
    mobs[k] = m

# ---------- 4. petals (flowrix) ----------
with open(os.path.join(STOLEN, "clone_refs", "flowrix_petals.json"), encoding="utf-8") as f:
    fx_pet_raw = json.load(f)
petals = {}
for key, p in fx_pet_raw.items():
    petals[norm(p.get("name", key))] = {
        "name": p.get("name", key),
        "damage": p.get("damage"),
        "hp": p.get("health"),
        "size": p.get("size"),
        "cooldown_ms": p.get("cooldown"),
        "color_hex": p.get("color"),
        "count": p.get("count"),
        "knockback": p.get("knockback"),
    }

# ---------- 5. AI 规则常量 (从 gardn Ai.cc 硬编码提取) ----------
ai_rules = {
    "source": "stolen/gardn_server/Process/Ai.cc",
    "detection_lose_multiplier": 1.5,   # 离 target 超过 1.5×detection_radius 就丢失目标
    "idle_retarget_ticks": 1,           # idle 每 1*TPS 随机换方向
    "idle_move_duration_ticks": 2.5,    # idleMoving 走 2.5*TPS
    "idle_accel_curve": "r-r^2",        # 加速度抛物线
    "homing_radius": 300,               # 离 parent >300px 开始归巢
    "homing_dock_radius": 100,          # <100px 归巢完成
    "player_accel_ref": "PLAYER_ACCELERATION",
}

# ---------- 6. 伤害公式 (从 florrust DATA_TABLES.md) ----------
damage_formula = {
    "source": "stolen/clone_refs/florrust/DATA_TABLES.md",
    "final_damage": "base_damage * damage_factor * crit * burn * entity_type * high_hp",
    "effective_defense": "defense * defense_factor",
    "effective_armor": "(armor * armor_factor) - armor_debuffs",
}

# ---------- 7. 合成表 (crafting_table.csv) ----------
crafting = {"source": "stolen/misc_data/crafting_table.csv", "note": "5合1, 成功率 64/32/16/8/4/2/1/0.1% 等比"}

# ---------- 8. 地图 ----------
maps = {
    "tiled_dir": "stolen/tiled_maps/",
    "files": ["garden.tmj", "desert.tmj", "ocean.tmj", "jungle.tmj", "ant_hell.tmj", "sewers.tmj", "hel.tmj"],
    "shortcut_ref": "stolen/ai_refs/auto_farm/map_routes.py",
}

# ---------- 9. 识别素材 ----------
assets = {
    "petal_images_dir": "stolen/petal_images/",
    "rarity_dirs": ["common", "unusual", "rare", "epic", "legendary", "mythic", "ultra", "super", "unique"],
    "yolo_models": ["stolen/models/afk-det.pt", "stolen/models/afk-seg.pt"],
    "human_cursor_ref": "stolen/ai_refs/helper/HumanCursor.py",
}

# ---------- 输出 ----------
out = {
    "version": "1.0",
    "generated_by": "tools/build_game_data.py",
    "note": "VSCode AI 读这一个文件即可改插件; 详细源码见 stolen/ 各文件",
    "mobs": mobs,
    "petals": petals,
    "ai_rules": ai_rules,
    "damage_formula": damage_formula,
    "crafting": crafting,
    "maps": maps,
    "assets": assets,
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print(f"[+] 合并完成: {OUT}")
print(f"    mobs: {len(mobs)} 条 (flowrix {len(fx_mobs)} + 行为表 {len(behaviors)})")
print(f"    petals: {len(petals)} 条")
print(f"    文件大小: {os.path.getsize(OUT)/1024:.1f} KB")
