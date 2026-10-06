# reference-florr-tools 第 06 批：机器人 / 地图 / 框架类小仓库深挖报告

> 范围：仅只读本地磁盘，全程未联网。根目录 `C:\Users\intel\Downloads\florr-auto-pathing-main\reference-florr-tools\`。
> 对照基线（已偷资产）：`wasm_dump\client.wasm`(9190KB)、`all_strings.txt`、`wasm_struct.json`、`wasm_map_data.json`；`data\all_mobs.json`、`all_petals.json`、`mob_stats_full.json`、`florr_dropchance.json`、`maps_list.json`、`mob_spawn_data.json`；现有插件 `combat.py`(屏幕检测)、`mob_db.py`(数据层)、`memory_reader.py`(内存读取)、`bridge`(桥)、`afk_solver.py`、`map_select.py`/`area_select.py`、`maps\`。

---

# 1. Florr_Bot（目录名 `Florr_Bot`，作者 Yanquan-Su，Chrome MV3 扩展）

## 能力摘要
一个 Manifest V3 浏览器扩展（content.js 24KB 为核心，background.js 仅 service worker 转发日志，popup.* 是设置面板）。**检测方式是纯屏幕像素颜色匹配**：`findGameCanvas()` 取 `document.querySelector('canvas')`，`getCanvasImageData()` 调 `ctx.getImageData(0,0,w,h)` 全帧读回，`detectColorMatches()` 以步长 4 像素扫描，按 RGB 绝对差阈值命中。**决策逻辑**在 `gameLoop()`：找离玩家最近的怪就 `attackMonster()`，在 `lootRadius=100` 内找最近掉落 `collectLoot()`，`healthThreshold=30` 以下停手；`trackMonsters()` 用 50px 内消失判定"被击杀"来累计 `killCount`。**控制方式**是 `dispatchMouseEvent()` 合成原生 `MouseEvent`（mousemove/mousedown/mouseup）直接派发到 canvas，`simulateHumanMovement()` 用三次方缓动 `1-(1-p)^3` + 随机 ±5px 抖动 + 随机延时 20~50ms 模拟人手移动。防 AFK 靠扫 DOM 文本关键词 + 灰色像素块，`performDragPuzzle()` 做 10 段随机拖拽。整体是"截图→颜色分块→贪心最近目标→合成鼠标"的最弱一档视觉 bot。

## 可偷清单
- ① 可直接整合进现有插件：
  - **颜色阈值表**（`findMonsters`/`findLoot`/`findPlayer`/`detectHealthBar` 里写死的 RGB 值与 threshold）——可直接作为 `combat.py` 屏幕检测的初始阈值表或对照基准：怪物色 `(139,69,19)/(255,0,0)/(128,0,128)/(0,128,0)` thr=40；掉落金色系 `(255,215,0)/(255,255,0)/(192,192,192)/(218,165,32)` thr=35；玩家 `(255,105,180)` thr=30；血条 `(255,0,0)` thr=20。
  - **`clusterPoints(points,minDistance)`** 贪心质心聚类（半径 `minDistance*5`）——可直接搬给 `combat.py` 把零散命中像素聚成目标框。
  - **`trackMonsters`/`trackLoot` 前后帧 50px/30px 匹配 + 消失计数**——可作为击杀计数、目标跨帧追踪的现成模板。
  - **`simulateHumanMovement`（easeOutCubic + 抖动 + 随机延时）**——可接进 `bridge` 桥的鼠标控制，让现有移动更像人。
- ② 协议/ID/中文名映射：无结构化 ID 表，仅上述硬编码颜色，无中文名。
- ③ 与已偷资产差异/增量：现有 `combat.py` 已是屏幕检测主力，本仓库的增量是**具体可用的阈值数值**和**人机缓动轨迹**；不读内存、不碰 wasm，与 `memory_reader.py` 无重叠。AFK 关键词表（`验证/人机验证/点击圆圈/拖动/滑动/完成验证`）和 `performDragPuzzle` 可补 `afk_solver.py`。

## 风险/注意
- 作者自己 README 写"目前写的不太好，欢迎大佬指正"，像素法对 florr 这种同屏多色、花瓣遮挡的场景鲁棒性很差，颜色阈值是按老版本 UI 估的，直接用误检会很高。
- `detectAFKChallenge()` 里 `afkIndicators` 数组有两个 `"验证"` 重复项，且 `querySelectorAll('*')` 全树遍历性能差；`detectHealthBar` 用红色像素数 `/10` 反推血量，纯属估算。
- 纯 DOM/canvas 注入，无封号级内存操作，但合成 MouseEvent 在有反作弊的页面可能被识别为 `isTrusted=false`。

---

# 2. florr-mob-bot（目录名 `florr-mob-bot`，作者 codertrout12，"super ping"）

## 能力摘要
**先纠正一个预期**：这里的 "super ping" **不是内存/网络偏移快速定位技术**，而是一个**第三方聚合站 + HTTP 响应嗅探 + Discord 告警**的常驻 bot。核心 `florr_bot.py`（4.4KB）用 Playwright 1.40 起一个 headless Chromium（`--no-sandbox --disable-gpu`），`page.goto("https://mobs.ashish.top/")` 挂住不离开，通过 `page.on("response", on_response)` 监听该页所有 HTTP 响应；判定规则是：响应 URL 同时包含 `petal-` 和 `-super.png`，且文件名不含 `craft`/`item`（滤掉合成物），就视为一只 super mob 刚被渲染加载——即"super mob 刷新"信号。命中后 `aiohttp` 下载该 png，拼成红色 Discord Embed（标题 `SUPER MOB`，`clean_mob_name()` 把 `petal-xxx-super.png` 去前缀后缀转 title 名），发到两个频道。本质是**别人搭好了 super mob 实时聚合站 mobs.ashish.top，这个仓库只是嗅它的贴图资源请求来做推送**。部署形态是 Heroku/Dyno：`Procfile` = `worker: python florr_bot.py`，`runtime.txt` = python-3.11.9，`requirements` = discord.py 2.3.2 / playwright 1.40.0 / aiohttp 3.9.1。

## 可偷清单
- ① 可直接整合：
  - **super mob 刷新信号判定规则**：`"petal-" in url and "-super.png" in url`，并 `not ("craft" in name.lower() or "item" in name.lower())`——这套"靠贴图资源命名约定抓事件"的思路可移植到现有插件做 super/稀有怪提醒。
  - **`clean_mob_name()` 命名还原规则**：`petal-{X}-super.png → X.replace('_',' ').title()`——可作为 mob 资源名→展示名的小映射。
- ② 协议/ID 映射：仓库内含 Discord 配置常量 `GUILD_ID=1473465801536307200`、`CHANNEL_IDS=[1473477387642732655, 1473465801536307203]`（他人私有服务器，仅作格式参考，不可复用）；`DISCORD_TOKEN` 走环境变量。数据源约定 `https://mobs.ashish.top/` 及其资源命名规则。
- ③ 与已偷资产差异/增量：`data\all_mobs.json` 等是静态图鉴，本仓库给的是**"super 变体贴图文件名 → 刷新事件"的运行时信号通道**，是增量；但它依赖外部网站 mobs.ashish.top，并非游戏协议本身。

