# florr.io 全自动挂机插件（内存/截图双模式）

> 全自动：进图 → 巡逻 → 打怪 → 捡掉落 → 回血 → 防挂机检测 → 死亡复活重进
> 不用看屏幕，不用动鼠标，键盘自动操作（WASD 移动 + 空格切换回血花瓣）
> 多语言架构：Python 主控 + HTML/CSS/JS 问卷界面 + 浏览器注入(JS) + Go 桥接 + C++ 级 OpenCV 加速（detect_mobs 合并连通域）

## 快速开始（小白版）

**免 Python 版**：到 [Releases 页面](https://github.com/florrplayer/florr-auto-plugin/releases) 下载最新 `florr-auto-beginners-vX.Y.zip`（即小白版，v1.34.0），解压后双击 `启动.bat`，按提示选择地图即可，无需安装 Python/依赖。

1. 打开 florr.io（Edge/Chrome 都行，**不要最小化，窗口保持在前台**）
2. 进地图（花园/沙漠/海洋/蚂蚁地狱都支持）
3. 运行 `py main.py 地图名`（如 `py main.py desert`）
4. 挂机中！看 cmd 日志就行

## 内存模式（v1.35 默认自动开启，免截图，更快更准）

- **默认自动**：运行 `py main.py 地图名` 会自动探测/拉起 bridge_server，连上即内存模式，连不上自动回退截图模式，零配置
- 小白版自带 **bridge_server.exe**（免 Python 环境），内存模式开箱即用
- 直接读 wasm 内存：玩家坐标 100% 准确、怪种类/稀有度(HP反推)/真实碰撞箱/追击圈全识别
- 参数：`--screenshot` 强制截图模式；`--memory` 强制内存模式

## 功能

- **全地图支持**：花园/沙漠/海洋/蚂蚁地狱/冥界/金字塔，进图自动识别（v1.25.0 小地图模板匹配）
- **巡逻/打怪**：巡逻点循环，秒杀优先追、打不动避开，稀有怪（正方形/闪亮瓢虫/金叶虫/潜水兵蚁/赌徒/组装机/法老甲虫/幽灵）权重 5000
- **深度 AI 研究**（v1.25.2）：目标粘滞速杀防拉扯 + 传送门 3 秒无敌窗 + 蟑螂/螃蟹打带跑横移 + 导弹射程撤出 + 波末原地防御
- **Super 雷达**：公告检测全图猎杀 Super，真人喊话模板
- **防挂机检测**：AFK 弹窗自动破解（拖动验证码）、聊天挑战自动回复、随机走动
- **回血系统**：低血切防御 + 自动切换回血花瓣（玫瑰/大丽花/丝兰/海星）
- **稀有度 13 档官方 RGB 表**（v1.25.3）：Eternal/Primordial/Exotic 全档颜色反查

## 目录结构

- `docs/`：全部研究报告与速查表（怪血量/掉落概率/稀有生物/地图与Boss机制等 12 份）
- `data/`：官方游戏数据（73 怪 / 118 花瓣 / 96 天赋 / 3.6万 wasm 字符串 / 332 条掉率实测 / 1px 换算表）
- `maps/`：全地图图片 + Tiled 地图源文件（*.tmj/*.tsj）
- `releases/`：小白版打包
- 根目录：插件源码（main.py / combat.py / utils.py …）

官方数据来源：通过浏览器 JS 调游戏 wasm 导出接口（`_Util_GetMobs`/`_Util_GetPetals`/`_Util_GetTalents`/`_Util_CalculateDropChance`）实测导出。
## 性能优化（v1.6.0）

- **每圈共享一次 HSV 转换**：主循环一次 `cvtColor` 供 detect_all/detect_super/detect_projectiles/detect_drops 复用（原每检测函数各转一次全图）
- **detect_all 合并连通域分析**：7 个稀有度档合并为 1 次 CC + 连通域中心单像素判档（原每档各跑一次全图连通域，快 2.5-5 倍）
- **低频检测闸门**：特殊稀有生物每 0.4s 检测一次、掉落每 0.3s 一次（极稀有/非战斗核心，不必每帧跑）
- **贴脸不再犹豫**：追击贴脸由"间歇点按试探"改为直接连续走（停在怪碰撞箱外，不会撞上）
- 实测：整圈四检测 300ms+ → 126ms
## 掉落价值筛选与威胁提示（v1.7.0）

- **掉落只捡值钱的**：detect_drops 现在按中心像素判稀有度，只捡 Epic(紫) 以上掉落（可改 PICKUP_MIN_RANK），垃圾掉落不再浪费时间跑过去
- **官方威胁提示**：新增 data/mob_threat.json（73 怪 × 7 档官方伤害/血量/护甲/exp/掉落），战斗日志显示目标怪官方伤害与血量（如"蜜蜂M 伤害12150/血110565"），打之前心里有数
- 威胁数据来源：官方 wasm 内存导出（_Util_GetMobs 全字段），与血量速查表同源
## Go 版桥接（v1.26.0）

- **bridge_server.exe（Go 交叉编译，双击即用，免 Python 环境）**：接口与 `py bridge_server.py` 100% 兼容（GET 拉数据 / POST 浏览器 hook 推送），单静态 exe 免装 Python，小白直接跑
- 源码 `bridge_server.go`：`go build bridge_server.go`（本机）/ `GOOS=windows GOARCH=amd64 go build -o bridge_server.exe bridge_server.go`（出 Windows exe）
- 实测桥接层不是性能瓶颈（Python 与 Go 同量级）；真正的"不犹豫"收益来自内存模式本身（免截图）+ 后续推送式协议（WebSocket/增量帧）
## 多语言增强（v1.34）

- **HTML/CSS/JS 问卷界面（config_web.py）**：启动配置弹窗从 tkinter 换成浏览器网页问卷（问卷星风格：一题一页、鼠标点选变蓝、下一步提交；点选可靠不串键），tkinter 自动兜底
- **detect_mobs 合并连通域**：M(青)/U(粉) 两个 mask 合并成 1 次降采样+连通域，按中心 5x5 平均 HSV 分拣（2 次 CC → 1 次），实测 7.1ms → 5.8ms（-18%）
- **Edge AIEP 窗口兼容**：Edge 更新后窗口类名带 `_AIEP_xxx:` 前缀，find_window 改包含匹配
- **完全后台键盘移动**：auto/默认一律 PostMessage 键盘（不碰真实鼠标），后台/最小化都能挂
