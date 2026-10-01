# florr.io 客户端 wasm 怪物 AI 机制逆向报告

> 分析对象：`client.wasm`（9,410,540 字节，Emscripten 构建）
> 分析方法：Python 手写 wasm section/export/data/code 二进制解析器（`wasm_analyze.py`），提取 6531 个内部函数的 `f64.const / f32.const / i32.const / call` 四类立即数，与数据段字符串池、changelog、spawn 配置做三层交叉印证。
> 重要前提：**该 wasm 不含任何 custom/name 段，46 个导出函数名也全部被压缩为 `Nf/Of/...` 两字母符号**。因此函数级命名无法从二进制恢复，本报告中"函数"一律以**内部序号**（global idx − 361 个导入函数）引用。凡无法定位到具体函数的结论，均标注为"字符串/行为推断"，不编造函数名。

---

## 1. WASM 结构摘要

| section | id | 文件偏移 | 大小 | 说明 |
|---|---|---:|---:|---|
| header | — | 0x000000 | 8 | magic `\0asm` + version 1 |
| type | 1 | 0x00000b | 1,448 B | **181 个函数签名** |
| import | 2 | 0x0005b6 | 2,475 B | **361 个导入函数**（JS 桥，名如 `a.a`~`a._a`），外加 1 table / 1 memory / 1 global |
| function | 3 | 0x000f64 | 6,586 B | **6,531 个内部函数** |
| table | 4 | 0x002920 | 7 B | 1 个 funcref 表 |
| memory | 5 | 0x002929 | 6 B | 线性内存（Emscripten 堆） |
| global | 6 | 0x002931 | 9 B | |
| export | 7 | 0x00293d | 275 B | **46 个导出**（见下表） |
| elem | 9 | 0x002a53 | 14,264 B | 表初始化（call_indirect 目标） |
| code | 10 | 0x006210 | 5,026,796 B | 6531 个函数体，全部成功逐指令解析 |
| data | 11 | 0x4d1601 | 4,358,635 B | **3,650 个数据段**，共 4.33 MB；提取出 84,214 条 ≥4 字符 ASCII 串 |

- **没有 id=0 的 custom 段**：不存在 `name` 段 / `producers` 段 → 无函数名、无局部变量名。
- 函数编号约定：全局 idx 0–360 为导入函数；内部函数 `global = 361 + internal_id`。

### 1.1 导出表（46 个，全部 minified）

| 导出符号 | global idx | internal idx | 桥接来源（client.js 已确认） |
|---|---:|---:|---|
| `Mf` | mem 0 | — | 线性内存（JS 直接读写实体字段） |
| `Nf` | 1684 | 1323 | 未知 |
| `Of` | 361 | 0 | 入口/初始化 |
| `Pf` | 365 | 4 | 未知 |
| `Qf`/`Uf`/`Vf`/`Wf`/`Xf`/`Yf`/`Zf`/`_f`/`$f`/`ag`/`bg`/`cg`/`dg`/`eg`/`fg`/`mg`/`ng`/`og`/`pg`/`sg`/`tg` | 5649–5676 | 5288–5315 | 一批 Wasm→JS 回调 |
| **`gg`** | **5674** | **5313** | **`_Util_GenerateMobImage`**（client.js: `l.gg`） |
| **`hg`** | **5672** | **5311** | **`_Util_GetMobs`**（client.js: `l.hg`） |
| `qg`/`rg` | 1612 | 1251 | 同一函数重复导出 |
| `vg`/`wg`/`xg` | 3765–3767 | 3404–3406 | 未知 |
| `yg`/`zg`/`Ag`/`Bg`/`Cg`/`Dg` | 2793–2799 | 2432–2438 | 未知 |

> 注：`_Util_GetMobs`(internal 5311) 与 `_Util_GenerateMobImage`(internal 5313) 在 wasm 内部**没有任何调用者**——它们只被 JS 层直接调用，用于把 mob 列表/图像数据导出给客户端 UI。真正的 AI 逻辑在 6531 个内部函数内部互相调用。

