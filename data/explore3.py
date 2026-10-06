import json,io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
# petals first record
with open("all_petals_full.json",encoding="utf-8") as f:
    lines=[l for l in f if l.strip()]
print("petal lines:",len(lines))
o=json.loads(lines[0]); print("PETAL keys:",list(o.keys())); print(json.dumps(o,ensure_ascii=False)[:800])
print()
with open("mob_stats_full.json",encoding="utf-8") as f: t=f.read()
print("=== mob_stats_full head ==="); print(t[:1000])
print()
with open("wasm_mob_list.json",encoding="utf-8") as f: t=f.read()
print("=== wasm_mob_list ==="); print(t[:1500])
