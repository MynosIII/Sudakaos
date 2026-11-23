/* Brújula política: quiz de 8 ejes con afinidad a dirigentes.
   Datos en BRUJULA.datos (ejes.json, preguntas.json, figuras.json). Si BRUJULA.endpoint está cargado y la persona
   acepta, envía sus respuestas anónimas al Apps Script (planilla privada). Nada se guarda si tiene menos de 16 años. */
(function () {
  'use strict';
  const CFG = window.BRUJULA || { datos: '../datos/', endpoint: '' };
  const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const PAISES = ['Argentina', 'Bolivia', 'Brasil', 'Chile', 'Colombia', 'Ecuador', 'México', 'Paraguay', 'Perú', 'Uruguay', 'Venezuela',
    'Centroamérica y Caribe', 'España', 'Estados Unidos', 'Otro'];
  const PROVS = ['Buenos Aires: conurbano', 'Buenos Aires: interior', 'CABA', 'Catamarca', 'Chaco', 'Chubut', 'Córdoba', 'Corrientes',
    'Entre Ríos', 'Formosa', 'Jujuy', 'La Pampa', 'La Rioja', 'Mendoza', 'Misiones', 'Neuquén', 'Río Negro', 'Salta', 'San Juan',
    'San Luis', 'Santa Cruz', 'Santa Fe', 'Santiago del Estero', 'Tierra del Fuego', 'Tucumán'];
  const S = { ejes: null, preg: null, fig: null, ver: null, qs: [], ans: [], i: 0, t0: 0, scores: null };

  // ------------------------------------------------------------ cálculo (mismo criterio que procesar.py)
  function puntajes(qs, ans) {
    const num = {}, den = {};
    S.ejes.ejes.forEach(e => { num[e.id] = 0; den[e.id] = 0 });
    qs.forEach((q, i) => {
      const a = ans[i] ?? 0;
      for (const [k, w] of Object.entries(q.e)) { num[k] += a * w; den[k] += 2 * Math.abs(w) }
    });
    const out = {};
    for (const k in num) out[k] = den[k] ? Math.round(50 + 50 * num[k] / den[k]) : 50;
    return out;
  }
  function afinidad(sc, pos) {
    const ks = Object.keys(sc);
    const d = ks.reduce((s, k) => s + Math.abs(sc[k] - pos[k]), 0) / ks.length;
    return Math.max(0, Math.round(100 - 2 * d));
  }
  function etiqueta(e, s) {
    if (s >= 40 && s <= 60) return 'Centro';
    if (s < 40) return e.a + (s < 20 ? ' · fuerte' : ' · moderado');
    return e.b + (s > 80 ? ' · fuerte' : ' · moderado');
  }
  function figuras(ver) { return S.fig[(S.ejes.versiones[ver] || {}).figuras || 'latam'] || [] }

  // ------------------------------------------------------------ inicio
  function reloj() {
    const t = new Date().toLocaleTimeString('es-AR', { timeZone: 'America/Argentina/Buenos_Aires', hour: '2-digit', minute: '2-digit' });
    $('#hdr-t').textContent = t;
  }
  function inicio() {
    const box = $('#versiones');
    box.innerHTML = Object.entries(S.ejes.versiones).map(([id, v]) => {
      const n = S.preg.preguntas.filter(q => q.v.includes(id)).length;
      const nf = v.figuras ? S.fig[v.figuras].length : 0;
      return `<button class="ver" data-v="${id}" ${v.activa ? '' : 'disabled'}><b>${esc(v.nombre)}</b><span>${v.activa ? `${n} preguntas · ${nf} dirigentes` : ''}</span></button>`;
    }).join('');
    box.onclick = ev => {
      const b = ev.target.closest('.ver'); if (!b || b.disabled) return;
      $$('.ver').forEach(x => x.classList.toggle('on', x === b));
      S.ver = b.dataset.v;
      const n = S.preg.preguntas.filter(q => q.v.includes(S.ver)).length;
      $('#go').disabled = false;
      $('#go-meta').textContent = `≈ ${Math.round(n * 9 / 60)} minutos`;
    };
    $('#go').onclick = () => empezar(S.ver);
  }
  function show(id) {
    $$('.screen').forEach(s => s.classList.toggle('on', s.id === id));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // ------------------------------------------------------------ preguntas
  function empezar(ver) {
    S.ver = ver;
    S.qs = S.preg.preguntas.filter(q => q.v.includes(ver));
    S.ans = new Array(S.qs.length).fill(null);
    S.i = 0; S.t0 = Date.now();
    $('#hdr-ver').textContent = '8 ejes · ' + S.ejes.versiones[ver].nombre;
    show('s-preg'); pregunta();
  }
  function pregunta() {
    const q = S.qs[S.i], n = S.qs.length;
    const ejes = Object.keys(q.e).map(k => S.ejes.ejes.find(e => e.id === k).nombre).join(' · ');
    $('#q-n').textContent = `PREG ${String(S.i + 1).padStart(2, '0')}/${n}`;
    $('#hdr-n').textContent = `${S.i + 1}/${n}`;
    $('#q-eje').textContent = ejes;
    $('#q-t').textContent = q.t;
    $('#prog-bar').style.width = (100 * S.i / n) + '%';
    $('#q-ops').innerHTML = S.ejes.respuestas.map((r, j) =>
      `<button class="op v${r.v}${S.ans[S.i] === r.v ? ' on' : ''}" data-v="${r.v}"><i>${j + 1}</i>${esc(r.t)}</button>`).join('');
    $('#q-back').disabled = S.i === 0;
  }
  function responder(v) {
    S.ans[S.i] = v;
    if (S.i < S.qs.length - 1) { S.i++; pregunta() }
    else { $('#prog-bar').style.width = '100%'; demograficas() }
  }

  // ------------------------------------------------------------ demográficas
  function demograficas() {
    S.scores = puntajes(S.qs, S.ans);
    const f = $('#demo');
    const opts = (a, sel) => '<option value="">Elegí</option>' + a.map(x => `<option${x === sel ? ' selected' : ''}>${esc(x)}</option>`).join('');
    f.pais_res.innerHTML = opts(PAISES, S.ver === 'ar' ? 'Argentina' : '');
    f.pais_nac.innerHTML = opts(PAISES, S.ver === 'ar' ? 'Argentina' : '');
    f.prov.innerHTML = opts(PROVS);
    const prov = () => { const ar = f.pais_res.value === 'Argentina'; $('#lab-prov').style.display = ar ? '' : 'none'; f.prov.required = ar };
    f.pais_res.onchange = prov; prov();
    if (!CFG.endpoint) { // sin destino configurado no tiene sentido pedir datos
      resultado(false); return;
    }
    show('s-demo');
  }
  function cid() {
    try {
      let c = localStorage.getItem('brujula_cid');
      if (!c) { c = (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2) + Date.now()); localStorage.setItem('brujula_cid', c) }
      return c;
    } catch (e) { return '' }
  }
  async function enviar(demo) {
    const top = figuras(S.ver).map(f => [f.nombre, afinidad(S.scores, f.pos)]).sort((a, b) => b[1] - a[1]).slice(0, 3).map(x => x[0]);
    const payload = {
      schema: 1, version: S.ver, ids: S.qs.map(q => q.id).join(','), ans: S.ans.map(a => a ?? 0).join(','),
      scores: S.scores, top, dur_s: Math.round((Date.now() - S.t0) / 1000), cid: cid(), demo,
      consent: true, ua_mobile: /Mobi|Android/i.test(navigator.userAgent)
    };
    try {
      await fetch(CFG.endpoint, { method: 'POST', mode: 'no-cors', headers: { 'Content-Type': 'text/plain;charset=utf-8' }, body: JSON.stringify(payload) });
      return true;
    } catch (e) { return false }
  }

  // ------------------------------------------------------------ resultado
  function resultado(enviado, desdeLink) {
    const sc = S.scores, ver = S.ver, figs = figuras(ver);
    $('#res-ver').textContent = '· ' + S.ejes.versiones[ver].nombre.toUpperCase();
    $('#hdr-ver').textContent = '8 ejes · ' + S.ejes.versiones[ver].nombre;
    const dom = S.ejes.ejes.map(e => ({ e, d: Math.abs(sc[e.id] - 50) })).sort((a, b) => b.d - a.d);
    const fuertes = dom.filter(x => x.d >= 15).slice(0, 3).map(x => sc[x.e.id] < 50 ? x.e.a : x.e.b);
    $('#res-titulo').textContent = desdeLink ? 'Un resultado compartido' : 'Tu brújula';
    $('#res-sub').textContent = fuertes.length
      ? `Lo que más te define: ${fuertes.join(', ').replace(/, ([^,]*)$/, ' y $1')}.`
      : 'Estás cerca del centro en casi todo: tus posiciones no se inclinan fuerte hacia ningún polo.';
    $('#ejes').innerHTML = S.ejes.ejes.map(e => {
      const b = sc[e.id], a = 100 - b;
      return `<div class="eje"><div class="pa">${esc(e.a)}<small>${a}%</small></div><div class="bar2" title="${esc(e.nombre)}"><i style="width:${a}%"></i></div>
        <div class="pb">${esc(e.b)}<small>${b}%</small></div><div class="lab">${esc(e.nombre)} <em>·</em> ${esc(etiqueta(e, b))}</div></div>`;
    }).join('');
    const rk = figs.map(f => ({ f, af: afinidad(sc, f.pos) })).sort((a, b) => b.af - a.af);
    $('#match').innerHTML = rk.slice(0, 5).map(({ f, af }) =>
      `<li><b>${esc(f.nombre)}</b><span class="af">${af}%</span><small>${esc(f.cargo || f.pais)}${f.espacio ? ' · ' + esc(f.espacio) : ''}</small><span class="bar3"><i style="width:${af}%"></i></span></li>`).join('');
    const far = rk[rk.length - 1];
    $('#lejos').textContent = far ? `Más lejos de vos: ${far.f.nombre} (${far.af}%).` : '';
    mapa(sc, rk);
    // compartir
    const url = location.origin + location.pathname + '#r=' + [ver, ...S.ejes.ejes.map(e => sc[e.id])].join('-');
    const txt = `Hice la Brújula política: me parezco ${rk[0].af}% a ${rk[0].f.nombre}. ¿Y vos?`;
    $('#share-wa').href = 'https://wa.me/?text=' + encodeURIComponent(txt + ' ' + url);
    $('#share-x').href = 'https://x.com/intent/post?text=' + encodeURIComponent(txt) + '&url=' + encodeURIComponent(url);
    $('#share').onclick = async () => {
      if (navigator.share) { try { await navigator.share({ title: 'Brújula política', text: txt, url }) } catch (e) { } }
      else { try { await navigator.clipboard.writeText(txt + ' ' + url); $('#share').textContent = 'Link copiado' } catch (e) { } }
    };
    $('#sent').textContent = enviado === true ? 'Gracias: tus respuestas anónimas ya suman al estudio.' : '';
    $('#again').textContent = desdeLink ? 'Hacer el quiz' : 'Hacerlo de nuevo';
    $('#again').onclick = () => { history.replaceState(null, '', location.pathname); show('s-inicio') };
    $('#hdr-n').textContent = '✓';
    show('s-res');
  }
  function mapa(sc, rk) {
    const W = 420, H = 360, P = 30, X = v => P + (W - 2 * P) * v / 100, Y = v => H - P - (H - 2 * P) * (100 - v) / 100;
    // Y: arriba conservadurismo (100), abajo progresismo (0)
    const yv = v => P + (H - 2 * P) * (1 - v / 100);
    const top = new Set(rk.slice(0, 5).map(x => x.f.nombre));
    let g = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Mapa económico por valores">`;
    for (let t = 0; t <= 100; t += 25) g += `<line class="gl" x1="${X(t)}" x2="${X(t)}" y1="${P}" y2="${H - P}"/><line class="gl" x1="${P}" x2="${W - P}" y1="${yv(t)}" y2="${yv(t)}"/>`;
    g += `<line class="ax" x1="${X(50)}" x2="${X(50)}" y1="${P}" y2="${H - P}"/><line class="ax" x1="${P}" x2="${W - P}" y1="${yv(50)}" y2="${yv(50)}"/>`;
    g += `<text class="q" x="${P}" y="${P - 10}">ESTADO · CONSERVADOR</text><text class="q" x="${W - P}" y="${P - 10}" text-anchor="end">MERCADO · CONSERVADOR</text>`;
    g += `<text class="q" x="${P}" y="${H - 10}">ESTADO · PROGRESISTA</text><text class="q" x="${W - P}" y="${H - 10}" text-anchor="end">MERCADO · PROGRESISTA</text>`;
    rk.forEach(({ f, af }) => {
      const t = top.has(f.nombre), cx = X(f.pos.eco), cy = yv(f.pos.soc), ap = f.nombre.split(' ').slice(-1)[0];
      g += `<g class="pt${t ? ' top' : ''}"><title>${esc(f.nombre)} · afinidad ${af}%</title><circle cx="${cx}" cy="${cy}" r="${t ? 5 : 3.5}"/>${t ? `<text x="${cx + 7}" y="${cy + 3}">${esc(ap)}</text>` : ''}</g>`;
    });
    g += `<g class="yo"><circle cx="${X(sc.eco)}" cy="${yv(sc.soc)}" r="8"/><text x="${X(sc.eco) + 11}" y="${yv(sc.soc) - 8}">VOS</text></g></svg>`;
    $('#mapa').innerHTML = g;
    $('#mapa').onclick = ev => { const p = ev.target.closest('.pt'); if (p) $('#mapa + .meta').textContent = p.querySelector('title').textContent };
  }

  // ------------------------------------------------------------ eventos
  function eventos() {
    $('#q-ops').onclick = ev => { const b = ev.target.closest('.op'); if (b) responder(+b.dataset.v) };
    $('#q-back').onclick = () => { if (S.i > 0) { S.i--; pregunta() } };
    document.addEventListener('keydown', ev => {
      if (!$('#s-preg').classList.contains('on')) return;
      const n = +ev.key; if (n >= 1 && n <= 5) responder(S.ejes.respuestas[n - 1].v);
      if (ev.key === 'Backspace' && S.i > 0) { S.i--; pregunta() }
    });
    $('#skip').onclick = () => resultado(false);
    $('#demo').onsubmit = async ev => {
      ev.preventDefault();
      const f = ev.target, err = $('#demo-err');
      if (!f.checkValidity()) { err.textContent = 'Completá los datos y marcá el consentimiento, o tocá "Ver resultado sin enviar".'; return }
      err.textContent = '';
      if (f.web.value) { resultado(false); return } // trampa para bots
      if (f.edad.value === '<16') { resultado('menor'); return } // no se guarda nada de menores de 16
      const demo = { edad: f.edad.value, genero: f.genero.value, pais_res: f.pais_res.value, prov: f.pais_res.value === 'Argentina' ? f.prov.value : '', pais_nac: f.pais_nac.value, red: f.red.value };
      const ok = await enviar(demo);
      resultado(ok);
    };
    document.addEventListener('click', ev => {
      const o = ev.target.closest('[data-open]'); if (o) { ev.preventDefault(); $('#' + o.dataset.open).hidden = false }
      if (ev.target.matches('[data-close]') || ev.target.classList.contains('modal')) $$('.modal').forEach(m => m.hidden = true);
    });
  }
  function desdeHash() {
    const m = location.hash.match(/^#r=([a-z]+)((?:-\d{1,3}){8})$/);
    if (!m || !S.ejes.versiones[m[1]] || !S.ejes.versiones[m[1]].activa) return false;
    const v = m[2].slice(1).split('-').map(Number);
    S.ver = m[1]; S.scores = {};
    S.ejes.ejes.forEach((e, i) => S.scores[e.id] = Math.max(0, Math.min(100, v[i])));
    resultado(null, true);
    return true;
  }

  async function main() {
    reloj(); setInterval(reloj, 30000);
    const get = f => fetch(CFG.datos + f).then(r => r.json());
    [S.ejes, S.preg, S.fig] = await Promise.all([get('ejes.json'), get('preguntas.json'), get('figuras.json')]);
    $('#foot-v').textContent = `posiciones: ${S.fig.fecha}`;
    inicio(); eventos();
    desdeHash();
  }
  main();
})();
