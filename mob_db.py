# -*- coding: utf-8 -*-
"""mob_db.py v1.18.0 - 统一游戏数据层
把偷来的全部数据(wasm反汇编/官方i18n/抓包)合成一个内存数据库:
  type_id(1-83) -> sid -> 中文名 -> 各稀有度HP/Damage/exp -> 稀有度反推
  -> 真实碰撞箱(wasm) -> 追击范围(wasm AI) -> 掉落价值(wasm) -> 决策
"""
import json, os, math

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
_cache = {}

def _load_json(name):
    if name in _cache:
        return _cache[name]
    path = os.path.join(_DATA_DIR, name)
    if not os.path.exists(path):
        _cache[name] = None
        return None
    with open(path, 'r', encoding='utf-8') as f:
        raw = f.read()
    try:
        _cache[name] = json.loads(raw)
    except Exception:
        # 多JSON对象拼接文件(all_petals.json): 逐个raw_decode
        dec = json.JSONDecoder()
        idx, out = 0, []
        while idx < len(raw):
            while idx < len(raw) and raw[idx] in ' \t\r\n':
                idx += 1
            if idx >= len(raw):
                break
            obj, end = dec.raw_decode(raw, idx)
            out.append(obj)
            idx = end
        _cache[name] = out
    return _cache[name]


# ================= type_id -> sid =================
# 静态怪type id 1-83 (从wasm _Util_GetMobs / all_mobs_full.json 确认)
TYPE_ID_TO_SID = {
    1:"rock",2:"cactus",3:"ladybug",4:"bee",5:"ant_baby",6:"ant_worker",7:"ant_soldier",
    8:"ant_queen",9:"ant_hole",10:"beetle",11:"hornet",12:"centipede",14:"centipede_evil",
    16:"centipede_desert",18:"square",19:"ladybug_dark",20:"ladybug_shiny",21:"spider",
    22:"scorpion",23:"fire_ant_soldier",24:"fire_ant_burrow",25:"sandstorm",26:"bubble",
    27:"bumble_bee",28:"shell",29:"starfish",30:"crab",31:"jellyfish",32:"digger",
    33:"sponge",34:"leech",36:"dandelion",37:"fire_ant_baby",38:"fire_ant_worker",
    39:"fire_ant_queen",40:"ant_egg",41:"fire_ant_egg",42:"fly",43:"leafbug",44:"mantis",
    45:"termite_baby",46:"termite_worker",47:"termite_soldier",48:"termite_overmind",
    49:"termite_mound",50:"termite_egg",51:"bush",52:"roach",53:"moth",54:"firefly",
    55:"beetle_hel",56:"wasp",58:"spider_hel",59:"centipede_hel",61:"wasp_hel",63:"gambler",
    65:"firefly_magic",67:"beetle_nazar",68:"worm",70:"mecha_flower",71:"wasp_mecha",
    72:"spider_mecha",73:"leafbug_shiny",74:"crab_mecha",75:"assembler",76:"barrel",
    77:"beetle_mummy",78:"beetle_pharaoh",79:"tomb",80:"silverfish",81:"garbage",
    82:"ant_soldier_diver",83:"ghost",
}
SID_TO_TYPE_ID = {v: k for k, v in TYPE_ID_TO_SID.items()}

