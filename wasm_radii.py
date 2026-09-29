# -*- coding: utf-8 -*-
"""从wasm反汇编提取的实际碰撞箱数据
func[6403-6498] = 73个怪物构造函数,每个函数的第一个f64.const就是碰撞箱半径
"""

# 按函数顺序对应73个怪物(从_Util_GetMobs的sid顺序)
# sid顺序: rock, cactus, ladybug, bee, ant_baby, ant_worker, ant_soldier, ant_queen, ant_hole, beetle...
WASM_RADII = {
    'rock': 12.0,
    'cactus': 12.0,       # 12,16 (宽高)
    'ladybug': 10.0,      # 10,5
    'bee': 5.0,           # 5,13
    'ant_baby': 10.0,     # 10,15
    'ant_worker': 12.0,   # 12,13
    'ant_soldier': 25.0,  # 25,40
    'ant_queen': 10.0,    # 10,6.28
    'ant_hole': 10.0,     # 10,6.28
    'beetle': 10.0,       # 10,5
    'hornet': 16.0,
    'centipede': 75.0,    # 长条
    'centipede_evil': 13.0,
    'centipede_desert': 12.0,
    'square': 35.0,       # 35!
    'spike': 11.0,
    'bullet': 10.0,
    'tank': 10.0,
    'tank_dark': 35.0,
    'crab': 25.0,
    'crab_hard': 20.0,     # 20,120
    'crab_king': 100.0,
    'jellyfish': 12.0,     # 12,16
    'jellyfish_gold': 15.0, # 15,7
    'eel': 22.0,
    'eel_dark': 28.57,
    'shark': 10.0,
    'whale': 7.0,
    'manta': 10.0,
    'octopus': 10.0,
    'squid': 40.0,
    'dolphin': 20.0,      # 20,24
    'turtle': 5.0,
    'seahorse': 10.0,
    'seahorse_gold': 10.0,
    'ray': 18.0,
    'ray_dark': 10.0,
    'ray_gold': 15.0,
    'ray_evil': 10.0,
    'starfish': 30.0,
    'starfish_king': 100.0,
    'urchin': 5.0,
    'urchin_dark': 10.0,
    'urchin_gold': 10.0,
    'coral': 50.0,
    'clam': 10.0,
    'clam_gold': 15.0,
    'fish': 10.0,
    'fish_gold': 10.0,
    'fish_dark': 10.0,
    'fish_evil': 10.0,
    'puffer': 50.0,
    'puffer_dark': 10.0,
    'puffer_gold': 15.0,
    'puffer_evil': 75.0,
    'narwhal': 7.0,
    'whale_dark': 50.0,
    'whale_gold': 20.0,
    'dolphin_dark': 10.0,
    'dolphin_gold': 10.0,
    'shark_dark': 25.0,
    'shark_gold': 5.0,
    'eel_gold': 5.0,
    'jellyfish_dark': 30.0,
    'jellyfish_evil': 12.0,
    'crab_dark': 10.0,
    'crab_evil': 4.0,
    'crab_gold': 200.0,   # 200,8
    'tank_gold': 5.0,
    'tank_evil': 5.0,
    'spike_dark': 10.0,
    'spike_gold': 50.0,
    'bullet_dark': 10.0,
    'bullet_gold': 150.0,  # 150,13
}

# 稀有度缩放
RARITY_SCALE = {
    'Common': 1.0, 'Rare': 1.3, 'Super': 1.5, 'Epic': 2.0,
    'Legendary': 3.0, 'Mythic': 5.0, 'Ultra': 8.0, 'Super': 10.0,
}


def get_real_radius(sid, rarity='Common'):
    """从wasm反汇编拿到的实际碰撞箱半径"""
    base = WASM_RADII.get(sid, 10.0)
    scale = RARITY_SCALE.get(rarity, 1.0)
    return base * scale


if __name__ == '__main__':
    print("=== wasm实际碰撞箱 ===")
    for sid in ['rock', 'square', 'ant_soldier', 'ant_queen', 'ant_hole', 'crab_gold']:
        print(f"  {sid:20s} Common={get_real_radius(sid):.0f}px  Mythic={get_real_radius(sid,'Mythic'):.0f}px")
