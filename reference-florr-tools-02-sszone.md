# florr-auto-sszone（SS 区自动刷）

> 来源：`reference-florr-tools/florr-auto-sszone`（Shiny-Ladybug 的 Desert 区 Sandstorm 自动刷，28MB）
> 只读本地磁盘，未联网。配套数据文件：`reference-florr-tools-02-sszone-数据提取.json`

## 能力摘要

这是一个 **Desert（沙漠）区刷 Sandstorm（沙尘暴，含 Super/Mythic 稀有度）** 的全自动挂机脚本。运行方式：浏览器全屏（F11）+ 地图最大化（M）+ 窗口置顶，脚本截屏后用 **YOLOv10 目标检测** 找 Sandstorm，按稀有度加权选择目标、保持安全距离追击，自动换装/回血，并通过 PaddleNLP+智谱 AI 自动回频道消息、自动处理 AFK 验证。鼠标挪到屏幕边缘即停。

- **技术栈**（`py39-requirements.txt`）：`ultralytics==8.3.65`（YOLOv10 检测）+ `opencv-python` + `pyautogui` + `paddlepaddle/paddlehub/paddlenlp`（OCR/NLP）+ `jieba` + `zhipuai`（ChatGLM 聊天）+ `lap`（匈牙利算法）+ `rdp` + `pycryptodome`。
- **识别方式**：**不是**纯颜色阈值，而是「YOLO 深度检测（怪/AFK）+ OpenCV 模板匹配（换装 UI）+ NLP/OCR（聊天/验证文字）」三段式。
- **main.py 形态**：单文件 205KB，但经过 **三层对抗性混淆**——外层 `pyobfuscate.com` 引导（base64+自定义字母表）→ 中层 pickle 反序列化重建 `ast.Module` → 内层深度嵌套 lambda 解释器。我已成功脱到第二层（530KB AST 载荷），但内层 VM 递归深度极大（128MB 线程栈仍栈溢出），真实业务函数名/行号无法静态还原。**所有可调数值来自 `config.json`（即脚本作者暴露的真实参数）与依赖清单**，下文均为真实取值。

### main.py 脱壳过程记录（可复现）
1. 外层 `main.py` 仅 76 行，第 6–7 行是 75KB 加密串、第 51–55 行是 ~40KB hex blob。尾部 `llIIlIlllllIIlllII` 用自定义 base64 字母表（第 58–59 行）解码后喂给 `exec`。
2. hook `builtins.exec`/`compile` 后拿到第二层载荷 **530028 字符**（`_payload_0_530028.py`）。
3. 第二层用 `import pickle; ________=pickle.loads(__0)` 逐层 `________.body[i]=pickle.loads(__0)` 重建一棵 AST（见 exec log：`body/handlers/targets/args/keywords` 全是 AST 节点属性）。
4. 在 `compile(ast_module)` 处用 `ast.unparse` 本可还原源码，但该 VM 递归深度在 128MB 栈下仍栈溢出（used 131MB），属刻意抗分析。故函数级算法以「架构推断 + config 常量」交付。

## 可偷数据清单

### ① 可直接整合进现有插件的算法/数据

现有插件已有 `combat.py`（OpenCV HSV `inRange` 颜色检测 + `RARITY_SIZE_FACTOR` + `classify_mob`）、`mob_db.py`、`memory_reader.py`、`bridge_*.py`、`afk_solver.py`。可偷点如下：

1. **稀有度目标加权选择（贪心 + 权重）** — 来源 `config.json → farmConfigs.weights`。
   - 逻辑：对检测到的所有 Sandstorm 按 `Weights[稀有度]` 加权排序选目标，`Legendary=0.6 / Mythic=3.7 / Ultra=1.8`，可在 config 里调（作者原话：不想要 Mythic 就调小 `Mythic` 权重）。
   - **怎么用**：现有 `combat.py` 的 `classify_mob` 出稀有度后，直接套这套权重做目标排序，替换你现在的固定优先级；把它做成 `mob_db.py` 里的一张 `rarity_weight` 表。