### 1.2 AI 相关重点函数（按常量特征推断，非命名）

| internal id | 特征常量 | 推断角色 |
|---:|---|---|
| **373** | `[-0.013389, 0.8001, 2000.0]` 且自调用循环 | **全局实体 tick/物理更新主循环**（被几乎所有构造函数间接调用） |
| 366 | `[2.718e-6, -1.98e-4, 8.33e-3, -0.1667]` | sin/cos 泰勒展开（快数学库） |
| 367 | `[2.44e-5, -1.39e-3, 4.17e-2, -0.5, 1.0]` | cos/sin 泰勒展开 |
| 375 | `[1.4]` | 伤害/击退辅助（1.4 是反复出现的碰撞伤害基准值） |
| 3552 | **441 个 f64**（含 `130,100,1.3×8,200, 3.6,243,0.0137, 1.38×8`） | 最大的实体构造函数——疑似**蚂蚁女王/白蚁超脑/assembler 类多部件 Boss** 或花园默认模板 |
| 1641 | 344 个 f64 | 大型多部件实体（疑似 jellyfish/hornet 弹幕模板） |
| 1603 | 306 个 f64（含 `-inf`×4、`-0.0306`×4、`2220000`、`1000`） | 含"无限"生命周期标记的实体（疑似 ultra/超级 Boss 或投射物） |
| 1597 | 263 个 f64（含 `1.1,1.4286,0.8333` RGB 衰减表） | 带渐变的实体（疑似 sandstorm 沙暴） |
| 441–446 | 20 元素数组 `[1.15/1.38/1.1, 1.0, ... 1.3225 ...]` ×2 组 | **稀有度倍率表**（hp/速度/伤害随 10 档 rarity 缩放） |
| 752 | `[3.1, 2.5, 0.6×4, 3.1, 2.5, 0.6×4]` | 某怪的速度/加速度参数对 |

---

## 2. 怪物名册与生成系统（字符串证据）

### 2.1 已破译的怪物种群（85 个，来自 i18n key `Mobs/<id>/...`）

```
ant_baby ant_egg ant_hole ant_queen ant_soldier ant_soldier_diver ant_worker
assembler barrel bee beetle beetle_hel beetle_mummy beetle_nazar beetle_pharaoh
bubble bumble_bee bush cactus centipede centipede_body centipede_desert
centipede_desert_body centipede_evil centipede_evil_body centipede_hel
centipede_hel_body crab crab_mecha crystal dandelion digger dummy
fire_ant_baby fire_ant_burrow fire_ant_egg fire_ant_queen fire_ant_soldier
fire_ant_worker firefly firefly_magic fly gambler garbage ghost hornet
jellyfish ladybug ladybug_dark ladybug_shiny leafbug leafbug_shiny leech
leech_body mantis mecha_flower moth oracle roach rock sandstorm scorpion
shell silverfish spider spider_hel spider_mecha sponge square starfish
termite_baby termite_egg termite_mound termite_overmind termite_soldier
termite_worker titan tomb trader wasp wasp_hel wasp_mecha worm worm_guts
```

> 已知静态怪 type id 1–83 与上述名册一一对应（用户已破译）。

### 2.2 生成权重表（数据段内嵌 JSON，共 81 条）

生成表格式为 `"value":"<mob_id>:<weight>;"`，直接嵌在 data 段。代表性样本：

| 区域/子区 | 权重表 |
|---|---|
| 蚂蚁洞 T1 | `ant_baby:1;ant_worker:1;ant_soldier:8;worm:0.3;` |
| 蚂蚁洞 T2 | `ant_baby:1;ant_worker:2;ant_soldier:7;worm:0.3;` |
| …（T3–T7 按梯度递减 soldier 权重） | |
| 火蚁洞 | 同构，`fire_ant_*` 系列 |
| 白蚁洞 | `termite_*` 同构 |
| 沙漠 | `cactus:1;sandstorm:1;desert:1;` / `cactus:1;ladybug_shiny:0.025;desert:1;` |
| 海洋 | `bubble:3;jellyfish:1;sponge:0.5;ocean:1;` / `starfish:3;jellyfish:1;bubble:1;ocean:1;` |
| 下水道 | `sewers:1;garbage:1;` / `sewers:1;moth:0.25;` / `sewers:1;roach:1;` |
| 机械区 | `mecha_flower:1;wasp_mecha:4;spider_mecha:4;crab_mecha:2;barrel:0.2;` |
| 精英 | `beetle_hel:3;wasp_hel:1;spider_hel:1;centipede_hel:0.1;` |
| 单怪 ultra | `assembler:1;` / `gambler:1;` / `titan:1;` |

