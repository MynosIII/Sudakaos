/* Brújula política: quiz de 12 ejes (base 12axes, MIT) con certeza por eje y afinidad a dirigentes.
   Datos en BRUJULA.datos (ejes.json, preguntas.json, figuras.json); textos en i18n.js (es / pt / en).
   Si BRUJULA.endpoint está cargado y la persona acepta, envía sus respuestas anónimas al Apps Script (planilla privada).
   Nada se guarda si tiene menos de 16 años. El cálculo es el mismo que procesar.py. */
(function () {
  'use strict';
  const CFG = window.BRUJULA || { datos: '../datos/', endpoint: '' };
  const I18N = window.BRUJULA_I18N, PAISES = window.BRUJULA_PAISES, VER_PAIS = window.BRUJULA_VER_PAIS;
  const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const VER_NOMBRE = {
    pt: { general: 'América Latina (geral)', pe: 'Peru', mx: 'México' },
    en: { general: 'Latin America (general)', br: 'Brazil', pe: 'Peru', mx: 'Mexico' }
  };
  const S = { ejes: null, preg: null, fig: null, ver: null, qs: [], ans: [], i: 0, t0: 0, scores: null, cert: null, lang: 'es', langElegido: false };
  const T = () => I18N[S.lang];

  // ------------------------------------------------------------ cálculo (mismo criterio que procesar.py)
  /* Posición: 50 + 50 × Σ(respuesta × peso) / Σ(2 × |peso|). 0 = polo a, 100 = polo b.
     Certeza (0-100) = decisión × coherencia. Decisión: neutral 0, de acuerdo 0,75, muy de acuerdo 1.
     Coherencia (modelo acumulativo, como 12axes): una frase de nivel L (1 moderada … 4 extrema) la aceptan quienes están del
     lado de su polo al menos (L - 1) × 12,5 puntos más allá del centro; cada respuesta que coincide con eso suma y la que no, resta. */
  function calcular(qs, ans) {
    const ids = S.ejes.ejes.map(e => e.id), Sm = {}, M = {}, D = {}, W = {}, sc = {}, cert = {};
    ids.forEach(k => { Sm[k] = 0; M[k] = 0; D[k] = 0; W[k] = 0 });
    qs.forEach((q, i) => {
      const a = ans[i] ?? 0;
      for (const [k, w] of Object.entries(q.e)) {
        Sm[k] += a * w; M[k] += 2 * Math.abs(w); W[k] += Math.abs(w);
        D[k] += Math.abs(w) * (a === 0 ? 0 : Math.abs(a) === 1 ? .75 : 1);
      }
    });
    ids.forEach(k => { sc[k] = M[k] ? 50 + 50 * Sm[k] / M[k] : 50 });
    ids.forEach(k => {
      let num = 0, den = 0;
      qs.forEach((q, i) => {
        const w = q.e[k], a = ans[i] ?? 0;
        if (!w || !a) return;
        const L = q.nivel || (Math.abs(w) >= 2 ? 3 : 1);
        const pred = Math.sign(w) * (sc[k] - 50) - (L - 1) * 12.5 >= 0 ? 1 : -1;
        num += (Math.sign(a) === pred ? 1 : -1) * Math.abs(w) * Math.abs(a); den += Math.abs(w) * Math.abs(a);
      });
      const d = W[k] ? D[k] / W[k] : 0, cons = den ? num / den : 0;
      cert[k] = Math.round(100 * d * Math.max(0, cons));
    });
    ids.forEach(k => { sc[k] = Math.round(sc[k]) });
    return { sc, cert };
  }
  // Afinidad: distancia ponderada por la certeza de cada eje (los ejes donde dudás pesan menos).
  function afinidad(sc, pos, cert) {
    let num = 0, den = 0;
    for (const k of Object.keys(sc)) {
      const c = 0.3 + 0.7 * ((cert && cert[k] != null ? cert[k] : 50) / 100);
      num += c * Math.abs(sc[k] - pos[k]); den += c;
    }
    return Math.max(0, Math.round(100 - 2 * num / den));
  }
  const certGlobal = cert => Math.round(Object.values(cert).reduce((s, v) => s + v, 0) / Object.values(cert).length);
  function eje(e) { const t = e[S.lang] || {}; return { id: e.id, nombre: t.nombre || e.nombre, a: t.a || e.a, b: t.b || e.b } }
  function etiqueta(e, s) {
    if (s >= 40 && s <= 60) return T().centro_l;
    if (s < 40) return e.a + ' · ' + (s < 20 ? T().fuerte : T().moderado);
    return e.b + ' · ' + (s > 80 ? T().fuerte : T().moderado);
  }
  const texto = q => (S.lang === 'pt' && q.t_pt) || (S.lang === 'en' && q.t_en) || q.t;
  const respuestas = () => S.ejes.respuestas.map((r, j) => ({ v: r.v, t: S.lang === 'pt' ? S.ejes.respuestas_pt[j] : S.lang === 'en' ? S.ejes.respuestas_en[j] : r.t }));
  const nombreVer = id => (VER_NOMBRE[S.lang] || {})[id] || S.ejes.versiones[id].nombre;
  function figuras(ver) { return S.fig[(S.ejes.versiones[ver] || {}).figuras || 'latam'] || [] }

  // ------------------------------------------------------------ idioma
  function idiomaInicial() {
    const u = new URLSearchParams(location.search).get('lang');
    if (I18N[u]) { S.langElegido = true; return u }
    try { const g = localStorage.getItem('brujula_lang'); if (I18N[g]) { S.langElegido = true; return g } } catch (e) { }
    const n = (navigator.language || 'es').slice(0, 2);
    return n === 'pt' || n === 'en' ? n : 'es';
  }
  function setLang(l, elegido) {
    if (!I18N[l]) return;
    S.lang = l;
    if (elegido) { S.langElegido = true; try { localStorage.setItem('brujula_lang', l) } catch (e) { } }
    document.documentElement.lang = l === 'pt' ? 'pt-BR' : l;
    $$('[data-i18n]').forEach(el => { const v = T()[el.dataset.i18n]; if (typeof v === 'string') el.innerHTML = v });
    $$('.lang button').forEach(b => b.classList.toggle('on', b.dataset.l === l));
    $('#priv-list').innerHTML = T().priv_t.map(x => `<li>${esc(x)}</li>`).join('');
    document.title = T().titulo;
    // repintar la pantalla activa
    if (S.ejes) {
      versiones();
      if ($('#s-preg').classList.contains('on')) pregunta();
      if ($('#s-demo').classList.contains('on')) opcionesDemo();
      if ($('#s-res').classList.contains('on')) resultado(S._enviado, S._link);
      if ($('#s-ejes').classList.contains('on')) guia();
      if ($('#s-mapa').classList.contains('on')) mapaPagina();
      if ($('#s-cara').classList.contains('on')) cara();
      $('#hdr-ver').textContent = S.ver ? `${T().sub} · ${nombreVer(S.ver)}` : T().sub;
    }
  }

  // ------------------------------------------------------------ inicio
  function reloj() {
    $('#hdr-t').textContent = new Date().toLocaleTimeString('es-AR', { timeZone: 'America/Argentina/Buenos_Aires', hour: '2-digit', minute: '2-digit' });
  }
  function versiones() {
    $('#versiones').innerHTML = Object.entries(S.ejes.versiones).map(([id, v]) => {
      const n = S.preg.preguntas.filter(q => q.v.includes(id)).length;
      const nf = v.figuras ? S.fig[v.figuras].length : 0;
      return `<button class="ver${id === S.ver ? ' on' : ''}" data-v="${id}" ${v.activa ? '' : 'disabled'}><b>${esc(nombreVer(id))}</b><span>${v.activa
        ? `${n} ${T().preguntas} · ${nf} ${T().dirigentes}` : T().pronto}</span></button>`;
    }).join('');
    $$('.modo').forEach(b => {
      b.disabled = !S.ver;
      const n = S.ver ? seleccion(S.ver, b.dataset.m).length : 0;
      $('#m-' + b.dataset.m).textContent = S.ver ? T().modo_d(n, Math.max(2, Math.round(n * 8 / 60))) : '';
    });
  }
  // Rápida: por eje, una frase hacia cada polo (de nivel intermedio) + 6 locales. Completa: todas.
  function seleccion(ver, modo) {
    const todas = S.preg.preguntas.filter(q => q.v.includes(ver));
    if (modo !== 'rapida') return todas;
    const elegidas = new Set();
    S.ejes.ejes.forEach(e => {
      const base = todas.filter(q => q.id[0] === 'x' && q.e[e.id]);
      [1, -1].forEach(sg => {
        const c = base.filter(q => Math.sign(q.e[e.id]) === sg).sort((a, b) => Math.abs((a.nivel || 2) - 2.5) - Math.abs((b.nivel || 2) - 2.5))[0];
        if (c) elegidas.add(c);
      });
    });
    todas.filter(q => q.id[0] !== 'x').slice(0, 6).forEach(q => elegidas.add(q));
    return todas.filter(q => elegidas.has(q));
  }
  function inicio() {
    versiones();
    $('#versiones').onclick = ev => {
      const b = ev.target.closest('.ver'); if (!b || b.disabled) return;
      S.ver = b.dataset.v;
      const pref = S.ejes.versiones[S.ver].lang || 'es';
      if (!S.langElegido && pref !== S.lang) setLang(pref, false); else versiones();
    };
    $$('.modo').forEach(b => b.onclick = () => { if (S.ver) empezar(S.ver, b.dataset.m) });
  }
  function show(id) {
    $$('.screen').forEach(s => s.classList.toggle('on', s.id === id));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // ------------------------------------------------------------ preguntas
  function empezar(ver, modo) {
    S.ver = ver;
    S.qs = seleccion(ver, modo);
    if (location.hash && location.hash !== '#/') history.replaceState(null, '', location.pathname + location.search + '#/');
    S.ans = new Array(S.qs.length).fill(null);
    S.i = 0; S.t0 = Date.now();
    $('#hdr-ver').textContent = `${T().sub} · ${nombreVer(ver)}`;
    show('s-preg'); pregunta();
  }
  function pregunta() {
    const q = S.qs[S.i], n = S.qs.length;
    $('#q-n').textContent = `${T().preg} ${String(S.i + 1).padStart(2, '0')}/${n}`;
    $('#hdr-n').textContent = `${S.i + 1}/${n}`;
    $('#q-eje').textContent = Object.keys(q.e).map(k => eje(S.ejes.ejes.find(e => e.id === k)).nombre).join(' · ');
    $('#q-t').textContent = texto(q);
    $('#prog-bar').style.width = (100 * S.i / n) + '%';
    $('#q-ops').innerHTML = respuestas().map((r, j) =>
      `<button class="op v${r.v}${S.ans[S.i] === r.v ? ' on' : ''}" data-v="${r.v}"><i>${j + 1}</i>${esc(r.t)}</button>`).join('');
    $('#q-back').disabled = S.i === 0;
  }
  function responder(v) {
    S.ans[S.i] = v;
    if (S.i < S.qs.length - 1) { S.i++; pregunta() }
    else { $('#prog-bar').style.width = '100%'; demograficas() }
  }

  // ------------------------------------------------------------ demográficas (opcionales)
  function opcionesDemo() {
    const f = $('#demo'), t = T();
    const opts = (a, sel, lab) => `<option value="">${esc(t.elegi_op)}</option>` +
      a.map(([v, l]) => `<option value="${esc(v)}"${v === sel ? ' selected' : ''}>${esc(l)}</option>`).join('');
    const keep = n => f[n].value;
    const paisDef = VER_PAIS[S.ver] || '';
    const paises = Object.keys(PAISES).map(p => [p, p === 'Otro' ? t.otro : p]);
    f.edad.innerHTML = opts([['<16', t.menos16], ...['16-17', '18-24', '25-34', '35-44', '45-54', '55-64', '65+'].map(x => [x, x])], keep('edad'));
    f.genero.innerHTML = opts([['Mujer', t.mujer], ['Varón', t.varon], ['No binario / otro', t.nb], ['Prefiero no decir', t.nodecir]], keep('genero'));
    f.pais_res.innerHTML = opts(paises, keep('pais_res') || paisDef);
    f.pais_nac.innerHTML = opts(paises, keep('pais_nac') || paisDef);
    f.red.innerHTML = opts([['Instagram', 'Instagram'], ['X (Twitter)', 'X (Twitter)'], ['TikTok', 'TikTok'], ['YouTube', 'YouTube'], ['Facebook', 'Facebook'],
      ['WhatsApp / Telegram', 'WhatsApp / Telegram'], ['Ninguna: medios tradicionales', t.ninguna]], keep('red'));
    provincias();
  }
  function provincias() {
    const f = $('#demo'), lista = PAISES[f.pais_res.value] || [], prev = f.prov.value;
    f.prov.innerHTML = `<option value="">${esc(T().elegi_op)}</option>` + lista.map(p => `<option${p === prev ? ' selected' : ''}>${esc(p)}</option>`).join('');
    $('#lab-prov').style.display = lista.length ? '' : 'none';
  }
  function demograficas() {
    const r = calcular(S.qs, S.ans); S.scores = r.sc; S.cert = r.cert;
    if (!CFG.endpoint) { resultado(false); return } // sin destino configurado no tiene sentido pedir datos
    opcionesDemo();
    $('#demo').pais_res.onchange = provincias;
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
    const top = figuras(S.ver).map(f => [f.nombre, afinidad(S.scores, f.pos, S.cert)]).sort((a, b) => b[1] - a[1]).slice(0, 3).map(x => x[0]);
    const payload = {
      schema: 2, version: S.ver, lang: S.lang, ids: S.qs.map(q => q.id).join(','), ans: S.ans.map(a => a ?? 0).join(','),
      scores: S.scores, cert: S.cert, top, dur_s: Math.round((Date.now() - S.t0) / 1000), cid: cid(), demo,
      consent: true, ua_mobile: /Mobi|Android/i.test(navigator.userAgent)
    };
    try {
      await fetch(CFG.endpoint, { method: 'POST', mode: 'no-cors', headers: { 'Content-Type': 'text/plain;charset=utf-8' }, body: JSON.stringify(payload) });
      return true;
    } catch (e) { return false }
  }

  // ------------------------------------------------------------ resultado
  function resultado(enviado, desdeLink) {
    S._enviado = enviado; S._link = desdeLink;
    const t = T(), sc = S.scores, cert = S.cert, ver = S.ver, figs = figuras(ver), E = S.ejes.ejes.map(eje);
    $('#res-ver').textContent = '· ' + nombreVer(ver).toUpperCase();
    $('#hdr-ver').textContent = `${t.sub} · ${nombreVer(ver)}`;
    const dom = E.map(e => ({ e, d: Math.abs(sc[e.id] - 50) * (0.5 + cert[e.id] / 200) })).sort((a, b) => b.d - a.d);
    const fuertes = dom.filter(x => Math.abs(sc[x.e.id] - 50) >= 15).slice(0, 3).map(x => sc[x.e.id] < 50 ? x.e.a : x.e.b);
    const y = { es: ' y ', pt: ' e ', en: ' and ' }[S.lang];
    $('#res-titulo').textContent = desdeLink ? t.res_link : t.res_h;
    $('#res-sub').textContent = fuertes.length ? t.define(fuertes.join(', ').replace(/, ([^,]*)$/, y + '$1')) : t.centro;
    const cg = certGlobal(cert);
    $('#cert-g').innerHTML = `<b>${cg}%</b> ${esc(cg >= 60 ? t.cert_alta : cg >= 35 ? t.cert_media : t.cert_baja)}<span class="bar3"><i style="width:${cg}%"></i></span>`;
    $('#ejes').innerHTML = E.map(e => {
      const b = sc[e.id], a = 100 - b, c = cert[e.id], hw = (100 - c) / 4;
      const lo = Math.max(0, a - hw), hi = Math.min(100, a + hw);
      return `<div class="eje"><div class="pa">${esc(e.a)}<small>${a}%</small></div>
        <div class="bar2" title="${esc(e.nombre)} · ${esc(t.certeza)} ${c}%"><i style="width:${a}%"></i><span class="band" style="left:${lo}%;width:${hi - lo}%"></span></div>
        <div class="pb">${esc(e.b)}<small>${b}%</small></div>
        <div class="lab">${esc(e.nombre)} <em>·</em> ${esc(etiqueta(e, b))} <em>·</em> <span class="c">${esc(t.certeza.toLowerCase())} ${c}%</span></div></div>`;
    }).join('');
    const rk = figs.map(f => ({ f, af: afinidad(sc, f.pos, cert) })).sort((a, b) => b.af - a.af);
    $('#match').innerHTML = rk.slice(0, 5).map(({ f, af }) =>
      `<li><b>${esc(f.nombre)}</b><span class="af">${af}%</span><small>${esc(f.cargo || f.pais)}${f.espacio ? ' · ' + esc(f.espacio) : ''}</small><span class="bar3"><i style="width:${af}%"></i></span></li>`).join('');
    const far = rk[rk.length - 1];
    $('#lejos').textContent = far ? t.lejos(far.f.nombre, far.af) : '';
    mapa(sc, rk, E);
    // compartir: versión, idioma, 12 posiciones y 12 certezas
    const ids = S.ejes.ejes.map(e => e.id);
    const url = location.origin + location.pathname + '#r=' + [ver, S.lang, ...ids.map(k => sc[k]), ...ids.map(k => cert[k])].join('-');
    const txt = t.share(rk[0].af, rk[0].f.nombre);
    $('#share-wa').href = 'https://wa.me/?text=' + encodeURIComponent(txt + ' ' + url);
    $('#share-x').href = 'https://x.com/intent/post?text=' + encodeURIComponent(txt) + '&url=' + encodeURIComponent(url);
    $('#share').onclick = async () => {
      if (navigator.share) { try { await navigator.share({ title: t.titulo, text: txt, url }) } catch (e) { } }
      else { try { await navigator.clipboard.writeText(txt + ' ' + url); $('#share').textContent = t.copiado } catch (e) { } }
    };
    $('#sent').textContent = enviado === true ? t.gracias : enviado === 'menor' ? t.menor : '';
    $('#again').textContent = desdeLink ? t.hacer : t.de_nuevo;
    $('#again').onclick = () => { history.replaceState(null, '', location.pathname + location.search + '#/'); show('s-inicio'); nav('quiz') };
    $('#hdr-n').textContent = '✓';
    if (!desdeLink) { try { localStorage.setItem('brujula_res', JSON.stringify({ ver, sc, cert })) } catch (e) { } }
    show('s-res'); nav('quiz');
  }
  function mapa(sc, rk, E) { svgMapa('#mapa', '#mapa-info', rk, 'pla', 'pro', sc, new Set(rk.slice(0, 5).map(x => x.f.nombre))) }
  // Mapa de dos ejes cualesquiera: puntos = dirigentes, "vos" si hay resultado.
  function svgMapa(sel, info, rk, xk, yk, sc, top) {
    const E = S.ejes.ejes.map(eje), ex = E.find(e => e.id === xk), ey = E.find(e => e.id === yk);
    const W = 420, H = 360, P = 30, X = v => P + (W - 2 * P) * v / 100, Yv = v => P + (H - 2 * P) * (1 - v / 100), U = s => esc(s.toUpperCase());
    let g = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(ex.nombre)} × ${esc(ey.nombre)}">`;
    for (let t = 0; t <= 100; t += 25) g += `<line class="gl" x1="${X(t)}" x2="${X(t)}" y1="${P}" y2="${H - P}"/><line class="gl" x1="${P}" x2="${W - P}" y1="${Yv(t)}" y2="${Yv(t)}"/>`;
    g += `<line class="ax" x1="${X(50)}" x2="${X(50)}" y1="${P}" y2="${H - P}"/><line class="ax" x1="${P}" x2="${W - P}" y1="${Yv(50)}" y2="${Yv(50)}"/>`;
    // polos en los extremos de cada eje (no en las esquinas: con nombres largos se pisan)
    g += `<text class="q" x="${X(50)}" y="${P - 10}" text-anchor="middle">▲ ${U(ey.b)}</text><text class="q" x="${X(50)}" y="${H - 8}" text-anchor="middle">▼ ${U(ey.a)}</text>`;
    g += `<text class="q" x="${P + 3}" y="${Yv(50) - 6}">◀ ${U(ex.a)}</text><text class="q" x="${W - P - 3}" y="${Yv(50) - 6}" text-anchor="end">${U(ex.b)} ▶</text>`;
    rk.forEach(({ f, af }) => {
      const tp = top.has(f.nombre), cx = X(f.pos[xk]), cy = Yv(f.pos[yk]), ap = f.nombre.split(' ').slice(-1)[0];
      g += `<g class="pt${tp ? ' top' : ''}"><title>${esc(f.nombre)}${af != null ? ' · ' + af + '%' : ''}${f.cargo ? ' · ' + esc(f.cargo) : ''}</title><circle cx="${cx}" cy="${cy}" r="${tp ? 5 : 3.5}"/>${tp ? `<text x="${cx + 7}" y="${cy + 3}">${esc(ap)}</text>` : ''}</g>`;
    });
    if (sc) {
      const yo = { es: 'VOS', pt: 'VOCÊ', en: 'YOU' }[S.lang];
      g += `<g class="yo"><circle cx="${X(sc[xk])}" cy="${Yv(sc[yk])}" r="8"/><text x="${X(sc[xk]) + 11}" y="${Yv(sc[yk]) - 8}">${yo}</text></g>`;
    }
    $(sel).innerHTML = g + '</svg>';
    $(sel).onclick = ev => { const p = ev.target.closest('.pt'); if (p) $(info).textContent = p.querySelector('title').textContent };
  }

  // ------------------------------------------------------------ secciones: 12 ejes, mapa, mi mapa, cara a cara
  function guardado() { try { const r = JSON.parse(localStorage.getItem('brujula_res') || 'null'); return r && r.sc ? r : null } catch (e) { return null } }
  const verDef = () => S.ver || (guardado() || {}).ver || (S.lang === 'pt' ? 'br' : 'ar');
  function selVer(sel, fn) {
    const el = $(sel), v = el.value || verDef();
    el.innerHTML = Object.entries(S.ejes.versiones).filter(([, x]) => x.activa).map(([id]) => `<option value="${id}"${id === v ? ' selected' : ''}>${esc(nombreVer(id))}</option>`).join('');
    el.onchange = fn;
    return el.value;
  }
  function guia() {
    const ver = selVer('#ej-ver', guia), figs = figuras(ver), r = guardado(), yo = r && r.sc;
    $('#ejes-guia').innerHTML = S.ejes.ejes.map(e0 => {
      const e = eje(e0), ord = figs.slice().sort((a, b) => a.pos[e.id] - b.pos[e.id]);
      const ex = arr => arr.map(f => esc(f.nombre.split(' ').slice(-1)[0])).join(', ');
      return `<div class="ejec"><h3>${esc(e.nombre)}</h3><div class="k">${esc(e.a)} ↔ ${esc(e.b)}</div>
        <div class="polos"><div><b>${esc(e.a)}</b>${esc(e0.a_desc || '')}</div><div><b>${esc(e.b)}</b>${esc(e0.b_desc || '')}</div></div>
        <div class="strip">${figs.map(f => `<i style="left:${f.pos[e.id]}%" title="${esc(f.nombre)} · ${f.pos[e.id]}"></i>`).join('')}${yo ? `<i class="yo" style="left:${yo[e.id]}%" title="${esc(T().vos)} · ${yo[e.id]}"></i>` : ''}</div>
        <div class="ext"><div>${ex(ord.slice(0, 3))}</div><div>${ex(ord.slice(-3).reverse())}</div></div></div>`;
    }).join('');
  }
  function mapaPagina() {
    const ver = selVer('#mp-ver', mapaPagina), E = S.ejes.ejes.map(eje), r = guardado();
    ['#mp-x', '#mp-y'].forEach((sel, i) => {
      const el = $(sel), v = el.value || (i ? 'pro' : 'pla');
      el.innerHTML = E.map(e => `<option value="${e.id}"${e.id === v ? ' selected' : ''}>${esc(e.nombre)} (${esc(e.a)} ↔ ${esc(e.b)})</option>`).join('');
      el.onchange = mapaPagina;
    });
    const sc = r && r.sc, cert = r && r.cert;
    const rk = figuras(ver).map(f => ({ f, af: sc ? afinidad(sc, f.pos, cert) : null })).sort((a, b) => (b.af || 0) - (a.af || 0));
    svgMapa('#mapa-g', '#mapa-g-info', rk, $('#mp-x').value, $('#mp-y').value, sc, new Set(sc ? rk.slice(0, 5).map(x => x.f.nombre) : rk.filter(x => x.f.nivel === 1).map(x => x.f.nombre)));
  }
  function cara() {
    const ver = selVer('#cc-ver', () => { $('#cc-a').value = ''; $('#cc-b').value = ''; cara() }), figs = figuras(ver), r = guardado(), t = T();
    const ops = (sel, def, conVos) => {
      const el = $(sel), v = el.value || def;
      el.innerHTML = (conVos && r ? `<option value="__vos">${esc(t.vos)}</option>` : '') + figs.map(f => `<option${f.nombre === v ? ' selected' : ''}>${esc(f.nombre)}</option>`).join('');
      if (v === '__vos' && r) el.value = '__vos';
      el.onchange = cara;
      return el.value;
    };
    const va = ops('#cc-a', r ? '__vos' : figs[0].nombre, true), vb = ops('#cc-b', figs[r ? 0 : 1].nombre, false);
    const get = v => v === '__vos' ? { nombre: t.vos, pos: r.sc, cert: r.cert } : figs.find(f => f.nombre === v);
    const A = get(va), B = get(vb), E = S.ejes.ejes.map(eje);
    const filas = E.map(e => ({ e, a: Math.round(A.pos[e.id]), b: Math.round(B.pos[e.id]), d: Math.round(Math.abs(A.pos[e.id] - B.pos[e.id])) }));
    const af = afinidad(A.pos, B.pos, A.cert), ord = filas.slice().sort((x, y) => x.d - y.d), n = x => x.map(f => esc(f.e.nombre)).join(', ');
    $('#cara-res').innerHTML = `<div class="leyenda"><span><i style="background:var(--sig)"></i>${esc(A.nombre)}</span><span><i style="background:var(--a)"></i>${esc(B.nombre)}</span></div>
      <div class="resumen"><div><b>${af}%</b>${esc(t.afin)}</div><div>${esc(t.coinciden)}: ${n(ord.slice(0, 3))}</div><div>${esc(t.chocan)}: ${n(ord.slice(-3).reverse())}</div></div>` +
      filas.map(({ e, a, b, d }) => `<div class="fila"><div>${esc(e.nombre)}<small>${esc(e.a)} ↔ ${esc(e.b)}</small></div>
        <div class="tr"><span class="seg" style="left:${Math.min(a, b)}%;width:${d}%"></span><span class="p b" style="left:${b}%" title="${esc(B.nombre)} ${b}"></span><span class="p a" style="left:${a}%" title="${esc(A.nombre)} ${a}"></span></div>
        <div class="d">${d}</div></div>`).join('');
  }
  const RUTAS = { ejes: ['s-ejes', guia], mapa: ['s-mapa', mapaPagina], cara: ['s-cara', cara] };
  function nav(r) { $$('.nav a').forEach(a => a.classList.toggle('on', a.dataset.r === r)) }
  function ruta() {
    const h = location.hash;
    if (h.startsWith('#r=')) return;
    const r = h.replace(/^#\/?/, '');
    if (RUTAS[r]) { show(RUTAS[r][0]); RUTAS[r][1](); nav(r); return }
    if (r === 'mimapa') {
      const g = guardado();
      if (g) { S.ver = g.ver; S.scores = g.sc; S.cert = g.cert; resultado(null, false); nav('mimapa') } else { show('s-vacio'); nav('mimapa') }
      return;
    }
    nav('quiz');
    if (!$('#s-preg').classList.contains('on') && !$('#s-demo').classList.contains('on')) show('s-inicio');
  }
  function tema(t) {
    document.documentElement.dataset.theme = t;
    try { localStorage.setItem('brujula_tema', t) } catch (e) { }
  }

  // ------------------------------------------------------------ eventos
  function eventos() {
    $('#q-ops').onclick = ev => { const b = ev.target.closest('.op'); if (b) responder(+b.dataset.v) };
    $('#q-back').onclick = () => { if (S.i > 0) { S.i--; pregunta() } };
    $('.lang').onclick = ev => { const b = ev.target.closest('button'); if (b) setLang(b.dataset.l, true) };
    document.addEventListener('keydown', ev => {
      if (!$('#s-preg').classList.contains('on')) return;
      const n = +ev.key; if (n >= 1 && n <= 5) responder(S.ejes.respuestas[n - 1].v);
      if (ev.key === 'Backspace' && S.i > 0) { S.i--; pregunta() }
    });
    $('#skip').onclick = () => resultado(false);
    $('#demo').onsubmit = async ev => {
      ev.preventDefault();
      const f = ev.target, err = $('#demo-err');
      if (!f.consiento.checked) { err.textContent = T().falta; return }
      err.textContent = '';
      if (f.web.value) { resultado(false); return } // trampa para bots
      if (f.edad.value === '<16') { resultado('menor'); return } // no se guarda nada de menores de 16
      if (!f.edad.value) { err.textContent = T().falta; return } // la edad es lo único necesario para saber que es mayor de 16
      const demo = { edad: f.edad.value, genero: f.genero.value, pais_res: f.pais_res.value, prov: $('#lab-prov').style.display === 'none' ? '' : f.prov.value, pais_nac: f.pais_nac.value, red: f.red.value };
      resultado(await enviar(demo));
    };
    document.addEventListener('click', ev => {
      const o = ev.target.closest('[data-open]'); if (o) { ev.preventDefault(); $('#' + o.dataset.open).hidden = false }
      if (ev.target.matches('[data-close]') || ev.target.classList.contains('modal')) $$('.modal').forEach(m => m.hidden = true);
    });
  }
  function desdeHash() {
    const m = location.hash.match(/^#r=([a-z]+)-(es|pt|en)((?:-\d{1,3}){24})$/);
    if (!m || !S.ejes.versiones[m[1]] || !S.ejes.versiones[m[1]].activa) return false;
    const v = m[3].slice(1).split('-').map(Number), ids = S.ejes.ejes.map(e => e.id), cl = x => Math.max(0, Math.min(100, x));
    S.ver = m[1]; S.scores = {}; S.cert = {};
    ids.forEach((k, i) => { S.scores[k] = cl(v[i]); S.cert[k] = cl(v[i + ids.length]) });
    if (!S.langElegido) setLang(m[2], false);
    resultado(null, true);
    return true;
  }

  try { const t = localStorage.getItem('brujula_tema'); if (t) document.documentElement.dataset.theme = t } catch (e) { }
  async function main() {
    reloj(); setInterval(reloj, 30000);
    const get = f => fetch(CFG.datos + f).then(r => r.json());
    [S.ejes, S.preg, S.fig] = await Promise.all([get('ejes.json'), get('preguntas.json'), get('figuras.json')]);
    $('#foot-v').textContent = S.fig.fecha || '';
    inicio(); eventos();
    setLang(idiomaInicial(), false);
    $('#tema').onclick = () => tema(document.documentElement.dataset.theme === 'light' ? 'dark' : 'light');
    window.addEventListener('hashchange', () => { if (!desdeHash()) ruta() });
    if (!desdeHash()) ruta();
  }
  main();
})();
