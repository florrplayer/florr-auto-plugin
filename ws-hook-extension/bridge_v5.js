// ===== v5: 玩家实体坐标 + camera 对比 (用现有 l.HEAPU8) =====
(function() {
  if (window.__v5) return;
  window.__v5 = true;
  const heap = l.HEAPU8;
  const dv = new DataView(heap.buffer);
  const CAM_X = 10835792, CAM_Y = 10835800;

  function scan() {
    const out = [];
    for (let i = 16000000; i < 22000000; i += 8) {
      try {
        const x = dv.getFloat64(i, true);
        if (isNaN(x) || x < 1000 || x > 64000) continue;
        const y = dv.getFloat64(i + 8, true);
        if (isNaN(y) || y < 1000 || y > 64000) continue;
        const hp = dv.getFloat32(i + 36, true);
        if (!(hp >= 2 && hp <= 50000)) continue;
        const t = dv.getUint32(i + 92, true);
        if (!(t >= 1 && t <= 83)) continue;
        out.push({ x: +x.toFixed(1), y: +y.toFixed(1), hp: +hp.toFixed(0), t });
      } catch(e) {}
    }
    return out;
  }

  function post() {
    try {
      const ents = scan();
      const players = ents.filter(e => e.t === 1);
      const cam = { x: dv.getFloat64(CAM_X, true), y: dv.getFloat64(CAM_Y, true) };
      const payload = {
        t: Date.now(),
        px: +cam.x.toFixed(1), py: +cam.y.toFixed(1),
        pEnts: players.slice(0, 20).map(p => ({x:p.x, y:p.y, hp:p.hp, i:p.i})),
        mobs: ents
      };
      fetch('http://127.0.0.1:18899/', {
        method: 'POST', mode: 'no-cors',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      }).catch(() => {});
    } catch(e) { console.log('v5 err', e); }
  }

  window.__v5scan = scan;
  window.__v5post = post;
  post();
  setInterval(post, 200);
  console.log('v5 ok, players:', scan().filter(e=>e.t===1).length, 'camera:', dv.getFloat64(CAM_X,true).toFixed(0), dv.getFloat64(CAM_Y,true).toFixed(0));
})();