# sid -> 中文名 (florr_mobs_official.json 生成)
MOB_CN = {
    "rock":"岩石","cactus":"仙人掌","ladybug":"瓢虫","bee":"蜜蜂","ant_baby":"幼蚁",
    "ant_worker":"工蚁","ant_soldier":"兵蚁","ant_queen":"蚁后","ant_hole":"蚁穴",
    "beetle":"甲虫","hornet":"黄蜂","centipede":"蜈蚣","centipede_evil":"邪恶蜈蚣",
    "centipede_desert":"沙漠蜈蚣","square":"正方形","ladybug_dark":"暗瓢虫",
    "ladybug_shiny":"闪亮瓢虫","spider":"蜘蛛","scorpion":"蝎子","fire_ant_soldier":"火蚁兵",
    "fire_ant_burrow":"火蚁穴","sandstorm":"沙暴","bubble":"泡泡","bumble_bee":"大黄蜂",
    "shell":"贝","starfish":"海星","crab":"蟹","jellyfish":"水母","digger":"挖掘者",
    "sponge":"海绵","leech":"水蛭","dandelion":"蒲公英","fire_ant_baby":"火蚁幼蚁",
    "fire_ant_worker":"火蚁工","fire_ant_queen":"火蚁后","ant_egg":"蚁卵","fire_ant_egg":"火蚁卵",
    "fly":"苍蝇","leafbug":"叶虫","mantis":"螳螂","termite_baby":"白蚁幼","termite_worker":"白蚁工",
    "termite_soldier":"白蚁兵","termite_overmind":"白蚁主宰","termite_mound":"白蚁丘",
    "termite_egg":"白蚁卵","bush":"灌木","roach":"蟑螂","moth":"飞蛾","firefly":"萤火虫",
    "beetle_hel":"冥界甲虫","wasp":"胡蜂","spider_hel":"冥界蜘蛛","centipede_hel":"冥界蜈蚣",
    "wasp_hel":"冥界胡蜂","gambler":"赌徒","firefly_magic":"魔法萤火虫","beetle_nazar":"纳扎尔甲虫",
    "worm":"蠕虫","mecha_flower":"机械花","wasp_mecha":"机械胡蜂","spider_mecha":"机械蜘蛛",
    "leafbug_shiny":"金叶虫","crab_mecha":"机械蟹","assembler":"组装机","barrel":"木桶",
    "beetle_mummy":"木乃伊甲虫","beetle_pharaoh":"法老甲虫","tomb":"墓穴","silverfish":"蠹虫",
    "garbage":"垃圾","ant_soldier_diver":"潜水兵蚁","ghost":"幽灵",
}

# 花瓣 sid -> 中文名 (all_petals.json)
PETAL_CN = {
    "basic":"基础","light":"轻","rose":"玫瑰","dahlia":"大丽花","yucca":"丝兰","starfish":"海星",
    "leaf":"叶子","square":"正方形","rock":"岩石","cactus":"仙人掌","stinger":"毒刺","rice":"大米",
    "honey":"蜂蜜","poo":"大便","magnet":"磁铁","wing":"翅膀","pollen":"花粉","web":"网",
    "missile":"导弹","lightning":"闪电","sand":"沙子","glass":"玻璃","lucky_clover":"幸运草",
    "corn":"玉米","faster":"更快","soil":"土壤","sponge":"海绵","root":"树根","shovel":"铲子",
    "mysterious_powder":"神秘粉末","mysterious_stick":"神秘树枝","talisman":"护符","coin":"硬币",
    "bullet":"子弹","flower":"花","paper":"纸","gambler":"赌徒","bubble":"泡泡","orb":"宝珠",
    "scythe":"镰刀","blade":"刀片","yggdrasil":"世界树","mark":"标记","strange_artifact":"奇异神器",
    "insignia":"徽章","eyeball":"眼球","net":"网","firefly":"萤火虫","moth":"飞蛾","stinger2":"毒针",
    "fertilizer":"肥料","duck":"鸭子","bottle":"瓶子","egg":"蛋","seashell":"贝壳","pearl":"珍珠",
    "frost":"霜","icicle":"冰柱","jelly":"果冻","paint":"油漆","fluff":"绒毛","diamond":"钻石",
    "mushroom":"蘑菇","clover":"三叶草","ant":"蚂蚁","beetle":"甲虫","square_petal":"方块花瓣",
}

# 特殊优先怪(用户要求最先打)
PRIORITY_SIDS = {"square", "ladybug_shiny", "leafbug_shiny", "ant_soldier_diver", "gambler", "assembler", "beetle_pharaoh", "ghost"}

# 危险怪(自动避开: 高伤害/毒/远程/召唤)
DANGER_SIDS = {"ant_queen", "ant_hole", "fire_ant_burrow", "hornet", "wasp", "centipede_evil",
               "scorpion", "jellyfish", "beetle_hel", "spider_hel", "centipede_hel", "wasp_hel",
               "gambler", "mecha_flower", "wasp_mecha", "spider_mecha", "crab_mecha", "termite_overmind",
               "beetle_mummy", "beetle_pharaoh", "assembler", "ghost"}

