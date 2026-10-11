# -*- coding: utf-8 -*-
"""核对 stolen/ 数据正确性: 交叉验证合并质量 + 关键数值一致性"""
import csv, json, os, re, sys

ROOT = r"C:\Users\intel\Downloads\florr-auto-pathing-main"
STOLEN = os.path.join(ROOT, "stolen")

def norm(name):
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')

print("="*60)
print("1) game_data.json 合并质量检查")
print("="*60)
gd = json.load(open(os.path.join(ROOT, "data", "game_data.json"), encoding="utf-8"))
mobs = gd["mobs"]
print(f"合并后 mobs 总数: {len(mobs)}")

# 原始两侧
fx = json.load(open(os.path.join(STOLEN, "clone_refs", "flowrix_mobs.json"), encoding="utf-8"))
fx_keys = set(norm(m.get("name", k)) for k, m in fx.items())
beh = {}
with open(os.path.join(STOLEN, "misc_data", "mob_datasheet.csv"), encoding="utf-8") as f:
    for row in csv.DictReader(f):
        n = row.get("Mob", "").strip()
        if n:
            beh[norm(n)] = row
beh_keys = set(beh)
both = fx_keys & beh_keys
only_fx = fx_keys - beh_keys
only_beh = beh_keys - fx_keys
print(f"两侧都有: {len(both)} | 只有flowrix: {len(only_fx)} | 只有行为表: {len(only_beh)}")
if only_fx:
    print("  只有flowrix:", sorted(only_fx)[:20])
if only_beh:
    print("  只有行为表:", sorted(only_beh)[:20])

# 合并错位检查: 同一怪 flowrix 数值 vs 行为表数值
print()
print("="*60)
print("2) 数值交叉检查 (flowrix hp vs 行为表 Max Health)")
print("="*60)
mismatch = 0
for k in sorted(both):
    f = fx.get([kk for kk, m in fx.items() if norm(m.get("name", kk)) == k][0], {})
    b = beh[k]
    fhp = f.get("health")
    bhp = b.get("Max Health", "").strip()
    if fhp is not None and bhp:
        try:
            if abs(float(fhp) - float(bhp)) > max(1.0, float(fhp)*0.3):
                mismatch += 1
                print(f"  [差] {k:20s} flowrix={fhp} 行为表={bhp}")
        except ValueError:
            pass
print(f"  数值差异>30% 的怪: {mismatch} 个")

print()
print("="*60)
print("3) 稀有度颜色 vs combat.py HSV 阈值")
print("="*60)
# 官方颜色 (来自 game_data.py / wasm)
MYTHIC_HEX = "#1fdbde"
ULTRA_HEX = "#ff2b75"
def hex_to_hsv(h):
    h = h.lstrip("#")
    r, g, b = int(h[0:2],16)/255, int(h[2:4],16)/255, int(h[4:6],16)/255
    mx, mn = max(r,g,b), min(r,g,b)
    d = mx-mn
    if d == 0: hh = 0
    elif mx == r: hh = 60*(((g-b)/d) % 6)
    elif mx == g: hh = 60*((b-r)/d + 2)
    else: hh = 60*((r-g)/d + 4)
    s = 0 if mx == 0 else d/mx
    v = mx
    return hh, s*255, v*255
mh, ms, mv = hex_to_hsv(MYTHIC_HEX)
uh, us, uv = hex_to_hsv(ULTRA_HEX)
print(f"Mythic #1fdbde -> H={mh:.0f} S={ms:.0f} V={mv:.0f} | combat.py 阈值 H85-100 S100-255")
print(f"Ultra  #ff2b75 -> H={uh:.0f} S={us:.0f} V={uv:.0f} | combat.py 阈值 H162-178 S100-255")
print(f"  Mythic OpenCV H = {mh/2:.0f} (需在 85-100 内) -> {'OK' if 85 <= mh/2 <= 100 else '不匹配!'}")
print(f"  Ultra  OpenCV H = {uh/2:.0f} (需在 162-178 内) -> {'OK' if 162 <= uh/2 <= 178 else '不匹配!'}")

print()
print("="*60)
print("4) 官方血量倍率 vs flowrix/florrust")
print("="*60)
official = {"common":1, "unusual":3.75, "rare":13.5, "epic":54, "legendary":324,
            "mythic":3159, "ultra":196830, "super":4374000, "unique":26244000}
print("官方: ", official)
# flowrix petals 的 health 是否按档位缩放
fp = json.load(open(os.path.join(STOLEN, "clone_refs", "flowrix_petals.json"), encoding="utf-8"))
print("flowrix petals 样例 (看是否有稀有度字段):")
k0 = list(fp.keys())[0]
print("  ", json.dumps({kk: v for kk, v in fp[k0].items() if kk != 'image'}, ensure_ascii=False)[:200])

print()
print("="*60)
print("5) gardn AI 参数 vs wasm mob_ai.py 追击范围")
print("="*60)
print("gardn Ai.cc: detection_radius (每怪不同), 丢失=1.5x, 归巢300px")
print("mob_ai.py:   default=255, aggressive=360, passive=60")
print("→ 两者是不同层面: gardn 是单怪精确值, mob_ai 是分类近似值")
print("  不算冲突, 但 mob_ai 的 default=255 如果被 gardn 单怪值覆盖会更准")

print()
print("="*60)
print("6) mob_datasheet 稀有度分布")
print("="*60)
from collections import Counter
c = Counter(b.get("Rarity", "").strip() for b in beh.values())
print("  ", dict(c))
