# -*- coding: utf-8 -*-
"""drop_rate.h 真源解析器 - 模拟执行 FlorrBt 掉率注册表, 输出结构化 JSON
用法: py -3.12 drop_rate_parser.py
输出: data/florr_dropchance_v2.json  {mob_sid: {mob_rarity: [{petal, rarity, rate}]}}
"""
import re, json, os

SHARED = r"C:\Users\intel\Downloads\florr-auto-pathing-main\reference-florr-tools\FlorrBt\src\Shared"
OUT = r"C:\Users\intel\Downloads\florr-auto-pathing-main\data\florr_dropchance_v2.json"

def read(p):
    with open(os.path.join(SHARED, p), encoding='utf-8', errors='ignore') as f:
        return f.read()

# 1. 枚举名
mob_names = re.findall(r'"(None|Beetle|Gambler|NormalLadybug|MechaFlower|NormalFlower|PlayerFlower|SoldierAnt|SoldierFireAnt|SoldierTermite|SummonedBeetle|SummonedSoldierAnt|BandageBeetle|Bee|Hornet|BumbleBee|Rock|BabyAnt|WorkerAnt|QueenAnt|AntHole|Spider|Sandstorm|Dummy|Dandelion|AntEgg|FireAntEgg|TermiteEgg|QueenAntEgg|QueenFireAntEgg|BabyFireAnt|WorkerFireAnt|FireQueenAnt|BabyTermite|WorkerTermite|TermiteOvermind|LeafPiece|LeafcutterSoldier|Titan)"', read('mob_type.h'))
petal_names = re.findall(r'"(None|Air|AntEgg|Antennae|Basic|BeetleEgg|Bone|Bubble|Carrot|Coin|Compass|Cogwheel|Disc|Dust|GoldenLeaf|Iris|Lentil|Moon|Nullification|Pincer|Relic|Rose|YinYang|Missile|BloodSacrifice|Corruption|Bandage|Heavy|Faster|Yggdrasil|Dahlia|Wing|Triangle|Sawblade|Fragment|Mimic|Glass|Stinger|BrokenEgg|Light|Leaf|Rock|Web|Cactus|Pollen|Corn|Rice|Basil|Soil|Honey|Wax|ThirdEye|Dandelion|Orange|Shovel|Yucca|WhiteFungus|BlackFungus|Broccoli|Douli|Trapper|Amulet|Plank|Tomato)"', read('petal_type.h'))
rar_names = re.findall(r'"(Null|Common|Unusual|Rare|Epic|Legendary|Mythic|Ultra|Super|Eternal|Unique|Primordial|Exotic)"', read('rarity.h'))
RAR = {n: i for i, n in enumerate(rar_names)}
print(f"枚举: mob={len(mob_names)} petal={len(petal_names)} rarity={len(rar_names)}")

# 2. 提取所有 inline 函数体
src = read('drop_rate.h')
funcs = {}  # name -> body
for m in re.finditer(r'inline void (\w+)\(([^)]*)\)\s*\n?\{', src):
    name, params = m.group(1), m.group(2)
    # 找配对花括号
    i = src.index('{', m.end() - 1)
    depth = 0
    j = i
    while j < len(src):
        if src[j] == '{': depth += 1
        elif src[j] == '}':
            depth -= 1
            if depth == 0: break
        j += 1
    funcs[name] = src[i + 1:j]

# 3. 迷你执行器
table = {}  # (mob, mob_rarity) -> [(petal, drop_rarity, rate)]
ORDER = ['Common','Unusual','Rare','Epic','Legendary','Mythic','Ultra','Super']

def add(mob, mrar, petal, drar, rate):
    rate = max(0.0, min(1.0, float(rate)))
    key = (mob, mrar)
    lst = table.setdefault(key, [])
    lst.append((petal, drar, rate))
    lst.sort(key=lambda x: (x[0], -RAR.get(x[1], 0)))
    table[key] = lst