## 风险/注意
- **强联网依赖**：整套价值押在 mobs.ashish.top 这个第三方站活着、且其资源命名约定不变；站一关或改名即失效。本报告其余结论均为本地读码，此条机制描述亦来自本地代码。
- 内嵌了他人 Discord 服务器/频道 ID，照搬无意义且可能打扰他人。
- 无任何游戏内走位/打怪能力，只做"发现→推送"，不能当战斗 bot 用。

---

# 3. maze-tool（目录名 `maze-tool`，作者 Stoplookin9）—— 本批最高风险：空壳仓库

## 能力摘要
**本地磁盘上没有任何可分析的地图工具代码或数据。** 该目录是一个 shallow clone，我用只读 git 命令穷举确认：`git log --oneline --all` 只有一条提交 `8ec2aa3 "Initial commit"`；`git ls-tree -r HEAD` 全树仅两个 blob——`LICENSE`(35823 字节) 和 `README.md`(37 字节)；`.git/pack` 打包文件仅 13KB，`packed-refs`/`shallow` 均指向同一个 shallow 提交。`README.md` 全文就是两行：标题 `# maze-tool` + `Florr.io maze map tool`。**没有 .html/.js/.py/.json，没有网格表、没有坐标条目、没有捷径条目、没有生成或解析算法。** 即作者只推了许可证和一句话描述，真正的迷宫工具本体从未提交到这个克隆可达的历史里。

