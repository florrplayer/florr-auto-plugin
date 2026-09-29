# -*- coding: utf-8 -*-
import json
petals = []
with open(r'C:\Users\intel\Downloads\florr-auto-pathing-main\data\all_petals_full.json','r',encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        try:
            petals.append(json.loads(line))
        except: pass
print(f'花瓣总数: {len(petals)}')
print()
print('=== 所有花瓣sid ===')
for p in petals:
    sid = p.get('sid','?')
    pid = p.get('id','?')
    rar = p.get('rarities',[])
    base = rar[0] if rar else {}
    tip = base.get('tooltip',[])
    rt = base.get('reloadTime','')
    print(f'  {pid:3d} {sid:25s} reload={rt:6} tip={tip}')
