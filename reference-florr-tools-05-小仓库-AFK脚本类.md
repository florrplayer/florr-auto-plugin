# reference-florr-tools 子报告 05 —— AFK / 脚本类小仓库

> 扫描范围：`C:\Users\intel\Downloads\florr-auto-pathing-main\reference-florr-tools\` 下 6 个指定仓库。
> 方法：只读本地磁盘，逐个打开全部非 `.git` 源文件（.user.js / .js / .py / .bat / .txt / README / requirements），未联网。
> 对照基线：现有 `afk_solver.py`（v1.18.0，位于 `C:\Users\intel\Downloads\florr-auto-pathing-main\afk_solver.py`）。
>
> **关键事实先行**：现有 `afk_solver.py` 破解的是「**拖动连线**」型 AFK 验证（稀有色起点圆点 → 灰色路径 → 孔洞终点，颜色归一化 + Dijkstra 最宽瓶颈路径 + RDP 简化 + win32 PostMessage 后台拖动）。本批 6 个老仓库破解的全部是**另一类/更老的防挂机手法**：定时按键保活、OCR 点单词「here」、点 DOM 按钮、模板匹配复活。**没有任何一个仓库实现拖动连线求解**——这正是本批的增量边界。

---

# 1. Florr.io-Auto-AFK（目录名：Florr.io-Auto-AFK，作者 liucang / 仓库属 IceCang）

## 能力摘要（约 200 字）
纯 Tampermonkey 用户脚本（`@grant none`，仅 1 个 `florr.io-auto-afk.user.js`），思路是**「定时切槽保活」**而非破解验证弹窗。按 F 启动后，`setInterval(..., 60000)` 每 60 毫秒级别周期（实际 `60000`ms=60 秒）向 `window` 派发两次合成 `keydown`/`keyup`，键码取自 `slotCode[switchSlot]`；两次按键之间、keydown 与 keyup 之间都插入 `Math.random()*100` 的随机延迟。可选按住鼠标：在 `canvas` 上 `dispatchEvent(new MouseEvent("mousedown",{button:mouseStat,clientX:309,clientY:326}))`，停止时补发 `mouseup`。内置仿游戏风格 UI（P 开面板、方向键选鼠标键位 0/1/2=左/无/右、选槽位 1~10、F 启停）。本质是周期性切换花瓣槽位 + 按住攻击，向服务器伪造「玩家在操作」的活动信号以避踢。

## 可偷清单
- ① 可整合算法/数据：
  - **槽位键码映射表** `slotCode = [0, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 48]`——索引即槽位号（1='1'=49 … 10='0'=48），这是 florr 花瓣槽位快捷键的实测键码，可直接喂给 bridge 的键盘注入层。
  - **随机化按键手法**：`Math.random()*100` 抖动 + 「双击同一槽位」连发（keydown→随机 delay→keyup→再随机 delay→再 keydown→keyup），是一种廉价的拟人化按键节奏，可叠加到现有 bridge 的保活线程里。
  - 与 `afk_solver.py` 异同：**完全不同层**。afk_solver 是「验证弹窗出现后求解拖动」；本仓库是「让验证弹窗根本不触发 / 不被踢」的前置保活层。二者是互补关系，不是替代——可作为 afk_solver 未触发时的常驻保活补充。
- ② 协议/ID 映射：无协议表；唯一结构化数据即上面的 `slotCode` 键码数组。
- ③ 与已偷资产差异/增量：已偷 wasm 数据层（all_mobs/petals）不含「保活节奏」类逻辑；本仓库的 60s 周期 + 随机抖动节奏是全新增量，且证明老版本 florr 靠「切槽位」就能过 AFK 检测，提示服务器早期判定偏宽松。

## 风险/注意
- 纯 DOM 合成事件（`@grant none`），浏览器侧易被 `Event.isTrusted` 检测识别为伪造；README 自述只是「避过 AFK Check」，无抗封号设计。
- 鼠标坐标 `clientX:309, clientY:326` 写死，仅适配固定分辨率/缩放。

---

# 2. Florr.io-Auto-Respawn（目录名：Florr.io-Auto-Respawn，作者 Crysiox / theflorr）

## 能力摘要（约 190 字）
PyQt6 无边框 GUI + OpenCV 模板匹配的**自动复活**工具（`src/app.py` 单文件）。后台线程 `clicker()` 每 `time.sleep(0.5)` 截一次全屏：`p.screenshot().convert('L')` 转灰度后 `c.matchTemplate(ss, redx, c.TM_CCOEFF_NORMED)`，取 `minMaxLoc(...)[1]` 匹配置信度，`>=0.8` 即视为命中死亡画面的「红叉」(redx.png)，于是 `p.click` 预设的 redx 坐标（默认 `{"X":473,"Y":186}`）；同理用 `ready.png` 模板命中后点 ready 按钮（默认 `{"X":1058,"Y":613}`）。模板图在运行时从 catbox.moe 下载到 `assets/`，坐标存 `settings.json` 可在 GUI 里改。死亡检测 = 红叉图标模板匹配；复活 = 点 ready 按钮。

## 可偷清单
- ① 可整合算法/数据：
  - **死亡画面模板匹配范式**：灰度 + `TM_CCOEFF_NORMED` + 阈值 0.8 + 0.5s 轮询，与现有 `combat.py` 的屏幕检测同思路，可直接复用其「截图→matchTemplate→阈值判定→动作」骨架。
  - 与 `afk_solver.py` 异同：afk_solver 关注验证弹窗；本仓库关注**死亡/复活状态机**，是 afk_solver 完全没有的「死后自动回到战场」闭环环节，可补上现有插件死后断线无人接管的缺口。
- ② 协议/ID 映射：无；但给出两个**关键 UI 锚点坐标**（redx 关闭叉 ≈(473,186)、ready 按钮 ≈(1058,613)），是 1920×1080 Chrome 下的实测落点，可作坐标标定参考。
- ③ 与已偷资产差异/增量：已偷 wasm/mob 数据表是静态游戏数值；本仓库是**视觉状态机**（死亡↔复活切换），类型全新。

## 风险/注意
- README 注明「made for 1080x1920」与实际默认坐标（1920×1080）口径混乱，分辨率/缩放一变即点空；`FAILSAFE` 未显式设置，pyautogui 失控时无急停。
- 模板图依赖外网 catbox.moe 下载，离线环境需自备 redx.png/ready.png。

---

# 3. Florr-Auto-AFK-Script（目录名：Florr-Auto-AFK-Script，作者 Beeeee / BeeLeap）

## 能力摘要（约 180 字）
移动端友好的用户脚本 v1.3.0（`script.js` 单文件）。启动后起两个定时器：`AFKinterval` 每 60000ms 派发一次 `keydown`/`keyup`（`{key:"1"}`，带 `Math.random()*100` 抖动）切回 1 号槽保活；另起 `afkCheckInterval` 每 `checkInterval=5000`ms 执行 `clickAFKCheckButton()`——`document.querySelector('button[data-qa-id="afkCheck"]') || document.querySelector('.afk-check-button')`，命中则直接 `.click()`。带一个可滚动日志面板和屏幕右下浮钮，支持手机端 Tampermonkey。README 自陈「目前有 bug，无法使用」「有封号风险」。

## 可偷清单
- ① 可整合算法/数据：
  - **⭐ 最有价值的一条：DOM 语义钩子 `button[data-qa-id="afkCheck"]` 与类选择器 `.afk-check-button`**。这是 6 个仓库里唯一直接指向 AFK 验证按钮 DOM 节点的线索。若 florr 当前版本仍把 AFK 按钮挂在 DOM 上，一次 `element.click()` 即可秒过验证，**远优于** afk_solver 的截图→求解→拖动整条视觉流水线。建议先用浏览器 DevTools 验证该选择器是否仍有效（仅本地探针，不联网猜）。
  - 与 `afk_solver.py` 异同：若 DOM 钩子仍活，afk_solver 的整套 OpenCV 拖动算法可被「直接 click 按钮」短路；若已失效（README 说 bug 不可用，很可能选择器已过时），则退回 afk_solver 视觉方案。二者是「优先 DOM、兜底视觉」的分层关系。
- ② 协议/ID 映射：`data-qa-id="afkCheck"` 这个 QA 测试 ID 本身就是结构化锚点，值得记入资产表。
- ③ 与已偷资产差异/增量：已偷资产全是内存/wasm 数据，无任何「DOM 钩子」层；本仓库补上了「浏览器内 DOM 直接操作」这一全新攻击面。

## 风险/注意
- 作者本人标注「有 bug、无法使用、有封号风险」，`data-qa-id` 极可能已随版本更新失效，不可照搬即信，必须本地实测。
- 用 `key:"1"`（字符串）而非 keyCode，与现代浏览器一致；但直接 click 按钮的行为在反作弊眼里非常显眼。

---

# 4. florr-AFK-indicator（目录名：florr-AFK-indicator，作者 3814279105）

## 能力摘要（约 230 字）
这是一个**只检测、不求解、只弹系统通知**的 AFK 指示器（`florr-AFK-indicator.user.js` + 教学版 `dev.js`）。`mainLoop()` 把游戏 `#canvas` 画到离屏 canvas，`toDataURL('image/png')` 后丢进 Web Worker；Worker 内 `importScripts` 加载 Tesseract.js，`createWorker('eng')` 对整屏截图 OCR，文本里 `.includes("AFK")` 就 `new Notification("Florr.io anti-AFK",...)`。每 5 秒扫一轮，Alt+P 启停。核心工程技巧有两个：(a) **Web Worker 独立线程做 OCR**，不卡游戏主线程；(b) **覆写 `window.requestAnimationFrame`**——脚本运行期把 RAF 替换成由另一个 Worker `setTimeout` 驱动的 `preciseTimeout(cb, 15, 'frame')`，绕过浏览器后台标签页把 RAF 节流到 0 的限制，使**游戏在最小化/虚拟桌面里仍以 15ms 帧速渲染**，从而脚本可以在后台持续截图检测。`dev.js` 是把 OCR 换成逐像素遍历占位（`postMessage({matchFound:false})`）的教学脚手架。

