# florr.io 地图结构 + 捷径 & Boss 机制研究报告

> 用途：服务于本地自动挂机插件 `C:\Users\intel\Downloads\florr-auto-pathing-main` 的路径规划与 Boss 遭遇应对优化。
> 整理时间：2026-09-26。所有关键数值均标注来源；查不到的一律标「未找到可靠数据」。
> ⚠️ florr.io 版本迭代很快（m28 仍在更新），维基数据可能滞后；每条来源后都附了更新时间，过时/传闻会单独标注。

---

## 数据来源优先级与时效

| 来源 | 性质 | 更新时间 | 可信度 |
|---|---|---|---|
| 官方 changelog `florr.io/static/i18n/en_US/changelog.txt` | 官方补丁日志 | 最新条目 2025-12-21 | 最高（机制变更权威） |
| 中文维基「生物」页（zh-my 变体）`florrio.fandom.com/zh/wiki/生物` | 玩家维护 | 2026-04-15 | 高（Bossbar/75级/播报） |
| 中文维基「二/Boss生物」页 | 玩家维护 | 2026-04-20 | 中（掉落名次表，与随机刷怪说法有冲突，见下文） |
| Namu Wiki（韩文）`namu.moe/w/Florr.io` | 玩家维护，更新勤 | 怪物表 2026-07-27 / 地图 2026-06-19 | 高（各区刷怪点） |
| 洛谷专栏《florr入坑攻略》`luogu.com/article/105mzp1d` | 玩家攻略 | 2026-05-23 | 高（25人掉落机制、练级路线） |
| ashish.top 系列博客 | 英文攻略 | 2026-04~05 | 中（部分数值与中文源有出入，已标注） |
| mobs.ashish.top/tracker | 实时事件追踪 | 2026-06 快照 | 高（验证 Super 刷新量级） |

---

# 第一部分：地图结构 + 捷径

## 0. 世界拓扑总览

florr.io 主世界是一张连通的圆形大地图（不是独立房间），从花园(Garden)向四周辐射。基础生物群系（出生屏幕可选直接进）：**Garden、Ocean、Desert、Jungle、Hel**；通过传送门(portal)进入的子群系：**Sewers、Ant Hell、Pyramid、Factory、Rift、Crystal Room**。

来源：Namu 地图页（2026-06-19）、ashish 生物群系指南（2026-05-20）。

**核心连接关系（文字版连接图）：**

```
                        Sewers(下水道)
                            ↑ (Garden 内传送门)
                            |
  Pyramid(金字塔) ←— Desert(沙漠) —— Garden(花园) —— Ocean(海洋)
       (沙漠内传送门)        |  \  \    \  \  \____________ ↘
                            |   \  \    \  \                 Jungle(丛林)
                            |    \  \    \  \_______________ ↗
                            |     \  \    \
                       Ant Hell(蚂蚁地狱) ←—(Garden/Desert/Jungle 各有传送门)
                            |
                       Factory(工厂) ← 在 Garden→Ocean/Jungle 的传送门路上
                            |
                       Crystal Room(水晶房间) ← Garden 出生点旁
                            |
                       Hel(地狱) ← 只能靠别人在你尸体上放 Mark 进入（非常驻传送门）
                            |
                       Rift(裂隙) ← Garden 右下黑色传送门，2~4 小时开一次
```

要点：
- **Garden 是绝对枢纽**：除了 Hel 和 Pyramid，所有地图都能从 Garden 走传送门到达（Namu：「가든 맵에서는 헬과 피라미드를 제외한 모든 맵을 포탈을 통해 갈 수 있다」）。
- **Factory 在 Garden→Ocean/Jungle 的必经传送门路上**，不是死路，路过时会被 Mecha 怪打扰。
- **Hel 没有常规传送门**：玩家死亡后由其他玩家用 Mark 花瓣标记尸体才能进入；去过一次后开始界面可直接进。是 PvP 区。
- **传送门触发方式**：白色六边形光圈，走进去静止数秒即传送（B 站新手攻略）。

