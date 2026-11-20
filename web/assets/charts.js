/* Sudakaos LATAM · gráficos ilustrativos animados (canvas 2D, sin dependencias).
   Todos los datos son simulados con una semilla fija: muestran el tipo de lectura, no resultados reales. */
(function () {
  'use strict';
  var RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
  // Paleta nocturna: "INK" es el trazo principal (claro sobre negro)
  var INK = '#0c0c0b', RED = '#d0213a', MUTED = '#77756e', LINE = '#e2e1dc', SOFT = '#f1f0ec', PAPER = '#ffffff', G1 = '#6d6b65', G2 = '#a3a19a', G3 = '#cfcdc6';
  var SANS = '"Schibsted Grotesk",Arial,Helvetica,sans-serif';
  var TAU = Math.PI * 2;

  function rng(seed) { var s = seed >>> 0; return function () { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
  function noise(seed) { // ruido suave 1D por interpolación de valores
    var r = rng(seed), v = []; for (var i = 0; i < 512; i++) v.push(r());
    return function (x) { var i = Math.floor(x), f = x - i, a = v[((i % 512) + 512) % 512], b = v[(((i + 1) % 512) + 512) % 512]; f = f * f * (3 - 2 * f); return a + (b - a) * f; };
  }
  function ease(x) { x = Math.max(0, Math.min(1, x)); return 1 - Math.pow(1 - x, 3); }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function alpha(hex, a) { var n = parseInt(hex.slice(1), 16); return 'rgba(' + (n >> 16) + ',' + (n >> 8 & 255) + ',' + (n & 255) + ',' + a + ')'; }
  function txt(g, s, x, y, o) { o = o || {}; g.font = (o.w || 400) + ' ' + ((o.s || 10) + 1) + 'px ' + (o.f || SANS); g.fillStyle = o.c || MUTED; g.textAlign = o.a || 'left'; g.textBaseline = o.b || 'alphabetic'; g.fillText(o.up ? String(s).toUpperCase() : s, x, y); }

  // Montaje común: tamaño con DPR, animación solo en pantalla, cuadro final si se reduce el movimiento
  function mount(cv, draw) {
    var g = cv.getContext('2d'), W = 0, H = 0, t0 = 0, vis = false, raf = 0, started = false, st = {};
    function size() { var d = Math.min(devicePixelRatio || 1, 2); W = cv.clientWidth; H = cv.clientHeight; cv.width = W * d; cv.height = H * d; g.setTransform(d, 0, 0, d, 0, 0); }
    function frame(now) { raf = 0; if (!started) { started = true; t0 = now; } var t = (now - t0) / 1000; g.clearRect(0, 0, W, H); draw(g, W, H, RM ? 60 : t, st); if (vis && !RM && !document.hidden) raf = requestAnimationFrame(frame); }
    function kick() { if (!raf) raf = requestAnimationFrame(frame); }
    size();
    addEventListener('resize', function () { size(); kick(); });
    new IntersectionObserver(function (es) { vis = es[0].isIntersecting; if (vis) kick(); }, { rootMargin: '80px' }).observe(cv);
    document.addEventListener('visibilitychange', kick);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(kick);
  }

  function axes(g, x0, y0, x1, y1, ticks, label) {
    g.strokeStyle = LINE; g.lineWidth = 1; g.beginPath();
    for (var i = 0; i <= ticks; i++) { var y = Math.round(lerp(y1, y0, i / ticks)) + .5; g.moveTo(x0, y); g.lineTo(x1, y); }
    g.stroke();
    if (label) txt(g, label, x0, y0 - 10);
  }

  var C = {};

  /* 01 · Inteligencia: flujo de menciones por fuente (streamgraph que avanza en el tiempo) */
  C.stream = function (g, W, H, t) {
    var src = ['Medios', 'Video', 'Búsquedas', 'Foros', 'Comentarios'], cols = [INK, RED, G1, G2, G3];
    var ns = src.map(function (_, i) { return noise(11 + i * 7); });
    var L = 46, R = W - (W < 600 ? 16 : 150), T = 34, B = H - 34, n = 90, sp = t * .9;
    var reveal = ease(t / 2.4);
    axes(g, L, T, R, B, 4, 'Menciones por hora · por fuente');
    var layers = [], base = [];
    for (var k = 0; k <= n; k++) {
      var x = (k + sp) / 6, spike = Math.exp(-Math.pow(((k + sp) % 140) - 70, 2) / 18) * 1.6;
      var col = [], sum = 0;
      for (var i = 0; i < src.length; i++) { var v = (.25 + ns[i](x + i * 3)) * (i === 1 ? 1 + spike * 1.4 : i === 0 ? 1 + spike * .6 : 1); col.push(v); sum += v; }
      layers.push(col); base.push(sum);
    }
    var max = 0; base.forEach(function (s) { max = Math.max(max, s); }); max = Math.max(max, 4.2);
    var mid = (T + B) / 2, sc = (B - T) / max * .92;
    for (var i = src.length - 1; i >= 0; i--) {
      g.beginPath();
      for (var k = 0; k <= n; k++) { var x = L + (R - L) * k / n, acc = -base[k] / 2; for (var j = 0; j < i; j++) acc += layers[k][j]; var y = mid + acc * sc; if (x > L + (R - L) * reveal) break; k ? g.lineTo(x, y) : g.moveTo(x, y); }
      for (var k = Math.min(n, Math.floor(n * reveal)); k >= 0; k--) { var x = L + (R - L) * k / n, acc = -base[k] / 2; for (var j = 0; j <= i; j++) acc += layers[k][j]; g.lineTo(x, mid + acc * sc); }
      g.closePath(); g.fillStyle = cols[i]; g.globalAlpha = i === 1 ? .9 : .82; g.fill(); g.globalAlpha = 1;
    }
    // Marcador de pico
    var pk = 0, pv = 0; for (var k = 0; k <= n * reveal; k++) if (layers[k][1] > pv) { pv = layers[k][1]; pk = k; }
    if (pv > 1.6) {
      var px = L + (R - L) * pk / n;
      g.strokeStyle = RED; g.setLineDash([3, 3]); g.beginPath(); g.moveTo(px + .5, T); g.lineTo(px + .5, B); g.stroke(); g.setLineDash([]);
      g.fillStyle = RED; g.fillRect(px - 1, T - 4, 2, 8);
      txt(g, 'Pico en video · revisar', px + 6, T + 6, { c: RED });
    }
    // Leyenda
    if (W >= 600) src.forEach(function (s, i) { var y = T + 10 + i * 20; g.fillStyle = cols[i]; g.fillRect(R + 18, y - 7, 10, 10); txt(g, s, R + 34, y + 2, { c: INK }); });
    txt(g, '−24 h', L, B + 20); txt(g, 'ahora', R, B + 20, { a: 'right' });
  };

  /* 01 · Inteligencia: depuración de datos (partículas que se filtran por etapas) */
  C.funnel = function (g, W, H, t, st) {
    var stages = ['Recolectado', 'Sin duplicados', 'Validado', 'En informe'], keep = [1, .62, .41, .18];
    var L = 24, R = W - 24, T = 40, B = H - 40, n = stages.length, w = (R - L) / n;
    if (!st.p) { var r = rng(5); st.r = r; st.p = []; for (var i = 0; i < 260; i++) st.p.push({ y: r(), o: r() * 4, s: .5 + r() * .5, k: r() }); }
    for (var i = 0; i < n; i++) {
      var x = L + i * w, hh = (B - T) * keep[i], y = (T + B) / 2 - hh / 2;
      g.fillStyle = i === n - 1 ? alpha(RED, .07) : SOFT; g.fillRect(x + 2, y, w - 4, hh);
      g.strokeStyle = i === n - 1 ? RED : LINE; g.strokeRect(x + 2.5, y + .5, w - 5, hh - 1);
      txt(g, String(i + 1).padStart(2, '0') + ' ' + stages[i], x + 8, T - 14, { c: i === n - 1 ? RED : INK, s: W < 600 ? 8 : 10 });
      txt(g, Math.round(keep[i] * 100) + '%', x + 8, B + 22, { c: MUTED, s: 9 });
    }
    st.p.forEach(function (p) {
      var pos = ((t * .55 * p.s + p.o) % 4.4), si = Math.floor(pos), f = pos - si; if (si >= n) return;
      if (p.k >= keep[si]) return; // ya descartado en una etapa anterior
      if (si < n - 1 && p.k >= keep[si + 1] && f > .75) return; // se descarta al cruzar
      var x = L + (si + f) * w, hh = (B - T) * lerp(keep[si], keep[Math.min(n - 1, si + 1)], ease((f - .75) * 4)), y = (T + B) / 2 + (p.y - .5) * hh * .9;
      g.fillStyle = si === n - 1 ? RED : INK; g.globalAlpha = .75; g.fillRect(x, y, 2.2, 2.2); g.globalAlpha = 1;
    });
  };

  /* 02 · Prospectiva: abanico de escenarios con umbral de alerta temprana */
  C.fan = function (g, W, H, t, st) {
    var L = 46, R = W - (W < 600 ? 16 : 120), T = 30, B = H - 34, nowX = L + (R - L) * .42;
    if (!st.paths) {
      var r = rng(9), hist = [], v = .45; for (var i = 0; i < 40; i++) { v += (r() - .5) * .05; hist.push(v); } st.hist = hist; st.paths = [];
      for (var p = 0; p < 46; p++) { var y = v, path = [], drift = (r() - .5) * .012; for (var i = 0; i < 56; i++) { y += drift + (r() - .5) * .04; y = Math.max(.04, Math.min(.96, y)); path.push(y); } st.paths.push(path); }
      st.paths.sort(function (a, b) { return a[55] - b[55]; });
    }
    axes(g, L, T, R, B, 4, 'Índice de tensión de agenda (simulado)');
    var Y = function (v) { return B - (B - T) * v; }, thr = .78;
    g.strokeStyle = INK; g.lineWidth = 1.6; g.beginPath(); st.hist.forEach(function (v, i) { var x = L + (nowX - L) * i / 39; i ? g.lineTo(x, Y(v)) : g.moveTo(x, Y(v)); }); g.stroke(); g.lineWidth = 1;
    var rv = ease((t - .4) / 2.6), m = Math.floor(55 * rv) + 1, N = st.paths.length;
    // Bandas de percentiles
    [[.1, .9, .07], [.25, .75, .12]].forEach(function (b) {
      var lo = st.paths[Math.floor(N * b[0])], hi = st.paths[Math.floor(N * b[1])];
      g.beginPath(); for (var i = 0; i < m; i++) { var x = lerp(nowX, R, i / 55); g.lineTo(x, Y(Math.max(lo[i], .0))); }
      for (var i = m - 1; i >= 0; i--) { var x = lerp(nowX, R, i / 55); g.lineTo(x, Y(hi[i])); }
      g.closePath(); g.fillStyle = alpha(INK, b[2]); g.fill();
    });
    st.paths.forEach(function (p, k) {
      g.beginPath(); g.moveTo(nowX, Y(st.hist[39]));
      for (var i = 0; i < m; i++) g.lineTo(lerp(nowX, R, i / 55), Y(p[i]));
      g.strokeStyle = p[Math.min(m - 1, 55)] > thr ? alpha(RED, .5) : alpha(INK, .12); g.stroke();
    });
    var named = [[N - 3, 'Tensión', RED], [Math.floor(N / 2), 'Base', INK], [2, 'Distensión', G1]];
    named.forEach(function (nm) { var p = st.paths[nm[0]]; g.beginPath(); g.moveTo(nowX, Y(st.hist[39])); for (var i = 0; i < m; i++) g.lineTo(lerp(nowX, R, i / 55), Y(p[i])); g.strokeStyle = nm[2]; g.lineWidth = 2; g.stroke(); g.lineWidth = 1; if (rv > .98 && W >= 600) txt(g, nm[1], R + 8, Y(p[55]) + 3, { c: nm[2], s: 10 }); });
    g.strokeStyle = RED; g.setLineDash([5, 4]); g.beginPath(); g.moveTo(L, Y(thr) + .5); g.lineTo(R, Y(thr) + .5); g.stroke(); g.setLineDash([]);
    txt(g, 'Umbral de alerta', L + 4, Y(thr) - 6, { c: RED, s: 9 });
    g.strokeStyle = INK; g.beginPath(); g.moveTo(nowX + .5, T); g.lineTo(nowX + .5, B); g.stroke(); txt(g, 'Hoy', nowX + 6, T + 10, { c: INK });
    txt(g, 'Historia', L, B + 20); txt(g, '+90 días', R, B + 20, { a: 'right' });
  };

  /* 02 · Prospectiva: matriz de escenarios con señales que se desplazan */
  C.matrix = function (g, W, H, t, st) {
    var pad = W < 600 ? 34 : 54, L = pad, R = W - 18, T = 20, B = H - 34, cx = (L + R) / 2, cy = (T + B) / 2;
    var q = [['Fragmentación', L + 10, T + 22], ['Disputa abierta', cx + 10, T + 22], ['Estabilidad', L + 10, cy + 22], ['Agenda dominante', cx + 10, cy + 22]];
    g.fillStyle = alpha(RED, .05); g.fillRect(cx, T, R - cx, cy - T);
    g.strokeStyle = LINE; g.strokeRect(L + .5, T + .5, R - L, B - T); g.beginPath(); g.moveTo(cx + .5, T); g.lineTo(cx + .5, B); g.moveTo(L, cy + .5); g.lineTo(R, cy + .5); g.stroke();
    q.forEach(function (a, i) { txt(g, a[0], a[1], a[2], { c: i === 1 ? RED : INK, s: W < 600 ? 8 : 10 }); });
    txt(g, 'Intensidad de agenda →', R, B + 22, { a: 'right' });
    g.save(); g.translate(L - 14, B); g.rotate(-Math.PI / 2); txt(g, 'Cohesión de actores →', 0, 0); g.restore();
    if (!st.s) { var r = rng(21); st.s = []; for (var i = 0; i < 14; i++) st.s.push({ x: r(), y: r(), a: r() * TAU, sp: .05 + r() * .08, hot: i < 3 }); }
    st.s.forEach(function (s, i) {
      var trail = 18;
      for (var k = trail; k >= 0; k--) {
        var tt = t - k * .12, x = .5 + (s.x - .5) * .8 + Math.sin(tt * s.sp * 3 + s.a) * .14 + (s.hot ? Math.min(.25, tt * .02) : 0), y = .5 + (s.y - .5) * .8 + Math.cos(tt * s.sp * 2.3 + s.a) * .12 + (s.hot ? Math.min(.2, tt * .016) : 0);
        x = Math.max(.03, Math.min(.97, x)); y = Math.max(.05, Math.min(.95, y));
        var px = L + (R - L) * x, py = B - (B - T) * y;
        if (k === 0) { g.fillStyle = s.hot ? RED : INK; g.beginPath(); g.arc(px, py, s.hot ? 4 : 3, 0, TAU); g.fill(); if (s.hot) { g.strokeStyle = alpha(RED, .4); g.beginPath(); g.arc(px, py, 4 + (t * 8 % 12), 0, TAU); g.stroke(); } }
        else { g.fillStyle = alpha(s.hot ? RED : INK, .12 * (1 - k / trail)); g.fillRect(px - 1, py - 1, 2, 2); }
      }
    });
  };

  /* 03 · Comunicación: red de narrativas y actores (fuerzas) con pulsos */
  C.network = function (g, W, H, t, st) {
    if (!st.n || st.W !== W || st.H !== H) {
      var r = rng(33); st.W = W; st.H = H; st.n = []; st.e = [];
      var hubs = ['Economía', 'Seguridad', 'Gestión', 'Transparencia', 'Territorio'];
      hubs.forEach(function (h, i) { var a = i / hubs.length * TAU; st.n.push({ x: W / 2 + Math.cos(a) * W * .22, y: H / 2 + Math.sin(a) * H * .26, vx: 0, vy: 0, hub: true, label: h, c: i === 0 ? RED : INK }); });
      for (var i = 0; i < 70; i++) { var h = Math.floor(r() * hubs.length); st.n.push({ x: st.n[h].x + (r() - .5) * 80, y: st.n[h].y + (r() - .5) * 80, vx: 0, vy: 0, hub: false, h: h, c: h === 0 ? RED : INK }); st.e.push([h, st.n.length - 1]); if (r() < .18) st.e.push([Math.floor(r() * hubs.length), st.n.length - 1]); }
      for (var i = 0; i < hubs.length; i++) st.e.push([i, (i + 1) % hubs.length]);
      st.p = []; for (var i = 0; i < 26; i++) st.p.push({ e: Math.floor(r() * st.e.length), o: r() });
    }
    var N = st.n, E = st.e, steps = RM ? 200 : 2;
    for (var s = 0; s < steps; s++) {
      for (var i = 0; i < N.length; i++) for (var j = i + 1; j < N.length; j++) { var a = N[i], b = N[j], dx = a.x - b.x, dy = a.y - b.y, d2 = dx * dx + dy * dy + 30, f = (a.hub && b.hub ? 2600 : 260) / d2; a.vx += dx * f * .02; a.vy += dy * f * .02; b.vx -= dx * f * .02; b.vy -= dy * f * .02; }
      E.forEach(function (e) { var a = N[e[0]], b = N[e[1]], dx = b.x - a.x, dy = b.y - a.y, d = Math.sqrt(dx * dx + dy * dy) || 1, k = (d - (a.hub && b.hub ? Math.min(W, H) * .42 : 46)) * .004; a.vx += dx / d * k * 4; a.vy += dy / d * k * 4; b.vx -= dx / d * k * 4; b.vy -= dy / d * k * 4; });
      N.forEach(function (n, i) { n.vx += (W / 2 - n.x) * .0008 + Math.sin(t * .4 + i) * .01; n.vy += (H / 2 - n.y) * .0012 + Math.cos(t * .37 + i) * .01; n.vx *= .82; n.vy *= .82; n.x = Math.max(12, Math.min(W - 12, n.x + n.vx)); n.y = Math.max(16, Math.min(H - 16, n.y + n.vy)); });
    }
    g.lineWidth = 1; E.forEach(function (e) { var a = N[e[0]], b = N[e[1]]; g.strokeStyle = a.hub && b.hub ? alpha(INK, .35) : alpha(a.c === RED ? RED : INK, .14); g.beginPath(); g.moveTo(a.x, a.y); g.lineTo(b.x, b.y); g.stroke(); });
    st.p.forEach(function (p) { var e = E[p.e], a = N[e[0]], b = N[e[1]], f = (t * .5 + p.o) % 1; g.fillStyle = a.c === RED ? RED : INK; g.beginPath(); g.arc(lerp(b.x, a.x, f), lerp(b.y, a.y, f), 1.8, 0, TAU); g.fill(); });
    N.forEach(function (n) { if (n.hub) return; g.fillStyle = n.c === RED ? RED : G1; g.beginPath(); g.arc(n.x, n.y, 2.6, 0, TAU); g.fill(); });
    N.forEach(function (n) { if (!n.hub) return; g.fillStyle = PAPER; g.strokeStyle = n.c; g.lineWidth = 1.5; g.beginPath(); g.arc(n.x, n.y, 9, 0, TAU); g.fill(); g.stroke(); g.lineWidth = 1; g.fillStyle = n.c; g.beginPath(); g.arc(n.x, n.y, 3.5, 0, TAU); g.fill(); txt(g, n.label, n.x + 14, n.y + 4, { c: n.c, s: 10, w: 700 }); });
  };

  /* 03 · Comunicación: curvas de atención de piezas en 72 h */
  C.decay = function (g, W, H, t, st) {
    var L = 46, R = W - 18, T = 30, B = H - 34;
    axes(g, L, T, R, B, 4, 'Atención por pieza · primeras 72 h');
    if (!st.c) { var r = rng(44); st.c = []; for (var i = 0; i < 16; i++) st.c.push({ a: .3 + r() * .7, k: .08 + r() * .12, d: r() * 6, s: r() < .2 ? 1.6 : 0 }); }
    var rv = ease(t / 3), n = 72;
    var f = function (c, h) { var x = Math.max(0, h - c.d); return c.a * (x / 3) * Math.exp(-c.k * x) * 2.2 + (c.s ? c.s * .8 * Math.exp(-Math.pow(h - 40, 2) / 30) : 0); };
    if (!st.mx) { st.mx = 0; st.c.forEach(function (c) { for (var h = 0; h <= n; h++) st.mx = Math.max(st.mx, f(c, h)); }); st.mx *= 1.08; }
    var Y = function (v) { return B - (B - T) * Math.min(1, v / st.mx); };
    st.c.forEach(function (c, i) { g.beginPath(); for (var h = 0; h <= n * rv; h++) { var x = L + (R - L) * h / n; h ? g.lineTo(x, Y(f(c, h))) : g.moveTo(x, Y(f(c, h))); } g.strokeStyle = c.s ? alpha(RED, .85) : alpha(INK, .18); g.lineWidth = c.s ? 1.6 : 1; g.stroke(); });
    g.beginPath(); for (var h = 0; h <= n * rv; h++) { var vs = st.c.map(function (c) { return f(c, h); }).sort(function (a, b) { return a - b; }); var x = L + (R - L) * h / n; h ? g.lineTo(x, Y(vs[8])) : g.moveTo(x, Y(vs[8])); }
    g.strokeStyle = INK; g.lineWidth = 2.2; g.stroke(); g.lineWidth = 1;
    if (rv > .6) { var mh = 14, vs0 = st.c.map(function (c) { return f(c, mh); }).sort(function (a, b) { return a - b; }); txt(g, 'Mediana', L + (R - L) * mh / n + 8, Y(vs0[8]) - 8, { c: INK, w: 700 }); }
    if (rv > .65) txt(g, 'Segundo pico: la pieza se recupera en otro canal', L + (R - L) * .5, T + 12, { c: RED, s: 9 });
    [0, 24, 48, 72].forEach(function (h) { txt(g, h + ' h', L + (R - L) * h / 72, B + 20, { a: h ? (h === 72 ? 'right' : 'center') : 'left' }); });
  };

  /* 04 · Sistemas: flujo de trabajo (sankey con partículas) */
  C.sankey = function (g, W, H, t, st) {
    var cols = [['Formularios', 'Territorio', 'Redes', 'Llamadas'], ['Clasificación', 'Asignación', 'Verificación'], ['Equipos', 'Reportes', 'Archivo']];
    var flows = [[0, 0, 0, 3], [0, 1, 1, 3], [0, 1, 0, 1], [0, 2, 2, 3], [0, 2, 0, 2], [0, 3, 1, 2], [1, 0, 0, 4], [1, 0, 2, 2], [1, 1, 0, 4], [1, 1, 1, 1], [1, 2, 1, 2], [1, 2, 2, 1]];
    var small = W < 600, L = small ? 8 : 20, R = W - (small ? 8 : 20), T = 30, B = H - 16, cw = small ? 8 : 12, gap = 14;
    var xs = [L, (L + R) / 2 - cw / 2, R - cw];
    var val = [[0, 0, 0, 0], [0, 0, 0], [0, 0, 0]];
    flows.forEach(function (f) { if (f[0] === 0) val[0][f[1]] += f[3]; val[f[0] + 1][f[2]] += f[3]; });
    var sum = val[0].reduce(function (a, b) { return a + b; }, 0), sc = (B - T - gap * 3) / sum;
    var pos = val.map(function (vs) { var y = T, o = []; vs.forEach(function (v) { o.push({ y: y, h: v * sc, oo: 0, oi: 0 }); y += v * sc + gap; }); var off = (B - y + gap) / 2; o.forEach(function (p) { p.y += off; }); return o; });
    var rv = ease(t / 2);
    if (!st.p) { var r = rng(77); st.p = []; for (var i = 0; i < 160; i++) st.p.push({ f: Math.floor(r() * flows.length), o: r(), y: r() }); }
    var geo = flows.map(function (f) { var c = f[0], a = pos[c][f[1]], b = pos[c + 1][f[2]], h = f[3] * sc; var y0 = a.y + a.oo, y1 = b.y + b.oi; a.oo += h; b.oi += h; return { x0: xs[c] + cw, x1: xs[c + 1], y0: y0, y1: y1, h: h, hot: c === 0 && f[1] === 1 }; });
    geo.forEach(function (q) {
      var mx = (q.x0 + q.x1) / 2, x1 = lerp(q.x0, q.x1, rv);
      g.beginPath(); g.moveTo(q.x0, q.y0); g.bezierCurveTo(mx, q.y0, mx, q.y1, q.x1, q.y1); g.lineTo(q.x1, q.y1 + q.h); g.bezierCurveTo(mx, q.y1 + q.h, mx, q.y0 + q.h, q.x0, q.y0 + q.h); g.closePath();
      g.save(); g.beginPath(); g.rect(0, 0, x1, H); g.clip(); g.beginPath(); g.moveTo(q.x0, q.y0); g.bezierCurveTo(mx, q.y0, mx, q.y1, q.x1, q.y1); g.lineTo(q.x1, q.y1 + q.h); g.bezierCurveTo(mx, q.y1 + q.h, mx, q.y0 + q.h, q.x0, q.y0 + q.h); g.closePath();
      g.fillStyle = q.hot ? alpha(RED, .22) : alpha(INK, .08); g.fill(); g.restore();
    });
    if (rv > .99) st.p.forEach(function (p) {
      var q = geo[p.f], f = (t * .22 + p.o) % 1, mx = (q.x0 + q.x1) / 2, u = 1 - f;
      var x = u * u * u * q.x0 + 3 * u * u * f * mx + 3 * u * f * f * mx + f * f * f * q.x1, yy = u * u * u * q.y0 + 3 * u * u * f * q.y0 + 3 * u * f * f * q.y1 + f * f * f * q.y1;
      g.fillStyle = q.hot ? RED : INK; g.globalAlpha = .7; g.fillRect(x, yy + p.y * q.h, 2, 2); g.globalAlpha = 1;
    });
    pos.forEach(function (c, ci) { c.forEach(function (p, i) { g.fillStyle = ci === 0 && i === 1 ? RED : INK; g.fillRect(xs[ci], p.y, cw, p.h); var lab = cols[ci][i], al = ci === 2 ? 'right' : 'left', lx = ci === 2 ? xs[ci] - 6 : xs[ci] + cw + 6; if (ci === 1) { al = 'center'; lx = xs[1] + cw / 2; txt(g, lab, lx, p.y - 6, { c: INK, a: al, s: small ? 8 : 10 }); } else txt(g, lab, lx, p.y + p.h / 2 + 3, { c: ci === 0 && i === 1 ? RED : INK, a: al, s: small ? 8 : 10 }); }); });
  };

  /* 04 · Sistemas: diagrama de flujo acumulado de tareas */
  C.cfd = function (g, W, H, t) {
    var L = 46, R = W - (W < 600 ? 16 : 110), T = 30, B = H - 34, n = 42;
    axes(g, L, T, R, B, 4, 'Tareas acumuladas por estado');
    var rv = ease(t / 3), m = Math.max(1, Math.floor(n * rv));
    var nz = noise(91), done = [], doing = [], todo = [], a = 0, b = 0, c = 0;
    for (var i = 0; i <= n; i++) { a += 2 + nz(i * .4) * 2.4; b = Math.min(a, b + 1.8 + nz(i * .3 + 5) * 2.2); c = Math.min(b, c + (i > 6 ? 1.9 + nz(i * .5 + 9) * 1.9 : .3)); todo.push(a); doing.push(b); done.push(c); }
    var max = todo[n] * 1.05, X = function (i) { return L + (R - L) * i / n; }, Y = function (v) { return B - (B - T) * v / max; };
    [[todo, G3, 'Pendiente'], [doing, G2, 'En curso'], [done, INK, 'Resuelto']].forEach(function (s, k) {
      g.beginPath(); g.moveTo(X(0), B); for (var i = 0; i <= m; i++) g.lineTo(X(i), Y(s[0][i])); g.lineTo(X(m), B); g.closePath(); g.fillStyle = s[1]; g.fill();
      if (W >= 600 && rv > .98) txt(g, s[2], R + 10, Y(k === 0 ? (todo[n] + doing[n]) / 2 : k === 1 ? (doing[n] + done[n]) / 2 : done[n] / 2) + 3, { c: k === 2 ? INK : G1 });
    });
    var x = X(m); g.strokeStyle = RED; g.beginPath(); g.moveTo(x + .5, T); g.lineTo(x + .5, B); g.stroke();
    var wip = Math.round(todo[m] - done[m]); txt(g, 'Trabajo abierto: ' + wip, x - 6, T + 10, { c: RED, a: 'right' });
    txt(g, 'Semana 1', L, B + 20); txt(g, 'Semana 6', R, B + 20, { a: 'right' });
  };

  /* 05 · Ciberseguridad: radar de exposición antes / después */
  C.radar = function (g, W, H, t) {
    var dims = ['Credenciales', 'Correo', 'Dominios', 'Dispositivos', 'Accesos', 'Respaldos', 'Proveedores', 'Personas'];
    var before = [.82, .7, .55, .74, .88, .62, .66, .8], after = [.34, .3, .28, .4, .32, .22, .45, .38];
    var cx = W / 2, cy = H / 2 + 6, R = Math.min(W, H) * .36, n = dims.length;
    for (var k = 1; k <= 4; k++) { g.strokeStyle = LINE; g.beginPath(); for (var i = 0; i <= n; i++) { var a = i / n * TAU - Math.PI / 2, r = R * k / 4; i ? g.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r) : g.moveTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r); } g.stroke(); }
    dims.forEach(function (d, i) { var a = i / n * TAU - Math.PI / 2; g.strokeStyle = LINE; g.beginPath(); g.moveTo(cx, cy); g.lineTo(cx + Math.cos(a) * R, cy + Math.sin(a) * R); g.stroke(); var ca = Math.cos(a); txt(g, d, cx + ca * (R + 12), cy + Math.sin(a) * (R + 12) + 3, { c: INK, a: Math.abs(ca) < .2 ? 'center' : ca > 0 ? 'left' : 'right', s: W < 600 ? 8 : 10 }); });
    var cyc = RM ? 1 : (Math.sin(t * .5 - Math.PI / 2) + 1) / 2, k = ease(Math.min(1, cyc * 1.15));
    function poly(vals, fill, stroke, lw) { g.beginPath(); vals.forEach(function (v, i) { var a = i / n * TAU - Math.PI / 2; i ? g.lineTo(cx + Math.cos(a) * R * v, cy + Math.sin(a) * R * v) : g.moveTo(cx + Math.cos(a) * R * v, cy + Math.sin(a) * R * v); }); g.closePath(); if (fill) { g.fillStyle = fill; g.fill(); } g.strokeStyle = stroke; g.lineWidth = lw; g.stroke(); g.lineWidth = 1; }
    poly(before, null, alpha(INK, .35), 1);
    var cur = before.map(function (v, i) { return lerp(v, after[i], k); });
    poly(cur, alpha(RED, .14), RED, 2);
    cur.forEach(function (v, i) { var a = i / n * TAU - Math.PI / 2; g.fillStyle = RED; g.beginPath(); g.arc(cx + Math.cos(a) * R * v, cy + Math.sin(a) * R * v, 3, 0, TAU); g.fill(); });
    if (!RM) { var sa = t * 1.2 % TAU - Math.PI / 2; var gr = g.createRadialGradient(cx, cy, 0, cx, cy, R); gr.addColorStop(0, alpha(RED, 0)); gr.addColorStop(1, alpha(RED, .25)); g.strokeStyle = gr; g.beginPath(); g.moveTo(cx, cy); g.lineTo(cx + Math.cos(sa) * R, cy + Math.sin(sa) * R); g.stroke(); }
    txt(g, k > .5 ? 'Después de controles' : 'Diagnóstico inicial', 16, 20, { c: k > .5 ? RED : INK, w: 700 });
    txt(g, '— línea gris: diagnóstico inicial', 16, 36, { s: 9 });
  };

  /* 05 · Ciberseguridad: cronograma de respuesta a incidentes */
  C.gantt = function (g, W, H, t) {
    var rows = [['Detección', 0, 2], ['Contención', 1.5, 5], ['Análisis técnico', 2.5, 10], ['Comunicación', 3, 12], ['Recuperación', 6, 16], ['Lecciones aprendidas', 14, 20]];
    var small = W < 600, L = small ? 112 : 170, R = W - 16, T = 30, B = H - 34, rh = (B - T) / rows.length, span = 20;
    var X = function (h) { return L + (R - L) * h / span; };
    g.strokeStyle = LINE; for (var h = 0; h <= span; h += 4) { g.beginPath(); g.moveTo(X(h) + .5, T - 6); g.lineTo(X(h) + .5, B); g.stroke(); txt(g, h + ' h', X(h), B + 20, { a: h === 0 ? 'left' : h === span ? 'right' : 'center' }); }
    txt(g, 'Horas desde la detección', L, T - 12);
    var ph = RM ? span : (t * 2.2) % (span + 6);
    rows.forEach(function (r, i) {
      var y = T + i * rh + rh * .28, h = rh * .44, x0 = X(r[1]), x1 = X(Math.min(r[2], Math.max(r[1], ph)));
      txt(g, r[0], L - 12, y + h / 2 + 3, { c: INK, a: 'right', s: small ? 8 : 10 });
      g.fillStyle = SOFT; g.fillRect(x0, y, X(r[2]) - x0, h);
      if (x1 > x0) { g.fillStyle = i === 3 ? RED : INK; g.fillRect(x0, y, x1 - x0, h); }
    });
    var px = X(Math.min(span, ph)); g.strokeStyle = RED; g.beginPath(); g.moveTo(px + .5, T - 6); g.lineTo(px + .5, B); g.stroke();
    g.fillStyle = RED; g.beginPath(); g.moveTo(px - 5, T - 12); g.lineTo(px + 5, T - 12); g.lineTo(px, T - 5); g.fill();
  };

  /* 06 · Comunidad: cobertura territorial (hexágonos que se activan) */
  C.hexmap = function (g, W, H, t, st) {
    var s = W < 600 ? 9 : 12, hw = Math.sqrt(3) * s, cols = Math.floor((W - 20) / hw), rows = Math.floor((H - 40) / (s * 1.5));
    if (!st.h || st.W !== W) {
      st.W = W; var r = rng(61), nz = noise(62); st.h = []; var seeds = [];
      for (var k = 0; k < 6; k++) seeds.push([r() * cols, r() * rows]);
      for (var j = 0; j < rows; j++) for (var i = 0; i < cols; i++) {
        var u = i / cols - .5, v = j / rows - .5, inside = (u * u) / .25 + (v * v) / .23 + (nz(i * .3 + j * .7) - .5) * .5 < 1; if (!inside) continue;
        var d = 1e9; seeds.forEach(function (sd) { d = Math.min(d, Math.hypot(sd[0] - i, sd[1] - j)); });
        st.h.push({ i: i, j: j, d: d + r() * 2, hub: d < .7 });
      }
    }
    var wave = RM ? 99 : (t * 3.2) % 34;
    st.h.forEach(function (c) {
      var x = 10 + hw / 2 + c.i * hw + (c.j % 2) * hw / 2, y = 24 + s + c.j * s * 1.5, on = c.d < wave, edge = on && c.d > wave - 1.5;
      g.beginPath(); for (var k = 0; k < 6; k++) { var a = Math.PI / 6 + k * Math.PI / 3; g.lineTo(x + Math.cos(a) * s * .9, y + Math.sin(a) * s * .9); } g.closePath();
      g.fillStyle = c.hub ? RED : edge ? alpha(RED, .55) : on ? alpha(INK, .78) : SOFT; g.fill();
    });
    var cov = st.h.filter(function (c) { return c.d < wave; }).length / st.h.length;
    txt(g, 'Cobertura de la red (simulada): ' + Math.round(Math.min(1, cov) * 100) + '%', 10, 14, { c: INK });
  };

  /* 06 · Comunidad: consultas recibidas por semana y cómo se resolvieron */
  C.bars = function (g, W, H, t) {
    var L = 46, R = W - (W < 600 ? 16 : 140), T = 30, B = H - 34, n = 12, nz = noise(71);
    axes(g, L, T, R, B, 4, 'Consultas por semana · resolución');
    var bw = (R - L) / n, keys = [['Resueltas en territorio', INK], ['Escaladas al equipo', RED], ['En seguimiento', G3]];
    for (var i = 0; i < n; i++) {
      var tot = 30 + i * 4 + nz(i * .7) * 18, sh = [.55 + i * .015, .22 - i * .006, .23 - i * .009], k = ease((t - i * .12) / .8), y = B;
      for (var j = 0; j < 3; j++) { var hh = (B - T) * (tot * sh[j]) / 100 * k; g.fillStyle = keys[j][1]; g.fillRect(L + i * bw + bw * .18, y - hh, bw * .64, hh); y -= hh + (hh > 0 ? 1 : 0); }
      txt(g, 'S' + (i + 1), L + i * bw + bw / 2, B + 18, { a: 'center', s: 9 });
    }
    if (W >= 600) keys.forEach(function (k, j) { var y = T + 10 + j * 20; g.fillStyle = k[1]; g.fillRect(R + 16, y - 8, 10, 10); txt(g, k[0], R + 32, y + 1, { c: INK, s: 9 }); });
  };

  document.querySelectorAll('canvas[data-chart]').forEach(function (cv) { var f = C[cv.getAttribute('data-chart')]; if (f) mount(cv, f); });
})();