def parse_specs(body):
    """解析函数体内嵌的 {ERarity::X, ERarity::Y, 0.xxx} 列表"""
    specs = []
    for m in re.finditer(r'\{ERarity::(\w+),\s*ERarity::(\w+),\s*([\d.]+)\}', body):
        specs.append((m.group(1), m.group(2), m.group(3)))
    return specs

def register_table(mob, petal, specs):
    for mrar, drar, rate in specs:
        add(mob, mrar, petal, drar, rate)

def exec_call(name, args, depth=0):
    """展开执行一个注册函数调用"""
    if name == 'RegisterDropRateTable':
        # 参数: (EMobType mob, EPetalType drop, {specs})
        mob, petal = args[0], args[1]
        spec_str = re.search(r'\{.*\}', args[2], re.S)
        if spec_str:
            register_table(mob, petal, parse_specs(spec_str.group(0)))
        return
    if name == 'RegisterDropRate':
        # (mob, mob_rarity, drop, drop_rarity, rate)
        if len(args) >= 5:
            add(args[0], args[1], args[2], args[3], args[4])
        return
    if name == 'RegisterLentilDropTable' or name.startswith('RegisterWiki'):
        body = funcs.get(name, '')
        # 函数体里是 RegisterDropRateTable(...) 调用, 参数可能是形参(如 mob_type, drop_type)
        for m in re.finditer(r'RegisterDropRateTable\(\s*(\w+)\s*,\s*(\w+)\s*,\s*\{', body):
            mob_arg, petal_arg = m.group(1), m.group(2)
            if mob_arg in ('mob_type',) or petal_arg in ('drop_type',):
                # 形参绑定实参
                if len(args) >= 1 and mob_arg == 'mob_type': mob_arg = args[0]
                if len(args) >= 2 and petal_arg == 'drop_type': petal_arg = args[1]
            if mob_arg in ('mob_type',) or petal_arg in ('drop_type',):
                continue
            # 找 specs
            brace = body.index('{', m.end() - 1)
            depth_b = 0; j = brace
            while j < len(body):
                if body[j] == '{': depth_b += 1
                elif body[j] == '}':
                    depth_b -= 1
                    if depth_b == 0: break
                j += 1
            register_table(mob_arg, petal_arg, parse_specs(body[brace:j + 1]))
        # 也可能调用其他 RegisterWiki 函数
        for m in re.finditer(r'Register(\w+DropTable|Wiki\w+)\(([^)]*)\)', body):
            sub = m.group(1); subargs = [a.strip() for a in m.group(2).split(',') if a.strip()]
            if sub in funcs or sub == 'RegisterDropRateTable' or sub == 'RegisterDropRate':
                if sub not in ('RegisterDropRateTable', 'RegisterDropRate'):
                    exec_call(sub, subargs, depth + 1)
        return
    if name == 'CopyDropRateTable':
        # (src_mob, src_petal, dst_mob, dst_petal)
        if len(args) >= 4:
            copied = [(k[1], v) for k, v in table.items() if k[0] == args[0]]
            for mrar, lst in copied:
                for petal, drar, rate in lst:
                    if petal == args[1]:
                        add(args[2], mrar, args[3], drar, rate)
        return
    if name == 'RemoveDropRatesForMob':
        if len(args) >= 1:
            preserved = set(args[1:])
            for key in list(table):
                if key[0] == args[0]:
                    table[key] = [(p, r, rt) for p, r, rt in table[key] if p in preserved]
                    if not table[key]: del table[key]
        return

# 4. 顶层 RegisterDropRates 函数体 -> 依次执行
top = funcs.get('RegisterDropRates', '')
calls = re.findall(r'(Register\w+|CopyDropRateTable|RemoveDropRatesForMob)\(([^;]*?)\)\s*;', top, re.S)
for name, argstr in calls:
    args = [a.strip() for a in argstr.split(',') if a.strip()]
    args = [a.replace('ERarity::', '').replace('EMobType::', '').replace('EPetalType::', '').replace('{', '').replace('}', '').strip() for a in args]
    exec_call(name, args)

