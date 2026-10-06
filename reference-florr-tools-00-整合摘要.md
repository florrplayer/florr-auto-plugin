# reference-florr-tools 全仓库深挖 · 整合摘要

> 覆盖 `reference-florr-tools\` 下 **20 个子目录**（含清单外新发现仓库 `florr-auto-framework-pytorch`；`FlorrCheatsV3` 为空）。全程只读本地磁盘，未联网、未启动游戏。全部结论来自对仓库文件的真实读取。
> 各仓库详细报告见同目录下 `reference-florr-tools-01~07`（每个仓库含 能力摘要 + ①可直接整合 ②结构化表 ③与已偷资产差异 三栏）。

---

## 0. 总览

| # | 仓库 | 规模 | 一句话结论 | 最高价值点 |
|---|------|------|-----------|-----------|
| 01 | FlorrBt | 1128 文件 / 31.5MB | 2026-08 的**私服自实现**（C++ 游戏服务器 + Web 客户端重制），非官方反编译 | `drop_rate.h` 99KB 结构化掉率真源；完整二进制线协议 protocol.js |
| 02 | florr-auto-sszone | 22 文件 / 27.5MB | main.py 三层对抗混淆（仅 config.json 数值可偷）；wiki.json 680 篇 wikitext | YOLOv10 检测权重 + AFK 模型；wiki 掉落矩阵作交叉校验 |
| 03 | florr_powerful_tools | 1099 文件 / 194.8MB | 行为克隆 RL 全家桶：模型权重、6583 条样本、YOLO 标签集 | `auto_stf/model.pth` + 73→128→64→5 网络 + 样本；像素读血 `check_health()` |
| 04 | florr-auto-farm | 136 文件 / 3MB | **认知增量最大**：整条 canvas 绘制指令解码管线替代像素猜 | 稀有度真值色表、血条三层规则、WASM 开关地址 0x53430E/0x534310、17 个回归帧 |
| 05 | 小仓库A（6 个 AFK 脚本） | 合计 ~0.4MB | 全是老版题型（切槽/OCR 点 here/DOM 按钮），与现有 afk_solver.py 零核心替代 | `button[data-qa-id="afkCheck"]` DOM 钩子、后台保渲染技巧 |
| 06 | 小仓库B（4 个：Bot/mob-bot/maze/pytorch） | 合计 ~12.4MB | maze-tool 是**空壳**（仅 LICENSE+README）；pytorch 框架是真货 | rotate.js 偷玩家朝向、Florr_Bot 像素阈值+拟人缓动 |
| 07 | 小仓库C（6 个：hacks/旧版/对比） | 合计 ~6.7MB | iogames 是混淆恶意包（只取情报）；BetterFlorrSite 的 wasm 是**插件本体非游戏客户端**（纠偏） | Canvas 矩阵求逆实体定位、换服 API、主插件 diff 结论 |

**横评**：本批 20 仓库里真正值得深挖的按价值排序为 **03 powerful_tools ≈ 04 auto-farm > 01 FlorrBt > 02 sszone(wiki部分) > 06 pytorch框架 > 07 旧版/情报**；05/06 其余仓库与 maze-tool 几乎零数据增量。

---

## 1. 可直接整合进现有插件的算法/数据（按现有插件模块分组）

现有插件文件：`combat.py`（OpenCV 屏幕检测）、`mob_db.py`（数据层）、`memory_reader.py`（内存读取）、`bridge_server.py`/`bridge_combat.py`（WebSocket 桥）、`afk_solver.py`（AFK 破解）、`net_protocol.py`/`drop_table.py`/`spawn_data.py`/`projectile_data.py` 等。

### 1.1 检测层（升级 combat.py / 新增解码管线）

- **【最高优先】canvas 绘制指令解码管线**（`04 florr-auto-farm`）：`canvas_hook.js` 经 Chrome CDP 拦截 `fill/stroke/fillText`，`canvas_decode.py` 反解出每只怪的**真名、血量、稀有度颜色、绝对世界坐标**。现有 OpenCV HSV 猜尺寸路线可整体升级，`RARITY_SIZE_FACTOR` 尺寸猜稀有度可退役。坐标换算公式可复现：`world = player_world + (screen − player_screen)/zoom`，zoom 取血条 CTM 的 `m[0]`（实测沙漠 0.315 / 蚁穴 0.45）；小地图另有 `MINIMAP_WORLD_SCALE` 真值表。
- **稀有度真值颜色表**（`04` enemy_detect.py:786）：`#DE1F1F`=传奇、`#1FDBDE`=神话、`#FF2B75`=究极、`#861FDE`=史诗、`#4D52E3`=稀有 等 9 个 hex，直接校准现有 HSV 阈值（现 combat.py 的 Mythic/Ultra 阈值就是凭经验估的）。
- **血条三层精确规则**（`04`）：底 `#222222` 满宽 / 红 `#DD3434` 已掉血 / 绿 `#75DD34` 剩血，`hp = 绿条覆盖比`；配中文怪名映射表（沙尘暴/蝎子/兵蚁…→slug）直接补 mob_db.py。
- **固定像素读血**（`03` dataset_utils.py::check_health()）：x=116..278 / y=97 扫血条，满血系数 32041——不依赖画布解码时的备用方案。
- **WASM 内存开关**（`04`）：反转攻击 `0x53430E`、反转防御 `0x534310`——bot 不按攻击键、写这字节让 florr 自动持续输出，可与 memory_reader.py 结合。
- **WinRT Graphics Capture 抓帧**（`03` capture/wgc.py）：按 hwnd 无边框抓帧，比 mss 更稳的战斗截图后端。

