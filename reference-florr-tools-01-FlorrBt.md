# FlorrBt（better-florr 插件本体）

## 能力摘要（一句话定位 + 技术栈 + 规模）

FlorrBt v1.0.1 是一个**从零重写的 florr.io 风格游戏**，由两部分组成：一个 **C++ 游戏服务器**（`src/Server`，Visual Studio / CMake 工程，含账号系统、持久化、热重载、WebSocket↔TCP 桥）和一个**纯浏览器前端客户端**（`web/`，原生 ES Module + Canvas 2D，无框架）。前端通过二进制 WebSocket 与服务器同步快照。规模：`web/src/game.js` 约 9598 行（任务书称 10474 行，实测 9598），全仓 1128 文件 / 31.5MB，其中 483 个 SVG、92 个 `.h`、52 个 `.c`、42 个 `.cpp`。**它不是官方 florr.io 的反编译产物，而是独立重写实现**——因此它的数值表是"这个私服自己的数值"，与官方 wasm dump 可能存在版本差异。

---

## 可偷数据清单

### ① 可直接整合进现有插件的算法/数据（来源文件 + 函数/表名 → 怎么用）

1. **实体类型 ID 映射（`web/src/game_ids.js` L50-94）**：`beetleType=1, normalLadybugType=3, mechaFlowerType=4, playerFlowerType=6, soldierAntType=7 … titanType=38`。
   → **直接补/对齐全靠插件 `mob_db.py` 的 `TYPE_ID_TO_SID`**。这是"网络实体 type_id → 内部实体名"的权威小表（38 个怪），比 wasm 反推干净。注意：召唤体/特殊 projectile 走 `protocol.js` 的网络偏移（见下）。

2. **花瓣类型 ID → 图标/英文名（`game_ids.js` L96-229 `PetalIconIds` + `protocol.js` L72-137 `PetalNames`）**：数组下标即 petalType，如 `[40]=leaf→"leaf"→叶子`、`[52]=dandelion→"dandelion"→蒲公英`。
   → **替换/补充 `data/all_petals.json` 与 `drop_table.py` 的 `petal_id2sid`**。还额外给出 `nonStackPetalTypes`（L242-256：air/antennae/moon/nullification/relic/bloodSacrifice/corruption/bandage/brokenEgg/wax/thirdEye/shovel/douli 共 13 个不可堆叠花瓣）——这是现有插件里没有的"可堆叠性"维度。

3. **完整二进制线协议（`web/src/protocol.js` 全文 744 行）**：
   - 帧格式：2 字节小端长度前缀（`popFrame` L291）；
   - 收包 opcode `ServerType`：Welcome=0x00 / Snapshot=0x01 / AuthResult=0x02 / OwnerState=0x10 / Inventory=0x11 / Chat=0x12 / CraftResult=0x13；
   - 发包 opcode：Auth=0xf0 / Input=0x00 / InputFrame=0xf8 / Chores=0x03 / Equip=0x01 / Unequip=0x02 / SecondarySlot=0xf2 / Craft=0xf3 / Forge=0xf6 / StateRequest=0xf5 / SnapshotAck=0xf7 / TalentRequest=0xf4 / Chat=0xf1；
   - 缩放系数：`NET_COORD_SCALE=64`、`NET_ANGLE_SCALE=1000`、`NET_PERCENT_SCALE=255`、`NET_SLOT_SIZE_SCALE=65535`；坐标 i32/64、半径 u16、血量百分比 u8/255。
   → **这是 `net_protocol.py` / `bridge_server.py`（WebSocket 桥）的逐字段参考实现**。`parseEntity()`（L362-439）把实体快照的字节布局写得清清楚楚：entityId(u16)+entityType(u8)+team(u8)+pos+radius(u16)+hpPercent(u8)+shieldPercent(u8)+flags(u16)+angle(i16/1000)+rarity(u8)+name+primarySlots+states。可直接照抄成 Python 解包。

4. **稀有度颜色 RGB（`protocol.js` L197-211 `RarityColors`）**：每个稀有度 6 个数 `[r,g,b, 第二色r,g,b]`。
   → **喂给 `combat.py` 的 HSV 颜色过滤识别**。例如 Common=rgb(111,211,96)、Legendary=rgb(219,31,31)、Eternal=rgb(238,238,238)、Unique=rgb(53,53,53)。比从 wasm 字符串里硬抠准确。

5. **实体 flags / 状态位（`game_ids.js` L11-33）**：`flagDead=1<<2(=4)`、`flagOwner=1<<3`、`flagSummoned=1<<8`、`skill_windup_mask=0xf000`；状态枚举 `statePoison=1 … statePsionicConnection=12`。
   → **解包快照后判断"怪死没死/是不是召唤体/中毒"直接用位运算**，补 `combat.py` 的实体过滤逻辑。