### 2.3 生成器配置 schema（data 段 `"name":"..."` 键）

```
density, difficulty, extra_spawn_delay, faction, force_rarity, level, map,
max_interval, min_interval, mobs, mobs2, once, overlay, sub_area, team,
type, warp_point, force_player_collisions, force_minimap_collisions, respawn
```

- `min_interval / max_interval`：刷新间隔（秒，f32/f64）。
- `density`：该区域同屏怪物密度上限。
- `extra_spawn_delay`：额外生成延迟（用于 egg/burrow 类）。
- `once`：该生成点是否只触发一次（ultra/Boss 用）。
- `force_rarity / max_rarity`：强制稀有度（如 "Ant holes can no longer have a rarity higher than Rare" — changelog）。
- `faction / team`：阵营系统（敌对/友方/召唤物）。
- `force_player_collisions`：是否强制与玩家碰撞（changelog: "Re-enabled player collisions in most cases"）。

---

## 3. 怪物 AI 行为结论（按目标逐项）

### 3.1 移动目标选择 / 追踪

**已确认（changelog 字符串证据）：**
- 怪物分三档攻击性：**aggressive / semi-aggressive / passive**（changelog: "Aggressive and semi-aggressive mobs will run away if attacked by an entity that it can't attack back (behind wall, underground, etc)"）。
- **仇恨范围 ≠ 攻击范围**：changelog 明确 "Enemies no longer have their attack range the same as their aggro range (so hornets for example won't start attacking from half way across the map)"。即每个实体有两个半径：进入 aggro 范围开始追，进入 attack 范围才出手。
- **仇恨范围随存活时间增长**：changelog "Mob aggro range now constantly increases while they're alive"。
- **波次结束时全体仇恨**：changelog "incentivize clearing mobs before the wave ends by making all mobs aggro when it ends"。
- **无法反击时会逃**：aggressive/semi 怪被墙/地下等打不到的实体攻击时会逃跑（flee 状态存在）。

**常量证据（构造函数层）：**
- 几乎每个实体构造函数都出现 `120.0, 0.0, 1.0` 三元组——推断为默认最大速度 120（px/s 量级）、初速 0、加速度系数 1.0。
- 主物理循环 func 373 内含 `-0.013389` 与 `0.8001`：即**速度阻尼 ≈ 每帧 1.34% 衰减**（等价 `v *= (1 - 0.0134)`），实体没有持续推力时约 0.5s 内停下。
- 弹幕/分身构造函数中反复出现角度常量对：`6.2832`(2π)、`±1.5708`(π/2)、`±3.1416`，以及扇形角偏移数组 `[-0.315,-0.105,0.105,0.315]`（func 5830）、`[-0.7,-0.233,0.233,0.7]`（func 5681）——这些是**远程怪的开火角度模板**（扇形/环形弹幕）。

> 未找到"巡逻/固定路线"的独立字符串证据；从构造函数常量看，普通怪的移动模型是"朝目标点加速 + 阻尼"，没有路径点表。**巡逻行为未找到可靠数据**。

### 3.2 仇恨（Aggro）建立 / 转移 / 丢失