## 可偷清单
- ① 可整合算法/数据：
  - **⭐ 后台保渲染技巧**：覆写 RAF + Worker 精准定时器（`timerBlob`/`preciseTimeout`）。现有 bridge 若在浏览器侧运行脚本，这套手法能让「最小化标签页也持续出帧」，是对 afk_solver 桌面级 PostMessage 的**浏览器层互补**。
  - **OCR 检测范式**：整屏 Tesseract OCR + 子串 `"AFK"` 判定。与 afk_solver 的颜色几何法不同，它是「文字出现即报警」，可作为 afk_solver `find_afk_window` 找不到弹窗时的**兜底告警通道**（检测到 AFK 字样→通知/触发求解）。
  - 与 `afk_solver.py` 异同：afk_solver 是「求解并拖动」；本仓库只「发现并通知」。二者天然串成一条链：indicator 负责发现，afk_solver 负责破解。
- ② 协议/ID 映射：无表；给出 DOM 锚点 `document.getElementById('canvas')`（游戏画布节点 id）。
- ③ 与已偷资产差异/增量：已偷 wasm 数据无「浏览器后台渲染保活」与「OCR 文字检测」逻辑；覆写 RAF 的手法是全新工程增量。

## 风险/注意
- 整屏 Tesseract OCR 性能开销大（每 5s 一次全图识别），`createWorker` 每次循环重建，未做 worker 复用，主线程仍有抖动。
- 它**只通知不点**，不会自动过验证；依赖系统通知权限 granted。

