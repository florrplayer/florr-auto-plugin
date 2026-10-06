# -*- coding: utf-8 -*-
"""net_protocol.py v1.18.1 - florr.io 网络协议解析器 (偷自 better florr FlorrBt 客户端)
完整消息: Welcome/Snapshot/AuthResult/OwnerState/Inventory/Chat/CraftResult
实体: 全量/紧凑格式, 含 rarity/name/slots 字段
发包: 0x00移动/0x01装备/0xf1聊天/0xf3合成/0xf7快照确认/0xf8输入帧...
用途: bridge 端直接解析 WebSocket 帧 -> 实体稀有度/名字/槽位 (比截图/内存更准)
"""
import struct

NET_COORD_SCALE = 64
NET_RELATIVE_COORD_SCALE = 1
NET_RADIUS_SCALE = 1
NET_ANGLE_SCALE = 1000
NET_PERCENT_SCALE = 255
NET_SLOT_SIZE_SCALE = 65535

NETWORK_PETAL_TYPE_OFFSET = 100
NETWORK_DROP_TYPE_OFFSET = 180
NETWORK_PROJECTILE_TYPES = {93, 94, 95, 96, 97, 98, 99}

ENTITY_SNAPSHOT_FULL = 0
ENTITY_SNAPSHOT_COMPACT = 1

FULL_SNAPSHOT_BASE_ID = 0xFFFFFFFF

ServerType = {
    'Welcome': 0x00, 'Snapshot': 0x01, 'AuthResult': 0x02,
    'OwnerState': 0x10, 'Inventory': 0x11, 'Chat': 0x12, 'CraftResult': 0x13,
}
ServerTypeRev = {v: k for k, v in ServerType.items()}

ChatFlag = {'Global': 0, 'Local': 1, 'Server': 2, 'Whisper': 3, 'Squad': 4}

# 网络实体怪表 (index -> 名字)
MobNames = ["None", "Beetle", "Gambler", "NormalLadybug", "MechaFlower", "NormalFlower",
    "PlayerFlower", "SoldierAnt", "SoldierFireAnt", "SoldierTermite", "SummonedBeetle",
    "SummonedSoldierAnt", "BandageBeetle", "Bee", "Hornet", "BumbleBee", "Rock", "BabyAnt",
    "WorkerAnt", "QueenAnt", "AntHole", "Spider", "Sandstorm", "Dummy", "Dandelion", "AntEgg",
    "FireAntEgg", "TermiteEgg", "QueenAntEgg", "QueenFireAntEgg", "BabyFireAnt", "WorkerFireAnt",
    "FireQueenAnt", "BabyTermite", "WorkerTermite", "TermiteOvermind", "LeafPiece",
    "LeafcutterSoldier", "Titan"]

# 网络花瓣表 (index -> 名字)
PetalNames = ["None", "Air", "AntEgg", "Antennae", "Basic", "BeetleEgg", "Bone", "Bubble",
    "Carrot", "Coin", "Compass", "Cogwheel", "Disc", "Dust", "GoldenLeaf", "Iris", "Lentil",
    "Moon", "Nullification", "Pincer", "Relic", "Rose", "YinYang", "Missile", "BloodSacrifice",
    "Corruption", "Bandage", "Heavy", "Faster", "Yggdrasil", "Dahlia", "Wing", "Triangle",
    "Sawblade", "Fragment", "Mimic", "Glass", "Stinger", "BrokenEgg", "Light", "Leaf", "Rock",
    "Web", "Cactus", "Pollen", "Corn", "Rice", "Basil", "Soil", "Honey", "Wax", "ThirdEye",
    "Dandelion", "Orange", "Shovel", "Yucca", "WhiteFungus", "BlackFungus", "Broccoli", "Douli",
    "Trapper", "Amulet", "Plank", "Tomato"]

# 稀有度 (13档)
RarityNames = ["Null", "Common", "Unusual", "Rare", "Epic", "Legendary", "Mythic", "Ultra",
    "Super", "Eternal", "Unique", "Primordial", "Exotic"]