# wasm反汇编真实碰撞箱 (Common基准, 地图像素)
# gardn Collision.cc 验证: 碰撞判定 = 圆碰撞(半径和), 玩家撞怪被质量比击退(_deal_knockback,
# 花侧_cancel_movement 硬顶), 接触伤害 DamageType::kContact 双向结算, Web 减速 speed_ratio=0.5
WASM_RADII = {
    "rock":12.0,"cactus":12.0,"ladybug":10.0,"bee":5.0,"ant_baby":10.0,"ant_worker":12.0,
    "ant_soldier":25.0,"ant_queen":10.0,"ant_hole":10.0,"beetle":10.0,"hornet":16.0,
    "centipede":75.0,"centipede_evil":13.0,"centipede_desert":12.0,"square":35.0,
    "spider":12.0,"scorpion":14.0,"fire_ant_soldier":12.0,"fire_ant_burrow":20.0,
    "sandstorm":40.0,"bubble":10.0,"bumble_bee":15.0,"shell":10.0,"starfish":30.0,"crab":25.0,
    "jellyfish":12.0,"digger":20.0,"sponge":30.0,"leech":10.0,"dandelion":5.0,
    "fire_ant_baby":6.0,"fire_ant_worker":12.0,"fire_ant_queen":25.0,"ant_egg":4.0,
    "fire_ant_egg":4.0,"fly":5.0,"leafbug":12.0,"mantis":15.0,"termite_baby":5.0,
    "termite_worker":10.0,"termite_soldier":18.0,"termite_overmind":60.0,"termite_mound":30.0,
    "termite_egg":4.0,"bush":18.0,"roach":8.0,"moth":8.0,"firefly":8.0,"beetle_hel":18.0,
    "wasp":10.0,"spider_hel":15.0,"centipede_hel":80.0,"wasp_hel":10.0,"gambler":8.0,
    "firefly_magic":10.0,"beetle_nazar":14.0,"worm":10.0,"mecha_flower":30.0,"wasp_mecha":15.0,
    "spider_mecha":20.0,"leafbug_shiny":12.0,"crab_mecha":30.0,"assembler":40.0,"barrel":15.0,
    "beetle_mummy":15.0,"beetle_pharaoh":20.0,"tomb":25.0,"silverfish":6.0,"garbage":10.0,
    "ant_soldier_diver":15.0,"ghost":12.0,
}
RARITY_RADIUS_SCALE = {
    "Common":1.0,"Rare":1.3,"Super":1.5,"Epic":2.0,"Legendary":3.0,
    "Mythic":5.0,"Ultra":8.0,"Unique":10.0,
}

# 追击范围(wasm AI): 怪在这距离内主动追玩家
AGGRO_RANGE = {
    "default":255,"aggressive":360,"very_aggressive":380,"passive":60,"turret":100,"boss":250,
}
MOB_AGGRO_CLASS = {
    "rock":"passive","cactus":"passive","ladybug":"passive","bee":"passive","ant_baby":"passive",
    "ant_worker":"passive","bush":"passive","shell":"passive","starfish":"passive","sponge":"passive",
    "dandelion":"passive","ant_egg":"passive","fire_ant_egg":"passive","termite_egg":"passive",
    "bubble":"passive","termite_mound":"turret","ant_hole":"turret","fire_ant_burrow":"turret",
    "sandstorm":"very_aggressive","hornet":"aggressive","wasp":"aggressive","scorpion":"aggressive",
    "spider":"aggressive","centipede_evil":"aggressive","jellyfish":"aggressive","leech":"aggressive",
    "beetle":"aggressive","ant_soldier":"aggressive","fire_ant_soldier":"aggressive",
    "termite_soldier":"aggressive","moth":"aggressive","beetle_hel":"very_aggressive",
    "spider_hel":"very_aggressive","centipede_hel":"very_aggressive","wasp_hel":"very_aggressive",
    "gambler":"very_aggressive","mecha_flower":"boss","assembler":"boss","beetle_pharaoh":"boss",
    "termite_overmind":"boss","ant_queen":"aggressive","fire_ant_queen":"aggressive",
    "centipede":"aggressive","centipede_desert":"aggressive","mantis":"aggressive",
    "leafbug":"passive","leafbug_shiny":"passive","ladybug_shiny":"passive","ladybug_dark":"passive",
    "square":"passive","digger":"passive","fly":"passive","roach":"passive","worm":"passive",
    "silverfish":"passive","garbage":"passive","firefly":"passive","firefly_magic":"passive",
    "beetle_nazar":"aggressive","wasp_mecha":"aggressive","spider_mecha":"aggressive",
    "crab_mecha":"aggressive","barrel":"passive","tomb":"turret","ghost":"very_aggressive",
    "ant_soldier_diver":"aggressive","beetle_mummy":"aggressive","mecha_flower":"boss",
}

