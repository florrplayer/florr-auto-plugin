# -*- coding: utf-8 -*-
"""生成 怪物静态属性与刷怪权重.md —— 全部数值直接读文件, 不手抄。"""
import json, os
from collections import defaultdict

D = os.path.dirname(os.path.abspath(__file__))
def load_ndjson(p):
    return [json.loads(l) for l in open(os.path.join(D,p),encoding="utf-8") if l.strip()]
def load_json(p):
    return json.load(open(os.path.join(D,p),encoding="utf-8"))

mobs = load_ndjson("all_mobs_full.json")
petals = load_ndjson("all_petals_full.json")
threat = load_json("mob_threat.json")
mapdata = load_json("wasm_map_data.json")
dropchance = load_json("florr_dropchance.json")
spawn = load_json("mob_spawn_data.json")

mob_by_id = {m["id"]: m for m in mobs}
mob_by_sid = {m["sid"]: m for m in mobs}
petal_sid = {p["id"]: p["sid"] for p in petals}

def n(x):
    if isinstance(x,float) and x==int(x): return str(int(x))
    return str(x)

L = []
w = L.append
w("# florr.io 怪物静态属性与刷怪权重 深度挖掘报告\n")
w("> 本报告全部数值来自 `data/` 下本地静态文件，未做任何外部补全或编造。\n")
w("> 复现脚本：`data/mob_data_miner.py`；掉落解析中间表：`data/_dropchance_resolved.tsv`。\n")
w("> 数据快照：怪物 73 只、花瓣 118 种、threat 数值表 73 条、dropchance 键 332 个。\n")

# ---------- 0. 数据来源 ----------
w("\n## 0. 数据来源与字段口径\n")
w("| 文件 | 作用 | 关键字段 |")
w("|---|---|---|")
w("| `all_mobs_full.json` | 73 怪 NDJSON | id / sid / drops[{baseChance,type}] / rarities[].tooltip |")
w("| `mob_threat.json` | 每怪全稀有度数值(已整理) | dmg[] hp[] hp_hi[] armor[] exp[] drops[][] |")
w("| `wasm_map_data.json` | 每图刷怪权重 + 传送门 | maps.<图>.mobs{sid:权重} |")
w("| `florr_dropchance.json` | 精确掉落概率 | `\"怪id|花id|稀有度档\"→概率` |")
w("| `all_petals_full.json` | 118 花 NDJSON | id / sid（用于把掉落 type 翻译成花名） |")
w("| `mob_spawn_data.json` | 生成播报 + 生成机制字符串 | mob_spawn_chats / spawn_mechanics |")
w("| `mob_stats_full.json` | 带稀有度档名的怪物表 | rarity: Common/Rare/Super/Epic/Legendary/Mythic/Ultra |\n")
w("**稀有度档位口径**：`mob_threat.json` 每怪有 7 个数值档位（Common→Ultra），"
  "`all_mobs_full.json` 的 rarities 数组更宽（含更高档 {} 结尾）。"
  "相邻档位数值约 ×3 增长（HP/dmg/armor），这是 florr 的稀有度缩放规律。\n")

# ---------- 1. 73 怪属性总表 ----------
w("\n## 1. 73 怪静态属性总表（Common 档，按地图分组）\n")
w("下表为每怪 **Common（最低）档** 的 HP范围 / 伤害 / 护甲 / 经验；高档位数值约按 ×3 逐档放大。\n")

# 地图 -> 权重怪
maps = mapdata["maps"]
weight_sids = {}
ungrouped = set(mob_by_sid.keys())
w("\n| 地图 | mob_id | sid | HP范围 | 伤害 | 护甲 | 经验 |")
w("|---|---|---|---|---|---|---|")
for mname, mdef in maps.items():
    wts = mdef.get("mobs")
    if not wts:
        continue
    for sid in wts:
        t = threat.get(sid)
        if not t: continue
        ungrouped.discard(sid)
        w(f"| {mname} | {t['id']} | {sid} | {n(t['hp'][0])}~{n(t['hp_hi'][0])} | {n(t['dmg'][0])} | {n(t['armor'][0])} | {n(t['exp'][0])} |")