### 1.2 数据层（补表 mob_db.py / data\*.json）

- **掉率真源**（`01` src/Shared/drop_rate.h，99KB / 约 1100 行 `RegisterDropRate`）：结构化掉率表，比已偷 `florr_dropchance.json`（wasm 反推）更干净，含切叶蚁复制兵蚁掉落等手工修正——**建议下一步专门解析转录**。
- **平衡常量库**（`01` src/Shared/game_config.h）：默认怪半径 80、速度 400、火蚁伤害×2 等；rarity.h / stats.h / drop_rate.h 为配套结构。
- **YOLO 类别权威表**（`03` data.yaml，nc=81，索引 0–80→怪名）+ `MOB_TYPE_ONE_HOTS` 90 项：合并去重后作为 mob_db.py 的 canonical 怪名键表。
- **不可堆叠花瓣集合**（`01` game_ids.js）：13 个不可堆叠花瓣 id 集合——现有插件没有这个维度，背包/拾取逻辑可用。
- **wiki 交叉校验**（`02` 数据提取 JSON）：115 怪 / 120 花瓣 / 60 区域条目与掉率矩阵（如 Ultra Sandstorm 掉 Mythic Sand 8.9%、Ultra 0.03%、相邻稀有度×3、合成 64%→1%），用于校正 mob_stats_full.json / florr_dropchance.json 的角落数值。
- **换装模板与刷怪走位参数**（`02` config.json 真实取值）：attackMinimumDist=350px、safeDistanceK=0.2、Weights{Legendary 0.6 / Mythic 3.7 / Ultra 1.8}、sizes{Mythic 170 / Ultra 300}、刷怪格子多边形、目的地 [25,25]。

### 1.3 桥接层（补 bridge_server.py / bridge_combat.py 消息 schema）

- **网页端→Python 推送**：`health / health_speed / inventory / 花瓣坐标`；**Python→网页端回推**：`showNotification` + 槽位 `1..9,0` 按键（`03` 桥接协议 + `06` rotate.js）。
- **玩家朝向偷取**（`06` rotate.js）：hook `Canvas.fillText("Mythic", 12号)` 的绘制坐标 → 本地 FastAPI 算 `degree`（atan2）——bridge 可直接复用这条思路拿朝向。
- **换服 API**（`07` old_betterflorr）：`window.cp6.forceServerID()`（游戏自带换服 API）+ `wss://xxxx.s.m28n.net/` 服号正则 + `regionToName`（NA→US/EU/AS）。
- **sponge 扩展现成策略**（`03`）：低血 ETA<1s 切海绵是现成脚本逻辑。