- 字符串证据：`Petal/Attribute/MobAggroRange=<...>Mob Aggro Range:</c> -{0:perc}%` —— 玩家花瓣（如 bulb 灯）可以**降低**怪物对自己的仇恨百分比；`Petals/bulb/Description=A shiny lightbulb. Draws aggro from mobs` —— bulb 是**嘲讽（拉怪）**道具。
- 仇恨丢失：changelog 未直接说"脱战回血/丢失目标"，但 "Aggro range increases while alive" 说明仇恨半径是单调递增的运行时字段（存在实体的 f64 字段上，每 tick 加大）。
- 阵营：`faction/team` 字段存在；召唤物（summoner petal）有独立碰撞规则（changelog: "Summoned mobs no longer have collision with other squad mobs. Summoned mobs now deal collision damage to non-squad friendly mobs"）。

### 3.3 攻击触发条件

- 触发条件 = 距离 ≤ attackRange（与 aggroRange 分离，见 3.1）。
- 近战碰撞：构造函数反复出现 `-1.4, 0.5` / `1.4, 0.5` 二元组——推断为**碰撞伤害 1.4、碰撞击退 0.5**（基准值，随 rarity 乘 1.15/1.38 等系数表缩放）。
- 远程：func 4330/5341/4368/4277/4302 等"弹幕模板"函数含 `0.01, 6.2832, -1.5708, 1.0, 50.0` 等——即开火间隔 0.01 rad/frame 旋转、扇形 ±π/2、弹幕射程 50。
- Hornet 特例：changelog "Fixed Hornet not receiving knockback when firing missiles" + "Mobs missile health now scale like petal health" —— **hornet 的导弹是有独立 HP 的实体**（func 1603 内含 `-inf` 生命周期、`-0.0306` 衰减，疑似导弹/穿透弹幕）。

### 3.4 攻击模式分类（从模板函数常量推断）

| 模式 | 证据 |
|---|---|
| 近战冲撞 | `1.4/0.5` 碰撞对，无角度数组（func 375 辅助） |
| 扇形弹幕 | 角度偏移数组 4–6 个角（func 5830, 5681, 5800, 5818） |
| 环形弹幕 | `6.2832` 整圆多次（func 4368, 272） |
| 定向导弹 | 含 `-inf`/`9.22e18`（u64 max）生命周期的长程实体（func 1603, 1596） |
| 多部件 Boss | func 3552/1641/1603 含数十个 `-1.4,0.5` 碰撞对 + 角度对 |

### 3.5 特殊能力（按种群）

| 怪物 | 证据 |
|---|---|
| **ant_queen / fire_ant_queen / termite_overmind** | 生成表独立 `:1`；changelog 蚂蚁洞分层权重；func 3552 多部件构造 |
| **assembler** | 独立 ultra 生成表 `"assembler:1;"`；无独立特殊字符串，**特殊能力细节未找到可靠数据** |
| **gambler** | `"gambler:1;"` + 孵化文案 `"You hear someone whisper faintly... just... one more game..."` |
| **titan** | `"titan:1;"` + 闲聊文案 "The Worldsmith wanders" |
| **sandstorm** | changelog: "Sandstorm now phases through non-flower entities (still deals damage normally)" + "We're slowly adding special moves to every Ultra+ mob. So far, Sandstorm and Shell got new moves" —— **沙暴可穿透非玩家实体、有专属新招式** |
| **shell** | 同上，有专属新招式（细节未在常量中定位） |
| **leech / leech_body** | changelog: "Leeches now share their health among all segments" —— 节段共享 HP |
| **centipede / *_body** | 节段式（desert/evil/hel 三种变体），主体+身体段 |
| **scorpion** | 存在于名册，**独立函数未定位** |
| **ghost** | 存在于名册（`"name":"ghosts"` 生成键），**能力未找到可靠数据** |
| **cactus** | changelog: "Cactus no longer turns poisonous at higher rarity, more health instead" —— 老版本高稀有度仙人掌带毒，已改为加 HP |
| **beetle** | changelog: "Changed the way beetles move" —— 移动模型与普通怪不同（未定位具体函数） |
| **firefly / firefly_magic** | 独立生成表 `"firefly:1;mantis:1;jungle:1;"` |
| **egg / burrow / mound** | changelog: "Eggs now only spawn mobs when they break" + `extra_spawn_delay` 字段 |

---