## 可偷清单
- ① 可直接整合：**无**。本地不存在任何地图数据结构、捷径坐标或迷宫算法，无法给 `map_select.py`/`area_select.py`/`maps\` 提供增量。
- ② 协议/ID 映射/地图捷径表：**无**。无网格尺寸、无坐标条目、无捷径样例可引用（按完成标准要求的"真实样例"在此仓库客观上不存在，不做编造）。
- ③ 与已偷资产差异/增量：与 `wasm_map_data.json`/`maps_list.json` 无可比内容——它本地为空，谈不上差异。

## 风险/注意
- **任务预期落空**：原以为这是本批最高价值项，实际仓库被克隆到的是空壳。要拿到迷宫捷径数据，需要（按用户"禁止联网"约束）另行从其他可达副本或上游补全本仓库，当前本地无米下锅。
- 不要把"Florr.io maze map tool"这句 README 标题当成它具备什么功能；它什么都没实现。

---

# 4. florr-auto-framework-pytorch（目录名同名，作者 lemonqu，清单外新发现，PyTorch 行为克隆框架）

## 能力摘要
这是一个**完整但作者弃坑**的 florr AI 演示框架（README："This is a DEMO repo to show how to train a custom florr-ai model … for Starfish Zone"；作者注释"fuck the game gives me no supers so im gonna opensource all my codes and quit"）。它由两套模型 + 一条前端桥组成。

**(a) 目标检测模型 `models/stf_det.pt`（5.6MB）**：基于 ultralytics **YOLO**，在 `dataset_utils.py` 顶部全局 `model = YOLO("./models/stf_det.pt")` 加载。`create_dataset.py` 与 `inference.py` 的 `yolo_thread()` 每帧 `pyautogui.screenshot(1920x1080)`→BGR→`model.predict(frame,verbose=False)`，置信度阈值 **0.5**，输出 `boxes.data=[x1,y1,x2,y2,conf,cls_id]`，检测**三类怪**：`one_hot_encode_mob()` 的 `MOB_TYPE_ONE_HOTS = ["Starfish","Jellyfish","Bubble"]`，即海星/水母/泡泡（旧版海星区怪）。

**(b) 行为克隆策略网络 `models/auto_stf/model.pth`（74KB）**：纯 MLP，`FlorrModel(input_dim=73, output_dim)`：`Linear(73→128)→ReLU→Linear(128→64)→ReLU→Linear(64→out)`，`forward` 里前 2 维过 `Tanh`（move_x/move_y），后几维过 `Sigmoid`（attack/defend/yinyang 等离散动作）。**训练配置（来自 `trains/config.json` 真实数值）**：`model_name=auto_stf`、`input_dim=73`、`output_dim=6`、`batch_size=128`、`epochs=250`、`dataset_path=./data`；优化器 Adam（`train.py` 默认 `lr=1e-3`），`ReduceLROnPlateau(mode='min', factor=0.5, patience=3)`，80/20 train/val 随机切分；自定义 `custom_loss` = `0.5*MSE(move) + 1.0*(BCE attack + BCE defend + BCE yinyang)`。注意：`train.py`/`FlorrModel` 代码里写的是 5 维输出，而最终 config 落盘是 **output_dim=6**，说明最后一版多了一维动作、代码与权重未完全同步（弃坑 demo 常态）。**数据集**：`trains/data/dataset_new_.jsonl`，实测 **6583 条样本**，按 `save_thread` 每 0.1s（10Hz）采集。

**输入向量怎么拼**：`state2dataset()` 把 `health/100`、`degree`、`yinyang` 三个标量 + 最多 `MAX_MOBS_NUM=10` 只怪、每只 7 维 `[x_norm,y_norm,w_norm,h_norm, one_hot(3)]`（按到屏幕中心距离排序、不足补零），合计 `3 + 10*7 = 73` 维。坐标全部相对 1920×1080 屏幕中心归一化。真实样例（首行）：`health=0.7499, degree=0.184, yinyang=1.0`，mobs 含 `[0.0708,0.0833,0.0875,0.15,1,0,0]`（=Starfish）与 `[…,0,1,0]`(Jellyfish)/`[…,0,0,1]`(Bubble)；对应 action `{move_x:-0.176, move_y:-0.211, attack:0.0, defend:1.0, pred_yinyang:1.0}`。

**(c) 前端桥（最值得偷的思路）**：`rotate.js` 是油猴脚本（`@match https://florr.io/`），**hook 掉 `CanvasRenderingContext2D.prototype.fillText`**——当游戏绘制文字 `"Mythic"` 且字号 `fontSize==12` 时，读 `this.getTransform()` 的 `e,f`（世界坐标）连同 canvas 宽高，每帧 `fetch('http://127.0.0.1:8000/textlist')` POST 出去。Python 端 `re_server.py` / `rotation_server_thread()`（FastAPI，0.0.0.0:8000，CORS 放行 florr.io）收 `textList`，取 `size==12` 项，用 `atan2(花瓣点-画布中心)/π` 算出玩家朝向 `degree∈[-1,1]`。