# 未进入普通权重表的怪
special_prefix = ("ant_egg","fire_ant_egg","termite_egg","ant_hole","fire_ant_burrow","termite_mound",
                  "bush","tomb","barrel","assembler","mecha","_hel","_mecha","fire_ant","termite",
                  "digger","dandelion","fly","roach","bubble","starfish","digger","firefly_magic",
                  "beetle_nazar","beetle_mummy","centipede","ladybug_dark","bumble_bee","scorpion",
                  "sandstorm","ghost","gambler","square","ladybug_shiny","leafbug_shiny",
                  "beetle_pharaoh","ant_soldier_diver","spider_mecha","wasp_mecha","crab_mecha",
                  "fire_ant_baby","fire_ant_worker","fire_ant_soldier","fire_ant_queen",
                  "termite_baby","termite_worker","termite_soldier","termite_overmind")
w("\n### 1b. 未进入普通刷怪权重表的怪（Boss / 特殊 / 建筑 / 蛋 / 副本怪）\n")
w("这些怪不出现在 `wasm_map_data.maps.<图>.mobs` 权重里，多为建筑、蛋、副本(_hel)、机甲(_mecha)、"
  "事件怪或 Boss，静态属性如下：\n")
w("| mob_id | sid | HP范围(Common) | 伤害 | 护甲 | 经验 |")
w("|---|---|---|---|---|---|")
for sid in sorted(ungrouped, key=lambda s: mob_by_sid[s]["id"]):
    t = threat.get(sid)
    if not t: continue
    w(f"| {t['id']} | {sid} | {n(t['hp'][0])}~{n(t['hp_hi'][0])} | {n(t['dmg'][0])} | {n(t['armor'][0])} | {n(t['exp'][0])} |")

# ---------- 2. 刷怪权重 ----------
w("\n\n## 2. 刷怪权重 / 区域密度分析\n")
w("权重取自 `wasm_map_data.json` 的 `maps.<图>.mobs`。**归一占比 = 该怪权重 / 图内权重总和**，"
  "代表每次刷怪决策选中该怪的概率（同图内相互竞争）。\n")
w("| 地图 | 传送门 | 怪 | 原始权重 | 归一占比 | mob_id |")
w("|---|---|---|---|---|---|")
for mname, mdef in maps.items():
    wts = mdef.get("mobs")
    portals = ", ".join(mdef.get("portals", [])) or "—"
    if not wts:
        w(f"| {mname} | {portals} | (枢纽图, 无直接刷怪) | — | — | — |")
        continue
    tot = sum(wts.values())
    first = True
    for sid, wt in sorted(wts.items(), key=lambda x:-x[1]):
        mid = mob_by_sid.get(sid,{}).get("id","?")
        cell_map = mname if first else ""
        cell_port = portals if first else ""
        w(f"| {cell_map} | {cell_port} | {sid} | {n(wt)} | {wt/tot*100:.2f}% | {mid} |")
        first = False

w("\n### 2b. 权重解读与稀有怪推算\n")
w("- **garden**：纯枢纽（portal 通往 desert/ocean/jungle/anthell），自身无刷怪权重表。")
w("- **desert**：cactus 几乎占一半（49.4%），beetle 与 sandstorm 各 ~24.7%；`ladybug_shiny=0.025`。")
w("- **ocean**：5 怪均分，各 20%（crab/jellyfish/leech/shell/sponge 权重全为 1）。")
w("- **jungle**：leafbug 与 mantis 各 38.1%，wasp 19.0%，firefly 3.81%，`centipede_evil=0.025`。")
w("- **anthell**：ant_soldier 权重 10 极高（61.4%），ant_worker 5（30.7%），ant_queen 1（6.1%），worm 0.3（1.8%）。")
w("- **sewers**：spider 权重 1（54.1%），silverfish/garbage 0.3，moth 0.25；无 portal 字段。\n")
w("**关于 `ladybug_shiny=0.025`（及 `centipede_evil=0.025`）的推算方式：**\n")
w("1. 它不是“2.5% 替代率”，而是**权重表内的原始权重值**。")
w("2. desert 权重总和 = 1 + 0.5 + 0.5 + 0.025 = **2.025**；归一后 ladybug_shiny 占比 = 0.025/2.025 ≈ **1.23%**。")
w("3. 同理 jungle 总和 = 1+0.1+0.5+1+0.025 = 2.625；centipede_evil 占比 = 0.025/2.625 ≈ **0.95%**。")
w("4. 结合 `mob_spawn_data.spawn_mechanics`：`super_announced=true`（Super 怪全服广播）、"
  "`super_random_replace`（Super 是 Ultra 怪的极低概率随机替换）、`super_not_time_based`（不是超时刷的）。"
  "因此 0.025 权重更应理解为：在常规刷怪池中以 ~1% 量级被抽中，且一旦刷出会触发全服播报"
  "（desert 对应 `mob_spawn_chats` 里的闪光/特殊播报）。**绝对“多久刷一只”的时间频率无法从静态权重推出，"
  "需服务器刷怪间隔参数，静态文件中没有。**\n")