---

## 1. Garden 花园（出生主城）

- **定位**：绿色背景，新手出生点（走完 Training Grounds 后落在这里）。除 Hel/Pyramid 外所有地图的传送门都在本区。
- **传送门**：通向下水道、水晶房间、Rift、海洋、丛林、蚂蚁地狱、沙漠、工厂（ashish 生物群系指南）。
- **子区域（按稀有度分区，Namu 地图页）**：
  | 子区 | 稀有度定位 | 刷怪 | 备注 |
  |---|---|---|---|
  | **Spiral（螺旋）** | 最深的 Ultra 区 | Ultra 怪为主 | **大部分 Super 怪都在这里刷**（蹲 Super 首选） |
  | **Mini Spiral（小螺旋）** | Mythic 区 | Mythic 怪为主 | 中期farm点 |
  | Bee zone | Legendary | Legendary Bee 为主，偶尔 Spider/Hornet/Bumble Bee | |
  | Ladybug zone | Legendary | Legendary Ladybug 为主 | |
- **常驻怪**：Rock(岩石)、Ladybug(瓢虫)、Ant Hole(蚁穴)、Spider(蜘蛛)、Dandelion(蒲公英)、Bee(蜜蜂)、Hornet(黄蜂)、Bumble Bee(熊蜂)。
- **安全/危险**：出生点周围是最安全的低级区；越往 Spiral 深处越危险。
- **入口等级**：无（1 级教程后即进入）。

---

## 2. Desert 沙漠

- **定位**：左下角，黄色背景。比 Garden 难。
- **传送门**：连接 Garden、Jungle、蚂蚁地狱（火蚁传送门）、Pyramid（金字塔）。
- **NPC**：**Trader 商人**（用一朵同稀有度花瓣换一枚硬币，24 小时冷却）。Namu 说它是「最难找的 NPC」。
- **子区域（Namu 地图页）**：
  | 子区 | 稀有度定位 | 备注 |
  |---|---|---|
  | **Box** | Ultra 区 | **大部分 Super 怪在此刷** |
  | **Tunnel** | Mythic 区 | Mythic 为主 |
  | ss zone（Sand Storm zone） | Legendary | Legendary Sandstorm(沙尘暴)为主 |
  | Beetle zone | Legendary | Legendary Beetle 为主，**效率很低，基本没人去** |
- **常驻怪**：Cactus(仙人掌)、Beetle(甲虫)、Nazar Beetle(纳扎尔甲虫)、Scorpion(蝎子)、Shiny Ladybug(闪光瓢虫)、Fire Ant Hole(火蚁穴)、Sandstorm(沙尘暴)、Desert Centipede(沙漠蜈蚣)。
- **插件 README 已指出**：沙漠入口区绿→蓝怪密集，效率约为花园 10 倍，巡逻点画在入口区刷怪最快。
- **入口等级**：无硬性等级（但怪比 Garden 强，建议有基础花瓣再进）。

---

## 3. Ocean 海洋

- **定位**：右上角，蓝色背景。
- **传送门**：连接 Garden 和 Jungle。Namu 英文旧档补充：丛林可从「East Waters 6 底部传送门（leech zone）」进入。
- **NPC**：**Oracle 神使**——保证一次合成成功，但要更多材料，28 分钟冷却。
- **常驻怪**：Bubble(泡泡)、Crab(螃蟹)、Jellyfish(水母)、Leech(水蛭)、Shell(扇贝)、Sponge(海绵)、Starfish(海星)、Diver Soldier Ant(潜水兵蚁)。
- **捷径/移动**：洛谷攻略提到「去海洋获取泡泡(Bubble)以增加去往蚁穴的速度」——Bubble 花瓣提供移速，是跨图赶路的关键道具。具体捷径路线坐标：**未找到可靠数据**（插件 ocean.tmj 已含捷径可走）。
- **安全/危险**：Leech(水蛭)吸血且全图移速最快，是本区最大威胁；Shell(扇贝)会射珍珠弹。海星 50% 血会逃跑回血，必须秒。
- **入口等级**：无硬性等级。

