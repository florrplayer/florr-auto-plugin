# florr-auto-farm

> 来源：`reference-florr-tools/florr-auto-farm/`（82 个 py，约 3MB）。只读本地磁盘分析，未联网。
> 定位：florr.io 的自动寻路 + 自动刷怪 bot。Windows 生产，pyautogui 模拟键鼠 **+ Chrome CDP（`--remote-debugging-port`）注入 Canvas 绘制钩子**。GPL-3.0（greatluca666/florr-auto-farm）。

## 能力摘要

- **双定位管线并行**（这是本项目最有价值的部分）：
  1. **像素/OpenCV 旧路**：300×300 小地图上找黄色玩家点（`PLAYER_MARKER_COLOR="f8de60"`）得到小地图像素坐标；`maps/*.png` 是手工/官方推导的二值可走图（255=可走，0=墙）。Lazy Theta* 寻路。
  2. **Canvas 绘制指令新路**（CDP 注入 `canvas_hook.js`）：拦截 `CanvasRenderingContext2D` 的 `fill/stroke/fillText`，把每一帧的绘制调用序列落到页面 `window.__canvasLog`，Python 侧 `canvas_decode.py` **反解出怪物名字、血量、稀有度颜色、绝对世界坐标、玩家世界坐标、洞口光效**——不需要任何模型，也不猜颜色。
- **自动刷怪主循环**：到区后持续走动（不站桩），输出靠 florr 自带的「反转攻击键」（bot 不按键，直接写 WASM 内存字节让它持续自动攻击）。
- **战斗决策**：flee（躲 Ultra）→ Mythic 近身锁定风筝 → 蚁群保持距离遛 → 追击 → 随机漫游，五级优先级。
- **死亡/换服自愈**：死了自动点继续/开始；连续短局自动 `forceServerID` 换服；蚁穴用「走进回花园的传送门、传送那一下换服」避免出生点重置。
- **多阶段进场路线**：花园→踩洞口光效→蚁穴（/下水道/工厂），像素判据 + canvas 世界坐标双重复查真传送。

---

## 可偷数据清单

### ① 可直接整合进现有插件的算法/数据

> 现有插件走 OpenCV HSV 像素识别（`combat.py` 的 `classify_mob`/`RARITY_SIZE_FACTOR`、`mob_db.py`、`memory_reader.py`、`bridge_server.py`/`bridge_combat.py`、`afk_solver.py`、`drop_table.py`、`spawn_data.py`）。下表每条都落到「偷哪个函数 → 替换/补充哪个文件」。

