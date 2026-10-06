import json,io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
txt=open("mob_hp.json",encoding="utf-8").read(); print("=== mob_hp head ==="); print(txt[:600])
# find isPassive
for p in ["all_mobs_full.json","mob_stats_full.json","all_petals_full.json"]:
    t=open(p,encoding="utf-8").read()
    if "isPassive" in t:
        i=t.find("isPassive"); print("isPassive in",p,"->",t[i-120:i+80])
# petal id map sample: what is petal 6,11,2,5,3,18,77
pets={}
for l in open("all_petals_full.json",encoding="utf-8"):
    if l.strip():
        o=json.loads(l); pets[o["id"]]=o["sid"]
for i in [2,3,5,6,11,13,14,18,21,22,24,25,39,41,46,49,51,73,78,79,94,114]:
    print("petal",i,"=",pets.get(i))