---

## 4. Ant Hell 蚂蚁地狱（重点：常规/机密/绝密）

- **定位**：左侧子群系，通过传送门进入。是新手中期最重要的 farm 区。
- **三个入口对应三个亚种区**（Namu + acgo）：
  - **普通蚁区** ← Garden 的蚁穴传送门进
  - **火蚁区(Fire Ant)** ← Desert 的传送门进（蚁穴左下角）
  - **白蚁区(Termite)** ← Jungle 的传送门进
  - Worm(蠕虫) 不受分区限制，全区随机刷。
- **子分区（按稀有度，来自 acgo 攻略 2026-07 + 洛谷）**：
  | 分区 | 怪物稀有度 | 建议等级 | 说明 |
  |---|---|---|---|
  | **常规（普通区）** | 普通/罕见为主，爆率低 | ≥4 | 复活点在 Garden 侧，落地即到 |
  | **机密** | 传说/史诗(Epic/Legendary)为主，爆率中等 | 20–40 首选 | 从常规区**再往左走，有一条密道**（看似过不去其实有通道） |
  | **绝密** | 传奇以上（传奇/神话/究极/超级） | ≥12（acgo）/ 20+ | 进机密后一直向上（机密之上、绝密之下），岔路**左转**进绝密 |
- **密道/捷径**：
  - 进蚁穴后**先往左走**，看似堵死其实有明显通道（洛谷）。
  - 再往左有密道通向**青区（Mythic 区）**，20–40 级首选。
  - ⚠️ 道德提示（洛谷）：被怪追时不要钻进密道消仇恨，素质差。
- **常驻怪**：Ant Egg(蚁卵)、Baby Ant(幼蚁)、Worker Ant(工蚁)、Soldier Ant(兵蚁)、Queen Ant(蚁后)、Fire Ant、Termite、Termite Overmind(白蚁主脑)、Worm。
- **特殊机制**：
  - 白蚁(Termite)：所有白蚁共享/分散血量，带闪电(Lightning)打效率高。
  - 打蚁卵会引来周围蚂蚁群仇恨。
  - 蚁后(Queen)很高傲，追你说明你惹事了。
- **安全/危险**：常规区安全；机密/绝密区怪伤害高，低级进会被秒（洛谷原话「随便一下就给你创死了」是正常现象）。
- **入口等级**：无硬等级，但 acgo 建议 ≥4 进常规、≥12 进绝密。

---

## 5. Jungle 丛林

- **定位**：深绿色背景（比 Garden 深），关键枢纽——除 Hel 外离所有出生点都只差一两个区。
- **传送门**：连接 Ant Hell、Desert、Garden、Ocean。
- **NPC/设施**：**Titan 泰坦熔炉**——把 **5 个 Super 花瓣合成 1 个 Unique 花瓣**（每种 Unique 全服同时只能存在一个）。这是获取 Unique 花瓣的唯一途径（ashish 合成指南 2026-04-28；2025-11-26 changelog 改版：固定 5 Super 合成，被别人合走会永久损失其中一个，有全局冷却）。
- **常驻怪**：Bush(灌木)、Leafbug(叶虫)、Golden Leafbug(金叶虫)、Mantis(螳螂)、Termite Mound(白蚁丘)、Wasp(黄蜂)、Firefly(萤火虫)、Magic Firefly(魔法萤火虫)、Dark Ladybug(暗黑瓢虫)。
- **危险**：螳螂 3 连发 + 降甲；灌木 Super+ 受击时会刷出随机丛林怪。
- **入口等级**：无硬等级。

---

## 6. Sewers 下水道

- **定位**：左上角，从 Garden 传送门进。
- **子区域（Namu）**：
  | 子区 | 稀有度 | 备注 |
  |---|---|---|
  | **Box** | Ultra 区 | **大部分 Super 怪在此刷** |
  | **Tunnel** | Mythic+Ultra 混合 | |
