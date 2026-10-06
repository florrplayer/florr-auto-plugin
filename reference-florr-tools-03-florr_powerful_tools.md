# florr_powerful_tools

> 扫描对象：`C:\Users\intel\Downloads\florr-auto-pathing-main\reference-florr-tools\florr_powerful_tools`
> 只读本地磁盘、未联网。统计由脚本实际读取得出（命令见文末“附：统计命令”）。
> 仓库体量：1099 个文件 / 194.8 MB（其中 `florr_mob_detector_training_package.tar.gz` 单文件 82.5 MB，两个 `.gz` 共 78.7 MB，261 张 png 共 87.5 MB）。

---

## 能力摘要

这是一个**多项目聚合仓库**（作者 PANP2010 / Shiny-Ladybug，README 标注 **GPL v3**），把 6~7 个 florr.io 自动化子项目打包在一起。核心能力四块：

1. **AFK 验证自动通过**（`florr-auto-afk-main`）：YOLO 检测 AFK 弹窗 `[Window/Start/End]` → YOLO 分割路径 mask → `skimage.skeletonize` 骨架化 → `heapq` Dijkstra 沿骨架寻路 → `rdp` 道格拉斯-普克平滑 → 鼠标沿路径移动。这是全仓库最成熟、带真实权重（`afk-det.pt` 5.4MB / `afk-seg.pt` 5.9MB）的部分。
2. **战斗 AI（行为克隆 MLP）**（`florr-auto-framework-pytorch-macos`）：YOLO 检怪 + 一个 73→128→64→5 的 MLP，把 `{血量, 花瓣角度, 最近10只怪}` 直接回归成 `{move_x, move_y, attack, defend, yinyang}`。**已训练权重 `auto_stf/model.pth`（72.7KB）在仓里可直接加载**。配套 6583 条 `state→action` 训练样本。
3. **桥接协议**：油猴脚本 `extension.js`（553KB，**重度混淆**）注入 florr.io，通过 WebSocket / FastAPI:8000 把网页内的 `health / health_speed / inventory / 聊天消息 / 花瓣坐标` 推给 Python，Python 回推 `showNotification / 换花瓣` 命令。**这正是你 bridge_server/bridge_combat 的同构思路，可直接对照协议字段。**
4. **数据与知识**：81 类怪的 YOLO 类别表（`data.yaml`）、90 类怪 one-hot 表、固定像素坐标读血量算法、9 张地图模板 + 多尺度模板匹配识别地图、241 篇 fandom wiki 爬取稿、87 张怪图标。

> 关键缺口：`dataset_utils.py` 里 `model = YOLO("./models/stf_det.pt")` 引用的**怪检测权重 `stf_det.pt` 不在仓中**；仓里只有 AFK 专用的 `afk-det.pt / afk-seg.pt`。即“能跑 AFK，不能开箱跑战斗怪检测”。

---

## json 数据文件清单

共 **21 个 `.json`** + 4 个 `.jsonl`（结构单独列）。下表条目数/字段均为脚本 `json.load` 后实测。

