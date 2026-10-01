// bridge_v10.js — 精确玩家实体扫描 (v10)
// 用法: 粘贴到 florr Console 一次。每250ms POST 到 http://127.0.0.1:18899/
// 改进点:
//  1. 扫描实体池步长8, 跨字段校验(x/y/hp/type)
//  2. 对每个实体在 ±96 字节内搜索可读名字字符串(内嵌名字 or 邻近名字标签)
//  3. 输出带名字的玩家候选, 便于确认哪个是本人
(function () {
  function getHeap() {
    try { return Module.HEAPU8; } catch (e) {}
    try { return window.Module.HEAPU8; } catch (e) {}
    return null;
  }
  function getDataView() {
    try { return Module.HEAPU8.buffer; } catch (e) {}
    try { return window.Module.HEAPU8.buffer; } catch (e) {}
    return null;
  }
  const h = getHeap();
  const buf = getDataView();
  if (!h || !buf) { console.log('v10: heap unavailable'); return; }
  const dv = new DataView(buf);

  const LO = 16000000, HI = 22000000;
  const RE = /^[a-zA-Z0-9_\-\[\]]{3,16}$/;

  function readName(addr, maxLen) {
    // 从 addr 读 ASCII 字符串(最长 maxLen), 返回 {name, addr} 或 null
    if (addr < 0 || addr + maxLen > h.length) return null;
    const bytes = [];
    for (let i = 0; i < maxLen; i++) {
      const c = h[addr + i];
      if (c === 0) break;
      if (c < 32 || c > 126) return null;   // 非法字符 → 不是名字
      bytes.push(c);
    }
    if (bytes.length < 3) return null;
    const s = String.fromCharCode.apply(null, bytes);
    if (!RE.test(s)) return null;
    return { name: s, addr: addr };
  }

  function scan() {
    const out = [];
    for (let i = LO; i < HI; i += 8) {
      try {
        const x = dv.getFloat64(i, true);
        const y = dv.getFloat64(i + 8, true);
        const hp = dv.getFloat32(i + 36, true);
        const t = dv.getUint32(i + 92, true);
        if (!(x >= 1000 && x <= 64000)) continue;
        if (!(y >= 1000 && y <= 64000)) continue;
        if (!(hp >= 2 && hp <= 50000)) continue;
        if (!(t >= 1 && t <= 83)) continue;
        // 附近找名字 (实体内嵌 or 紧邻名字标签)
        let nm = null;
        for (let off = -96; off <= 96 && !nm; off += 4) {
          const p = i + off;
          if (p < 0 || p + 16 > h.length) continue;
          nm = readName(p, 16);
        }
        out.push({ i, x: +x.toFixed(1), y: +y.toFixed(1), hp: +hp.toFixed(0), t, name: nm ? nm.name : null });
      } catch (e) {}
    }
    return out;
  }

  function post() {
    try {
      const ents = scan();
      const payload = { t: Date.now(), ents: ents };
      fetch('http://127.0.0.1:18899/', { method: 'POST', mode: 'no-cors',
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }).catch(() => {});
    } catch (e) { console.log('v10 err', e); }
  }

  window.__v10scan = scan;
  window.__v10post = post;
  post();
  setInterval(post, 250);
  const r = scan();
  const named = r.filter(e => e.name);
  console.log('v10 ok ents=' + r.length + ' named=' + named.length + ' players=' + r.filter(e => e.t === 1).length);
  console.log('v10 named samples:', named.slice(0, 15));
})();
