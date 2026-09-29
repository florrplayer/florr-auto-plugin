"""从client.wasm挖到的游戏数据"""

# 各区域怪物生成率
MAP_MOBS = {
    'garden': {'bee':1, 'ladybug':1, 'rock':1, 'ant_baby':1, 'ant_worker':1, 'ant_soldier':1, 'hornet':1, 'beetle':1, 'spider':1},
    'desert': {'cactus':1, 'beetle':0.5, 'sandstorm':0.5, 'ladybug_shiny':0.025},
    'ocean': {'crab':1, 'jellyfish':1, 'leech':1, 'shell':1, 'sponge':1, 'starfish':3, 'bubble':3},
    'jungle': {'leafbug':1, 'firefly':0.1, 'wasp':0.5, 'mantis':1, 'centipede_evil':0.025, 'bush':0.3},
    'anthell': {'ant_soldier':10, 'ant_worker':5, 'ant_queen':1, 'worm':0.3},
    'fire_anthell': {'fire_ant_soldier':10, 'fire_ant_worker':5, 'fire_ant_queen':1, 'worm':0.3},
    'sewers': {'spider':1, 'moth':0.25, 'silverfish':0.3, 'garbage':1},
}

# 地图传送门
PORTALS = {
    'garden': ['to_desert', 'to_ocean', 'to_jungle', 'to_anthell'],
    'desert': ['to_garden'],
    'ocean': ['to_garden'],
    'jungle': ['to_garden', 'to_anthell'],
    'anthell': ['to_garden', 'to_desert'],
}

# 秘密捷径(wasm里的br= bypass route)
SECRET_ROUTES = {
    'ocean': ['br_ocean_1', 'br_ocean_2', 'br_ocean_3'],
    'anthell': ['br_anthell_1', 'br_anthell_2', 'br_anthell_3'],
}

# Super/Ultra怪生成时的聊天提示(监听这些就知道大怪刷了)
SPAWN_CHAT = {
    'rock': 'Something mountain-like appears',
    'cactus': 'A tower of thorns rises',
    'hornet': 'A big yellow spot',
    'jellyfish': 'lightning strikes',
    'firefly': 'bright light in the horizon',
    'beetle_hel': 'ominous vibrations',
    'spider_hel': 'ominous vibrations',
    'centipede_hel': 'ominous vibrations',
    'wasp_hel': 'ominous vibrations',
    'gambler': 'one more game',
}

# 怪物列表(47种)
MOBS = [
    'ant_baby','ant_egg','ant_queen','ant_soldier','ant_worker',
    'fire_ant_baby','fire_ant_egg','fire_ant_queen','fire_ant_soldier','fire_ant_worker',
    'termite_baby','termite_egg','termite_overmind','termite_soldier','termite_worker',
    'beetle','beetle_mummy','beetle_hel',
    'crab','crab_mecha',
    'spider','spider_mecha','spider_hel',
    'wasp','wasp_mecha','wasp_hel',
    'jellyfish','leech','starfish',
    'ladybug','ladybug_shiny','ladybug_dark',
    'worm','rock','shell','bush','cactus','sandstorm',
    'bee','bumble_bee','hornet','mantis','firefly','leafbug',
    'centipede_evil','centipede_hel','mecha_flower','gambler','ghost',
]

# 稀有度8档
RARITIES = ['common','rare','super','epic','legendary','mythic','ultra','unique']

# Yggdrasil花瓣(复活)
YGGDRASIL_DESC = "A dried leaf from the Yggdrasil tree. Can revive fallen players. 30s cooldown."
# Mark花瓣(黑暗标记)
MARK_DESC = "Dark mark that binds to a fallen soul."

# 值得优先打的稀有怪
PRIORITY_MOBS = ['square', 'ladybug_shiny', 'centipede_evil', 'golden_leafbug', 'diver_ant']