---

# 5. antiafkflorrio（目录名：antiafkflorrio，作者 iiasceri）

## 能力摘要（约 240 字）
本批体量最大（~0.4MB，含图标/打包脚本）的 PySide6 抗 AFK 工具，核心是 `florrioafk.py`。思路是 **OCR 找单词「here」并双击它**——这是 florr 老式 AFK 验证的典型形态（弹窗里出现 "click here" 字样）。`anti_afk_florrio("here")`：Windows 下先 `pyautogui.doubleClick(屏幕中心)` 抢焦，再 `pytesseract.image_to_data` 对整屏 OCR；`scan_and_click` 遍历每个词框，若目标词是词子串就算中心点并 `pyautogui.doubleClick`；**若词里含 "?"**（即验证提示问句），则循环 15 次每次 `center_v += 3` 下移再双击，兜底去点下方的 "here"。两条定时器：`HelloWorldTimer` 每 **5s** 跑一次 `anti_afk_florrio("here")`；`HelloWorldLongTimer` 每 **120s** 在固定点 (900,500) 双击一次，模拟人偶尔动鼠标。Mac 分支用 `system_profiler` 读分辨率并按 `random.uniform(1,2)` 的 `img_multiplier` 做 OCR 缩放。

## 可偷清单
- ① 可整合算法/数据：
  - **⭐ 老式 "here" 单词验证解法**：OCR `image_to_data` 拿词框 → 中心点 → doubleClick；对 "?" 提示词做**逐行下移双击（v+=3，循环 15 次）**去够下方 "here"。这是 afk_solver（连线型）之外的**第二种验证题型解法**，若服务器回退到老式点击验证，可直接移植。
  - **拟人化节奏**：随机 OCR 缩放倍率 `img_multiplier=random.uniform(1,2)`、双击而非单击、先点屏幕中心抢焦、120s 一次的周期性存在感点击——这些「模拟人」细节可注入现有 bridge 的行为层，降低被风控识别为脚本的概率。
  - 与 `afk_solver.py` 异同：同属「截图→屏幕动作」，但题型不同（点单词 vs 拖路径）；afk_solver 的 PostMessage 后台拖动不抢焦点，本仓库用 pyautogui 真鼠标且会抢焦，**抗检测性本仓库更弱**，但其拟人节奏思路可被 afk_solver 借鉴。
