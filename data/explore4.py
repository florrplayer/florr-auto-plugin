import json,io,sys,re
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
# gather all leaf keys
keys=set()
def walk(o):
    if isinstance(o,dict):
        for k,v in o.items(): keys.add(k); walk(v)
    elif isinstance(o,list):
        for v in o: walk(v)
for p in ["all_mobs_full.json","mob_stats_full.json","mob_threat.json","wasm_map_data.json","mob_hp.json","all_petals_full.json","local_storage.json"]:
    try:
        with open(p,encoding="utf-8") as f:
            txt=f.read()
        # NDJSON
        if p=="all_mobs_full.json" or p=="all_petals_full.json":
            for l in txt.splitlines():
                if l.strip(): walk(json.loads(l))
        else:
            walk(json.loads(txt))
    except Exception as e:
        print(p,"ERR",e)
ai=[k for k in keys if re.search(r"speed|range|aggro|attack|move|sight|chase|follow|accel|radius|velocity|ai",k,re.I)]
print("ALL KEYS:",sorted(keys))
print()
print("AI-like keys:",ai)
# dropchance third segment distribution
dc=json.load(open("florr_dropchance.json",encoding="utf-8"))
segs={}
for k in dc:
    a,b,c=k.split("|"); segs[c]=segs.get(c,0)+1
print("dropchance third-seg counts:",segs)
print("total keys:",len(dc))
