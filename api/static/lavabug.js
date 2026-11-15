// The lava bugs: an easter egg. Click "bugs" in the footer ("This site is free of bugs") and a molten centipede
// crawls out and follows your cursor. Every click adds another, each in a new colour and body style, up to 20.
// They shoulder each other aside instead of overlapping, and now and then two of them meet: they greet, give
// chase, or one steals the word the other is carrying. Words they crawl over heat up in their colour; now and
// then a bug rips a word out of the page, carries it and flings it. Thrown words drift and fly home after a while,
// so the page stays usable. Esc (or reloading the page) sends every bug away and puts every word back.
(function () {
  if (window.LavaBug) return;

  const MAX_BUGS = 20, MAX_DEBRIS = 20;

  // Ten colourways; each appears in two body styles, so 20 bugs never repeat.
  const PALETTES = [
    { name: "lava", hot: "#fff1c4", mid: "#ff8a1f", deep: "#a8320a", crust: "#2b0c05", glow: "255,110,20", leg: "#ff9a30", eye: "#fff6c8" },
    { name: "frost", hot: "#f0fbff", mid: "#5fc8ff", deep: "#1d5f9e", crust: "#06162b", glow: "80,180,255", leg: "#8fdcff", eye: "#ffffff" },
    { name: "venom", hot: "#f4ffd0", mid: "#8dff3a", deep: "#2f7d12", crust: "#0a1f05", glow: "120,255,60", leg: "#b6ff6a", eye: "#fffbd0" },
    { name: "void", hot: "#f3e6ff", mid: "#b46bff", deep: "#4b1b8f", crust: "#12052a", glow: "170,90,255", leg: "#cf9bff", eye: "#ffe6ff" },
    { name: "gold", hot: "#fffbe0", mid: "#ffd23a", deep: "#9a6b05", crust: "#2a1c02", glow: "255,210,60", leg: "#ffe27a", eye: "#ffffff" },
    { name: "blood", hot: "#ffe0e0", mid: "#ff3b3b", deep: "#7a0b0b", crust: "#200303", glow: "255,50,50", leg: "#ff7070", eye: "#fff0f0" },
    { name: "rose", hot: "#fff0f7", mid: "#ff5fb4", deep: "#8f1a5a", crust: "#25061a", glow: "255,90,180", leg: "#ff9bd0", eye: "#ffffff" },
    { name: "tide", hot: "#e6fffb", mid: "#2ff5d0", deep: "#0e7a6a", crust: "#03201b", glow: "40,240,200", leg: "#7fffe6", eye: "#ffffff" },
    { name: "ash", hot: "#ffffff", mid: "#cfd3d8", deep: "#5d636b", crust: "#15181c", glow: "220,230,240", leg: "#e8edf2", eye: "#ff5a2a" },
    { name: "copper", hot: "#ffe9d6", mid: "#ff9a5a", deep: "#8a3a12", crust: "#220d04", glow: "255,140,80", leg: "#ffb98a", eye: "#fff3e0" },
  ];
  // Body styles: how many segments, how big, how leggy, and what's on its back.
  const STYLES = [
    { segs: 11, size: 1.0, legsFrom: 1, legsTo: 7, legLen: 13, back: "crust", antenna: 14, jaw: 9, speed: 1.0 },     // the original
    { segs: 15, size: 0.72, legsFrom: 1, legsTo: 13, legLen: 10, back: "dots", antenna: 18, jaw: 6, speed: 1.15 },  // long centipede
    { segs: 7, size: 1.35, legsFrom: 1, legsTo: 4, legLen: 17, back: "plates", antenna: 10, jaw: 12, speed: 0.8 },  // squat beetle
    { segs: 10, size: 0.95, legsFrom: 1, legsTo: 6, legLen: 15, back: "spikes", antenna: 20, jaw: 8, speed: 1.05 }, // spiny
    { segs: 13, size: 0.85, legsFrom: 2, legsTo: 9, legLen: 19, back: "stripe", antenna: 24, jaw: 7, speed: 1.2 },  // skittering long-legs
    { segs: 9, size: 1.15, legsFrom: 1, legsTo: 5, legLen: 12, back: "crust", antenna: 8, jaw: 14, speed: 0.9 },    // big-jawed
  ];

  let alive = false, cv, cx, raf = 0, last = 0, t = 0, dpr = 1, made = 0;
  let mouse = { x: innerWidth * 0.5, y: innerHeight * 0.6 }, idleSince = 0;
  let bugs = [], embers = [], debris = [], words = new Set(), lastProbe = 0, nextMeet = 0;

  const css = document.createElement("style");
  css.textContent = `
.lb-w { transition: color .9s ease, text-shadow .9s ease; }
.lb-gone { visibility: hidden; }
.lb-debris { position: fixed; left: 0; top: 0; z-index: 2147483001; pointer-events: none; white-space: nowrap;
  padding: 1px 5px; border: 1px solid; border-radius: 2px; background: rgba(14,10,8,.6); will-change: transform; }
.lb-canvas { position: fixed; inset: 0; width: 100vw; height: 100vh; z-index: 2147483000; pointer-events: none; }`;

  // ---------- Bugs ----------
  function makeBug(n, x0, y0) {
    const pal = PALETTES[n % PALETTES.length];
    // Each colourway pairs with a different style the second time round.
    const st = STYLES[(n + Math.floor(n / PALETTES.length) * 3) % STYLES.length];
    const radii = Array.from({ length: st.segs }, (_, i) => (i === 0 ? 11 : Math.max(3.2, 9.5 - i * (6 / st.segs))) * st.size);
    const gap = radii.map((r, i) => (i === 0 ? 0 : (radii[i - 1] + r) * 0.78));
    const segs = Array.from({ length: st.segs }, (_, i) => ({ x: x0, y: y0 + i * 5, a: -Math.PI / 2 }));
    const legs = [];
    for (let s = st.legsFrom; s <= Math.min(st.legsTo, st.segs - 2); s++) {
      for (const side of [-1, 1]) {
        legs.push({ seg: s, side, len: st.legLen * st.size * (1 - (s - st.legsFrom) * 0.03), phase: (s + (side > 0 ? 1 : 0)) % 2,
          foot: { x: x0 + side * 14, y: y0 + s * 5 }, from: null, to: null, st: 0, lift: 0 });
      }
    }
    return { n, pal, st, radii, gap, segs, legs, vel: { x: 0, y: 0 }, jaw: 0, jawTarget: 0, holding: null, lastGrab: 0,
      // Its own place around the cursor, so a swarm circles you instead of piling on one spot.
      orbit: { a: Math.random() * 6.283, r: n === 0 ? 0 : 55 + Math.min(n, 12) * 16, spin: (Math.random() < 0.5 ? -1 : 1) * (0.004 + Math.random() * 0.006) },
      wander: null, mode: "follow", until: 0, other: null, wiggle: 0 };
  }

  function add() {
    if (!alive) start();
    if (bugs.length >= MAX_BUGS) return bugs.length;
    const from = document.querySelector("[data-lavabug]")?.getBoundingClientRect();
    const x0 = from ? from.left + from.width / 2 : innerWidth / 2;
    const y0 = from ? Math.min(from.top, innerHeight - 20) : innerHeight - 40;
    const b = makeBug(made++, x0 + (Math.random() - 0.5) * 20, y0);
    bugs.push(b);
    sparkBurst(x0, y0, 18, b.pal);
    return bugs.length;
  }

  // ---------- Setup ----------
  function start() {
    alive = true;
    document.head.appendChild(css);
    cv = document.createElement("canvas");
    cv.className = "lb-canvas";
    cv.setAttribute("aria-hidden", "true");
    document.body.appendChild(cv);
    cx = cv.getContext("2d");
    size();
    mouse = { x: innerWidth / 2, y: innerHeight * 0.45 };
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
    removeEventListener("resize", size);
    removeEventListener("keydown", onKey);
    document.querySelector("[data-lavabug]")?.classList.remove("on");
    debris.forEach(d => { d.el.remove(); if (d.span.isConnected) d.span.classList.remove("lb-gone"); });
    debris = []; embers = []; bugs = []; made = 0;
    // Put every word they touched back exactly as it was.
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
  function onMove(e) { mouse.x = e.clientX; mouse.y = e.clientY; idleSince = performance.now(); bugs.forEach(b => b.wander = null); }
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
    if (!el) return null;
    if (el.classList.contains("lb-w")) return el.classList.contains("lb-gone") ? null : el;
    if (el.closest(SKIP)) return null;
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
  function heat(span, pal) {
    // The word glows in the colour of the bug that touched it, then cools.
    span.style.transition = "color .08s, text-shadow .08s";
    span.style.color = pal.hot;
    span.style.textShadow = `0 0 6px ${pal.mid}, 0 0 14px rgba(${pal.glow},.6)`;
    clearTimeout(span._lbT);
    span._lbT = setTimeout(() => { span.style.transition = ""; span.style.color = ""; span.style.textShadow = ""; }, 900);
  }
  function grab(b, span) {
    const r = span.getBoundingClientRect(), cs = getComputedStyle(span);
    const el = document.createElement("span");
    el.className = "lb-debris"; el.textContent = span.textContent;
    el.style.font = cs.font; el.style.letterSpacing = cs.letterSpacing;
    paintDebris(el, b.pal);
    document.body.appendChild(el);
    span.classList.add("lb-gone");
    const d = { el, span, x: r.left + r.width / 2, y: r.top + r.height / 2, w: r.width, h: r.height,
      vx: 0, vy: 0, a: 0, va: 0, phase: "held", by: b, t0: performance.now(), hold: 700 + Math.random() * 900,
      life: 7000 + Math.random() * 5000 };
    debris.push(d); b.holding = d; b.jawTarget = 1;
    sparkBurst(d.x, d.y, 12, b.pal);
  }
  function paintDebris(el, pal) {
    el.style.color = pal.hot;
    el.style.borderColor = `rgba(${pal.glow},.75)`;
    el.style.boxShadow = `0 0 10px rgba(${pal.glow},.35), inset 0 0 6px rgba(${pal.glow},.2)`;
  }

  // ---------- Meetings ----------
  // Rare, and never two at once: when two bugs bump heads, maybe they greet, give chase, or one steals the other's word.
  function meet(a, b, now) {
    if (now < nextMeet || a.mode !== "follow" || b.mode !== "follow" || Math.random() > 0.08) return;
    nextMeet = now + 9000 + Math.random() * 9000;
    const roll = Math.random();
    if (b.holding && roll < 0.35) {
      // A thief: a snatches the word out of b's jaws and runs; b chases it.
      const d = b.holding; b.holding = null; a.holding = d; d.by = a; d.t0 = now; d.hold = 1800;
      paintDebris(d.el, a.pal);
      a.mode = "flee"; a.other = b; a.until = now + 2500;
      b.mode = "chase"; b.other = a; b.until = now + 2500;
      sparkBurst(d.x, d.y, 16, a.pal);
    } else if (roll < 0.65) {
      // A greeting: both stop, face each other, antennae flutter, sparks in both colours.
      for (const [x, y] of [[a, b], [b, a]]) { x.mode = "greet"; x.other = y; x.until = now + 1600; }
      const mx = (a.segs[0].x + b.segs[0].x) / 2, my = (a.segs[0].y + b.segs[0].y) / 2;
      sparkBurst(mx, my, 14, a.pal); sparkBurst(mx, my, 14, b.pal);
    } else {
      // A game of chase.
      a.mode = "chase"; a.other = b; a.until = now + 3200;
      b.mode = "flee"; b.other = a; b.until = now + 3200;
    }
  }

  // ---------- Motion ----------
  function steer(b, target, dt, now) {
    const head = b.segs[0];
    const dx = target.x - head.x, dy = target.y - head.y, dist = Math.hypot(dx, dy);
    let da = ((Math.atan2(dy, dx) - head.a + Math.PI * 3) % (Math.PI * 2)) - Math.PI;
    const near = dist < 28;
    if (near) da = Math.sin(t * 0.07 + b.n) * 0.08;   // close to where it wants to be: it circles and sniffs
    if (b.mode === "greet") da = 0;
    head.a += Math.max(-0.11, Math.min(0.11, da)) * dt;
    let speed = (near ? 0.9 : Math.min(7.5, 1.2 + dist * 0.045)) * b.st.speed;
    if (b.mode === "greet") speed = 0.15;
    if (b.mode === "flee" || b.mode === "chase") speed = Math.max(speed, 5.5 * b.st.speed);
    const side = Math.sin(t * 0.35 + b.n) * 0.4;
    const vx = Math.cos(head.a) * speed + side * Math.cos(head.a + 1.57);
    const vy = Math.sin(head.a) * speed + side * Math.sin(head.a + 1.57);
    b.vel.x += (vx - b.vel.x) * 0.25; b.vel.y += (vy - b.vel.y) * 0.25;
    head.x += b.vel.x * dt; head.y += b.vel.y * dt;
    head.x = Math.max(-40, Math.min(innerWidth + 40, head.x));
    head.y = Math.max(-40, Math.min(innerHeight + 40, head.y));
  }

  function targetFor(b, now) {
    if (b.mode !== "follow" && now > b.until) { b.mode = "follow"; b.other = null; }
    const o = b.other?.segs;
    if (b.mode === "greet" && o) return o[0];
    if (b.mode === "chase" && o) return o[o.length - 1];
    if (b.mode === "flee" && o) {
      const h = b.segs[0], dx = h.x - o[0].x, dy = h.y - o[0].y, d = Math.hypot(dx, dy) || 1;
      return { x: h.x + (dx / d) * 200, y: h.y + (dy / d) * 200 };
    }
    if (now - idleSince > 3500) {
      // Mouse still: each bug goes looking for words on its own.
      const h = b.segs[0];
      if (!b.wander || Math.hypot(b.wander.x - h.x, b.wander.y - h.y) < 30 || now - b.wander.t0 > 5000) {
        b.wander = { x: 60 + Math.random() * (innerWidth - 120), y: 60 + Math.random() * (innerHeight - 120), t0: now };
      }
      return b.wander;
    }
    b.orbit.a += b.orbit.spin;
    return { x: mouse.x + Math.cos(b.orbit.a) * b.orbit.r, y: mouse.y + Math.sin(b.orbit.a) * b.orbit.r };
  }

  function follow(b) {
    // Body: each segment trails the one ahead at a fixed gap.
    for (let i = 1; i < b.segs.length; i++) {
      const p = b.segs[i - 1], s = b.segs[i];
      const ax = p.x - s.x, ay = p.y - s.y, d = Math.hypot(ax, ay) || 1;
      s.a = Math.atan2(ay, ax);
      s.x = p.x - (ax / d) * b.gap[i]; s.y = p.y - (ay / d) * b.gap[i];
    }
  }

  function collide(dt, now) {
    // No overlapping: any two segments of different bugs that touch are pushed apart, and a head that runs into
    // another bug turns away from it, so they bounce off each other.
    for (let i = 0; i < bugs.length; i++) {
      const A = bugs[i];
      for (let j = i + 1; j < bugs.length; j++) {
        const B = bugs[j];
        const reach = A.radii[0] * 2 * A.segs.length + B.radii[0] * 2 * B.segs.length;
        if (Math.abs(A.segs[0].x - B.segs[0].x) > reach || Math.abs(A.segs[0].y - B.segs[0].y) > reach) continue;
        for (let p = 0; p < A.segs.length; p++) {
          const s = A.segs[p], rs = A.radii[p];
          for (let q = 0; q < B.segs.length; q++) {
            const u = B.segs[q], ru = B.radii[q];
            const dx = u.x - s.x, dy = u.y - s.y, d = Math.hypot(dx, dy), min = rs + ru + 2;
            if (d >= min || d === 0) continue;
            const push = (min - d) / 2, nx = dx / d, ny = dy / d;
            s.x -= nx * push; s.y -= ny * push; u.x += nx * push; u.y += ny * push;
            if (p === 0) bounce(A, -nx, -ny);
            if (q === 0) bounce(B, nx, ny);
            if (p === 0 && q === 0) meet(Math.random() < 0.5 ? A : B, Math.random() < 0.5 ? B : A, now);
          }
        }
      }
    }
  }
  function bounce(b, nx, ny) {
    // Turn the head away along the contact normal and give it a little shove.
    if (b.mode === "greet") return;
    const away = Math.atan2(ny, nx);
    let da = ((away - b.segs[0].a + Math.PI * 3) % (Math.PI * 2)) - Math.PI;
    b.segs[0].a += da * 0.35;
    b.vel.x += nx * 1.2; b.vel.y += ny * 1.2;
  }

  function legsStep(b, dt) {
    // Each foot stays planted until its rest spot runs ahead of it, then steps. Neighbours alternate.
    for (const L of b.legs) {
      const s = b.segs[L.seg], perp = s.a + L.side * Math.PI / 2;
      const rest = { x: s.x + Math.cos(perp) * L.len * 1.25 + Math.cos(s.a) * 7, y: s.y + Math.sin(perp) * L.len * 1.25 + Math.sin(s.a) * 7 };
      if (L.from) {
        L.st += 0.16 * dt;
        const k = Math.min(1, L.st), e = k * k * (3 - 2 * k);
        L.foot.x = L.from.x + (L.to.x - L.from.x) * e; L.foot.y = L.from.y + (L.to.y - L.from.y) * e;
        L.lift = Math.sin(k * Math.PI);
        if (k >= 1) { L.from = null; L.lift = 0; if (Math.random() < 0.2) sparkBurst(L.foot.x, L.foot.y, 1, b.pal); }
      } else {
        const off = Math.hypot(rest.x - L.foot.x, rest.y - L.foot.y);
        const gait = Math.floor(t / 4) % 2 === L.phase;
        if (off > L.len * 0.9 && (gait || off > L.len * 1.8)) {
          L.from = { ...L.foot }; L.to = { x: rest.x + b.vel.x * 3, y: rest.y + b.vel.y * 3 }; L.st = 0;
        }
      }
    }
  }

  function frame(now) {
    if (!alive) return;
    const dt = Math.min(2.5, (now - last) / 16.67); last = now; t += dt;

    for (const b of bugs) { steer(b, targetFor(b, now), dt, now); follow(b); }
    collide(dt, now);
    for (const b of bugs) { follow(b); legsStep(b, dt); }

    // Jaws and words: one bug probes per frame (round robin), so a swarm stays cheap.
    if (bugs.length && now - lastProbe > 70 / Math.min(bugs.length, 4)) {
      lastProbe = now;
      const b = bugs[Math.floor(t) % bugs.length];
      const h = b.segs[0], r0 = b.radii[0];
      const mx = h.x + Math.cos(h.a) * (r0 + 5), my = h.y + Math.sin(h.a) * (r0 + 5);
      const span = wordAt(mx, my);
      if (span && !span.classList.contains("lb-gone")) {
        heat(span, b.pal);
        const can = !b.holding && debris.length < MAX_DEBRIS && now - b.lastGrab > 1300 && Math.random() < 0.35;
        if (can && !span.closest("label,h1")) { b.lastGrab = now; grab(b, span); }
      }
    }
    for (const b of bugs) {
      b.jaw += ((b.holding ? 0.15 : b.jawTarget) - b.jaw) * 0.25;
      if (!b.holding) b.jawTarget = Math.max(0, b.jawTarget - 0.06 * dt) + (Math.sin(t * 0.25 + b.n) > 0.97 ? 0.6 : 0);
      b.wiggle = b.mode === "greet" ? 1 : b.wiggle * 0.9;
    }

    // Debris: held in the jaws, then flung; drifts, bounces off the edges and bugs, and finally flies home.
    for (const d of debris) {
      const age = now - d.t0, b = d.by;
      if (d.phase === "held" && bugs.includes(b)) {
        const h = b.segs[0], r0 = b.radii[0];
        const mx = h.x + Math.cos(h.a) * (r0 + 5 + d.w * 0.35), my = h.y + Math.sin(h.a) * (r0 + 5 + d.w * 0.35);
        d.x += (mx - d.x) * 0.35; d.y += (my - d.y) * 0.35;
        d.a += ((h.a + 0.2) - d.a) * 0.3;
        if (age > d.hold) {
          d.phase = "flung"; b.holding = null; b.jawTarget = 1;
          const fling = 9 + Math.random() * 6, dir = h.a + (Math.random() - 0.5) * 2.2;
          d.vx = Math.cos(dir) * fling + b.vel.x; d.vy = Math.sin(dir) * fling + b.vel.y;
          d.va = (Math.random() - 0.5) * 0.35;
          sparkBurst(d.x, d.y, 8, b.pal);
        }
      } else if (d.phase === "flung" || d.phase === "held") {
        d.phase = "flung";
        d.x += d.vx * dt; d.y += d.vy * dt; d.a += d.va * dt;
        d.vx *= Math.pow(0.975, dt); d.vy *= Math.pow(0.975, dt); d.va *= Math.pow(0.985, dt);
        d.vy += Math.sin(t * 0.05 + d.w) * 0.02;
        const hw = d.w / 2, hh = d.h / 2;
        if (d.x < hw) { d.x = hw; d.vx = Math.abs(d.vx) * 0.7; }
        if (d.x > innerWidth - hw) { d.x = innerWidth - hw; d.vx = -Math.abs(d.vx) * 0.7; }
        if (d.y < hh) { d.y = hh; d.vy = Math.abs(d.vy) * 0.7; }
        if (d.y > innerHeight - hh) { d.y = innerHeight - hh; d.vy = -Math.abs(d.vy) * 0.7; }
        for (const bb of bugs) for (let i = 0; i < Math.min(4, bb.segs.length); i++) {
          const s = bb.segs[i], px = d.x - s.x, py = d.y - s.y, pd = Math.hypot(px, py), reach = bb.radii[i] + Math.min(hw, 30);
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
        if (k >= 1) { d.dead = true; d.el.remove(); d.span.classList.remove("lb-gone"); heat(d.span, d.by.pal); }
      }
      if (!d.dead) d.el.style.transform = `translate(${d.x - d.w / 2 - 5}px, ${d.y - d.h / 2 - 2}px) rotate(${d.a}rad)`;
    }
    debris = debris.filter(d => !d.dead);

    // Embers shed from the bodies.
    for (const b of bugs) {
      if (Math.random() < 0.35 * dt) {
        const s = b.segs[2 + ((Math.random() * (b.segs.length - 3)) | 0)];
        embers.push({ x: s.x + (Math.random() - 0.5) * 8, y: s.y + (Math.random() - 0.5) * 8, pal: b.pal,
          vx: (Math.random() - 0.5) * 0.6, vy: -0.3 - Math.random() * 0.8, life: 1, decay: 0.015 + Math.random() * 0.03 });
      }
    }
    if (embers.length > 600) embers.splice(0, embers.length - 600);
    embers = embers.filter(e => (e.life -= e.decay * dt) > 0);
    for (const e of embers) { e.x += e.vx * dt; e.y += e.vy * dt; e.vx += (Math.random() - 0.5) * 0.08; }

    draw();
    raf = requestAnimationFrame(frame);
  }

  function sparkBurst(x, y, n, pal) {
    for (let i = 0; i < n; i++) {
      const a = Math.random() * 6.283, v = 0.8 + Math.random() * 2.4;
      embers.push({ x, y, pal, vx: Math.cos(a) * v, vy: Math.sin(a) * v - 0.6, life: 1, decay: 0.03 + Math.random() * 0.04 });
    }
  }

  // ---------- Drawing ----------
  function ik(hip, foot, a, b, side) {
    // Two-bone leg: the knee bends outward.
    const dx = foot.x - hip.x, dy = foot.y - hip.y, d = Math.min(Math.hypot(dx, dy), a + b - 0.01);
    const base = Math.atan2(dy, dx), cosA = (a * a + d * d - b * b) / (2 * a * d);
    const ang = base - side * Math.acos(Math.max(-1, Math.min(1, cosA)));
    return { x: hip.x + Math.cos(ang) * a, y: hip.y + Math.sin(ang) * a };
  }

  function draw() {
    cx.clearRect(0, 0, innerWidth, innerHeight);
    cx.lineCap = "round"; cx.lineJoin = "round";
    for (const e of embers) {
      cx.fillStyle = e.life > 0.6 ? e.pal.hot : e.life > 0.3 ? e.pal.mid : e.pal.deep;
      cx.globalAlpha = Math.min(1, e.life * 1.4);
      const s = e.life > 0.5 ? 2.2 : 1.6;
      cx.fillRect(e.x - 1, e.y - 1, s, s);
    }
    cx.globalAlpha = 1;
    for (const b of bugs) drawBug(b);
  }

  function drawBug(b) {
    const { pal, st, segs, radii } = b;
    for (const L of b.legs) {
      const s = segs[L.seg], perp = s.a + L.side * Math.PI / 2, r = radii[L.seg];
      const hip = { x: s.x + Math.cos(perp) * r * 0.8, y: s.y + Math.sin(perp) * r * 0.8 };
      const foot = { x: L.foot.x, y: L.foot.y - (L.lift || 0) * 4 };
      const knee = ik(hip, foot, L.len * 0.75, L.len * 0.85, L.side);
      cx.strokeStyle = pal.crust; cx.lineWidth = 3.2 * Math.min(1.2, st.size);
      cx.beginPath(); cx.moveTo(hip.x, hip.y); cx.lineTo(knee.x, knee.y); cx.lineTo(foot.x, foot.y); cx.stroke();
      cx.strokeStyle = pal.leg; cx.globalAlpha = 0.75; cx.lineWidth = 1;
      cx.beginPath(); cx.moveTo(hip.x, hip.y); cx.lineTo(knee.x, knee.y); cx.lineTo(foot.x, foot.y); cx.stroke();
      cx.globalAlpha = 1;
      cx.fillStyle = pal.hot; cx.beginPath(); cx.arc(knee.x, knee.y, 1.4, 0, 6.283); cx.fill();
    }
    // Glow pass, then the segments tail to head.
    cx.save(); cx.globalCompositeOperation = "lighter";
    for (let i = segs.length - 1; i >= 0; i--) {
      const s = segs[i], R = radii[i] * 3, g = cx.createRadialGradient(s.x, s.y, 0, s.x, s.y, R);
      const pulse = 0.2 + 0.08 * Math.sin(t * 0.12 - i * 0.6 + b.n);
      g.addColorStop(0, `rgba(${pal.glow},${pulse})`); g.addColorStop(1, `rgba(${pal.glow},0)`);
      cx.fillStyle = g; cx.beginPath(); cx.arc(s.x, s.y, R, 0, 6.283); cx.fill();
    }
    cx.restore();
    for (let i = segs.length - 1; i >= 0; i--) {
      const s = segs[i], r = radii[i];
      const g = cx.createRadialGradient(s.x - r * 0.2, s.y - r * 0.2, r * 0.1, s.x, s.y, r);
      const hot = 0.5 + 0.5 * Math.sin(t * 0.12 - i * 0.6 + b.n);
      g.addColorStop(0, hot > 0.6 ? pal.hot : pal.mid); g.addColorStop(0.45, pal.mid);
      g.addColorStop(0.8, pal.deep); g.addColorStop(1, pal.crust);
      cx.fillStyle = g;
      cx.beginPath();
      if (st.back === "plates") cx.ellipse(s.x, s.y, r * 1.15, r * 0.85, s.a + Math.PI / 2, 0, 6.283);
      else cx.arc(s.x, s.y, r, 0, 6.283);
      cx.fill();
      backDetail(b, s, r, i);
    }
    drawHead(b);
  }

  function backDetail(b, s, r, i) {
    const { pal, st } = b;
    if (st.back === "crust") {
      cx.strokeStyle = pal.crust; cx.globalAlpha = 0.85; cx.lineWidth = Math.max(1, r * 0.22);
      cx.beginPath(); cx.arc(s.x, s.y, r * 0.62, s.a + 1.9, s.a + 4.4); cx.stroke(); cx.globalAlpha = 1;
    } else if (st.back === "dots" && i > 0) {
      cx.fillStyle = pal.crust;
      for (const side of [-1, 1]) {
        cx.beginPath(); cx.arc(s.x + Math.cos(s.a + side * 1.57) * r * 0.45, s.y + Math.sin(s.a + side * 1.57) * r * 0.45, r * 0.22, 0, 6.283); cx.fill();
      }
    } else if (st.back === "plates" && i > 0) {
      cx.strokeStyle = pal.crust; cx.lineWidth = 1.4;
      cx.beginPath(); cx.ellipse(s.x, s.y, r * 0.9, r * 0.55, s.a + Math.PI / 2, Math.PI, 2 * Math.PI); cx.stroke();
    } else if (st.back === "spikes" && i > 0) {
      cx.fillStyle = pal.crust;
      const back = s.a + Math.PI;
      for (const side of [-1, 1]) {
        const a0 = s.a + side * 1.57, bx = s.x + Math.cos(a0) * r * 0.7, by = s.y + Math.sin(a0) * r * 0.7;
        const tx = s.x + Math.cos(a0 + side * -0.4) * r * 1.7 + Math.cos(back) * r * 0.5;
        const ty = s.y + Math.sin(a0 + side * -0.4) * r * 1.7 + Math.sin(back) * r * 0.5;
        cx.beginPath(); cx.moveTo(bx + Math.cos(s.a) * r * 0.3, by + Math.sin(s.a) * r * 0.3);
        cx.lineTo(tx, ty); cx.lineTo(bx - Math.cos(s.a) * r * 0.3, by - Math.sin(s.a) * r * 0.3); cx.fill();
        cx.strokeStyle = pal.leg; cx.globalAlpha = 0.6; cx.lineWidth = 0.8; cx.stroke(); cx.globalAlpha = 1;
      }
    } else if (st.back === "stripe" && i > 0) {
      cx.strokeStyle = pal.hot; cx.globalAlpha = 0.7; cx.lineWidth = Math.max(1, r * 0.35);
      cx.beginPath(); cx.moveTo(s.x + Math.cos(s.a) * r * 0.6, s.y + Math.sin(s.a) * r * 0.6);
      cx.lineTo(s.x - Math.cos(s.a) * r * 0.6, s.y - Math.sin(s.a) * r * 0.6); cx.stroke(); cx.globalAlpha = 1;
    }
    if (i > 0 && st.back !== "plates") {
      cx.strokeStyle = pal.crust; cx.globalAlpha = 0.9; cx.lineWidth = 1.2;
      cx.beginPath();
      cx.moveTo(s.x + Math.cos(s.a + 1.57) * r * 0.9, s.y + Math.sin(s.a + 1.57) * r * 0.9);
      cx.lineTo(s.x + Math.cos(s.a - 1.57) * r * 0.9, s.y + Math.sin(s.a - 1.57) * r * 0.9);
      cx.stroke(); cx.globalAlpha = 1;
    }
  }

  function drawHead(b) {
    const { pal, st, segs, radii } = b, h = segs[0], r = radii[0], fa = h.a;
    for (const side of [-1, 1]) {
      const open = 0.35 + b.jaw * 0.55, J = st.jaw * st.size;
      const bx = h.x + Math.cos(fa + side * 0.5) * r * 0.85, by = h.y + Math.sin(fa + side * 0.5) * r * 0.85;
      const tx = bx + Math.cos(fa + side * open) * J, ty = by + Math.sin(fa + side * open) * J;
      const ex = tx + Math.cos(fa - side * 0.9) * J * 0.55, ey = ty + Math.sin(fa - side * 0.9) * J * 0.55;
      cx.strokeStyle = pal.crust; cx.lineWidth = 3;
      cx.beginPath(); cx.moveTo(bx, by); cx.lineTo(tx, ty); cx.lineTo(ex, ey); cx.stroke();
      cx.strokeStyle = pal.leg; cx.lineWidth = 1;
      cx.beginPath(); cx.moveTo(bx, by); cx.lineTo(tx, ty); cx.lineTo(ex, ey); cx.stroke();
      // Antennae: flutter fast while greeting.
      const sway = Math.sin(t * (0.2 + b.wiggle * 1.4) + side + b.n) * (0.25 + b.wiggle * 0.35);
      const A = st.antenna * st.size;
      const ax0 = h.x + Math.cos(fa + side * 0.9) * r * 0.7, ay0 = h.y + Math.sin(fa + side * 0.9) * r * 0.7;
      const ax1 = ax0 + Math.cos(fa + side * 0.55 + sway) * A, ay1 = ay0 + Math.sin(fa + side * 0.55 + sway) * A;
      const ax2 = ax1 + Math.cos(fa + side * 0.85 + sway * 1.6) * A * 0.7, ay2 = ay1 + Math.sin(fa + side * 0.85 + sway * 1.6) * A * 0.7;
      cx.strokeStyle = pal.leg; cx.globalAlpha = 0.85; cx.lineWidth = 1;
      cx.beginPath(); cx.moveTo(ax0, ay0); cx.quadraticCurveTo(ax1, ay1, ax2, ay2); cx.stroke(); cx.globalAlpha = 1;
      cx.fillStyle = pal.hot; cx.beginPath(); cx.arc(ax2, ay2, 1.3, 0, 6.283); cx.fill();
      const exx = h.x + Math.cos(fa + side * 0.55) * r * 0.55, eyy = h.y + Math.sin(fa + side * 0.55) * r * 0.55;
      cx.fillStyle = pal.crust; cx.beginPath(); cx.arc(exx, eyy, 2.6 * Math.min(1.2, st.size), 0, 6.283); cx.fill();
      cx.fillStyle = pal.eye; cx.beginPath(); cx.arc(exx + Math.cos(fa) * 0.8, eyy + Math.sin(fa) * 0.8, 1.2, 0, 6.283); cx.fill();
    }
  }

  window.LavaBug = {
    add,                                   // one more bug (up to 20); returns how many there are
    clear: stop,                           // what Esc does
    get count() { return bugs.length; },
    get on() { return alive; },
  };
})();