6. **小地图材质配色表（`client_config.js` L148-192 `minimapMaterialColors`，40 项 hex）**：`grass=#78b86b、ocean/water=#4d98d4、desert/sand=#d7bd72、pvp=#4c5b53…`。
   → **`spawn_data.py` / 地图识别 / HSV 底色判断可直接用**；也是"按地面材质区分当前在哪个地图区域"的现成查表。

7. **天赋 ID 与天赋树（`talent_data.js` 全文 + `zh-Hans.json` talents 段）**：`TalentId` 1-17，5 个分组（花朵/花瓣/装备/支援/毒素），每个节点的 cost(TP) 与前置链都在 `buildTalentNodes()` 里。
   → **补充 `data/all_talents.json`**：现有 json 只有平铺数据，这里有"分组 + 前置依赖链(base) + 每级 TP 花费"的结构（如 Health 链花费 `[2,5,8,11,14,17,20,21,24]`）。

8. **客户端可调数值滑杆 / 作弊调试开关（`client_config.js` L4-146 + `game.js` `executeClientCommand` L2582-2708）**：`/hitbox` 切换碰撞箱可视化（`state.debugHitbox`）、`/set <key> <value>`、`/slider`、`/colorful_map`、`/map <name>`、`/login_map_x/y/horizon`；可滑的关键项：`dande_missile_scale=4.5`、`hornet_sprite_scale=2.3`、`titan_sprite_scale=2`、`dummy_sprite_scale=1.5`。
   → **这些就是现成的"外挂参数面板"思路**：碰撞箱可视化可用于校准 `combat.py` 的检测框；各 sprite scale 是怪在屏幕上的视觉放大系数。

9. **怪的视觉绘制/碰撞参数（6 个 `*_sprite.js` 顶部 const）**：所有怪统一 110 viewBox、effective box 91.667；碰撞半径直接来自服务器快照 `radius` 字段（`NET_RADIUS_SCALE=1`），血条由 `game.js` 的 `drawMobFrame(snap,pos,radius)` 统一画。
   → **`combat.py` 的 `classify_mob()` 形状分类可对照**：每种怪的绘制锚点/朝向角 `BASE_FACE_ANGLE=-PI*0.75`、身体半径（ladybug=27.5、soldierAnt=19）。

10. **C++ 服务端平衡常量（`src/Shared/game_config.h`、`stats.h`、`rarity.h`）**：默认怪半径 80、视野 horizon=8192、默认怪速度 400、`mob_velocity_multiplier=1.25`、火蚁伤害×2、白蚁生命×2、白蚁主宰者半径×2.5/速度×0.333、蛛网减速 0.75、开放区稀有度难度 `open_rarity_difficulty_scale=10` + 高斯 σ=0.36。
    → **补 `mob_stats_full.json` / `mob_threat.json`**：这些是"怪之间的相对倍率"，可作为数值权重先验。

### ② 协议/ID映射/中文名等结构化表（含真实样例）

**稀有度编号（1-12，`rarity.h` + `protocol.js`）**：
```
1 Common 普通   2 Unusual 罕见  3 Rare 稀有   4 Epic 史诗   5 Legendary 传说
6 Mythic 神话   7 Ultra 究极    8 Super 超级  9 Eternal 永恒 10 Unique 唯一
11 Primordial 原初  12 Exotic 何异位
```
排序位次（`GetRaritySortRank`）：Exotic=**7.5**，插在 Ultra(7) 与 Super(8) 之间——对应 JS `rarityDisplayOrder=[1,2,3,4,5,6,7,12,8,9,10,11]`。短名 `rarityShortNames=[C,Un,R,E,L,M,U,S,Et,Q,P,Ex]`。

**怪 ID → 中/英（样例，`game_ids.js` L50-94 × `zh-Hans.json` mobs 段）**：
```
1  Beetle 甲虫      13 Bee 蜜蜂      21 Spider 蜘蛛     35 TermiteOvermind 白蚁主宰者
3  NormalLadybug 瓢虫 14 Hornet 黄蜂   19 QueenAnt 蚁后    37 LeafcutterSoldier 切叶兵蚁
7  SoldierAnt 兵蚁   15 BumbleBee 熊蜂 32 FireQueenAnt 火蚁后 38 Titan 泰坦
```

**花瓣 ID → 中/英（样例，`game_ids.js` PetalIconIds × zh-Hans petals 段）**：
```
4 Basic 基本   23 Missile 导弹   37 Stinger 毒刺   40 Leaf 叶子   52 Dandelion 蒲公英
43 Cactus 仙人掌 44 Pollen 花粉   59 Douli 斗笠     60 Trapper 陷阱炮 63 Tomato 番茄
```

**特殊网络实体类型（`protocol.js` L8-14）**：花瓣本体在网络层 = 100+petalType，掉落物 = 180+；特殊 projectile：trap=93、血祭=94、蒲公英导弹=95、花粉=96、蛛网=97、黄蜂导弹=98、传送门=99。