### 1.4 AFK 层（afk_solver.py 增强）

- **成熟 YOLO+分割 AFK 迷宫求解**（`03`）：`afk-det.pt`（类别 `["Window","Start","End"]`）→ `afk-seg.pt` 分割迷宫路径 → segment_utils 骨架化 → Dijkstra → RDP 平滑 → 鼠标沿路径移动。afk_solver.py 可整体换成这套带权重方案。
- **AFK 三模型**（`02`）：afk.pt / afk-det.pt / afk-seg-pro.pt 通用/检测/分割三件套。
- **DOM 钩子**（`05` Florr-Auto-AFK-Script）：`button[data-qa-id="afkCheck"]`——若仍存活可把整条视觉流水线短路成一次 click（作者自陈有 bug、选择器可能已失效，须本地验活）。
- **后台保渲染**（`05` florr-AFK-indicator）：覆写 `requestAnimationFrame` + Worker 定时器让**最小化标签页仍出帧**。
- **拟人节奏库**（`05` antiafkflorrio）：5s 短定时器 + 120s 周期存在感点击 + 随机 OCR 缩放 + 随机双击抖动（`03` Florr_Bot simulateHumanMovement 三次方缓动+抖动同款）。
- **换槽位保活**（`05` Florr.io-Auto-AFK）：每 60s 切槽位 + `slotCode=[0,49..58,48]` 键码表。
- **对比结论**：现有 afk_solver.py 破解的是**拖动连线型**验证；05 批全是更老的题型，核心算法零替代，增量在 DOM 钩子/后台保渲染/拟人节奏三条。

### 1.5 寻路 / 走位 / 决策

- **战斗决策表直接抄**（`04`）：Ultra 蝎子/甲虫=AVOID、Ultra 沙暴/仙人掌=CAUTIOUS 保持距离、Mythic 按物种风筝（甲虫环绕/蝎子直冲/仙人掌站桩）；Dijkstra 逃跑规划 `flee_planner.plan_flee`（自己比追兵早到 1 格的格子才安全）。
- **目标选择表**（`03`）：`MOB_TYPES` 11 怪 priority/danger 表 + YOLO/HSV 双通道；navigator 粉色 HSV 玩家定位 + 卡死脱困。
- **地图识别**（`03` map_classifier.py）：多尺度+图像金字塔模板匹配 + 9 张地图模板 png——运行时识别当前地图，pathing 直接用。
- **传送门坐标真值**（`04`）：花园↔蚁穴/下水道/工厂传送门的小地图格 + 世界坐标双套真值。
- **主插件寻路原版对比**（`07`）：寻路核心（θ*、anti-stuck 斥力场、色点判态）沿用原版；主插件新增分辨率解耦 `set_screen_center`、巡逻点选取 `select_patrol_points`、main.py 340→1351 行战斗层（chase/dodge/pickup/flee/拟人节奏）与 movement/memory/bridge 模块。

### 1.6 可直接落盘的模型资产

| 模型 | 来源 | 用途 | 状态 |
|------|------|------|------|
| `auto_stf/model.pth`（74KB）+ FlorrModel 73→128→64→5 + 6583 条 10Hz 样本（epochs=250, batch=128, lr=1e-3, 80/20） | 03 / 06 | 行为克隆战斗策略网络（输出 6 维动作） | ✅ 权重在仓，可 load_model 直接推理 |
| `afk-det.pt` / `afk-seg.pt` / `afk-seg-pro.pt` | 03 / 02 | AFK 验证窗口检测与迷宫分割 | ✅ 在仓 |
| `stf_det.pt`（Starfish/Jellyfish/Bubble 三类，conf≥0.5） | 03 / 06 | YOLO 怪检测 | ⚠️ **03 仓缺失**（代码引用但文件不在），06 仓另有同名文件需核验版本 |
| `sandstorm.pt` | 02 | Sandstorm 检测 | ✅ 在仓 |

