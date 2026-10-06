# -*- coding: utf-8 -*-
"""
mob_data_miner.py — florr.io 本地静态数据深度挖掘
输入: data/ 下各 JSON / NDJSON
输出: 控制台摘要 + 供报告引用的结构化结果
全部数值来自文件, 不编造。
"""
import json, io, sys, os, re
from collections import defaultdict, OrderedDict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
D = os.path.dirname(os.path.abspath(__file__))

def load_ndjson(p):
    out = []
    with open(os.path.join(D, p), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out

def load_json(p):
    with open(os.path.join(D, p), encoding="utf-8") as f:
        return json.load(f)

# ---------- 1. 基础映射 ----------
mobs = load_ndjson("all_mobs_full.json")
petals = load_ndjson("all_petals_full.json")
threat = load_json("mob_threat.json")
mapdata = load_json("wasm_map_data.json")
dropchance = load_json("florr_dropchance.json")
spawn = load_json("mob_spawn_data.json")

mob_by_id = {m["id"]: m for m in mobs}
mob_by_sid = {m["sid"]: m for m in mobs}
petal_by_id = {p["id"]: p for p in petals}
petal_sid = {p["id"]: p["sid"] for p in petals}

print(f"[计数] mobs={len(mobs)} petals={len(petals)} threat={len(threat)} dropchance_keys={len(dropchance)}")

# 稀有度档位名 (来自 mob_stats_full 的 rarity 字段)
stats_full = load_json("mob_stats_full.json")
rarity_names = []
for s in stats_full:
    for r in s.get("rarities", []):
        if "rarity" in r:
            rarity_names.append(r["rarity"])
# 去重保序
seen = set(); RNAMES = []
for x in rarity_names:
    if x not in seen:
        seen.add(x); RNAMES.append(x)
print("[稀有度档位]", RNAMES)

# ---------- 2. 地图 -> 怪物权重 ----------
maps = mapdata["maps"]
print("\n=== 各图刷怪权重 ===")
map_mob_weights = {}
for mname, mdef in maps.items():
    w = mdef.get("mobs", {})
    map_mob_weights[mname] = w
    portals = mdef.get("portals", [])
    print(f"[{mname}] portals={portals}")
    if w:
        tot = sum(w.values())
        for sid, wt in sorted(w.items(), key=lambda x: -x[1]):
            mid = mob_by_sid.get(sid, {}).get("id", "?")
            print(f"    {sid:20s} weight={wt:<7} 归一占比={wt/tot*100:6.2f}%  (mob_id={mid})")
    else:
        print("    (无权重表, 枢纽/特殊图)")

# ---------- 3. 每怪静态属性总表 ----------
# 以 threat 为主表 (已整理好 dmg/hp/hp_hi/armor/exp)
def fmt_num(x):
    if isinstance(x, float) and x == int(x):
        return str(int(x))
    return str(x)

print("\n=== 怪物属性(Common 档 HP范围/伤害/护甲/经验) ===")
rows = []
for sid, t in threat.items():
    i = 0  # Common 档
    hp_lo = t["hp"][0]; hp_hi = t["hp_hi"][0]
    dmg = t["dmg"][0]; arm = t["armor"][0]; exp = t["exp"][0]
    rows.append((t["id"], sid, hp_lo, hp_hi, dmg, arm, exp, len(t["dmg"])))
rows.sort()
for r in rows:
    print(f"id={r[0]:<3} {r[1]:20s} HP={r[2]}-{r[3]}  dmg={r[4]}  armor={r[5]}  exp={r[6]}  档位数={r[7]}")

# ---------- 4. 掉落概率表解析 ----------
# key = "mobId|petalId|tier", 仅出现 tier 5 / 6
dc_group = defaultdict(dict)
for k, v in dropchance.items():
    a, b, c = k.split("|")
    dc_group[(int(a), int(b))][c] = v

print("\n=== dropchance 三段含义探查 ===")
# 统计 (mob,petal) 对里 tier5+tier6 是否为 1
sums = []
for (mid, pid), d in dc_group.items():
    s = sum(d.values())
    sums.append(s)
print(f"(mob,petal)对数={len(dc_group)}  tier5+tier6 之和: min={min(sums):.6f} max={max(sums):.6f}")
# 抽几个例子
for (mid, pid), d in list(dc_group.items())[:8]:
    mname = mob_by_id.get(mid, {}).get("sid", "?")
    pname = petal_sid.get(pid, "?")
    print(f"  mob{mid}({mname}) | petal{pid}({pname}) | " +
          "  ".join(f"tier{c}={v:.3e}" for c, v in sorted(d.items())))

# ---------- 5. 特殊怪 ----------
SPECIAL = {18: "square", 20: "ladybug_shiny", 63: "gambler", 73: "leafbug_shiny",
           78: "beetle_pharaoh", 82: "ant_soldier_diver", 83: "ghost"}
print("\n=== 特殊怪专项 ===")
for sid_want in SPECIAL.values():
    m = mob_by_sid.get(sid_want)
    t = threat.get(sid_want)
    if not m:
        print(f"[{sid_want}] all_mobs_full 中无记录"); continue
    print(f"\n--- {sid_want} (id={m['id']}) ---")
    print(f"  drops(baseChance): {[(petal_sid.get(d['type']), d['baseChance']) for d in m.get('drops',[])]}")
    if t:
        print(f"  档位数={len(t['dmg'])}")
        for i in range(len(t['dmg'])):
            print(f"    档{i}: HP={t['hp'][i]}-{t['hp_hi'][i]} dmg={t['dmg'][i]} armor={t['armor'][i]} exp={t['exp'][i]}")
    else:
        print("  threat 表无 (可能为特殊/不可杀/事件怪), all_mobs rarities 档位数=", len(m.get("rarities",[])))
        for i, r in enumerate(m.get("rarities", [])):
            tt = r.get("tooltip")
            print(f"    档{i}: tooltip={tt} exp={r.get('exp')}")

# ---------- 6. AI 参数存在性 ----------
print("\n=== AI 参数字段扫描 ===")
ai_keys = set()
def walk(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if re.search(r"speed|range|aggro|attack|move|sight|chase|follow|accel|velocity", str(k), re.I):
                ai_keys.add(str(k))
            walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
for p in ["all_mobs_full.json", "mob_stats_full.json", "mob_threat.json", "mob_hp.json"]:
    walk(load_json(p) if p.endswith("threat.json") or p.endswith("hp.json") or "stats" in p else load_ndjson(p))
print("命中疑似AI字段:", ai_keys if ai_keys else "无")
print("怪物对象全部键:", sorted(set(k for m in mobs for k in m.keys())))

# 导出 dropchance 完整映射到文件, 供报告表格
with open(os.path.join(D, "_dropchance_resolved.tsv"), "w", encoding="utf-8") as f:
    f.write("mob_id\tmob_sid\tpetal_id\tpetal_sid\ttier5\ttier6\n")
    for (mid, pid), d in sorted(dc_group.items()):
        msid = mob_by_id.get(mid, {}).get('sid', '?')
        f.write(f"{mid}\t{msid}\t{pid}\t{petal_sid.get(pid,'?')}\t"
                f"{d.get('5','')}\t{d.get('6','')}\n")
print("\n[导出] _dropchance_resolved.tsv")
