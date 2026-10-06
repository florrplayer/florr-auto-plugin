# -*- coding: utf-8 -*-
# 解析官方 en_US i18n: mobs.txt/petals.txt/rarities.txt -> JSON 映射
# 输出: data/mob_names_en.json, data/petal_names_en.json, data/rarity_names_en.json
import json, re, os

BASE = r"C:\Users\intel\Downloads\florr-auto-pathing-main\data"

def parse_ini(path, prefix):
    out = {}
    cur = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            m = re.match(r"^" + prefix + r"/([A-Za-z0-9_]+)/(Name)$", key)
            if m:
                sid = m.group(1)
                cur = out.setdefault(sid, {})
                cur["sid"] = sid
                cur["name"] = val
                continue
            m2 = re.match(r"^" + prefix + r"/([A-Za-z0-9_]+)/(Description|Spawn)$", key)
            if m2 and cur is not None:
                sid2, field2 = m2.group(1), m2.group(2)
                if sid2 == cur.get("sid"):
                    cur[field2.lower()] = val
    return out

mobs = parse_ini(os.path.join(BASE, "florr_i18n_en_mobs.txt"), "Mobs")
petals = parse_ini(os.path.join(BASE, "florr_i18n_en_petals.txt"), "Petals")

def parse_rarities(path):
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip()
            m = re.match(r"^Rarities/([A-Za-z0-9_]+)/(Name|NameColored|Color)$", key)
            if m:
                sid, field = m.group(1), m.group(2)
                out.setdefault(sid, {})[field] = val
    return out

rarities = parse_rarities(os.path.join(BASE, "florr_i18n_en_rarities.txt"))

with open(os.path.join(BASE, "mob_names_en.json"), "w", encoding="utf-8") as f:
    json.dump(mobs, f, ensure_ascii=False, indent=1)
with open(os.path.join(BASE, "petal_names_en.json"), "w", encoding="utf-8") as f:
    json.dump(petals, f, ensure_ascii=False, indent=1)
with open(os.path.join(BASE, "rarity_names_en.json"), "w", encoding="utf-8") as f:
    json.dump(rarities, f, ensure_ascii=False, indent=1)

print("mobs:", len(mobs), "petals:", len(petals), "rarities:", len(rarities))
print("sample mob:", mobs.get("bee"))
print("sample petal:", list(petals.items())[0])
print("sample rarity:", list(rarities.items())[0])
