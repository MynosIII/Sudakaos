/* Sudakaos LATAM · tablero por país.
   Política (web/data/politica.json, curado a mano con fuente y fecha de cada encuesta) y datos públicos
   automáticos (web/data/paises.json y situacion.json: tipo de cambio, inflación, índice, alertas y titulares). Sin dependencias. */
(function () {
  'use strict';
  var ORDEN = ['AR', 'BO', 'BR', 'CL', 'CO', 'EC', 'GY', 'PY', 'PE', 'SR', 'UY', 'VE', 'MX', 'US', 'ES', 'GB', 'EU'];
  var css = getComputedStyle(document.documentElement);
  var INK = css.getPropertyValue('--ink').trim() || '#0c0c0b', RED = css.getPropertyValue('--red').trim() || '#d0213a',
    MUTED = css.getPropertyValue('--muted').trim() || '#75736c', LINE = css.getPropertyValue('--line').trim() || '#e2e1dc';
  var PAL = [INK, RED, '#2f6db3', '#9d9c94', '#c9861b'];
  var SANS = '"Schibsted Grotesk",Arial,sans-serif', MONO = 'ui-monospace,SFMono-Regular,Menlo,Consolas,monospace';
  var DATA = null, SIT = null, POL = null, FOT = {}, IMG = {}, CUR = 'AR', sortK = 'img', sortD = -1;
  var MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
  var $ = function (id) { return document.getElementById(id); };

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function num(n, d) { if (n == null || isNaN(n)) return '—'; d = d == null ? 1 : d; return Number(n).toLocaleString('es-AR', { maximumFractionDigits: d, minimumFractionDigits: d }); }
  function n0(n) { return n == null ? '—' : Number(n).toLocaleString('es-AR', { maximumFractionDigits: 1 }); }
  function last(s) { return s && s.length ? s[s.length - 1] : null; }
  function ago(t) { var m = Math.max(0, (Date.now() - Date.parse(t)) / 60000); return m < 60 ? 'hace ' + Math.round(m) + ' min' : m < 1440 ? 'hace ' + Math.round(m / 60) + ' h' : 'hace ' + Math.round(m / 1440) + ' d'; }
  function fecha(s) { if (!s) return ''; var p = String(s).split('-'); if (p.length === 1) return p[0]; if (p.length === 2) return MESES[+p[1] - 1] + ' ' + p[0]; return +p[2] + ' ' + MESES[+p[1] - 1] + ' ' + p[0]; }
  function fechaC(s) { var p = String(s).split('-'); return p.length === 3 ? +p[2] + ' ' + MESES[+p[1] - 1] : p.length === 2 ? MESES[+p[1] - 1] + ' ' + p[0].slice(2) : s; }
  function fxVar(s, days) { if (!s || s.length < 2) return null; var l = s[s.length - 1], t0 = Date.parse(l[0]) - days * 864e5, b = s[0]; s.forEach(function (r) { if (Date.parse(r[0]) <= t0) b = r; }); return b === l ? null : (l[1] / b[1] - 1) * 100; }
  function flag(c, w) { return '<img class="flag" src="https://flagcdn.com/w' + (w || 40) + '/' + c.toLowerCase() + '.png" alt="" loading="lazy">'; }
  function foto(n, cls) { var f = FOT[n]; return f ? '<img class="' + cls + '" src="' + esc(f.img) + '" alt="' + esc(n) + '" loading="lazy" referrerpolicy="no-referrer">' : '<span class="' + cls + ' ph">' + esc(n.split(' ').map(function (w) { return w[0]; }).slice(0, 2).join('')) + '</span>'; }
  function img(n) { var f = FOT[n]; if (!f) return null; if (!IMG[n]) { IMG[n] = new Image(); IMG[n].referrerPolicy = 'no-referrer'; IMG[n].onload = function () { clearTimeout(img.t); img.t = setTimeout(render, 60); }; IMG[n].src = f.img; } return IMG[n].complete && IMG[n].naturalWidth ? IMG[n] : null; }
  function pct(v) { return v == null ? '—' : (v >= 0 ? '+' : '') + num(v) + ' %'; }
  function sizeCv(cv) { var d = Math.min(devicePixelRatio || 1, 2), W = cv.clientWidth, H = cv.clientHeight; cv.width = W * d; cv.height = H * d; var g = cv.getContext('2d'); g.setTransform(d, 0, 0, d, 0, 0); g.clearRect(0, 0, W, H); return { g: g, W: W, H: H }; }

  // Promedio: última medición de cada encuestadora en los últimos 45 días.
  function promedio(P) {
    var cut = Date.now() - 45 * 864e5, vis = {}, usadas = [];
    (P.enc || []).slice().sort(function (a, b) { return a.fecha < b.fecha ? 1 : -1; }).forEach(function (e) {
      if (vis[e.f] || Date.parse(e.fecha) < cut || e.a == null) return; vis[e.f] = 1; usadas.push(e);
    });
    if (!usadas.length) return null;
    var a = 0, d = 0, nd = 0; usadas.forEach(function (e) { a += e.a; if (e.d != null) { d += e.d; nd++; } });
    return { a: a / usadas.length, d: nd ? d / nd : null, n: usadas.length, enc: usadas };
  }
  function tendencia(P) { // última variación de la serie más larga, en puntos
    var best = null; Object.keys(P.series || {}).forEach(function (k) { var s = P.series[k]; if (s.length > 1 && (!best || s.length > best.length)) best = s; });
    return best && !P.intencion ? best[best.length - 1][1] - best[best.length - 2][1] : null;
  }

  // ---------- Gráficos ----------
  function lines(cv, series, o) {
    o = o || {}; var c = sizeCv(cv), g = c.g, W = c.W, H = c.H, keys = Object.keys(series), all = [];
    keys.forEach(function (k) { series[k].forEach(function (r) { all.push([Date.parse(r[0]), r[1]]); }); });
    if (!all.length) return;
    var L = 34, R = 16, T = 18, B = 24;
    var x0 = Math.min.apply(null, all.map(function (r) { return r[0]; })), x1 = Math.max.apply(null, all.map(function (r) { return r[0]; }));
    if (x1 - x0 < 20 * 864e5) { x0 -= 10 * 864e5; x1 += 10 * 864e5; }
    var vs = all.map(function (r) { return r[1]; }), y0 = Math.min.apply(null, vs), y1 = Math.max.apply(null, vs);
    y0 = Math.max(0, Math.floor((y0 - 6) / 10) * 10); y1 = Math.min(100, Math.ceil((y1 + 6) / 10) * 10);
    var X = function (t) { return L + (t - x0) / (x1 - x0) * (W - L - R); }, Y = function (v) { return T + (y1 - v) / (y1 - y0) * (H - T - B); };
    g.font = '10px ' + MONO; g.textBaseline = 'middle'; g.textAlign = 'right';
    for (var v = y0; v <= y1; v += 10) { g.strokeStyle = LINE; g.lineWidth = 1; g.beginPath(); g.moveTo(L, Y(v)); g.lineTo(W - R, Y(v)); g.stroke(); g.fillStyle = MUTED; g.fillText(v + '%', L - 6, Y(v)); }
    if (o.ref != null && o.ref > y0 && o.ref < y1) { g.setLineDash([3, 4]); g.strokeStyle = MUTED; g.beginPath(); g.moveTo(L, Y(o.ref)); g.lineTo(W - R, Y(o.ref)); g.stroke(); g.setLineDash([]); }
    g.textAlign = 'center'; g.textBaseline = 'alphabetic'; g.fillStyle = MUTED;
    var d0 = new Date(x0); d0 = new Date(d0.getFullYear(), d0.getMonth() + 1, 1);
    var step = (x1 - x0) > 200 * 864e5 ? 3 : 1;
    for (var t = d0; t.getTime() <= x1; t = new Date(t.getFullYear(), t.getMonth() + step, 1)) { var xx = X(t.getTime()); if (xx > L + 10 && xx < W - R - 10) g.fillText(MESES[t.getMonth()] + (t.getMonth() === 0 ? ' ' + String(t.getFullYear()).slice(2) : ''), xx, H - 6); }
    var used = [];
    keys.forEach(function (k, i) {
      var s = series[k].map(function (r) { return [Date.parse(r[0]), r[1]]; }), col = PAL[i % PAL.length];
      g.strokeStyle = col; g.fillStyle = col; g.lineWidth = 2; g.lineJoin = 'round'; g.beginPath();
      s.forEach(function (r, j) { if (j) g.lineTo(X(r[0]), Y(r[1])); else g.moveTo(X(r[0]), Y(r[1])); }); g.stroke();
      s.forEach(function (r) { g.beginPath(); g.arc(X(r[0]), Y(r[1]), 3, 0, 7); g.fill(); });
      var l = s[s.length - 1], lx = X(l[0]), ly = Y(l[1]) - 10;
      if (used.some(function (u) { return Math.abs(u[0] - lx) < 40 && Math.abs(u[1] - ly) < 12; })) return;
      used.push([lx, ly]); g.font = '600 11px ' + SANS; g.textAlign = lx > W - 40 ? 'right' : 'left'; g.textBaseline = 'middle';
      g.fillText(n0(l[1]), lx + (g.textAlign === 'right' ? -7 : 7), ly);
    });
  }
  function simple(cv, serie, o) { // línea simple (tipo de cambio, inflación)
    o = o || {}; var c = sizeCv(cv), g = c.g, W = c.W, H = c.H, pts = (serie || []).filter(function (r) { return r[1] != null; });
    if (pts.length < 2) { g.font = '600 15px ' + SANS; g.fillStyle = MUTED; g.fillText(o.vacio || 'Sin datos suficientes en la fuente.', 0, 34); return; }
    var L = 50, R = 12, T = 14, B = 24, vs = pts.map(function (r) { return r[1]; }), y0 = Math.min.apply(null, vs), y1 = Math.max.apply(null, vs);
    if (y1 === y0) { y1 += 1; y0 -= 1; } var pad = (y1 - y0) * .1; y0 -= pad; y1 += pad;
    var X = function (i) { return L + i / (pts.length - 1) * (W - L - R); }, Y = function (v) { return T + (y1 - v) / (y1 - y0) * (H - T - B); };
    g.font = '10px ' + MONO; g.textBaseline = 'middle'; g.textAlign = 'right';
    for (var k = 0; k <= 3; k++) { var v = y0 + (y1 - y0) * k / 3; g.strokeStyle = LINE; g.beginPath(); g.moveTo(L, Y(v)); g.lineTo(W - R, Y(v)); g.stroke(); g.fillStyle = MUTED; g.fillText(num(v, Math.abs(y1 - y0) < 6 ? 2 : 0), L - 6, Y(v)); }
    g.textAlign = 'center'; g.textBaseline = 'alphabetic';
    [0, Math.floor((pts.length - 1) / 2), pts.length - 1].forEach(function (i) { g.fillText(o.fx ? o.fx(pts[i][0]) : pts[i][0], Math.min(W - R - 18, Math.max(L + 16, X(i))), H - 6); });
    g.strokeStyle = o.color || RED; g.lineWidth = 2; g.lineJoin = 'round'; g.beginPath();
    pts.forEach(function (r, i) { if (i) g.lineTo(X(i), Y(r[1])); else g.moveTo(X(i), Y(r[1])); }); g.stroke();
    g.fillStyle = o.color || RED; g.beginPath(); g.arc(X(pts.length - 1), Y(last(pts)[1]), 3.5, 0, 7); g.fill();
  }
  function corto(n) { if (/Lula/.test(n)) return 'Lula'; var p = n.split(' '); return n.length > 15 ? p[p.length - 1] : n; }
  function compass(cv, actores) {
    var c = sizeCv(cv), g = c.g, W = c.W, H = c.H, m = 30, S = Math.min(W - 2 * m, H - 2 * m), ox = (W - S) / 2, oy = (H - S) / 2;
    var X = function (x) { return ox + (x + 10) / 20 * S; }, Y = function (y) { return oy + (10 - y) / 20 * S; };
    [['rgba(208,33,58,.06)', -10, 10], ['rgba(47,109,179,.06)', 0, 10], ['rgba(157,156,148,.08)', -10, 0], ['rgba(201,134,27,.07)', 0, 0]].forEach(function (r) { g.fillStyle = r[0]; g.fillRect(X(r[1]), Y(r[2]), S / 2, S / 2); });
    g.strokeStyle = LINE; g.lineWidth = 1;
    for (var i = -10; i <= 10; i += 5) { g.beginPath(); g.moveTo(X(i), Y(10)); g.lineTo(X(i), Y(-10)); g.stroke(); g.beginPath(); g.moveTo(X(-10), Y(i)); g.lineTo(X(10), Y(i)); g.stroke(); }
    g.strokeStyle = INK; g.beginPath(); g.moveTo(X(0), Y(10)); g.lineTo(X(0), Y(-10)); g.moveTo(X(-10), Y(0)); g.lineTo(X(10), Y(0)); g.stroke();
    g.fillStyle = MUTED; g.font = '600 10px ' + SANS; g.textAlign = 'center'; g.textBaseline = 'alphabetic';
    g.fillText('AUTORITARIO', X(0), oy - 10); g.textBaseline = 'top'; g.fillText('LIBERTARIO', X(0), oy + S + 9);
    g.save(); g.translate(ox - 12, Y(0)); g.rotate(-Math.PI / 2); g.textBaseline = 'alphabetic'; g.fillText('IZQUIERDA', 0, 0); g.restore();
    g.save(); g.translate(ox + S + 12, Y(0)); g.rotate(Math.PI / 2); g.textBaseline = 'alphabetic'; g.fillText('DERECHA', 0, 0); g.restore();
    var placed = [];
    actores.slice().sort(function (a, b) { return a.gob ? -1 : b.gob ? 1 : 0; }).forEach(function (a) {
      var x = X(a.x), y = Y(a.y), r = a.gob ? 20 : 14, name = corto(a.n);
      g.font = (a.gob ? '700 12px ' : '500 11px ') + SANS;
      var w = g.measureText(name).width, left = x + r + 4 + w > ox + S - 2, lx = left ? x - r - 4 - w : x + r + 4, ly = y - 7;
      for (var k = 0; k < 8 && placed.some(function (p) { return Math.abs(p[1] - ly) < 13 && lx < p[0] + p[2] + 2 && lx + w > p[0] - 2; }); k++) ly += (k % 2 ? -1 : 1) * 13 * (k + 1);
      placed.push([lx, ly, w]); a._p = [x, y, r, lx, ly, name];
    });
    actores.forEach(function (a) { if (!a.gob) draw(a); }); actores.forEach(function (a) { if (a.gob) draw(a); });
    function draw(a) {
      var p = a._p, im = img(a.n);
      if (im) {
        var rr = p[2], sw = Math.min(im.naturalWidth, im.naturalHeight);
        g.save(); g.beginPath(); g.arc(p[0], p[1], rr, 0, 7); g.clip();
        g.drawImage(im, (im.naturalWidth - sw) / 2, 0, sw, sw, p[0] - rr, p[1] - rr, rr * 2, rr * 2); g.restore();
        g.strokeStyle = a.gob ? RED : '#fff'; g.lineWidth = a.gob ? 3 : 2; g.beginPath(); g.arc(p[0], p[1], rr, 0, 7); g.stroke();
      } else { g.fillStyle = a.gob ? RED : INK; g.strokeStyle = '#fff'; g.lineWidth = 2; g.beginPath(); g.arc(p[0], p[1], p[2] * .45, 0, 7); g.fill(); g.stroke(); }
      g.font = (a.gob ? '700 12px ' : '500 11px ') + SANS; g.textAlign = 'left'; g.textBaseline = 'top';
      g.lineWidth = 3; g.strokeStyle = 'rgba(255,255,255,.85)'; g.strokeText(p[5], p[3], p[4]); g.fillText(p[5], p[3], p[4]);
    }
  }

  // ---------- Render ----------
  function kpi(lab, val, foot) { return '<div class="kpi"><span>' + lab + '</span><strong>' + val + '</strong><small>' + (foot || '&nbsp;') + '</small></div>'; }
  function barsHTML(items, max, unidad) {
    return '<ul class="hbars">' + items.map(function (it) {
      var neg = it.length > 2 && it[2] != null;
      return '<li><span class="hb-l">' + esc(it[0]) + '</span><span class="hb-t"><i style="width:' + Math.max(1, it[1] / max * 100) + '%"></i>' + (neg ? '<b style="width:' + (it[2] / max * 100) + '%"></b>' : '') + '</span><span class="hb-v">' + n0(it[1]) + (unidad || ' %') + (neg ? ' <em>' + n0(it[2]) + ' %</em>' : '') + '</span></li>';
    }).join('') + '</ul>';
  }
  function src(u) { return u ? ' · <a href="' + esc(u) + '" target="_blank" rel="noopener">fuente</a>' : ''; }

  function renderPol(c) {
    var P = POL && POL.paises[c];
    $('polSec').hidden = !P;
    if (!P) { $('pLead').textContent = 'Sin datos políticos cargados para este país.'; return; }
    var gob = P.gob;
    $('pGob').innerHTML = foto(gob.n, 'gobph');
    $('pLead').innerHTML = 'Gobierna <strong>' + esc(gob.n) + '</strong> (' + esc(gob.p) + '), ' + esc(gob.cargo.charAt(0).toLowerCase() + gob.cargo.slice(1)) + ' desde ' + fecha(gob.desde) + '.';
    $('pCtx').textContent = P.contexto || '';
    var pr = promedio(P), h = '';
    $('imgH').textContent = P.intencion && !pr ? 'Intención de voto' : (P.medida || 'Imagen');
    if (pr) {
      var t = tendencia(P);
      h += '<div class="big"><strong>' + num(pr.a) + '<small>%</small></strong><div><span>Promedio de ' + pr.n + ' encuesta' + (pr.n > 1 ? 's' : '') + ' de los últimos 45 días</span>'
        + (pr.d != null ? '<span>Desaprobación promedio <b>' + num(pr.d) + ' %</b></span>' : '')
        + (t != null ? '<span>Última variación <b class="' + (t < 0 ? 'neg' : 'pos') + '">' + (t > 0 ? '+' : '') + n0(t) + ' pts</b></span>' : '') + '</div></div>';
    } else if (P.intencion) {
      var it = P.intencion.items[0], it2 = P.intencion.items[1];
      h += '<div class="big"><strong>' + num(it[1]) + '<small>%</small></strong><div><span><b>' + esc(it[0]) + '</b> primero, ' + n0(it[1] - it2[1]) + ' puntos sobre ' + esc(it2[0]) + '</span><span>' + esc(P.intencion.fuente) + ', ' + fecha(P.intencion.fecha) + '</span></div></div>';
    }
    if (P.nota) h += '<p class="pnote">' + esc(P.nota) + (P.nota_u ? src(P.nota_u) : '') + '</p>';
    $('pImg').innerHTML = h;
    var ser = P.series || {}, hasSer = Object.keys(ser).length > 0;
    $('cImgWrap').hidden = !hasSer;
    $('imgLeg').innerHTML = hasSer ? Object.keys(ser).map(function (k, i) { return '<span><i style="background:' + PAL[i % PAL.length] + '"></i>' + esc(k) + '</span>'; }).join('') + (P.series_nota ? '<span class="n">' + esc(P.series_nota) + '</span>' : '<span class="n">Evolución por encuestadora</span>') : '';
    if (hasSer) lines($('cImg'), ser, { ref: P.intencion ? null : 50 });
    var enc = (P.enc || []).concat((P.agregadores || []).map(function (a) { return Object.assign({ ag: 1 }, a); }));
    var rows = enc.slice().sort(function (a, b) { return a.fecha < b.fecha ? 1 : -1; }).map(function (e) {
      var used = pr && pr.enc.indexOf(e) >= 0;
      return '<tr' + (used ? '' : ' class="dim"') + '><td><a href="' + esc(e.u) + '" target="_blank" rel="noopener">' + esc(e.f) + '</a>' + (e.ag ? ' <small>promedio propio</small>' : '') + (e.nota ? ' <small>' + esc(e.nota) + '</small>' : '') + '</td><td>' + fechaC(e.fecha) + '</td><td>' + n0(e.a) + ' %</td><td>' + (e.d == null ? '—' : n0(e.d) + ' %') + '</td></tr>';
    });
    if (P.sondeos) rows = P.sondeos.map(function (s) { return '<tr><td><a href="' + esc(s.u) + '" target="_blank" rel="noopener">' + esc(s.f) + '</a></td><td>' + fechaC(s.fecha) + '</td><td>' + ['PP', 'PSOE', 'Vox'].map(function (k) { return s.v[k] == null ? '—' : n0(s.v[k]); }).join(' · ') + '</td></tr>'; });
    $('pPolls').innerHTML = rows.length ? '<table class="polls"><thead><tr><th>' + (P.sondeos ? 'Encuesta' : 'Encuestadora') + '</th><th>Campo</th>' + (P.sondeos ? '<th>PP · PSOE · Vox</th>' : '<th>Aprueba</th><th>Desaprueba</th>') + '</tr></thead><tbody>' + rows.join('') + '</tbody></table>'
      + (!P.sondeos && enc.some(function (e) { return !(pr && pr.enc.indexOf(e) >= 0); }) ? '<p class="pnote">En gris, mediciones que no entran en el promedio: tienen más de 45 días o son promedios de terceros.</p>' : '') : '';
    compass($('cComp'), P.actores || []);
    $('pActors').innerHTML = (P.actores || []).map(function (a) { return '<li' + (a.gob ? ' class="gob"' : '') + '>' + foto(a.n, 'aph') + '<div><strong>' + esc(a.n) + '</strong><span class="pty">' + esc(a.p) + '</span><small>' + esc(a.rol) + '</small></div></li>'; }).join('') + (Object.keys(FOT).length ? '<li class="cred">Fotos: Wikipedia / Wikimedia Commons</li>' : '');
    $('pParties').innerHTML = (P.partidos || []).map(function (p) { return '<li><strong>' + esc(p[0]) + '</strong><small>' + esc(p[1]) + '</small></li>'; }).join('');
    var el = P.eleccion; $('pElec').innerHTML = el ? '<span>Próxima elección</span><strong>' + esc(el.n) + ' · ' + fecha(el.fecha) + '</strong>' + (el.nota ? '<small>' + esc(el.nota) + '</small>' : '') : '';
    var x = '';
    if (P.intencion) x += '<h3>Intención de voto</h3><p class="sub">' + esc(P.intencion.fuente) + ' · ' + fecha(P.intencion.fecha) + src(P.intencion.u) + '</p>' + barsHTML(P.intencion.items, 40) + (P.intencion.escanos ? '<p class="pnote">' + esc(P.intencion.escanos) + '</p>' : '');
    if (P.dirigentes) x += '<h3>' + esc(P.dirigentes.medida) + ' de dirigentes</h3><p class="sub">' + esc(P.dirigentes.fuente) + ' · ' + fecha(P.dirigentes.fecha) + src(P.dirigentes.u) + '</p>' + barsHTML(P.dirigentes.items, 100);
    if (P.ultima) { var mx = Math.max.apply(null, P.ultima.items.map(function (i) { return i[1]; })); x += '<h3>' + esc(P.ultima.n) + '</h3><p class="sub">' + fecha(P.ultima.fecha) + src(P.ultima.u) + '</p>' + barsHTML(P.ultima.items, P.ultima.unidad ? mx : 100, P.ultima.unidad ? ' ' + P.ultima.unidad : ' %'); }
    $('pExtra').innerHTML = x; $('pExtraP').hidden = !x;
  }

  function render() {
    var p = DATA && DATA.paises[CUR];
    var nombre = (p && p.nombre) || CUR;
    document.title = nombre + ' — Tablero por país — Sudakaos LATAM';
    $('pName').innerHTML = flag(CUR, 160) + '<span>' + esc(nombre) + '</span>';
    [].forEach.call($('pTabs').children, function (a) { if (a.dataset.c === CUR) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
    renderPol(CUR);
    if (p) {
      var fx = p.fx || {}, fl = last(fx.serie), ix = p.indice, il = ix && last(ix.serie), inf = p.inflacion, nv = (SIT && SIT.nivel && SIT.nivel[CUR]) || {};
      var k = '';
      if (CUR === 'EC') k += kpi('Moneda', 'US$', 'Economía dolarizada');
      else if (fl) k += kpi(CUR === 'US' ? 'Euros por US$' : esc((fx.moneda || '').toUpperCase()) + ' por US$', num(fl[1], fl[1] < 10 ? 3 : 1), pct(fxVar(fx.serie, 30)) + ' en 30 días · ' + fechaC(fl[0]));
      if (inf) k += kpi('Inflación interanual', num(inf.valor) + ' %', esc(inf.fuente) + ' · ' + (inf.frecuencia === 'mensual' ? fecha(inf.periodo) : 'año ' + inf.periodo));
      if (il) k += kpi(esc(ix.nombre), num(il[1], 0), pct((il[1] / ix.serie[0][1] - 1) * 100) + ' en 30 días · ' + fechaC(il[0]));
      k += kpi('Alertas en medios', String(nv.n7 != null ? nv.n7 : (p.alertas || {}).n7 || 0), 'Últimos 7 días · ' + (nv.n24 || 0) + ' en 24 h');
      $('pKpis').innerHTML = k;
      $('fxSub').textContent = CUR === 'EC' ? 'Ecuador usa el dólar: no hay tipo de cambio propio.' : 'Cierre diario, últimos 30 días · currency-api';
      var fxs = (fx.serie || []).filter(function (r) { return Date.parse(r[0]) > Date.now() - 31 * 864e5; });
      simple($('cFx'), CUR === 'EC' ? [] : fxs, { fx: function (s) { return s.slice(8, 10) + '/' + s.slice(5, 7); }, vacio: CUR === 'EC' ? 'Economía dolarizada.' : undefined });
      var monthly = inf && inf.serie && inf.serie.length > 1;
      $('infSub').textContent = inf ? (monthly ? 'Interanual, mensual · ' + inf.fuente + ' · último dato ' + fecha(inf.periodo) : 'Último dato disponible: año ' + inf.periodo + ' · ' + inf.fuente + '. No hay serie mensual gratuita y comparable para este país.') : 'Sin dato en la fuente.';
      simple($('cInf'), monthly ? inf.serie : [], { color: INK, fx: function (s) { return MESES[+s.slice(5, 7) - 1] + ' ' + s.slice(2, 4); }, vacio: inf ? 'Inflación ' + inf.periodo + ': ' + num(inf.valor) + ' %' : 'Sin dato.' });
      var mes = Date.now() - 30 * 864e5, al = SIT && SIT.alertas ? SIT.alertas.filter(function (a) { return a.pais === CUR && Date.parse(a.t) > mes; }) : [];
      $('pAlerts').innerHTML = al.length ? al.slice(0, 8).map(function (a) {
        return '<li><span class="meta"><span class="tag s' + a.sev + '">' + esc(a.cat) + '</span> ' + esc(a.fuente) + ' · ' + ago(a.t) + '</span><a href="' + esc(a.url) + '" target="_blank" rel="noopener">' + esc(a.titulo) + '</a></li>';
      }).join('') : '<li class="empty">Sin alertas en los últimos 30 días.</li>';
      var tl = (p.titulares || []).filter(function (a) { return Date.parse(a.t) > mes; });
      $('pNews').innerHTML = tl.length ? tl.slice(0, 8).map(function (a) {
        return '<li><span class="meta">' + esc(a.fuente) + ' · ' + ago(a.t) + '</span><a href="' + esc(a.url) + '" target="_blank" rel="noopener">' + esc(a.titulo) + '</a></li>';
      }).join('') : '<li class="empty">Sin titulares recientes en la fuente.</li>';
    }
    table();
  }

  function rowData(c) {
    var p = (DATA && DATA.paises[c]) || {}, P = (POL && POL.paises[c]) || {}, pr = promedio(P), inf = p.inflacion, nv = (SIT && SIT.nivel && SIT.nivel[c]) || {};
    return { c: c, nombre: p.nombre || c, gob: P.gob ? P.gob.n : '', img: pr ? pr.a : null, des: pr ? pr.d : null, tend: tendencia(P),
      inf: inf ? inf.valor : null, infP: inf ? (inf.frecuencia === 'mensual' ? fechaC(inf.periodo) : inf.periodo) : '',
      fx30: c === 'EC' ? null : fxVar((p.fx || {}).serie, 30), a7: nv.n7 != null ? nv.n7 : (p.alertas || {}).n7 };
  }
  var COLS = [['nombre', 'País'], ['gob', 'Gobierna'], ['img', 'Aprobación'], ['des', 'Desaprob.'], ['tend', 'Última var.'], ['inf', 'Inflación'], ['fx30', 'Moneda 30 d'], ['a7', 'Alertas 7 d']];
  function table() {
    var rows = ORDEN.map(rowData);
    rows.sort(function (a, b) { var x = a[sortK], y = b[sortK]; if (x == null || x === '') return 1; if (y == null || y === '') return -1; return (typeof x === 'string' ? x.localeCompare(y) : x - y) * sortD; });
    $('pHead').innerHTML = '<tr>' + COLS.map(function (k) { return '<th data-k="' + k[0] + '"' + (k[0] === sortK ? ' aria-sort="' + (sortD > 0 ? 'ascending' : 'descending') + '"' : '') + '>' + k[1] + '</th>'; }).join('') + '</tr>';
    $('pRows').innerHTML = rows.map(function (r) {
      return '<tr data-c="' + r.c + '"' + (r.c === CUR ? ' class="on"' : '') + '><td>' + flag(r.c, 40) + esc(r.nombre) + '</td><td class="gobc">' + esc(r.gob) + '</td><td>' + (r.img == null ? '—' : num(r.img) + ' %<span class="bar" style="width:' + Math.round(r.img * .5) + 'px"></span>') + '</td><td>' + (r.des == null ? '—' : num(r.des) + ' %') + '</td><td class="' + (r.tend < 0 ? 'neg' : r.tend > 0 ? 'pos' : '') + '">' + (r.tend == null ? '—' : (r.tend > 0 ? '+' : '') + n0(r.tend) + ' pts') + '</td><td>' + (r.inf == null ? '—' : num(r.inf) + ' %<small> ' + esc(r.infP) + '</small>') + '</td><td>' + pct(r.fx30) + '</td><td>' + (r.a7 == null ? '—' : r.a7) + '</td></tr>';
    }).join('');
  }

  function go(c) { if (ORDEN.indexOf(c) < 0) c = 'AR'; CUR = c; render(); }

  function getJ(u) { return fetch(u, { cache: 'no-cache' }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }); }
  Promise.all([getJ('../data/paises.json'), getJ('../data/situacion.json'), getJ('../data/politica.json'), getJ('../data/fotos.json')]).then(function (r) {
    DATA = r[0]; SIT = r[1]; POL = r[2]; FOT = r[3] || {};
    if (!DATA && !POL) { $('pLead').textContent = 'Los datos todavía no están disponibles. Volvé a intentar en unos minutos.'; return; }
    $('pUpd').textContent = (POL ? 'Encuestas revisadas el ' + fecha(POL.meta.revisado) + '. ' : '') + (DATA ? 'Economía y alertas actualizadas ' + ago(DATA.meta.actualizado) + '.' : '');
    $('pTabs').innerHTML = ORDEN.map(function (c) { var n = (DATA && DATA.paises[c] && DATA.paises[c].nombre) || c; return '<a href="#' + c + '" data-c="' + c + '">' + flag(c, 40) + esc(n) + '</a>'; }).join('');
    $('pHead').addEventListener('click', function (e) { var th = e.target.closest('th'); if (!th) return; var k = th.dataset.k; if (k === sortK) sortD = -sortD; else { sortK = k; sortD = (k === 'nombre' || k === 'gob') ? 1 : -1; } table(); });
    $('pRows').addEventListener('click', function (e) { var tr = e.target.closest('tr'); if (tr) location.hash = tr.dataset.c; });
    addEventListener('hashchange', function () { go(location.hash.slice(1).toUpperCase()); scrollTo({ top: 0, behavior: 'smooth' }); });
    var rt; addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(render, 150); });
    go((location.hash.slice(1) || 'AR').toUpperCase());
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(render);
  });
})();