## 4. 移动/速度/物理常量表

| 常量值 | 出现次数 | 推断含义 | 证据 |
|---:|---:|---|---|
| `120.0` | 极高频（几乎所有构造函数） | 默认最大速度（px/s 量级） | 构造函数三元组 `120.0,0.0,1.0` |
| `-0.0134` | 高频 | 每帧速度阻尼 1.34% | func 373（主物理循环）含 `-0.013389` |
| `-0.0063` / `-0.0214` / `-0.0306` / `-0.0416` | 各数十次 | 不同实体类的阻尼/衰减档位 | 构造函数常量 |
| `0.9999 / 0.0001` | 高频 | 计时器/生命周期衰减尾项 | 构造函数 |
| `1.4 / 0.5` | 高频 | 碰撞伤害基准 / 击退基准 | func 375 `[1.4]` |
| `1.15` / `1.38` / `1.1` | 多组 | rarity 缩放系数（hp/速度/伤害） | func 441–446, 503 |
| `1.3225 = 1.15²` | 多次 | 二阶 rarity 乘积 | func 441 |
| `6.2832 / 3.1416 / 1.5708` | 高频 | 2π/π/π/2 角度模板 | 弹幕构造函数 |
| 扇形角 `±0.105/±0.315/±0.233/±0.7` | 数十次 | 远程开火扇形角偏移 | func 5830/5681/5681 |
| `1000.0` | 127 次 | 默认仇恨/攻击/脱战半径上限 | 构造函数常量 |
| `2000.0` | 多次 | 视距/渲染或 ultra 索敌半径 | func 373 |
| `3.1 / 2.5 / 0.6` | 成对 | 某怪速度/加速度档 | func 752 |
| `-0.055 / -0.0894` | func 1596/3455 | 特殊实体（web/减速区）的场衰减 | 构造函数 |

> 注：wasm_floats.txt 中 `0x4e0819 = 535568.22` 等大值是**地图坐标**（data 段/坐标立即数），不是 AI 常量； moderate 常量主要是上述角度与阻尼。

---

## 5. 伤害结算机制

### 5.1 已有字符串证据

- `Petal/Attribute/ArmorDebuff=<...>Armor Debuff:</c> {0:tooltip}` —— **护甲减益**作为可施加 debuff 存在（降低目标护甲）。
- `Petal/Attribute/CollisionDamageResistance=<...>Collision Damage Resistance:</c> +{0:perc}%` —— **碰撞伤害抗性**是百分比减伤。
- `Petal/Attribute/FlowerKnockback=<...>Flower Knockback:</c> +{0:tooltip}` —— 花（玩家）击退加成。
- `Mob/Attribute/Bounces=...Bounces:` —— 弹幕弹跳次数属性。
- changelog: "Increased base poison damage rate to **15/s** (from 9/s)"；"Poison from different players against the same mob now stack"；"Fixed poison deaths being mislabeled"。
- changelog: "Web no longer stacks, **slow increased to -75%**"；"Web movement speed debuff changed from -75% to -50%"；"Web rarity now affects radius rather than duration"。
- changelog: "Higher tier mobs now have varying amounts of **slow resistance**"；"Slows effectiveness will depend on mob vs petal rarity"。
- changelog: "Salt... **Reflected damage is reduced by 75% against flowers**"。
- changelog: "Doubled most Ultra+ mobs HP"；"Rebalanced... offensive and defensive types... changes how their damage and health scales"。

### 5.2 推断的公式（常量层）

- **碰撞伤害**：`dmg = 1.4 × rarity_mult[rarity] × CollisionDamageResistance减伤`（func 375 基准 1.4，rarity 倍率 1.15/1.38 等表）。
- **护甲 Armor**：存在 ArmorDebuff 属性字符串 → 怪物有护甲字段，可被 debuff 降低；具体减伤百分比公式**未在常量中定位**（可能是线性 `dmg × (1 - armor/(armor+k))`，但无证据，标注"未找到可靠数据"）。
- **弹幕伤害**：每个弹幕实体自带 HP（hornet 导弹按 petal HP 缩放），与怪物 HP 分离。
- **暴击**：**未找到 crit/暴击字符串证据**（i18n 中无 Crit 键），按"未找到"处理。
- **毒**：15 dps，多玩家叠加。
- **减速**：基数 -75%（web），高稀有度怪有 slow resistance，实际效果按怪/花瓣 rarity 差缩放。

