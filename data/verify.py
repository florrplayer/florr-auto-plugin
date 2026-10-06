import json,io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
mobs=[json.loads(l) for l in open("all_mobs_full.json",encoding="utf-8") if l.strip()]
md=json.load(open("wasm_map_data.json",encoding="utf-8"))
weighted=set()
for m in md["maps"].values():
    for s in m.get("mobs",{}): weighted.add(s)
all_sids=set(m["sid"] for m in mobs)
print("总数:",len(all_sids)," 权重怪:",len(weighted)," 未分组:",len(all_sids-weighted))
print("权重怪不在73里:",weighted-all_sids)