print(f"注册表: {len(table)} 条 (mob,rarity) 键")
# 5. 名字 -> sid 映射 (私服名 -> 插件 mob_db sid)
M = {'Beetle':'beetle','Gambler':'gambler','NormalLadybug':'ladybug','MechaFlower':'mecha_flower',
     'NormalFlower':'flower','SoldierAnt':'ant_soldier','SoldierFireAnt':'fire_ant_soldier',
     'SoldierTermite':'termite_soldier','SummonedBeetle':'summoned_beetle','SummonedSoldierAnt':'summoned_ant_soldier',
     'BandageBeetle':'bandage_beetle','Bee':'bee','Hornet':'hornet','BumbleBee':'bumble_bee','Rock':'rock',
     'BabyAnt':'ant_baby','WorkerAnt':'ant_worker','QueenAnt':'ant_queen','AntHole':'ant_hole','Spider':'spider',
     'Sandstorm':'sandstorm','Dandelion':'dandelion','AntEgg':'ant_egg','FireAntEgg':'fire_ant_egg',
     'TermiteEgg':'termite_egg','QueenAntEgg':'queen_ant_egg','QueenFireAntEgg':'queen_fire_ant_egg',
     'BabyFireAnt':'fire_ant_baby','WorkerFireAnt':'fire_ant_worker','FireQueenAnt':'fire_ant_queen',
     'BabyTermite':'termite_baby','WorkerTermite':'termite_worker','TermiteOvermind':'termite_overmind',
     'LeafPiece':'leaf_piece','LeafcutterSoldier':'leafcutter_soldier','Titan':'titan'}
P = {'Air':'air','AntEgg':'ant_egg','Antennae':'antennae','Basic':'basic','BeetleEgg':'beetle_egg',
     'Bone':'bone','Bubble':'bubble','Carrot':'carrot','Coin':'coin','Compass':'compass','Cogwheel':'cogwheel',
     'Disc':'disc','Dust':'dust','GoldenLeaf':'golden_leaf','Iris':'iris','Lentil':'lentil','Moon':'moon',
     'Nullification':'nullification','Pincer':'pincer','Relic':'relic','Rose':'rose','YinYang':'yin_yang',
     'Missile':'missile','BloodSacrifice':'blood_sacrifice','Corruption':'corruption','Bandage':'bandage',
     'Heavy':'heavy','Faster':'faster','Yggdrasil':'yggdrasil','Dahlia':'dahlia','Wing':'wing','Triangle':'triangle',
     'Sawblade':'sawblade','Fragment':'fragment','Mimic':'mimic','Glass':'glass','Stinger':'stinger',
     'BrokenEgg':'broken_egg','Light':'light','Leaf':'leaf','Web':'web','Cactus':'cactus','Pollen':'pollen',
     'Corn':'corn','Rice':'rice','Basil':'basil','Soil':'soil','Honey':'honey','Wax':'wax','ThirdEye':'third_eye',
     'Orange':'orange','Shovel':'shovel','Yucca':'yucca','WhiteFungus':'white_fungus','BlackFungus':'black_fungus',
     'Broccoli':'broccoli','Douli':'douli','Trapper':'trapper','Amulet':'amulet','Plank':'plank','Tomato':'tomato',
     'Rock':'rock','Dandelion':'dandelion'}

out = {}
unmapped_m = set(); unmapped_p = set()
for (mob, mrar), lst in table.items():
    sid = M.get(mob)
    if not sid: unmapped_m.add(mob); continue
    if sid not in out: out[sid] = {}
    for petal, drar, rate in lst:
        psid = P.get(petal)
        if not psid: unmapped_p.add(petal); continue
        out[sid].setdefault(mrar, []).append({'petal': psid, 'rarity': drar, 'rate': rate})
if unmapped_m: print('未映射怪:', unmapped_m)
if unmapped_p: print('未映射花瓣:', unmapped_p)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"输出 {OUT}: {len(out)} 种怪")
for sid in sorted(out):
    rars = list(out[sid].keys())
    print(f"  {sid:24s} 档位={rars}")