---

## 6. 防无敌 / 平衡机制

| 机制 | 证据 |
|---|---|
| 波次推进 | changelog: "Next wave will now start once current wave has **4 or fewer mobs alive**" |
| 刷空保护 | changelog: "An area can now temporarily run out of mobs if they're farmed too quickly" |
| 仇恨随时间增长 | changelog: aggro range constantly increases while alive |
| 波末全体仇恨 | changelog: making all mobs aggro when wave ends |
| Ultra 唯一性 | changelog: "There can still only be one Ultra of each type at a time in the realm" + "global per-realm timer" |
| Super 概率 | changelog: "Ultra mobs now have a 1% chance of spawning as Super" |
| Luck 影响 | changelog: "Luck now affects mob spawns again, increasing the rarity of mobs that spawn" |
| 掉落保护 | changelog: "Drops... shared among the 4 players that dealt the most damage (≥5% damage)" → "Ultra+ damage threshold decreased from 5% to 1%, 4→15 players" |
| 召唤物碰撞 | changelog: summoned mobs 不与同队怪碰撞，但对非队友友方怪造成碰撞伤害 |
| 玩家碰撞 | `force_player_collisions` 字段；changelog "Re-enabled player collisions in most cases" |
| 地图缩放 | changelog: "Map now scales based on the mobs contained within"；late-game waves "significantly shorter" |

---

## 7. 对自动寻路/战斗插件的初步启示

1. **仇恨是两阶段半径**：进入 aggroRange 怪物开始追，进入 attackRange 才攻击。插件可利用"站在 attackRange 外、aggroRange 内"风筝（changelog 明确分离）。
2. **怪物存活越久仇恨越大**：长时间拉扯同一群怪会让仇恨半径单调增大——不要在一只怪上拖太久，优先击杀。
3. **波末所有怪会主动冲玩家**（all-aggro）：最后 4 只以下时不要继续刷远，准备接怪。
4. **bulb 灯可拉怪、MobAggroRange 花瓣可减仇恨**：战术上可用灯拉仇恨绕开精英。
5. **沙暴 sandstorm 穿透非玩家实体**：不能用小怪当掩体；它对玩家仍造碰撞伤害。
6. **hornet 导弹有独立 HP**：可以用花瓣/碰撞打掉导弹（changelog: missiles scale like petal HP）。
7. **节段怪 leech/centipede 共享 HP**：打哪段都一样，优先切最近段。
8. **高稀有度怪有减速抗性**：web 控制对高 rarity 怪效果衰减。
9. **毒伤 15/s 可叠加**：多毒源优于单次爆发。
10. **召唤物不对同队怪碰撞**：自己的召唤物不会卡位，但会打中立怪。

---

## 8. 证据缺口（诚实标注）

- **函数名**：wasm 无 name 段，全部 6531 函数只有内部序号；本报告未编造任何函数名。
- **巡逻/路径点**：未找到路径表字符串。
- **assembler / scorpion / ghost 的独立特殊能力**：未在常量中定位到专属构造函数。
- **护甲减伤精确公式、暴击机制**：未在字符串或常量中找到可靠证据。
- **aggroRange 与 attackRange 的具体数值表**：常量池中大量 `1000.0` 可能是默认上限，但每类怪的具体数值需要逐构造函数人工对照实体字段偏移才能确认（需动态调试/断点，超出本次静态分析范围）。

---

### 附：本次分析生成的中间文件

- `wasm_analyze.py` —— 手写 wasm 解析器（section/export/data/code 全量）
- `wasm_struct.json` —— 导出表、导入表、字符串→函数交叉引用
- `all_func_consts.json` —— 6531 函数的 f64/f32/i32/call 立即数全量
