
> 最新小白版下载: [florr-auto-v1.7.3-win64.zip](https://github.com/florrplayer/florr-auto-plugin/releases/download/v1.7.0/florr-auto-v1.7.3-win64.zip) (解压后双击 启动.bat 即用, 无需装 Python)
# florr-auto-pathing

## 📥 直接下载（小白版，双击即用，无需装 Python）

👉 **[点这里下载 florr-auto-v1.7.3-win64.zip](https://github.com/florrplayer/florr-auto-plugin/raw/main/releases/florr-auto-v1.7.3-win64.zip)**

下载后解压：用 Edge 打开 florr.io 进游戏 → 双击 `启动.bat` → 输入地图数字 → 回车。

---

## 🆕 中文功能简介（v1.4.0）

- **巡逻挂机**：**刷怪区域系统（v1.4.0 新增）**——启动时问"选区域还是自动"：自动=按你的秒杀等级推荐对应稀有度刷怪区（游戏里按 Alt 可看各区域稀有度），手动=直接选这张图的区域（出生点/蜜蜂区/Spiral、入口区/ss区/Tunnel/Box、常规/机密/绝密、浅水/中部/深水……），自动生成巡逻点，**再也不用鼠标点巡逻点**；也可选"重新设置"回退手动点选（校准用）
- **智能战斗**：启动时问你"全程攻击 / 防御 / 不弄" + "能秒杀的怪等级" + "刷怪区域"（问卷星风格弹窗，鼠标点选高亮）
  - = 秒杀等级 → 自动追着打（贴脸 0.5px，攻击模式 2px）
  - > 秒杀等级 → 避开（往怪最少的方向跑）
  - < 秒杀等级 → 不管
- **只打 M 怪（青）/避开 U 怪（粉）**：人性化小心走位（提前绕开、追击中停手、贴脸减速试探）
- **避开飞行物**：黄蜂/胡蜂导弹、蝎子螫针、大黄蜂花粉、蒲公英花瓣、海胆导弹等（通用帧差检测，含 Mythic 超大导弹）
- **回血花瓣种类设置（v1.3.0 新增）**：启动时问"你带哪种回血花瓣"——玫瑰(20%爆发救急)/大丽花(30%稳定)/丝兰(20%防御回血)/海星(40%提前切)，自动定低血触发线；血量低时自动把回血花瓣切到主槽 + 防御 + 往怪少处跑，恢复后自动切回原配置；**自动扫描副槽回血花瓣并弹窗确认**（防颜色误检），支持多个回血槽
- **Boss 血条检测（v1.3.0 新增）**：屏幕顶部出现 Super+ 级 Boss 大血条时，暂停追怪 10 秒先回避（75 级前杀 Boss 只掉究极档，别送死）
- **掉落自动拾取（v1.4.0 新增）**：识别屏幕内小尺寸彩色亮点（掉落花瓣），顺路走过去捡（只捡近的，不影响战斗主线）；没点 Magnet 天赋也不漏花瓣
- **更智能（v1.4.1 新增）**：卡墙自动绕路（随机偏走绕过障碍，不再干卡住）｜巡逻顺序随机化（不固定路线，更像人+防挂机）｜怪潮预警（屏幕怪太多被围时往怪少处走）｜运行统计（每 5 分钟打印：运行时长/战斗次数/拾取数）
- **特殊稀有生物优先打（v1.4.4）**：金叶虫（黄金之叶）> 黄瓢虫Shiny Ladybug（Yggdrasil复活）> shiny闪亮 > 潜水兵蚁 > 正方形，60px 内优先放下巡逻去追（固定目标模式，一路追到消失）；**追金叶虫前会警告"别带魔法球"**（否则不掉黄金之叶）；颜色为初版估计，实测误检/漏检截图后可精调
- **Super 薄荷绿识别（v1.4.4）**：识别超级怪（#2BFFA3 薄荷绿描边），leech 开则蹭 1% 掉落（Super 分 25 人），否则避开（75 级前杀 Super 只掉究极档）
- **AFK Check 弹窗自动点（v1.4.4）**：游戏随机弹 "Are you here?"（60 秒不点踢下线）——检测到屏幕中央暗色遮罩+画面静止，自动点 Yes 按钮（按钮位置初版估算，实测不准可校准）
- **实际碰撞箱感知（v1.4.6）**：florr 碰撞检测=圆形 hitbox，半径=怪图形半径——插件用**轮廓最小外接圆**精确算出每只怪的实际碰撞半径（圆形怪误差≈0，非圆怪按长轴保守偏大），追击/蹭掉落的目标点外移到「实际碰撞半径+安全距」之外——**打怪站在碰撞箱外，不再撞进怪身体掉血**；高稀有度大怪自动更远站定；Super 大怪蹭伤害时更安全
- **官方体型缩放表（v1.4.7）**：依据 Unofficial Florr Data Spreadsheet（游戏数据）——怪体型相对 Common：Unusual ×1.1 / Rare ×1.3 / Epic ×1.5 / Mythic ×3 / Super ×10。插件视觉轮廓测量天然包含该缩放（M 怪自动站 3 倍远、Super 站 10 倍远）；并新增 **Super 体型校验**——薄荷绿小色块（半径<下限）不算 Super，防误检
- **怪种识别（v1.5.0）**：读取游戏内存官方数据（73 种怪 sid + 官方体型缩放表）→ **每只怪自动识别种类**——屏幕半径 ÷ 官方体型缩放 = Common 基准大小，按「大小+形状（宽高比/矩形度）」分类怪种（岩石/蜜蜂/瓢虫/甲虫/蚁穴/幼蚁/工蚁/兵蚁/黄蜂/蚁后/蜈蚣/正方形…），战斗日志显示怪种中文名（如"发现目标 黄蜂(mythic)"）；官方 73 sid 中文名映射表 mob_table.py 由游戏数据生成
- **官方掉落概率（v1.5.1）**：从游戏 wasm 调用 `_Util_CalculateDropChance` 实测导出 **332 条 Mythic/Ultra 档掉率**（florr_dropchance.json + 掉落概率速查表.md）→ 战斗日志显示目标怪掉落提示，如 `[战斗] 发现目标 蜜蜂(mythic) ... | M档掉落: stinger 94.1% pollen<0.1% honey<0.1%`；打什么怪掉什么花瓣一目了然
- **实时地图窗口**：红色线实时显示寻路路径、绿点=玩家、蓝点=巡逻点、黄点=当前目标
- **所有地图**：沙漠 / 蚁之狱 / 海洋 / 花园 / 丛林 / 下水道 / 地狱 / 工厂 / 水晶房间 / 训练场（含捷径）
- **死亡后全键盘操作**：按 Enter 复活、按 Enter 开始，自动回游戏继续挂机
- **防挂机**：人性化微操作（随机微转向/微停顿/微抖动，无副作用不打断战斗）+ 随机停顿 + 鼠标微动 + 反应延迟
- **启动更快**：回血花瓣确认过一次后跳过扫描；巡逻点同地图自动复用（问一次"用上次的"）
- **任意分辨率自动适配**：4K/1080p/笔记本缩放都行（启动自动标定）
- **窗口随便弄**：florr 最小化/被遮挡会自动恢复窗口继续挂机（画面冻结监测）
- **黑窗口标题实时状态**：巡逻中 / 战斗中 / 低血逃跑 / 死亡复活中
- **日志精简**：菜单等待/死亡复活等高频消息节流，不刷屏

## 🎯 打怪策略（基于维基/攻略整理）
- **秒杀 = 必拿掉落**：游戏掉落按伤害贡献分配（U级以下恰好4人分掉落，总伤害>1%才有资格；单人挂机杀死必得），插件贴脸持续输出能秒的怪 = 100%伤害 = 掉落必得
- **别打高一级**（修正）：维基生物表显示高一级血量 ×3.6~46（神话→究极 ×46），经验只多约 ×4~9 —— 秒不了的高一级绝对不划算，只打主力同级
- **蹭掉落（可选）**：打不动的 M/U 怪在附近时，上去打 2.5 秒混伤害（>1% 即够）拿掉落然后撤退
- **回血阈值按花瓣种类**：玫瑰20%/大丽花30%/丝兰20%/海星40%（v1.3.0 启动设置选种类自动定线），血量低时自动切回血花瓣+防御+往怪少处跑（维基攻略建议提前切，防秒杀）
- **召唤流适合挂机**：蚂蚁蛋/甲虫蛋/树枝+防蠕虫的poo，配插件自动巡逻很稳（挂机首选）
- **沙漠入口区**：绿到蓝怪密集，效率约为花园 10 倍，巡逻点画那里刷怪最快
- **避开飞行物**：黄蜂/胡蜂导弹、蝎子螫针（命中持续掉血）、花粉、海胆导弹都会自动躲

## 👾 怪物图鉴速查（依据中文维基生物属性表）
- **必避（会发射远程弹，插件自动闪避）**：黄蜂/胡蜂（蜂针，史诗+会预判）、蝎子（螯针+剧毒持续掉血）、熊蜂（沿途花粉）、扇贝（珍珠弹）、蒲公英（受伤发射一圈）、螳螂（3连发+降甲）
- **危险近战**：蜘蛛（剧毒+传奇以上留网）、水蛭（吸血+全图最快）、甲虫（直线冲刺→绕圈打，用攻击模式2px别贴脸）、蟑螂（受伤高速冲撞）、沙尘暴（超级会吸人）、仙人掌/铀桶（碰就受伤）
- **优先刷（血薄经验好）**：泡泡5血、幼蚁10血、瓢虫10血、兵蚁10血、蜈蚣10血（打头变敌对）、苍蝇10血（但90%闪避，带闪电/电池才打得中）
- **别浪费时间**：岩石/仙人掌（经验=1）、蜜蜂50血1经验（S形会蜇）、正方形（所有稀有度经验都是1）
- **特殊机制**：海星50%血会逃跑回血（要秒杀）、蚁穴打它会引蚂蚁群（绕开）、挖掘者=友方别打、训练假人无敌
- **配装提示**：下水道/蚂蚁地狱带闪电（打苍蝇、水蛭共享血量）；打甲虫用攻击模式；被水蛭追时回血花瓣保命

## 📖 全量研究 →《研究手册.md》（v2.0 硬核完整版，2026-09-27）

> 深度研究全部整理进仓库里的 `研究手册.md`（12 章）：
> **稀有度倍率体系 / 花瓣全图鉴 / 怪物掉落全表 / 天赋树全数值 / 合成与升级 / 地图结构与捷径 / Boss 机制 / NPC与商店 / 打怪策略 / 流派配装 / 操作技巧 / 版本史与封禁政策**
> 📖 在线阅读：https://github.com/florrplayer/florr-auto-plugin/blob/main/研究手册.md

**一句话速查：**
- **天赋（挂机）**：Loadout 满 10 槽 → Reload 到 Mythic(−58%) → Health 到 Epic → Medic 到 Legendary → Magnetism；洗点免费无限
- **回血选型**：玫瑰=爆发救急最强 / 丝兰=防御回血(与插件联动) / 海星=75%被动 / 大丽花=稳定 / 叶子淘汰
- **Boss**：Super 是 Ultra 随机替换生成(非定时刷)；75 级前别蹲(只掉究极档)；蹭 1% 参与奖最划算
- **合成**：5 合 1 成功率 64%→0.1% 无保底；只赌玻璃；Eternal(0.01%)/Unique 别碰
- **地图**：沙漠入口区效率≈花园 10 倍；蚁狱密道=常规→左→机密→左→绝密；Spiral/Box 是 Super 集中区
- **封禁**：官方 2022-08-29 起封任何脚本(永久+清空进度)；本插件纯截屏方案不动浏览器 DOM

## Usage（源码版）

```bat
py -3.12 main.py desert    :: desert map (anthell / ocean / garden / jungle / sewers / hel / factory / crystal_room / training_grounds)
py -3.12 main.py anthell
```

Run with the florr window visible (minimize the cmd window so it does not cover the minimap). When the script starts, the current map opens automatically for patrol-point selection: left-click to add points, right-click to undo, and press Enter to confirm.

---

Time to upload some of my useful codes.

The whole codes stand on CLIENT-SIDE.

This project is **welcomed** to be used in any other florr.io projects.

## Features

- Lazy Theta\* pathing with updated 1.20 maps (Ant Hell / Desert / Ocean / Garden / Jungle / Sewers / Hel / Factory / Crystal Room / Training Grounds, shortcuts walkable)
- Patrol mode: cycle through user-defined waypoints
- Smart combat (quiz-style setup dialog): auto-chase rank you can oneshot, avoid higher ranks toward fewest-mob direction, ignore lower ranks
- Mythic (cyan) hunt, Ultra (pink) avoidance with human-like care (early warn margin, stop-attack when danger near, kiss-slow probe)
- Projectile dodge: wasp/hornet missiles, scorpion stingers, bumblebee pollen, dandelion, urchin missiles (universal frame-diff detection, up to 24px including Mythic oversize)
- Low-HP survival: HP<10% swaps configured heal petals (rose/leaf, multi-slot) to main slot + defense + flee, swaps back at 35%
- Live map window: red path overlay, green player, blue patrol waypoints, yellow current goal (0.3s refresh)
- Anti-AFK: random pauses + periodic petal slot switching
- Auto-reconnect: keyboard-only (Enter) respawn and start from main menu
- Auto-open browser: launches Edge at florr.io if no window found
- Dynamic resolution support: works at 4096x2160 (4K) / maximized window / any window size, no manual setup needed (auto-calibrates screen center, minimap position and canvas offset)
- Keyboard (WASD) movement via PostMessage

## The Lazy Theta Star

After I used `a*` pathing for a few months, I found this method caused a lot of time wasting on collision with florr's walls, I quickly turned to use `lazyθ*`. And here's the differences (Green for lazy_theta_star and Red for a_star)

![](https://raw.githubusercontent.com/florrplayer/florr-auto-plugin/main/compare.jpg)

## Maps

To decide on the positions and areas, I've already prepared `map_select.py` and `area_select.py` for you.

> \> python3 map_select.py # And you click anywhere you want on the map
>
> Map position: (53, 144)
> Map position: (55, 109)

> \> python3 area_select.py # And you first click on the left_top bound, next click on the right_bottom bound.
>
> Area added: [(6, 5), (40, 44)]
> Area added: [(1, 43), (27, 87)]
> Final areas: [[(6, 5), (40, 44)], [(1, 43), (27, 87)]]

## Implements

The plugin auto-detects the window size (including 4096x2160 4K and maximized windows), so no resolution setup is needed. Just keep the florr.io tab visible (not covered by other windows) and run `main.py`.

Go run `main.py`

```python
if __name__ == "__main__":
    apply_map("<map>")
    location = <location> # the location decided in `map_select.py`
    dedicated_area = [(0, 0), (200, 200)]  
    # optional, if the player has moved into the area and got stuck, the code will end. Otherwise it will try to callibrate until reaching the final location
    while True:
        if lazy_theta_pathing(location, dedicated_area):
            break
    print("Pathing Done")
```

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