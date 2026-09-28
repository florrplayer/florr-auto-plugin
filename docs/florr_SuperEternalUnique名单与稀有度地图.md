# florr.io：Super / Eternal / Unique 怪物完整名单 + 稀有度地图机制

> 用途：服务于 `florr-auto-pathing-main` 插件的怪物视觉识别与巡逻点优化。
> 整理时间：2026-09-27。承接上一份《研究报告-地图与Boss机制.md》。
> ⚠️ 数值均标来源与时间；查不到的标「未找到可靠数据」。

---

## 数据来源

| 来源 | 更新时间 | 用途 |
|---|---|---|
| 中文维基「生物」大表（zh-my 变体）`florrio.fandom.com/zh/wiki/生物` | 2026-04-15 | 84 种怪的稀有度列、专属播报文案、血量/伤害 |
| Namu 怪物表 `namu.moe/w/Florr.io/몹 목록` | 2026-07-27 | Super+/特殊技能/血量倍率 |
| Namu 地图页 `namu.moe/w/Florr.io/맵` | 2026-06-19 | 子区域稀有度 |
| 博客园配色表 `cnblogs.com/Tzf-tzf/p/17289337` | 2023-04-05 | 稀有度十六进制色值 |
| HFOJ 冷知识 `hfoj.net/blog/1941/...` | 2025-01-13（版本 2025.1.13） | Alt 键真实功能、地图底色、AFK 弹窗 |
| 洛谷策略#1 `luogu.com/article/h1bxz0sg` | 2023-08-01 | 世界地图图例、区域代号 C/O/D/J/S |
| 官方 changelog | 最新 2025-12-21 | Luck 改动、Unique 合成 |
| mobs.ashish.top/tracker | 2026-06 快照 | Super/Unique 刷新量级 |

---

# 第一部分：稀有度阶梯（复习）

生物/花瓣稀有度从低到高（中文维基 2026-04-15）：

**Common 普通 → Unusual 罕见 → Rare 稀有 → Epic 史诗 → Legendary 传奇 → Mythic 神话 → Ultra 究极 → Super 超级 → Eternal 永恒 → Unique 唯一**

血量倍率（相对上一级）：普通→罕见 ×3.75，罕见→稀有 ×3.6，稀有→史诗 ×4，史诗→传奇 ×6，传奇→神话 ×9.75，神话→究极 **×46.15**，究极→超级 **×27.94**，超级→唯一 ×6。伤害每级 ×3。

> 关键事实：**生物大表里每一只怪（84 种）都有「超级」列和「唯一」列的数值**，意味着设计上几乎每种怪都能刷出 Super 和 Unique 变体；而**「永恒」列在整张表里全是空的**——见第三部分。

---

# 第二部分：Super 级怪物完整名单

## 2.1 总览

- **几乎每种普通怪都有 Super 变体**：当一只 Ultra 怪生成时，极低概率（最初 1%，2023-12-25 减半）升级成 Super。不是每种怪单独刷新，而是"同一张脸、放大数倍、颜色变 Super 绿"。
- **同屏识别特征**：Super 怪体型约为 Common 版的 ×4374000（中文维基血量表），视觉上极大；身体/花瓣描边色 = Super 稀有度色（见 2.4）。
- **生成播报**：绝大多数是通用句 `A Super <怪名> has spawned somewhere!`；同图则不带 somewhere。

## 2.2 有专属播报的"Boss 型"Super（插件视觉/听觉识别重点）

这些 Super **不报怪名**，用一句氛围文案代替，必须靠位置+外观判断：

| Super 怪 | 专属播报文案（中译） | 所在地图 | 识别要点 |
|---|---|---|---|
| **Rock 岩石** | "Something mountain-like appears in the distance..."（远处浮现山般巨物） | Garden | 巨型石头，障碍型 |
| **Cactus 仙人掌** | "A tower of thorns rises in the sand..."（沙海升起荆棘塔） | Desert | 巨型仙人掌，障碍型，碰就伤 |
| **Hornet 黄蜂** | "A big yellow spot shows up in the distance..."（天边金黄斑痕） | Garden | 飞在天上的大黄点，射蜂针 |
| **Jellyfish 水母** | "You hear lightning strikes coming from a far distance..."（远方闷雷） | Ocean | 会闪电连锁，敌对 |
| **Firefly 萤火虫** | "There's a bright light in the horizon..."（地平线黄光） | Jungle | 发光体，闪电连锁 |
| **Hel Beetle/Spider/Centipede/Wasp 冥界四件套** | "You sense ominous vibrations coming from a different realm..."（异界不祥波动） | Hel | 冥界外观，会瞬移/高毒 |
| **Gambler 赌徒** | "You hear someone whisper faintly... 'just... one more game...'"（耳边呢喃"最后一注"） | Hel | NPC 型，掉腐化 |

