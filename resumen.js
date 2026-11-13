/* Pestañas "Meta" y "Resumen accionable" del tablero nacional.
   - Meta: Instagram (Business Discovery) y Biblioteca de Anuncios, desde meta/data/meta.json.
   - Resumen accionable: informe por dirigente, armado con reglas sobre los agregados del Radar, Meta y la
     agenda vacante. Se descarga como PDF con la impresión del navegador.
   - Prompt para videos: no se ve en la página. Se abre con Alt+Shift+P o con el punto "·" al pie del informe,
     y queda en window.Resumen.prompt(). */
(function () {
  const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const fmt = n => n == null ? '—' : Number(n).toLocaleString('es-AR');
  const kfmt = n => n == null ? '—' : n >= 1e6 ? (n / 1e6).toLocaleString('es-AR', { maximumFractionDigits: 1 }) + ' M' : n >= 1e4 ? Math.round(n / 1e3).toLocaleString('es-AR') + ' mil' : fmt(n);
  const pct = (x, d = 0) => x == null ? '—' : Number(x).toLocaleString('es-AR', { maximumFractionDigits: d }) + '%';
  const J = u => fetch(u, { cache: 'no-cache' }).then(r => r.ok ? r.json() : null).catch(() => null);
  const med = a => { const b = a.filter(x => x != null && !isNaN(x)).sort((x, y) => x - y); if (!b.length) return null; const m = b.length >> 1; return b.length % 2 ? b[m] : (b[m - 1] + b[m]) / 2 };
  const list = a => a.length <= 1 ? (a[0] || '') : a.slice(0, -1).join(', ') + ' y ' + a[a.length - 1];
  const cap = s => s ? s[0].toUpperCase() + s.slice(1) : s;
  const C = { s1: '#13161d', grid: '#232834', line: '#272c38', txt: '#eef0f4', muted: '#a6adbb', dim: '#717887' };
  const GCOL = { 'País': '#3987e5', 'Boca': '#c98500', 'Provincia de Buenos Aires': '#199e70', 'CABA': '#d55181', 'San Isidro': '#9085e9' };
  const GEN = { female: 'mujeres', male: 'varones', unknown: 'sin dato' };
  const EMO = { ira: 'enojo', asco: 'rechazo', miedo: 'miedo', tristeza: 'tristeza', alegria: 'alegría', sorpresa: 'sorpresa' };
  const BASE = {
    paper_bgcolor: C.s1, plot_bgcolor: C.s1, font: { family: 'Inter,system-ui,sans-serif', color: C.txt, size: 11.5 }, margin: { l: 50, r: 16, t: 16, b: 40 },
    hoverlabel: { bgcolor: '#0b0d12', bordercolor: C.line }, legend: { orientation: 'h', y: -0.2, font: { color: C.muted } },
    xaxis: { gridcolor: C.grid, zerolinecolor: C.line, linecolor: C.line, tickfont: { color: C.muted } }, yaxis: { gridcolor: C.grid, zerolinecolor: C.line, linecolor: C.line, tickfont: { color: C.muted } }
  };
  const mergeL = (a, b) => { const o = JSON.parse(JSON.stringify(a)); for (const k in b) o[k] = (b[k] && typeof b[k] === 'object' && !Array.isArray(b[k]) && o[k] && typeof o[k] === 'object') ? mergeL(o[k], b[k]) : b[k]; return o };
  const P = (el, d, l) => window.Plotly && Plotly.react(el, d, mergeL(BASE, l || {}), { responsive: true, displaylogo: false, modeBarButtonsToRemove: ['lasso2d', 'select2d', 'toImage'] });

  const D = { ready: null, A: [], byName: {}, L: null, M: null, MG: null, sel: null, grupo: '', prompt: '' };
  D.ready = Promise.all([J('radar/data/actors.json'), J('radar/data/live.json'), J('meta/data/meta.json'), J('massa/data/massa.json')]).then(([A, L, M, MG]) => {
    D.A = A ? A.actors : []; D.byName = Object.fromEntries(D.A.map(a => [a.name, a])); D.L = L; D.M = M; D.MG = MG;
    D.meta = Object.fromEntries((M && M.dirigentes || []).map(d => [d.name, d]));
    // "Juan Román Riquelme" en Meta y en el Radar comparten nombre; alias por si el Radar todavía no lo tiene
    D.sel = (() => { try { return localStorage.getItem('resumen-sel') } catch (e) { return null } })() || 'Sergio Massa';
  });

  /* ================================================================ META ================================================================ */
  const metaOK = () => D.M && D.M.estado === 'ok';
  function drawMeta() {
    const host = $('#meta-body'); if (!host) return;
    const M = D.M;
    if (!M) { host.innerHTML = '<div class="empty">Todavía no hay datos de Meta publicados.</div>'; return }
    const rows = M.dirigentes || [];
    const grupos = M.grupos || [...new Set(rows.map(r => r.grupo))];
    $('#meta-g').innerHTML = ['', ...grupos].map(g => `<button class="pill ${g === D.grupo ? 'on' : ''}" data-g="${esc(g)}">${g ? esc(g) : 'Todos'}</button>`).join('');
    $$('#meta-g .pill').forEach(b => b.onclick = () => { D.grupo = b.dataset.g; drawMeta() });
    $('#meta-upd').textContent = M.updated_at ? 'ACT ' + new Date(M.updated_at).toLocaleString('es-AR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }) : '';
    const R = rows.filter(r => !D.grupo || r.grupo === D.grupo);
    if (!metaOK()) {
      host.innerHTML = `<div class="mg-warn">Falta conectar la cuenta de Meta: el tablero ya sabe a quién medir, pero necesita un token gratuito para leer Instagram y la Biblioteca de Anuncios.</div>
      <div class="g"><div class="card c7"><h3>A quién se mide <span class="tag">${rows.length} dirigentes</span></h3>${grupoTabla(R)}</div>
      <div class="card c5"><h3>Qué se va a ver acá</h3><ul class="mg-ol">
        <li><b>Instagram:</b> seguidores y su evolución, publicaciones por semana, interacción mediana, tasa de interacción, qué formato rinde más (Reel, carrusel, foto) y en qué día y franja horaria.</li>
        <li><b>Pauta política en Facebook e Instagram:</b> cantidad de avisos, gasto e impresiones (en rangos, como los publica Meta), a qué provincias, edades y género llegaron.</li>
        <li><b>Comparación dentro de cada grupo:</b> País, Boca, Provincia (con Tigre), CABA y San Isidro.</li></ul>
        <p class="note">Las dos fuentes son de la API oficial de Meta y son gratis. Facebook (páginas) queda afuera: Meta exige revisión de la app para leer páginas ajenas.</p></div></div>`;
      return;
    }
    const ok = R.filter(r => r.ig), adsAll = R.filter(r => r.ads && r.ads.n);
    const fol = ok.reduce((s, r) => s + r.ig.followers, 0);
    const bestER = ok.slice().sort((a, b) => (b.ig.er || 0) - (a.ig.er || 0))[0];
    const activos = R.reduce((s, r) => s + (r.ads && r.ads.activos || 0), 0);
    const gasto = R.reduce((s, r) => [s[0] + (r.ads && r.ads.gasto ? r.ads.gasto[0] : 0), s[1] + (r.ads && r.ads.gasto ? r.ads.gasto[1] : 0)], [0, 0]);
    const K = [['Dirigentes medidos', `${ok.length}/${R.length}`, 'con cuenta de Instagram encontrada'], ['Seguidores sumados', kfmt(fol), 'en Instagram'],
      ['Mejor interacción', bestER ? pct(bestER.ig.er, 2) : '—', bestER ? bestER.name : ''], ['Publicaciones por semana', med(ok.map(r => r.ig.posts_semana))?.toLocaleString('es-AR', { maximumFractionDigits: 1 }) ?? '—', 'mediana del grupo'],
      ['Avisos políticos activos', fmt(activos), `${adsAll.length} dirigentes con pauta en ${D.M.ads_days || 90} días`], ['Gasto en pauta', gasto[1] ? `${kfmt(gasto[0])}–${kfmt(gasto[1])}` : '—', 'pesos, rango informado por Meta']];
    const miss = R.filter(r => !r.ig);
    host.innerHTML = `<div class="kpis">${K.map(([l, v, d]) => `<div class="kpi"><div class="l">${l}</div><div class="v">${v}</div><div class="d">${esc(d)}</div></div>`).join('')}</div>
      ${D.M.ads_error ? `<div class="mg-warn">La Biblioteca de Anuncios respondió con error (${esc(D.M.ads_error)}). Suele ser que falta confirmar identidad en facebook.com/ID.</div>` : ''}
      <div class="g">
        <div class="card c12"><h3>Ranking en Instagram <span class="tag">últimos 30 días</span></h3><div style="overflow-x:auto"><table class="rank" id="meta-t"></table></div>
          ${miss.length ? `<p class="note">Sin cuenta encontrada: ${miss.map(r => esc(r.name)).join(', ')}. Se corrige el usuario en meta/config.json.</p>` : ''}</div>
        <div class="card c6"><h3>Seguidores <span class="tag">Instagram</span></h3><div id="meta-fol" style="height:${Math.max(260, 34 * ok.length + 60)}px"></div></div>
        <div class="card c6"><h3>Frecuencia vs. interacción <span class="tag">burbuja = seguidores</span></h3><div id="meta-sc" style="height:${Math.max(260, 34 * ok.length + 60)}px"></div></div>
        <div class="card c6"><h3>Qué formato rinde <span class="tag">interacción mediana por publicación</span></h3><div id="meta-fmt" style="height:340px"></div></div>
        <div class="card c6"><h3>Cuándo rinde publicar <span class="tag">franja horaria · hora argentina</span></h3><div id="meta-hr" style="height:340px"></div></div>
        <div class="card c12"><h3>Pauta política en Facebook e Instagram <span class="tag">Biblioteca de Anuncios · ${D.M.ads_days || 90} días</span></h3><div id="meta-ads"></div></div>
        <div class="card c12"><h3>Publicaciones con más interacción</h3><div id="meta-top"></div></div>
      </div>`;
    const S = ok.slice().sort((a, b) => b.ig.followers - a.ig.followers);
    const dl = d => d == null ? '<span class="num" style="color:var(--dim)">—</span>' : `<span class="num">${d >= 0 ? '+' : ''}${kfmt(d)}</span>`;
    $('#meta-t').innerHTML = `<thead><tr><th>Dirigente</th><th>Grupo</th><th class="num">Seguidores</th><th class="num">7 días</th><th class="num">Posts/sem.</th><th class="num">Interacción</th><th class="num">Tasa</th><th>Mejor formato</th><th>Mejor momento</th><th class="num">Avisos</th></tr></thead><tbody>${S.map(r => `<tr class="click" data-rgo="${esc(r.name)}">
      <td><b>${esc(r.name)}</b><br><a href="https://www.instagram.com/${esc(r.ig.usuario)}/" target="_blank" rel="noopener" style="font-size:11.5px">@${esc(r.ig.usuario)}</a></td>
      <td><span class="mg-sw" style="background:${GCOL[r.grupo] || '#5d6470'}"></span> ${esc(r.grupo)}${r.distrito ? ' · ' + esc(r.distrito) : ''}</td>
      <td class="num">${kfmt(r.ig.followers)}</td><td>${dl(r.ig.delta7)}</td><td class="num">${String(r.ig.posts_semana).replace('.', ',')}</td><td class="num">${kfmt(r.ig.inter_med)}</td><td class="num">${pct(r.ig.er, 2)}</td>
      <td>${esc(r.ig.mejor_formato || '—')}</td><td>${esc(momento(r.ig) || '—')}</td><td class="num">${r.ads && r.ads.n ? fmt(r.ads.n) : '—'}</td></tr>`).join('')}</tbody>`;
    $$('#meta-t tr[data-rgo]').forEach(tr => tr.onclick = e => { if (e.target.closest('a')) return; goResumen(tr.dataset.rgo) });
    const Sr = S.slice().reverse();
    P('meta-fol', [{ type: 'bar', orientation: 'h', y: Sr.map(r => r.name), x: Sr.map(r => r.ig.followers), marker: { color: Sr.map(r => GCOL[r.grupo] || '#5d6470') }, hovertemplate: '%{y}: %{x:,} seguidores<extra></extra>' }], { margin: { l: 150, r: 16, t: 8, b: 30 } });
    const mx = Math.max(...ok.map(r => r.ig.followers), 1);
    P('meta-sc', grupos.filter(g => ok.some(r => r.grupo === g)).map(g => { const x = ok.filter(r => r.grupo === g); return { type: 'scatter', mode: 'markers+text', name: g, x: x.map(r => r.ig.posts_semana), y: x.map(r => r.ig.er), text: x.map(r => r.name.split(' ').slice(-1)[0]), textposition: 'top center', textfont: { color: C.muted, size: 10.5 }, marker: { size: x.map(r => 10 + 34 * Math.sqrt(r.ig.followers / mx)), color: GCOL[g], opacity: .8, line: { width: 0 } }, hovertemplate: '%{text}<br>%{x} posts/semana · tasa %{y:.2f}%<extra></extra>' } }),
      { xaxis: { title: { text: 'publicaciones por semana', font: { color: C.dim } } }, yaxis: { title: { text: 'tasa de interacción %', font: { color: C.dim } } } });
    const FM = ['Reel', 'Carrusel', 'Foto', 'Video'], FC = { Reel: '#3987e5', Carrusel: '#199e70', Foto: '#c98500', Video: '#d55181' };
    P('meta-fmt', FM.map(f => ({ type: 'bar', name: f, x: S.map(r => r.name.split(' ').slice(-1)[0]), y: S.map(r => r.ig.formatos[f] ? r.ig.formatos[f].inter_med : null), marker: { color: FC[f] }, hovertemplate: `%{x} · ${f}: %{y:,}<extra></extra>` })), { barmode: 'group', margin: { l: 56, b: 70 } });
    const FR = ['00-03', '03-06', '06-09', '09-12', '12-15', '15-18', '18-21', '21-24'];
    P('meta-hr', [{ type: 'heatmap', x: FR, y: S.map(r => r.name), z: S.map(r => { const v = FR.map(f => r.ig.franjas[f] ?? null), m = Math.max(...v.filter(x => x != null), 1); return v.map(x => x == null ? null : Math.round(100 * x / m)) }), colorscale: [[0, '#13161d'], [.5, '#1d4f8c'], [1, '#3987e5']], showscale: false, hovertemplate: '%{y} · %{x} h: %{z}% de su mejor franja<extra></extra>' }], { margin: { l: 150, r: 10, t: 8, b: 40 }, xaxis: { type: 'category' } });
    // pauta
    const A2 = R.filter(r => r.ads).sort((a, b) => ((b.ads.gasto || [0, 0])[1]) - ((a.ads.gasto || [0, 0])[1]));
    const withAds = A2.filter(r => r.ads.n);
    $('#meta-ads').innerHTML = withAds.length ? `<div style="overflow-x:auto"><table class="rank"><thead><tr><th>Dirigente</th><th class="num">Avisos</th><th class="num">Activos</th><th class="num">Gasto (ARS)</th><th class="num">Impresiones</th><th>Dónde</th><th>A quién</th><th>Aviso más visto</th></tr></thead><tbody>${withAds.map(r => { const a = r.ads; const reg = Object.entries(a.regiones || {}).slice(0, 3), ed = Object.entries(a.edades || {}).sort((x, y) => y[1] - x[1])[0], gn = Object.entries(a.genero || {}).sort((x, y) => y[1] - x[1])[0]; return `<tr>
      <td><b>${esc(r.name)}</b></td><td class="num">${fmt(a.n)}</td><td class="num">${fmt(a.activos)}</td><td class="num">${kfmt(a.gasto[0])}–${kfmt(a.gasto[1])}</td><td class="num">${kfmt(a.impresiones[0])}–${kfmt(a.impresiones[1])}</td>
      <td>${reg.map(([k, v]) => `${esc(k)} ${pct(v)}`).join('<br>') || '—'}</td><td>${ed ? `${esc(ed[0])} años (${pct(ed[1])})` : '—'}${gn ? `<br>${esc(GEN[gn[0]] || gn[0])} ${pct(gn[1])}` : ''}</td>
      <td style="min-width:220px">${a.avisos && a.avisos[0] ? `<a href="${esc(a.avisos[0].u)}" target="_blank" rel="noopener">${esc(a.avisos[0].t)}</a><br><small style="color:var(--dim)">${esc(a.avisos[0].d)}</small>` : '—'}</td></tr>` }).join('')}</tbody></table></div>
      ${A2.length > withAds.length ? `<p class="note">Sin avisos políticos en ${D.M.ads_days || 90} días: ${A2.filter(r => !r.ads.n).map(r => esc(r.name)).join(', ')}.</p>` : ''}` : '<div class="empty">Ninguno de los dirigentes de este grupo tuvo avisos políticos en el período.</div>';
    $('#meta-top').innerHTML = `<div class="mg-facts">${S.filter(r => r.ig.top && r.ig.top[0]).map(r => { const t = r.ig.top[0]; return `<div class="mg-fact" style="border-top-color:${GCOL[r.grupo] || '#5d6470'}"><span><b style="font-size:13px;color:var(--txt)">${esc(r.name)}</b> · ${esc(t.f)} · ${esc(t.d)}</span><b>${kfmt(t.i)}</b><span>${esc(t.t || '(sin texto)')}</span><a href="${esc(t.u)}" target="_blank" rel="noopener">ver en Instagram ↗</a></div>` }).join('')}</div>`;
  }
  const momento = ig => [ig.mejor_dia, ig.mejor_franja != null ? `${String(ig.mejor_franja).padStart(2, '0')}-${String(+ig.mejor_franja + 3).padStart(2, '0')} h` : null].filter(Boolean).join(' · ');
  const grupoTabla = R => `<div style="overflow-x:auto"><table class="rank"><thead><tr><th>Grupo</th><th>Dirigentes</th></tr></thead><tbody>${[...new Set(R.map(r => r.grupo))].map(g => `<tr><td><span class="mg-sw" style="background:${GCOL[g] || '#5d6470'}"></span> ${esc(g)}</td><td>${R.filter(r => r.grupo === g).map(r => esc(r.name) + (r.distrito ? ` <small style="color:var(--dim)">(${esc(r.distrito)})</small>` : '')).join(', ')}</td></tr>`).join('')}</tbody></table></div>`;

  /* ================================================================ RESUMEN ================================================================ */
  // Pares: mismo grupo de Meta si lo tiene; si no, mismos país y espacio del Radar; si no, todo AR.
  function peers(name) {
    const m = D.meta[name];
    if (m) return (D.M.dirigentes || []).filter(d => d.grupo === m.grupo && d.name !== name).map(d => d.name);
    const a = D.byName[name]; if (!a) return [];
    let p = D.A.filter(x => x.pais === a.pais && x.espacio === a.espacio && x.name !== name);
    if (p.length < 3) p = D.A.filter(x => x.pais === a.pais && x.name !== name);
    return p.map(x => x.name);
  }
  // Diagnóstico: lista de acciones posibles con puntaje 0-100, cada una con su porqué en datos.
  function diagnose(name) {
    const a = D.byName[name], m = D.meta[name], ig = m && m.ig, ads = m && m.ads, pr = peers(name);
    const pa = pr.map(n => D.byName[n]).filter(Boolean), pm = pr.map(n => D.meta[n]).filter(x => x && x.ig);
    const acts = [], facts = {};
    const add = (k, score, titulo, verbo, porque, kpi, video) => acts.push({ k, score: Math.round(Math.max(0, Math.min(100, score))), titulo, verbo, porque, kpi, video });
    if (a && a.n) {
      const share = a.share, mshare = med(pa.map(x => x.share)), d = a.prev7 ? Math.round(100 * (a.last7 - a.prev7) / a.prev7) : null;
      Object.assign(facts, { n: a.n, share, mshare, d, tone: a.tone, tone_news: a.tone_news, base: a.tone_base, emo: a.emotions, pressure: a.pressure });
      if (mshare != null && share < mshare * 0.7) add('vis', 55 + 30 * (1 - share / Math.max(mshare, .01)), 'ganar conversación propia', 'ganar volumen de conversación propia',
        `tiene ${fmt(a.n)} menciones en 30 días (${pct(share, 1)} de la conversación), contra ${pct(mshare, 1)} de la mediana de sus pares`, 'menciones semanales y participación en la conversación', 'una idea fuerte, propia, que se pueda repetir en titulares');
      if (d != null && d >= 30 && a.last7 >= 10) add('mom', 50 + Math.min(35, d / 4), 'capitalizar la suba de esta semana', 'aprovechar el pico de atención',
        `sus menciones subieron ${d}% en 7 días (${fmt(a.last7)} contra ${fmt(a.prev7)})`, 'menciones en los próximos 7 días por encima de ' + fmt(a.last7), 'reacción rápida al tema del momento, con postura clara');
      if (d != null && d <= -30 && a.prev7 >= 10) add('caida', 45 + Math.min(35, -d / 3), 'reactivar presencia', 'volver a instalarse en la agenda',
        `sus menciones cayeron ${-d}% en 7 días (${fmt(a.last7)} contra ${fmt(a.prev7)})`, 'recuperar al menos ' + fmt(a.prev7) + ' menciones semanales', 'anuncio o propuesta concreta que dé un motivo nuevo para nombrarlo en la conversación');
      const neg = a.tone && a.tone.NEG, mneg = med(pa.map(x => x.tone && x.tone.NEG));
      const emoTop = a.emotions ? Object.entries(a.emotions).sort((x, y) => y[1] - x[1])[0] : null;
      facts.emoTop = emoTop;
      if (neg != null && neg >= 45) add('tono', 40 + (neg - 45) * 1.2 + (mneg != null && neg > mneg ? 10 : 0), 'bajar el tono negativo', 'cambiar el clima de la conversación sobre su figura',
        `${pct(neg)} de ${a.tone_base === 'redes' ? 'los comentarios' : 'los textos'} sobre su figura son negativos${mneg != null ? ` (sus pares: ${pct(mneg)})` : ''}${emoTop && emoTop[1] > 30 ? ` y la emoción dominante es ${EMO[emoTop[0]] || emoTop[0]} (${pct(emoTop[1])})` : ''}`,
        'porcentaje de comentarios negativos por debajo de ' + pct(Math.max(30, neg - 10)), emoTop && emoTop[0] === 'ira' ? 'empatía con el enojo y una solución concreta, sin confrontar' : emoTop && emoTop[0] === 'miedo' ? 'tranquilidad y orden, con datos' : 'cercanía y respuesta directa a la crítica más repetida');
      if (a.pressure >= 40) add('presion', 45 + (a.pressure - 40), 'contener la presión reputacional', 'ordenar una respuesta a la crítica',
        `su índice de presión reputacional es ${a.pressure}/100 (${Object.entries(a.pressure_parts || {}).sort((x, y) => y[1] - x[1]).slice(0, 2).map(([k, v]) => `${k} ${v}`).join(', ')})`, 'índice de presión por debajo de 40', 'respuesta breve, con datos verificables, a la acusación principal');
      const nar = (a.narratives || [])[0], co = (a.co || [])[0];
      if (nar && nar.pct >= 40) { const rivals = (a.co || []).slice(0, 3).map(c => c.a).filter(n => nar.n.includes(n.split(' ').slice(-1)[0].toLowerCase()));
        add('narr', 35 + (nar.pct - 40) * .8 + (rivals.length ? 10 : 0), rivals.length ? `despegarse de ${list(rivals)}` : 'diversificar sus temas', rivals.length ? `construir una agenda propia, fuera de la sombra de ${list(rivals)}` : 'ampliar su agenda',
          `${pct(nar.pct)} de lo que se dice sobre su figura gira alrededor de «${nar.n}»${co ? ` y su compañía más frecuente en los textos es ${co.a} (${fmt(co.n)} veces)` : ''}`, 'una segunda narrativa que supere el 20% de sus menciones', 'tema propio, sin nombrar a los otros dirigentes') }
      const prov = Object.entries(a.provinces || {}).sort((x, y) => y[1] - x[1]);
      facts.prov = prov;
    }
    // Agenda vacante (temas con cobertura y sin dirigente que los encabece)
    const ag = (D.MG && D.MG.agenda || []).filter(t => t.pct_sin_dirigente >= 90).sort((x, y) => (y.n * (1 + Math.max(0, y.delta4) / 100)) - (x.n * (1 + Math.max(0, x.delta4) / 100)));
    if (ag[0]) { const t = ag[0]; facts.vacante = t;
      add('vac', 45 + Math.min(30, t.delta4 / 6) + (a && a.n < 100 ? 8 : 0), `tomar la bandera de «${t.corto}»`, `ocupar un tema que nadie está liderando: ${t.corto.toLowerCase()}`,
        `«${t.tema}» suma ${fmt(t.n)} notas en ${fmt(t.medios)} medios${t.delta4 ? ` (${t.delta4 > 0 ? '+' : ''}${t.delta4}% en las últimas 4 semanas)` : ''} y en ${pct(t.pct_sin_dirigente)} de ellas no aparece ningún dirigente`,
        'aparecer en notas del tema dentro de 4 semanas', `propuesta concreta sobre ${t.corto.toLowerCase()}, contada con un caso real`) }
    // Instagram
    if (ig) {
      facts.ig = ig;
      const allMed = ig.inter_med || 1, f = ig.mejor_formato && ig.formatos[ig.mejor_formato], fr = f ? f.inter_med / allMed : 1;
      const mps = med(pm.map(x => x.ig.posts_semana)), mer = med(pm.map(x => x.ig.er));
      if (f && fr >= 1.25 && f.n >= 2) add('fmt', 40 + Math.min(35, (fr - 1) * 40), `priorizar ${ig.mejor_formato === 'Reel' ? 'Reels' : ig.mejor_formato.toLowerCase() + 's'}`, `concentrar la producción en ${ig.mejor_formato.toLowerCase()}`,
        `en Instagram sus ${ig.mejor_formato.toLowerCase()}s tienen una interacción mediana de ${kfmt(f.inter_med)}, ${fr.toLocaleString('es-AR', { maximumFractionDigits: 1 })} veces su promedio${momento(ig) ? `, y su mejor momento para publicar es ${momento(ig)}` : ''}`,
        `interacción mediana por encima de ${kfmt(Math.round(allMed * 1.2))} por publicación`, null);
      if (mps != null && ig.posts_semana < mps * 0.7) add('freq', 40 + 30 * (1 - ig.posts_semana / Math.max(mps, .1)), 'publicar más seguido', 'sostener una presencia constante en redes',
        `publica ${String(ig.posts_semana).replace('.', ',')} veces por semana en Instagram; la mediana de su grupo es ${mps.toLocaleString('es-AR', { maximumFractionDigits: 1 })}`, `al menos ${Math.ceil(mps)} publicaciones por semana`, null);
      if (mer != null && ig.er != null && ig.er < mer * 0.7) add('er', 40 + 30 * (1 - ig.er / Math.max(mer, .001)), 'mejorar la interacción en Instagram', 'conseguir que su audiencia participe',
        `su tasa de interacción es ${pct(ig.er, 2)} por publicación contra ${pct(mer, 2)} de su grupo: tiene ${kfmt(ig.followers)} seguidores pero responden poco`, `tasa de interacción por encima de ${pct(mer, 2)}`, 'preguntas a cámara y pedidos de opinión');
      if (mer != null && ig.er != null && ig.er > mer * 1.4) add('er+', 30 + Math.min(20, (ig.er / mer - 1) * 15), 'usar su comunidad como megáfono', 'convertir su comunidad digital en difusión',
        `su tasa de interacción (${pct(ig.er, 2)}) supera a la de su grupo (${pct(mer, 2)})`, 'compartidos y menciones de terceros', 'pedido explícito de compartir, con un mensaje simple');
    }
    if (ads) {
      facts.ads = ads;
      const pAds = pr.map(n => D.meta[n]).filter(x => x && x.ads && x.ads.n);
      if (!ads.n && pAds.length && metaOK()) add('pauta0', 35 + 8 * pAds.length, 'abrir pauta segmentada', 'sumar pauta digital chica y medida',
        `no tuvo avisos políticos en ${D.M.ads_days || 90} días, mientras ${list(pAds.slice(0, 3).map(x => x.name))} sí pautaron`, 'primeros avisos con costo por mil impresiones medido', 'versión corta del mejor video orgánico para pautar');
      if (ads.n && ads.regiones) { const r = Object.entries(ads.regiones)[0]; if (r && r[1] >= 70) add('pautareg', 30 + (r[1] - 70), 'ampliar el alcance de la pauta', 'llevar su pauta más allá de su base',
        `${pct(r[1])} de las impresiones de sus ${fmt(ads.n)} avisos fueron a ${r[0]}`, 'al menos 3 provincias con más de 10% de impresiones', null) }
    }
    const al = (D.L && D.L.alerts || []).filter(x => x.actor === name && x.nivel === 'alta');
    if (al.length) { facts.alerts = al; add('alerta', 50 + 5 * al.length, 'responder la alerta activa', 'responder rápido a la crítica del momento',
      `tiene ${al.length} alerta${al.length > 1 ? 's' : ''} alta${al.length > 1 ? 's' : ''}: «${al[0].titulo}»`, 'que la alerta no se repita la semana siguiente', 'aclaración breve, con la fuente a la vista') }
    if (!acts.length) add('base', 30, 'sostener lo que funciona', 'consolidar su posición actual', 'no hay señales de alarma en la conversación ni en redes', 'mantener tono y volumen actuales', 'contenido de gestión, cercano');
    acts.sort((x, y) => y.score - x.score);
    return { name, a, m, ig, ads, pr, acts, facts };
  }
  // Y: el objetivo que ordena todo, según qué tipo de señal domina
  function objetivo(dx) {
    const k = dx.acts.slice(0, 3).map(x => x.k);
    if (k.includes('presion') || k.includes('alerta')) return { y: 'recuperar el control de su propia historia', why: 'hoy la conversación la marcan las críticas y no sus propuestas' };
    if (k.includes('tono')) return { y: 'cambiar el clima de la conversación sobre su figura', why: 'la mayoría de lo que se dice sobre su figura es negativo' };
    if (k.includes('vis') || k.includes('caida')) return { y: 'ganar visibilidad con una agenda propia', why: 'hoy tiene poca presencia en la conversación frente a sus pares' };
    if (k.includes('narr')) return { y: 'construir una identidad propia', why: 'la conversación sobre su figura gira alrededor de otros dirigentes' };
    if (k.includes('mom')) return { y: 'convertir la atención de esta semana en posicionamiento', why: 'tiene un pico de menciones que se puede aprovechar' };
    return { y: 'consolidar y ampliar lo que ya le funciona', why: 'los indicadores no muestran alarmas' };
  }
  const ap = n => { const a = D.byName[n]; return a ? a : null };

  function informe(name) {
    const dx = diagnose(name), ob = objetivo(dx), [O, Pq, Q] = dx.acts, f = dx.facts, a = dx.a, ig = dx.ig, ads = dx.ads;
    const top = [O, Pq, Q].filter(Boolean);
    const today = new Date().toLocaleDateString('es-AR', { day: 'numeric', month: 'long', year: 'numeric' });
    const resumen = `<b>${esc(name)} tiene que ${esc(ob.y)}.</b> Los datos lo muestran con claridad: ${esc(O.porque)}. ` +
      (top.length > 1 ? `Por eso las tres acciones que más rinden ahora son <b>${esc(list(top.map(x => x.titulo)))}</b>: la primera ataca directamente ese punto; ` +
        top.slice(1).map(x => `${esc(x.titulo)}, porque ${esc(x.porque)}`).join('; y ') + '.' : '');
    const sec = [];
    if (a && a.n) {
      sec.push(['Conversación', `<p>En los últimos 30 días ${esc(name)} sumó <b>${fmt(a.n)} menciones</b> (${fmt(a.n_news)} titulares y ${fmt(a.n_social)} comentarios), el ${pct(a.share, 1)} de toda la conversación política medida${f.mshare != null ? `; la mediana de sus pares (${esc(list(dx.pr.slice(0, 4)))}${dx.pr.length > 4 ? ' y otros' : ''}) es ${pct(f.mshare, 1)}` : ''}. ${f.d != null ? `En la última semana las menciones ${f.d >= 0 ? 'subieron' : 'bajaron'} ${Math.abs(f.d)}% (${fmt(a.last7)} contra ${fmt(a.prev7)}).` : ''}</p>`]);
      const t = a.tone || {}, em = Object.entries(a.emotions || {}).filter(e => e[1] > 0).sort((x, y) => y[1] - x[1]).slice(0, 3);
      sec.push(['Tono y emociones', `<p>${a.tone_base === 'redes' ? 'En comentarios de redes' : 'En los textos analizados'}: <b>${pct(t.NEG)} negativo</b>, ${pct(t.NEU)} neutro y ${pct(t.POS)} positivo.${a.tone_news ? ` En titulares de prensa el tono es ${pct(a.tone_news.NEG)} negativo y ${pct(a.tone_news.POS)} positivo.` : ''} ${em.length ? `Emociones que más aparecen: ${esc(list(em.map(([k, v]) => `${EMO[k] || k} (${pct(v)})`)))}.` : ''} Índice de presión reputacional: <b>${a.pressure ?? '—'}/100</b>.</p>`]);
      const nar = (a.narratives || []).slice(0, 4), co = (a.co || []).slice(0, 4);
      if (nar.length || co.length) sec.push(['Narrativas y compañía', `<p>${nar.length ? `Temas con los que aparece: ${esc(list(nar.map(n => `«${n.n}» (${pct(n.pct)})`)))}.` : ''} ${co.length ? `Aparece junto a ${esc(list(co.map(c => `${c.a} (${fmt(c.n)})`)))}.` : ''}</p>${(a.cloud || []).length ? `<p>Palabras más asociadas: ${esc(a.cloud.slice(0, 12).map(w => w.w).join(', '))}.</p>` : ''}`]);
      if (f.prov && f.prov.length) sec.push(['Territorio', `<p>Provincias con más menciones en comentarios: ${esc(list(f.prov.slice(0, 4).map(([k, v]) => `${k} (${v})`)))}.</p>`]);
      const hl = (a.headlines || []).slice(0, 3);
      if (hl.length) sec.push(['Últimos titulares', `<ul>${hl.map(h => `<li><a href="${esc(h.u)}" target="_blank" rel="noopener">${esc(h.t)}</a> <small>${esc(h.o || '')}</small></li>`).join('')}</ul>`]);
    } else sec.push(['Conversación', `<p>El Radar todavía no tiene menciones suficientes de ${esc(name)} en noticias y comentarios: se suma en la próxima corrida diaria.</p>`]);
    if (ig) sec.push(['Instagram', `<p>@${esc(ig.usuario)} tiene <b>${kfmt(ig.followers)} seguidores</b>${ig.delta30 != null ? ` (${ig.delta30 >= 0 ? '+' : ''}${kfmt(ig.delta30)} en 30 días)` : ''}, publica ${String(ig.posts_semana).replace('.', ',')} veces por semana y cada publicación junta una interacción mediana de ${kfmt(ig.inter_med)} (${pct(ig.er, 2)} de sus seguidores). ${ig.mejor_formato ? `El formato que mejor le rinde es <b>${esc(ig.mejor_formato.toLowerCase())}</b>` : ''}${momento(ig) ? `, y el mejor momento para publicar, ${esc(momento(ig))}` : ''}.${ig.temas && ig.temas.length ? ` Temas que más usa en sus textos: ${esc(ig.temas.slice(0, 8).join(', '))}.` : ''}</p>${(ig.top || []).length ? `<ul>${ig.top.map(t => `<li><a href="${esc(t.u)}" target="_blank" rel="noopener">${esc(t.t || '(sin texto)')}</a> <small>${esc(t.f)} · ${kfmt(t.i)} interacciones · ${esc(t.d)}</small></li>`).join('')}</ul>` : ''}`]);
    else if (dx.m && metaOK()) sec.push(['Instagram', `<p>No se encontró una cuenta profesional pública de ${esc(name)} en Instagram.</p>`]);
    if (ads && ads.n) { const reg = Object.entries(ads.regiones || {}).slice(0, 3), ed = Object.entries(ads.edades || {}).sort((x, y) => y[1] - x[1]).slice(0, 2);
      sec.push(['Pauta en Meta', `<p>${fmt(ads.n)} avisos políticos en ${D.M.ads_days || 90} días (${fmt(ads.activos)} activos), con un gasto informado de ${kfmt(ads.gasto[0])} a ${kfmt(ads.gasto[1])} pesos y ${kfmt(ads.impresiones[0])} a ${kfmt(ads.impresiones[1])} impresiones. ${reg.length ? `Llegaron sobre todo a ${esc(list(reg.map(([k, v]) => `${k} (${pct(v)})`)))}` : ''}${ed.length ? `, en especial a personas de ${esc(list(ed.map(([k, v]) => `${k} años (${pct(v)})`)))}` : ''}.</p>`]) }
    else if (ads && metaOK()) sec.push(['Pauta en Meta', `<p>Sin avisos políticos registrados en la Biblioteca de Anuncios en ${D.M.ads_days || 90} días.</p>`]);
    if (f.vacante) sec.push(['Agenda vacante', `<p>${esc(f.vacante.tema)}: ${fmt(f.vacante.n)} notas, ${pct(f.vacante.pct_sin_dirigente)} sin ningún dirigente. Es un tema con demanda informativa y sin dueño político.</p>`]);
    const acc = `<ol class="rs-acc">${top.map((x, i) => `<li><b>${esc(cap(x.titulo))}.</b> ${esc(cap(x.porque))}. <span class="rs-kpi">Cómo se mide: ${esc(x.kpi)}.</span></li>`).join('')}</ol>`;
    const concl = `<p>El diagnóstico es consistente: ${esc(ob.why)}. La prioridad para las próximas dos semanas es <b>${esc(O.titulo)}</b>${Pq ? `, apoyada en ${esc(list(top.slice(1).map(x => x.titulo)))}` : ''}. Si en ese plazo se alcanza la meta (${esc(O.kpi)}), la estrategia está funcionando y conviene profundizarla; si no, hay que revisar el mensaje antes que la frecuencia.</p>`;
    const fuentes = ['noticias de Google News y medios', 'comentarios públicos de YouTube', metaOK() ? 'Instagram y Biblioteca de Anuncios de Meta' : null, D.MG ? 'agenda vacante del paquete Massa · Galmarini' : null].filter(Boolean);
    return { dx, ob, top, html: `<article class="rs-doc" id="rs-doc">
      <header class="rs-h"><div><div class="rs-k">Resumen accionable</div><h2>${esc(name)}</h2><div class="rs-m">${esc([dx.m && dx.m.grupo, (dx.m && dx.m.espacio) || (a && a.espacio)].filter(Boolean).join(' · '))} · ${today}</div></div></header>
      <section class="rs-sum"><p>${resumen}</p></section>
      <h3 class="rs-t">Acciones recomendadas</h3>${acc}
      <h3 class="rs-t">Análisis</h3>${sec.map(([t, b]) => `<div class="rs-s"><h4>${esc(t)}</h4>${b}</div>`).join('')}
      <h3 class="rs-t">Conclusión</h3>${concl}
      <footer class="rs-f">Fuentes: ${esc(list(fuentes))}. Ventana de 30 días. Tono y emociones estimados con modelos automáticos; los rangos de pauta son los que publica Meta. <span class="rs-x" id="rs-x" title="" aria-hidden="true">·</span></footer>
    </article>` };
  }

  /* ---------------- prompt para videos (no visible) ---------------- */
  function videoPrompt(r) {
    const { dx, ob, top } = r, a = dx.a, ig = dx.ig, ads = dx.ads, f = dx.facts, name = dx.name;
    const words = a && a.cloud ? a.cloud.filter(w => w.neg < 35).slice(0, 10).map(w => w.w) : [];
    const avoid = a && a.cloud ? a.cloud.filter(w => w.neg >= 50).slice(0, 8).map(w => w.w) : [];
    const fmtV = ig && ig.mejor_formato ? ig.mejor_formato : 'Reel';
    const aud = ads && ads.n ? `${list(Object.entries(ads.regiones || {}).slice(0, 3).map(([k]) => k))}; edades ${list(Object.entries(ads.edades || {}).sort((x, y) => y[1] - x[1]).slice(0, 2).map(([k]) => k))}` : (f.prov && f.prov.length ? list(f.prov.slice(0, 3).map(([k]) => k)) : 'votantes de su distrito');
    return `Actuá como director creativo y guionista de campaña política en Argentina. Con los datos de abajo, escribí 3 guiones de video corto para ${name}.

OBJETIVO DE LA CAMPAÑA
${cap(ob.y)}. Motivo: ${ob.why}.

DATOS DEL TABLERO (no inventes otros)
${a && a.n ? `- Conversación: ${a.n} menciones en 30 días (${pct(a.share, 1)} del total)${f.d != null ? `, ${f.d >= 0 ? '+' : ''}${f.d}% en la última semana` : ''}.
- Tono: ${a.tone ? `${pct(a.tone.NEG)} negativo, ${pct(a.tone.POS)} positivo` : 's/d'}${f.emoTop ? `; emoción dominante: ${EMO[f.emoTop[0]] || f.emoTop[0]} (${pct(f.emoTop[1])})` : ''}.
- Narrativa principal: ${(a.narratives || [])[0] ? `«${a.narratives[0].n}» (${pct(a.narratives[0].pct)})` : 's/d'}. Aparece junto a: ${(a.co || []).slice(0, 3).map(c => c.a).join(', ') || 's/d'}.` : '- Conversación: todavía sin volumen suficiente.'}
${ig ? `- Instagram @${ig.usuario}: ${kfmt(ig.followers)} seguidores, ${String(ig.posts_semana).replace('.', ',')} posts/semana, interacción mediana ${kfmt(ig.inter_med)}. Mejor formato: ${ig.mejor_formato || 's/d'}. Mejor momento: ${momento(ig) || 's/d'}. Temas propios: ${(ig.temas || []).slice(0, 6).join(', ')}.` : ''}
${ads && ads.n ? `- Pauta Meta: ${ads.n} avisos en ${D.M.ads_days || 90} días, sobre todo en ${aud}.` : ''}
${f.vacante ? `- Tema sin dueño político: «${f.vacante.tema}» (${f.vacante.n} notas, ${pct(f.vacante.pct_sin_dirigente)} sin dirigente).` : ''}

UN VIDEO POR ACCIÓN
${top.map((x, i) => `${i + 1}. ${cap(x.titulo)}. Por qué: ${x.porque}.${x.video ? ` Enfoque: ${x.video}.` : ''} Éxito si: ${x.kpi}.`).join('\n')}

FORMATO
- ${fmtV === 'Reel' || fmtV === 'Video' ? 'Vertical 9:16, 30 a 45 segundos' : fmtV === 'Carrusel' ? 'Vertical 9:16, 30 segundos, más una versión carrusel de 5 placas' : 'Vertical 9:16, 30 segundos, más una placa fija con la frase central'}, con subtítulos quemados (se mira sin sonido).
- Gancho en los primeros 3 segundos: una frase o imagen que nombre el problema, no al candidato.
- Estructura: gancho → problema con un dato real del tablero → propuesta concreta → cierre con llamada a la acción.
- Público: ${aud}.
${ig && momento(ig) ? `- Publicar: ${momento(ig)}.` : ''}
${words.length ? `- Palabras que conviene usar (asociadas a su figura con tono no negativo): ${words.join(', ')}.` : ''}
${avoid.length ? `- Palabras a evitar (aparecen en contextos negativos): ${avoid.join(', ')}.` : ''}

PARA CADA GUION ENTREGÁ
Título interno, gancho, guion segundo a segundo (voz en off y texto en pantalla), indicaciones de imagen y plano, música sugerida, texto del posteo con hasta 3 hashtags y la métrica con la que se va a evaluar.

REGLAS
- Usá solo los datos de arriba; si necesitás uno que no está, marcalo como [DATO A CONFIRMAR].
- No muestres ni imites a otros dirigentes, ni generes la cara o la voz de personas reales con IA. Si se usa IA en imágenes, indicá que va rotulado como tal.
- Respetá la ley electoral (veda y período de campaña) y no prometas lo que el cargo no permite.
- Español rioplatense, frases cortas, sin jerga técnica.`.replace(/\n{3,}/g, '\n\n');
  }

  function showPrompt() {
    if (!D.prompt) return;
    let m = $('#rs-modal');
    if (!m) { m = document.createElement('div'); m.id = 'rs-modal'; m.innerHTML = `<div class="rs-mb"><div class="rs-mh"><b>Prompt para videos</b><span id="rs-mok"></span><button id="rs-mc" aria-label="Cerrar">×</button></div><textarea id="rs-mt" readonly></textarea><div class="rs-mf"><button class="pill on" id="rs-mcp">Copiar</button></div></div>`; document.body.appendChild(m);
      m.addEventListener('click', e => { if (e.target === m || e.target.id === 'rs-mc') m.remove() });
      $('#rs-mcp').onclick = () => copy() }
    $('#rs-mt').value = D.prompt; copy();
  }
  const copy = () => { const ok = () => { const s = $('#rs-mok'); if (s) s.textContent = 'copiado al portapapeles' };
    try { navigator.clipboard.writeText(D.prompt).then(ok, () => { }) } catch (e) { } };

  function drawResumen() {
    const host = $('#rs-body'); if (!host) return;
    const s = $('#rs-sel');
    if (!s.dataset.ok) {
      s.dataset.ok = 1;
      const meta = D.M && D.M.dirigentes || [], gs = D.M && D.M.grupos || [], inMeta = new Set(meta.map(d => d.name));
      const rest = D.A.filter(a => a.pais === 'AR' && !inMeta.has(a.name)).sort((x, y) => x.name.localeCompare(y.name));
      s.innerHTML = gs.map(g => `<optgroup label="${esc(g)}">${meta.filter(d => d.grupo === g).map(d => `<option>${esc(d.name)}</option>`).join('')}</optgroup>`).join('') +
        (rest.length ? `<optgroup label="Otros dirigentes del Radar">${rest.map(a => `<option>${esc(a.name)}</option>`).join('')}</optgroup>` : '');
      if (!meta.length && !rest.length) s.innerHTML = '<option>Sergio Massa</option>';
      s.onchange = () => { D.sel = s.value; try { localStorage.setItem('resumen-sel', D.sel) } catch (e) { } drawResumen() };
      $('#rs-pdf').onclick = () => { const t = document.title; document.title = `Resumen accionable - ${D.sel}`; window.print(); setTimeout(() => document.title = t, 500) };
    }
    if (![...s.options].some(o => o.value === D.sel)) D.sel = s.options[0] ? s.options[0].value : D.sel;
    s.value = D.sel;
    const r = informe(D.sel);
    host.innerHTML = r.html;
    D.prompt = videoPrompt(r);
    $('#rs-x').onclick = showPrompt;
  }
  function goResumen(n) { D.sel = n; const b = $('#tabs button[data-t="resumen"]'); if (b) b.click(); window.scrollTo({ top: 0 }) }

  document.addEventListener('keydown', e => { if (e.altKey && e.shiftKey && (e.key === 'P' || e.key === 'p' || e.code === 'KeyP')) { e.preventDefault(); D.ready.then(() => { if (!D.prompt) drawResumen(); showPrompt() }) } if (e.key === 'Escape' && $('#rs-modal')) $('#rs-modal').remove() });

  window.Resumen = {
    draw: id => D.ready.then(() => { if (id === 'meta') drawMeta(); if (id === 'resumen') drawResumen() }),
    prompt: () => D.prompt,
    go: goResumen,
  };
})();