---

## 2. 结构化数据表清单（①协议 ②ID映射 ③中文名 ④颜色 ⑤掉率）

| 表 | 来源 | 内容 | 交付位置 |
|----|------|------|---------|
| **二进制线协议** | 01 protocol.js | 帧=2 字节小端长度前缀；收包 opcode Welcome=0x00…CraftResult=0x13；发包 0xf0 auth…0xf7 snapshotAck；坐标缩放 `NET_COORD_SCALE=64`、角度 /1000、血量 /255；实体快照结构、打包解包函数 | 01 报告 ②节 |
| **怪 type_id 权威表** | 01 game_ids.js L50-94 | 38 怪（beetle=1、ladybug=3、soldierAnt=7…titan=38）+ 特殊网络实体偏移（花瓣=100+type、掉落=180+、7 种 projectile=93-99） | 01 数据提取 JSON |
| **花瓣表** | 01 game_ids.js | 63 花瓣 id→图标→英文名 + 13 个不可堆叠集合 | 01 数据提取 JSON |
| **稀有度体系** | 01 protocol.js RarityColors + 02 wiki | 12 稀有度编号与 RGB 主/次色（Exotic 排序位=7.5，夹在 Ultra 与 Super 间）；wiki 侧 3x 缩放、8×7 掉率矩阵 | 01 数据提取 JSON / 02 数据提取 JSON |
| **中文名全量映射** | 01 zh-Hans.json | 花瓣/怪物/稀有度/UI 中文名（13KB 全量） | 01 数据提取 JSON |
| **天赋数据** | 01 talent_data.js | 天赋 ID 1-17 + 移速倍率链 {3:1.1…9:2} | 01 数据提取 JSON |
| **怪 sprite 参数** | 01 *_sprite.js | 7 个怪绘制参数/碰撞箱/尺寸/血条 | 01 报告 ①节 |
| **小地图材质配色** | 01 client_config.js | 40 项 hex 配色（判地面/区域） | 01 报告 ①节 |
| **掉率表** | 01 drop_rate.h | 99KB / 约 1100 行结构化掉率 | 01 报告 ③节（待专门转录） |
| **稀有度颜色表（实测）** | 04 enemy_detect.py | 9 个真值 hex | 04 报告 |
| **hacks 色表** | 07 The-Script-andnn | 8 档稀有度颜色（Common `#7eef6d`…Super `#000000`）；flowr.fun 16 档扩展 | 07 报告 |
| **YOLO 81 类怪名** | 03 data.yaml | 索引 0–80→怪名 + 90 项 one-hot | 03 报告 |
| **wiki 全站结构化** | 02 wiki.json | 680 篇 wikitext（115 怪/120 花瓣/139 掉落子页/60 区域/158 Fantasy 同人页） | 02 数据提取 JSON |

> 注：`01` 的 game_ids.js 是**私服** ID 体系，与官方 wasm（type_id 1-83 那套）未必一致，整合前须先做映射校准；`02` wiki 为精选子集非全站快照。

---

## 3. 与已偷资产的差异与增量（关键对照）

