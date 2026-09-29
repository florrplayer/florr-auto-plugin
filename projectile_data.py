# -*- coding: utf-8 -*-
"""从wasm反汇编提取的投射物数据 - 插件用来躲避子弹/导弹"""

# 投射物类型: 速度 + 半径
# 速度越快越难躲,半径越大越容易撞
PROJECTILE_TYPES = {
    # 高速(>30) - 黄蜂导弹等
    'wasp_missile': {'speed': 35, 'radius': 5, 'danger': 'high'},
    'hornet_needle': {'speed': 35, 'radius': 1.4, 'danger': 'high'},
    # 中速(15-25) - 普通子弹
    'bullet_normal': {'speed': 20, 'radius': 1.4, 'danger': 'medium'},
    'bullet_fast': {'speed': 30, 'radius': 1.4, 'danger': 'high'},
    # 慢速(<15) - 花瓣投射物/蝎子针
    'scorpion_sting': {'speed': 10, 'radius': 3, 'danger': 'low'},
    'petal_basic': {'speed': 10, 'radius': 5, 'danger': 'none'},
    'bullet_slow': {'speed': 6, 'radius': 1.4, 'danger': 'low'},
    'bullet_very_slow': {'speed': 4, 'radius': 4, 'danger': 'low'},
    # 特殊
    'spike': {'speed': 5, 'radius': 5, 'danger': 'medium'},
    'eel_electric': {'speed': 20, 'radius': 5, 'danger': 'high'},
}

# 躲避距离建议(地图像素)
# 高速弹保持更远距离
def get_dodge_distance(proj_type):
    p = PROJECTILE_TYPES.get(proj_type, {'speed': 10, 'radius': 3})
    # 速度越快,需要提前躲的距离越远
    return p['speed'] * 1.5 + p['radius']


def should_dodge(proj_type):
    """这个投射物值得躲吗"""
    p = PROJECTILE_TYPES.get(proj_type, {'danger': 'medium'})
    return p['danger'] in ('high', 'medium')


if __name__ == '__main__':
    print("=== 投射物躲避数据 ===")
    for name, d in PROJECTILE_TYPES.items():
        dodge = get_dodge_distance(name)
        print(f"  {name:20s} 速度={d['speed']:2d} 半径={d['radius']:.1f} 躲避距离={dodge:.0f}px 危险={d['danger']}")