RarityRGB = [
    (0, 0, 0), (111, 211, 96), (255, 230, 93), (68, 72, 200), (134, 31, 222),
    (219, 31, 31), (31, 219, 222), (225, 38, 103), (40, 240, 153), (238, 238, 238),
    (53, 53, 53), (110, 110, 110), (218, 218, 218),
]
# 网络稀有度索引 -> 我们数据层的 rarity 名
RARITY_NAME = {i: RarityNames[i] for i in range(len(RarityNames))}


class Reader:
    def __init__(self, data):
        self.b = data
        self.o = 0

    def has(self, n):
        return self.o + n <= len(self.b)

    def u8(self):
        v = self.b[self.o]; self.o += 1; return v

    def u16(self):
        v = struct.unpack_from('<H', self.b, self.o)[0]; self.o += 2; return v

    def i16(self):
        v = struct.unpack_from('<h', self.b, self.o)[0]; self.o += 2; return v

    def u32(self):
        v = struct.unpack_from('<I', self.b, self.o)[0]; self.o += 4; return v

    def i32(self):
        v = struct.unpack_from('<i', self.b, self.o)[0]; self.o += 4; return v

    def u64(self):
        lo = self.u32(); hi = self.u32(); return lo + hi * 0x100000000

    def string(self, length):
        v = self.b[self.o:self.o + length].decode('utf-8', 'replace'); self.o += length; return v


def parse_entity(r, origin=None):
    fmt = r.u8()
    if fmt == ENTITY_SNAPSHOT_COMPACT:
        if not origin:
            raise ValueError('compact without origin')
        e = {
            'entityId': r.u16(), 'entityType': r.u8(), 'team': r.u8(),
            'x': origin[0] + r.i16(), 'y': origin[1] + r.i16(),
            'radius': r.u16(), 'hpPercent': r.u8() / 255.0,
            'shieldPercent': r.u8() / 255.0, 'flags': r.u16(),
            'angle': r.i16() / 1000.0, 'rarity': r.u8(),
            'name': '', 'primarySlots': [], 'states': [],
        }
        return e
    if fmt != ENTITY_SNAPSHOT_FULL:
        raise ValueError(f'unknown fmt {fmt}')
    e = {
        'entityId': r.u16(), 'entityType': r.u8(), 'team': r.u8(),
        'x': r.i32() / NET_COORD_SCALE, 'y': r.i32() / NET_COORD_SCALE,
        'radius': r.u16(), 'hpPercent': r.u8() / 255.0,
        'shieldPercent': r.u8() / 255.0, 'flags': r.u16(),
        'angle': r.i16() / 1000.0, 'rarity': r.u8(),
        'name': '', 'primarySlots': [], 'states': [],
    }
    name_len = r.u8()
    e['name'] = r.string(name_len)
    n_slots = r.u8()
    for _ in range(n_slots):
        slot = {'petalType': r.u8(), 'rarity': r.u8(), 'visualType': r.u8(), 'copies': []}
        n_copies = r.u8()
        for _c in range(n_copies):
            copy = {'state': r.u8(), 'progress': r.u8() / 255.0, 'visual': None}
            if slot['visualType'] == 1:
                copy['visual'] = r.i16() / 1000.0
            elif slot['visualType'] == 2:
                copy['visual'] = r.u16() / 65535.0
            slot['copies'].append(copy)
        e['primarySlots'].append(slot)
    n_states = r.u8()
    for _ in range(n_states):
        e['states'].append({'type': r.u8(), 'rarity': r.u8()})
    return e


