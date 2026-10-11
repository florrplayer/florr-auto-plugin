# florr-auto-plugin 设计方案（给 VSCode AI）

> 你是插件开发者。读完本文件 + `data/game_data.json` 后，按下面的方案改代码。
> 原则：**只改行为，不改架构**；每改一处先看 `stolen/` 里的参考源码。

---

## 一、数据库怎么读

`data/game_data.json` 是唯一数据源，结构：

```json
{
  "mobs": { "bee": { "name":"Bee", "hp":35, "damage":50, "ai_type":"passive",
                     "aggro_range":100, "color_hex":"#ebe834",
                     "passive":"...", "aggro_trigger":"...", "aggro_behavior":"..." } },
  "petals": { "rose": { "name":"Rose", "damage":.., "hp":.., "color_hex":".." } },
  "ai_rules": { "detection_lose_multiplier":1.5, "idle_move_duration_ticks":2.5, ... },
  "damage_formula": { "final_damage":"base * damage_factor * crit * burn * entity_type * high_hp" },
  "maps": { "tiled_dir":"stolen/tiled_maps/", ... },
  "assets": { "petal_images_dir":"stolen/petal_images/", "yolo_models":[...] }
}
```

启动时 `mob_db.py` 加载它，提供查询：
- `get_mob(屏幕识别到的颜色/名字) -> {hp, damage, ai_type, aggro_range, behavior}`
- `is_passive(mob) / is_aggressive(mob)`
- `aggro_radius(mob)` —— 从 game_data 读，不再硬编码

---

## 二、怪物 AI 预判（核心升级）

参考：`stolen/gardn_server/Process/Ai.cc`

怪的行为规律（从源码挖出来的）：
1. **发现半径** `detection_radius`：进入这个半径怪才追你
2. **丢失阈值** 1.5×发现半径：离怪超过 1.5 倍半径，怪放弃追你
3. **巡逻节奏**：idle 每秒随机转一次方向，然后走 2.5 秒（抛物线加速）
4. **归巢**：离出生点 >300px 会往回走，<100px 停下来

**插件怎么用：**
- 看到一只 aggressive 怪，先查 `aggro_range`，站在它半径外 → 安全
- 被追时，往**远离它出生点**的方向跑，跑过 1.5×半径就脱战
- 不要在怪的 2.5 秒移动周期结束前站在它正前方（它会突然转向）

---

## 三、打怪策略升级

参考：`stolen/clone_refs/florrust/DATA_TABLES.md`（伤害公式）

1. **秒杀判断**：用 `damage_formula` 估算你这一花瓣能打多少血
   - 你花瓣伤害 > 怪 HP × 1.2 → 直接追
   - 你花瓣伤害 < 怪 HP × 0.5 → 绕开
2. **不撞上去**：攻击距离 1~2px 就停（一直按攻击时不需要贴脸）
3. **血 <10%**：立刻切回血花瓣（Rose/Yucca/Starfish，见 game_data.petals），按右键防御，原路撤退
4. **优先打**：正方形 / Shiny / 金叶虫 / 潜水兵蚁（特殊稀有，在 mobs 里查 region/special 字段）

---

## 四、避怪/避弹

参考：`stolen/ai_refs/auto_farm/flee_planner.py`

1. **碰撞箱**：用 `stolen/gardn_server/Process/Collision.cc` 的半径，别用视觉大小
2. **飞弹**：黄蜂导弹/蝎子螯针，检测到就往垂直于弹道的方向闪 1px
3. **不往墙角跑**：逃跑路径末端 50px 内有墙就换方向（参考 tiled_maps 的 tile 类型）
4. **被追时**：往怪少的方向跑（空间哈希，参考 `stolen/gardn_server/SpatialHash*.cc`）

---

## 五、识别升级

参考：`stolen/ai_refs/auto_farm/enemy_species.py`、`stolen/petal_images/`

1. **颜色识别 → 模板匹配**：截图怪/花瓣，和 `stolen/petal_images/{rarity}/` 里的 PNG 比像素
2. **怪名识别**：canvas 上有文字（怪名+稀有度标签），用 `stolen/ai_refs/auto_farm/canvas_decode.py` 的方法直接读字，比颜色准
3. **稀有度颜色**：青 #1fdbde（Mythic）/ 粉 #ff2b75（Ultra），命中就优先标记

---

## 六、反检测

参考：`stolen/ai_refs/helper/HumanCursor.py`

1. **人类光标**：移动鼠标用贝塞尔曲线 + 加减速，不要直线瞬移
2. **随机停顿**：每 3~7 秒停一下，像人看画面
3. **AFK 弹窗**：用 `stolen/models/afk-det.pt`（YOLO）检测圆点位置，`afk-seg.pt` 识别路径，自动拖动

---

## 七、地图/捷径

参考：`stolen/tiled_maps/*.tmj`、`stolen/ai_refs/auto_farm/map_routes.py`

1. **区域选择**：不再要玩家设巡逻点，按秒杀等级选区域（花园/沙漠/海洋/蚁狱）
2. **区域内随机走**：在区域边界内随机游走，不是固定 4 个点
3. **捷径**：读 map_routes.py 里的捷径坐标，直接穿

---

## 八、要改的文件清单

| 文件 | 改什么 |
|---|---|
| `mob_db.py` | 从 game_data.json 加载，提供 get_mob/aggro_radius/is_aggressive |
| `combat.py` | 用 damage_formula 判断秒杀距离，1~2px 停手，血<10% 切回血花瓣 |
| `flee.py` | 用 1.5×半径脱战逻辑 + 不撞墙 + 避飞弹 |
| `detect.py` | 颜色识别升级到模板匹配 + canvas 文字解码 |
| `cursor.py` | 加 HumanCursor 贝塞尔曲线移动 |
| `maps.py` | 区域随机游走 + 捷径 |

---

## 九、不要做的

- ❌ 不要把 stolen/ 里的 1061 张 PNG 全打进 exe（只打包用到的）
- ❌ 不要改网络协议层（bridge 已经稳定）
- ❌ 不要硬编码怪名/血量，全部从 game_data.json 读
- ❌ 不要为了"像人"加无意义延迟拖慢刷怪效率