- **常驻怪**：Moth(蛾)、Fly(苍蝇)、Roach(蟑螂)、Spider(蜘蛛)、Garbage(垃圾)、Silverfish(衣鱼)。
- **特殊**：有 Fly(苍蝇)，90% 物理闪避，**必须带 Lightning/Battery（电系弹跳）才打得中**；水蛭共享血量。
- **入口等级**：无硬等级。

---

## 7. Hel 地狱

- **定位**：异次元位面，PvP 区。**没有常规传送门**——玩家死亡后由其他玩家用 Mark 花瓣标记尸体才能进入；去过一次后开始界面可直进。
- **常驻怪**：Hel Beetle(地狱甲虫)、Hel Wasp(地狱蜂)、Hel Centipede(地狱蜈蚣)、Hel Spider(地狱蜘蛛)、Gambler(赌徒)。
- **特殊机制**：
  - 难度极高，正常 farming 很困难。
  - 本区是 **PvP 判定**，可以攻击其他玩家，人多时小心。
  - 玩家死亡时，按在 Hel 累计的分数掉落对应稀有度的 Basic 花瓣：
    | 稀有度 | 分数门槛 |
    |---|---|
    | Common | 0–20 |
    | Unusual | 20–180 |
    | Rare | 180–2.7k |
    | Epic | 2.7k–72k |
    | Legendary | 72k–6.2m |
    | Mythic | 6.2m–790m |
    | Ultra | 790m–199.4b |
    | Super | 199.4b–324.6t |
  - 地狱甲虫会瞬移，血量是普通甲虫 1.5 倍（Namu）。
- **入口限制**：需要别人标记尸体（或去过一次）。

---

## 8. Factory 工厂（2025-02-23 新增）

- **定位**：在 Garden→Ocean/Jungle 的传送门路上，路过会经过。
- **NPC**：**Assembler 合成机**——用轮换配方把指定花瓣合成别的花瓣。
- **常驻怪**：Mecha Wasp(机械蜂)、Mecha Spider(机械蜘蛛)、Mecha Crab(机械蟹)、Mecha Flower(机械花)、Barrel(铀桶)。
- **特殊机制**：
  - Barrel(铀桶)：被打后开盖放绿色光环，近距离按距离毒伤，**远程用 Missile 打或用 Lotus 减毒**；Common/Unusual 不掉花瓣。
  - 机械蟹掉碎片/激光器/磁铁/电池等材料（洛谷：工厂是刷 U 碎片和齿轮的地方）。
- **入口等级**：无硬等级，但 Mecha 怪较强。

---

## 9. Crystal Room 水晶房间

- **定位**：Garden 出生点旁边的小房间（插件 crystal_room.tmj 仅 4KB，是个很小的区域）。
- **功能**：融卡/强化站。水晶有能量会持续恢复，融卡消耗能量，升级提高能量上限。
- **关键等级**：**lv142 以上才能融 Super 卡**（B 站 m28 更新视频 2025-12-13）。
- **怪物**：无战斗怪，是安全功能区。
- **入口**：Garden 出生点旁传送门，无等级门槛（但融 Super 要 142 级）。

---

## 10. Training Grounds 训练场

- **定位**：新手教程区。Target Dummy(训练假人)无敌，用来熟悉操作。
- **怪物**：训练假人（无敌，无掉落）。
- **出口**：走完教程进入 Garden。
- **对挂机插件**：无需挂机。

---

## （补充）Pyramid 金字塔 与 Rift 裂隙

- **Pyramid 金字塔**：从 Desert 出生点左侧进。Mummy Beetle(木乃伊甲虫)、Nazar Beetle、Tomb(墓碑)、**Pharaoh Beetle(法老甲虫，金字塔 Boss)**。特征：视野受限，每隔一段时间迷宫随机重排（提示语 "The sands under you are starting to shift..."）；捡到大地图(Map)道具可看清迷宫。法老甲虫每分钟召唤 2 级木乃伊甲虫，HP 437m，是 Pyramid 专属 Super+ Boss。
- **Rift 裂隙**：Garden 右下角**黑色传送门**，每 2–4 小时开一次，限时 1 小时。PvP 混战小游戏，花瓣最多 Common–Mythic。第一名奖励：永久 Super Basic 或临时 Champion's Crown(Unique)。**不适合挂机插件**。