| 文件（相对仓库根） | 体积 | 条目数 | 顶层字段 | 用途判断 |
|---|---|---|---|---|
| `kaggle.json` | 64 B | 2 | `username, key` | **Kaggle API 凭证（真密钥）** |
| `florr-auto-afk-main/config.json`（及 macos 同名副本 2544B） | 2544 B | 6 键 | `runs, exposure, gui, extensions, advanced, yoloConfig` | 主运行配置（AFK 行为、OBS、量化、模型路径） |
| `florr-auto-afk-main/conversation.json` | 4531 B | list[4] | `role, content` | AI 聊天系统提示词（猫娘人设，见风险） |
| `florr-auto-afk-main/extension.swap.json` | 96 B | 4 键 | `block_alpha, send, connected, aspac`(bool) | 油猴扩展运行时开关状态 |
| `…/extensions/magnet/registry.json` | 276 B | 8 键 | `name, description, author, version, enabled, events, schedule, args` | 扩展清单（magnet，参数=`inventory`） |
| `…/extensions/sponge/registry.json` | 363 B | 8 键（同上） | events=`florrHealth`，args=`health_ping['health']` | 扩展清单（低血换海绵花瓣） |
| `…/extensions/superping/registry.json` | 350 B | 8 键（同上） | events=`florrMessages`，args=`chat_ping` | 扩展清单（自动聊天） |
| `florr-auto-afk-main/gui/backgrounds/structure.json`（+macos 副本） | 1931 B | list[14] | `name, path, weight, type` | 启动页背景轮换表（样例 `{"name":"Crystal",…,"weight":1,"type":"tile"}`） |
| `florr-auto-framework-pytorch-macos/config.json` | 155 B | 6 键 | `model_name, input_dim, output_dim, batch_size, epochs, dataset_path` | 训练超参（input_dim=73, output_dim=5） |
| `…/auto_stf/config.json` | 94 B | 5 键 | `model_name, input_dim, output_dim, batch_size, epochs` | **已训模型元信息（配 model.pth 加载用）** |
| `florr_knowledge_base/data/index.json` | 4946 B | 5 键 | `mobs:[75], petals:[74], areas:[33], mechanics:[12], other:[47]` | wiki 索引（分类→标题名列表） |
| `florr_knowledge_base/data/metadata.json` | 221 B | 4 键 | `last_update, total_entries, stats{new/updated/skipped/failed}, source` | 爬取任务元数据 |
| `florr_knowledge_base/data/wiki.json` | **1.87 MB** | **list[241]** | `title, content, url, updated_at, categories` | **fandom wiki 全文爬取库**（wikitext 格式，含模板语法） |
| `mob_wiki_monitor/data/known_mobs.json` | 1475 B | dict[6] | 每键 `{wiki_name, image_url, download_time}` | 6 只怪的 wiki 图标 URL 映射（garbage/silverfish/ghost/crystal/acid_bubble/queen_termite） |
| `overlay/ui_config.json` | 89 B | 3 键 | `position:[x,y], lock_position, opacity` | 悬浮窗位置配置 |
| `upload_package/dataset-metadata.json` | 317 B | 6 键 | `title, id, licenses:[CC0-1.0], keywords[5], collaborators, data` | Kaggle 数据集发布元数据（许可 CC0-1.0） |

> macos 目录下另有 6 个 json（`config/structure/3×registry`），与 Windows 版**逐字节重复**，不重复计。

### jsonl 训练数据（脚本实测行数）

| 文件 | 体积 | 记录数 | 字段 | 用途 |
|---|---|---|---|---|
| `florr-auto-framework-pytorch-macos/data/dataset_new_.jsonl` | 7.0 MB | **6583** | `state{health, degree, mobs[[dx,dy,w,h,c1,c2,c3]×≤10]}, action` | **行为克隆主数据集**（喂 `FlorrDataset`） |
| `florr_assistant/data/training/data_anthell_20260222_123510.jsonl` | 256 B | 1 | `state{health_percent,health_florr,degree,yinyang,mobs,mob_count}, action{move_x,move_y,attack,defend,yinyang}, timestamp, map` | Ant Hell 采集片段 |
| `…/data_anthell_20260222_123540.jsonl` | 21.9 KB | 85 | 同上 | 同上 |
| `…/data_anthell_20260222_123607.jsonl` | 19.0 KB | 74 | 同上（样例 `health_florr:1048, move_x:-0.8086, attack:1.0`） | 同上 |

主数据集首条原文：`{"state":{"health":0.7499,"degree":0.1840,"mobs":[[0.0708,0.0833,0.0875,0.15,1,0,0],[-0.0781,-0.2120,0.05625,0.1324,1,0,0],…]}, …}` —— 即“玩家相对怪的归一化偏移 + 框宽高 + 3 维 one-hot”。

---

## 高价值 py 模块清单

按 AI/检测/控制/数据处理分类。“可偷程度”★ 越高越值得直接搬进你现有插件。