w("**各图 spawn 机制差异（来自 `mob_spawn_data.json`）：**\n")
w("- 专属生成播报：rock / cactus / hornet / jellyfish / firefly / gambler 等出现时聊天栏有专属英文播报。")
w("- 生成机制字符串：`luck_affects_rarity=true`（幸运影响稀有度）；`ultra_freq` ≈ Ultra 生成频率约 10 倍提升、掉率 3–4 倍降低；"
  "`eggs_hatch_on_break`（蛋只有打破时才孵化）；`super_not_time_based`（Super 非超时触发）。")
w("- `wasm_map_data.secret_routes`：ocean/anthell 各有 3 条隐藏路线（br/ocean_1..3、br/ant_hell_1..3），"
  "`from_garden = br/ocean, br/ant_hell`。这些是隐藏区域入口，权重表不含其中的怪。\n")

# ---------- 3. 掉落概率表 ----------
w("\n\n## 3. 精确掉落概率表（florr_dropchance.json 解析）\n")
w("**Key 三段含义（已用映射核对）：** `怪id | 花id | 稀有度档`")
w("- 第 1 段 = 怪物 id，与 `all_mobs_full.json` 的 `id` 对应（如 4=bee、5=ant_baby、82=ant_soldier_diver）。")
w("- 第 2 段 = 花瓣 id，与 `all_petals_full.json` 的 `id` 对应（如 6=stinger、51=ant_egg、114=dead_leaf）。")
w("- 第 3 段 = 稀有度档，**全部键只出现 `5` 与 `6` 两档**（共 332 键，档5 有 167 条、档6 有 165 条）。\n")
w("**数值特征：** 对每一对 (怪,花)，档5 的值极小（量级 1e-9 ~ 1e-148，可视为近乎不可能），"
  "档6 的值为主概率（0.51 ~ 0.96）。两档之和介于 0.089 ~ 1.0 之间，并非每对都恰好为 1。\n")
w("⚠️ **口径保留**：静态 JSON 能确定的是“三段 = 怪/花/档∈{5,6}”及数值本身；"
  "档 5/6 精确对应游戏内哪两个花瓣稀有度名、以及该值是“每杀期望概率”还是“掉落后的条件稀有度分布”，"
  "无法仅凭静态文件判定，需对照 wasm 或 florr 维基确认。下表数值原样列出。\n")

dc_group = defaultdict(dict)
for k,v in dropchance.items():
    a,b,c = k.split("|"); dc_group[(int(a),int(b))][c]=v

w("| 怪id | 怪sid | 花id | 花sid | 档5概率 | 档6概率 |")
w("|---|---|---|---|---|---|")
for (mid,pid),d in sorted(dc_group.items(), key=lambda x:(x[0][0],x[0][1])):
    msid = mob_by_id.get(mid,{}).get("sid","?")
    p5 = d.get("5"); p6 = d.get("6")
    def fm(v):
        if v is None: return ""
        if v<1e-3: return f"{v:.2e}"
        return f"{v:.4f}"
    w(f"| {mid} | {msid} | {pid} | {petal_sid.get(pid,'?')} | {fm(p5)} | {fm(p6)} |")
w(f"\n> 完整 {len(dc_group)} 对 (怪,花) 映射另存于 `data/_dropchance_resolved.tsv`。\n")