**血条与装备检测**：`check_health()` 硬编码 1920×1080 坐标——截屏后扫 y=97、x∈[116,278] 的血条，满血判定点 (288,108)、死亡判定点 (105,110) 是否近黑(r,g,b≤50)，公式 `health_num = (last-116)*(92/162)+4`，`florr血量 = health_num*34954*0.01`（满值 32041）。`get_if_equip()` 用 `cv2.matchTemplate(TM_CCOEFF_NORMED, threshold=0.8)` 拿 `templates/yinyang.png` 模板匹配，命中 y∈(920,930) 判阴阳板已装备。**部署控制**（`inference.py`）：P 键切 `auto_suggest`；attack→`pyautogui.mouseDown/Up(left)`、defend→right、pred_yinyang 变化→`pyautogui.write("2")` 切阴阳板、全程 `keyDown("g")`，`moveTo(mouse_pos_x,mouse_pos_y,duration=0.1)`。

## 可偷清单
- ① 可直接整合进现有插件：
  - **`check_health()` 像素血条读数算法 + 全部硬编码坐标**（1920×1080，血条 x∈[116,278]/y=97，满血点(288,108)，死亡点(105,110)，满血量 32041，换算系数 34954）——可直接搬进 `combat.py` 做生命值读取，比 Florr_Bot 的"红像素数/10"靠谱得多。
  - **`stf_det.pt` YOLO 检测权重 + 加载/后处理代码**（`model.predict`、conf≥0.5、boxes.data 取框、cls→名字映射）——可直接替换/增强 `combat.py` 的颜色法，做真正的目标检测；输入 1920×1080 BGR 截图。
  - **`rotate.js` 的 Canvas.fillText hook + FastAPI degree 回传链路**——这是"从游戏渲染层直接偷坐标/朝向"的范式，与 `memory_reader.py` 的内存读取互补（纯前端、不碰进程内存），可移植用来在桥里精确拿玩家朝向/花瓣位置。
  - **`cv2.matchTemplate` 装备检测**（`templates/yinyang.png`、TM_CCOEFF_NORMED、thresh=0.8、y∈920~930 判装备）——可搬进 `combat.py`/`bridge` 做花瓣装备状态识别。
  - **整套状态归一化 + 73 维特征拼法 + 5 维动作接口**（`state2dataset`/`FlorrDataset`/`get_action`）——若要自己训一个策略网络，这份数据schema和动作空间定义可直接复用。
  - **`models/auto_stf/model.pth` 现成权重**：可加载（`load_model("./models/auto_stf")`）直接当策略 baseline，输入73维、输出离散动作阈值 0.5。
