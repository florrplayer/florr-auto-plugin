# florr.io WebSocket recv 消息逆向分析报告

> 分析对象：`recv_capture.json`(50) + `recv_late.json`(20) + `ws_state_snapshots.json`(100) = **共 170 条 recv 字节帧**
> 分析脚本：`ws_protocol_analysis.py`（及同目录 `ws_analysis2~6.py`、`ws_final_stats.py` 为中间过程）
> 结论先行：**线上 recv 字节是高熵加密/混淆流，无法离线还原出坐标/HP/行为状态；行为状态字段"未能还原"。**

---

## 0. 外层结构确认

- `recv_capture.json` / `recv_late.json`：`[{"t":毫秒时间戳, "d":[字节...]}]`，每条 = 一次 `onmessage` 收到的 Uint8Array。
- `ws_state_snapshots.json`：外层是长度 100 的数组，**每个元素本身就是一条消息的字节列表**（不是"一批消息"），即 100 条独立 recv 帧。
- 三者合并后共 170 条帧。

---

## 1. 消息长度分布（直方图）

| 长度(B) | 条数 | 推断 |
|---:|---:|---|
| 1 | 19 | 心跳/ACK（内容恒为 `[0]`） |
| 10 | 1 | 短控制帧 |
| 37 | 27 | 小更新帧（3 条 ~12B 记录） |
| 46 | 2 | 短更新帧 |
| 502–591 | ~90 | **主流实体状态更新帧** |
| 1376 | 1 | 全量快照帧（开局/切图后） |

分桶：`1–8B:19`，`9–32B:1`，`33–64B:29`，`65–512B:7`，`513–1024B:113`，`1025–2048B:1`。

**典型长度簇**：
- **1B 控制帧**：`[0]` ×19，对应 WebSocket 心跳/链路保活。
- **37B 增量帧**：固定长度，约 30ms 一条（时间戳间隔 29–31ms），与 send 帧同频。
- **~520–560B 实体更新帧**：长度随场上怪物数浮动（502–591），是主力帧。
- **1376B 全量帧**：仅 1 条（在 capture 早期，byte0=0x16），对应"一次性下发所有实体"。

> 注意：旧笔记里"recv 约 5KB 全地图快照"的估计偏大，实测最大帧 1376B，主流帧 ~520B。

---

## 2. opcode / 首字节分类

byte0 取值高度集中（不是 send 帧那种 30–93 连续区间）：

| byte0 | 十进制 | 条数 | 对应长度 | 猜测 |
|---:|---:|---:|---|---|
| 0x00 | 0 | 19 | 恒 1B | 心跳/ACK |
| 0x16 | 22 | 4 | 518–1376 | 全量/特殊通道帧 |
| 0x1D | 29 | 1 | 10B | 控制帧 |
| 0x30 | 48 | 5 | 507–550 | 实体更新通道 C |
| 0x3B | 59 | 45 | 37 / 521 / 540… | 实体更新通道 A |
| 0x42 | 66 | 3 | 538–562 | 实体更新通道（少量） |
| 0x49 | 73 | 46 | 37 / 518 / 521… | 实体更新通道 B |
| 0x5C | 92 | 47 | 37 / 521 / 540… | 实体更新通道 D |

**关键观察**：37B 小更新帧的 byte0 严格按 `73→92→59→73→92→59…` 循环。这与 `client_js_analysis.md` 里"MultiStream 7 连接复用"吻合——byte0 更像 **MultiStream 逻辑通道号/分片标记**，而不是游戏语义 opcode。游戏真正的消息类型在负载内部（已加密，见 §3）。

> 结论：**无法仅凭 byte0 判断"这一帧是怪物追击还是攻击"**；byte0 只区分通道/分片。

---

## 3. 核心发现：负载是高熵加密流，无法离线反序列化

这是本次分析最重要的结论，证据链如下：

### 3.1 熵接近满值
- 121 条 >400B 大帧，**香农熵均值 6.97 bit/byte**（min 6.54 / max 7.49）。
- 256 种字节值出现了 247 种，最高频字节仅 32 次/1376B（接近均匀分布）。
- 对比：明文 JSON 约 5.5 bit，未压缩二进制结构约 4–6 bit；**7.0 bit 已是加密/压缩水平**（真随机=8.0）。

