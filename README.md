# florr-auto-pathing

## 📥 直接下载（小白版，双击即用，无需装 Python）

👉 **[点这里下载 florr-auto-v1.2.3-win64.zip](https://github.com/florrplayer/florr-auto-plugin/raw/main/releases/florr-auto-v1.2.3-win64.zip)**

下载后解压：用 Edge 打开 florr.io 进游戏 → 双击 `启动.bat` → 输入地图数字 → 回车。

---

## 🆕 中文功能简介（v1.2.3）

- **巡逻挂机**：在地图上鼠标点选巡逻点（左键加、右键撤销、回车确认），自动循环巡逻
- **智能战斗**：启动时问你"全程攻击 / 防御 / 不弄" + "能秒杀的怪等级"（问卷星风格弹窗，鼠标点选高亮）
  - = 秒杀等级 → 自动追着打（贴脸 0.5px，攻击模式 2px）
  - > 秒杀等级 → 避开（往怪最少的方向跑）
  - < 秒杀等级 → 不管
- **只打 M 怪（青）/避开 U 怪（粉）**：人性化小心走位（提前绕开、追击中停手、贴脸减速试探）
- **避开飞行物**：黄蜂/胡蜂导弹、蝎子螫针、大黄蜂花粉、蒲公英花瓣、海胆导弹等（通用帧差检测，含 Mythic 超大导弹）
- **低血量保命**：血量 <10% 时自动把回血花瓣（玫瑰/叶子/海星）切到主槽 + 防御 + 往怪少处跑，恢复到 35% 自动切回原配置；**自动扫描副槽回血花瓣并弹窗确认**（防颜色误检），支持多个回血槽
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
- **回血阈值 20%**：血量<20%自动切回血花瓣+防御+往怪少处跑（维基攻略建议提前切，防秒杀）
- **召唤流适合挂机**：蚂蚁蛋/甲虫蛋/树枝+防蠕虫的poo，配插件自动巡逻很稳（挂机首选）
- **沙漠入口区**：绿到蓝怪密集，效率约为花园 10 倍，巡逻点画那里刷怪最快
- **避开飞行物**：黄蜂/胡蜂导弹、蝎子螫针（命中持续掉血）、花粉、海胆导弹都会自动躲

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