> 其余所有 Super 怪（瓢虫/蜜蜂/蚂蚁/蜘蛛/蝎子/泡泡/扇贝/海星/螃蟹/水蛭/蒲公英/叶虫/螳螂/白蚁/蠕虫/机械系列/木乃伊/法老/棺材/蠹虫/垃圾袋/幽灵/铀桶/蚁穴/蚁卵等）都用**通用播报**，不报位置特色。

## 2.3 按地图分组的 Super 怪名单

> 「机制」列只列与挂机/闪避相关的特殊点；HP 为该怪 **Super 档**身体伤害（括号内为精确值），血量见各怪子页。

| 地图 | 可刷 Super 的怪 | 特殊机制（Super 档） |
|---|---|---|
| **Garden 花园** | Rock 岩石、Cactus(本图外)、Ladybug 瓢虫、Ladybug Dark 深瓢虫、Ladybug Yellow 黄瓢虫、Bee 蜜蜂、Baby/Worker/Soldier Ant、Ant Hole 蚁穴、Ant Egg 蚁卵、Hornet 黄蜂、Centipede 蜈蚣、Evil Centipede 邪恶蜈蚣、Dandelion 蒲公英、Bumble Bee 熊蜂、Spider 蜘蛛、Square 正方形 | 黄蜂射蜂针（史诗+预判）；蒲公英受伤射一圈弹；蜘蛛剧毒；蜈蚣须打头；正方形 0.001% 替换率 |
| **Desert 沙漠** | Cactus 仙人掌、Beetle 甲虫、Nazar Beetle 邪眼甲虫、Scorpion 蝎子、Shiny Ladybug、Sandstorm 沙尘暴、Desert Centipede 沙漠蜈蚣、Fire Ant Burrow 火蚁穴 | 蝎子射毒针；沙尘暴 Super 会吸人；沙漠蜈蚣钻地+极快；Nazar 每 1 秒免伤 3 次(Super 15 次) |
| **Ocean 海洋** | Bubble 泡泡、Crab 螃蟹、Jellyfish 水母、Shell 扇贝、Starfish 海星、Sponge 海绵、Leech 水蛭、Soldier Ant(Diver) 潜水兵蚁 | 泡泡血量最低/溅射击退，Super 受击召小泡泡；扇贝射珍珠弹；海星 50% 血逃跑回血（须秒）；水蛭吸血+全图最快+共享身体血 |
| **Jungle 丛林** | Bush 灌木、Leafbug 叶虫、Leafbug(Shiny) 闪亮叶虫、Mantis 螳螂、Wasp 胡蜂、Termite 系列、Firefly 萤火虫、Magic Firefly 魔法萤火虫 | 灌木 Super 受击刷随机丛林怪；螳螂 3 连发+降甲；白蚁全组共享血量；胡蜂射导弹 |
| **Ant Hell 蚁地狱** | Baby/Worker/Soldier Ant、Queen Ant 蚁后、Ant Hole、Ant Egg、Fire Ant 全系列、Termite 全系列、Termite Overmind 白蚁主宰者、Termite Mound 白蚁丘、Worm 蠕虫 | 打蚁卵引蚁群仇恨；蚁后高仇恨；白蚁灵能链接共享伤害；蠕虫钻地吃花 |
| **Sewers 下水道** | Fly 苍蝇、Roach 蟑螂、Moth 飞蛾、Spider、Garbage 垃圾袋、Silverfish 蠹虫 | 苍蝇 90% 物理闪避（必须闪电）；蟑螂受伤高速冲撞 |
| **Hel 地狱** | Hel Beetle、Hel Spider、Hel Centipede、Hel Wasp、Gambler 赌徒 | 冥界四件套会瞬移/高毒；PvP 区；赌徒掉腐化可 PvP |
| **Factory 工厂** | Mecha Flower 机械花、Mecha Wasp、Mecha Spider、Mecha Crab、Barrel 铀桶 | 机械蜘蛛/螃蟹用闪电伤害；铀桶开盖放毒光环（远程打） |
| **Pyramid 金字塔** | Mummy Beetle 木乃伊甲虫、Nazar Beetle、Pharaoh Beetle 法老甲虫、Tomb 棺材 | 木乃伊死了进"腐败"延迟状态；法老每分钟召 2 级木乃伊（Pyramid 专属 Boss，HP 437m）；迷宫随机重排 |

