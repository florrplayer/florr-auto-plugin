# reference-florr-tools-07 小仓库：Hacks 与旧版类

> 范围：`reference-florr-tools/` 下 6 个 Hacks/旧版/对比类仓库，全程只读本地磁盘，未联网。
> 对照资产：主插件 `florr-auto-pathing-main/`（combat.py / mob_db.py / memory_reader.py / bridge / afk_solver.py / net_protocol.py），已偷 wasm 资产 `wasm_dump/client.wasm`(9,410,540 B) / client.js(125,937 B) / all_strings.txt / wasm_struct.json / AI逆向_wasm函数分析.md。

---

# The-Script-andnn（Andn-X iogames 合集）

## 能力摘要
一个油猴脚本收藏夹（非单一插件），覆盖 florr.io 官方站与私服 flowr.fun，共约 18 个文件。核心是一个**基于 Canvas 2D Proxy 的无内存读取外挂**：不靠读游戏内部对象，而是 hook `fillText/strokeText/beginPath/moveTo/lineTo/requestAnimationFrame/addEventListener`，从游戏渲染调用中反推怪物位置、血条、按钮坐标。代表文件 `hack florr.io`（作者 m28）实现了稀有度染色追踪线（tracers）、自动寻最近怪刷怪（autoGrind）、自动换生物群系复活（autoRespawn，可选 Garden/Desert/Ocean/Jungle/Hel）、绕过 AFK 检测（伪造 mousemove 正弦抖动 + 自动点 `I'm here`）。其余文件为小工具：服务器选择器（hook `m28n.findServerPreference`）、小地图贴图、无受击白闪、关动画提帧、按键可视化、花瓣刷取计数器、hornex 服进度查询等。

## 可偷清单
- ① 可直接整合进现有插件的算法/数据：
  - **稀有度→颜色/序号表**（`hack florr.io` 内 `rarities` 对象，8 档）：Common `#7eef6d`/0、Unusual `#ffe65d`/1、Rare `#4d52e3`/2、Epic `#861fde`/3、Legendary `#de1f1f`/4、Mythic `#1fdbde`/5、Ultra `#ff2b75`/6、Super `#000000`/7。可校准 combat.py 屏幕颜色识别的颜色阈值。
  - **Canvas 反推怪物/按钮坐标法**：当 mob_db 内存读取失效时，备用“屏幕渲染反解”通道。它通过 `getTransform()` + 矩阵求逆（`untransform`，`multiply` 3x3）把画布坐标映射回世界坐标——可作为 memory_reader.py 的视觉兜底。
  - **按钮识别表 `buttonData`**：Ready/Garden/Desert/Ocean/Jungle/Hel/Continue/Play as guest 各自的 `color`+`font`（如 Ready `'#ffffff'`/`'27.5px Ubuntu'`），可用于 afk_solver.py 的菜单按钮定位。
  - **AFK 绕过参数**：每 100ms 周期、`clickButton` 要求按钮静止（位移 `<0.01`）且存在满 2000ms 才点、`I'm here` 点击前随机延迟 `500+2000*Math.random()`——拟人化反检测节奏可直接借用。
- ② 协议/ID/中文名等结构化表：
  - **服务器 API**：`https://api.n.m28.io/endpoint/florrio/findEach/` 返回 `servers`（含 `id`、linode-/vultr- 前缀）；WebSocket URL 形如 `wss://(\w{4}).`，首字节 `getUint8(0)===1` 为连接握手（见 `Florr.io Server Selector`）。
  - flowr.fun 复兴服扩展稀有度（`FlowrScriptcloud.txt`，`window.flowrMod.rarities[0..15]`）共 16 档，比官方站多 8 档（索引 8~15，如 Ultra 之后新增 `#494849/#ff5500/#67549c/#b25dd9/#520380/#046307/#00bfff/#c77e5b`）——若主插件以后兼容私服，是现成数据表。
  - `localStorage.florrio_tutorial='complete'` 跳教程；`localStorage.cp6_player_id` 玩家 ID（跨多个脚本一致）。
- ③ 与已偷资产的差异与增量：主插件走“内存读取 + 像素截屏”路线，这里走“渲染 hook 反解”，**是一条完全独立的实体定位通道**，未被现有 memory_reader/combat 覆盖；稀有度颜色表与 mob_db 的颜色标定互为校验。