**天赋（`talent_data.js`）**：`TalentId` 1=PetalHealth 花瓣生命 … 17=Movement 移速；移速天赋每稀有度倍率 `{3:1.1, 4:1.2, 5:1.3, 6:1.4, 7:1.5, 8:1.75, 9:2}`（`game.js` L515）。

### ③ 与已偷资产的差异与增量（已有 vs 新增）

> 已偷资产：wasm dump（client.wasm/all_strings/wasm_struct/all_func_consts/petal_extract）、data/ 下 all_mobs.json/all_petals.json/all_talents.json/mob_stats_full.json/mob_hp.json/mob_threat.json/florr_dropchance.json/wasm_map_data.json/maps_list.json/mob_spawn_data.json。

1. **【新增·最大增量】完整掉率真源在 C++ 端**：`src/Shared/drop_rate.h`（99KB，约 1100 行 `RegisterDropRate(mob, mobRarity, petal, petalRarity, rate)`，含 `RollDrops` 按类型独立 roll 的算法）。已偷的 `florr_dropchance.json` 是 wasm 反推结果，这份是**结构化、可直接 parse 的注册表**，且末尾有 `RegisterWikiAntDropRates / RegisterHardcodedHighRarityDropRates / CopyDropRateTable(切叶蚁复制兵蚁的 Wing→白木耳、Glass→黑木耳)` 这类手工修正规则。**建议下一步专门解析此文件**（本任务按约定未逐行转录）。

2. **【新增】二进制线协议逐字段布局**：已偷资产里 `net_protocol.py` 多半是猜的；`protocol.js` 给出权威的快照/槽位/天赋/聊天字节布局与缩放系数，可直接校对。

3. **【新增】不可堆叠花瓣集合（13 个）**：wasm 反推里未必显式标出，这里 `nonStackPetalTypes` 明确列出。

4. **【新增】小地图 40 种地面材质 hex 配色**：可服务于按地面 HSV 判断当前地图/区域。

5. **【新增】怪的视觉绘制参数（viewbox/body radius/各 visual_scale）**：对 `combat.py` 的形状/尺寸识别是一手参考；已偷的 mob 数据偏"数值"，缺"怎么画出来的"。

6. **【差异/注意】稀有度 RGB 两边不完全一致**：`protocol.js`(JS) 的 Exotic 颜色是 `[218,218,218, 170,170,170]`，而 `rarity.h`(C++ 服务端)是 `[180,180,180, 126,126,126]`——以哪个为准需按你对接的实际服务器选。

7. **【没有的东西·别白找】**：前端 JS 客户端**不含**怪血量/伤害/掉率/稀有度尺寸倍率（`RARITY_SIZE_FACTOR` 在前端不存在，尺寸由服务器 radius 下发）。要这些得去 C++ 的 `game_config.h` / `mob.cpp` / `petal.cpp`。本仓库是私服自实现，数值**未必等于官方**，与 wasm dump 对照时以官方 wasm 为准。

---

## 风险/注意（许可证、代码质量、版本差异、不可用部分）

- **许可证**：仓库内 `web/assets/florr/NOTICE.txt` + 自带 `Ubuntu-B.ttf` 字体，根目录未见明确 LICENSE；引用其数据表前需确认授权。README 仅声明 "florr.io-inspired"，是同人/私服实现，**与官方 florr.io 无授权关系**。
- **版本差异**：`flowerTextureVersion="20260802a"`，是 2026-08 的私服版本；怪/花瓣 ID 编号体系与官方 wasm 可能错位（例如这里 beetle=1、ladybug=3、mechaFlower=4、playerFlower=6，召唤体另起 10/11）。对接 `mob_db.py` 的 `TYPE_ID_TO_SID` 时**必须先做映射校准，不能假设序号一致**。
- **代码质量**：前端模块化干净、注释少但常量集中；C++ 端 `game_config.h` 41K token、大量 `inline` 全局可变变量，适合读常量不适合直接移植逻辑。
- **不可用部分**：C++ 服务器源码依赖 VS/MSBuild/CMake，**不可联网/不可运行**（按任务约定只读）；`data/`、`tools/web_client_server.js`（8080 静态+桥服务）仅作协议旁证。
- **诚实声明**：`game.js`（9598 行）我完整读了网络区(839-1238)、常量/导入区(1-531)、客户端命令区(2582-2708)、渲染派发区(6960-7400)；中间 1238-6960、7400-9598 的预测插值/背包 UI/合成面板等**未逐行读**，仅通过 grep 函数清单掌握骨架。`protocol.js/game_ids.js/client_config.js/talent_data.js/zh-Hans.json` 为全文通读；sprite 文件为顶部常量 + 绘制调用 grep，未逐行读像素路径。
