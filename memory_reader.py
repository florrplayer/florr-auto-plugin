# -*- coding: utf-8 -*-
"""
直接读wasm内存获取游戏状态 - 不需要OpenCV截图!
实体结构 (每392字节):
  +0:  X坐标 (float64, little-endian)
  +8:  Y坐标 (float64)
  +36: HP (float32)
  +92: 怪物类型ID (uint32)
  +120: 半径 (float32)
实体数组范围: ~12,700,000 - 12,800,000
"""
import struct, requests, json

# 浏览器bridge服务器
BRIDGE_URL = "http://localhost:18899"

# 实体结构偏移
OFF_X = 0
OFF_Y = 8
OFF_HP = 36
OFF_TYPE = 92
OFF_RADIUS = 120
ENTITY_STRIDE = 392

# 扫描范围
SCAN_START = 12700000
SCAN_END = 12800000

# 怪物类型ID映射 (从wasm偷的数据)
MOB_TYPE_NAMES = {
    0: "unknown",
    1: "player",
    2: "petal",
    15: "desert_scorpion",
    21: "ocean_jelly",
    257: "desert_mantis_shrimp",
    262: "desert_vulture",
    264: "desert_roadrunner",
    289: "desert_buzzard",
    292: "desert_hawk",
    3841: "boss",
    3859: "anthell_worker",
    3867: "anthell_soldier",
    513: "desert_beetle",
    1066: "desert_scarab",
    7936: "projectile",
}

def fetch_heap_range(start, end):
    """通过bridge从浏览器读取wasm堆内存"""
    try:
        r = requests.get(f"{BRIDGE_URL}/heap?start={start}&end={end}", timeout=2)
        if r.status_code == 200:
            return r.content
    except:
        pass
    return None

def scan_entities(heap_data=None):
    """扫描wasm堆, 返回所有活跃怪物"""
    if heap_data is None:
        heap_data = fetch_heap_range(SCAN_START, SCAN_END)
    if not heap_data:
        return []

    entities = []
    offset = 0
    while offset < len(heap_data) - 400:
        try:
            # 读取X, Y (float64)
            x = struct.unpack_from('<d', heap_data, offset)[0]
            y = struct.unpack_from('<d', heap_data, offset + 8)[0]

            # 合理坐标范围
            if not (10000 < x < 50000 and 10000 < y < 60000):
                offset += 8
                continue

            # 读取HP (float32)
            hp = struct.unpack_from('<f', heap_data, offset + OFF_HP)[0]

            # 有效怪物: HP在1-100000之间
            if not (1 < hp < 100000):
                offset += 8
                continue

            # 读取类型ID
            mob_type = struct.unpack_from('<I', heap_data, offset + OFF_TYPE)[0]

            # 过滤掉花瓣/装饰 (HP=7, X≈Y的)
            if hp == 7 and abs(x - y) < 100:
                offset += 8
                continue

            # 读取半径
            radius = struct.unpack_from('<f', heap_data, offset + OFF_RADIUS)[0]

            type_name = MOB_TYPE_NAMES.get(mob_type, f"type_{mob_type}")
            entities.append({
                'x': x, 'y': y,
                'hp': hp,
                'type_id': mob_type,
                'type': type_name,
                'radius': radius if radius > 0 else 5,
                'addr': SCAN_START + offset,
            })
            offset += ENTITY_STRIDE
        except:
            offset += 8

    return entities

def get_player_pos():
    """获取玩家位置 (在4958248附近)"""
    try:
        heap = fetch_heap_range(4958000, 4959000)
        if heap:
            x = struct.unpack_from('<d', heap, 248)[0]
            y = struct.unpack_from('<d', heap, 256)[0]
            if 10000 < x < 50000 and 10000 < y < 60000:
                return (x, y)
    except:
        pass
    return None

if __name__ == '__main__':
    print("扫描wasm内存中的怪物...")
    ents = scan_entities()
    print(f"找到 {len(ents)} 个实体:")
    for e in ents:
        print(f"  {e['type']:20s} at ({e['x']:.0f}, {e['y']:.0f}) HP={e['hp']:.0f} r={e['radius']:.1f}")
    pos = get_player_pos()
    if pos:
        print(f"\n玩家位置: ({pos[0]:.0f}, {pos[1]:.0f})")