# 追击速度系数(源码级: gardn Ai.cc, ×玩家加速度) —— 决定"能不能风筝"
# ≥1.0 = 追得上玩家, 不能边走边打;  <1.0 = 追不上, 可风筝
AGGRO_SPEED = {
    "scorpion":1.20,"spider":1.20,"centipede_desert":1.33,
    "soldier_ant":0.95,"ant_soldier":0.95,"fire_ant_soldier":0.95,"beetle":0.95,
    "beetle_massive":0.95,"centipede_evil":0.95,"hornet":0.975,"wasp":0.975,
    "ant_worker":0.975,"ladybug_dark":0.975,"ladybug_shiny":0.975,"queen_ant":0.95,"ant_queen":0.95,
    "digger":0.95,"termite_soldier":0.95,"mantis":0.95,"moth":0.95,"leech":0.975,
}

def get_aggro_speed(sid):
    """怪的追击速度系数; 默认0.95(攻击态基准) / 被动怪=0"""
    if sid in AGGRO_SPEED:
        return AGGRO_SPEED[sid]
    cls = MOB_AGGRO_CLASS.get(sid, "passive")
    if cls == "passive":
        return 0.0
    return 0.95

def get_escape_dist(sid):
    """风筝线 = 1.5 × 检测半径(源码 _focus_lose_clause): 出这个圈才丢仇恨"""
    return 1.5 * get_aggro(sid)

# ================= 怪物属性 =================
def mobs():
    m = _load_json('mob_stats_full.json')
    if not m:
        return {}
    return {x['sid']: x for x in m}

def rarity_tiers(sid):
    m = mobs().get(sid)
    if not m:
        return []
    return m.get('rarities', [])

def hp_range(sid, rarity):
    """返回 [min_hp, max_hp] 或 None"""
    for r in rarity_tiers(sid):
        if r.get('rarity') == rarity:
            hr = r.get('HealthRange', r.get('Health', None))
            if hr is None:
                return None
            return hr if isinstance(hr, list) else [hr, hr]
    return None

def damage_of(sid, rarity):
    for r in rarity_tiers(sid):
        if r.get('rarity') == rarity:
            return r.get('Damage')
    return None

def exp_of(sid, rarity):
    for r in rarity_tiers(sid):
        if r.get('rarity') == rarity:
            return r.get('exp', 0)
    return 0

def rarity_infer(sid, hp):
    """按HP反推稀有度 (内存实体只有type id+hp, 没有稀有度字段)"""
    if hp is None or hp <= 0:
        return 'Common'
    best, best_d = None, None
    for r in rarity_tiers(sid):
        hr = r.get('HealthRange', r.get('Health', None))
        if hr is None:
            continue
        lo, hi = (hr[0], hr[1]) if isinstance(hr, list) else (hr, hr)
        if lo <= hp <= hi:
            return r.get('rarity')
        d = min(abs(hp - lo), abs(hp - hi))
        if best_d is None or d < best_d:
            best_d, best = d, r.get('rarity')
    return best or 'Common'

def get_radius(sid, rarity='Common'):
    """真实碰撞箱(地图像素)"""
    base = WASM_RADII.get(sid, 12.0)
    return base * RARITY_RADIUS_SCALE.get(rarity, 1.0)

def get_aggro(sid):
    """追击范围"""
    cls = MOB_AGGRO_CLASS.get(sid, 'default')
    return AGGRO_RANGE.get(cls, 255)

def cn(sid):
    return MOB_CN.get(sid, sid)