## 风险/注意
`hack florr.io` 会主动伪造 mousemove/mousedown/mouseup 事件并 hook `blur/focus/visibilitychange`（屏蔽切窗检测），属明确对抗服务器反作弊逻辑；`florr-anti-afk` 会外链播放 `zvukogram.com` 音频；`hornex.pro.txt` 通过 `GM_xmlhttpRequest` 拉 `zcxjames.top/data.json`。仅作算法参考，不建议原样运行。

---

# iogames（theiogamedestroysa 单文件 3.1MB hacks 包）

## 能力摘要
目录下唯一文件 `iogames/florr`，9 行、3,121,326 B，是一份**重度混淆的 “Florr Cheats” 油猴脚本**。脚本头自称功能：Infinite accounts（无限账号）、auto bubble、minimap、fov、boss countdown timer、tracers、anti alt detection（仅对至少有一件 legendary 的账号/游客号生效）。正文是标准 JS 混淆管线：字符级拼接（`'t'+'o'+'n'...`）+ `constructor`/`unescape("%5X")` 取字符 + 一个运行时字符串数组轮换解码器（形如 `_0x9440(offset, ...)`，用一大串十六进制偏移算术还原字符串）。我静态还原了拼接片段与 token，能读懂的部分包括：它读取 `localStorage`（命中 `cp6_player`、`oauth2_dat`、`:local` 等 token），使用 `application/x-www-form-urlencoded` 做 HTTP POST（疑似账号/登录接口），并调用 `entries/push/shift/apply/constructor/flat/search` 等运行时 API。**读不懂的部分**：占体积 95% 以上的主体是被解码器虚拟化的字节码式函数表（`_0x44a3db={...}` 数百个 `_0x....:0x..` 映射 + `_0x314b` 解码函数），所有真实功能字符串（协议 opcode、实体表、作弊函数名）都在运行时由偏移算术拼出，静态无法逐段还原——要彻底读懂必须在沙箱里执行，而按要求未执行、也不应执行。

## 可偷清单
- ① 可直接整合进现有插件的算法/数据：
  - 静态可确认的**功能清单本身**就是需求验证：minimap / fov / boss countdown / tracers / auto bubble 这些需求方向，与主插件 combat.py、afk_solver.py 的目标高度重合——说明这些是社区公认的高价值功能。
  - **反 alt 检测的已知作用条件**：header 明说“只对至少有一件 legendary 的账号/游客号生效”——这泄露了服务器 alt 检测的判定粒度（与账号资产挂钩），对 bridge 层做拟人化/多开规避有情报价值。
- ② 协议/ID/中文名等结构化表：
  - 命中 `cp6_player_id`（与 old_betterflorr、The-Script-andnn 三方一致，确认是 florr 官方玩家 ID 的稳定 localStorage key）。
  - 命中 `oauth2_dat` / form-urlencoded POST——暗示账号体系走 OAuth2 + 表单接口，是“无限账号”功能的攻击面。
  - **未能提取**：具体 WS opcode、实体 ID 表、boss 倒计时逻辑——这些被虚拟化在解码器里，静态无产出。
- ③ 与已偷资产的差异与增量：相比 `wasm_dump` 已还原的游戏协议，这份包是“外挂侧”实现，但混淆度太高，**没有可直接落表的结构化增量**；其价值主要是功能情报与 localStorage key 确认。

## 风险/注意
**高风险**。这是带反 alt 检测绕过 + 无限账号 + 读取 oauth2/玩家凭证 localStorage 的混淆包，且主动发 form-urlencoded POST——具备把账号凭证外发的能力特征。混淆本身即恶意代码的典型特征。仅作文物分析，**严禁在登录态浏览器里运行**，不建议整合任何代码，只保留“功能方向 + localStorage key”两点情报。

---

# old_betterflorr（Crystal-awa，18 个 super ping 老版 js，约 0.7MB）

## 能力摘要
“BetterFlorr / super ping”插件的**早期纯 JS 油猴时代版本**（v1.1 → v2.8，文件名即迭代史）。README 自述：作者无 JS 基础，靠 DeepSeek/ChatGPT 一点一点写出，早期转发 fluffy 的 ping、后合作，中期独立开发，后期由“小燕子”用 Vue 重构（重构产物即本批 BetterFlorrSite）。技术核心是 **hook 游戏 WebSocket**：保存 `nativeWebSocket`，正则 `wss://([a-z0-9]+).s.m28n.net/` 从 URL 提取服号，结合服务器列表解析出 `{region, map, serverId}`，左上角实时显示当前服信息。功能随版本递增：v1.x 纯 super ping；v2.0 显示各服务器人数；v2.1/2.2 防顶号（断线自动重连 wss、强制换服）；v2.3 播报提示音（`new Audio()`）；v2.4 界面复位；v2.6 服号查询；v2.7 auto attack。开关状态持久化在 `localStorage['switch-N']`。

