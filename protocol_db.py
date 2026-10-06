# -*- coding: utf-8 -*-
"""protocol_db.py v1.27.0 - florr.io 网络协议全表 (NETWORK_PROTOCOL_DOC.md, FlorrBt protocol.js 真源)
把完整收发协议映射成可查询数据库:
  - 网络实体名表 MobNames(39) / PetalNames(62)  -> 协议type/名 -> 本地sid
  - 服务端消息类型 ServerType / 客户端发包表
  - 实体类型编码 EntityType (怪/投射物/传送门/花瓣/掉落)
  - 聊天 ChatFlag (2=Server管理员=挂机检测聊天挑战)
  - 紧凑实体解码 decode_compact_entity (直接解析WebSocket帧)
用途: bridge 数据带网络type时优先解析; 未来自定义客户端发包; 挂机挑战flag识别
"""
import struct

# ===== 1. 缩放常量 (§1) =====
NET_COORD_SCALE = 64          # 世界坐标: i32 / 64
NET_RELATIVE_COORD_SCALE = 1  # 紧凑实体相对坐标 i16
NET_RADIUS_SCALE = 1          # 半径 u16
NET_ANGLE_SCALE = 1000        # 角度 i16 / 1000
NET_PERCENT_SCALE = 255       # 百分比 u8 / 255
NET_SLOT_SIZE_SCALE = 65535   # 槽位大小 u16 / 65535

# ===== 2. 服务端消息类型 (§2) =====
SERVER_TYPES = {
    0x00: ('Welcome', 'playerId(u16)+ownerEntityId(u16)+tickRate(u8)+mapName(string)'),
    0x01: ('Snapshot', 'snapshotId+baseSnapshotId+serverTick+ownerEntityId+viewRadius+实体列表+removedIds'),
    0x02: ('AuthResult', 'resultCode(u8)+message(string)'),
    0x10: ('OwnerState', 'level+flags+expProgress+ownerSlots+secondarySlots+talentPoints+talents'),
    0x11: ('Inventory', 'count(u16)+[{petalType(u8),rarity(u8),count(u32)}]'),
    0x12: ('Chat', 'flag(u8)+playerId(u16)+time(u32)+playerName(string)+message(string)'),
    0x13: ('CraftResult', 'success(u8)+petalType+rarity+consumed(u32)+items'),
}
SERVER_TYPE_NAMES = {k: v[0] for k, v in SERVER_TYPES.items()}

# ===== 3. 实体类型编码 (§4) =====
ENTITY_MOB_MAX = 92                 # 0-92: 普通怪物
ENTITY_TRAP = 93                    # trap 投射物
ENTITY_BLOOD_SACRIFICE = 94         # 血祭实体
ENTITY_DANDELION_MISSILE = 95       # 蒲公英导弹
ENTITY_POLLEN = 96                  # 花粉
ENTITY_SPIDER_WEB = 97              # 蜘蛛网
ENTITY_MISSILE = 98                 # 导弹
ENTITY_PORTAL = 99                  # 传送门
NETWORK_PETAL_TYPE_OFFSET = 100     # 100+: 花瓣实体 (petalType = entityType-100)
NETWORK_DROP_TYPE_OFFSET = 180      # 180+: 掉落物 (petalType = entityType-180)

PROJECTILE_TYPES = {ENTITY_TRAP, ENTITY_BLOOD_SACRIFICE, ENTITY_DANDELION_MISSILE,
                    ENTITY_POLLEN, ENTITY_SPIDER_WEB, ENTITY_MISSILE}


def entity_kind(type_id):
    """协议实体类型 -> 类别: mob/projectile/portal/petal/drop/unknown"""
    t = type_id
    if t <= ENTITY_MOB_MAX:
        return 'mob'
    if t == ENTITY_PORTAL:
        return 'portal'
    if t in PROJECTILE_TYPES:
        return 'projectile'
    if t >= NETWORK_DROP_TYPE_OFFSET:
        return 'drop'
    if t >= NETWORK_PETAL_TYPE_OFFSET:
        return 'petal'
    return 'unknown'

