/* Brújula · tablero opinión × conversación. Lee solo agregados:
   data/quiz.json (procesar.py), data/listener.json (listener/analyze.py), data/cruce.json (cruce.py) y datos/ejes.json.
   Con ?demo=1 lee data/demo/ (datos simulados, con aviso visible). */
(function () {
  'use strict';
  const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const fmt = (n, d = 0) => n == null || isNaN(n) ? '—' : Number(n).toLocaleString('es-AR', { maximumFractionDigits: d, minimumFractionDigits: d });
  const DEMO = /[?&]demo=1/.test(location.search);
  const BASE = DEMO ? 'data/demo/' : 'data/';
  const C = { a: '#3987e5', b: '#e8a33d', pos: '#43d17a', neg: '#ff6b6b', neu: '#5d6470', dim: '#5c6676', txt: '#e4e8ee' };
  const PAL = ['#e8a33d', '#3987e5', '#43d17a', '#d55181', '#9085e9', '#5fb3c9', '#ff6b6b', '#c98500', '#7c8b9e', '#b5d33d', '#e86f3d', '#3dc9a8'];
  const CFG = { displayModeBar: false, responsive: true };
  const S = { E: null, Q: {}, L: {}, X: {}, ver: 'ar', var: 'genero', eje: 'pla', br: 'brecha_jovenes', hl: 'pla' };
  const lay = (h, extra = {}) => Object.assign({ height: h, margin: { l: 10, r: 10, t: 10, b: 30 }, showlegend: false }, extra);
  const plot = (id, data, layout) => { const el = $('#' + id); if (el) Plotly.newPlot(el, data, layout, CFG) };
  const empty = (id, t) => { const el = $('#' + id); if (el) el.innerHTML = `<div class="empty">${esc(t)}</div>` };
  const ejeN = id => S.E.ejes.find(e => e.id === id);
  const chips = (id, opts, cur, fn) => {
    const el = $('#' + id); if (!el) return;
    el.innerHTML = opts.map(([v, t]) => `<button class="chip${v === cur ? ' on' : ''}" data-v="${esc(v)}">${esc(t)}</button>`).join('');
    el.onclick = ev => { const b = ev.target.closest('.chip'); if (b) fn(b.dataset.v) };
  };

  // ------------------------------------------------------------------ cabecera
  function cabecera() {
    const upd = [S.Q.updated_at, S.L.updated_at, S.X.updated_at].filter(Boolean).sort().pop();
    const age = upd ? (Date.now() - new Date(upd)) / 36e5 : 999;
    $('#live').classList.toggle('old', age > 30);
    const t = () => $('#clock').innerHTML = `<span>ART <b>${new Date().toLocaleTimeString('es-AR', { timeZone: 'America/Argentina/Buenos_Aires', hour: '2-digit', minute: '2-digit' })}</b></span>` +
      `<span>ACT <b>${upd ? new Date(upd).toLocaleString('es-AR', { timeZone: 'America/Argentina/Buenos_Aires', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'}</b></span>`;
    t(); setInterval(t, 30000);
    const items = (S.X.alertas || []).map(a => `<span><em>ALERTA</em>${esc(a.t)}</span>`)
      .concat(Object.entries(S.L.ejes || {}).slice(0, 8).flatMap(([k, v]) => (v.titulares || []).slice(0, 1).map(h => `<span><em>${esc(ejeN(k).nombre.toUpperCase())}</em>${esc(h.t)}</span>`)));
    $('#ticker').innerHTML = items.join('') || '<span>Esperando la primera corrida de datos</span>';
    if (DEMO || S.Q.simulado) $('#sim').innerHTML = '<div class="sim">Datos simulados' + (DEMO ? ' (encuesta y conversación)' : ' de encuesta') + ': solo para ver cómo se arma el tablero</div>';
    $('#foot').textContent = 'Brújula · encuesta propia (quiz de 12 ejes con certeza) y escucha de Google News, YouTube, Biblioteca de Anuncios de Meta, Instagram y X.';
  }

  // ------------------------------------------------------------------ panorama
  function panorama() {
    const q = (S.Q.versiones || {}).ar || {};
    const L = S.L.totales || {};
    const nf = Object.values(S.L.figuras || {}).filter(f => f.n).length;
    const k = [['', 'Respuestas válidas', fmt((S.Q.campo || {}).validas), `de ${fmt((S.Q.campo || {}).recibidas)} recibidas`],
      ['', 'n efectivo (AR)', fmt(q.n_efectivo), q.ponderacion || 'sin datos'],
      ['', 'Certeza media (AR)', q.certeza == null ? '—' : fmt(q.certeza) + '/100', 'qué tan firmes son las posturas'],
      ['', 'Textos escuchados', fmt(L.textos), L.desde ? `${L.desde} a ${L.hasta}` : 'sin datos'],
      ['', 'Dirigentes mencionados', fmt(nf), `de ${S.figs.length} del quiz`],
      ['f', 'Alertas', fmt((S.X.alertas || []).length), 'cruce automático']];
    $('#kpis').innerHTML = k.map(x => `<div class="kpi ${x[0]}"><div class="l">${x[1]}</div><div class="v">${x[2]}</div><div class="d">${esc(x[3])}</div></div>`).join('');
    const ej = S.X.ejes || [];
    if (ej.some(e => e.quiz != null || e.encuadre != null)) {
      const y = ej.map(e => `${e.a} ↔ ${e.b}`);
      const lines = ej.flatMap((e, i) => e.quiz != null && e.encuadre != null ? [{ type: 'line', x0: e.quiz, x1: e.encuadre, y0: i, y1: i, line: { color: '#3a4558', width: 3 } }] : []);
      plot('p-dumb', [
        { x: ej.map(e => e.quiz), y, mode: 'markers', name: 'Quiz', marker: { size: 13, color: C.b }, hovertemplate: '%{y}<br>Quiz: %{x:.0f}<extra></extra>' },
        { x: ej.map(e => e.encuadre), y, mode: 'markers', name: 'Conversación', marker: { size: 12, color: C.a, symbol: 'diamond' }, hovertemplate: '%{y}<br>Conversación: %{x:.0f}<extra></extra>' }],
        lay(440, { margin: { l: 255, r: 10, t: 10, b: 30 }, showlegend: true, legend: { orientation: 'h', y: 1.08 }, shapes: [...lines, { type: 'line', x0: 50, x1: 50, y0: -0.5, y1: ej.length - .5, line: { color: '#263040', dash: 'dot' } }],
          xaxis: { range: [0, 100] }, yaxis: { autorange: 'reversed' } }));
    } else empty('p-dumb', 'Sin datos todavía');
    $('#p-alertas').innerHTML = (S.X.alertas || []).map(a => `<div class="${esc(a.nivel)}">${esc(a.t)}</div>`).join('') || '<div class="info">Sin alertas.</div>';
    $('#p-acc').innerHTML = (S.X.acciones || []).slice(0, 5).map(a => `<li><b>${esc(a.accion)}</b><small>${esc(a.metrica)}</small></li>`).join('') || '<li>Se arman cuando hay datos de las dos fuentes.</li>';
    figScatter('p-fig', 330);
  }
  function figScatter(id, h) {
    const f = (S.X.figuras || []).filter(x => x.afinidad > 0 || x.sov > 0);
    if (!f.length) return empty(id, 'Sin datos todavía');
    const mx = Math.max(5, ...f.map(x => Math.max(x.afinidad, x.sov))) * 1.1;
    plot(id, [{ x: f.map(x => x.afinidad), y: f.map(x => x.sov), text: f.map(x => Math.max(x.afinidad, x.sov) >= 2.5 ? x.nombre.split(' ').slice(-1)[0] : ''), mode: 'markers+text', textposition: 'top center',
      textfont: { size: 10, color: '#98a2b2' }, marker: { size: 9, color: f.map(x => x.tono == null ? C.neu : x.tono >= 0 ? C.pos : C.neg) },
      customdata: f.map(x => [x.nombre, x.tono]), hovertemplate: '%{customdata[0]}<br>Afinidad %{x:.1f}% · SoV %{y:.1f}%<extra></extra>' }],
      lay(h, { margin: { l: 44, r: 10, t: 10, b: 40 }, xaxis: { title: { text: 'Afinidad en el quiz (%)' }, range: [0, mx] }, yaxis: { title: { text: 'Share of voice (%)' }, range: [0, mx] },
        shapes: [{ type: 'line', x0: 0, y0: 0, x1: mx, y1: mx, line: { color: '#263040', dash: 'dot' } }] }));
  }

  // ------------------------------------------------------------------ encuesta
  function encuesta() {
    const vers = Object.keys(S.Q.versiones || {});
    if (!vers.length) {
      ['e-ejes', 'e-figs', 'e-seg', 'e-eg', 'e-re', 'e-preg', 'e-tribus', 'e-campo'].forEach(i => empty(i, 'Todavía no hay respuestas suficientes del quiz.'));
      return;
    }
    if (!vers.includes(S.ver)) S.ver = vers[0];
    chips('e-ver', vers.map(v => [v, (S.E.versiones[v] || {}).nombre + ` · n ${fmt(S.Q.versiones[v].n)}`]), S.ver, v => { S.ver = v; encuesta() });
    const q = S.Q.versiones[S.ver];
    const E = S.E.ejes;
    plot('e-ejes', [{ type: 'bar', orientation: 'h', y: E.map(e => `${e.a} ↔ ${e.b}`), x: E.map(e => q.ejes[e.id].m - 50), base: 50,
      error_x: { type: 'data', array: E.map(e => q.ejes[e.id].ci), color: '#98a2b2', thickness: 1 },
      marker: { color: E.map(e => q.ejes[e.id].m >= 50 ? C.b : C.a) }, hovertemplate: '%{y}<br>%{customdata[0]:.1f}/100 · certeza %{customdata[1]:.0f}<extra></extra>',
      customdata: E.map(e => [q.ejes[e.id].m, q.ejes[e.id].cert]) }],
      lay(440, { margin: { l: 255, r: 14, t: 10, b: 30 }, xaxis: { range: [0, 100] }, yaxis: { autorange: 'reversed' } }));
    const fg = (q.figuras || []).slice(0, 15).reverse();
    plot('e-figs', [{ type: 'bar', orientation: 'h', y: fg.map(f => f.nombre), x: fg.map(f => f.pct), marker: { color: C.b }, hovertemplate: '%{y}: %{x:.1f}%<extra></extra>' }],
      lay(440, { margin: { l: 170, r: 10, t: 10, b: 30 } }));
    const vars = [['genero', 'Género'], ['edad_g', 'Edad'], ['region', 'Región'], ['red', 'Red principal'], ['pais_res', 'País']];
    chips('e-var', vars, S.var, v => { S.var = v; encuesta() });
    const seg = q.por[S.var] || {};
    const gs = Object.keys(seg);
    const cx = ['Total', ...gs], cz = E.map(e => [q.ejes[e.id].cert, ...gs.map(g => seg[g].ejes[e.id].cert)]);
    plot('e-cert', [{ type: 'heatmap', x: cx.map((g, i) => i ? `${g} · media ${fmt(seg[g].certeza)}` : `Total · media ${fmt(q.certeza)}`), y: E.map(e => e.nombre), z: cz, zmin: 0, zmax: 70,
      colorscale: [[0, '#10151d'], [1, C.pos]], showscale: false, text: cz.map(r => r.map(v => v == null ? '' : v.toFixed(0))), texttemplate: '%{text}',
      hovertemplate: '%{x}<br>%{y}: certeza %{z:.0f}<extra></extra>' }], lay(400, { margin: { l: 110, r: 10, t: 10, b: 60 }, yaxis: { autorange: 'reversed' } }));
    if (gs.length) {
      const z = E.map(e => gs.map(g => seg[g].ejes[e.id].m));
      plot('e-seg', [{ type: 'heatmap', x: gs.map(g => `${g} (n ${seg[g].n})`), y: E.map(e => `${e.a} ↔ ${e.b}`), z, zmin: 20, zmax: 80, zmid: 50,
        colorscale: [[0, C.a], [.5, '#10151d'], [1, C.b]], text: z.map(r => r.map(v => v.toFixed(0))), texttemplate: '%{text}', showscale: false,
        hovertemplate: '%{x}<br>%{y}: %{z:.1f}<extra></extra>' }], lay(440, { margin: { l: 255, r: 10, t: 10, b: 60 }, yaxis: { autorange: 'reversed' } }));
    } else empty('e-seg', 'Ningún grupo llega al mínimo de respuestas todavía.');
    chips('e-eje', E.map(e => [e.id, e.nombre]), S.eje, v => { S.eje = v; encuesta() });
    heat('e-eg', q.edad_genero, 'edad_g', 'genero');
    heat('e-re', q.region_edad, 'region', 'edad_g');
    const brs = [['brecha_jovenes', 'Varones vs. mujeres jóvenes'], ['brecha_genero', 'Varones vs. mujeres'], ['brecha_edad', '16-24 vs. 50+']];
    chips('e-br', brs, S.br, v => { S.br = v; encuesta() });
    const pr = (q.preguntas || []).filter(p => p[S.br] != null).sort((a, b) => Math.abs(b[S.br]) - Math.abs(a[S.br])).slice(0, 10);
    const lab = { brecha_jovenes: ['varon_joven', 'mujer_joven', 'Varones 16-34', 'Mujeres 16-34'], brecha_genero: ['varon', 'mujer', 'Varones', 'Mujeres'], brecha_edad: ['jov', 'may', '16-24', '50+'] }[S.br];
    $('#e-preg').innerHTML = pr.length ? `<table><thead><tr><th>Frase</th><th class="n">Total</th><th class="n">${lab[2]}</th><th class="n">${lab[3]}</th><th class="n">Brecha</th></tr></thead><tbody>` +
      pr.map(p => `<tr><td>${esc(p.t)}</td><td class="n">${fmt(p.acuerdo)}%</td><td class="n">${fmt(p[lab[0]])}%</td><td class="n">${fmt(p[lab[1]])}%</td><td class="n" style="color:${p[S.br] > 0 ? C.b : C.a}">${p[S.br] > 0 ? '+' : ''}${fmt(p[S.br])}</td></tr>`).join('') +
      '</tbody></table><p class="note">% de acuerdo (de acuerdo + muy de acuerdo). Brecha en puntos porcentuales.</p>' : '<div class="empty">Hace falta más n por grupo.</div>';
    $('#e-tribus').innerHTML = (q.segmentos || []).map(s => {
      const comp = Object.entries(s.composicion.edad_g || {}).slice(0, 2).map(([k, v]) => `${k} ${fmt(v)}%`).join(' · ');
      const gen = Object.entries(s.composicion.genero || {}).slice(0, 2).map(([k, v]) => `${k} ${fmt(v)}%`).join(' · ');
      return `<div class="seg"><h4>${esc(s.nombre)}</h4><div class="p">${fmt(s.pct, 1)}%</div><small>${esc(gen)}<br>${esc(comp)}<br>Red: ${esc(Object.keys(s.composicion.red || {})[0] || '—')}<br>Cerca de: ${esc((s.figuras || []).map(f => f.nombre).join(', '))}</small></div>`;
    }).join('') || '<div class="empty">Las tribus aparecen con más respuestas.</div>';
    const d = (S.Q.campo || {}).por_dia || {};
    plot('e-campo', [{ type: 'bar', x: Object.keys(d), y: Object.values(d), marker: { color: C.b } }], lay(200, { margin: { l: 40, r: 10, t: 10, b: 30 } }));
  }
  function heat(id, cells, v1, v2) {
    cells = cells || [];
    if (!cells.length) return empty(id, 'Ningún cruce llega al mínimo de respuestas todavía.');
    const xs = [...new Set(cells.map(c => c[v2]))], ys = [...new Set(cells.map(c => c[v1]))].sort();
    const z = ys.map(y => xs.map(x => { const c = cells.find(c => c[v1] === y && c[v2] === x); return c ? c.ejes[S.eje] : null }));
    const e = ejeN(S.eje);
    plot(id, [{ type: 'heatmap', x: xs, y: ys, z, zmin: 20, zmax: 80, zmid: 50, colorscale: [[0, C.a], [.5, '#10151d'], [1, C.b]], showscale: false,
      text: z.map(r => r.map(v => v == null ? '' : v.toFixed(0))), texttemplate: '%{text}', hovertemplate: `%{y} · %{x}<br>${esc(e.a)} 0 ↔ ${esc(e.b)} 100: %{z:.1f}<extra></extra>` }],
      lay(260, { margin: { l: 90, r: 10, t: 10, b: 40 } }));
  }

  // ------------------------------------------------------------------ conversación
  function conversacion() {
    const L = S.L.ejes;
    if (!L) { ['c-vol', 'c-tono', 'c-sem', 'c-sov', 'c-plat', 'c-ads', 'c-hl'].forEach(i => empty(i, 'Esperando la primera corrida del listener.')); return }
    const E = S.E.ejes;
    plot('c-vol', [{ type: 'bar', x: E.map(e => e.nombre), y: E.map(e => L[e.id].n), marker: { color: PAL }, hovertemplate: '%{x}: %{y} textos<extra></extra>' }], lay(300, { margin: { l: 40, r: 10, t: 10, b: 60 } }));
    const tr = (k, c, n) => ({ type: 'bar', name: n, x: E.map(e => e.nombre), y: E.map(e => (L[e.id].tono || {})[k] || 0), marker: { color: c }, hovertemplate: `%{x}<br>${n}: %{y:.0f}%<extra></extra>` });
    plot('c-tono', [tr('neg', C.neg, 'Negativo'), tr('neu', C.neu, 'Neutro'), tr('pos', C.pos, 'Positivo')], lay(300, { barmode: 'stack', showlegend: true, legend: { orientation: 'h', y: 1.1 }, margin: { l: 40, r: 10, t: 20, b: 60 } }));
    plot('c-sem', E.map((e, i) => { const s = L[e.id].semanas || {}; return { x: Object.keys(s), y: Object.values(s), name: e.nombre, mode: 'lines', line: { color: PAL[i], width: 2 } } }),
      lay(280, { showlegend: true, legend: { orientation: 'h', y: 1.12 }, margin: { l: 40, r: 10, t: 20, b: 30 } }));
    const fs = Object.entries(S.L.figuras || {}).filter(([, f]) => f.n).sort((a, b) => b[1].n - a[1].n).slice(0, 18).reverse();
    if (fs.length) plot('c-sov', [{ type: 'bar', orientation: 'h', y: fs.map(f => f[0]), x: fs.map(f => f[1].sov), customdata: fs.map(f => [f[1].n, (f[1].tono || {}).neto]),
      marker: { color: fs.map(f => (f[1].tono || {}).neto == null ? C.neu : f[1].tono.neto >= 0 ? C.pos : C.neg) },
      hovertemplate: '%{y}: %{x:.1f}% · %{customdata[0]} menciones<br>tono neto %{customdata[1]}<extra></extra>' }], lay(440, { margin: { l: 170, r: 10, t: 10, b: 30 } }));
    else empty('c-sov', 'Sin menciones todavía.');
    const P = S.L.plataformas || {}, ps = Object.keys(P);
    if (ps.length) plot('c-plat', [{ type: 'heatmap', x: ps, y: E.map(e => e.nombre), z: E.map(e => ps.map(p => P[p].ejes[e.id])), colorscale: [[0, '#0b0f15'], [1, C.b]], showscale: false,
      texttemplate: '%{z}', hovertemplate: '%{x} · %{y}: %{z}<extra></extra>' }], lay(440, { margin: { l: 120, r: 10, t: 10, b: 60 }, yaxis: { autorange: 'reversed' } }));
    const A = S.L.anuncios || {}, ak = Object.keys(A);
    $('#c-ads').innerHTML = ak.length ? `<table><thead><tr><th>Eje</th><th class="n">Avisos</th><th>Páginas que más pautan</th></tr></thead><tbody>` +
      ak.map(k => `<tr><td>${esc(ejeN(k).nombre)}</td><td class="n">${fmt(A[k].avisos)}</td><td>${esc((A[k].paginas || []).slice(0, 3).map(p => p.p).join(', '))}</td></tr>`).join('') + '</tbody></table>'
      : '<div class="empty">La Biblioteca de Anuncios todavía no respondió.</div>';
    chips('c-hl-sel', E.map(e => [e.id, e.nombre]), S.hl, v => { S.hl = v; conversacion() });
    $('#c-hl').innerHTML = (L[S.hl].titulares || []).map(h => `<a href="${esc(h.url)}" target="_blank" rel="noopener noreferrer">${esc(h.t)}<small>${esc(h.medio)} · ${esc(h.f)}</small></a>`).join('') || '<div class="empty">Sin titulares.</div>';
  }

  // ------------------------------------------------------------------ cruce
  function cruce() {
    const ag = (S.X.agenda || []).filter(a => a.divide != null && a.se_habla != null);
    if (ag.length) plot('x-agenda', [{ x: ag.map(a => a.divide), y: ag.map(a => a.se_habla), text: ag.map(a => a.nombre), mode: 'markers+text', textposition: 'top center',
      marker: { size: 12, color: C.b }, textfont: { size: 11, color: '#98a2b2' }, hovertemplate: '%{text}<br>Divide %{x:.0f}% · se habla %{y:.0f}%<extra></extra>' }],
      lay(320, { margin: { l: 44, r: 10, t: 10, b: 40 }, xaxis: { title: { text: '% con posición fuerte en el quiz' } }, yaxis: { title: { text: '% de la conversación' } } }));
    else empty('x-agenda', 'Hacen falta datos de las dos fuentes.');
    const br = (S.X.ejes || []).filter(e => e.brecha != null);
    if (br.length) plot('x-brecha', [{ type: 'bar', orientation: 'h', y: br.map(e => `${e.a} ↔ ${e.b}`), x: br.map(e => e.brecha), marker: { color: br.map(e => e.brecha >= 0 ? C.b : C.a) },
      hovertemplate: '%{y}<br>%{x:+.0f} puntos<extra></extra>' }], lay(440, { margin: { l: 255, r: 10, t: 10, b: 30 }, yaxis: { autorange: 'reversed' } }));
    else empty('x-brecha', 'El encuadre aparece con 20+ textos por eje y respuestas del quiz.');
    const pl = S.X.plataformas || [];
    $('#x-plat').innerHTML = pl.length ? `<table><thead><tr><th>Se informa por</th><th class="n">n</th>${S.E.ejes.map(e => `<th class="n" title="${esc(e.a)} 0 ↔ ${esc(e.b)} 100">${esc(e.nombre)}</th>`).join('')}<th>Dirigente más elegido</th><th class="n">Tono en esa red</th></tr></thead><tbody>` +
      pl.map(p => `<tr><td>${esc(p.red)}</td><td class="n">${fmt(p.n_quiz)}</td>${S.E.ejes.map(e => `<td class="n" style="color:${p.perfil[e.id] >= 55 ? C.b : p.perfil[e.id] <= 45 ? C.a : C.txt}">${fmt(p.perfil[e.id])}</td>`).join('')}<td>${esc(p.figura || '—')}</td><td class="n">${p.tono == null ? '—' : (p.tono > 0 ? '+' : '') + fmt(p.tono)}</td></tr>`).join('') + '</tbody></table>'
      : '<div class="empty">Hace falta n por red social.</div>';
    const ad = S.X.anuncios || [];
    $('#x-ads').innerHTML = ad.length ? `<table><thead><tr><th>Eje</th><th class="n">Avisos</th><th>Público principal</th><th class="n">Posición del público</th><th class="n">Posición total</th></tr></thead><tbody>` +
      ad.map(a => `<tr><td>${esc(a.nombre)}</td><td class="n">${fmt(a.avisos)}</td><td>${esc(a.publico.map(p => `${p.genero} ${p.edad} (${fmt(p.pct)}%)`).join(' · '))}</td><td class="n">${fmt(a.posicion_publico, 1)}</td><td class="n">${fmt(a.posicion_total, 1)}</td></tr>`).join('') + '</tbody></table>'
      : '<div class="empty">Sin avisos de Meta cruzables todavía.</div>';
    const f = (S.X.figuras || []).filter(x => x.afinidad || x.sov).slice();
    if (f.length) {
      const top = [...f.slice(0, 8), ...f.slice(-8)].filter((x, i, a) => a.indexOf(x) === i);
      plot('x-figs', [{ type: 'bar', orientation: 'h', y: top.map(x => x.nombre), x: top.map(x => x.brecha), marker: { color: top.map(x => x.brecha >= 0 ? C.pos : C.neg) },
        hovertemplate: '%{y}<br>afinidad − sov: %{x:+.1f}<extra></extra>' }], lay(420, { margin: { l: 170, r: 10, t: 10, b: 30 }, yaxis: { autorange: 'reversed' } }));
    } else empty('x-figs', 'Sin datos todavía.');
  }

  // ------------------------------------------------------------------ resumen accionable
  function resumen() {
    const hoy = new Date().toLocaleDateString('es-AR', { day: 'numeric', month: 'long', year: 'numeric' });
    const q = (S.Q.versiones || {}).ar || {};
    const acc = S.X.acciones || [];
    const top = acc[0];
    const dom = (S.X.ejes || []).filter(e => e.share != null).sort((a, b) => b.share - a.share).slice(0, 2).map(e => e.nombre.toLowerCase());
    $('#rs').innerHTML = `<div class="rs-k">Resumen accionable</div><h2>Opinión y conversación</h2><div class="note">Argentina · ${esc(hoy)} · quiz n = ${fmt(q.n)} · ${fmt((S.L.totales || {}).textos)} textos escuchados</div>
      ${top ? `<p style="margin-top:16px;font-size:16px"><b>${esc(top.accion)}</b> ${esc(top.metrica)}</p>` : '<p>El resumen se arma cuando hay datos de las dos fuentes.</p>'}
      ${dom.length ? `<p>La conversación está dominada por ${esc(dom.join(' y '))}.</p>` : ''}
      <div class="rs-t">Acciones</div><ol class="acc">${acc.map(a => `<li><b>${esc(a.accion)}</b><small>${esc(a.metrica)}</small></li>`).join('')}</ol>
      <div class="rs-t">Alertas</div><ul>${(S.X.alertas || []).map(a => `<li>${esc(a.t)}</li>`).join('') || '<li>Sin alertas.</li>'}</ul>
      <div class="rs-t">Ficha</div><p class="note">Encuesta: ${esc(q.ponderacion || '—')}, n efectivo ${fmt(q.n_efectivo)}. Escucha: Google News, YouTube, Biblioteca de Anuncios de Meta, Instagram y X.</p>`;
    $('#pdf').onclick = () => { $$('.tab').forEach(t => t.classList.toggle('on', t.id === 't-resumen')); window.print() };
  }

  // ------------------------------------------------------------------ método
  function metodo() {
    const st = Object.assign({}, S.L.status || {});
    st.quiz = { ok: !!(S.Q.campo || {}).validas, items: (S.Q.campo || {}).validas, at: S.Q.updated_at };
    $('#m-st').innerHTML = '<thead><tr><th>Fuente</th><th>Estado</th><th class="n">Ítems</th><th>Detalle</th></tr></thead><tbody>' +
      Object.entries(st).map(([k, v]) => `<tr><td>${esc(k)}</td><td class="${v.ok ? 'ok' : 'ko'}">${v.ok ? 'OK' : 'Falla'}</td><td class="n">${fmt(v.items)}</td><td>${esc(v.error || v.nota || (v.at || '').slice(0, 16).replace('T', ' '))}</td></tr>`).join('') + '</tbody>';
    const q = (S.Q.versiones || {}).ar || {}, c = S.Q.campo || {};
    $('#m-ficha').innerHTML = `<table><tbody>
      <tr><td>Universo</td><td>Personas de 16 años o más que hacen el quiz y aceptan sumar sus respuestas</td></tr>
      <tr><td>Modo</td><td>Online, autoadministrado, anónimo</td></tr>
      <tr><td>Fechas</td><td>${esc(Object.keys(c.por_dia || {})[0] || '—')} a ${esc(Object.keys(c.por_dia || {}).pop() || '—')}</td></tr>
      <tr><td>Casos</td><td>${fmt(c.recibidas)} recibidos · ${fmt(c.validas)} válidos · ${esc(Object.entries(c.descartes || {}).map(([k, v]) => `${k}: ${v}`).join(', ') || 'sin descartes')}</td></tr>
      <tr><td>Argentina</td><td>n ${fmt(q.n)} · n efectivo ${fmt(q.n_efectivo)} · ${esc(q.ponderacion || '—')}</td></tr>
      <tr><td>Publicación</td><td>Solo grupos con ${fmt(S.Q.min_n)}+ respuestas</td></tr></tbody></table>`;
    const m = Object.assign({}, S.Q.metodo || {}, S.L.metodo || {}, S.X.metodo || {});
    $('#m-met').innerHTML = Object.entries(m).map(([k, v]) => `<p><b>${esc(k)}</b> · <span class="note">${esc(v)}</span></p>`).join('');
  }

  // ------------------------------------------------------------------ pestañas y arranque
  const PINTA = { panorama, encuesta, conversacion, cruce, resumen, metodo }, hecho = {};
  function tab(t) {
    $$('#tabs button').forEach(b => b.classList.toggle('on', b.dataset.t === t));
    $$('.tab').forEach(s => s.classList.toggle('on', s.id === 't-' + t));
    if (!hecho[t]) { hecho[t] = 1; PINTA[t]() }
    window.dispatchEvent(new Event('resize'));
  }
  $('#tabs').onclick = ev => { const b = ev.target.closest('button'); if (b) tab(b.dataset.t) };
  const get = p => fetch(p, { cache: 'no-cache' }).then(r => r.ok ? r.json() : {}).catch(() => ({}));
  Promise.all([get('datos/ejes.json'), get('datos/figuras.json'), get(BASE + 'quiz.json'), get(BASE + 'listener.json'), get(BASE + 'cruce.json')]).then(([e, f, q, l, x]) => {
    S.E = e; S.figs = f.ar || []; S.Q = q; S.L = l; S.X = x;
    cabecera(); tab('panorama'); resumen();
  });
})();
