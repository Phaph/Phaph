// The lava bug: an easter egg. Click "bugs" in the footer ("This site is free of bugs") and a molten
// centipede crawls out and follows your cursor. Words it crawls over heat up; now and then it rips a word
// out of the page, carries it in its jaws and flings it. Thrown words drift, bounce off the screen edges,
// and fly back to their place after a while, so the page stays usable. Click "bugs" again or press Esc.
(function () {
  if (window.LavaBug) return;

  const SEGS = 11;                       // body segments, head first
  const RADII = Array.from({ length: SEGS }, (_, i) => i === 0 ? 11 : Math.max(3.5, 9.5 - i * 0.6));
  const GAP = RADII.map((r, i) => i === 0 ? 0 : (RADII[i - 1] + r) * 0.78);
  const LEG_SEGS = [1, 2, 3, 4, 5, 6, 7]; // segments with a leg on each side
  const MAX_DEBRIS = 14;

  let alive = false, cv, cx, raf = 0, last = 0, t = 0, dpr = 1;
  let mouse = { x: innerWidth * 0.5, y: innerHeight * 0.6 }, idleSince = 0;
  let segs = [], legs = [], embers = [], debris = [], words = new Set();
  let headVel = { x: 0, y: 0 }, jaw = 0, jawTarget = 0, holding = null, lastProbe = 0, lastGrab = 0;
  let wander = null;

  const css = document.createElement("style");
  css.textContent = `
.lb-w { transition: color .9s ease, text-shadow .9s ease; }
.lb-hot { color: #ffb347 !important; text-shadow: 0 0 6px #ff6a00, 0 0 14px rgba(255,90,0,.6); transition: color .08s, text-shadow .08s; }
.lb-gone { visibility: hidden; }
.lb-debris { position: fixed; left: 0; top: 0; z-index: 2147483001; pointer-events: none; white-space: nowrap;
  padding: 1px 5px; border: 1px solid rgba(255,140,60,.75); border-radius: 2px; background: rgba(20,10,6,.55);
  box-shadow: 0 0 10px rgba(255,90,0,.35), inset 0 0 6px rgba(255,120,40,.2); will-change: transform; }
.lb-canvas { position: fixed; inset: 0; width: 100vw; height: 100vh; z-index: 2147483000; pointer-events: none; }`;

  // ---------- Setup ----------
  function start() {
    if (alive) return;
    alive = true;
    document.head.appendChild(css);
    cv = document.createElement("canvas");
    cv.className = "lb-canvas";
    cv.setAttribute("aria-hidden", "true");
    document.body.appendChild(cv);
    cx = cv.getContext("2d");
    size();
    // Crawl out from the footer word that woke it.
    const from = document.querySelector("[data-lavabug]")?.getBoundingClientRect();
    const x0 = from ? from.left + from.width / 2 : innerWidth / 2, y0 = from ? from.top : innerHeight - 40;
    segs = Array.from({ length: SEGS }, (_, i) => ({ x: x0, y: y0 + i * 6, a: -Math.PI / 2 }));
    legs = [];
    LEG_SEGS.forEach((s, k) => [-1, 1].forEach(side => legs.push({
      seg: s, side, len: 13 - k * 0.6, phase: (k + (side > 0 ? 1 : 0)) % 2,
      foot: { x: x0 + side * 14, y: y0 + s * 6 }, from: null, to: null, st: 0,
    })));
    mouse = { x: x0, y: y0 - 160 };
    idleSince = performance.now();
    addEventListener("pointermove", onMove, { passive: true });
    addEventListener("mousemove", onMove, { passive: true });
    addEventListener("pointerdown", onMove, { passive: true });
    addEventListener("resize", size);
    addEventListener("keydown", onKey);
    last = performance.now();
    raf = requestAnimationFrame(frame);
  }

  function stop() {
    if (!alive) return;
    alive = false;
    cancelAnimationFrame(raf);
    removeEventListener("pointermove", onMove);
    removeEventListener("mousemove", onMove);
    removeEventListener("pointerdown", onMove);
    document.querySelector("[data-lavabug]")?.classList.remove("on");
    removeEventListener("resize", size);
    removeEventListener("keydown", onKey);
    debris.forEach(d => { d.el.remove(); if (d.span.isConnected) d.span.classList.remove("lb-gone"); });
    debris = []; holding = null; embers = [];
    // Put every word it touched back exactly as it was.
    words.forEach(span => {
      if (!span.isConnected) return;
      const parent = span.parentNode;
      parent.replaceChild(document.createTextNode(span.textContent), span);
      parent.normalize();
    });
    words.clear();
    cv.remove(); css.remove();
  }

  function size() {
    dpr = Math.min(devicePixelRatio || 1, 2);
    cv.width = innerWidth * dpr; cv.height = innerHeight * dpr;
    cx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  function onMove(e) { mouse.x = e.clientX; mouse.y = e.clientY; idleSince = performance.now(); wander = null; }
  function onKey(e) { if (e.key === "Escape") stop(); }

  // ---------- Words ----------
  const SKIP = "input,textarea,select,option,button,a,canvas,svg,script,style,code,pre,[contenteditable],.lb-debris";
  function wordAt(x, y) {
    let node, off;
    if (document.caretPositionFromPoint) {
      const p = document.caretPositionFromPoint(x, y); if (!p) return null; node = p.offsetNode; off = p.offset;
    } else if (document.caretRangeFromPoint) {
      const r = document.caretRangeFromPoint(x, y); if (!r) return null; node = r.startContainer; off = r.startOffset;
    } else return null;
    if (!node || node.nodeType !== 3) return null;
    const el = node.parentElement;
    if (!el || el.closest(SKIP) && !el.classList.contains("lb-w")) return null;
    if (el.classList.contains("lb-w")) return el.classList.contains("lb-gone") ? null : el;
    const text = node.textContent;
    let a = off, b = off;
    while (a > 0 && /\S/.test(text[a - 1])) a--;
    while (b < text.length && /\S/.test(text[b])) b++;
    if (b - a < 3) return null;
    // The caret must really be over the word, not next to a line's end.
    const range = document.createRange(); range.setStart(node, a); range.setEnd(node, b);
    const rect = range.getBoundingClientRect();
    if (x < rect.left - 2 || x > rect.right + 2 || y < rect.top - 2 || y > rect.bottom + 2) return null;
    const span = document.createElement("span"); span.className = "lb-w";
    try { range.surroundContents(span); } catch { return null; }
    words.add(span);
    return span;
  }
  function heat(span) {
    span.classList.add("lb-hot");
    clearTimeout(span._lbT);
    span._lbT = setTimeout(() => span.classList.remove("lb-hot"), 900);
  }
  function grab(span) {
    const r = span.getBoundingClientRect(), cs = getComputedStyle(span);
    const el = document.createElement("span");
    el.className = "lb-debris"; el.textContent = span.textContent;
    el.style.font = cs.font; el.style.color = "#ffcf8a"; el.style.letterSpacing = cs.letterSpacing;
    document.body.appendChild(el);
    span.classList.add("lb-gone");
    const d = { el, span, x: r.left + r.width / 2, y: r.top + r.height / 2, w: r.width, h: r.height,
      vx: 0, vy: 0, a: 0, va: 0, phase: "held", t0: performance.now(), hold: 700 + Math.random() * 900,
      life: 7000 + Math.random() * 5000 };
    debris.push(d); holding = d; jawTarget = 1;
    sparkBurst(d.x, d.y, 14);
  }

  // ---------- Motion ----------
  function frame(now) {
    if (!alive) return;
    const dt = Math.min(2.5, (now - last) / 16.67); last = now; t += dt;
    const head = segs[0];

    // Stand still too long and it goes looking for words to eat on its own.
    let target = mouse;
    if (now - idleSince > 3500) {
      if (!wander || Math.hypot(wander.x - head.x, wander.y - head.y) < 30 || now - wander.t0 > 5000) {
        wander = { x: 60 + Math.random() * (innerWidth - 120), y: 60 + Math.random() * (innerHeight - 120), t0: now };
      }
      target = wander;
    }
    const dx = target.x - head.x, dy = target.y - head.y, dist = Math.hypot(dx, dy);
    const want = Math.atan2(dy, dx);
    let da = ((want - head.a + Math.PI * 3) % (Math.PI * 2)) - Math.PI;
    const near = dist < 28;
    // Close to the cursor it doesn't sit still: it circles and sniffs.
    if (near) da = Math.sin(t * 0.07) * 0.08;
    head.a += Math.max(-0.11, Math.min(0.11, da)) * dt;
    const speed = near ? 0.9 : Math.min(7.5, 1.2 + dist * 0.045);
    const vx = Math.cos(head.a) * speed + Math.sin(t * 0.35) * 0.4 * Math.cos(head.a + 1.57);
    const vy = Math.sin(head.a) * speed + Math.sin(t * 0.35) * 0.4 * Math.sin(head.a + 1.57);
    headVel.x += (vx - headVel.x) * 0.25; headVel.y += (vy - headVel.y) * 0.25;
    head.x += headVel.x * dt; head.y += headVel.y * dt;

    // Body: each segment trails the one ahead at a fixed gap.
    for (let i = 1; i < SEGS; i++) {
      const p = segs[i - 1], s = segs[i];
      const ax = p.x - s.x, ay = p.y - s.y, d = Math.hypot(ax, ay) || 1;
      s.a = Math.atan2(ay, ax);
      s.x = p.x - (ax / d) * GAP[i]; s.y = p.y - (ay / d) * GAP[i];
    }

    // Legs: each foot stays planted until its rest spot runs ahead of it, then steps. Neighbours alternate.
    for (const L of legs) {
      const s = segs[L.seg], perp = s.a + L.side * Math.PI / 2;
      const rest = { x: s.x + Math.cos(perp) * L.len * 1.25 + Math.cos(s.a) * 7, y: s.y + Math.sin(perp) * L.len * 1.25 + Math.sin(s.a) * 7 };
      if (L.from) {
        L.st += 0.16 * dt;
        const k = Math.min(1, L.st), e = k * k * (3 - 2 * k);
        L.foot.x = L.from.x + (L.to.x - L.from.x) * e; L.foot.y = L.from.y + (L.to.y - L.from.y) * e;
        L.lift = Math.sin(k * Math.PI);
        if (k >= 1) { L.from = null; L.lift = 0; if (Math.random() < 0.25) sparkBurst(L.foot.x, L.foot.y, 1); }
      } else {
        const off = Math.hypot(rest.x - L.foot.x, rest.y - L.foot.y);
        const gait = Math.floor(t / 4) % 2 === L.phase;
        if (off > L.len * 0.9 && (gait || off > L.len * 1.8)) {
          L.from = { ...L.foot };
          L.to = { x: rest.x + headVel.x * 3, y: rest.y + headVel.y * 3 };
          L.st = 0;
        }
      }
    }

    // Jaws and words.
    const mouthX = head.x + Math.cos(head.a) * (RADII[0] + 5), mouthY = head.y + Math.sin(head.a) * (RADII[0] + 5);
    if (now - lastProbe > 70) {
      lastProbe = now;
      const span = wordAt(mouthX, mouthY);
      if (span && !span.classList.contains("lb-gone")) {
        heat(span);
        const canGrab = !holding && debris.length < MAX_DEBRIS && now - lastGrab > 1300 && Math.random() < 0.35;
        if (canGrab && !span.closest("label,h1")) { lastGrab = now; grab(span); }
      }
    }
    jaw += ((holding ? 0.15 : jawTarget) - jaw) * 0.25;
    if (!holding) jawTarget = Math.max(0, jawTarget - 0.06 * dt) + (Math.sin(t * 0.25) > 0.97 ? 0.6 : 0);

    // Debris: held in the jaws, then flung; drifts, bounces off the edges, and finally flies home.
    for (const d of debris) {
      const age = now - d.t0;
      if (d.phase === "held") {
        d.x += (mouthX + Math.cos(head.a) * d.w * 0.35 - d.x) * 0.35;
        d.y += (mouthY + Math.sin(head.a) * d.w * 0.35 - d.y) * 0.35;
        d.a += ((head.a + 0.2) - d.a) * 0.3;
        if (age > d.hold) {
          d.phase = "flung"; holding = null; jawTarget = 1;
          const fling = 9 + Math.random() * 6, dir = head.a + (Math.random() - 0.5) * 2.2;
          d.vx = Math.cos(dir) * fling + headVel.x; d.vy = Math.sin(dir) * fling + headVel.y;
          d.va = (Math.random() - 0.5) * 0.35;
          sparkBurst(d.x, d.y, 10);
        }
      } else if (d.phase === "flung") {
        d.x += d.vx * dt; d.y += d.vy * dt; d.a += d.va * dt;
        d.vx *= Math.pow(0.975, dt); d.vy *= Math.pow(0.975, dt); d.va *= Math.pow(0.985, dt);
        d.vy += Math.sin(t * 0.05 + d.w) * 0.02;    // a slow float, like ash in hot air
        const hw = d.w / 2, hh = d.h / 2;
        if (d.x < hw) { d.x = hw; d.vx = Math.abs(d.vx) * 0.7; }
        if (d.x > innerWidth - hw) { d.x = innerWidth - hw; d.vx = -Math.abs(d.vx) * 0.7; }
        if (d.y < hh) { d.y = hh; d.vy = Math.abs(d.vy) * 0.7; }
        if (d.y > innerHeight - hh) { d.y = innerHeight - hh; d.vy = -Math.abs(d.vy) * 0.7; }
        // The bug shoulders floating words out of its way.
        for (let i = 0; i < 4; i++) {
          const s = segs[i], px = d.x - s.x, py = d.y - s.y, pd = Math.hypot(px, py), reach = RADII[i] + Math.min(hw, 30);
          if (pd < reach && pd > 0) { d.vx += (px / pd) * 1.2; d.vy += (py / pd) * 1.2; d.va += (Math.random() - 0.5) * 0.1; }
        }
        if (age > d.life) { d.phase = "home"; d.h0 = { x: d.x, y: d.y, a: d.a }; d.th = now; }
      } else if (d.phase === "home") {
        if (!d.span.isConnected) { d.dead = true; d.el.remove(); continue; }
        const r = d.span.getBoundingClientRect();
        const k = Math.min(1, (now - d.th) / 650), e = 1 - Math.pow(1 - k, 3);
        d.x = d.h0.x + (r.left + r.width / 2 - d.h0.x) * e;
        d.y = d.h0.y + (r.top + r.height / 2 - d.h0.y) * e - Math.sin(k * Math.PI) * 40;
        d.a = d.h0.a * (1 - e);
        if (k >= 1) { d.dead = true; d.el.remove(); d.span.classList.remove("lb-gone"); heat(d.span); }
      }
      if (!d.dead) d.el.style.transform = `translate(${d.x - d.w / 2 - 5}px, ${d.y - d.h / 2 - 2}px) rotate(${d.a}rad)`;
    }
    debris = debris.filter(d => !d.dead);

    // Embers shed from the body.
    if (Math.random() < 0.5 * dt) {
      const s = segs[2 + ((Math.random() * (SEGS - 3)) | 0)];
      embers.push({ x: s.x + (Math.random() - 0.5) * 8, y: s.y + (Math.random() - 0.5) * 8,
        vx: (Math.random() - 0.5) * 0.6, vy: -0.3 - Math.random() * 0.8, life: 1, decay: 0.015 + Math.random() * 0.03 });
    }
    embers = embers.filter(e => (e.life -= e.decay * dt) > 0);
    for (const e of embers) { e.x += e.vx * dt; e.y += e.vy * dt; e.vx += (Math.random() - 0.5) * 0.08; }

    draw();
    raf = requestAnimationFrame(frame);
  }

  function sparkBurst(x, y, n) {
    for (let i = 0; i < n; i++) {
      const a = Math.random() * 6.283, v = 0.8 + Math.random() * 2.4;
      embers.push({ x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v - 0.6, life: 1, decay: 0.03 + Math.random() * 0.04 });
    }
  }

  // ---------- Drawing ----------
  function ik(hip, foot, a, b, side) {
    // Two-bone leg: the knee bends outward, and up while the foot is lifted.
    const dx = foot.x - hip.x, dy = foot.y - hip.y, d = Math.min(Math.hypot(dx, dy), a + b - 0.01);
    const base = Math.atan2(dy, dx), cosA = (a * a + d * d - b * b) / (2 * a * d);
    const ang = base - side * Math.acos(Math.max(-1, Math.min(1, cosA)));
    return { x: hip.x + Math.cos(ang) * a, y: hip.y + Math.sin(ang) * a };
  }

  function draw() {
    cx.clearRect(0, 0, innerWidth, innerHeight);
    cx.lineCap = "round"; cx.lineJoin = "round";

    for (const e of embers) {
      cx.fillStyle = e.life > 0.6 ? "#ffe0a0" : e.life > 0.3 ? "#ff9a30" : "#c2410c";
      cx.globalAlpha = Math.min(1, e.life * 1.4);
      cx.fillRect(e.x - 1, e.y - 1, e.life > 0.5 ? 2.2 : 1.6, e.life > 0.5 ? 2.2 : 1.6);
    }
    cx.globalAlpha = 1;

    // Legs under the body.
    for (const L of legs) {
      const s = segs[L.seg], perp = s.a + L.side * Math.PI / 2, r = RADII[L.seg];
      const hip = { x: s.x + Math.cos(perp) * r * 0.8, y: s.y + Math.sin(perp) * r * 0.8 };
      const foot = { x: L.foot.x, y: L.foot.y - (L.lift || 0) * 4 };
      const knee = ik(hip, foot, L.len * 0.75, L.len * 0.85, L.side);
      cx.strokeStyle = "#1c0b05"; cx.lineWidth = 3.2;
      cx.beginPath(); cx.moveTo(hip.x, hip.y); cx.lineTo(knee.x, knee.y); cx.lineTo(foot.x, foot.y); cx.stroke();
      cx.strokeStyle = "rgba(255,120,30,.75)"; cx.lineWidth = 1;
      cx.beginPath(); cx.moveTo(hip.x, hip.y); cx.lineTo(knee.x, knee.y); cx.lineTo(foot.x, foot.y); cx.stroke();
      cx.fillStyle = "#ffb347"; cx.beginPath(); cx.arc(knee.x, knee.y, 1.4, 0, 6.283); cx.fill();
    }

    // Glow pass, then the crusted segments tail to head.
    cx.save(); cx.globalCompositeOperation = "lighter";
    for (let i = SEGS - 1; i >= 0; i--) {
      const s = segs[i], g = cx.createRadialGradient(s.x, s.y, 0, s.x, s.y, RADII[i] * 3);
      const pulse = 0.22 + 0.08 * Math.sin(t * 0.12 - i * 0.6);
      g.addColorStop(0, `rgba(255,110,20,${pulse})`); g.addColorStop(1, "rgba(255,60,0,0)");
      cx.fillStyle = g; cx.beginPath(); cx.arc(s.x, s.y, RADII[i] * 3, 0, 6.283); cx.fill();
    }
    cx.restore();
    for (let i = SEGS - 1; i >= 0; i--) {
      const s = segs[i], r = RADII[i];
      const g = cx.createRadialGradient(s.x - r * 0.2, s.y - r * 0.2, r * 0.1, s.x, s.y, r);
      const hot = 0.5 + 0.5 * Math.sin(t * 0.12 - i * 0.6);
      g.addColorStop(0, hot > 0.6 ? "#fff1c4" : "#ffd27a");
      g.addColorStop(0.45, "#ff8a1f"); g.addColorStop(0.8, "#a8320a"); g.addColorStop(1, "#2b0c05");
      cx.fillStyle = g; cx.beginPath(); cx.arc(s.x, s.y, r, 0, 6.283); cx.fill();
      // Cooled crust plates across the back, glowing cracks between them.
      cx.strokeStyle = "rgba(30,10,4,.85)"; cx.lineWidth = Math.max(1, r * 0.22);
      cx.beginPath(); cx.arc(s.x, s.y, r * 0.62, s.a + 1.9, s.a + 4.4); cx.stroke();
      if (i > 0) {
        cx.strokeStyle = "rgba(25,8,3,.9)"; cx.lineWidth = 1.2;
        cx.beginPath();
        cx.moveTo(s.x + Math.cos(s.a + 1.57) * r * 0.9, s.y + Math.sin(s.a + 1.57) * r * 0.9);
        cx.lineTo(s.x + Math.cos(s.a - 1.57) * r * 0.9, s.y + Math.sin(s.a - 1.57) * r * 0.9);
        cx.stroke();
      }
    }

    // Head: jaws, eyes, antennae.
    const h = segs[0], r = RADII[0], fa = h.a;
    for (const side of [-1, 1]) {
      const open = 0.35 + jaw * 0.55;
      const bx = h.x + Math.cos(fa + side * 0.5) * r * 0.85, by = h.y + Math.sin(fa + side * 0.5) * r * 0.85;
      const tx = bx + Math.cos(fa + side * open) * 9, ty = by + Math.sin(fa + side * open) * 9;
      const ex = tx + Math.cos(fa - side * 0.9) * 5, ey = ty + Math.sin(fa - side * 0.9) * 5;
      cx.strokeStyle = "#1c0b05"; cx.lineWidth = 3;
      cx.beginPath(); cx.moveTo(bx, by); cx.lineTo(tx, ty); cx.lineTo(ex, ey); cx.stroke();
      cx.strokeStyle = "#ff9a30"; cx.lineWidth = 1;
      cx.beginPath(); cx.moveTo(bx, by); cx.lineTo(tx, ty); cx.lineTo(ex, ey); cx.stroke();
      // Antennae, swinging a little behind the head's turns.
      const sway = Math.sin(t * 0.2 + side) * 0.25;
      const ax0 = h.x + Math.cos(fa + side * 0.9) * r * 0.7, ay0 = h.y + Math.sin(fa + side * 0.9) * r * 0.7;
      const ax1 = ax0 + Math.cos(fa + side * 0.55 + sway) * 14, ay1 = ay0 + Math.sin(fa + side * 0.55 + sway) * 14;
      const ax2 = ax1 + Math.cos(fa + side * 0.85 + sway * 1.6) * 10, ay2 = ay1 + Math.sin(fa + side * 0.85 + sway * 1.6) * 10;
      cx.strokeStyle = "rgba(255,150,60,.85)"; cx.lineWidth = 1;
      cx.beginPath(); cx.moveTo(ax0, ay0); cx.quadraticCurveTo(ax1, ay1, ax2, ay2); cx.stroke();
      cx.fillStyle = "#fff1c4"; cx.beginPath(); cx.arc(ax2, ay2, 1.3, 0, 6.283); cx.fill();
      // Eyes.
      const exx = h.x + Math.cos(fa + side * 0.55) * r * 0.55, eyy = h.y + Math.sin(fa + side * 0.55) * r * 0.55;
      cx.fillStyle = "#1a0602"; cx.beginPath(); cx.arc(exx, eyy, 2.6, 0, 6.283); cx.fill();
      cx.fillStyle = "#fff6c8"; cx.beginPath(); cx.arc(exx + Math.cos(fa) * 0.8, eyy + Math.sin(fa) * 0.8, 1.2, 0, 6.283); cx.fill();
    }
  }

  window.LavaBug = { toggle() { alive ? stop() : start(); return alive; }, get on() { return alive; } };
})();