---

# 第二部分：Boss 机制

## 1. 稀有度阶梯与血量倍率

生物/花瓣稀有度从低到高（中文维基「生物」页 2026-04-15）：

**Common 普通 → Unusual 罕见 → Rare 稀有 → Epic 史诗 → Legendary 传奇 → Mythic 神话 → Ultra 究极 → Super 超级 → Eternal 永恒 → Unique 唯一**

同级血量/伤害倍率：

| 跨越 | 血量倍率（相对上一级） | 备注 |
|---|---|---|
| 普通→罕见 | ×3.75 | |
| 罕见→稀有 | ×3.6 | |
| 稀有→史诗 | ×4 | |
| 史诗→传奇 | ×6 | |
| 传奇→神话 | ×9.75 | |
| 神话→究极 | **×46.15** | 巨大跳跃（插件 README 已用 ×46） |
| 究极→超级 | **×27.94** | |
| 超级→唯一 | ×6 | （Namu 记为 ×4.5，略有出入，以中文维基表为准） |
| 每级伤害 | ×3 | 身体/投掷物伤害 |
| 护甲 | 究极后基本不再涨 | |

> 这印证了插件 README 的策略：**高一级血量 ×3.6~46，经验只多 ×4~9，秒不了的高一级绝对不打**。

## 2. Super / Eternal / Unique 生成规律

**核心结论：Super 怪不是定时刷的，是「随机替换」生成。**

- 正常刷怪时刷出的是 Ultra 怪；**极低概率（最初 1%，2023-12-25 改为减半）这只 Ultra 会升级成 Super**（官方 changelog 2023-02-14 / 2023-12-25）。
- **每个 realm（服务器大区）每种 Ultra 怪同时只能存在一只**；有全局 realm 冷却防止刷太快（changelog 2024-01-05）。
- Ultra 可在任何普通怪能刷的地方刷出，但**高稀有度区（Spiral/Box/Tunnel 等）概率大得多**（changelog 2024-01-05）。
- 刷新频率历史调整：
  - 2023-05-03：Ultra 刷出频率约 ×10，掉落率 ×(1/3~1/4)。
  - 2023-12-25：Ultra 复活速度 ×2，Super 概率减半（整体频率不变）。
  - 2024-01-01：Ultra（不含 Super）掉落约 ×2。
  - 2025-10-14：Luck(幸运)天赋重新影响刷怪稀有度。
- **量级参考**：实时追踪站 mobs.ashish.top 快照显示，一整天全区约 **1546 次刷怪 / 261 只 Super / 27 只 Unique / 8 次 Rift**。即 Super 大约每 5~6 分钟全区刷一只，Unique 约每小时一只——**是随机事件，没有固定钟点**。
- Eternal(永恒)：在 Super 和 Unique 之间，极稀有。**Eternal 怪是否存在、如何生成，中文维基只在稀有度表里列了名字，具体刷法/血量未找到可靠数据**；传闻 Eternal 有 1% 概率掉 Super 花瓣（待验证）。
- Unique(唯一)：比 Super 高约 ×6 血量，掉落是同 Super 怪的 **10 倍**（2026-04-01 愚人节 M28 召唤 Unique 验证）。

> ⚠️ **冲突说明**：中文维基「二/Boss生物」页称 Boss「每天在固定时间点、每服务器出现」。但该说法与主「生物」页、Namu、官方 changelog、实时追踪站（每天 261 只 Super）全部矛盾。**判定：定时刷怪说法已过时/错误，当前 Super/Unique 为随机替换刷出**。该页的「伤害名次掉落表」（见下）仍与现行 25 人机制吻合，可采用。

## 3. 掉落分配规则（25 人机制 + 伤害门槛）

**按伤害贡献分配，分两档（洛谷 2026-05-23，与插件 README 一致）：**