**有专属数据的几个 Boss 型 Super：**
- **Pharaoh Beetle 法老甲虫**（Pyramid）：HP 437m，伤害 65.6k，腐败 8s，掉 Ankh/Bandage/Pharaoh's Crown（0.4% Unique，需持 4+ Super 花瓣）。Namu 2026-07-27。
- **Hel Beetle 冥界甲虫**（Hel）：HP 30m(29,524,500)，比普通甲虫快、HP×1.5、会瞬移。中文维基甲虫(冥界)页。
- **Super Shell 扇贝**（Ocean）：2023 YouTube 实测 HP 98,000,000 / 伤害 21,900（**已过时，仅供量级参考**）。
- **Termite Overmind 白蚁主宰者**：HP 28m（Super 档），灵能链接。

## 2.4 外观颜色速查（插件视觉识别用）

稀有度描边/UI 色值（博客园 2023-04-05，可能微调但插件 README 的"青=M、粉=U"已印证）：

| 稀有度 | 色值 | 大致颜色 | 插件现状 |
|---|---|---|---|
| Common 普通 | `#7EEF6D` | 绿 | |
| Unusual 罕见 | `#FFE65D` | 黄 | |
| Rare 稀有 | `#4D52E3` | 蓝（原蓝紫，后改蓝） | |
| Epic 史诗 | `#861FDE` | 紫 | |
| Legendary 传奇 | `#DE1F1F` | 红 | |
| Mythic 神话 | `#1FDBDE` | 青 | 插件已识别为"M(青)" |
| Ultra 究极 | `#FF2B75` | 粉 | 插件已识别为"U(粉)" |
| Super 超级 | `#2BFFA3` | 薄荷绿 | **插件未专门处理，建议新增** |
| Eternal 永恒 | 未找到可靠数据 | — | |
| Unique 唯一 | 2024-12-12 重新加入时改为"唯一"专属色；**精确色值需游戏截图实测** | — | |

> 提示：生物体型随稀有度暴涨（Common→Super 血量差 437 万倍），**"体型突然巨大 + Super 薄荷绿描边"是比颜色更稳的视觉信号**。具体像素色值建议在游戏里开 Super 怪后用插件现有的 1px 取色器实测，维基给的是 UI 色不是怪身体色。

---

# 第三部分：Eternal 永恒级怪物

**结论：Eternal 作为稀有度档位存在，但「Eternal 级怪物」本身几乎没有可靠数据。**

- 中文维基生物大表的列头里有「永恒」一档，但**84 种怪的永恒列全部为空**（没有任何血量/伤害数值）。
- Namu 把 Eternal 列在 Super 与 Unique 之间（TP 天赋成本 18，血量介于两者），但怪物表里没有任何一只怪列出 Eternal 数据。
- **Eternal 花瓣**确实存在（合成 Super→Eternal 成功率 0.1%，ashish 2026-04-28），但那是花瓣不是怪。
- 中文维基原文：「传闻 Eternal 生物有 1% 概率掉落 Super 花瓣（待验证）」——**明确标注为传闻**。
- 实时追踪站一天约 261 只 Super、27 只 Unique，但**没有单独统计 Eternal**，侧面说明 Eternal 怪极少或不单独计数。

**判定**：Eternal 怪要么尚未实装为可刷怪、要么极稀有到没有可靠样本。**未找到可靠数据**，插件无需为其单独写识别逻辑（碰到就当 Unique 级危险怪处理即可）。

---

# 第四部分：Unique 唯一级怪物

- **存在且会刷新**：追踪站一天约 27 只 Unique（全区），约每小时 1 只。
- **生成方式**：比 Super 更稀有的随机变体（Super→Unique 血量 ×6）。不是定时刷。
- **掉落**：中文维基明确「Unique 生物掉落 = 10× 同 Super 生物的掉落」（2026-04-01 愚人节 M28 召唤 Unique 验证）。
- **全服唯一机制**（针对**花瓣**，不是怪）：Unique 花瓣每种全服同时只能存在一个；Jungle 的 Titan 熔炉用 5 个 Super 花瓣合成 1 个 Unique（2025-11-26 改版：固定 5 Super，被别人合走会永久损失其一，有全局冷却）。
- **有数据的 Unique 怪**：
  - **Leafbug (Shiny) 闪亮叶虫**（Jungle）：Unique 档 HP **1.3b**、伤害 197k、护甲 66.2k，掉金叶/Monstera/Golden Leaf。中文维基叶虫(闪亮)页 2026-07-04。
  - 其余怪的 Unique 列在大表里有理论数值（伤害约 Super ×3），但是否实际刷出、外观如何：**未找到可靠数据**。
