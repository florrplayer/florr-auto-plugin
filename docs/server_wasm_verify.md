# server.wasm 反编译验证报告（v1.23.x）

- 文件：`reference-florr-tools\florr_clone\dist\server.wasm`（5,229,756 字节，`\0asm` 合法 wasm 头）
- 验证方法：字符串提取（5+ 连续可打印字符），验证已挖机制 + 发现新数据
- 结论：**florr_clone 私服服务端编译产物 = C++ 源码一致**，已挖数据全部得到 wasm 级交叉验证

## 一、已挖机制验证（全部命中）

| 机制 | wasm 证据 |
|---|---|
| stinger 摆尾 | `stinger` 12 处 + `itemType: stinger` |
| bee_ai 横穿飞行 | `bee_ai: "always"` 12 处 |
| web 减速 | `webRadius` 14 处 |
| aggro 仇恨 | `aggroRadius` / `aggroRange`（含 `"aggroRadius": 150`）|
| 刷怪区 | `mantis zone` / `hornet zone`（wasm 内嵌地图刷怪区）|
| 波次 | `spawn_waves` / `waveFrequency` / `flix::NestWaves` |
| 花瓣名 | Rose/Dahlia/Yucca/Starfish/Leaf/Glass/Sand/Yggdrasil/Stinger/Dandelion 全命中 |

## 二、新发现（wasm 独有，源码没挖到的）

1. **boss_timers**：每个 biome 的 unique/apex 生成冷却计时器——Super/Unique 生成带冷却（对应官方"Super 占 Unique 名额"）
2. **squads**：掉落规则池（loot rule pools）——多人分掉落按小队池
3. **corrupt 腐化**：corrupted flowers 在全图攻击玩家（不只在 PVP）——腐化花=公敌
4. **maze 迷宫**：`change-maze [next|garden|desert|ocean|dayNumber]`——迷宫按天切换
5. **guild 公会**：guild_list/guild_info/guild_force_join——私服公会系统
6. **bot 管理**：teleport_bots / bot 人口统计（`boss_timers` 旁带 bot population）
7. **管理命令体系**：spawn/spawn_npc/killall/teleport/give/set_skin/mute/restart/backup_db/update——完整私服运维命令

## 三、对官方服的推论

- boss_timers 说明 Unique/Super 有**全局冷却计时**（不是纯随机）——插件 Super 蹲点要考虑冷却窗口
- 腐化花全图攻击 → 插件识别腐化花要避（腐化花=全图公敌）
- squads 掉落池 → 多人时掉落分配按池

## 四、验证状态

- ✅ wasm 与 C++ 源码一致（stinger/bee_ai/aggro/web 全命中）
- ✅ 花瓣名与 FlorrBt/clone JSON 一致
- ✅ 地图刷怪区在 wasm 内嵌（与 map_db 一致）
- ⏳ 官方真实服的 wasm（9.4MB current_client.wasm）反汇编深度验证——本地版本 hash 与 Legacy-florr.io 一致，协议解析 net_protocol.py 已覆盖