2. **安全追击距离公式 `safeDistanceK`** — 来源 `config.json`：`attackMinimumDist=350`（px）、`safeDistanceK=0.2`。
   - 逻辑：保持与目标的距离在「最小攻击距离 × (1+safeDistanceK)」附近，打不到就调小 K。可作为 `combat.py` 追怪走位的阻尼系数。
3. **目标尺寸阈值筛稀有度** — 来源 `config.json → farmConfigs.sizes`：`Mythic=170px / Ultra=300px`（框像素边长）。
   - **怎么用**：现有插件已有 `RARITY_SIZE_FACTOR`（按大小推稀有度），这里给了两个真实锚点（Mythic 框≈170px、Ultra 框≈300px @ 全屏），可直接校准你的 size→rarity 映射表。
4. **匈牙利任务分配（`lap`）** — 来源 `py39-requirements.txt` 依赖 `lap`（LAPJV 线性分配）。
   - 逻辑：多 Sandstorm 同时出现时，把「检测框」与「玩家可攻击槽位/移动目标」做全局最优匹配，避免来回抖。可移植成 `smart_combat.py` 的多目标分配器。
5. **配置驱动的换装/回血策略** — 来源 `config.json → equipPetals`：antennae(slot1)/rubber(slot6)/heal(slots 3,7,8,阈值 HP<60%)/powder(slot5)/fang(slot9,默认关)。
   - **怎么用**：现有插件若有桥接按键（`bridge_combat.py`），可直接抄这套槽位布局与「血量阈值 60% 触发 heal」的状态机。
6. **模板匹配换装 UI** — 来源 `equips/{ante,fang,heal,powder,rubber}.png`（5 张小图）。
   - 逻辑：`cv2.matchTemplate` 在背包界面定位花瓣图标 → 点对应槽位。可补现有插件「不会自动换装」的空白。

### ② 协议/ID映射/中文名等结构化表（含真实样例）

来源 `data/wiki.json`（680 篇 MediaWiki wikitext，**非全站快照**，是 A–Y 主游戏内容精选 + 158 篇 `Fantasy:` 同人页）。统计：怪物 infobox **115**、花瓣 infobox **120**、掉落子页 **139**（`Mob/Drop Petal`）、区域 **60**。

- **怪物数值 ID**（来自 `Mobs` 列表页表格，与 wasm/协议 ID 对齐）：`Rock=1, Cactus=2, Ladybug=3, Bee=4, Baby Ant=5, Worker Ant=6, Soldier Ant=7 …`。
- **稀有度缩放**：相邻稀有度属性 **×3**（Common→Unusual→Rare…）；合成成功率 `64%/32%/16%/8%/4%/2%/1%`（逐级）；掉落物地面留存 `Common15s/Unusual30s/Rare40s/Epic50s/Legendary60s/Mythic+120s`。
- **Sandstorm（本脚本刷的目标）逐稀有度真实属性**（样例，Common 基准 HP=125/体伤=40/护甲=0.8）：
  - `Legendary: HP=50625, 体伤=3240, 护甲=64.8, XP=307`
  - `Mythic: HP=303750, 体伤=9720, 护甲=194.4, XP≈4.7k`
  - `Ultra: HP=3,645,000, 体伤=29160, 护甲=583.2, XP≈29.7k`
  - `Super: HP=164,025,000, 体伤=87480, 护甲=583.2, XP≈3.2m`
- **掉率矩阵（怪物稀有度 × 花瓣稀有度，单位 %）真实样例**——Sandstorm→Sand：
  - Common 怪掉 Common 花瓣 **45.5%**、Unusual **10.1%**
  - Mythic 怪掉 Epic **21.2%**、Legendary **78.3%**、Mythic **0.5%**
  - Ultra 怪掉 Legendary **91.8%**、Mythic **8.9%**、Ultra **0.03%**
  - Super 怪掉 Mythic **85.7%**、Ultra **14.3%**
