# florr.io 三领域调研报告（服务于 florr-auto-pathing 挂机插件）

> 调研日期：2026-09-26
> 目标插件：`C:\Users\intel\Downloads\florr-auto-pathing-main`（Python 屏幕取色 + Lazy Theta* 巡逻 + 自动战斗/躲弹/低血切回血/自动复活）
> 原则：不编造数值；查不到的标「未找到可靠数据」。同人复刻版（洛谷 U458201 等）的数值**不作为**真实游戏依据。

---

## 领域 1：天赋 / 技能加点

### 核心事实（带数值）

- **打开方式**：游戏内按 `X` 键打开天赋树。旧称 "Skill"，2023-12-08 起改名 "Talent"。
- **天赋点（TP）获取**：
  - **每升 1 级固定给 1 TP**（changelog 2023-02-10：「Changed TP reward per level (now it's always 1 per level)」）。
  - 等级上限 200（2022-11-29 设定）。
  - **2024-05-08 等级需求翻倍、玩家等级减半**，同时新增成就（Achievements），成就给 TP 以补偿被砍掉的等级 TP。即：现在 TP = 升级（1/级）+ 成就奖励。
- **洗点**：
  - 2024-06-02 起**免费、无限次、无冷却**洗点（changelog：「Talents can now be reset for free an unlimited amount of times without delay」）。
  - 历史：2022-12-11 花 5 级退款 → 2023-12-08 每 30 天免费一次 → 2024-06-02 起免费无限。**插件无需为洗点成本做任何判断。**
- **已删除的天赋分支**（重要，别再照着老攻略点）：
  - **合成系天赋（Crafting talents）已于 2024-05-22 移除**（changelog）。
  - **回收天赋（Salvaging）已于 2024-04-21 移除**。
- **Luck（幸运）天赋**：2022-12-26 被移除退款 → 2023-12-08 重新启用 → **2025-10-14 起再次影响刷怪稀有度**（changelog：「Luck now affects mob spawns again, increasing the rarity of mobs that spawn in that area」）。

### 天赋树结构与数值（主力分支）

> 数值来源：韩国 namu.wiki《Florr.io》条目，最后修订 2026-08-12。每档为「上一档 → 本档」的效果与该档所需 TP。

**(1) Loadout（槽位）——最优先，共 45 TP**

| 档位 | 可装备花瓣数（基础 5） | 该档 TP |
|---|---|---|
| Common | 5 → 6 | 3 |
| Unusual | 6 → 7 | 6 |
| Rare | 7 → 8 | 9 |
| Epic | 8 → 9 | 12 |
| Legendary | 9 → 10 | 15 |

- 侧枝（挂在 Loadout 上）：**Antennae、Reach、Duplicator、Magnetism**。

**(2) Reload（冷却/装填）——挂机 DPS 核心，共 162 TP**

| 档位 | 装填速度减少 | 切花速度减少 | 该档 TP | 参考 Stinger（基础 10s） |
|---|---|---|---|---|
| Common | 0% → −10% | 2.5s → 2s | 6 | 10→9s |
| Unusual | −10% → −19% | 2s → 1.5s | 9 | 9→8.1s |
| Rare | −19% → −27.1% | 1.5s → 1s | 12 | 8.1→7.29s |
| Epic | −27.1% → −34.39% | 1s → 0.5s | 15 | 7.29→6.56s |
| Legendary | −34.39% → −47.51% | 0.5s → 0s | 18 | 6.56→5.25s |
| Mythic | −47.51% → −58.01% | — | 21 | 5.25→4.2s |
| Ultra | −58.01% → −66.41% | — | 24 | 4.2→3.36s |
| Super | −66.41% → −73.13% | — | 27 | 3.36→2.69s |
| Eternal | −73.13% → −81.19% | — | 30 | 2.69→1.88s |

**(3) Health（花朵血量）——生存向，共 122 TP**

| 档位 | 血量提升 | 该档 TP |
|---|---|---|
| Common | 100% → 130% | 2 |
| Unusual | 130% → 169% | 5 |
| Rare | 169% → 220% | 8 |
| Epic | 220% → 286% | 11 |
| Legendary | 286% → 371% | 14 |

（更高档数值 namu 未完整列出 → 未找到可靠数据。）

**(4) Medic（治疗加成）——配合回血花瓣，共 126 TP**

| 档位 | 治疗效果提升 | 该档 TP |
|---|---|---|
| Common | 100% → 115% | 2 |
| Unusual | 115% → 132.25% | 5 |
| Rare | 132.25% → 152.09% | 8 |
| Epic | 152.09% → 174.9% | 11 |
| Legendary | 174.9% → 201.14% | 14 |
| Mythic | 201.14% → 231.31% | 17 |
| Ultra | 231.31% → 266% | 20 |
| Super | 266% → 305.9% | 23 |
| Eternal | 305.9% → 404.56% | 26 |

**(5) Petal Health（花瓣血量）——共 90 TP**：每档约 ×1.15（Common 100→115%，Eternal 305.9→404.56%），TP 2/4/6/8/10/12/14/16/18。对高血量花瓣（Corn、Moon Rock）收益大；对 1 血花瓣无效。

**(6) Duplicator（重瓣/分裂）——共 100 TP**

| 档位 | 效果 | 该档 TP |
|---|---|---|
| Legendary | 多段花瓣 +1 段（蚁卵 4→5） | 10 |
| Ultra | 多段花瓣再 +1 段（5→6） | 20 |
| Super | Loadout 最左花瓣 +1 段（对 Bone 等单段花瓣也生效；不对 Unique/Eternal 生效） | 30 |
| Eternal | 上述效果对 Unique/Eternal 也生效 | 40 |

**(7) Magnetism（磁吸天赋）——单档 Mythic，15 TP**：活着时拾取范围 +1000，与 Magnet 花瓣叠加。省一个花瓣槽。

**(8) 其他分支（效果方向已知，逐档数值未找到可靠数据）**：
- **Petal Rotation（花瓣转速）**：后期主力点，用 Wing 点满、用 Missile 点 2 档即可（洛谷/B 站玩家经验）。
- **Reach（花瓣延展/范围）**：扩大花瓣环绕半径。
- **Vision（视野）**：扩大屏幕反应范围（B 站 FNRC 攻略建议 Lv10 点第一档）。
- **Recover（自我痊愈）/ Armor（护甲）/ Cutter（碰撞伤）/ Knockback（击退）/ Antitoxicity（抗毒）/ Evasion（闪避）/ Second Chance（二次机会）**：方向见玩家配装帖，**逐档精确数值未找到可靠数据**（同人复刻表 1/3/5/7/10 等数字不能当真）。

### 加点推荐表（挂机向）

| 流派 | 优先级顺序 | 适用场景 |
|---|---|---|
| **通用挂机（推荐默认）** | ① Loadout 全点到 10 槽 → ② Reload 点到 Mythic（−58%）→ ③ Health 点到 Epic → ④ Medic 点到 Legendary → ⑤ Magnetism（15 TP）→ ⑥ 富余再补 Rotation/Reach/Vision | 插件巡逻 + 自动切回血，稳字当头 |
| **纯攻击流（抢伤害/冲 DPS）** | ① Loadout 10 槽 → ② Reload 点满 → ③ Duplicator（召唤/多段花瓣）→ ④ Rotation → ⑤ Health 只点 2~3 档 | 翅膀流/三角轮/召唤流，打能秒的同级怪 |
| **防御/回血流（长时挂机不回城）** | ① Loadout 10 槽 → ② Health 点满 → ③ Medic 点到 Ultra → ④ Petal Health → ⑤ Magnetism → ⑥ Reload 只到 Rare | 骨轮/召唤挂机、高 M 区、低血自动逃跑阈值以下硬扛 |

> 升级节奏（B 站 FNRC 攻略，2026-07）：Lv4 点出 6 槽 → 开始点转速 → Lv10 点 7 槽 + 第一档 Reach + 第一档视野 → Lv18 点 8 槽 → Lv22 点 9 槽 → Lv30 点 10 槽，其余优先转速。

### 对自动挂机插件的影响与建议

1. **洗点免费无冷却**：插件可以在「换地图/换流派」时毫无成本地建议玩家洗点——例如沙漠刷怪用攻击流，切到 Hell 刷 Gambler 前手动洗成防御回血流。无需在代码里做洗点冷却判断。
2. **Loadout 槽位 = 插件回血槽扫描的前提**：`config.py` 里 `HEAL_NAMES` 支持到 10 槽，但玩家若 Loadout 没点满到 10，副槽数量会少。建议启动时扫描实际可用槽位数，避免往不存在的槽位切回血。
3. **Magnetism 天赋 ≈ 省一个 Magnet 花瓣槽**：如果玩家点了 Magnetism（+1000 拾取范围），插件就不必再在副槽留 Magnet，可多塞一个回血花瓣——建议在回血槽扫描时提示玩家「已有点磁吸天赋可省槽」。
4. **Reload 档位直接影响插件「能秒杀等级」设定**：插件靠 `kill_rank` 配置贴脸追怪。Reload 点到 Mythic 后 DPS 显著提升，建议在 `ask_config` 里加一句提示：「Reload 到 Mythic 后可把秒杀等级上调一档」。
5. **别再点合成系天赋**：老攻略（洛谷 025awfha、ga5lo773）里的「合成成功率天赋/skilled crafting」已于 2024-05-22 删除，插件 README 的配装提示若引用了这些需删除，避免误导玩家白洗点。

### 来源 / 时间 / 时效

- 官方 changelog：https://florr.io/static/i18n/en_US/changelog.txt （抓取于 2026-09-26，最新条目 2025-12-21）
- namu.wiki 天赋数值表：https://namu.moe/w/Florr.io （修订 2026-08-12）
- B 站 FNRC 加点节奏：https://www.bilibili.com/video/BV1GpKA62Erv/ （2026-07-18，玩家经验，非官方）
- 洛谷流派分析：https://florrio.fandom.com/zh/wiki/策略/流派分析 （修订 2026-08-23）
- ⚠️ 过时标注：2023 年及更早洛谷攻略里的「合成天赋+成功率」「花 5 级洗点」「30 天洗点」均已失效。

---

## 领域 2：合成 / 升级机制

### 核心事实（带数值）

- **基础合成（Craft）**：按 `C` 打开，**放 5 张同种、同稀有度花瓣**，尝试升 1 级稀有度。
  - **成功**：产出 1 张下一稀有度花瓣。
  - **失败**：**随机毁掉其中 1~4 张**（不全部销毁）。
  - Shift+点击一次性放入所有同类；Alt+点击连赌 5 次。
- **成功率表**（当前版本，无合成天赋——因为该天赋已删除）：

| 合成路线 | 成功率 | 期望消耗（张/成品，约） |
|---|---|---|
| Common → Unusual | **64%** | ~8 |
| Unusual → Rare | **32%** | ~16 |
| Rare → Epic | **16%** | ~31 |
| Epic → Legendary | **8%** | ~63 |
| Legendary → Mythic | **4%** | ~125 |
| Mythic → Ultra | **2%** | ~250 |
| Ultra → Super | **1%** | ~500 |
| Super → Eternal | **0.1%** | 极高 |

  - 数据来源：ashish.top（2026-04-28）、洛谷 5fvdv4g0（2024-04，Rare→Epic 写 20%，与 16% 略有出入，以 64/32/16/8/4/2/1/0.1 的等比递减为准）。
  - **Super / Eternal 只能靠合成获得，不掉落**；合成 Super 会全服公告。
  - **伪随机（失败递增保底）已于 2022-10-20 移除**，现在是真随机（changelog：「Pseudo-RNG system has been removed from crafting. Now it's back to truly random」）。
- **Unique（唯一）锻造**：丛林 **Titan** 用 **5 张 Super 锻造 1 张 Unique**。
  - **2025-11-26 重做**：固定 5 Super 锻造；但若别人锻造了同一种 Unique，你会永久损失其中 1 张 Super；每种花瓣有全局冷却防秒偷。
  - 每种 Unique 全服同时只能存在一张。

### Absorb（吸收/融卡）——2025 年 12 月回归

- **历史**：
  - 2022-11-29 加入「吸花瓣换经验」。
  - 2024-04-20 宣布将移除；**2024-04-21 正式移除 Absorb 与 Salvaging 天赋**，改为杀怪给经验。
  - **2025-12 中旬回归**：花园出生点旁新开**水晶室（Crystal Room）**传送门（changelog 2025-12-21 提到「花园裂开一道神秘裂隙，把花带回更简单的时代」）。
- **新机制**：
  - 吸收花瓣换经验，**但每次消耗水晶能量**；水晶能量随时间自动回复。
  - **升级提高能量上限**。
  - **Lv142 以上才能吸收 Super 花瓣**（B 站视频 BV1samQBuEoX、BV125meBoE6f，2025-12）。
  - 插件地图里已有 `crystal_room.tmj` / `maps/crystal_room.png`，说明作者已预留此地图。
- **吸收经验值表**（洛谷 udskrh3b，2024-04 旧版数据；**水晶室回归后数值可能已调整，标注为「旧版参考」**）：

| 花瓣稀有度 | 吸收经验 |
|---|---|
| Common | 1 |
| Unusual | 5 |
| Rare | 50 |
| Epic | 500 |
| Legendary | 10,000 |
| Mythic | 500,000 |
| Ultra | 50,000,000 |

  - Basic 花瓣不提供经验；剩余花瓣数 ≤ 槽位数时不可继续吸收。

### 稀有度提升规则

- 稀有度梯度（低→高）：Basic → Common(绿) → Unusual(黄) → Rare(蓝) → Epic(紫) → Legendary(红) → Mythic/青 M → Ultra/粉 U → Super → Eternal(永恒) → Unique(唯一)。
- **花瓣升级经验体系**：花瓣本身有「强化等级」（吸卡/合成喂大），稀有度提升时强化等级清空（见旧规则文档）；当前版本花瓣数值随稀有度指数膨胀，高一级怪血量 ×3.6~46（README 已引用）。
- **Factory（工厂，2025-02-23 加入）的 Assembler/重构机**：跨花瓣类型转化，配方**轮换**（不是固定的）。已知配方（B 站 factory 更新一览，2025-03-01；HFOJ 补充，2026-08）：

| 输入 | 输出 |
|---|---|
| ×10 Air | ×1 Bubble |
| ×1 Moon | ×25 Rock |
| ×3 Battery | ×1 Battery + ×1 Lightning |
| ×1 Glass | ×1 Sand（反向 ×1 Sand→×1 Glass 也成立）|
| ×3 Honey | ×1 Wax |
| ×1 Glass + ×1 Battery + ×1 Bulb | ×2 Laser |
| ×1 Fragment + ×1 Magnet + ×1 Glass | ×1 Compass |
| ×1 Leaf + ×1 Uranium | ×1 Monstera |
| ×1 Antennae + ×1 Bulb | ×1 M…（HFOJ 截断，未找到完整）|

  - 注：B 站另有「重构机所有配方（至 2 月 26 日为止）」视频（BV1dYPLegEdw），说明配方会随版本增减，**上表非全量**。

### 对自动挂机插件的影响与建议

1. **别自动赌合成**：成功率 4%/2%/1% 且失败毁 1~4 张，插件若自动合卡等于随机烧卡。README 已强调「刷同级怪直接拿掉落」，与官方建议一致——保持只刷不赌。
2. **水晶室挂机 = 自动吸卡练级**：插件已有 crystal_room 地图。可加一个「水晶室模式」：自动走到水晶旁，当能量满时按 A 吸掉背包里多余的低稀有度花瓣（Common/Unusual），能量空了回主地图继续刷怪。**注意 Lv142 才能吸 Super，低于此级别尝试吸 Super 卡。**
3. **重构机 Glass→Sand 是 DPS 毕业路线**：维基 DPS 攻略建议「黑蚁地狱刷 Mythic 玻璃（别合 U）→ 工厂找重构机玻璃换沙子」。插件若要服务毕业，可加一条「anthell 刷 glass → 路由到 factory 换 sand」的任务链，但配方轮换需人工确认后写死坐标。
4. **Unique 锻造有「被抢永久损失 1 Super」风险**：插件/玩家不应在高活跃时段自动走 Titan 锻造，避免刚砸 5 Super 就被别人 forge 走一张。
5. **掉落门槛**：changelog 2023-02-14 把 Ultra+ 掉血阈值从 5% 降到 1%，最多 15 人同分掉落。插件 `leech`（蹭 2.5 秒混伤害）阈值 1% 是对的，保持。

### 来源 / 时间 / 时效

- 官方 changelog：https://florr.io/static/i18n/en_US/changelog.txt （最新 2025-12-21）
- 成功率表：https://ashish.top/blog/florrio-crafting-explained/ （2026-04-28）；洛谷 https://www.luogu.com/article/5fvdv4g0 （2024-04-17）
- Absorb 回归（B 站，玩家实测）：https://www.bilibili.com/video/BV125meBoE6f/ （2025-12-14）、https://www.bilibili.com/video/BV1samQBuEoX/ （2025-12-13）
- 吸收经验旧表：https://www.luogu.com/article/udskrh3b （2024-04-17，⚠️ 水晶室回归后可能已改）
- 重构机配方：https://www.bilibili.com/opus/1037584100702027782 （2025-03-01）
- ⚠️ 过时标注：2023 年洛谷帖里「skilled crafting +20/40/60% 成功率」已随合成天赋删除而失效。

---

## 领域 3：商店 / NPC

### NPC 功能对照表

| NPC | 所在地图 | 功能 | 消耗 / 冷却 | 刷新/位置 |
|---|---|---|---|---|
| **Trader / 商人** | 沙漠（Desert） | **1 张花瓣 → 同稀有度 Coin（硬币）**；Corruption 花瓣也能拿来交易。Unique/Eternal **不能**换。 | **24 小时冷却** | 会游荡，固定刷点在沙漠右下圆圈附近，可能跑到 S 区；外观像一朵花瓣全是金币的花 |
| **Oracle / 神使** | 海洋（Ocean），出生点往下一点 | **保证合成必定成功**（不赌概率） | 需**更多材料**，**28 分钟冷却** | 固定 NPC |
| **Titan / 锻造台** | 丛林（Jungle） | **5 张 Super → 1 张 Unique**（唯一获取途径） | 5 Super；2025-11-26 后有全局冷却 + 被抢永久损失 1 Super | 固定 |
| **Assembler / 重构机** | 工厂（Factory） | 按**轮换配方**跨类型转化花瓣（见领域 2 配方表） | 按配方消耗 | 固定机器 |
| **Gambler / 赌徒** | 冥界 / Hel | **可被击杀的 NPC 生物**，掉落 Corruption、Chip、Card、Dice、Domino | — | 冥界到处游荡，随机移动 |
| **Premium Shop / 主菜单商店** | 主菜单左上角 | 用 **Stars（星星）**直接买花瓣；Stars 靠广告或充值（2024-04-01 起广告对全员关闭但仍照常发 Stars） | Stars | 常驻；2023-12-02 曾全店 5 折 |

### 赌徒（Gambler）与「腐化 2% / 98.4%」含义

- **腐化（Corruption）** 是 2024-08-27/28 加入的功能型花瓣：无伤害无耐久；装备后外形变赌徒、可攻击 20 级以上其他玩家、强制退队；**无法主动卸下**；**Ultra 及以下死亡时从构筑消失（一次性）**，Super 及以上死亡不消失。
- **2% / 98.4% 是腐化花瓣的掉落率**，不是「赌博成功率」：

| 击杀对象 | 掉落 Ultra 腐化概率 |
|---|---|
| 究极赌徒（Ultra Gambler） | **2.0%** |
| 超级赌徒（Super Gambler） | **98.4%** |
| 唯一赌徒（Unique Gambler） | **98.4%** |

  - 注：另有 B 站玩家视频称「U:0.2% / S:64.3%」，与中文维基 2.0%/98.4% 不一致，**以中文维基生物表为准，差异可能来自版本更新或统计口径，标注存疑**。
- Super 腐化可出现在商店；它的实际用途是 PVP 捣乱/交易给商人，**对纯 PVE 挂机无收益**。

### 对自动挂机插件的影响与建议

1. **插件目前完全不碰 NPC**（只巡逻打怪）。若要加自动化，**优先级最低的就是 Gambler/Corruption**——它是 PVP 向，挂机号装备腐化会引来玩家仇杀，反而断挂机。建议插件**明确避开设 Gambler 路线**。
2. **商人（Trader）24h 冷却 + 游荡难定位**：自动找商人性价比低（要在沙漠右下圈反复巡逻还可能跑了）。若要做 Coin 农场，建议手动蹲点时插件辅助巡逻那一个圈，而不是全程自动寻路。
3. **Oracle 28 分钟必成合成**：适合高价值卡（Mythic→Ultra 2% 赌不起时）。插件可加一个「提醒」：当玩家背包攒够 5 张某 Mythic 时弹窗「去海洋找 Oracle 必成」，但不必自动操作（28 分钟冷却 + 需人工选卡）。
4. **Titan 锻造有被抢风险**：不要把「自动攒 5 Super 去丛林锻造」写进自动流程；2025-11-26 后被别人 forge 会永久损失 1 Super，风险由玩家手动承担。
5. **Hel（冥界）刷 Gambler 是插件可扩展的地图**：插件已有 `hel.tmj`。Gambler 是 NPC 生物、血厚但掉落好，可在 `combat.py` 的怪物分级里把 Gambler 标为「中立/NPC，可打但别追太远（它随机游走）」，并避开它召唤/联动的高威胁怪。

### 来源 / 时间 / 时效

- NPC 对照：https://ashish.top/blog/florrio-biomes-guide/ （2026-05-20）、https://ashish.top/blog/florrio-crafting-explained/ （2026-04-28）
- 腐化掉落率：https://florrio.fandom.com/zh/wiki/腐化 （修订 2026-07-26）
- 商人刷点：https://wenda.codingtang.com/questions/29792/ （2026-07-10，玩家问答）；Trader 外观/机制 https://www.vintageisthenewold.com/faq/what-is-the-best-petal-in-florr （2026-05-29）
- ⚠️ 存疑：腐化掉落率维基 2.0%/98.4% 与玩家视频 0.2%/64.3% 不一致；商人具体卖价/刷新间隔**未找到可靠数据**（Trader 是换 Coin 而非标价卖货，无固定价格表）。

---

## 附：一句话给插件作者

- 插件现在的「刷同级秒杀怪 + 低血切回血 + 躲弹 + 自动复活」路线与官方「直接farm最高能打的稀有度、别硬赌合成」的建议完全一致，**核心战斗策略不用改**。
- 最值得加的两个低风险功能：① crystal_room 能量满时自动吸低稀有度卡练级；② 启动时按玩家 Loadout 实际槽位数扫描回血槽。其余 NPC（商人/神使/Titan/重构机）建议做成「手动触发 + 弹窗提醒」，不要全自动。