| 文件 | 职责 | 入口函数/类 | 关键依赖 | 可偷程度 |
|---|---|---|---|---|
| `florr-auto-framework-pytorch-macos/dataset_utils.py` | **状态编码+MLP+读血+模板匹配，全仓库信息密度最高** | `FlorrModel`, `state2dataset()`, `check_health()`, `one_hot_encode_mob()`, `get_action()`, `find_image()` | torch, ultralytics, pyautogui, cv2, jsonlines | ★★★★★ |
| `…/inference.py` | 5 线程实时战斗机器人：YOLO检怪 / MLP推理 / 悬浮窗 / 鼠标动作 / **FastAPI:8000 收花瓣角度** | `yolo_thread, inference_thread, action_thread, rotation_server_thread` | fastapi, pynput, pyautogui, ultralytics | ★★★★★ |
| `…/create_dataset.py` | 把游戏帧录制成 `state/action` jsonl 训练数据 | （采集主循环） | pyautogui, ultralytics | ★★★★ |
| `florr-auto-afk-main/segment_utils.py` | **AFK 求解核心**：弹窗/起止点检测、mask-IoU 选路径、骨架 Dijkstra、鼠标沿路径走、GitHub 自动上传数据集 | 类 `AFK_Path / AFK_Segment / AFK_BW`；`detect_afk_window`, `detect_afk_things`, `get_masks_by_iou`, `apply_mouse_movement`, `locate_ready` | cv2, scipy(KDTree/距离变换), skimage.skeletonize, rdp, ultralytics, capture(gdi/bitblt/wgc) | ★★★★★ |
| `…/segment.py` | AFK 线程调度 + 弹窗_label 悬浮 UI | `execute_afk`, `afk_thread`, `run_segment` | segment_utils, pyautogui | ★★★ |
| `…/infer_pretrain_det.py` | 用 afk-det.pt 批量把截图转 YOLO 标签（半自动标注） | `inference(image)`, `inference_flow()`；类别 `["Window","Start","End"]` | ultralytics, cv2 | ★★★★（标注流水线） |
| `…/infer_pretrain_seg.py` | 用 afk-seg.pt 把路径 mask 导成 labelme polygon（rdp 平滑） | `export_segmentation()` | ultralytics, rdp, cv2 | ★★★ |
| `…/extensions/sponge/main.py` | **桥接消费侧范本**：收 health/health_speed/inventory，低血 ETA<1s 自动切海绵花瓣 | `main(health,health_speed,inventory,websocket)`, `switchPetal(i)`, `findPetal(inv,name)` | pyautogui, asyncio, websocket | ★★★★★（桥协议字段） |
| `…/extensions/superping/main.py` | 自动聊天扩展（消费 chat_ping） | `main(...)` | asyncio | ★★ |
| `…/extensions/magnet/main.py` | 自动拾取/背包相关扩展 | `main(...)` | asyncio | ★★ |
| `…/capture/wgc.py` | **WinRT Graphics Capture 无边框窗口截屏** | `wgc_capture(hwnd)` | `zbl.Capture`(WinRT), ctypes | ★★★★（比 mss 更稳的窗口捕获） |
| `…/capture/bitblt.py`, `gdi.py` | BitBlt / GDI 窗口截屏回退 | `bitblt_capture` / `gdi_capture` | cv2, win32 | ★★★ |
| `…/server.py` | AFK 机器人的本地 Web/扩展服务端（15KB） | FastAPI/websocket 服务 | fastapi | ★★★ |
| `florr_assistant/modules/combat/target_selector.py` | **目标选择**：YOLO+HSV 双通道检怪，按最近/优先级/危险度排序 | `TargetSelector._select_target()`, `MOB_TYPES` 表 | ultralytics, cv2, numpy | ★★★★★（MOB_TYPES 表直接入 mob_db） |
| `florr_assistant/modules/combat/fighter.py` | 战斗执行（走位/攻击/防御） | `Fighter` | platform | ★★★ |
| `florr_assistant/modules/pathing/map_classifier.py` | **多尺度+图像金字塔模板匹配识别当前地图** | `FullscreenTemplateMatcher.match/match_all`, `MapClassifier._classify()` | cv2, numpy | ★★★★★（pathing 直接复用） |
| `florr_assistant/modules/pathing/navigator.py` | 粉色 HSV 找玩家位置 + 网格 A* 寻路 + 卡死脱困 | `Navigator._lazy_theta_star()`, `_detect_player_position()` | cv2, heapq, numpy | ★★★★（玩家定位算法） |
| `florr_assistant/modules/afk/detector.py` / `responder.py` | afk-det.pt 的薄封装 + 应答逻辑 | `AFKDetector._detect()` | ultralytics | ★★ |
| `florr_assistant/core/platform.py` | 跨平台截屏/键鼠统一封装（Windows 用 win32gui） | `PlatformManager`, `WindowsPlatform` | mss, pyautogui, win32 | ★★★ |
| `florr_assistant/modules/data_collector/collector.py` (17KB) | 游戏状态数据采集器 | `Collector` | platform, cv2 | ★★★ |
| `florr_assistant/modules/stats/collector.py` | 战斗统计采集 | `StatsCollector` | — | ★★ |
| `florr_assistant/generate_synthetic_data*.py` (v1/v2/v3, 共 ~35KB) | 合成训练数据生成 | `generate_synthetic_data_v3` | numpy, cv2 | ★★★ |
| `florr_knowledge_base/scripts/knowledge_base.py` | fandom wiki API 爬取→结构化 | `WikiEntry`, 爬取类 | requests | ★★（你已有 wasm dump，优先级低） |
| `mob_wiki_monitor/__init__.py` | 监控 wiki 新怪并下载图标 | 主类 | requests | ★ |

