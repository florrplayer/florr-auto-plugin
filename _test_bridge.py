# -*- coding: utf-8 -*-
from bridge_server import start_server, get_latest
import time
start_server(18899)
print("等待浏览器数据...")
for i in range(8):
    time.sleep(1)
    d = get_latest()
    mobs = d.get('mobs', [])
    if mobs:
        print(f"收到! 怪物数: {len(mobs)}")
        for m in mobs[:8]:
            print(f"  type={m['t']} hp={m['hp']} at ({m['x']},{m['y']})")
        break
    else:
        print(f"  {i+1}s: 无数据 keys={list(d.keys())}")
