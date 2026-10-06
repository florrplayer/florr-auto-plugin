# wasm 9.4MB 最新版侦察报告 (2026-10-06)

来源: C:\Users\intel\Downloads\florr_client.wasm (9410540 bytes, 2026版客户端)
方法: 字符串表 + 上下文提取 (完整反汇编见 wasm_radii/disasm 系列)

## 1. AFK 检测机制 (重要更新)

- 两种验证类型 (UI/AFKCheck):
  - Drag: "Drag the circle until the end" / 中文"将圆球拖动到终点" —— 已破解(afk_solver)
  - **Flap: "Flap until the end" / 中文"操控圆球飞行到终点"** —— **新类型, v1.29.3 已加破解** (键盘WASD飞行)
- 聊天命令: `Chat/Command/afk-check/Args=[target]` "Runs manual AFK check" (开发者命令)
- Changelog 确认:
  - "Added an AFK timer in public squads." (公开小队新增AFK计时器)
  - "Ant holes now have a timer so players can't afk inside." (蚁穴有挂机计时器)
- 触发 UI 键: UI/AFKCheck/Title=AFK Check (多语言: 中/英/日/葡/俄/越)

## 2. 开发者命令全集 (58条, 玩家环境通常不可用, 机制参考)

help, guild, guild-create, guild-invite, guild-transfer-leader, guild-motd,
squad, squad-create, squad-invite, squad-leave, squad-find-public,
squad-public, squad-private, whisper, w, reply, r, local, map, global,
unblock, unblock-all, rot-speed, print-players, fake-achievements,
fill-chat, disable-save, reset-talents, one-of-everything, wipe, flush,
make-enemies, spawn-mob, warp, warp-everyone, kill, kill-everyone,
revive-everyone, kill-mobs, revive, set-loadout, set-loadout-all, levelup,
isolate, unisolate, change-name, dev-boss, afk-check, bot-finder,
wipe-achievements, reset-coin-delay, bring, goto, bring-everyone,
contagious-corruption, purge-contagious-corruption, calculate-next-shop,
lock-in-hel

注意: 玩家侧实际可用的只有 help/guild/squad/whisper/w/reply/r/local/map/global 等常规命令;
spawn-mob/warp/kill/dev-boss/afk-check 等为服务器开发者命令, 普通号触发会被忽略或封禁, 勿试。

## 3. 服务器基础设施

- API: https://api.n.m28.io/endpoint/ 和 https://api.n.m28.io/server/ (服务器发现)
- WebSocket: ws:// / wss:// (MultiStream<WebSocket>)
- 错误码: kServerError / kProtocolError / kServerFull
- OAuth: google / discord / appleid (https://florr.io/?oauth2=...)

## 4. 掉落机制

- ExtraDropChance (花瓣属性/天赋): "{0:perc}% 的几率从怪身上获得额外掉落"
  幸运草类花瓣提供此属性 —— 插件可提示玩家该属性影响实际掉落率
- Changelog: "Adjusted drop rates for ultra+ mobs" (ultra+ 掉落率已调整, 最新更新)
- 历史: "Increased craft chances for higher rarities" / "Reduced drop rate" 等

## 5. 其他

- 稀有度色板: 插件 RARITY_COLORS_BGR 与游戏一致 (8色)
- 地图: garden/desert/ocean/jungle/sewer/anthell/hel/pyramid/rift 全量
- 新花瓣: grapes(毒) / blueberries(闪电) 描述确认
