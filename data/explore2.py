import json,io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
for p in ["mob_threat.json","wasm_map_data.json","florr_dropchance.json","mob_spawn_data.json","maps_list.json"]:
    print("="*30,p,"="*30)
    with open(p,encoding="utf-8") as f:
        t=f.read()
    print(t[:1200])
    print()