- ② 协议/ID 映射/结构化表：
  - 三类怪 one-hot 顺序表 `["Starfish","Jellyfish","Bubble"]`（YOLO cls_id→名字）。
  - 动作语义表：输出位 = move_x, move_y(tanh 归一化方向) + attack(左键) / defend(右键) / pred_yinyang(按"2"切阴阳板)；快捷键映射：左键=攻击、右键=防御、`g` 长按、`2`=阴阳板切换、`p`=自动开关。
  - 数据标注格式：JSONL，每行 `{"state":{health,degree,mobs[10][7],yinyang}, "action":{move_x,move_y,attack,defend,pred_yinyang}}`。
- ③ 与已偷资产差异/增量：
  - 已偷 `wasm_map_data.json`/`all_mobs.json` 是**静态世界/图鉴数据**；本仓库给的是**可运行的"截屏→YOLO→MLP→鼠标"闭环**和一份 6583 条**人工演示操作数据集**，这是全新增量。
  - 与现有 `combat.py`(颜色法屏幕检测) 的差异：它用 YOLO 权重做检测，精度更高；`memory_reader.py` 走内存，它走渲染 hook+截图，是另一条互补通路。
  - 局限：YOLO 只认 Starfish/Jellyfish/Bubble 三类（旧海星区），换地图/新怪即失效；血条坐标写死 1920×1080；策略网络只有 74KB、数据 6583 条（≈11 分钟人工录像），演示性质，强度有限。

## 风险/注意
- 作者明确弃坑、README 自称"highly hard to run"，依赖一堆重型库（ultralytics/torch/pyautogui/pynput/cv2/fastapi/discord），且 YOLO 权重 `stf_det.pt` 仅认三类旧怪，迁移到现版本 florr 几乎必须重训检测。
- config 写 `output_dim=6` 而代码写 5 维，存在版本漂移，加载 `model.pth` 时若维度对不上会报 shape mismatch——需先按 `models/auto_stf/config.json` 的 6 维建网络。
- 前端 hook `fillText` 依赖游戏仍用 Canvas2D 绘制 `"Mythic"`/12号字；游戏渲染一改（WebGL/改文案）degree 桥立即断。
- 全程 `pyautogui` 真截屏真控鼠标，运行时会霸占键鼠，调试需用 P 键随时关 auto_suggest。

---

## 本批小结
1. **真正有货的只有 2 个半**：`florr-auto-framework-pytorch` 是本批最有价值资产——给了现成 YOLO 检测权重 `stf_det.pt`、一个可加载的行为克隆 MLP、真实训练配置（73→128→64、batch128、epoch250、lr1e-3）、6583 条 JSONL 数据集，以及一条"hook Canvas.fillText → 本地 FastAPI 偷玩家朝向"的前端桥，可直接补 `combat.py`（血条坐标/YOLO/模板匹配）和 `bridge`（渲染层偷坐标）。`Florr_Bot` 给的是可搬运的颜色阈值表、质心聚类、人机缓动轨迹和 AFK 拖拽解法（补 `afk_solver.py`），但属最弱视觉档。
2. **"super ping" 名不副实**：`florr-mob-bot` 不是内存/网络偏移技术，而是 Playwright 嗅探第三方站 mobs.ashish.top 的 `-super.png` 贴图请求发 Discord 告警；可偷的是"贴图命名约定=事件信号"这条思路，强联网依赖、无战斗能力。
3. **最高预期项落空**：`maze-tool` 经 git 穷举确认是空壳仓库（仅 LICENSE + 37 字 README，单次 Initial commit），本地**没有任何迷宫网格、坐标表或捷径数据**，无法给 `map_select.py`/`maps\` 提供增量；要这块数据必须另找上游副本，当前约束下拿不到。
4. **与已偷资产关系**：本批全部是"运行时视觉/渲染层"路线（截屏检测、YOLO、DOM hook、鼠标合成），与已偷的 wasm 静态数据（`wasm_map_data.json`/`all_mobs.json`）和内存读取 `memory_reader.py` 形成互补而非重叠；maze 捷径数据这一项本批零收获，是唯一缺口。