## 可偷清单
- ① 可直接整合进现有插件的算法/数据：
  - **换服/强制指定服号**：`window.cp6.forceServerID(id)`——这是**游戏自身暴露的换服 API**，主插件 bridge 若要做“自动选人少的服”，可直接调它，比模拟点击靠谱。
  - **断线重连 wss 逻辑**（`reconnectPendingGameWSS`）：保存原 WebSocket、关旧 socket、用 `Reconnectingserver` 重连的套路，可用于 bridge_server 的断线自愈。
- ② 协议/ID/中文名等结构化表：
  - **服号/区域映射 `regionToName`**：`NA→'US'`、`EU→'EU'`、`AS→'AS'`，默认原样返回——可直接进 net_protocol 的区域表。
  - **服务器 URL 正则**：`/^wss:\/\/[a-zA-Z0-9]+\.s\.m28n\.net(:443)?$/`（校验合法游戏服）；服号提取 `/wss:\/\/([a-z0-9]*).s.m28n.net\//`。
  - **localStorage 约定**：`cp6_player_id`（玩家 ID）、`florrio_lang`（语言，`isEnglishLang()` 判断）、`switch-N`（功能开关）。
  - **功能开关清单**（`switchNames`）：`["super播报","防顶号","聊天","super播报声音提醒","各服务器code查询","日志"]`。
- ③ 与已偷资产的差异与增量：
  - 注意：`reference-florr-tools/FlorrBt` 是一个 **C++ 工程**（`.slnx`/`FlorrBt.Server.vcxproj`/`CMakeLists` + `.tmj` 地图），是 florr 的私服服务端/启动器重实现，**并不是 super ping 插件的新版**；super ping 的真正后继是本批 BetterFlorrSite（见下节）。因此“与 FlorrBt 对比”在此不成立，已如实更正。
  - 老版**独有/已退化的点**：纯前端油hook、零构建，调试友好；新版 Kotlin/Wasm 化后，这类“hook WebSocket URL 正则取服号”的轻量技巧在 wasm 里不直观，老版是最易读的参考实现。老版的 `cp6.forceServerID` 用法在新版 wasm 中未见对应可读符号。

## 风险/注意
含“防顶号”（模拟强制换服、保持连接）属对抗账号顶号机制；播报提示音外链音频。代码为 AI 生成、作者自述“写得很石”，质量参差，引用时取思路不复用其 UI/重连实现。

---

# BetterFlorrSite（LittleSwift，wasm 1.997MB + js 940KB + CNAME）

## 能力摘要
BetterFlorr 经“小燕子”重构后的**新版（Kotlin/Wasm 编译产物）**：`BetterFlorr-wasm-js.wasm`(1,997,678 B) + `BetterFlorr.js`(940,680 B，webpack + eval-source-map 胶水) + `CNAME`。我对两个 wasm 做了逐 section 解析硬对比，结论明确（见下）。

