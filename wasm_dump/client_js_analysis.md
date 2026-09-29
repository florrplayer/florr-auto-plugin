# client.js 逆向分析结果

## WebSocket 协议
- URL: `wss://25jp.s.m28n.net/`
- 库: MultiStream<WebSocket> (多路复用)
- binaryType: arraybuffer
- onopen: 发送 [2,0,0] 握手
- onclose: 发送 [4,0,0]
- onmessage: 收到 Uint8Array → 传给 wasm Z.s... 处理
- 断线原因: Idle(超时), KTooManyConnections(连接过多)

## wasm 导出函数(从client.js桥接层发现)
- `_Util_GenerateMobImage()` - 生成怪物图片
- `_Util_GetMobs()` - 获取所有怪物数据!
- `_webRTCProxyMessage()` - WebRTC代理

## 服务器
- 4401469: WebSocket连接
- 4402222: 关闭连接
- API: api.n.m28.io/endpoint/, api.n.m28.io/server/

## 认证
- Google/Discord/Apple OAuth
- Xsolla支付
- QQ群: qm.qq.com/q/5dMiUwLocg
- Discord: discord.gg/TRMtDSE

## 数据加载
- wasm 加载时 fetch 额外数据文件
- `Loading data file` 日志
- Sprite: blob: URL 动态生成 SVG

## 结论
游戏逻辑全在 wasm 里(9.2MB), client.js 只是 Emscripten 桥接层。
要拿怪物HP/伤害需要在浏览器里调用 wasm 导出函数,但全局Module名被混淆。
