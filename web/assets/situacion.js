/* Sudakaos LATAM · sala de situación con alertas reales (web/data/situacion.json).
   Titulares de medios (Google News) clasificados por reglas de palabras clave, sismos M4.5+ (USGS) y alertas de desastres (GDACS). */
(function () {
  'use strict';
  var NOMBRE = { AR: 'Argentina', BO: 'Bolivia', BR: 'Brasil', CL: 'Chile', CO: 'Colombia', EC: 'Ecuador', GY: 'Guyana', PY: 'Paraguay', PE: 'Perú', SR: 'Surinam', UY: 'Uruguay', VE: 'Venezuela', MX: 'México', US: 'Estados Unidos', ES: 'España', GB: 'Reino Unido', EU: 'Unión Europea' };
  var ORDEN = Object.keys(NOMBRE);
  var CATS = ['Todas', 'Seguridad', 'Desastre', 'Sismo', 'Protesta', 'Institucional', 'Economía', 'Elecciones'];
  var SEV = { 3: '#ef3b52', 2: '#f2a33a', 1: '#9d9c94' };
  var RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var $ = function (id) { return document.getElementById(id); };
  var SIT = null, cat = 'Todas', pais = '', marks = [];

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function ago(t) { var m = Math.max(0, (Date.now() - Date.parse(t)) / 60000); return m < 60 ? 'hace ' + Math.round(m) + ' min' : m < 1440 ? 'hace ' + Math.round(m / 60) + ' h' : 'hace ' + Math.round(m / 1440) + ' d'; }
  function hhmm(t) { var d = new Date(t), p = function (n) { return (n < 10 ? '0' : '') + n; }; return p(d.getDate()) + '/' + p(d.getMonth() + 1) + ' ' + p(d.getHours()) + ':' + p(d.getMinutes()); }
  function hash(s) { var h = 2166136261; for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return (h >>> 0) / 4294967296; }
  function visible(a) { return (cat === 'Todas' || a.cat === cat) && (!pais || a.pais === pais); }

  // ---------- Mapa (proyección equirectangular de las Américas y Europa) ----------
  var GEO = window.SUDAKAOS_GEO, cv = $('map'), tip = $('mtip'), base = document.createElement('canvas');
  var LON0 = -128, LON1 = 34, LAT0 = -57, LAT1 = 71, W = 0, H = 0, D = 1, sc = 1, ox = 0, oy = 0;
  function decode(b64) { var s = atob(b64), out = [], v = 0, sh = 0, prev = 0; for (var i = 0; i < s.length; i++) { var b = s.charCodeAt(i); v |= (b & 127) << sh; if (b & 128) sh += 7; else { prev += v; out.push(prev); v = 0; sh = 0; } } return out; }
  var N = GEO.n, GOLD = Math.PI * (3 - Math.sqrt(5)), land = decode(GEO.latam).concat(decode(GEO.rest)), cid = {};
  (GEO.cc || []).forEach(function (b, k) { decode(b).forEach(function (i) { cid[i] = ORDEN[k]; }); });
  function P(lat, lon) { return [ox + (lon - LON0) * sc, oy + (LAT1 - lat) * sc]; }
  function drawBase() {
    D = Math.min(devicePixelRatio || 1, 2); W = cv.clientWidth; H = cv.clientHeight;
    cv.width = base.width = W * D; cv.height = base.height = H * D;
    sc = Math.min(W / (LON1 - LON0), H / (LAT1 - LAT0)); ox = (W - (LON1 - LON0) * sc) / 2; oy = (H - (LAT1 - LAT0) * sc) / 2;
    var g = base.getContext('2d'); g.setTransform(D, 0, 0, D, 0, 0); g.clearRect(0, 0, W, H);
    var lv = (SIT && SIT.nivel) || {}, r = Math.max(1, sc * .55);
    land.forEach(function (i) {
      var y = 1 - (i + .5) / N * 2, lat = Math.asin(y) * 180 / Math.PI, lon = ((i * GOLD) % (Math.PI * 2)) * 180 / Math.PI - 180;
      if (lon < LON0 || lon > LON1 || lat < LAT0 || lat > LAT1) return;
      var c = cid[i], p = P(lat, lon), k = c && lv[c] ? Math.sqrt(lv[c].indice) : 0;
      g.fillStyle = c ? (k > 0 ? 'rgba(239,59,82,' + (.25 + k * .6).toFixed(2) + ')' : '#6b6a63') : '#33322e';
      g.fillRect(p[0] - r / 2, p[1] - r / 2, r, r);
    });
  }
  function buildMarks() {
    marks = (SIT ? SIT.alertas : []).filter(visible).map(function (a) {
      var j = a.tipo === 'medios' ? 1.6 : 0, h1 = hash(a.url || a.titulo), h2 = hash((a.titulo || '') + 'x');
      var p = P(a.lat + (h1 - .5) * 2 * j, a.lon + (h2 - .5) * 2 * j);
      return { a: a, x: p[0], y: p[1], age: (Date.now() - Date.parse(a.t)) / 36e5 };
    });
  }
  var t0 = performance.now(), raf = 0, vis = true;
  function frame(now) {
    raf = 0; var t = (now - t0) / 1000, g = cv.getContext('2d');
    g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, cv.width, cv.height); g.drawImage(base, 0, 0); g.setTransform(D, 0, 0, D, 0, 0);
    marks.forEach(function (m, i) {
      var col = SEV[m.a.sev] || SEV[1], r = 2.2 + m.a.sev * 1.3;
      if (m.age < 12 && !RM) { var ph = (t * .6 + i * .137) % 1; g.strokeStyle = col; g.globalAlpha = (1 - ph) * .7; g.lineWidth = 1.2; g.beginPath(); g.arc(m.x, m.y, r + ph * 16, 0, 7); g.stroke(); }
      g.globalAlpha = m.age < 24 ? 1 : .55; g.fillStyle = col; g.beginPath(); g.arc(m.x, m.y, r, 0, 7); g.fill();
    });
    g.globalAlpha = 1;
    if (vis && !RM && !document.hidden) raf = requestAnimationFrame(frame);
  }
  function kick() { if (!raf) raf = requestAnimationFrame(frame); }
  new IntersectionObserver(function (es) { vis = es[0].isIntersecting; if (vis) kick(); }).observe(cv);
  document.addEventListener('visibilitychange', kick);
  function nearest(e) { var r = cv.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top, best = 12, bm = null; marks.forEach(function (m) { var d = Math.hypot(m.x - x, m.y - y); if (d < best) { best = d; bm = m; } }); return bm; }
  cv.addEventListener('mousemove', function (e) {
    var m = nearest(e); cv.style.cursor = m ? 'pointer' : 'crosshair';
    if (!m) { tip.classList.remove('on'); return; }
    tip.innerHTML = '<b>' + esc(m.a.cat) + ' · ' + esc(NOMBRE[m.a.pais] || m.a.pais) + ' · ' + ago(m.a.t) + '</b>' + esc(m.a.titulo);
    var tx = Math.min(m.x + 14, W - 300); tip.style.transform = 'translate(' + Math.max(0, tx) + 'px,' + (m.y + 26) + 'px)'; tip.classList.add('on');
  });
  cv.addEventListener('mouseleave', function () { tip.classList.remove('on'); });
  cv.addEventListener('click', function (e) { var m = nearest(e); if (m && m.a.url) window.open(m.a.url, '_blank', 'noopener'); });

  // ---------- Listas ----------
  function render() {
    var al = SIT.alertas, c24 = Date.now() - 864e5, a24 = al.filter(function (a) { return Date.parse(a.t) > c24; });
    var paises24 = {}; a24.forEach(function (a) { paises24[a.pais] = 1; });
    var cnt = {}; a24.forEach(function (a) { cnt[a.cat] = (cnt[a.cat] || 0) + 1; });
    var top = Object.keys(cnt).sort(function (a, b) { return cnt[b] - cnt[a]; })[0];
    $('sKpis').innerHTML = [['Alertas en 24 h', a24.length, 'medios, USGS y GDACS'], ['Países con alertas', Object.keys(paises24).length + ' de 17', 'últimas 24 horas'],
      ['Severidad alta', a24.filter(function (a) { return a.sev === 3; }).length, 'seguridad, desastres, sismos fuertes'], ['Tema dominante', top || '—', top ? cnt[top] + ' alertas' : 'sin alertas']]
      .map(function (k) { return '<div class="kpi"><span>' + k[0] + '</span><strong>' + esc(k[1]) + '</strong><small>' + k[2] + '</small></div>'; }).join('');
    var f = al.filter(visible);
    $('sFeed').innerHTML = f.length ? f.slice(0, 80).map(function (a) {
      return '<li><span class="t">' + hhmm(a.t) + '</span><span class="c">' + esc(a.pais) + '</span><span><span class="tag s' + a.sev + '">' + esc(a.cat) + '</span><a href="' + esc(a.url) + '" target="_blank" rel="noopener">' + esc(a.titulo) + '</a><small>' + esc(a.fuente) + ' · ' + ago(a.t) + '</small></span></li>';
    }).join('') : '<li class="empty">Sin alertas para este filtro.</li>';
    $('sCount').textContent = f.length + ' alertas';
    var lv = SIT.nivel || {}, mx = Math.max.apply(null, ORDEN.map(function (c) { return (lv[c] || {}).n24 || 0; }).concat([1]));
    $('sLevels').innerHTML = ORDEN.slice().sort(function (a, b) { return ((lv[b] || {}).peso || 0) - ((lv[a] || {}).peso || 0); }).map(function (c) {
      var n = (lv[c] || {}).n24 || 0; return '<li data-c="' + c + '"><span>' + NOMBRE[c] + '</span><b>' + n + '</b><span class="m"><span style="width:' + Math.round(n / mx * 100) + '%"></span></span></li>';
    }).join('');
    buildMarks(); kick();
  }

  $('sFilters').innerHTML = CATS.map(function (c) { return '<button type="button" aria-pressed="' + (c === cat) + '" data-cat="' + c + '">' + c + '</button>'; }).join('') +
    '<select id="sPais" aria-label="Filtrar por país"><option value="">Todos los países</option>' + ORDEN.map(function (c) { return '<option value="' + c + '">' + NOMBRE[c] + '</option>'; }).join('') + '</select>';
  $('sFilters').addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; cat = b.dataset.cat; [].forEach.call(this.querySelectorAll('button'), function (x) { x.setAttribute('aria-pressed', String(x === b)); }); if (SIT) render(); });
  $('sPais').addEventListener('change', function () { pais = this.value; if (SIT) render(); });
  $('sLevels').addEventListener('click', function (e) { var li = e.target.closest('li'); if (!li) return; pais = li.dataset.c === pais ? '' : li.dataset.c; $('sPais').value = pais; render(); $('sFeed').scrollIntoView({ behavior: 'smooth', block: 'start' }); });

  function clock() { var d = new Date(), p = function (n) { return (n < 10 ? '0' : '') + n; }; $('sClock').textContent = 'UTC ' + p(d.getUTCHours()) + ':' + p(d.getUTCMinutes()) + ':' + p(d.getUTCSeconds()); }
  clock(); setInterval(clock, 1000);
  function load() {
    fetch('../data/situacion.json', { cache: 'no-cache' }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }).then(function (d) {
      if (!d) { if (!SIT) $('sUpd').textContent = 'Los datos todavía no están disponibles.'; return; }
      SIT = d; $('sUpd').textContent = 'Actualizado ' + hhmm(d.meta.actualizado) + ' (' + ago(d.meta.actualizado) + '). Se actualiza cada 3 horas.';
      drawBase(); render();
    });
  }
  drawBase(); kick(); load(); setInterval(load, 10 * 60 * 1000);
  var rt; addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(function () { drawBase(); if (SIT) render(); }, 150); });
})();
