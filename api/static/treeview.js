/* TreeView: the passive tree on a canvas, animated by what the engine actually does.
   Data comes from /tree/data (engine/tree.py): nodes {id: [x, y, kind, name, stats, ascendancy]}, edges [a, b(, gx, gy, r)].
   No game art: our own shapes in the site's palette.

   const tv = TreeView(canvas, treeData, { reduceMotion })
   tv.setAlloc(ids)             show these passives as taken, no animation
   tv.step({chosen, path, considered, scanned})   one live search step: candidates flicker, the path draws in, the pick ignites
   tv.reveal(ids)               draw a finished path in, growing out from the class start
   tv.focus(ids) / tv.stop()
*/
(function () {
  const SIZE = { c: 70, A: 40, k: 52, j: 34, n: 36, a: 18, s: 20 };

  window.TreeView = function (canvas, data, opt = {}) {
    const cx = canvas.getContext("2d");
    const reduce = !!opt.reduceMotion;
    const nodes = data.nodes, edges = data.edges.filter(e => nodes[e[0]] && nodes[e[1]] && !nodes[e[0]][5] && !nodes[e[1]][5]);
    const byNode = new Map();
    for (const e of edges) {
      for (const k of [String(e[0]), String(e[1])]) (byNode.get(k) || byNode.set(k, []).get(k)).push(e);
    }
    let W = 1, H = 1, dpr = 1, alive = true, raf = 0;
    let alloc = new Set();
    const cam = { x: 0, y: 0, s: 0.03 }, target = { x: 0, y: 0, s: 0.03 };
    let flickers = [], flashes = [], drawing = [], sparks = [], queue = [];
    let lastStep = 0;

    let lastAim = null;   // what the camera was asked to frame, so a resize can frame it again
    function size() {
      const r = canvas.getBoundingClientRect(); dpr = Math.min(devicePixelRatio || 1, 2);
      W = Math.max(1, r.width); H = Math.max(1, r.height); canvas.width = W * dpr; canvas.height = H * dpr;
      if (lastAim) aim(lastAim.ids, lastAim.pad, true);
      kick();
    }
    const ro = new ResizeObserver(size); ro.observe(canvas);

    function bbox(ids) {
      const pts = [...ids].map(id => nodes[id]).filter(n => n && !n[5]);
      if (!pts.length) return data.bounds;
      return [Math.min(...pts.map(n => n[0])), Math.min(...pts.map(n => n[1])), Math.max(...pts.map(n => n[0])), Math.max(...pts.map(n => n[1]))];
    }
    function aim(ids, pad = 900, snap = false) {
      lastAim = { ids, pad };
      const b = bbox(ids);
      target.x = (b[0] + b[2]) / 2; target.y = (b[1] + b[3]) / 2;
      target.s = Math.min(W / (b[2] - b[0] + 2 * pad), H / (b[3] - b[1] + 2 * pad), 0.22);
      if (snap || reduce) Object.assign(cam, target);
      kick();
    }

    function edgePath(e, upto = 1) {
      const a = nodes[e[0]], b = nodes[e[1]];
      cx.beginPath();
      if (e.length > 2) {
        const [gx, gy, r] = [e[2], e[3], e[4]];
        const a1 = Math.atan2(a[1] - gy, a[0] - gx); let d = Math.atan2(b[1] - gy, b[0] - gx) - a1;
        while (d > Math.PI) d -= 2 * Math.PI; while (d < -Math.PI) d += 2 * Math.PI;
        cx.arc(gx, gy, r, a1, a1 + d * upto, d < 0);
      } else { cx.moveTo(a[0], a[1]); cx.lineTo(a[0] + (b[0] - a[0]) * upto, a[1] + (b[1] - a[1]) * upto); }
    }
    // An edge drawn from `from` toward the other end (so a new path grows outward).
    function orient(e, from) { return String(e[0]) === from ? e : [e[1], e[0], ...e.slice(2)]; }

    function frame(now) {
      raf = 0;
      if (!alive) return;
      const k = reduce ? 1 : 0.08;
      cam.x += (target.x - cam.x) * k; cam.y += (target.y - cam.y) * k; cam.s += (target.s - cam.s) * k;
      const moving = Math.abs(target.x - cam.x) * cam.s > 0.5 || Math.abs(target.s - cam.s) / cam.s > 0.004;

      cx.setTransform(dpr, 0, 0, dpr, 0, 0);
      cx.clearRect(0, 0, W, H);
      cx.setTransform(dpr * cam.s, 0, 0, dpr * cam.s, dpr * (W / 2 - cam.x * cam.s), dpr * (H / 2 - cam.y * cam.s));
      const px = 1 / cam.s, lw = Math.max(1.1 * px, 6);
      cx.lineCap = "round";
      // The whole tree, faint
      cx.strokeStyle = "#26221d"; cx.lineWidth = lw;
      for (const e of edges) { edgePath(e); cx.stroke(); }
      // Taken path: ember glow under brass
      const taken = edges.filter(e => alloc.has(String(e[0])) && alloc.has(String(e[1])) && !drawing.some(d => d.e === e));
      cx.strokeStyle = "rgba(232,115,58,.32)"; cx.lineWidth = lw * 3.4; for (const e of taken) { edgePath(e); cx.stroke(); }
      cx.strokeStyle = "#f0c97f"; cx.lineWidth = lw * 1.3; for (const e of taken) { edgePath(e); cx.stroke(); }
      // Path segments being drawn in right now
      drawing = drawing.filter(d => now - d.t0 < d.dur + 50);
      for (const d of drawing) {
        const t = Math.min(1, Math.max(0, (now - d.t0) / d.dur));
        if (t <= 0) continue;
        cx.strokeStyle = "rgba(255,170,90,.55)"; cx.lineWidth = lw * 4.5; edgePath(d.e, t); cx.stroke();
        cx.strokeStyle = "#fff1d6"; cx.lineWidth = lw * 1.5; edgePath(d.e, t); cx.stroke();
      }
      // Nodes
      for (const id in nodes) {
        const n = nodes[id]; if (n[5]) continue;
        const on = alloc.has(id), r = Math.max(SIZE[n[2]] || 20, 1.6 * px);
        cx.beginPath();
        if (n[2] === "j") cx.rect(n[0] - r, n[1] - r, 2 * r, 2 * r); else cx.arc(n[0], n[1], r, 0, 6.2832);
        cx.fillStyle = on ? "#d0a45a" : n[2] === "k" ? "#3a3027" : n[2] === "n" ? "#2c2722" : "#1e1b18";
        cx.fill();
        if (on || n[2] === "k" || n[2] === "n") { cx.lineWidth = Math.max(px, 6); cx.strokeStyle = on ? "#f0c97f" : "#4a4136"; cx.stroke(); }
      }
      // Candidates being weighed: ember rings that flicker and fade
      flickers = flickers.filter(f => now - f.t0 < f.life);
      for (const f of flickers) {
        const n = nodes[f.id]; if (!n) continue;
        const t = (now - f.t0) / f.life, a = (1 - t) * (0.55 + 0.45 * Math.sin(now / 45 + f.ph));
        cx.beginPath(); cx.arc(n[0], n[1], (SIZE[n[2]] || 20) + 18 + t * 40, 0, 6.2832);
        cx.lineWidth = Math.max(2 * px, 9); cx.strokeStyle = `rgba(232,115,58,${Math.max(0, a)})`; cx.stroke();
      }
      // The pick: a flash ring and a burst of sparks in world space
      flashes = flashes.filter(f => now - f.t0 < 900);
      for (const f of flashes) {
        const n = nodes[f.id]; if (!n) continue;
        const t = (now - f.t0) / 900;
        const g = cx.createRadialGradient(n[0], n[1], 0, n[0], n[1], 260 + t * 500);
        g.addColorStop(0, `rgba(255,214,150,${0.55 * (1 - t)})`); g.addColorStop(1, "rgba(255,214,150,0)");
        cx.fillStyle = g; cx.beginPath(); cx.arc(n[0], n[1], 260 + t * 500, 0, 6.2832); cx.fill();
        cx.beginPath(); cx.arc(n[0], n[1], 60 + t * 260, 0, 6.2832);
        cx.lineWidth = Math.max(2 * px, 14 * (1 - t)); cx.strokeStyle = `rgba(255,241,214,${1 - t})`; cx.stroke();
      }
      sparks = sparks.filter(p => p.life > 0);
      for (const p of sparks) {
        p.x += p.vx; p.y += p.vy; p.vy += 0.9; p.vx *= 0.97; p.life -= p.decay;
        cx.strokeStyle = `rgba(255,${Math.round(150 + 100 * p.life)},${Math.round(80 + 140 * p.life)},${p.life})`;
        cx.lineWidth = Math.max(1.4 * px, 5); cx.beginPath(); cx.moveTo(p.x, p.y); cx.lineTo(p.x - p.vx * 2.5, p.y - p.vy * 2.5); cx.stroke();
      }
      // Feed queued steps at a steady pace, so a batch from one poll plays out instead of landing at once.
      if (queue.length && now - lastStep > Math.max(60, 1600 / queue.length)) { lastStep = now; apply(queue.shift(), now); }

      if (moving || flickers.length || flashes.length || drawing.length || sparks.length || queue.length) kick();
    }
    function kick() { if (!raf && alive) raf = requestAnimationFrame(frame); }

    function apply(ev, now) {
      const path = (ev.path || []).map(String), chosen = String(ev.chosen);
      if (reduce) { path.forEach(id => alloc.add(id)); alloc.add(chosen); aim(alloc); kick(); return; }
      (ev.considered || []).slice(0, 8).forEach((id, i) => flickers.push({ id: String(id), t0: now + i * 25, life: 700, ph: Math.random() * 6 }));
      // Draw the path in, one edge after another, starting from the already-taken side.
      const order = [...path];
      let t0 = now + 180;
      for (const id of order) {
        const link = (byNode.get(id) || []).find(e => { const o = String(e[0]) === id ? String(e[1]) : String(e[0]); return alloc.has(o); });
        if (link) {
          const other = String(link[0]) === id ? String(link[1]) : String(link[0]);
          drawing.push({ e: orient(link, other), t0, dur: 220 });
          t0 += 200;
        }
        alloc.add(id);
      }
      alloc.add(chosen);
      const n = nodes[chosen];
      setTimeout(() => {
        flashes.push({ id: chosen, t0: performance.now() });
        if (n && !n[5]) for (let i = 0; i < (n[2] === "n" || n[2] === "k" ? 26 : 12); i++) {
          const a = Math.random() * 6.2832, v = 8 + Math.random() * 30;
          sparks.push({ x: n[0], y: n[1], vx: Math.cos(a) * v, vy: Math.sin(a) * v - 10, life: 1, decay: 0.018 + Math.random() * 0.025 });
        }
        kick();
      }, t0 - now);
      aim(new Set([...alloc].slice(-60)));   // follow the newest growth
    }

    return {
      setAlloc(ids, snap = true) { alloc = new Set((ids || []).map(String)); aim(alloc, 900, snap); },
      step(ev) { queue.push(ev); kick(); },
      reveal(ids) {
        // Grow a finished path outward from the class start, breadth first along taken edges.
        const want = new Set((ids || []).map(String));
        const start = [...want].find(id => nodes[id] && nodes[id][2] === "c") || [...want][0];
        alloc = new Set(start ? [start] : []);
        aim(want, 700, true);
        if (reduce || !start) { alloc = want; kick(); return; }
        const seen = new Set([start]); let frontier = [start], t0 = performance.now() + 250, wave = 0;
        while (frontier.length) {
          const next = [];
          for (const id of frontier) for (const e of byNode.get(id) || []) {
            const o = String(e[0]) === id ? String(e[1]) : String(e[0]);
            if (want.has(o) && !seen.has(o)) { seen.add(o); next.push(o); drawing.push({ e: orient(e, id), t0: t0 + wave * 70, dur: 260 }); }
          }
          const ids2 = next.slice(); const at = t0 + wave * 70 + 240;
          setTimeout(() => { ids2.forEach(id => alloc.add(id)); kick(); }, at - performance.now());
          frontier = next; wave++;
        }
        setTimeout(() => { want.forEach(id => alloc.add(id)); kick(); }, t0 + wave * 70 + 400 - performance.now());
        kick();
      },
      focus(ids) { aim(new Set((ids || []).map(String))); },
      stop() { alive = false; ro.disconnect(); if (raf) cancelAnimationFrame(raf); },
    };
  };
})();
