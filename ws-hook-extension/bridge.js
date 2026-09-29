// bridge.js - 注入florr.io, 直接读wasm内存解析怪物, 发给Python
(function() {
  const PYTHON_PORT = 18899;
  const SCAN_START = 12700000;
  const SCAN_END   = 12800000;
  let timer = null;

  function readEntities() {
    try {
      if (typeof l === 'undefined' || !l.HEAPU8) return null;
      const heap = l.HEAPU8;
      const dv = new DataView(heap.buffer);
      const ents = [];

      for (let i = SCAN_START; i < SCAN_END - 400; i += 8) {
        try {
          const x = dv.getFloat64(i, true);
          const y = dv.getFloat64(i + 8, true);
          if (x < 10000 || x > 50000 || y < 10000 || y > 60000) continue;

          const hp = dv.getFloat32(i + 36, true);
          if (hp < 1 || hp > 100000) continue;

          const typeId = dv.getUint32(i + 92, true);
          if (typeId > 10000) continue;

          // 过滤花瓣/装饰
          if (hp === 7 && Math.abs(x - y) < 100) continue;

          const r = dv.getFloat32(i + 120, true);
          ents.push({
            x: +x.toFixed(1),
            y: +y.toFixed(1),
            hp: +hp.toFixed(0),
            t: typeId,
            r: r > 0 ? +r.toFixed(1) : 5
          });
          i += 384; // 跳过下一个实体
        } catch(e) {}
      }

      // 玩家位置
      let px = null, py = null;
      try {
        px = dv.getFloat64(4958248 + 248, true);
        py = dv.getFloat64(4958248 + 256, true);
      } catch(e) {}

      return {
        t: Date.now(),
        player: px && px > 10000 ? {x: +px.toFixed(1), y: +py.toFixed(1)} : null,
        mobs: ents
      };
    } catch(e) { return null; }
  }

  function send(data) {
    if (!data) return;
    fetch('http://127.0.0.1:' + PYTHON_PORT, {
      method: 'POST',
      mode: 'no-cors',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    }).catch(() => {});
  }

  // 每200ms读一次 (5fps, 够战斗用)
  timer = setInterval(() => { send(readEntities()); }, 200);
  console.log('[桥接] 内存读取已启动, 每200ms同步怪物数据');
})();