- ② 协议/ID 映射：无表；关键字符串 = 目标词 `"here"` 与提示词特征 `"?"`。
- ③ 与已偷资产差异/增量：已偷 wasm 无验证题型库；本仓库把「老式点击验证」这一题型的 OCR 解法补全，与连线型形成题型对照。

## 风险/注意
- pyautogui 真鼠标双击会**抢焦点、动真鼠标**，最小化不可用，且动作硬编码（`(900,500)`、中心双击），分辨率敏感。
- `pyautogui.FAILSAFE` 未设（本文件），误点风险高；依赖本机装 Tesseract-OCR。

---

# 6. florr.io-scripts（目录名：florr.io-scripts，作者 SquchyBear）

## 能力摘要（约 150 字）
单文件脚本 `AFK Checker.py`，是仓库 5（antiafkflorrio）的**极简教学阉割版**，仅 38 行。硬编码游戏区域 `top_left=(0,180)`、`bottom_right=(1920,1130)`，`pyautogui.screenshot(region=...)` 只截这条横向游戏带。主循环（实际跑一轮后 `break`）：先 `doubleClick` 截图区中心抢焦，再 `click_word(image,"here")`——OCR 找 "here"，算词框中心后**循环 10 次、每次 y+=10、间隔 0.1s 双击**，沿竖直方向逐行去点 "here"。开头 `sleep(2)`，结尾 `sleep(5)` 后退出。设了 `FAILSAFE=True` 并硬编码 tesseract 路径 `C:\Program Files\Tesseract-OCR\tesseract.exe`。