# ================= 官方汉化映射 (FlorrTranslate-zh_CN, GPL-3.0) =================
# 地图名官方中文 (汉化包): map key -> 中文名
MAP_CN = {
    "garden": "后花园", "desert": "南部沙漠", "ocean": "东部水域", "jungle": "丛林",
    "anthell": "蚂蚁地狱", "hel": "冥界", "pyramid": "金字塔", "rift": "裂隙",
    # Centralia 系列(后花园)
    "Centralia Fields 1": "后花园 1 (石头)", "Centralia Fields 2": "后花园 2",
    "Centralia Fields 3": "后花园 3 (瓢虫)", "Centralia Fields 4": "后花园 4",
    "Centralia Fields 5": "后花园 5 (蜈蚣)", "Centralia Fields 6": "后花园 6 (黄蜂)",
    "Centralia Fields 7": "后花园 7 (蒲公英)", "Centralia Maze": "后花园迷宫",
    "Centralia Sewers 1": "后花园下水道 1 (飞蛾)", "Centralia Sewers 2": "后花园下水道 2 (蟑螂)",
    "Centralia Sewers 3": "后花园下水道 3 (苍蝇)", "Centralia Sewers 4": "后花园下水道 4 (蜘蛛)",
    "Centralia Beach": "后花园海滩",
    # 沙漠
    "South Desert 1": "南部沙漠 1 (沙尘暴)", "South Desert 2": "南部沙漠 2",
    "South Desert 3": "南部沙漠 3 (仙人掌)", "South Desert 4": "南部沙漠 4 (闪亮瓢虫)",
    "South Desert 5": "南部沙漠 5 (甲虫)",
    # 水域
    "East Waters 1": "东部水域 1", "East Waters 2": "东部水域 2",
    "East Waters 3": "东部水域 3", "East Waters 4": "东部水域 4 (贝壳)",
    "East Waters 6": "东部水域 6 (水蛭)", "Jellyfish Fields": "水母之地 (水母)",
    "Crab Kingdom": "螃蟹王国 (泡泡&螃蟹)",
    # 蚂蚁地狱
    "Ant Hell 1": "火蚁地狱 (火蚁后)", "Ant Hell 2": "黑蚁地狱 (黑蚁后)",
    "Ant Hell 3": "白蚁地狱 (白蚁领主)",
}

_I18N = None
def i18n(text):
    """官方汉化查询: 返回 text 的中文翻译(若有), 否则原样返回"""
    global _I18N
    if _I18N is None:
        try:
            import json as _json
            _I18N = _json.load(open(os.path.join(_DATA_DIR, 'florr_i18n_zh.json'), encoding='utf-8'))
        except Exception:
            _I18N = {}
    return _I18N.get(text, text)

def map_cn(key):
    """地图中文名(支持 alias): key 小写匹配 MAP_CN, 否则 i18n"""
    if not key:
        return key
    k = str(key).lower()
    if k in MAP_CN:
        return MAP_CN[k]
    return i18n(key)

def type_id_to_sid(tid):
    return TYPE_ID_TO_SID.get(tid)

# ================= 掉落价值 =================
_RARITY_VALUE = {"Common":1,"Rare":2,"Super":3,"Epic":4,"Legendary":5,"Mythic":10,"Ultra":30,"Unique":50}

def drop_value(sid):
    """打这只怪的价值分: 掉落花瓣种类数x稀有度权重x基础概率
    v1.19.6: 真源掉率优先(dropchance_v2 期望掉落数 × 档位稀有度权重), 无数据回退旧表"""
    v2 = _load_drop_v2().get(sid)
    if v2:
        _TIER_W = {"Common":1,"Unusual":2,"Rare":4,"Epic":8,"Legendary":16,"Mythic":40,"Ultra":120,"Super":400}
        total = 0.0
        for tier, rows in v2.items():
            if not rows:
                continue
            exp = sum(r.get('rate', 0) for r in rows)  # 该档期望掉落花瓣数(每花瓣独立roll)
            total += exp * _TIER_W.get(tier, 1)
        return total
    m = mobs().get(sid)
    if not m:
        return 0.0
    return sum(d.get('baseChance', 0) * 50 for d in m.get('drops', []))

# ================= 真源掉率表 (FlorrBt私服 drop_rate.h 转译, v1.19.0) =================
_DROP_V2 = None
def _load_drop_v2():
    global _DROP_V2
    if _DROP_V2 is None:
        _DROP_V2 = _load_json('florr_dropchance_v2.json') or {}
    return _DROP_V2

def drop_rates(sid, rarity=None):
    """真源掉率: sid -> {稀有度档 -> [{petal, rarity, rate}]}
    无数据返回 {} (该怪掉率未知时回退旧表)"""
    tbl = _load_drop_v2()
    m = tbl.get(sid)
    if not m:
        return {} if rarity is None else []
    if rarity is None:
        return m
    return m.get(rarity, [])

def drop_hint(sid, rarity):
    """战斗提示: 该档位最值得掉的 3 种花瓣 (按概率x稀有度权重)"""
    rows = drop_rates(sid, rarity)
    if not rows:
        return ''
    _RV = {"Common":1,"Unusual":2,"Rare":4,"Epic":8,"Legendary":16,"Mythic":40,"Ultra":120,"Super":400}
    rows = sorted(rows, key=lambda r: -(r.get('rate', 0) * _RV.get(r.get('rarity', 'Common'), 1)))
    parts = []
    seen = set()
    for r in rows:
        p = r.get('petal')
        if p in seen:
            continue
        seen.add(p)
        rate = r.get('rate', 0)
        if rate < 0.0005:
            continue
        parts.append(f"{petal_cn(p) or p} {rate*100:.1f}%")
        if len(parts) >= 3:
            break
    return '、'.join(parts)