| # | 来源文件 / 函数 | 与现有插件的映射 | 具体怎么用 |
|---|---|---|---|
| 1 | `canvas_hook.js`（页面侧）+ `cdp_bridge.inject_canvas_hook/drain_canvas_log`（`cdp_bridge.py:436/406`）+ `canvas_decode.py` 全套 | **替代/升级** `memory_reader.py` + `bridge_combat.py` 的取数层 | 现有插件若也是浏览器注入路线，直接装这个 hook（只读、原样放行原调用），把每帧 `fill/stroke/fillText` 记录回传；不再截图像素猜。若现有插件是纯截图路线，则这是一条可叠加的"高精度真值通道"。 |
| 2 | `canvas_decode.mobs_from_frame()`（`canvas_decode.py:618`） | 输出 dict 直接当 Mob 数据喂 `combat.py` 下游 | 每只怪输出 `{name, rarity, rarity_color, hp, sx, sy, x, y}`（sx/sy=屏幕坐标，x/y=绝对世界坐标）。把它的返回值包成现有 Mob 对象即可，**`classify_mob` 的颜色/形状猜测可整体退役**。 |
| 3 | `canvas_decode.camera_from_frame()`（L298）+ `screen_to_world()`（L420） | **替换** `combat.py`/`memory_reader.py` 里的"地图坐标换算" | 坐标换算公式（见 ②）：世界坐标直接由游戏绘制给出，不需要自己标定缩放。 |
| 4 | `enemy_detect._RANK_BY_RARITY_COLOR`（`enemy_detect.py:786`） | **校准/替换** `combat.py` 的 HSV 稀有度颜色阈值 | 这是游戏名牌文字 fill 色的**真值表**（9 个色值，见 ②）。现有 HSV 阈值按它收边；`RARITY_SIZE_FACTOR`（靠尺寸猜稀有度）可废弃——canvas 直接给 rarity 字符串。 |
| 5 | `enemy_detect._RANK_BY_RARITY_WORD`（L825） | 同上的兜底信源 | 名牌上的中文/英文稀有度词（传奇/神话/ultra…）当颜色识别失败时兜底，两信源冲突以颜色为准。 |
| 6 | `enemy_detect._SPECIES_ALIASES`（L747）+ `MAP_SPECIES`（L726） | **补充** `mob_db.py` 的中文名/物种枚举 | 中文客户端怪物名→slug 全表（见 ②），新图做索敌只需往 `MAP_SPECIES` 加 slug。 |
| 7 | `enemy_detect.classify_action()`（L42）+ `_AVOID_PAIRS`/`_CAUTIOUS_PAIRS`（L35-39） | **补充** 战斗决策表（`bridge_combat.py`/决策层） | Ultra 蝎子/甲虫=AVOID（打不过就跑），Ultra 沙尘暴/仙人掌/沙蜈蚣/火蚁=CAUTIOUS（保持距离接战），其余 <Ultra 全 ENGAGE，未覆盖的超稀有兜底 AVOID（"失败方向选别惹"）。 |
| 8 | `enemy_detect.MYTHIC_KITE_SPECIES`（L66）+ `pick_mythic_target`（L134） | 新增"贴脸 Mythic 先清"走位策略 | beetle/火蚁=strafe 环绕（半径 `MYTHIC_STRAFE_RADIUS=180`px，径向修正 `K_RADIAL=0.8`），蝎子/沙蜈蚣=ram 直冲，仙人掌=hold 站桩保持 220px；engaged 650px / release 850px 迟滞。 |
| 9 | `enemy_detect.find_swarm()`（L506）+ `swarm_move_target()`（L545） | 新增"蚁群保持距离遛" | 以每只为心数 100px 内怪数找最大堆；按离玩家最近那只的距离 d：d>keep×1.2 靠过去、d<keep×0.8 退、中间停。适合怪多密刷的图。 |
| 10 | `enemy_detect.ApproachTracker`（main.py:846 `_APPROACH`） | 新增"究极冲过来了"提前躲 | 跨扫描用世界坐标速度跟踪 AVOID 怪是否在逼近玩家，比单纯距离阈值提前触发 flee。 |
| 11 | `flee_planner.plan_flee()`（`flee_planner.py:116`） | **升级** 现有 flee（当前多半是"背离危险像素"） | 在自己周围 ±20 格（`HORIZON=20`≈4300 世界单位）做 Dijkstra，选"自己比追兵早到 `SAFE_MARGIN=1` 格"的格子当逃点，绕开怪群（`CROWD_BLOCK_R=0.8`），带 `prefer` 保持上一拍方向不抖动。 |
| 12 | `main._steer_clear_of_walls()`（`main.py:978`） | flee 方向的避墙修正 | 从理想背离方向起按 `(0,±15,±30,...,±90)°` 试到第一个前方 `FLEE_WALL_CLEARANCE=3` 格全可走的方向，免得躲怪一头顶墙。 |
| 13 | `main.lazy_theta_star()`（`main.py:80`）+ `line_of_sight()`（L57，Bresenham） | 若现有插件无寻路可直接抄 | 8 邻域 A* + 可视线松弛（`current.parent` 与 neighbor 有 LOS 就直连 parent），路径点比 A* 少、能斜穿。 |
| 14 | `main.move_to_position()`（`main.py:352`）的到达/停滞判据 | 替换"到了没/卡住没"的判定 | 到达半径 `ARRIVE_RADIUS=5` 格；冲过头（dist>last+1.5 且 last≤2×ARRIVE）直接算到；停滞用"累计最佳距离没缩短 `progress_epsilon=1.5` 容差带"而非"距离相等"（位置读数有量化噪声，== 永远攒不起来）。 |
| 15 | `utils.execute_anti_stuck()`（`utils.py:343`）+ `_map_aware_escape()`（L312） | 防卡死脱困 | 在二值图上 BFS 找"净空最大"的方向硬闯几步；墙色没标定的图退化成随机方向。 |
| 16 | `florr_settings.INVERT_ATTACK_ADDR=0x53430E` / `INVERT_DEFENSE_ADDR=0x534310`（`florr_settings.py:20-21`） | 若走 WASM/页面内存路线可直接用 | bot 不按攻击键，靠把这两个字节写成 1 让 florr 自动持续攻击/防御；每轮进游戏 florr 会从账号数据盖回，必须每轮重写。 |
| 17 | `map_routes.py` 传送门世界坐标（见 ②） | 若现有插件要做进场/换服路线直接用 | 洞口/回巢门的小地图格 + 绝对世界坐标双套真值。 |
| 18 | `test_frames/*.json`（17 个真实帧） | 给 `combat.py` 当回归测试夹具（见专节） | 离线喂帧断言识别结果，不用开游戏。 |

