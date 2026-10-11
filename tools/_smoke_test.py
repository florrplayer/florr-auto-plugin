# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import importlib
mods = ['main','memory_battle','bridge_combat','afk_solver','chat_solver','map_auto_detect',
        'mob_db','mob_ai','game_data','protocol_db','combat_strategy','flee_planner',
        'net_protocol','smart_combat','game_db']
for m in mods:
    try:
        importlib.import_module(m)
        print(f'OK  {m}')
    except Exception as e:
        print(f'FAIL {m}: {type(e).__name__}: {str(e)[:90]}')