def parse_server_message(payload):
    """解析一条服务端消息, 返回 dict"""
    r = Reader(payload)
    t = r.u8()
    msg = {'type': t, 'typeName': ServerTypeRev.get(t, 'Unknown')}
    if t == ServerType['Welcome']:
        msg['playerId'] = r.u16()
        msg['ownerEntityId'] = r.u16()
        msg['tickRate'] = r.u8()
        msg['mapName'] = r.string(r.u8()) if r.has(1) else ''
    elif t == ServerType['Snapshot']:
        msg['snapshotId'] = r.u32()
        msg['baseSnapshotId'] = r.u32()
        msg['serverTick'] = r.u64()
        msg['ownerEntityId'] = r.u16()
        msg['viewRadius'] = r.i32() / NET_COORD_SCALE
        count = r.u16()
        removed = r.u16()
        ents = []
        origin = None
        for _ in range(count):
            e = parse_entity(r, origin)
            if origin is None:
                origin = (e['x'], e['y'])
            ents.append(e)
        msg['entities'] = ents
        msg['removedEntityIds'] = [r.u16() for _ in range(removed)]
    elif t == ServerType['AuthResult']:
        msg['resultCode'] = r.u8()
        msg['message'] = r.string(r.u8())
    elif t == ServerType['OwnerState']:
        msg['level'] = r.u8()
        msg['flags'] = r.u8()
        pc, sc = r.u8(), r.u8()
        msg['expProgress'] = (r.u16() / 10000.0) if r.has(2) else 0
        msg['ownerSlots'] = [{'petalType': r.u8(), 'rarity': r.u8()} for _ in range(pc)]
        msg['secondarySlots'] = [{'petalType': r.u8(), 'rarity': r.u8()} for _ in range(sc)]
        msg['talentPoints'] = 0
        msg['talents'] = []
        if r.has(3):
            msg['talentPoints'] = r.u16()
            n = r.u8()
            msg['talents'] = [{'id': r.u16(), 'rarity': r.u8(), 'rank': r.u8()} for _ in range(n)]
    elif t == ServerType['Inventory']:
        n = r.u16()
        msg['inventory'] = [{'petalType': r.u8(), 'rarity': r.u8(), 'count': r.u32()} for _ in range(n)]
    elif t == ServerType['Chat']:
        msg['chat'] = {
            'flag': r.u8(), 'playerId': r.u16(), 'time': r.u32(),
            'playerName': r.string(r.u8()), 'message': r.string(r.u8()),
        }
    elif t == ServerType['CraftResult']:
        msg['success'] = r.u8() != 0
        msg['petalType'] = r.u8()
        msg['rarity'] = r.u8()
        msg['consumed'] = r.u32()
        n = r.u16()
        msg['items'] = [{'petalType': r.u8(), 'rarity': r.u8(), 'count': r.u32()} for _ in range(n)]
    return msg


def pop_frame(buffer):
    """从字节流弹出一条带长度前缀的消息 (2字节小端长度)"""
    if not buffer or len(buffer) < 2:
        return None, buffer
    length = buffer[0] | (buffer[1] << 8)
    if length <= 0:
        return bytearray(), buffer[2:]
    if len(buffer) < 2 + length:
        return None, buffer
    payload = buffer[2:2 + length]
    return bytes(payload), buffer[2 + length:]


def entity_kind(entity_type):
    """实体类型分类: 'mob' / 'petal' / 'drop' / 'projectile' / 'unknown'"""
    if 0 <= entity_type < NETWORK_PETAL_TYPE_OFFSET:
        return 'mob'
    if NETWORK_PETAL_TYPE_OFFSET <= entity_type < NETWORK_DROP_TYPE_OFFSET:
        return 'petal'
    if entity_type >= NETWORK_DROP_TYPE_OFFSET:
        return 'drop'
    if entity_type in NETWORK_PROJECTILE_TYPES:
        return 'projectile'
    return 'unknown'


def mob_name(entity_type):
    if 0 <= entity_type < len(MobNames):
        return MobNames[entity_type]
    return f'Mob{entity_type}'


def petal_name(entity_type):
    idx = entity_type - NETWORK_PETAL_TYPE_OFFSET
    if 0 <= idx < len(PetalNames):
        return PetalNames[idx]
    idx = entity_type - NETWORK_DROP_TYPE_OFFSET
    if 0 <= idx < len(PetalNames):
        return PetalNames[idx]
    return f'Petal{entity_type}'


if __name__ == '__main__':
    print('=== net_protocol 测试 ===')
    print('ServerType:', ServerType)
    print('MobNames:', len(MobNames), 'PetalNames:', len(PetalNames))
    print('RarityNames:', RarityNames)
    print('RarityRGB mythic:', RarityRGB[6])
    print('entity_kind(5)=', entity_kind(5), '| 120=', entity_kind(120), '| 185=', entity_kind(185), '| 93=', entity_kind(93))
    print('mob_name(19)=', mob_name(19), '| petal_name(121)=', petal_name(121))