### ② 协议/ID 映射/中文名等结构化表（含真实样例）

**稀有度文字颜色 → 档位**（`enemy_detect.py:786`，主信源；名牌文字的 fill 色）：

| 颜色 hex | 档位 rank | 中文名 |
|---|---|---|
| `#7EEF6D` | 0 Common | 普通 |
| `#FFE65D` | 1 Unusual | 罕见 |
| `#4D52E3` | 2 Rare | 稀有 |
| `#861FDE` | 3 Epic | 史诗 |
| `#DE1F1F` | 4 Legendary | 传奇 |
| `#1FDBDE` | 5 Mythic | 神话（青） |
| `#FF2B75` | 6 Ultra | 究极（粉） |
| `#2BFFA3` | 7 Super | 超神 |
| `#555555` | 9 Unique | 独特 |

稀有度词兜底（`_RANK_BY_RARITY_WORD`）：中文 `普通/罕见/稀有/史诗/传奇/神话/究极/超神/独特`，英文 `common/unusual/rare/epic/legendary/mythic/ultra/super/eternal/unique`。

**中文怪物名 → slug**（`_SPECIES_ALIASES`）：

| 中文名 | slug | 中文名 | slug |
|---|---|---|---|
| 沙尘暴 | sandstorm | 幼蚁 | baby_ant |
| 仙人掌 | cactus | 工蚁 | worker_ant |
| 甲虫 | beetle | 兵蚁 | soldier_ant |
| 蝎子 | scorpion | 蠕虫 | worm |
| 蜈蚣 | sand_centipede | 蚁卵 | ant_egg |
| 火兵蚁/火蚁 | soldier_fire_ant | 蚁后 | queen_ant（未实机验证） |
| 瓢虫 | sandstorm（乱入高价值怪，借最高优先级） | 火蚁穴 | 出怪口建筑，**忽略**不打 |

**血条三层结构**（`canvas_decode.py:28-30`，真实帧实测）：
- 底层 `#222222`（HEALTHBAR_BG，满宽黑条）
- 中层 `#DD3434`（HEALTHBAR_DAMAGE，红色 = 已掉血）
- 顶层 `#75DD34`（绿色 = 剩余血条）；另有窄的青色 `#42E3F5` 副条。
- **hp = 绿色条覆盖比例**。样例（desert_ultra_44mobs 帧）：同一锚点三条 stroke，`lw` 分别 10/6/7，`alpha=0.2` 时是低血/残留条。