# ===== 4. MobNames 网络表 (§5, index->名字, 共39) =====
NET_MOB_NAMES = {
    0: 'None', 1: 'Beetle', 2: 'Gambler', 3: 'NormalLadybug', 4: 'MechaFlower',
    5: 'NormalFlower', 6: 'PlayerFlower', 7: 'SoldierAnt', 8: 'SoldierFireAnt',
    9: 'SoldierTermite', 10: 'SummonedBeetle', 11: 'SummonedSoldierAnt',
    12: 'BandageBeetle', 13: 'Bee', 14: 'Hornet', 15: 'BumbleBee', 16: 'Rock',
    17: 'BabyAnt', 18: 'WorkerAnt', 19: 'QueenAnt', 20: 'AntHole', 21: 'Spider',
    22: 'Sandstorm', 23: 'Dummy', 24: 'Dandelion', 25: 'AntEgg', 26: 'FireAntEgg',
    27: 'TermiteEgg', 28: 'QueenAntEgg', 29: 'QueenFireAntEgg', 30: 'BabyFireAnt',
    31: 'WorkerFireAnt', 32: 'FireQueenAnt', 33: 'BabyTermite', 34: 'WorkerTermite',
    35: 'TermiteOvermind', 36: 'LeafPiece', 37: 'LeafcutterSoldier', 38: 'Titan',
}

# 协议怪名 -> 本地sid (静态表)
NET_MOB_TO_SID = {
    'Beetle': 'beetle', 'Gambler': 'gambler', 'NormalLadybug': 'ladybug',
    'MechaFlower': 'mecha_flower', 'NormalFlower': None, 'PlayerFlower': None,
    'SoldierAnt': 'ant_soldier', 'SoldierFireAnt': 'fire_ant_soldier',
    'SoldierTermite': 'termite_soldier', 'SummonedBeetle': 'beetle',
    'SummonedSoldierAnt': 'ant_soldier', 'BandageBeetle': 'beetle',
    'Bee': 'bee', 'Hornet': 'hornet', 'BumbleBee': 'bumble_bee', 'Rock': 'rock',
    'BabyAnt': 'ant_baby', 'WorkerAnt': 'ant_worker', 'QueenAnt': 'ant_queen',
    'AntHole': 'ant_hole', 'Spider': 'spider', 'Sandstorm': 'sandstorm',
    'Dummy': None, 'Dandelion': 'dandelion', 'AntEgg': 'ant_egg',
    'FireAntEgg': 'fire_ant_egg', 'TermiteEgg': 'termite_egg',
    'QueenAntEgg': 'ant_egg', 'QueenFireAntEgg': 'fire_ant_egg',
    'BabyFireAnt': 'fire_ant_baby', 'WorkerFireAnt': 'fire_ant_worker',
    'FireQueenAnt': 'fire_ant_queen', 'BabyTermite': 'termite_baby',
    'WorkerTermite': 'termite_worker', 'TermiteOvermind': 'termite_overmind',
    'LeafPiece': None, 'LeafcutterSoldier': 'termite_soldier', 'Titan': None,
}


def net_mob_name(type_id):
    """协议怪type -> 网络名 (index查表)"""
    return NET_MOB_NAMES.get(type_id)


def net_mob_sid(type_id):
    """协议怪type -> 本地sid (无映射返回None, 由调用方回退)"""
    name = NET_MOB_NAMES.get(type_id)
    if not name:
        return None
    return NET_MOB_TO_SID.get(name)

# ===== 5. PetalNames 网络表 (§6, index->名字, 共62) =====
NET_PETAL_NAMES = {
    0: 'None', 1: 'Air', 2: 'AntEgg', 3: 'Antennae', 4: 'Basic', 5: 'BeetleEgg',
    6: 'Bone', 7: 'Bubble', 8: 'Carrot', 9: 'Coin', 10: 'Compass', 11: 'Cogwheel',
    12: 'Disc', 13: 'Dust', 14: 'GoldenLeaf', 15: 'Iris', 16: 'Lentil', 17: 'Moon',
    18: 'Nullification', 19: 'Pincer', 20: 'Relic', 21: 'Rose', 22: 'YinYang',
    23: 'Missile', 24: 'BloodSacrifice', 25: 'Corruption', 26: 'Bandage',
    27: 'Heavy', 28: 'Faster', 29: 'Yggdrasil', 30: 'Dahlia', 31: 'Wing',
    32: 'Triangle', 33: 'Sawblade', 34: 'Fragment', 35: 'Mimic', 36: 'Glass',
    37: 'Stinger', 38: 'BrokenEgg', 39: 'Light', 40: 'Leaf', 41: 'Rock', 42: 'Web',
    43: 'Cactus', 44: 'Pollen', 45: 'Corn', 46: 'Rice', 47: 'Basil', 48: 'Soil',
    49: 'Honey', 50: 'Wax', 51: 'ThirdEye', 52: 'Dandelion', 53: 'Orange',
    54: 'Shovel', 55: 'Yucca', 56: 'WhiteFungus', 57: 'BlackFungus',
    58: 'Broccoli', 59: 'Douli', 60: 'Trapper', 61: 'Amulet', 62: 'Plank',
    63: 'Tomato',
}