- **Ultra 及以下的怪**：掉落分给 **恰好 4 人**。
  - 按「小队平均伤害」排序。
  - 小队总伤害 < 怪血量 **1%** → 全队无掉落。
  - maxrank ≤ 4 的小队 → 全队都有。
  - 否则在卡线小队里**随机抽人**直到凑满 4 人。
- **Super 及以上的怪**：机制完全相同，只是把 **4 改成 25**（即最多 25 人能分掉落）。
  - 门槛仍是小队总伤害 ≥ 怪血量 1%。
  - 人少的时候只要你能破甲，几乎等于 free loot。

**伤害名次掉落表**（中文维基「二/Boss生物」页，适用于 Super+ Boss 击杀）：

| 名次 | 掉落 | 所需伤害门槛 |
|---|---|---|
| 1 | 2 张随机 Boss 特殊花瓣 + 1 随机升级卡 | ≥50% 必拿第一；至少 45% |
| 2 | 2 张随机 Boss 特殊花瓣 | ≥25% |
| 3 | 1 Boss 特殊 + 1 Super 花瓣 + 1 升级卡 | ≥15% |
| 4–5 | 2 Super 花瓣 + 2 升级卡 | ≥10% |
| 6–8 | 2 Ultra 花瓣 + 2 升级卡 | ≥8% |
| 9–12 | 1 Ultra + 1 Mythic + 1 升级卡 | ≥5% |
| 13–20 | 2 Mythic + 1 升级卡 | ≥3% |
| 2% 概率档 | 1 Mythic + 1 Legendary + Ultra 升级卡 | 进不了前 20 |
| 1% 概率档 | 1 Mythic + 1 Legendary + Legendary 升级卡 | 无 |
| 参与奖 | 2 Legendary + 1 Legendary 升级卡 | ≥0.5% 伤害 |
| 见证者 | 1 Legendary + 1 Legendary 升级卡 | 同区见证其死亡即可 |

**其他掉落规则（官方 changelog）：**
- 2023-02-22 起：掉落不再全队相同，按每个玩家**独立随机 roll**。
- 2024-05-22：**死亡复活会清零伤害记录（借尸还魂复活不算）**——即死了再回来之前打的伤害不算 loot。
- 2023-12-30：只有大约**一屏距离内**的花才能吃到掉落。
- 小队伤害合并计算。

## 4. Bossbar（血条）显示机制

（中文维基「生物」页 2026-04-15）
- 玩家靠近 **Super / Eternal / Unique** 怪（除训练假花、泰坦、重构机、水晶外）时，屏幕**上方中央出现大血条（Bossbar）**。
- 若同时有多只不同种类的 Super/Eternal/Unique，且有的在视野外：**同时显示多个血条**（最近的 + 视野外的）；否则只显示最近的一只。
- 同种类多只同稀有度怪：血条显示该范围内所有该种同稀有度怪的**平均血量**。
- （2024-04-07 更新前，Ultra 怪也有 Bossbar；之后 Ultra 不再显示。）
- 蜈蚣的 Bossbar 是所有身体段血量的平均值，必须打头部才计入击杀。

## 5. 击杀播报系统

（中文维基「生物」页 + Namu）
- **生成播报**：Super 怪生成时，聊天栏通知**全服 75 级及以上玩家**。
  - 默认格式：`A Super <怪名> has spawned somewhere!`
  - 血祭召唤的 Super：`A Super <怪名> has been summoned!`
  - 部分 Super 有专属播报（不报怪名，需自己认）：
    - Super Rock 岩石：`Something mountain-like appears in the distance...`
    - Super Cactus 仙人掌：`A tower of thorns rises in the sand...`
    - Super Hornet 黄蜂：`A big yellow spot shows up in the distance...`
    - Super Hel Beetle 地狱甲虫：`You sense ominous vibrations coming from a different realm...`
  - 若你就在同一张图，会显示 `has spawned!`（不带 somewhere）；别的图则带 `somewhere!`。
