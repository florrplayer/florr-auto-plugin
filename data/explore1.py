import json,io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
def head_json(p,n=1):
    with open(p,encoding="utf-8") as f: return f.read()[:n]
print("=== all_mobs_full first 1500 ===")
print(head_json("all_mobs_full.json",1500))