**关键常量真值**：
- 玩家花身色 `#FFE763`（PLAYER_BODY_COLOR，小地图金点同色）；花身描边圈/身体圈半径比 `1.128`（`_AVATAR_RING_RATIO=(1.10,1.16)`）。
- 名牌配对窗口：`LABEL_MAX_DX=120`、dy∈`[-20, 600]` 屏幕像素；名牌永远在血条下方。
- 小地图像素/世界单位：`MINIMAP_WORLD_SCALE = {anthell: 0.00461708941, garden/desert/ocean/jungle: 0.00469101826}`；通用公式 `300/(格数×512+2000)`（1 格=512 世界单位）。
- 区域名映射 `ZONE_LABELS`：`{"蚂蚁地狱":"anthell","沙漠":"desert","花园":"garden",...}`（HUD 文字）。
- 传送门坐标（`map_routes.py`）：花园→蚁穴门 小地图`(133,234)`/世界`(27392,48896)`；蚁穴→花园门 `(121,102)`/`(25344,21248)`；下水道门 `(86,185)`/`(17408,38600)`；工厂门 `(215,150)`/`(44987.9,30975.8)`。
- WASM 开关地址：反转攻击 `0x53430E`、反转防御 `0x534310`。

**坐标换算公式**（可复现，`screen_to_world` L420）：
```
zoom        = 第一条非小地图、stroke=="#222222" 的血条记录的 m[0]   # 实测沙漠 0.315 / 蚁穴 0.45
player_world = ((x - m[4])/m[0], (y - m[5])/m[3])                   # 小地图 #FFE763 金点反解
world_x = player_world.x + (screen_x - player_screen.x) / zoom
world_y = player_world.y + (screen_y - player_screen.y) / zoom
```
其中 `m=[a,b,c,d,e,f]` 是 Canvas CTM 矩阵（`m[0]=a` 缩放、`m[4]=e`、`m[5]=f` 平移）。

### ③ 与已偷资产的差异与增量

- 已偷的 `wasm_dump/`、`data/` 下 JSON（all_mobs/all_petals/mob_stats_full/florr_dropchance/wasm_map_data）都是**静态数值表**（血量/掉率/地图数据）。
- 本仓库新增的是**运行时识别管线本身**：怎么从游戏页面实时拿到每只怪的名字/血量/稀有度颜色/世界坐标（canvas hook + decode），以及**决策策略表**（动作分档、Mythic 风筝、蚁群遛、Dijkstra 逃跑）。
- 增量真值：稀有度颜色 hex 表（现有 HSV 是猜的，这是游戏实际 fill 色）、中文物种名映射、血条三层色、世界坐标↔小地图缩放真值、传送门双套坐标、两个 WASM 开关地址。
- 注意：现有插件的 `RARITY_SIZE_FACTOR`（靠尺寸猜稀有度）在这套新管线里**没有对应物且被刻意绕过**——canvas 直接给 rarity，不需要尺寸倍率。

---

## test_frames 测试基准说明（结构+如何复用）

**顶层结构**：
```json
{ "map": "desert", "frame": 80, "note": "...可选", "raw": [ ...绘制记录... ] }
```
- `map`：生态区名（anthell/desert/garden…），可为 null。
- `frame`：游戏帧号。
- `raw`：该帧全部 canvas 绘制记录数组（185~578 条不等）。

**每条 raw 记录字段**（实测）：
```json
{"frame":80,"op":"stroke","x":633.5,"y":374.7,"r":null,
 "bbox":[x1,y1,x2,y2],"n":2,"fill":"#FFFFFF","stroke":"#222222",
 "lw":10,"alpha":0.2,"m":[0.315,0,0,0.315,633.5,317.1]}
```
- `op` ∈ `fill`(圆形实体，`r`=半径) / `stroke`(血条线段，`r`=null) / `text`(文字，多一个 `text` 字段)。
- `m`：CTM 矩阵；`bbox`：包围盒；`lw`：线宽；`alpha`：透明度（0=刚渲染/残留，识别时主要信 alpha≈1 的）。

