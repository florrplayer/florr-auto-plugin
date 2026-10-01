# 怪物AI机制（源码级逆向）— gardn 官方早期开源版 Ai.cc

> 来源: reference-florr-tools/gardn/Server/Process/Ai.cc（florr.io 官方早期开源 C++ 版，机制=现版本）
> 价值: 服务端 AI 源码 = 每只怪的仇恨/追击/攻击/逃跑行为 100% 确定

## 一、AI 状态机（每只怪都有的状态）
| 状态 | 含义 |
|---|---|
| kIdle | 静止待机（每 1 秒随机换方向 → 进入 IdleMoving） |
| kIdleMoving | 漫游（0.5s 加速 → 2s 减速回 Idle，路径=抛物线加速-减速） |
| kReturning | 回归（召唤物超 SUMMON_RETREAT_RADIUS 时返回父级） |
| 行为态 | passive(被动) / neutral(中立) / aggro(攻击) |

## 二、仇恨核心规则
1. **记仇**：`tick_ai_behavior` 开头——无目标但有 last_damaged_by → **目标=最后打它的实体**（你打它没秒掉，它就追你）
2. **仇恨半径**：`detection_radius`（每怪不同）——`find_nearest_enemy(sim, ent, detection_radius + radius)` 找目标
3. **仇恨丢失**：`_focus_lose_clause` = **距离 > 1.5 × detection_radius → 丢仇**（风筝线=1.5倍检测半径）
4. **丢失后**：攻击态怪重新找最近敌人（继续攻击最近的）；中立/被动转待机

## 三、每怪行为表（tick_ai_behavior 的 switch）
| 怪 | 行为 | 追击速度(×玩家加速度) | 特殊 |
|---|---|---|---|
| BabyAnt / Ladybug / MassiveLadybug | **被动** | 不追 | 纯漫游 |
| Bee | 被动+漂移 | — | sin摆动轨迹, 1.5倍速, 每1.5s变速一次(×0.5) |
| Centipede | 被动 | — | 慢速0.1倍游走, 左右缓转 |
| EvilCentipede | **攻击** | 0.95 | 直接追 |
| DesertCentipede | 中立 | **1.33** | 漫游也保持1.33倍速(沙漠蜈蚣很快!) |
| WorkerAnt / DarkLadybug / ShinyLadybug | 中立 | 0.975 | 被打才追 |
| SoldierAnt / Beetle / MassiveBeetle | **攻击** | 0.95 | 出生即攻击 |
| Scorpion | **攻击** | **1.20** | 追得比玩家默认快 |
| Spider | **攻击** | **1.20** | **每秒吐网(alloc_web 25px半径)** |
| QueenAnt | **攻击** | 0.95 | **每2秒在身后召唤SoldierAnt(10秒消失)** |
| Hornet | 攻击 | 0.975 | **>300px追 / <300px停住发射导弹(1.5秒一发, 伤害10, 3秒消失, 发射后坐力2.5)** |
| Digger(挖掘者) | 攻击 | 0.95 | **血>10% 攻击冲脸 / 血<10% 切防御+反向逃跑!(怪也会回血跑)** |
| Boulder / Rock / Cactus / **Square** | **完全不动** | — | 静态障碍/正方形=纯静态 |
| Sandstorm | 特殊 | — | 随机漂移+跟随父级(0.75混合), 每帧随机转向 |

## 四、其他机制
- **召唤物**：超 SUMMON_RETREAT_RADIUS 自动回归父级；父死子亡(kDieOnParentDeath)
- **墙回避**：无目标时撞墙弹回（只反射角度，不转向）
- **被Culled**：视野外直接清目标+待机（同屏外的怪不打人）
- **玩家加速度基准**：PLAYER_ACCELERATION（怪速=玩家速×系数）→ 玩家默认 0.975 系数的怪基本追不上你（可风筝）；1.20 的蝎子/蜘蛛追得上——**不能风筝，要么秒要么跑出1.5×检测半径**

## 五、战斗应用（写进插件）
1. **风筝线**：离怪 1.5×detection_radius 内会被一直追；想甩掉必须出这个圈
2. **打怪记得要秒**：打不死的怪会记仇追你（last_damaged_by）——攻击态怪尤其
3. **蝎子/蜘蛛**：速度 1.20 追得上玩家 → 别边走边打，站桩输出或秒杀
4. **黄蜂**：300px 内会停下射导弹 → 要么贴身输出（导弹贴脸难中），要么保持>300px 风筝
5. **女王蚁**：会无限召唤兵蚁 → 速战速决，别拖
6. **蜘蛛**：每秒放网 → 网=减速/束缚，优先秒
7. **挖掘者**：半血以下会防御逃跑（和海星一样）→ 半血前秒掉
8. **正方形完全不动** → 永远可以安全输出（插件已 5 倍优先）
9. **QueenAnt 召唤的兵蚁 10 秒消失** → 别恋战

## 六、配套资产（本轮新偷）
- gardn/Shared/StaticData.cc：**PETAL_DATA 全表**（每花瓣 health/damage/radius/reload/count/rarity/attributes）+ MOB_DATA（hp/radius/score/detection_radius）——官方数值，可交叉验证 mob_db
- Legacy-florr.io：老版 client.wasm(1.8MB) + **sp_server.wasm(466KB 单机服务端)** + 3.3MB HAR 抓包（含协议样本）
- FlorrTranslate-zh_CN：全量汉化翻译表（油猴版43KB + console版38KB）
- Florr_Maze_MiniMap_Mod：迷宫(C8)小地图 mod（mitmproxy 拦截+注入方案）
- florr-maps-browser(53文件)/florr-io-maps(267文件)：地图查看器（地图/捷径数据）
- hidehidev7/florrData + wiki：日文维基数据（32文件）
- florr_clone(1168文件)：完整克隆（含资源/代码）