- **掉率**：已偷 `data\florr_dropchance.json`（10.9KB，wasm 反推）→ 新发现 `drop_rate.h`（99KB 结构化真源，含手工修正）＝**升级替代**。
- **wasm**：`wasm_dump\client.wasm`（9190KB）是**游戏客户端**（46 个 minified 导出）；BetterFlorrSite 的 wasm（1.997MB）是**插件本体 Kotlin/Wasm 产物**（14 个 `__callFunction_` 导出、命名空间 `moe.littleswift:BetterFlorr`、3968 条 kotlin/dom import）——**两者不是新旧版关系**（体积/导出数/符号已复核）。
- **线协议**：主代理已有 `net_protocol.py` 抓包协议（来自 21 万条 WS 抓包）→ FlorrBt protocol.js 提供**逐字段二进制解包实现**，可对照补漏（帧长前缀、坐标缩放 64、血量 /255）。
- **怪物/花瓣静态表**：已偷 `all_mobs.json`/`all_petals.json`/`mob_stats_full.json` 是 wasm 反推的官方数据 → 本批增量主要是 **YOLO 类别表（81 类怪名）**、**不可堆叠花瓣集合**、**wiki 掉落矩阵交叉校验**；FlorrBt 私服数值**不做**替换只用校准参考。
- **检测范式**：现有插件纯 OpenCV HSV → 04 的 canvas 指令解码（真名/血量/世界坐标）与 03 的 YOLO/像素读血是两套**可并行**的新范式。
- **AFK**：现有 afk_solver.py（连线拖动破解）→ 03/02 提供 YOLO+分割+Dijkstra 的整套迷宫求解权重链。
- **零增量项**（如实说明）：maze-tool 空壳（无地图数据）、iogames（混淆不可读，只情报）、05 批 AFK 老脚本（无结构化数据）、florr-mob-bot（网页嗅探，无战斗能力）。

---

## 4. 风险与注意事项

1. **许可证**：`florr_powerful_tools` 为 **GPL v3**——代码勿整段抄进闭源插件；其数据标注为 CC0 可用。其余仓库多为无明确 LICENSE（用前自行确认）。
2. **安全红线**：`iogames` 单文件 3MB 是重度混淆的 "Florr Cheats"，触碰 `cp6_player_id`/`oauth2_dat`/form-urlencoded POST，静态无法还原——**判为高风险恶意特征，只取情报，绝不整合运行**。
3. **泄露凭证**：`florr_powerful_tools\constants.py` 内嵌 base64 三次解码的 **GitHub token**、根目录 `kaggle.json` 为**真 Kaggle key**——勿带入任何发布物/提交。
4. **空壳与缺件**：maze-tool 仅 LICENSE+README（要地图捷径数据需另找上游副本）；`stf_det.pt` 在 03 仓缺失（代码引用但文件不在）。
5. **版本/体系校准**：FlorrBt 是 2026-08 私服自实现，怪 ID 与官方 wasm 体系未必一致（JS 与 C++ 的 Exotic 颜色两边已不一致）；sszone main.py 三层对抗混淆无法静态还原函数级逻辑（已用 config.json 真实取值交付）。
6. **诚实声明**：各子报告均标注了逐行读/仅 grep 的范围；`game.js` 等大文件存在"只 grep 骨架未逐行"的段落（见 01 报告）。

---

## 5. 优先整合路线图（建议顺序）

1. **canvas 解码管线**（04）接入 bridge 抓帧侧 → 替换/并存 combat.py 的 HSV 识别，拿真名+真血+世界坐标（最大收益，改动集中在检测层）。
2. **掉率真源转录**（01 drop_rate.h 约 1100 行）→ 生成 `data\florr_dropchance_v2.json` 替换 wasm 反推版。
3. **行为克隆模型**（03 `auto_stf/model.pth` + 6583 样本 + 桥接协议）→ 先做离线对拍（规则决策 vs 模型动作），验证后再考虑上线。
4. **AFK 迷宫求解**（03/02 权重 + segment_utils Dijkstra 链）替换 afk_solver.py 视觉方案；05 批的 DOM 钩子本地验活后可用作短路优化。
5. **地图识别**（03 map_classifier + 9 模板）接入 map_select.py；传送门坐标真值（04）进 maps 目录。
6. **结构化表入库**（01 中文名/ID/稀有度色、03 81 类名、02 wiki 矩阵）按 1.2 节并入 mob_db.py。