# 协议花瓣名 -> 本地sid (小写化匹配)
NET_PETAL_TO_SID = {
    'Air': 'light', 'AntEgg': 'egg', 'Antennae': 'antennae', 'Basic': 'basic',
    'BeetleEgg': 'beetle_egg', 'Bone': 'bone', 'Bubble': 'bubble', 'Carrot': 'carrot',
    'Coin': 'coin', 'Compass': 'compass', 'Cogwheel': 'cogwheel', 'Disc': 'disc',
    'Dust': 'dust', 'GoldenLeaf': 'golden_leaf', 'Iris': 'iris', 'Lentil': 'lentil',
    'Moon': 'moon', 'Nullification': 'nullification', 'Pincer': 'pincer',
    'Relic': 'relic', 'Rose': 'rose', 'YinYang': 'yinyang', 'Missile': 'missile',
    'BloodSacrifice': 'blood_sacrifice', 'Corruption': 'corruption',
    'Bandage': 'bandage', 'Heavy': 'heavy', 'Faster': 'faster',
    'Yggdrasil': 'yggdrasil', 'Dahlia': 'dahlia', 'Wing': 'wing',
    'Triangle': 'triangle', 'Sawblade': 'sawblade', 'Fragment': 'fragment',
    'Mimic': 'mimic', 'Glass': 'glass', 'Stinger': 'stinger',
    'BrokenEgg': 'broken_egg', 'Light': 'light', 'Leaf': 'leaf', 'Rock': 'rock',
    'Web': 'web', 'Cactus': 'cactus', 'Pollen': 'pollen', 'Corn': 'corn',
    'Rice': 'rice', 'Basil': 'basil', 'Soil': 'soil', 'Honey': 'honey',
    'Wax': 'wax', 'ThirdEye': 'third_eye', 'Dandelion': 'dandelion',
    'Orange': 'orange', 'Shovel': 'shovel', 'Yucca': 'yucca',
    'WhiteFungus': 'white_fungus', 'BlackFungus': 'black_fungus',
    'Broccoli': 'broccoli', 'Douli': 'douli', 'Trapper': 'trapper',
    'Amulet': 'amulet', 'Plank': 'plank', 'Tomato': 'tomato',
}


def net_petal_name(type_id):
    """协议花瓣type (entityType-100) -> 网络名"""
    return NET_PETAL_NAMES.get(type_id)


def net_petal_sid(type_id):
    name = NET_PETAL_NAMES.get(type_id)
    if not name:
        return None
    return NET_PETAL_TO_SID.get(name)

# ===== 6. 稀有度网络索引 (§7, 13档) =====
NET_RARITY_NAMES = {
    0: 'Null', 1: 'Common', 2: 'Unusual', 3: 'Rare', 4: 'Epic', 5: 'Legendary',
    6: 'Mythic', 7: 'Ultra', 8: 'Super', 9: 'Eternal', 10: 'Unique',
    11: 'Primordial', 12: 'Exotic',
}

# ===== 7. 客户端→服务器发包表 (§8) =====
CLIENT_CMDS = {
    0x00: ('输入移动', 'moveX(i8)+moveY(i8)'),
    0x01: ('装备', 'petalType(u8)+(slotIndex(4bit)<<4)|(rarity(4bit))'),
    0x02: ('卸装', '(slotIndex(4bit)<<2)'),
    0xf0: ('认证', 'mode(u8)+4个长度+name/password/email/code'),
    0xf1: ('聊天', 'flag(u8)+len+message (max 180字节)'),
    0xf2: ('副槽', 'slotIndex(u8)+petalType(u8)+rarity(u8)'),
    0xf3: ('合成', 'petalType(u8)+rarity(u8)+count(u32)'),
    0xf4: ('天赋操作', 'action(u8:1加/2删)+count+[{id(u16),rarity(u8),rank(u8)}]'),
    0xf5: ('状态请求', '空'),
    0xf6: ('锻造Forge', 'petalType(u8)+8(u8)+5(u32)'),
    0xf7: ('快照确认', 'snapshotId(u32) (全量快照=0xffffffff)'),
    0xf8: ('输入帧', 'sequence(u32)+targetServerTick(u64)+moveX(i8)+moveY(i8)+flags(bit0攻/bit1防/bit2挖)'),
}