**抗检测/绕过逻辑**：没有复杂反作弊绕过。仅见：`extension.swap.json` 的 `block_alpha`（隐藏扩展 DOM 避免被页面检测）、`move_after_AFK`（AFK 通过后小幅 WASD 动一下防“移动检查”）、`rdpEpsilon` 鼠标轨迹平滑、`mouseSpeed` 限速 + `sleep(0.1)#prevent throttling`。属“拟人化”层面，非注入/封包级绕过。

---

## txt 文件分析

628 个 txt **总内容仅 61 KB**，绝大多数是 YOLO 标签。按目录归类（脚本实测）：

| 归类 | 数量 | 位置 | 内容性质 |
|---|---|---|---|
| **YOLO 检测标签** | 304 | `florr-auto-framework-pytorch-macos/new_mob_dataset/val/labels/` | 怪检测验证集标注 |
| **YOLO 检测标签（副本）** | 304 | `upload_package/dataset/val/labels/` | 同上（拟发 Kaggle 的副本） |
| 中文/英文 UI 翻译 | 6+6 | `florr-auto-afk-main/gui/i18n/`（+macos 副本） | `key=中文` 形式的语言包 |
| 提示文案 tip | 2 | `…/gui/i18n/tip_zh-cn.txt / tip_en-us.txt` | 配置项说明长文案 |
| `requirements.txt` | 4 | 各子项目根 | pip 依赖清单 |
| PyInstaller 版本资源 | 2 | `florr-auto-afk-main/file_version_info_sv/_ex.txt` | exe 版本信息脚本 |
| 杂项单文件 | ~2 | overlay / kb 等 | 依赖或说明 |

**命名模式**：标签文件一律 `<mob_name>_<rarity>_<idx>.txt`，稀有度取值 `common/rare/epic/legendary/mythic/super`，例如 `ant_baby_common_1.txt`、`beetle_pharaoh_super_9.txt`、`centipede_hel_body_mythic_18.txt`。即文件名本身就是“怪名×稀有度”标注。

### 抽样 10 个真实内容（逐字引用）

1. `…/new_mob_dataset/val/labels/ant_baby_common_1.txt`（39 B）：
   `0 0.480469 0.480469 0.300781 0.300781`