### 3.2 跨帧 XOR = 随机（排除静态 XOR）
取两条 byte0 相同、相隔 123ms 的大帧逐字节异或：
- 结果中 `0x00` 占比 **0.4%**，与纯随机（1/256≈0.4%）完全一致。
- 若负载是明文，123ms 内同一批怪物的 ID/类型/未动坐标应大量不变 → XOR 应出现远多于 0.4% 的 `0x00`。实测没有。
- → **每帧密钥流不同**，不是固定密钥 XOR，而是流密码或逐帧密钥。

### 3.3 无标准压缩
- 对 1376B 全量帧尝试 `zlib`、raw deflate（跳过 0/1/2/3 字节头）：**全部失败**。
- brotli/lz4 环境未装，但即便如此，§3.2 的跨帧随机性已说明不是静态字典压缩。

### 3.4 单帧内的周期结构（仅能看到"形状"，看不到"值"）
- 对单条 1376B 帧做重合指数（IC）：周期 P=48 及其约数（6/12/24）IC 显著升高（0.024 vs 随机 0.004）。
- 把所有大帧**拼接**后再测，IC 立刻跌回随机（0.005）。
- 含义：**单帧内部明文是 ~48B 定长实体记录序列**，但每条记录用不同密钥流加密，跨帧无法对齐。
- 37B 小帧同理：`1B 头 + 3×12B 记录`，两帧 XOR 后呈现 12B 周期（说明 3 条记录里有一个 4B 字段在两帧间不变，疑似地图/目标常量），但具体值仍被密钥流掩盖。

### 3.5 wasm 侧佐证
- `client.js` 是 Emscripten 桥接层，`onmessage` 把 Uint8Array 直接喂给 wasm，**JS 层无解密代码**。
- wasm 导入/导出函数名全部混淆（导入 `a.a…a.Zb`，导出 `Mf…Dg`），`_Util_GetMobs` 只是 client.js 桥接别名，真实 wasm 导出名已被 mangle。
- wasm 字符串里搜不到 `aes/rc4/chacha/xor/decrypt` 等明文凭据 → 加密例程是手写/内联的，静态无法快速定位。

---

## 4. 实体更新帧字段偏移表

**未能还原。**

原因：§3 证明负载是加密流，无法把字节直接按 `<d/<f` 解成坐标。曾尝试的对齐方式（均失败）：
- 对 1376B 帧按 8B 对齐扫 `f64`，统计"第 7 字节落在 0x3F–0x43（正浮点指数高位）"的数量——最优单字节 XOR 命中仅 22/171，无显著峰。
- 对 payload 各 8B 列位置做字节分布，全部平坦（无恒定高字节），与明文 f64 坐标应有的"高字节聚集"特征不符。

> 已知的内存结构 `X f64(+0)/Y f64(+8)/HP f32(+36)/type u32(+92)/radius f32(+120)` 是 **wasm 解密后、游戏逻辑堆里的对象布局**，不是线上字节布局。两者之间隔着一层我们没攻破的传输加密。

---

## 5. 行为状态字段（追击/巡逻/攻击）

**未能还原。**

- 无法解密负载 → 无法在实体记录里定位"状态字节/目标 ID/速度向量"。
- 37B 增量帧虽能看出是"每帧 3 条 12B 小记录"（疑似少量实体的位置/HP 增量），但字节被密钥流保护，无法判断哪几位对应"追击/攻击"。
- 即使解密成功，florr.io 怪物 AI 是否在协议里**显式下发状态机枚举值**也未知——更可能的是：服务器只下发位置+HP，"追击/攻击"是客户端 wasm 根据距离**本地推算**的（achievement 文案里有 "Move a little bit to proceed"、flower 自动跟随鼠标，说明移动预测在客户端）。若是后者，**协议里根本不存在"行为状态"字段**，只能由插件自己根据怪物位置相对玩家的变化方向推断。

---

## 6. Python 解码函数原型

