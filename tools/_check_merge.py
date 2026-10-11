# -*- coding: utf-8 -*-
import json
from collections import Counter
gd = json.load(open(r"C:\Users\intel\Downloads\florr-auto-pathing-main\data\game_data.json", encoding="utf-8"))
mobs = gd["mobs"]
print("=== 别名合并检查 ===")
for a, b in [("shiny_ladybug","ladybug_shiny"), ("cube","square"),
             ("evil_centipede","centipede_evil"), ("beetle_normal","beetle")]:
    print(f"  {a} 存在: {a in mobs} | {b} 存在: {b in mobs} (应只保留 {b})")
print()
print("=== 来源分布 ===")
c = Counter(m.get("source","?") for m in mobs.values())
print(" ", dict(c))
print()
n_beh = sum(1 for m in mobs.values() if m.get("passive") or m.get("aggro_trigger"))
n_hp = sum(1 for m in mobs.values() if m.get("hp") or m.get("max_hp"))
print(f"带行为数据: {n_beh} 个 | 带血量: {n_hp} 个 | 总数: {len(mobs)}")
print()
print("=== 重要怪抽查 ===")
for k in ["ladybug_shiny","square","centipede_evil","scorpion","crab","rock","cactus"]:
    m = mobs.get(k)
    if m:
        print(f"  {k}: hp={m.get('hp')} max_hp={m.get('max_hp')} aggro={m.get('aggro_range')} src={m.get('source')}")
