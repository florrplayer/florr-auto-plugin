// bridge.js - 注入到florr.io页面,定时读wasm游戏数据发给Python
(function() {
  const PYTHON_PORT = 18899;
  let lastSend = 0;

  function readGameState() {
    try {
      if (typeof l === 'undefined' || !l.HEAPU8) return null;
      const p = l._Util_GetMobs();
      let s = '';
      for (let i = p; l.HEAPU8[i] != 0 && i < p + 5000; i++) {
        s += String.fromCharCode(l.HEAPU8[i]);
      }
      return {
        time: Date.now(),
        mobData: s.substring(0, 500),  // 只发前500字符(够了)
      };
    } catch(e) { return null; }
  }

  function sendToPython(data) {
    if (!data) return;
    fetch(`http://127.0.0.1:${PYTHON_PORT}/game`, {
      method: 'POST',
      mode: 'no-cors',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    }).catch(() => {});
  }

  // 每2秒读一次
  setInterval(() => {
    const now = Date.now();
    if (now - lastSend > 2000) {
      lastSend = now;
      sendToPython(readGameState());
    }
  }, 2000);

  console.log('[桥接] 已连接,每2秒同步游戏数据');
})();
