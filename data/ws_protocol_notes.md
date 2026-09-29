# florr.io WebSocket 协议逆向笔记
## 连接
- wss://25jp.s.m28n.net/ (MultiStream<WebSocket> 复用, 7个连接)
- 协议: 二进制 ArrayBuffer

## send 帧 (已逆向)
每帧 6 字节 uint8:
74,213,144,93,231,131
36,113,215,149,71,28
37,96,214,39,73,226
90,327,77,101,38,58
93,230,56,174,197,28
90,197,11,16,39,14
74,194,65,158,183,51
30,17,86,190,143,174
37,48,119,125,157,133
36,16,90,172,43,18

- byte0: opcode/channel (30-93)
- byte1-4: 移动坐标/方向数据
- byte5: 状态标志
- 移动时约 30-60fps 发送

## recv 帧 (未抓到)
- DevTools Network 面板只显示 send 6B, recv 被 MultiStream 分片
- WebSocket 实例在闭包中, window 直接属性 0 个
- 递归遍历 window 深度6会卡死浏览器
- 需在页面加载最早期 hook WebSocket 构造函数
- 已知: recv 约 5KB 全地图状态快照(怪物坐标/HP)

## Hook 代码 (需在页面加载时运行)
window.__recv=[];
const O=window.WebSocket;
function H(u,p){const w=new O(u,p);w.addEventListener('message',e=>{if(e.data instanceof ArrayBuffer)window.__recv.push(Array.from(new Uint8Array(e.data)))});return w}
H.prototype=O.prototype;window.WebSocket=H;
