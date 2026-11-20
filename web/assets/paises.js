/* Sudakaos LATAM · tablero por país con datos públicos reales (web/data/paises.json y situacion.json).
   Fuentes: Banco Mundial, currency-api, Google News, GDELT, USGS y GDACS. Sin dependencias. */
(function () {
  'use strict';
  var ORDEN = ['AR', 'BO', 'BR', 'CL', 'CO', 'EC', 'GY', 'PY', 'PE', 'SR', 'UY', 'VE', 'MX', 'US', 'ES', 'GB', 'EU'];
  var css = getComputedStyle(document.documentElement);
  var INK = css.getPropertyValue('--ink').trim() || '#0c0c0b', RED = css.getPropertyValue('--red').trim() || '#d0213a',
    MUTED = css.getPropertyValue('--muted').trim() || '#75736c', LINE = css.getPropertyValue('--line').trim() || '#e2e1dc';
  var SANS = '"Schibsted Grotesk",Arial,sans-serif', MONO = 'ui-monospace,SFMono-Regular,Menlo,Consolas,monospace';
  var DATA = null, SIT = null, CUR = 'AR', sortK = 'alertas', sortD = -1;
  var $ = function (id) { return document.getElementById(id); };

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function num(n, d) { if (n == null || isNaN(n)) return '—'; d = d == null ? 1 : d; return Number(n).toLocaleString('es-AR', { maximumFractionDigits: d, minimumFractionDigits: d }); }
  function last(s) { return s && s.length ? s[s.length - 1] : null; }
  function ago(t) { var m = Math.max(0, (Date.now() - Date.parse(t)) / 60000); return m < 60 ? 'hace ' + Math.round(m) + ' min' : m < 1440 ? 'hace ' + Math.round(m / 60) + ' h' : 'hace ' + Math.round(m / 1440) + ' d'; }
  function hhmm(t) { var d = new Date(t), p = function (n) { return (n < 10 ? '0' : '') + n; }; return p(d.getDate()) + '/' + p(d.getMonth() + 1) + ' ' + p(d.getHours()) + ':' + p(d.getMinutes()); }
  function fxVar(s, days) { if (!s || s.length < 2) return null; var l = s[s.length - 1], t0 = Date.parse(l[0]) - days * 864e5, b = s[0]; s.forEach(function (r) { if (Date.parse(r[0]) <= t0) b = r; }); return b === l ? null : (l[1] / b[1] - 1) * 100; }
  function tonoProm(p) { var t = p.tono || []; if (!t.length) return null; var s = 0; t.forEach(function (r) { s += r[1]; }); return s / t.length; }
  function compact(n) { if (n == null) return '—'; if (n >= 1e12) return num(n / 1e12, 2) + ' bill.'; if (n >= 1e9) return num(n / 1e9, 1) + ' mil M'; if (n >= 1e6) return num(n / 1e6, 1) + ' M'; return num(n, 0); }

  // ---------- Gráfico de líneas / barras en canvas ----------
  function chart(cv, series, o) {
    o = o || {};
    var d = Math.min(devicePixelRatio || 1, 2), W = cv.clientWidth, H = cv.clientHeight; cv.width = W * d; cv.height = H * d;
    var g = cv.getContext('2d'); g.setTransform(d, 0, 0, d, 0, 0); g.clearRect(0, 0, W, H);
    var pts = series.filter(function (r) { return r[1] != null; });
    if (pts.length < 2) { g.font = '13px ' + SANS; g.fillStyle = MUTED; g.fillText('Sin datos suficientes en la fuente.', 0, 32); return; }
    var L = 46, R = 12, T = 16, B = 26, xs = pts.map(function (r) { return o.x ? o.x(r[0]) : r[0]; });
    var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs), vs = pts.map(function (r) { return r[1]; });
    var y0 = Math.min.apply(null, vs), y1 = Math.max.apply(null, vs);
    if (o.bars || o.zero) { y0 = Math.min(0, y0); y1 = Math.max(0, y1); }
    if (y1 === y0) { y1 += 1; y0 -= 1; }
    var pad = (y1 - y0) * .08; y1 += pad; if (y0 < 0 || !o.bars) y0 -= pad;
    var inset = o.bars ? Math.max(4, (W - L - R) / pts.length * .4) : 0;
    var X = function (x) { return L + inset + (x - x0) / (x1 - x0 || 1) * (W - L - R - 2 * inset); }, Y = function (v) { return T + (y1 - v) / (y1 - y0) * (H - T - B); };
    g.font = '10px ' + MONO; g.textBaseline = 'middle';
    for (var k = 0; k <= 4; k++) { var v = y0 + (y1 - y0) * k / 4, y = Y(v); g.strokeStyle = LINE; g.lineWidth = 1; g.beginPath(); g.moveTo(L, y); g.lineTo(W - R, y); g.stroke(); g.fillStyle = MUTED; g.textAlign = 'right'; g.fillText(num(v, Math.abs(y1 - y0) < 8 ? 1 : 0), L - 6, y); }
    if (y0 < 0 && y1 > 0) { g.strokeStyle = INK; g.beginPath(); g.moveTo(L, Y(0)); g.lineTo(W - R, Y(0)); g.stroke(); }
    g.textAlign = 'center'; g.textBaseline = 'alphabetic'; g.fillStyle = MUTED;
    var lbls = o.labels || [pts[0][0], pts[Math.floor(pts.length / 2)][0], pts[pts.length - 1][0]];
    lbls.forEach(function (lb) { var r = pts.find(function (p) { return p[0] === lb; }); if (r) g.fillText(o.fmtX ? o.fmtX(lb) : lb, Math.min(W - R - 20, Math.max(L + 14, X(o.x ? o.x(lb) : lb))), H - 8); });
    if (o.bars) {
      var bw = Math.max(2, (W - L - R) / pts.length * .62);
      pts.forEach(function (r) { var x = X(o.x ? o.x(r[0]) : r[0]), y = Y(r[1]), z = Y(0); g.fillStyle = r[1] < 0 ? RED : INK; g.fillRect(x - bw / 2, Math.min(y, z), bw, Math.abs(z - y) || 1); });
    } else {
      g.strokeStyle = o.color || RED; g.lineWidth = 2; g.lineJoin = 'round'; g.beginPath();
      pts.forEach(function (r, i) { var x = X(o.x ? o.x(r[0]) : r[0]), y = Y(r[1]); if (i) g.lineTo(x, y); else g.moveTo(x, y); }); g.stroke();
      var l = pts[pts.length - 1], lx = X(o.x ? o.x(l[0]) : l[0]), ly = Y(l[1]); g.fillStyle = o.color || RED; g.beginPath(); g.arc(lx, ly, 3.5, 0, 7); g.fill();
    }
  }

  // ---------- Render ----------
  function kpi(lab, val, foot, cls) { return '<div class="kpi"><span>' + lab + '</span><strong' + (cls ? ' class="' + cls + '"' : '') + '>' + val + '</strong><small>' + (foot || '&nbsp;') + '</small></div>'; }
  function wbv(p, k) { return last((p.wb || {})[k]); }

  function render() {
    var p = DATA.paises[CUR]; if (!p) return;
    document.title = p.nombre + ' — Tablero por país — Sudakaos LATAM';
    $('pName').textContent = p.nombre;
    var nv = (SIT && SIT.nivel && SIT.nivel[CUR]) || { n24: 0 };
    $('pLead').textContent = nv.n24 ? nv.n24 + ' alerta' + (nv.n24 === 1 ? '' : 's') + ' en las últimas 24 horas y ' + p.notas24 + ' notas de medios sobre ' + p.nombre + '.' : 'Sin alertas en las últimas 24 horas. ' + p.notas24 + ' notas de medios sobre ' + p.nombre + '.';
    [].forEach.call($('pTabs').children, function (a) { if (a.dataset.c === CUR) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
    var inf = wbv(p, 'inflacion'), gdp = wbv(p, 'pib_crec'), un = wbv(p, 'desempleo'), pc = wbv(p, 'pib_pc'), pop = wbv(p, 'poblacion'), net = wbv(p, 'internet');
    var fx = p.fx || {}, fl = last(fx.serie), v30 = fxVar(fx.serie, 30), tono = tonoProm(p);
    var h = kpi('Inflación anual', inf ? num(inf[1]) + ' %' : '—', inf ? 'Banco Mundial · ' + inf[0] : 'Sin dato', inf && inf[1] > 10 ? 'up' : '') +
      kpi('Crecimiento del PIB', gdp ? num(gdp[1]) + ' %' : '—', gdp ? 'Banco Mundial · ' + gdp[0] : 'Sin dato', gdp && gdp[1] < 0 ? 'up' : '') +
      kpi('Desempleo', un ? num(un[1]) + ' %' : '—', un ? 'OIT / Banco Mundial · ' + un[0] : 'Sin dato') +
      (CUR === 'EC' ? kpi('Moneda', 'US$', 'Dolarizado desde 2000') :
        kpi(CUR === 'US' ? 'Euros por US$' : (fx.moneda || '') + ' por US$', fl ? num(fl[1], fl[1] < 10 ? 3 : 1) : '—', v30 != null ? (v30 >= 0 ? '+' : '') + num(v30) + ' % en 30 días · ' + fl[0] : (fl ? fl[0] : 'Sin dato'), v30 > 3 ? 'up' : '')) +
      kpi('PIB per cápita', pc ? 'US$ ' + num(pc[1], 0) : '—', pc ? 'Banco Mundial · ' + pc[0] : 'Sin dato') +
      kpi('Población', pop ? compact(pop[1]) : '—', pop ? 'Banco Mundial · ' + pop[0] : 'Sin dato') +
      kpi('Usuarios de internet', net ? num(net[1], 0) + ' %' : '—', net ? 'UIT / Banco Mundial · ' + net[0] : 'Sin dato') +
      kpi('Tono de la cobertura', tono != null ? (tono > 0 ? '+' : '') + num(tono, 2) : '—', tono != null ? 'GDELT · promedio 7 días' : 'Sin dato', tono != null && tono < -2 ? 'up' : '');
    $('pKpis').innerHTML = h;

    var yr = function (s) { return (s || []).filter(function (r) { return r[0] >= 2005; }); };
    var si = yr(p.wb.inflacion), sg = yr(p.wb.pib_crec);
    chart($('cInf'), si, { zero: true });
    chart($('cGdp'), sg, { bars: true });
    var fxs = (fx.serie || []);
    $('fxSub').textContent = CUR === 'EC' ? 'Ecuador usa el dólar estadounidense.' : (CUR === 'US' ? 'Euros por dólar' : (fx.moneda || '') + ' por dólar') + ' · cierre diario o semanal · currency-api';
    if (CUR === 'EC') chart($('cFx'), [], {}); else chart($('cFx'), fxs, { x: function (s) { return Date.parse(s); }, color: INK, fmtX: function (s) { return s.slice(8, 10) + '/' + s.slice(5, 7); } });
    chart($('cTone'), (p.tono || []), { bars: true, fmtX: function (s) { return s.slice(6, 8) + '/' + s.slice(4, 6); }, x: function (s) { return Date.parse(s.slice(0, 4) + '-' + s.slice(4, 6) + '-' + s.slice(6, 8)); } });

    var al = SIT && SIT.alertas ? SIT.alertas.filter(function (a) { return a.pais === CUR; }) : [];
    $('pAlerts').innerHTML = al.length ? al.slice(0, 12).map(function (a) {
      return '<li><span class="t">' + hhmm(a.t) + '</span><span><span class="tag s' + a.sev + '">' + esc(a.cat) + '</span><a href="' + esc(a.url) + '" target="_blank" rel="noopener">' + esc(a.titulo) + '</a><small>' + esc(a.fuente) + ' · ' + ago(a.t) + '</small></span></li>';
    }).join('') : '<li class="empty">Sin alertas en las últimas 48 horas.</li>';
    $('pNews').innerHTML = (p.titulares || []).length ? p.titulares.slice(0, 10).map(function (a) {
      return '<li><span class="t">' + hhmm(a.t) + '</span><span><a href="' + esc(a.url) + '" target="_blank" rel="noopener">' + esc(a.titulo) + '</a><small>' + esc(a.fuente) + '</small></span></li>';
    }).join('') : '<li class="empty">Sin titulares en esta actualización.</li>';
    table();
  }

  function rowData(c) {
    var p = DATA.paises[c], nv = (SIT && SIT.nivel && SIT.nivel[c]) || { n24: 0 };
    var g = function (k) { var v = wbv(p, k); return v ? v[1] : null; };
    return { c: c, nombre: p.nombre, inflacion: g('inflacion'), pib_crec: g('pib_crec'), desempleo: g('desempleo'), pib_pc: g('pib_pc'), fx30: c === 'EC' ? null : fxVar((p.fx || {}).serie, 30), tono: tonoProm(p), alertas: nv.n24 };
  }
  var COLS = [['nombre', 'País'], ['inflacion', 'Inflación %'], ['pib_crec', 'PIB %'], ['desempleo', 'Desempleo %'], ['pib_pc', 'PIB p/c US$'], ['fx30', 'Tipo de cambio 30 d'], ['tono', 'Tono medios'], ['alertas', 'Alertas 24 h']];
  function table() {
    var rows = ORDEN.filter(function (c) { return DATA.paises[c]; }).map(rowData);
    rows.sort(function (a, b) { var x = a[sortK], y = b[sortK]; if (x == null) return 1; if (y == null) return -1; return (typeof x === 'string' ? x.localeCompare(y) : x - y) * sortD; });
    var mx = Math.max.apply(null, rows.map(function (r) { return r.alertas; }).concat([1]));
    $('pHead').innerHTML = '<tr>' + COLS.map(function (k) { return '<th data-k="' + k[0] + '"' + (k[0] === sortK ? ' aria-sort="' + (sortD > 0 ? 'ascending' : 'descending') + '"' : '') + '>' + k[1] + '</th>'; }).join('') + '</tr>';
    $('pRows').innerHTML = rows.map(function (r) {
      var f = function (v, d) { return v == null ? '—' : num(v, d); };
      return '<tr data-c="' + r.c + '"' + (r.c === CUR ? ' class="on"' : '') + '><td>' + esc(r.nombre) + '</td><td>' + f(r.inflacion) + '</td><td>' + f(r.pib_crec) + '</td><td>' + f(r.desempleo) + '</td><td>' + f(r.pib_pc, 0) + '</td><td>' + (r.fx30 == null ? '—' : (r.fx30 >= 0 ? '+' : '') + num(r.fx30) + ' %') + '</td><td>' + f(r.tono, 2) + '</td><td>' + r.alertas + '<span class="bar" style="width:' + Math.round(r.alertas / mx * 40) + 'px"></span></td></tr>';
    }).join('');
  }

  function go(c) { if (!DATA.paises[c]) c = 'AR'; CUR = c; render(); }

  Promise.all(['../data/paises.json', '../data/situacion.json'].map(function (u) { return fetch(u, { cache: 'no-cache' }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }); })).then(function (r) {
    DATA = r[0]; SIT = r[1];
    if (!DATA) { $('pLead').textContent = 'Los datos todavía no están disponibles. Volvé a intentar en unos minutos.'; return; }
    $('pUpd').textContent = 'Actualizado ' + hhmm(DATA.meta.actualizado) + ' (' + ago(DATA.meta.actualizado) + ')';
    $('pTabs').innerHTML = ORDEN.filter(function (c) { return DATA.paises[c]; }).map(function (c) { return '<a href="#' + c + '" data-c="' + c + '">' + esc(DATA.paises[c].nombre) + '</a>'; }).join('');
    $('pHead').addEventListener('click', function (e) { var th = e.target.closest('th'); if (!th) return; var k = th.dataset.k; if (k === sortK) sortD = -sortD; else { sortK = k; sortD = k === 'nombre' ? 1 : -1; } table(); });
    $('pRows').addEventListener('click', function (e) { var tr = e.target.closest('tr'); if (tr) location.hash = tr.dataset.c; });
    addEventListener('hashchange', function () { go(location.hash.slice(1).toUpperCase()); scrollTo({ top: 0, behavior: 'smooth' }); });
    var rt; addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(render, 150); });
    go((location.hash.slice(1) || 'AR').toUpperCase());
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(render);
  });
})();
