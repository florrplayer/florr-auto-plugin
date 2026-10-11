# 插件修改清单（给 VSCode AI 按顺序执行）

> 先读 `data/game_data.json`（唯一数据源）和 `stolen/INDEX.md`（参考源码索引）。
> 每完成一个任务跑一次 `py -3.12 main.py` 冒烟测试，别一起全改。
> 原则：改行为不改架构；数据从 game_data.json 读，不硬编码。

---

## 任务 1：怪物动态 AI 预判（收益最高）
- **改**：`mob_ai.py`
- **参考**：`stolen/gardn_server/Process/Ai.cc`（怪物 AI 状态机源码）
- **加**：
  - `LOSE_RANGE_MULT = 1.5` —— 离目标超过 1.5×发现半径就丢目标（脱战判断）
  - `PATROL_CYCLE_SEC = 2.5` —— 巡逻移动走 2.5 秒后随机转向（预判走位）
  - `HOMING_RADIUS = 300` —— 离出生点 >300px 怪会归巢（安全区判断）
- **接入**：
  - `flee_planner.py` 用「超过 1.5×半径」判断何时停止逃跑（不用瞎跑）
  - `combat.py` 选目标时避开「即将转向」的怪，别站它正前方
- **验收**：`py -3.12 -c "import mob_ai; print(mob_ai.is_detached(400, 255))"` → True

## 任务 2：每怪行为表接入
- **改**：`mob_db.py` / `mob_table.py`
- **参考**：`stolen/misc_data/mob_datasheet.csv`（54 怪：被动行为/攻击触发/攻击行为/防御行为/Ultra行为）
- **加**：每怪 `behavior` 字段：`{passive, aggro_trigger, aggro_behavior, defensive_behavior, ultra_behavior}`
- **接入**：`combat_strategy.classify_action` 里 Ultra 档结合行为表决定 AVOID/CAUTIOUS
- **数据**：CSV 已在 `data/game_data.json` 的 mobs 里（behavior 字段），直接读

## 任务 3：game_data.json 加载
- **改**：`mob_db.py` / `game_data.py` / `game_db.py`
- **目标**：启动时读 `data/game_data.json`，与现有硬编码**合并**（不冲突时用 JSON，冲突时硬编码优先保稳）
- **验收**：`py -3.12 -c "import mob_db; print(len(mob_db.all_mobs()))"` 正常且 ≥73

## 任务 4：血 <10% 切回血花瓣（保命）
- **改**：`combat.py` / `memory_battle.py`（血量来源）
- **参考**：`stolen/ai_refs/auto_farm/loadout_swap.py`（换卡逻辑）
- **逻辑**：
  1. HP <10% → 切回血花瓣（Rose/Yucca/Starfish，从 `game_data.json` petals 查，别猜颜色）
  2. 按右键防御（防御中 Yucca 才回血）
  3. 原路撤退（已有撤退轨迹）
  4. HP >70% 切回原花瓣
- **副槽**：从内存模式读（`memory_reader.py`）或截图识别花瓣槽数量

## 任务 5：攻击距离 1~2px
- **改**：`combat.py`
- **逻辑**：攻击中保持距离 1~2px（地图像素），**不贴脸 0.5px**；只在持续攻击状态生效
- 血 <10% 的跑路逻辑不受影响

## 任务 6：区域随机游走
- **改**：`main.py`（巡逻循环）/ `area_select.py`
- **逻辑**：区域内随机取点走，走到再取，**不要固定 4 巡逻点**
- **区域边界**：参考 `stolen/tiled_maps/*.tmj` 或 `map_db.py` 已有区域数据

## 任务 7：避飞弹
- **改**：`combat.py` / `flee_planner.py`
- **参考**：`projectile_data.py`（已有投射物数据）+ `stolen/gardn_server/Process/Ai.cc`
- **逻辑**：检测到黄蜂导弹/蝎子螯针 → 垂直弹道方向闪避，不硬吃

## 任务 8：HumanCursor 人类光标
- **改**：`movement.py`（鼠标模式分支）
- **参考**：`stolen/ai_refs/helper/HumanCursor.py`（贝塞尔曲线+加减速，反检测）
- **逻辑**：鼠标模式移动用贝塞尔曲线+随机加减速，不直线瞬移；键盘模式（默认）不需要

---

## 执行顺序
1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

## 别做
- ❌ 不打包 1061 张 PNG 进 exe（只打包用到的识别模板）
- ❌ 不改网络协议层（bridge 已稳定）
- ❌ 不硬编码怪名/血量（一律读 game_data.json）
- ❌ 不加无意义延迟拖慢刷怪效率
- ❌ 不擅自升版本号