- **识别**：比 Super 更大、更稀有；出现时同样走 Super 播报体系（同图播报）。插件把它当"比 Super 更不能碰的怪"即可。

---

# 第五部分：稀有度地图机制

## 5.1 先纠正：Alt 键到底干什么

**根据 HFOJ 冷知识（2025-01-13 版本）：「按下 Alt 能去除花瓣堆叠时的乘号（×N）」。** 也就是说 Alt 是 UI 开关，用来隐藏花瓣上的堆叠数量标记，**不是用来显示稀有度地图的**。

> 「Alt 显示稀有度地图」这一说法**未找到可靠数据**，可能是与 M 键世界地图混淆，或近期版本改动。建议插件作者实际进游戏按一下 Alt 确认（若新版有改动）。

## 5.2 M 键世界地图 / 小地图怎么读

- **M 键**展开世界地图（洛谷入坑攻略明确"按 M 键展开地图"）。
- 小地图图例（洛谷策略#1 附图，2023-08-01）：
  - 🟡 黄星 = spawn 出生点；🟢 绿星 = 新区域
  - **🟥🟩 红绿块 = ultra/super 刷新区**
  - **🌈 彩虹色块 = 区内稀有度分布（rarity within area）**
  - 黄点 = 自己位置；蓝点 = 传送门；白底 = 地面；黑底 = 墙（Namu）
- 区域代号体系：**C1–C8** = Centralia Fields（花园），**O1–O9** = East Waters（海洋），**D1–D5** = South Desert（沙漠），**J1–J5 / Ellne** = Jungle，**S1–S4** = Sewers。

## 5.3 各地图子区域稀有度分级（详细）

> 这是巡逻点选址的核心。来源：Namu 地图页 2026-06-19 + 中文维基东海页 2026-07-20 + 洛谷。

### Garden 花园（Centralia）
| 子区 | 稀有度 | 刷怪 |
|---|---|---|
| C1（出生点/Centralia Fields） | 普通~罕见 | 新手区 |
| C2/C3/C5/C6/C7（Centralia 外围） | 罕见~稀有 | 过渡 |
| **Mini Spiral（小螺旋）** | **神话 Mythic 区** | Mythic 怪为主 |
| **Spiral（螺旋）** | **究极 Ultra 区（最深）** | Ultra 为主，**大部分 Super 在此刷** |
| Bee zone（蜜蜂区） | 传奇 Legendary | Legendary Bee，偶见蜘蛛/黄蜂/熊蜂 |
| Ladybug zone（瓢虫区） | 传奇 Legendary | Legendary Ladybug |
| Centralia Maze（C8） | 迷宫 | |

### Desert 沙漠（South Desert）
| 子区 | 稀有度 | 备注 |
|---|---|---|
| D1/D2/D3 入口 | 普通~稀有 | 绿蓝怪密集，效率约花园 10 倍（插件 README） |
| **Tunnel** | **神话 Mythic** | |
| **Box** | **究极 Ultra** | **大部分 Super 在此刷** |
| ss zone（Sand Storm） | 传奇 | Legendary Sandstorm |
| Beetle zone | 传奇 | 效率低，没人去 |

### Ocean 海洋（East Waters，中文维基东海页 2026-07-20）
| 子区 | 普遍稀有度 | 备注 |
|---|---|---|
| O1 海滩 beach | 普通~传奇 | 海绵/泡泡/扇贝/海星/水母/螃蟹 |
| O2/O3 东部水域 | 过渡 | O3 旁有 ocean maze |
| O4 shell zone 贝壳区 | — | 扇贝 |
| **O6 leech zone 水蛭区** | 较高 | 水蛭；底部传送门通 Jungle |
| O7 crab kingdom 螃蟹王国 | — | 螃蟹 |
| O5 jellyfish fields 水母平原 | — | 水母 |
| O8/O9 深处 | 更高 | |

### Sewers 下水道
| 子区 | 稀有度 |
|---|---|
| Tunnel | Mythic + Ultra 混合 |
| **Box** | **Ultra（大部分 Super 在此刷）** |