## 可偷清单
- ③ **wasm 对照 `wasm_dump/client.wasm`（本批核心结论）**——两者根本不是同一程序，BetterFlorrSite **不是**主游戏 client.wasm 的旧版：

  | 维度 | BetterFlorrSite/BetterFlorr-wasm-js.wasm | wasm_dump/client.wasm（主游戏） |
  |---|---|---|
  | 文件大小 | 1,997,678 B | 9,410,540 B（约 4.7 倍） |
  | 导出函数数 | **14** | **46** |
  | 导出名形态 | `__callFunction_((Js?)->Js?)`、`(String)->Unit`、`main`、`_initialize`、`memory` | 压缩混淆名 `Mf/Nf/Qf/Of/...`（2~3 字母） |
  | import 模块 | 单一 `js_code`，**3968 条**，全是 `kotlin.wasm.internal.*` / `kotlin.js.*` / `org.w3c.dom.*` / `org.khronos.webgl.*` | 少量游戏宿主 import（2,475 B） |
  | 代码段 | 394,287 B | 5,026,796 B |
  | 数据段 | 125,626 B | 4,358,635 B |
  | 自定义段 | **1,088,679 B（debug/sourcemap 符号）** | 无大符号段 |
  | 技术栈标识 | 命名空间 `<moe.littleswift:BetterFlorr>`，入口 `addBetterFlorrWidget`、`showUI`、`lazyMessage` | 无 Kotlin 符号，纯游戏逻辑 |

  **判定**：BetterFlorr 的 wasm 是**插件（mod）本身用 Kotlin/Wasm 编译的产物**（导出名是 Kotlin 类型签名 `(Js?)->Js?`，import 全是 Kotlin stdlib/DOM/WebGL 绑定），而 `client.wasm` 是 **florr.io 游戏客户端本体**（minified 导出名 + 5MB 代码 + 4.3MB 游戏数据）。二者体积、导出名风格、符号表完全对不上，不存在“旧版/新版”关系。BetterFlorrSite 的 `BetterFlorr.js` 是 `kotlin/BetterFlorr-wasm-js.uninstantiated.mjs`，即 Kotlin/Wasm 的 JS 运行时胶水（`instantiate(imports)`、`js_code={kotlin.wasm.internal...}`），**不是**游戏 client.js。

  **增量价值**：正因为它是 Kotlin/Wasm 且带 1MB 符号段，插件自身的类名/入口（`addBetterFlorrWidget`、`showUI`、`lazyMessage`）**可读**，比 minified 的游戏 client.wasm 易懂得多；它通过 `org.w3c.dom.MessageEvent`、`Notification`、WebSocket DOM 绑定挂钩游戏消息——是研究“BetterFlorr 新版如何拦截游戏 WS 消息”的最佳样本，而这部分逻辑在游戏 client.wasm 里是混在 9MB 混淆码中的。

- ①/②：wasm 内应用层类名已被混淆（仅 `addBetterFlorrWidget` 等少数入口残留），未发现可直接落表的新协议 opcode 或实体 ID；消息拦截面体现在对 `MessageEvent`/WebSocket 的 DOM 绑定上，与 net_protocol.py 是互补（它 hook 浏览器 WS，主插件 hook 进程内存）。

## 风险/注意
本地 `CNAME` 表明这是部署到某域名的站点产物；wasm 带 sourcemap 符号段说明是**非发行优化构建**。仅作结构对照样本，不参与运行。

---

# florr-auto-pathing（Shiny-Ladybug，11 文件 0.1MB）——主插件原版基础

## 能力摘要
主插件 `florr-auto-pathing-main/` 的**原始上游版本**（作者 Shiny-Ladybug，纯客户端、1920×1080 硬编码、pyautogui + OpenCV）。核心是 **Lazy Theta\* 路径规划**：在二值化小地图上做 `lazy_theta_star`（带 `line_of_sight` 视线检测的 θ\* 平滑），再用 `go_direction` 移动鼠标到屏幕中心偏移点来走位，带 `execute_anti_stuck`（检测地图边界色点做斥力场脱困）。配套 `map_select.py`（点选目标坐标）、`area_select.py`（框选活动区域）。

## 可偷清单（逐文件 diff 主插件，结论明确）
以文件名为锚点，主插件相对原版的**新增/修改**：

- **main.py：340 行 → 1351 行（+1011 行，最大改动）**。
  - 保留：`lazy_theta_star`、`line_of_sight`、`go_neighbor`、`go_direction`、`lazy_theta_pathing` 核心骨架与原版基本一致。
  - **主插件新增**（原版完全没有）：`human_ticks`（拟人鼠标节奏）、`throttle_print`、`set_title`、`freeze_watchdog`（冻屏看门狗）、`chase_target`（追怪/巡逻击杀，含 `kill_rank` 分级）、`walk_to_pickup`（走位捡物）、`leech_target`（蹭/寄生目标）、`handle_danger`（危险实体规避）、`dodge_proj`/`nearest_proj`（躲弹幕）、`flee_low_hp`（低血逃跑，`heal_slots`）、`screen_to_map_safe/_keep_r/_keep_sid`（屏幕↔地图坐标换算）、`draw_overlay_window`（叠加窗）、`attack_loop`/`defense_loop`/`human_mouse_loop`（战斗主循环）。即主插件已从“纯寻路脚本”进化为“战斗 bot”。