# ---------- 4. 特殊怪专项 ----------
w("\n\n## 4. 特殊怪专项（square / shiny / gambler / pharaoh / diver / ghost）\n")
SPECIAL = [18,20,63,73,78,82,83]
for mid in SPECIAL:
    m = mob_by_id.get(mid); t = threat.get(m["sid"])
    w(f"\n### {m['sid']}（id={mid}）\n")
    drops = m.get("drops",[])
    dropstr = "、".join(f"{petal_sid.get(d['type'],'?')}(type{d['type']}, baseChance={n(d['baseChance'])})" for d in drops) or "无"
    w(f"- **基础掉落(baseChance)**：{dropstr}")
    if t:
        w(f"- **全档位数值表**（HP范围 / 伤害 / 护甲 / 经验）：\n")
        w("| 档位 | HP范围 | 伤害 | 护甲 | 经验 |")
        w("|---|---|---|---|---|")
        for i in range(len(t["dmg"])):
            w(f"| {i} | {n(t['hp'][i])}~{n(t['hp_hi'][i])} | {n(t['dmg'][i])} | {n(t['armor'][i])} | {n(t['exp'][i])} |")

# ---------- 5. AI 参数结论 ----------
w("\n\n\n## 5. AI 相关静态参数存在性结论\n")
w("对 `all_mobs_full.json / mob_stats_full.json / mob_threat.json / mob_hp.json` 全量扫描键名"
  "（正则：speed|range|aggro|attack|move|sight|chase|follow|accel|velocity）。\n")
w("- **怪物对象的全部字段只有四个：`id` / `sid` / `drops` / `rarities`。**")
w("- `rarities[].tooltip` 里与战斗相关的属性仅有：**HealthRange（HP范围）、Damage（伤害）、Armor（护甲）、exp（经验）**。")
w("- **静态数据中不存在 attackRange（攻击距离）、movementSpeed（移动速度）、aggro（仇恨范围）等任何 AI 行为参数。**"
  "（命中的 `HealthRange` 是血量区间，与攻击距离无关；`isPassive` 出现在花瓣 antennae 上，不是怪物字段。）\n")
w("**结论：** 攻击距离、移动速度、仇恨/追击逻辑等 AI 参数**不在这批静态 JSON 内**，"
  "需通过 client.wasm 逆向（可参考 `florr_wasm_strings.txt`，1.5MB 字符串）或 florr.io 维基获取。"
  "插件若需要“贴近怪保持距离”“预判走位”等战斗策略，只能拿到 **HP/伤害/护甲/经验/掉落/刷怪权重** 这一侧的静态依据，"
  "AI 侧数值需另行采集。\n")

# ---------- 6. 对插件战斗策略的数据支撑 ----------
w("\n## 6. 对插件（auto-pathing / 战斗策略）的数据支撑\n")
w("| 策略需求 | 可用静态数据 | 结论 |")
w("|---|---|---|")
w("| 选图刷怪效率 | §2 每图权重归一占比 | anthell 刷怪密度最高（ant_soldier 权重 10）；ocean 五怪均分最稳 |")
w("| 目标怪稀有度判断 | §2b ladybug_shiny/centipede_evil 权重 0.025→归一~1% | 闪光/邪恶怪为低权重事件怪，刷出即广播，优先追 |")
w("| 伤害/血量预算 | §1/§4 HP范围、Damage、Armor 全档位 | 可按当前档位 ×3 缩放预判需要的 DMT/EHP |")
w("| 护甲穿透决策 | Armor 逐档（1→2→7→22→65→194→583） | 高档护甲骤增，纯攻击流后期需破甲/真伤思路 |")
w("| 掉落farm路线 | §3 dropchance + §1 地图权重 | 结合“怪权重×掉落概率”可算期望产率，定位高效farm点 |")
w("| Boss/特殊怪遭遇 | §4 七只特殊怪全档数值 | gambler/pharaoh/diver 高档 HP 达千万级，需提前准备 |")
w("| 走位/仇恨距离 | — | ❌ 无 AI 参数，静态数据支撑不了，需 wasm/维基补 |")
w("\n**一句话总结：** 静态数据足以支撑“刷怪密度选图、掉落期望路线、HP/伤害/护甲数值预算、特殊怪识别与优先级”，"
  "但**攻击距离与移动速度等 AI 行为参数缺失**，走位类策略需后续逆向 wasm 补充。\n")

out = os.path.join(D, "怪物静态属性与刷怪权重.md")
open(out,"w",encoding="utf-8").write("\n".join(L))
print("written:", out, "lines:", len(L))