### Ant Hell 蚁地狱
| 分区 | 稀有度 | 建议等级 |
|---|---|---|
| 常规 | 普通/罕见为主 | ≥4 |
| 机密（密道左进） | 史诗/传奇为主 | 20–40 |
| 绝密（岔路左转） | 传奇/神话/究极/**有概率 Super** | ≥12 |

### Jungle / Hel / Factory
- Jungle：无明确稀有度子区划分，整体比 Garden 高；Titan 熔炉在本区。
- Hel：PvP，按死亡掉分定稀有度（0–324.6t 分对应 Common–Super，见上一份报告）。
- Factory：Mecha 怪区，无明确稀有度子区。

## 5.4 边界 / 过渡机制

- 各区之间**无缝连接**，稀有度渐变过渡，没有硬墙（slopeplay 2026-03）。
- 越深入高稀有度区（Spiral/Box 这类"盒子/螺旋"结构中心），怪稀有度越高；边缘是低稀有度。
- **传送门出来有 3 秒无敌**（敌对怪变中立、不掉血），且传送后 3 秒不能再传送（HFOJ 冷知识）——插件跨图后这 3 秒是安全窗口。
- 一只怪 5 分钟不受伤害会自动回满血（中文维基）。

## 5.5 Luck 天赋 / 幸运草对刷怪稀有度的影响

- **2025-10-14 changelog**：「Luck now affects mob spawns again, increasing the rarity of mobs that spawn in that area.」——Luck 天赋重新生效，会提升所在区域刷怪的稀有度。
- 含义：点了 Luck 后，巡逻区内 Mythic/Ultra 出现率会上升。**插件若按"当前怪稀有度"调整战斗策略，要把 Luck 这个变量算进去**（同样巡逻点，点了 Luck 后危险怪更多）。
- 高稀有度区（Spiral/Box）本来就更容易刷 Ultra/Super，Luck 是叠加增益。

---

# 对自动挂机插件的影响与建议

1. **新增 Super（薄荷绿 #2BFFA3）识别**：目前插件只区分 M(青)/U(粉)。建议加一档"Super 体型+薄荷绿描边"检测——一旦发现，75 级以上才考虑蹭伤害，75 级以下直接绕（只掉 Ultra）。
2. **巡逻点压在 Ultra 区"Box/Spiral"边缘**：Garden Spiral、Desert Box、Sewers Box 是 Super 高发区。压边缘既能蹭 Super 刷新又不站在 Ultra 堆里被秒。
3. **专属播报怪不要硬刚**：Rock/Cactus/Hornet/Jellyfish/Firefly/冥界四件套/Gambler 这几只 Super 有专属机制（吸人、瞬移、连锁闪电、高毒），插件碰到应切"回避"而非"贴脸输出"。
4. **Alt 不要用来判断稀有度**：Alt 实际只是隐藏花瓣 ×N 标记。稀有度请靠 M 地图色块 + 怪体型/描边色判断；建议在游戏里实测 Super/Unique 的精确身体色值后写进 `config.py`。
5. **处理 AFK Check 弹窗**：HFOJ 冷知识提到游戏会随机弹 "AFK Check: Are you here?"（60 秒不点就踢），半小时静止/规律运动后还会弹 AFK?。插件现有的防挂机微操要能**识别并点击这个弹窗的"Yes"按钮**，否则会被强制下线——这是比反检测更硬的存活要求。
6. **传送门 3 秒无敌窗口**：跨图传送后 3 秒内安全，插件可利用这 3 秒重新校准巡逻点/读取小地图，不必担心被怪偷袭。
7. **Eternal 不用专门处理**：Eternal 怪无可靠数据，插件把它归入"比 Unique 更危险、绕开"即可，无需单列逻辑。

---

## 存疑 / 未找到可靠数据
- **Alt 键是否（新版）显示稀有度地图**：旧资料只说 Alt 隐藏花瓣 ×N；未找到"Alt=稀有度地图"的可靠依据，需游戏内实测。
- **Unique 怪的身体颜色**：2024-12-12 重新加入时改了专属色，精确色值需游戏截图实测。
- **Eternal 怪**：是否存在、如何生成、HP/掉落，均无可靠数据（仅传闻 1% 掉 Super 花瓣）。
- **各子区精确坐标边界**：维基只给了子区名和稀有度定位，未给像素边界；插件 .tmj 已含地图，建议在 `map_select.py` 里按已知子区手动框巡逻点。
- **Super Shell 等单怪 HP**：2023 YouTube 数字已过时，仅作量级参考。