- **utils.py：229 行 → 406 行（+177 行）**。
  - 原版硬编码 `1920×1080`、`./maps` 相对路径。
  - **主插件新增**：`MAP_DIR`（地图目录常量，相对本文件）、`set_screen_center/get_screen_center`（**分辨率自适应**，原版没有）、`get_frame`（共享截帧）、`detect_canvas_offset`、`_detect_minimap`、`respawn()`、`_nearest_grid`。
- **area_select.py：58 → 63 行**。改为 `MAP_DIR` 定位 + 支持 `sys.argv[1]` 传地图名 + 中文报错（找不到地图时列出可选）；核心框选逻辑不变。
- **map_select.py：26 → 52 行**。从“点一下打坐标即退出”升级为**巡逻点选取循环** `select_patrol_points()`：左键加点、右键撤销、`Enter` 确认、`Esc` 取消、至少一点，返回 `patrol_points` 列表——直接服务 main.py 的巡逻/追怪。
- **主插件独有、原版不存在的文件**：`config.py`(15.6KB)/`config.json`、`movement.py`(MoveState 类，`set_mode`/`move_towards`/`_mouse`/`_keys` 鼠标/按键双模)、`memory_reader.py`(3.7KB)、`combat.py`/`mob_db.py`/`net_protocol.py`/`afk_solver.py`/`bridge_server.py` 等——这些是主代理在原版寻路之上自建的整套战斗/内存/桥接体系。
- **maps/**：原版带 `anthell.png/desert.png/ocean.png` 三张二值地图，主插件沿用。

- ① 可偷：原版的 `execute_anti_stuck` 边界斥力场（`calc_anti_stuck`：以屏幕中心 960,540 为原点，对每个边界轮廓点施加反向斥力再 `clip` 到 1920×1080）是个干净的脱困算法，主插件已吸收；`check_stage()` 通过固定像素点色值判定 `in_game/in_game_dead/in_menu`（(316,32)=(187,85,85) 游戏中、白色死亡、(156,35)=(155,181,107) 菜单）这套色点判态可复用。

## 风险/注意
原版声明客户端、1920×1080 全屏硬编码；主插件已做分辨率解耦。无恶意行为（纯 pyautogui 模拟鼠标），风险低。

---

# FlorrCheatsV3

## 能力摘要
空仓库（目录存在、0 文件）。无内容可分析。

## 可偷清单
无。

## 风险/注意
占位/已删空仓库，跳过。

---

## 本批小结
1. **BetterFlorrSite 的 wasm 与主代理 `client.wasm` 的版本对比结论（重点）**：不是新旧版本关系。BetterFlorr-wasm-js.wasm(1,997,678 B, 14 个 `__callFunction_` Kotlin 签名导出, 3968 条 kotlin/dom/webgl import, 1MB 符号段, 命名空间 `moe.littleswift:BetterFlorr`) 是 **BetterFlorr 插件本体的 Kotlin/Wasm 编译产物**；`wasm_dump/client.wasm`(9,410,540 B, 46 个 minified 导出 Mf/Nf/…, 5MB 代码 + 4.3MB 数据) 是 **florr.io 游戏客户端本体**。两者导出名风格、体积、符号表完全不同，无可比性；BetterFlorrSite 的价值在于它带 Kotlin 符号、可读地展示了新版插件如何经 DOM `MessageEvent`/WebSocket 挂钩游戏消息。
2. **跨仓库稳定命中的协议/情报锚点**：`wss://xxxx.s.m28n.net/`（服号）、`localStorage.cp6_player_id`（玩家 ID）、`window.cp6.forceServerID(id)`（游戏自带换服 API）、`https://api.n.m28.io/endpoint/florrio/findEach/`（服务器列表）、区域映射 NA→US/EU/AS——这些在 The-Script-andnn、old_betterflorr、iogames 三处独立复现，可信度高，可直接固化进 net_protocol.py。
3. **安全红线**：iogames 的 3.1MB 混淆包（反 alt + 无限账号 + 读 oauth2 凭证 + form POST）判定为高风险恶意特征，仅取功能情报、不整合代码；The-Script-andnn 的 Canvas-proxy 外挂与 old_betterflorr 的防顶号属对抗服务器逻辑，只借算法思路。
4. **主插件 vs 原版 florr-auto-pathing**：已逐文件给出 diff——寻路核心（θ\*、anti-stuck、色点判态）沿用原版，主插件自加了分辨率解耦、巡逻点选取、以及整套战斗层（chase/dodge/pickup/flee/拟人节奏）与内存/桥接体系。