# ===== 8. ChatFlag (§9) =====
CHAT_FLAGS = {
    0: 'Global', 1: 'Local', 2: 'Server', 3: 'Whisper', 4: 'Squad',
}
# 挂机检测聊天挑战 = flag 2 (Server 管理员) — chat_solver 优先检测
AFK_CHALLENGE_FLAG = 2


def is_server_message(flag):
    """该聊天消息是否来自服务器(管理员=挂机检测聊天挑战来源)"""
    return flag == AFK_CHALLENGE_FLAG

# ===== 9. 紧凑实体解码 (§3, 相对首个实体origin) =====
# 格式: entityId(u16)+type(u8)+team(u8)+pos(origin+i16/1)+radius(u16)+hpPercent(u8/255)
#       +shieldPercent(u8/255)+flags(u16)+angle(i16/1000)+rarity(u8)+name=""
_COMPACT_LEN = 2 + 1 + 1 + 2 + 2 + 2 + 1 + 1 + 2 + 2 + 1  # 17 bytes


def decode_compact_entity(buf, offset, origin_x, origin_y):
    """解析一个紧凑实体(相对坐标), 返回 (entity, next_offset) 或 (None, offset)
    entity: dict(entityId,type,team,x,y,radius,hpPercent,shieldPercent,flags,angle,rarity,kind)"""
    if len(buf) - offset < _COMPACT_LEN:
        return None, offset
    b = buf
    entity_id, = struct.unpack_from('<H', b, offset); offset += 2
    etype = b[offset]; offset += 1
    team = b[offset]; offset += 1
    rx, = struct.unpack_from('<h', b, offset); offset += 2
    ry, = struct.unpack_from('<h', b, offset); offset += 2
    radius, = struct.unpack_from('<H', b, offset); offset += 2
    hp_pct = b[offset]; offset += 1
    shield_pct = b[offset]; offset += 1
    flags, = struct.unpack_from('<H', b, offset); offset += 2
    angle, = struct.unpack_from('<h', b, offset); offset += 2
    rarity_idx = b[offset]; offset += 1
    # 紧凑实体 name 为空 (无 nameLen 字段)
    return {
        'entityId': entity_id,
        'type': etype,
        'team': team,
        'x': origin_x + rx * NET_RELATIVE_COORD_SCALE,
        'y': origin_y + ry * NET_RELATIVE_COORD_SCALE,
        'radius': radius * NET_RADIUS_SCALE,
        'hpPercent': hp_pct / NET_PERCENT_SCALE,
        'shieldPercent': shield_pct / NET_PERCENT_SCALE,
        'flags': flags,
        'angle': angle / NET_ANGLE_SCALE,
        'rarity': NET_RARITY_NAMES.get(rarity_idx, 'Unknown'),
        'rarityIndex': rarity_idx,
        'kind': entity_kind(etype),
    }, offset


def decode_compact_entities(buf, origin_x, origin_y, limit=512):
    """解码一段紧凑实体列表 (假设buf=连续紧凑实体, 到limit个或解析失败停)"""
    out, off = [], 0
    for _ in range(limit):
        ent, off = decode_compact_entity(buf, off, origin_x, origin_y)
        if ent is None:
            break
        out.append(ent)
    return out


if __name__ == '__main__':
    print("=== 协议全表测试 ===")
    print(f"MobNames: {len(NET_MOB_NAMES)}个, PetalNames: {len(NET_PETAL_NAMES)}个")
    print(f"net_mob_name(14)={net_mob_name(14)}, ->sid={net_mob_sid(14)}")
    print(f"net_petal_name(30)={net_petal_name(30)}, ->sid={net_petal_sid(30)}")
    print(f"entity_kind(5)={entity_kind(5)}, (99)={entity_kind(99)}, (150)={entity_kind(150)}, (200)={entity_kind(200)}")
    print(f"rarity[7]={NET_RARITY_NAMES[7]}, is_server_message(2)={is_server_message(2)}")
    print(f"CLIENT_CMDS[0xf8]={CLIENT_CMDS[0xf8]}")
    # 解码测试: 构造一个紧凑实体 (type=16 Rock, rarity=1 Common)
    import struct as _s
    buf = _s.pack('<HBBhhHBBHhB', 42, 16, 2, 100, -50, 12, 255, 0, 0, 0, 1)
    ent, off = decode_compact_entity(buf, 0, 30000, 30000)
    print(f"解码紧凑实体: {ent}")
    print(f"实体kind={ent['kind']}, 网络名={net_mob_name(ent['type'])}")