2. `…/val/labels/ant_egg_common_1.txt`（39 B，YOLO 格式= `class cx cy w h` 归一化）：同构单行。
3. `…/val/labels/beetle_hel_common_5.txt`（40 B）：单行 `class cx cy w h`（坐标随框略大）。
4. `florr_assistant/requirements.txt`：
   ```
   # Florr Assistant Requirements
   # UI Framework
   PyQt5>=5.15.0
   # AI/ML
   ultralytics>=8.0.0
   torch>=2.0.0
   torchvision>=0.15.0
   opencv-python>=4.8.0
   ```
5. `overlay/overlay_requirements.txt`（13 B，全仓最小）：
   `PyQt5>=5.15.0`
6. `florr-auto-afk-main/gui/i18n/zh-cn.txt`（节选）：
   ```
   runs=运行
   exposure=曝光
   gui=程序界面（重启后生效）
   extensions=插件
   advanced=高级
   runs.autoTakeOverWhenIdle=检测到用户离开后自动接管操作
   runs.idleTimeThreshold=无响应时长阈值
   ```
7. `florr-auto-afk-main/gui/i18n/tip_zh-cn.txt`（节选）：
   ```
   runs.autoTakeOverWhenIdle=当用户闲置`runs.idleTimeThreshold`秒后，程序将接管 AFK
   runs.moveAfterAFK=AFK 绕过后进行小幅移动`wasd`以防止`移动检查`
   runs.rejoin=被踢出或服务器后自动重进（点击`Ready`）
   ```
8. `florr-auto-afk-main/file_version_info_sv.txt`（节选，PyInstaller 资源）：
   ```
   # UTF-8
   VSVersionInfo(
     ffi=FixedFileInfo(
       filevers=(1, 3, 2, 0),
       prodvers=(1, 3, 2, 0),
       mask=0x3f,
   ```
9. `florr_knowledge_base/requirements.txt`（18 B，全仓次小）：依赖一行（`requests` 类）。
10. `…/val/labels/termite_overmind_common_54.txt`（40 B）：单行 YOLO 框，`class` 恒为 `0`（该 val 集当前只验证单类定位，不区分怪种——怪种区分靠文件名，不靠 class id）。

> 结论：txt 里**没有日志、没有协议样本、没有中文标注**；608 个标签是“可用但需配合 png 图像才能训练”的标注，且 val 集图像未随仓（`new_mob_dataset` 下只有 `data.yaml` 和 `val/labels`，**`val/images` 图像缺失**）。

---

## 可偷数据清单

### ① 可直接整合进现有插件的算法/数据

- **`dataset_utils.py` 的 `check_health()`（★最实用）**：固定屏幕坐标像素读血。逻辑——以 `(x=116..278, y=97)` 为血条行，从右向左扫到第一个非黑（RGB>50）像素 `last`，`health%=(last-116)*(92/162)+4`；`(x=288,y=108)` 非空=满血 100%/32041；`(x=105,y=110)` 黑=死亡 0%。**直接替代你 combat.py 里的血条解析，给出像素级实现与 32041 的满血换算系数。**
- **`auto_stf/model.pth` + `FlorrModel` 结构（★）**：73→128→ReLU→64→ReLU→5；前 2 维 `tanh`（move_x/y），后 3 维 `sigmoid`（attack/defend/yinyang）。配 `auto_stf/config.json`（input_dim=73, output_dim=5）即可 `load_model` 加载，输出归一化动作。
- **`target_selector.py` 的 `MOB_TYPES` 表**：11 只怪的 `priority/danger` 评分（ladybug 0.1 → sandstorm 0.9 / queen_ant 0.8），目标选择“最近/优先级/低危险”三策略——直接并入 `mob_db.py`。
- **`map_classifier.py` 多尺度模板匹配**：粗尺度 `[0.5…2.0]` 定位 + 细尺度 0.05 步进精修，右上角 35%×40% 区域内匹配——直接给你的 pathing 做“当前地图识别”，配仓里 9 张模板（anthell/desert/factory/garden/hel/jungle/ocean/sewers/worm's inside）。
- **`navigator.py` 玩家定位**：HSV `[150,50,50]~[180,255,255]` 粉色块 + 形态学开运算 + 矩求质心 = 玩家圆心；卡死检测（位移<5px 持续 3s 则空格+随机方向脱困）。
- **桥接协议字段（★）**：网页→Python 推 `health, health_speed, inventory{main[],secondary[]}, chat消息, 花瓣{x,y,size,canvasWidth/Height}`；Python→网页回 `{command:"showNotification",title,info,icon(base64),duration}`、换花瓣按槽位 `1..9,0`。`inference.py` 的 `/textlist` 用 `atan2(y-cy,x-cx)/π` 由花瓣坐标算朝向角 `degree`。
- **`capture/wgc.py`**：`zbl.Capture`(WinRT Graphics Capture) 按 hwnd 无边框抓帧，比 mss 全屏更适合做窗口化战斗截图。