```python
import struct, collections

def classify_recv(data: bytes) -> dict:
    """只做我们能确定的部分：分帧 + 通道分类。
    返回帧类型；payload 标记为 ENCRYPTED，不要尝试 struct.unpack。"""
    if not data:
        return {"type": "empty"}
    n = len(data)
    if n == 1 and data[0] == 0:
        return {"type": "heartbeat"}
    if n == 1376:                      # 实测唯一全量帧长度
        return {"type": "full_snapshot", "channel": data[0], "len": n,
                "payload": "ENCRYPTED"}
    if 502 <= n <= 591:
        return {"type": "mob_update_bulk", "channel": data[0], "len": n,
                "payload": "ENCRYPTED", "records_hint": "~48B/entity, count≈(n-1)/48"}
    if n == 37:
        return {"type": "mob_update_delta", "channel": data[0], "len": n,
                "payload": "ENCRYPTED", "records_hint": "3 records x 12B"}
    return {"type": "other", "channel": data[0], "len": n, "payload": "ENCRYPTED"}


# ============================================================
# 下面这段【离线永远跑不通】——仅在你已经 hook 到 wasm 解密后的
# 内存对象（而非线上字节）时才有意义。它对应已破译的内存布局：
#   +0  X f64
#   +8  Y f64
#   +36 HP f32
#   +92 type u32
#   +120 radius f32
# ============================================================
def parse_mob_from_wasm_mem(buf: bytes, off: int) -> dict:
    """buf 必须是 wasm 线性内存里从 mob 对象头开始截的字节。
    直接对线上 recv 字节调用本函数会得到垃圾值——线上字节是加密的。"""
    x, y = struct.unpack_from('<dd', buf, off + 0)
    hp   = struct.unpack_from('<f',  buf, off + 36)[0]
    mtype= struct.unpack_from('<I',  buf, off + 92)[0]
    radius=struct.unpack_from('<f',  buf, off + 120)[0]
    return {"x": x, "y": y, "hp": hp, "type": mtype, "radius": radius}


# 行为状态：协议里【未发现】显式枚举字段。
# 若一定要判断，只能在拿到解密后坐标的前提下，用相邻帧位移方向自算：
def infer_behavior(prev, cur, player_pos) -> str:
    dx, dy = cur["x"] - prev["x"], cur["y"] - prev["y"]
    dist_to_player = ((cur["x"]-player_pos[0])**2 + (cur["y"]-player_pos[1])**2) ** 0.5
    speed = (dx*dx + dy*dy) ** 0.5
    if speed < 0.5:                 return "idle/patrol"
    # 位移方向是否指向玩家？
    to_player = (player_pos[0]-cur["x"], player_pos[1]-cur["y"])
    moving_toward = (dx*to_player[0] + dy*to_player[1]) > 0
    return "chasing" if moving_toward else "moving"
```

---

## 7. 对插件的可行性结论（直读协议 vs 屏幕取色）

| 方案 | 可行性 | 说明 |
|---|---|---|
| **离线解码线上 recv 字节** | ❌ 不可行 | 负载高熵加密（§3），无密钥/未攻破 wasm 加密例程，无法还原坐标/HP/类型/行为。 |
| **Hook wasm 解密后内存 / 调 GetMobs** | ✅ 可行但成本高 | `onmessage`→wasm 后，数据会落到堆里的 mob 对象（即已知的 +0/+8/+36/+92/+120 布局）。需在浏览器里 hook `wasm` 内存或找到那个导出函数（导出名已混淆，要动态调试定位）。拿到的是**坐标+HP+类型+半径**。 |
| **从协议读"行为状态"（追击/巡逻/攻击）** | ⚠️ 大概率不存在 | 服务器很可能只下发位置/HP，行为是客户端本地算的。即使 hook 到内存，也得自己用位移方向推断（见 §6 `infer_behavior`）。 |
| **继续屏幕取色** | ✅ 最稳 | 当前 florr 是 canvas 渲染，屏幕取色能拿到怪物位置/血条，无需碰加密协议。缺点是拿不到精确 HP 数值和视野外怪物。 |

**最终建议**：
1. **短期**：维持屏幕取色做路径规划；它不依赖被加密的协议。
2. **中期（收益最大）**：放弃"解码线上字节"，改为**在页面里 hook wasm**——在 `onmessage` 把 Uint8Array 交给 wasm 之后、或每帧渲染前，直接读 wasm 线性内存里的 mob 数组（用 `_Util_GetMobs` 的真实地址，需 Chrome DevTools 动态断点定位）。这样能拿到精确 X/Y/HP/type/radius。
3. **行为状态**：别指望协议下发。拿到解密坐标后，用"相邻帧位移是否指向玩家 + 距离阈值"自行判定 chasing/patrol/idle。

---

## 附：本次用到的证据文件

- 长度/byte0 统计：`ws_protocol_analysis.py`、`ws_final_stats.py`
- 熵与 XOR 测试：`ws_analysis3.py`（XOR 周期）、`ws_analysis4.py`（重合指数）、`ws_analysis6.py`（跨帧密钥流复用测试）
- 解压测试：`ws_analysis5.py`