**17 个帧清单（含用途标注）**：
| 帧文件 | map | 记录数 | 价值 |
|---|---|---|---|
| `desert_ultra_44mobs.json` | desert | 451 | **密集帧基准**：解出 44 只怪，含神话/传奇/究极沙尘暴+蝎子 |
| `desert_mythic_26mobs.json` | desert | 295 | Mythic 风筝逻辑基准（26 只） |
| `anthell_gold_blob_bigger_than_self.json` | anthell | 578 | **历史 bug 回归**：金色圆比花身大，旧逻辑误选它当目标 |
| `anthell_gold_ring_55px.json` | anthell | 519 | 同上的另一录段 |
| `anthell_other_player_radius_noise.json` | anthell | 431 | **误检回归**：6 个同色花身，别人半径大 1.5e-5，旧逻辑选错"自己" |
| `self_tint_poison/red/pale/dimgold/rotated_*`（6 帧） | desert | 211~420 | 花身中毒/变色/旋转时**自己锚点识别**回归 |
| `self_hitflash_red/white.json` | garden | 230 | 受击闪白/闪红不误判 |
| `afk_popup_20260920.json` | null | 314 | AFK 弹窗帧 |
| `zone_garden/anthell_20260930.json` | null | 185/398 | 区域名 HUD 帧 |

**复用方法（已实跑验证可行）**：
```python
import json, sys
sys.path.insert(0, r"...\florr-auto-farm")
import canvas_decode as cd
data = json.load(open(r"...\test_frames\desert_ultra_44mobs.json", encoding="utf-8"))
cam  = cd.camera_from_frame(data["raw"], best_effort=True)
# → {'zoom':0.315, 'player_world':(5178.4,6529.1), 'player_screen':(960,472.5), 'approx':False}
mobs = cd.mobs_from_frame(data["raw"], cam)
# → 44 只，每只 {name:'沙尘暴', rarity:'传奇', rarity_color:'#DE1F1F',
#                 hp:1.0, sx:633.5, sy:317.1, x:4142.0, y:6035.7}
```
**喂给现有 combat.py 做回归**：把 `mobs` 列表当作"真值检测结果"，喂给现有 `classify_mob`/目标选择/flee 决策层，断言：
1. `desert_ultra_44mobs` → 解出 44 只、稀有度档位颜色与名字对得上；
2. `anthell_gold_blob_bigger_than_self` → **不得**把那枚无描边的金色圆选为目标（`note` 里记录的旧 bug）；
3. `anthell_other_player_radius_noise` → 6 个同色花身时选中的"自己"必须是带描边圈/无等级字的那具；
4. `self_tint_*` → 花身变色时 `camera_from_frame` 仍能解出玩家锚点。

---

## 风险/注意

- **账号风险**：脚本自己声明可能违反 florr.io ToS，有封号风险；且会 `taskkill /IM chrome.exe /F` 强杀所有 Chrome、开 `--remote-debugging-port` + `--remote-allow-origins=*`（本机调试端口对任意网页开放）。
- **强依赖 Chrome CDP**：canvas 解码/换服务器/写 WASM 开关全部走浏览器调试接口，不是内存读取；Edge/Firefox 不行。
- **稀有度颜色表是硬编码**：florr 改版换色会全线退化成 Common（作者自己也标注了这个风险，所以才加了"名牌词"兜底）。
- **部分值未实机标定**：蚁后（queen_ant）是按译名猜的没抓到过；下水道/工厂的小地图缩放是按官方 .tmj 公式预测的；`ANTHELL_HOLD_PX_BY_SPECIES` 等走位半径作者标注"未标定"。
- **版本耦合**：WASM 地址 `0x53430E/0x534310` 随 florr 更新会失效，失效时 bot 会在日志警告（需要手动勾设置）。
- **与现有插件架构差异**：这套是"读图绘制指令"，比 OpenCV HSV 截图路线准得多，但前提是你也能往 florr.io 页面注入 hook（即浏览器路线）；纯截图路线只能复用它的**色值表/决策表/坐标公式/test_frames 夹具**，用不了实时解码。