### ② 协议/ID映射/中文名等结构化表

- **`new_mob_dataset/data.yaml`：81 类怪的权威 ID→英文名映射**（nc=81，`0:ant_baby … 80:worm_guts`）。这是 `stf_det.pt` 的类别定义，**直接当 mob_db 的 canonical 英文键表**。
- **`dataset_utils.py` 的 `MOB_TYPE_ONE_HOTS`**：90 项 one-hot 怪名清单（比 data.yaml 多 assembler/cactus/oracle/titan/trader 等），可与 data.yaml 合并去重得到更全的怪名表。
- **`knowledge_base/data/wiki.json`**：241 篇 wiki 全文（wikitext），含稀有度/掉落/区域描述；`index.json` 已按 mobs/petals/areas/mechanics 分类好标题。
- **`mobs_images/` 87 张英文怪名 png**（`acid_bubble.png, ant_queen.png …`），可做模板匹配素材。
- **i18n `zh-cn.txt`**：配置项中文名（非怪名翻译，注意）。

### ③ 与已偷资产的差异与增量

你已有 `wasm_dump/client.wasm + all_strings.txt + wasm_struct.json` 和 `data/all_mobs.json/all_petals.json/mob_stats_full.json/florr_dropchance.json`。本仓库的**增量**：

1. **像素级读血算法 + 32041 满血系数**——wasm dump 给的是结构，这里给的是“在屏幕哪个像素读”的实战实现，互补。
2. **已训练的动作 MLP（model.pth）+ 6583 条行为克隆样本**——你现有插件是规则/OpenCV，这里是可直接加载的学习模型，量级最大增量。
3. **AFK 弹窗/路径的 YOLO 权重（afk-det/afk-seg.pt）+ Dijkstra 骨架求解管线**——你的 afk_solver.py 可直接换成这套带权重的成熟方案。
4. **桥接协议字段定义**——你已有 bridge，这里给出网页端实际推送的 `health_speed/inventory/花瓣坐标` 字段清单，可补全你 bridge 的消息 schema。
5. **9 张地图模板 + 多尺度匹配**——wasm 里没有的“运行时识别当前地图”能力。
6. **不重复**：这里没有 wasm 里的内部内存偏移/协议包结构，也没有你已有的掉落概率表；`wiki.json` 与你 `all_mobs.json` 内容重叠度高（都是 wiki 来源），增量有限。

---

## 风险 / 注意

1. **许可证 GPL v3**（README 徽章 + LICENSE）：直接复制代码进你自己的插件会触发 GPL 传染性（衍生作品需开源）。`upload_package/dataset-metadata.json` 里数据集声明 **CC0-1.0**（数据可自由用），但**代码仍受 GPL**。商用/闭源请只取算法思想与数据，勿整段抄代码。
2. **硬编码凭证泄露**：
   - `florr-auto-afk-main/constants.py` 内嵌一段 base64（连续解码 3 次）的 **GitHub Personal Access Token**。作者注释自称“只对 dataset 仓库有 rw 权限，泄露无所谓”——但它仍是真密钥，**不要在你的代码/发布物里再次带上，也别拿去请求任何 GitHub API**（请求即可能触审/被吊销，且属他人密钥）。
   - 根目录 `kaggle.json` 含**真 Kaggle API key**，同理勿用、勿传播。
