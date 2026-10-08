# -*- coding: utf-8 -*-
"""提取 FlorrTranslate-zh_CN 官方汉化映射 -> data/florr_i18n_zh.json"""
import re, json

src = r'C:\Users\intel\Downloads\florr-auto-pathing-main\reference-florr-tools\FlorrTranslate-zh_CN\src\FlorrTranslate-zh_CN-browser-console-version.txt'
text = open(src, encoding='utf-8').read()

# 取 const translate = { ... } 块
m = re.search(r'const translate = \{(.*?)\n\}', text, re.S)
body = m.group(1)

pairs = {}
# 匹配 'key': 'value' 形式
for k, v in re.findall(r"'((?:[^'\\]|\\.)*)'\s*:\s*'((?:[^'\\]|\\.)*)'", body):
    key = k.replace("\\'", "'")
    val = v.replace("\\'", "'")
    pairs[key] = val

out = r'C:\Users\intel\Downloads\florr-auto-pathing-main\data\florr_i18n_zh.json'
json.dump(pairs, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

print('提取 %d 条映射 -> %s' % (len(pairs), out))

# 怪名映射(生物详细介绍区)
mob_keys = ['Ant Egg','Ant Hole','Baby Ant','Baby Fire Ant','Baby Termite','Bee','Beetle','Bumble Bee',
 'Centipede','Roach','Crab','Dandelion','Desert Centipede','Digger','Evil Centipede','Fire Ant Burrow',
 'Fire Ant Egg','Fly','Hornet','Jellyfish','Ladybug','Leech','Moth','Queen Ant','Queen Fire Ant',
 'Rock','Sandstorm','Scorpion','Shell','Soldier Ant','Soldier Fire Ant','Soldier Termite','Spider',
 'Sponge','Square','Starfish','Termite Overmind','Worker Ant','Worker Fire Ant','Worker Termite','Cactus','Bubble']
print('怪名映射:')
for k in mob_keys:
    if k in pairs:
        print('  %-22s -> %s' % (k, pairs[k]))