- **Desert 区域刷怪分布**（真实描述）：左上=大量 Legendary/Mythic Sandstorm；右上=频繁 Legendary 沙漠怪；右下=Mythic/Ultra 且 Yggdrasil 掉率最高；底部=频繁 Ultra、最难、有 Developer Statue。
- **`data/user_dict.txt`**：jieba 自定义分词词典，680 行，格式 `"词条名 n"`（词性=名词），即全部 wiki 词条名。用途：PaddleNLP 解析游戏内聊天/验证文字时正确切出 "Sandstorm/Yggdrasil/Antennae" 等专有名词。

### ③ 与已偷资产的差异与增量（对照）

已偷资产：`wasm_dump/client.wasm` + `all_mobs.json(98KB)`、`all_petals.json(126KB)`、`mob_stats_full.json(107KB)`、`florr_dropchance.json(10.9KB)`、`maps_list.json`、`mob_spawn_data.json` 等。

| 维度 | 已偷资产（wasm/JS 逆向） | 本仓库新增量 |
|---|---|---|
| 怪物/花瓣属性 | `mob_stats_full.json` 已是结构化数值表 | wiki.json 是 **wikitext 叙述 + 表格**，多了行为描述/刷怪区域分布/策略文字，数值与 wasm 一致，可作交叉校验 |
| 掉率 | `florr_dropchance.json(10.9KB)` 结构化 | wiki 的 **139 张「怪稀有度×花瓣稀有度」完整矩阵**（如上面 Sandstorm→Sand 8×7），覆盖更全、可补 wasm 缺失格 |
| 地图 | `maps_list.json`/`wasm_map_data.json` | wiki 60 篇区域 infobox 给了 **每区细分角落刷怪稀有度倾向**（如 Desert 四个角），wasm 里没有这种「角落级」语义 |
| 怪物 ID | `wasm_mob_list.json` | wiki `Mobs` 列表页的 ID（1=Rock…）可与 wasm ID 映射互相印证 |
| 检测范式 | 现有 `combat.py` 全靠 OpenCV HSV `inRange` 颜色阈值 | 本脚本用 **YOLOv10 模型**（4 个 .pt）做检测——这是**质的差异**：你现有插件没有任何深度学习权重；若要引入，可直接拿 `models/*.pt` 当现成检测器 |
| AFK 验证 | 现有 `afk_solver.py` | 本仓库有 **3 个专用 AFK 模型**（afk/afk-det/afk-seg-pro，检测+分割），比纯 OCR 更稳 |
| 路径规划 | 现有插件靠 wasm 内存/桥 | 本脚本用 **config 格子坐标多边形 + 目标权重 + 匈牙利分配**，与你的 `memory_reader` 路线完全互补 |

**核心增量一句话**：它不补「游戏数据表」（那部分你 wasm 已有且更干净），它补的是「**一套现成的 YOLO 检测权重 + 配置化刷怪走位参数 + AFK 模型**」——这是你现有 OpenCV-only 栈没有的东西。

## 风险/注意

1. **main.py 强对抗混淆**：三层 VM、运行时重建字符串、递归栈溢出。不要尝试在本机直接 `python main.py` 脱壳；本报告的函数级细节为架构推断，非逐行反编译结果。若后续要拿到精确阈值，需在装齐 torch/ultralytics 的环境里让真实模型跑通后 hook 调用，而非静态读码。
2. **模型权重版权/合规**：4 个 `.pt` 是作者训练的检测模型，直接分发/集成有版权与 ToS 风险；florr.io 对自动化/外挂有封号机制（README 提到 Ban、AFK Check）。
3. **wiki.json 含 158 篇 `Fantasy:` 同人页**，非真实游戏数据，整合时必须按前缀过滤，否则会把同人设定当官方数值。
4. **数值时效**：wiki 是某一时刻的快照，版本更新后掉率/属性可能变动；与 wasm 数据冲突时以 wasm 为准。
5. **AI 聊天自动回复**（zhipuai + `aiChat.whitelistSender=["M28"]`）会真实发消息，集成前务必关掉，避免账号行为异常。