3. **`extension.js`（553KB）被 javascript-obfuscator 重度混淆**：不要盲目 `eval`/运行。它注入 florr.io 页面并向本机 8000 端口 POST，行为需审计后再用；建议只参考其协议字段，不直接跑混淆产物。
4. **机器人/ToS 风险**：自动战斗、自动聊天（`conversation.json` 是“猫娘伪装玩家”人设）、自动 AFK 绕过均违反 florr.io 用户协议，有封号风险；`block_alpha`/`move_after_AFK` 等即作者用来规避页面检测的手段。
5. **不可用/缺失部分**：
   - 怪检测权重 `stf_det.pt` **不在仓里**（`dataset_utils.py` 引用了但文件缺失），战斗 YOLO 不能开箱跑。
   - `new_mob_dataset/val/images` 图像缺失，608 个 txt 标签**无图可训**；`data.yaml` 里 `path` 指向作者 Mac 路径 `/Users/panjiyang/…`，需改。
   - 大量路径是 macOS 绝对路径；`florr-auto-framework-pytorch-macos` 目录名虽带 macos，但代码是跨平台的。
6. **无后门实据**：通读主入口未见向第三方服务器回传你的数据（除作者自己的 GitHub 数据集上传 `gh_upload_dataset` 和 Kaggle 发布）；但因 `extension.js` 混淆 + 内嵌 token，建议把该目录当“半可信”处理。

---

## 附：统计命令（数字来源）

```powershell
# 文件总数/扩展名分布
$all = Get-ChildItem $root -Recurse -File
# JSON：python analyze_json.py （json.load 后打印顶层结构/条目数/样例）
# JSONL：python analyze_jsonl.py （逐行 json.loads 计数、并集字段）
# TXT 归类：python analyze_txt.py （按父目录分组、文件名数字归一化后分组、总字节）
# 实测：总文件 1099 / 194.8MB；txt 628(共61KB)；json 21；jsonl 4
#   dataset_new_.jsonl = 6583 行；index.json mobs:75/petals:74/areas:33
#   wiki.json = list[241]；known_mobs.json = dict[6]
# YOLO 类别：Read new_mob_dataset/data.yaml → nc=81 (0..80)
```

---

## 最值得偷的内容（按优先级）

1. **`dataset_utils.py::check_health()` 像素读血法**（坐标 116..278/y=97、满血 32041 系数）——直接升级 combat.py 的血条解析。★
2. **`auto_stf/model.pth` + `FlorrModel`(73→128→64→5) + 6583 条 jsonl**——一个能直接 `load_model` 的行为克隆战斗网络，规则插件 → 学习型的最大增量。
3. **`data.yaml` 81 类怪 ID→英文名表 + `MOB_TYPE_ONE_HOTS` 90 项**——合并去重后当 mob_db.py 的 canonical 键表。
4. **桥接协议字段**（网页推 `health/health_speed/inventory/花瓣坐标`；Python 回 `showNotification`+按槽位 `1..9,0` 换花瓣；`atan2` 算朝向角）——补全你 bridge 的消息 schema，sponge 扩展“低血 ETA<1s 切海绵”是现成策略范本。
5. **afk-det.pt/afk-seg.pt + segment_utils 的骨架 Dijkstra 求解管线**——你的 afk_solver.py 可整体替换成这套带权重的成熟 AFK 绕过方案。
6. **`map_classifier.py` 多尺度+金字塔模板匹配 + 9 张地图模板 png**——运行时识别当前地图，pathing 直接复用。
7. **`MOB_TYPES` 目标优先级/危险度表 + navigator 的粉色 HSV 玩家定位与卡死脱困**——目标选择与走位的即插即用规则。
8. **`capture/wgc.py` WinRT Graphics Capture 按 hwnd 无边框抓帧**——比 mss 全屏更稳的战斗截图后端。