- **死亡播报**：Super 非友善怪死亡后，显示 `<稀有度色> A <稀有度> <怪名> has been defeated by <伤害最高小队全体成员>!`（游客击杀则没有 by 谁）。蚁穴(Ant Hole)播报时有时无，疑似 bug。
- **伤害日志**：你打过它，会显示 `You dealt <数值> Damage to the <怪名>.`
- ⚠️ **必须在设置里打开「聊天(Chat)」选项才能看到所有播报**。
- Boss 被击败还会给账号加一个分数：`加分 = 你造成的伤害比例 / 你的伤害排名 × 100`；每天按分数/10 给经验，同时永久加幸运（分数/10000）——幸运越高刷怪稀有度越高。

## 6. 75 级限制详解

（中文维基「生物」页 2026-04-15，原文摘录）

> 「在超级生物生成时会在聊天栏通知全服 75 级及以上的玩家，死亡时会通知全服玩家。**在玩家 75 级以前杀死超级生物，只会有究极生物的掉落**，但图鉴会保留（只显示究极生物的掉落和经验）。**同时，在拥有 4 个究极花瓣前杀死超级生物也只会有究极生物的掉落。**」

**两条「软封顶」同时成立：**
1. **等级 < 75**：杀 Super 怪 → 只掉 Ultra（究极）级别的东西，不掉 Super 级。
2. **身上 < 4 个 Ultra 花瓣**：哪怕你 ≥75 级，只要还没凑齐 4 个究极花瓣，杀 Super 也照样只掉 Ultra。

> 实例（维基原文括号）：一个 lvl56 新手打死一只 S 级怪，结果只爆出 1 个 Legendary clover。

**对挂机的含义**：75 级（且凑齐 4 个 U 花瓣）之前，蹲 Super 怪的「Super 花瓣收益」是被锁死的，顶多拿 Ultra 档参与奖。

## 7. Boss / Super 怪一览表

> 只列有可靠数据的；HP 为该怪 **Super 档**血量（无 Super 数据的列基础机制）。来源已标。

