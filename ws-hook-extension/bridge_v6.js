// ===== v6: 步长392扫实体数组 (实体结构392字节: +0x +8y +36hp +92type +120r) =====
(function() {
  if (window.__v6) return;
  window.__v6 = true;
  const heap = l.HEAPU8;
  const dv = new DataView(heap.buffer);
  const CAM_X = 10835792, CAM_Y = 10835800;

  function scan(start, end, step) {
    const out = [];
    for (let i = start; i < end - 392; i += step) {
      try {
        const x = dv.getFloat64(i, true);
        if (isNaN(x) || x < 1000 || x > 64000) continue;
        const y = dv.getFloat64(i + 8, true);
        if (isNaN(y) || y < 1000 || y > 64000) continue;
        const hp = dv.getFloat32(i + 36, true);
        if (!(hp >= 2 && hp <= 50000)) continue;
        const t = dv.getUint32(i + 92, true);
        if (!(t >= 1 && t <= 83)) continue;
        out.push({ i, x: +x.toFixed(1), y: +y.toFixed(1), hp: +hp.toFixed(0), t });
      } catch(e) {}
    }
    return out;
  }

  function post() {
    try {
      const ents = scan(10000000, 24000000, 392);
      const players = ents.filter(e => e.t === 1);
      const cam = { x: dv.getFloat64(CAM_X, true), y: dv.getFloat64(CAM_Y, true) };
      const payload = {
        t: Date.now(),
        px: +cam.x.toFixed(1), py: +cam.y.toFixed(1),
        pEnts: players.slice(0, 30).map(p => ({x:p.x, y:p.y, hp:p.hp, i:p.i})),
        mobs: ents
      };
      fetch('http://127.0.0.1:18899/', {
        method: 'POST', mode: 'no-cors',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      }).catch(() => {});
    } catch(e) { console.log('v6 err', e); }
  }

  window.__v6scan = scan;
  window.__v6post = post;
  post();
  setInterval(post, 200);
  console.log('v6 ok, ents:', scan(10000000,24000000,392).length, 'players:', scan(10000000,24000000,392).filter(e=>e.t===1).length);
})();