def assess_mob(sid, hp, player_dps, dist=None):
    """综合评估一只怪: 返回 (action, score, rarity, name_cn)
    action: 'oneshot'(秒杀追) / 'fight'(可打) / 'flee'(避开) / 'ignore'(不管) / 'danger'(危险逃跑)
    v1.18.3: 危险怪能秒杀照样打(用户: 秒杀自动追), 秒不了才避开
    """
    rarity = rarity_infer(sid, hp)
    hi = hp_range(sid, rarity)
    max_hp = hi[1] if hi else hp
    if player_dps > 0:
        if max_hp <= player_dps:
            action = 'oneshot'
        elif max_hp <= player_dps * 3:
            action = 'fight'
        else:
            action = 'ignore'
    else:
        action = 'fight' if max_hp < 500 else 'ignore'
    # 危险怪: 秒不了的才避开(能秒的走 oneshot 追击)
    if sid in DANGER_SIDS and action != 'oneshot':
        return 'danger', -1000, None, cn(sid)
    # 评分: 秒杀优先 + 特殊怪加成 + 掉落价值 + 距离
    score = 0.0
    if action == 'oneshot':
        score += 1000.0
    elif action == 'fight':
        score += 300.0
    if sid in PRIORITY_SIDS:
        score += 5000.0
    score += drop_value(sid) * 10.0
    # v1.19.0 真源掉率加分: 有高稀有度掉落的怪更值得打 (drop_rate.h 转译表)
    v2 = drop_rates(sid)
    if v2:
        hi = sum(1 for rar, rows in v2.items() if rar in ('Ultra', 'Super') and rows)
        score += hi * 800.0
        score += len(v2) * 15.0
    # 源码级危险修正: 追得上的怪(≥1.0倍速)危险加倍 - 必须秒杀或立即风筝
    spd = get_aggro_speed(sid)
    if spd >= 1.0:
        score -= 3000.0 if action != 'oneshot' else 0.0
    if dist is not None:
        score += 2000.0 / (dist + 50)
    return action, score, rarity, cn(sid)

# ================= 花瓣库 =================
def petals():
    return _load_json('all_petals.json') or []

def petal_sids():
    return {p.get('sid') for p in petals()}

# 回血花瓣 (从all_petals.json tooltip精确属性确认)
#   Petal/Attribute/Heal            -> 一次性爆发回血 (玫瑰/大丽花)
#   Petal/Attribute/HealPerSecond   -> 持续回血 (丝兰/海星/叶子, 防御时生效)
_HEAL_ATTRS = ('Petal/Attribute/Heal', 'Petal/Attribute/HealPerSecond')

def _petal_has_heal(sid):
    for p in petals():
        if p.get('sid') != sid:
            continue
        for r in p.get('rarities', []):
            for t in r.get('tooltip', []):
                if t[0] in _HEAL_ATTRS:
                    return True
    return False

HEAL_PETALS = None
def heal_petals():
    """返回回血花瓣sid集合"""
    global HEAL_PETALS
    if HEAL_PETALS is not None:
        return HEAL_PETALS
    s = set()
    for sid in petal_sids():
        if _petal_has_heal(sid):
            s.add(sid)
    HEAL_PETALS = s
    return s

def is_heal_petal(sid):
    return sid in heal_petals()

def petal_cn(sid):
    return PETAL_CN.get(sid, sid)


if __name__ == '__main__':
    print(f"=== 统一数据层测试 ===")
    print(f"怪物: {len(mobs())} 只, 花瓣: {len(petals())} 个")
    print(f"回血花瓣: {sorted(heal_petals())}")
    for tid in (18, 20, 8, 73, 82, 7):
        sid = type_id_to_sid(tid)
        if not sid: continue
        print(f"  type{tid:>3} {sid:18s} {cn(sid)}  半径={get_radius(sid):.0f}px 追击={get_aggro(sid)}px")
    print(f"square hp=35: 稀有度={rarity_infer('square',35)}, 玩家DPS=1000 -> {assess_mob('square',35,1000)}")
    print(f"ant_queen hp=5000: -> {assess_mob('ant_queen',5000,1000)}")
    print(f"rock hp=80: -> {assess_mob('rock',80,1000)}")