## 可偷清单
- ① 可整合算法/数据：
  - **裁剪 ROI 思路**：只截游戏主条带 (0,180)-(1920,1130) 而非全屏，缩小 OCR 搜索域、提速。可给现有 combat.py 的屏幕检测圈定有效区域做参考。
  - **逐行下探点击**：`for _ in range(10): doubleClick(x, y); sleep(0.1); y+=10`——和仓库 5 的 "?" 下探同构，是「OCR 定位不准时沿一个方向补点」的通用兜底手法。
  - 与 `afk_solver.py` 异同：同为视觉解题，但它是点单词题型 + 真鼠标单击循环，afk_solver 是连线题型 + PostMessage 后台拖；逻辑最简，适合当 OCR 点击验证的最小可跑模板。
- ② 协议/ID 映射：无；关键字符串仍是 `"here"`；并给出 1920×1080 下游戏可视带 y∈[180,1130] 的实测裁剪框。
- ③ 与已偷资产差异/增量：无数据表增量；价值仅在「最精简的 OCR 点击验证骨架」可作原型。

## 风险/注意
- 只跑一轮就 `break`，不是常驻脚本，需外部循环反复拉起。
- 硬编码分辨率与 tesseract 路径，跨机即废；无 GUI、无异常处理。

---

# 本批小结：6 个仓库 AFK 手法 vs 现有 afk_solver.py 的横向结论

1. **题型代差是核心差异**。现有 `afk_solver.py` 破解的是**「拖动连线」型**验证（稀有色起点→灰路径→孔洞终点，Dijkstra 最宽瓶颈 + RDP + PostMessage 后台拖），这是较新版本的 florr 验证；而本批 6 个老仓库破解/绕过的全是**更早的题型**：定时切槽保活（仓库 1、3）、OCR 点单词 "here"（仓库 5、6）、DOM 点 afkCheck 按钮（仓库 3）、OCR 监测弹 AFK 字样（仓库 4）、红叉模板匹配自动复活（仓库 2）。**没有一个仓库碰拖动连线**，故对 afk_solver 的核心求解算法零直接替代，价值在「补题型 + 补保活 + 补工程技巧」。

2. **真正值得偷的 3 条增量**：
   - **DOM 钩子** `button[data-qa-id="afkCheck"]`（仓库 3）——若仍有效，可把 afk_solver 的整套视觉流水线短路成一次 click；务必本地 DevTools 先验活。
   - **后台保渲染**：覆写 `requestAnimationFrame` + Web Worker 精准计时（仓库 4）——让浏览器侧脚本在标签最小化时仍出帧，是 afk_solver 桌面级 PostMessage 的浏览器层互补。
   - **拟人化节奏**：随机按键抖动（仓库 1）、随机 OCR 缩放倍率、双击、5s/120s 双定时器周期性存在感点击（仓库 5）——可注入 bridge 行为层抗风控。

3. **与现有模块的搭接点**：仓库 2 的「红叉/ready 模板匹配死亡状态机」可补 combat.py 死后无人接管的闭环；仓库 5/6 的 OCR "here" 下探点击可作 afk_solver 找不到连线弹窗时的兜底题型。整体建议优先级：先验仓库 3 的 DOM 钩子是否存活 → 再评估仓库 4 的后台保渲染是否值得移植 → 仓库 1/5 的拟人节奏作调参参考；仓库 6 仅作最小原型，仓库 2 视是否需要自动复活闭环决定取舍。

4. **已偷资产对照**（③ 统一清单）：wasm_dump\client.wasm(9190KB)/all_strings.txt/wasm_struct.json；data\all_mobs.json / all_petals.json / mob_stats_full.json / florr_dropchance.json。本批 6 仓库**均未提供任何新的怪物/花瓣/掉落结构化数据**，全部为行为/工程脚本，故对上述数据层无增量，增量集中在 AFK 题型解法、保活节奏与浏览器后台技巧。