| 名称 | 所在地图 | 类型 | 生成规律 | 掉落 | 特殊机制 |
|---|---|---|---|---|---|
| 通用 Super 怪 | 高稀有度区（Garden Spiral / Desert Box / Sewers Box 等） | Super | Ultra 极低概率替换，随机 | Mythic~Ultra 花瓣 + Boss 特殊花瓣 | 靠近出 Bossbar；专属播报 |
| **Pharaoh Beetle 法老甲虫** | Pyramid 金字塔 | Super+ 专属 Boss | 仅 Super+ 档存在 | Ankh/Bandage/**Pharaoh's Crown**(0.4% Unique，需持有 4+ Super 花瓣) | 每 1 秒召唤 2 级木乃伊甲虫；HP 437m（Namu） |
| **Gambler 赌徒** | Hel 地狱 | Super+ | Hel 区刷 | 腐化(Corruption) | 装备腐化可 PvP；究极赌徒掉 2%、超级/唯一赌徒掉 98.4% 腐化 |
| **Super Shell 扇贝** | Ocean 海洋 | Super | 随机 | Magnet/Shell | Super 档有新技能；HP 约 98,000,000（2023 YouTube 实测，**可能过时**） |
| **Super Sandstorm 沙尘暴** | Desert | Super | 随机 | — | Super 会吸人（插件 README 已规避） |
| **Super Hel Beetle 地狱甲虫** | Hel | Super | 专属播报召唤 | Dice/Beetle Egg/Mark | 比普通甲虫快、HP ×1.5、会瞬移；HP 30m(29,524,500)（中文维基甲虫冥界页） |
| Termite Overmind 白蚁主脑 | Ant Hell(白蚁区) | Super+ | 白蚁区刷 | — | 白蚁共享血量 |
| Queen Ant / Queen Fire Ant 蚁后 | Ant Hell | Super+ | 蚁区/火蚁区 | 双子/加速/翅膀/蛋/三重 | 高仇恨 |
| Eternal 永恒怪 | 未明确 | Eternal | 介于 Super 与 Unique 之间 | 传闻 1% 掉 Super 花瓣（待验证） | **具体名单/HP 未找到可靠数据** |
| Unique 唯一怪 | 高稀有度区 | Unique | 极稀有（每天全区约 27 只） | 同 Super 怪 ×10 掉落 | 每种 Unique 花瓣全服唯一 |

---

# 对自动挂机插件的影响与建议

> 结合插件现状（已有 10 张 .tmj 含捷径、Lazy θ* 寻路、同级秒杀/高一级规避、M 怪狩猎/U 怪规避、>1% 蹭伤害、低血保命）。

### 地图/路径侧
1. **巡逻点优先画「高稀有度刷 Super 区」边缘而非中心**：Super 主要刷在 Garden Spiral、Desert Box、Sewers Box。挂机想蹭 Super 伤害，巡逻点应压在这些 Ultra 区的**边界**——既能吃到刷怪，又不至于站在 Ultra 堆里被秒。比现在全图巡逻更高效。
2. **蚂蚁地狱三入口分流**：插件 anthell.tmj 已含密道。建议加一个「机密/绝密」巡逻预设——20–40 级走左侧密道进 Mythic 青区，高等级再岔路左转转绝密；低级号不要进绝密（会被创死）。
3. **路过 Factory / 传送门路口要预判 Mecha 怪**：Factory 在 Garden→Ocean/Jungle 的必经路上，跨图寻路经过时应把 Barrel(铀桶)加入「避开」名单（开盖放毒光环），远程 Missile 处理。
4. **Hel / Pyramid / Rift 不适合挂机**：Hel 是 PvP 区会被人杀、Pyramid 迷宫会随机重排（路径会失效）、Rift 是限时 PvP。插件应在选图层面把这三张图标为「不推荐 AFK」，或在 Pyramid 检测到迷宫重排提示语时暂停寻路。

### Boss 遭遇侧
5. **75 级前不要专门蹲 Super**：等级 <75 且 <4 个 U 花瓣时，杀 Super 只掉 Ultra 档，专门跑过去性价比低。插件可加一个等级判断：低于阈值时，Super 播报来了最多原地打 2.5 秒蹭 >1% 参与奖就走，不要切输出花瓣长途奔赴。
6. **Super 来了怎么应对**：同图播报 `A Super X has spawned!`（不带 somewhere）才说明在本图；带 `somewhere!` 是别的图，不用动。检测到本图 Super + 自己能破甲时，切高 DPS 花瓣贴脸打满 1%（人少≈free loot）；打不动就立刻撤，别硬刚（Super HP 是 Ultra 的 ×28，绝对秒不掉）。
7. **利用「5 分钟不攻击就回满血」机制**：Super 5 分钟没人打会自己回满。蹭完 1% 伤害后如果打不动，不必死贴，退到安全区等别人打——你那 1% 伤害已经计入 loot 资格（只要别死，死亡会清零伤害记录）。
8. **Bossbar 是比聊天更可靠的遭遇信号**：Super 进屏幕顶部就会出 Bossbar，不依赖「设置里开聊天」。插件若做视觉检测，盯屏幕顶部血条比读聊天文本更稳（聊天可能被用户关了）。

---

## 仍存疑 / 未找到可靠数据的点
- 各地图传送门的**精确坐标**（插件 .tmj 已含，未额外核对坐标数值）。
- Ocean「捷径」的具体路线坐标（只知 Bubble 提供移速、East Waters 6 底部通 Jungle）。
- Eternal(永恒) 怪的具体名单、HP、刷新方式（维基只列了稀有度名）。
- 「二/Boss生物」页的「每天定时刷 Boss」说法已判定过时，但无法 100% 排除存在另一套已下线的定时 Boss 系统。
- ashish.top 称标准怪「需 15% 伤害 + top4」，与洛谷「>1% 小队总伤」冲突——本报告采用洛谷（更详细且与插件现有 README 一致）；15% 说法可能为旧版或误写。
