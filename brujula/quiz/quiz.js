/* Brújula política v2: quiz de 12 ejes (base 12axes, MIT) con certeza por eje, ideologías, dirigentes, análisis y tarjeta.
   Datos en BRUJULA.datos (ejes.json, preguntas.json, figuras.json, ideologias.json); textos en i18n.js (es / pt / en).
   Si BRUJULA.endpoint está cargado y la persona acepta, envía sus respuestas anónimas al Apps Script (planilla privada).
   Nada se guarda si tiene menos de 16 años. El cálculo de posición y certeza es el mismo que procesar.py. */
(function () {
  'use strict';
  const CFG = window.BRUJULA || { datos: '../datos/', endpoint: '' };
  const I18N = window.BRUJULA_I18N, PAISES = window.BRUJULA_PAISES, VER_PAIS = window.BRUJULA_VER_PAIS, GLOS = window.BRUJULA_GLOS || {};
  const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const VER_NOMBRE = {
    pt: { general: 'América Latina (geral)', pe: 'Peru', mx: 'México' },
    en: { general: 'Latin America (general)', br: 'Brazil', pe: 'Peru', mx: 'Mexico' }
  };
  // Un color y un ícono por eje (identidad propia: grafito + ámbar).
  const COLOR = { fed: '#d9a441', dem: '#5b8def', int: '#2bb3a3', mil: '#a8987f', lib: '#c2cf5f', col: '#e0607e', rel: '#b08cd9', pro: '#f08a4b', mig: '#4fc3e8', pla: '#3fbf7f', glo: '#e8c547', tec: '#8fa3b8' };
  const ICON = {
    fed: '<circle cx="12" cy="5" r="2.5"/><circle cx="5" cy="18" r="2.5"/><circle cx="19" cy="18" r="2.5"/><path d="M10.8 7.2 6.2 15.8M13.2 7.2l4.6 8.6M7.5 18h9"/>',
    dem: '<path d="M4 11h16v9H4z"/><path d="M8 11V4h8v7M10 7h4M9 15h6"/>',
    int: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.2 3 14.8 0 18M12 3c-3 3.2-3 14.8 0 18"/>',
    mil: '<path d="M12 3 5 6v6c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6z"/><path d="M9 12l2 2 4-4"/>',
    lib: '<circle cx="8" cy="15" r="4"/><path d="M11 12l8-8M16 7l3 3M14 9l2 2"/>',
    col: '<circle cx="8" cy="8" r="3"/><circle cx="16.5" cy="9" r="2.5"/><path d="M2.5 20c0-3.5 2.5-6 5.5-6s5.5 2.5 5.5 6M14 14.5c3.5-.5 7 1.5 7 5.5"/>',
    rel: '<path d="M12 3v18M7 8h10"/><path d="M5 21h14"/>',
    pro: '<path d="M4 12h14M13 6l6 6-6 6"/><path d="M4 6v12"/>',
    mig: '<path d="M4 8h15l-3-3M20 16H5l3 3"/>',
    pla: '<path d="M4 20V10M10 20V4M16 20v-7M2 20h20"/>',
    glo: '<path d="M3 15h18l-2 5H5z"/><path d="M6 15V9h5v6M11 11h5v4"/>',
    tec: '<rect x="7" y="7" width="10" height="10" rx="1.5"/><path d="M10 3v4M14 3v4M10 17v4M14 17v4M3 10h4M3 14h4M17 10h4M17 14h4"/>'
  };
  Object.assign(COLOR, { ecl: '#5fae7a', dis: '#e07a7a', bie: '#e8a05c', epi: '#5aa9e6', ges: '#9aa7b8', tra: '#d9776a', idc: '#d6b25e', pen: '#6fb8ad',
    lab: '#8f9be0', eti: '#63c1cf', tem: '#ef8f6a', fut: '#86c98a', ind: '#b39278', mon: '#b98ad0', inf: '#c2c8d0', ipe: '#9a7fd0', uni: '#6aa8e8' });
  Object.assign(ICON, {
    ecl: '<path d="M5 19c0-8 6-14 14-14 0 8-6 14-14 14z"/><path d="M5 19l8-8"/>',
    dis: '<path d="M12 4v16M7 20h10M4 8h16"/><path d="M4 8l-2 5h4zM20 8l-2 5h4z"/>',
    bie: '<path d="M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.5A4 4 0 0 1 19 10c0 5.5-7 10-7 10z"/>',
    epi: '<circle cx="10.5" cy="10.5" r="6"/><path d="M15 15l5 5"/>',
    ges: '<circle cx="12" cy="12" r="3"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/>',
    tra: '<path d="M20 12a8 8 0 1 1-2.3-5.7"/><path d="M20 4v5h-5"/>',
    idc: '<circle cx="8" cy="9" r="3"/><circle cx="16" cy="9" r="3"/><path d="M3 20c0-3 2.2-5 5-5s5 2 5 5M11 20c0-3 2.2-5 5-5s5 2 5 5"/>',
    pen: '<path d="M14 4l6 6M10.5 7.5l6 6M12 6l-5 5M3 21l7-7"/>',
    lab: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5h6v2M3 13h18"/>',
    eti: '<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9V16h7v-2.1A6 6 0 0 0 12 3z"/>',
    tem: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/>',
    fut: '<path d="M6 3h12M6 21h12M7 3c0 6 10 6 10 9s-10 3-10 9M17 3c0 6-10 6-10 9s10 3 10 9"/>',
    ind: '<path d="M3 20V10l6 4V10l6 4V6h4v14z"/>',
    mon: '<circle cx="12" cy="12" r="8"/><path d="M14.5 9.5c-.5-1-1.5-1.5-2.5-1.5-1.5 0-2.5.8-2.5 2s1 1.6 2.5 2 2.5.8 2.5 2-1 2-2.5 2c-1 0-2-.5-2.5-1.5M12 6.5v11"/>',
    inf: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M7 9h10M7 13h6M7 16h8"/>',
    ipe: '<path d="M3 9l9-5 9 5M5 9v9M10 9v9M14 9v9M19 9v9M3 20h18"/>',
    uni: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="5" r="1.6"/><circle cx="18.5" cy="15" r="1.6"/><circle cx="5.5" cy="15" r="1.6"/>'
  });
  const ic = k => `<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">${ICON[k] || ''}</svg>`;
  const icb = k => `<span class="icb" style="color:${COLOR[k]}">${ic(k)}</span>`;
  const DIMS = { d_pol: ['dem', 'lib', 'fed', 'mil'], d_soc: ['pro', 'rel', 'mig', 'int'], d_eco: ['pla', 'col', 'glo', 'tec'] };
  // Pares que suelen ir juntos: +1 = misma dirección, -1 = dirección opuesta. Si alguien los combina al revés, es una tensión.
  const PARES = [['pla', 'col', 1], ['pro', 'rel', 1], ['lib', 'dem', -1], ['int', 'glo', -1], ['int', 'mig', -1], ['pla', 'glo', 1], ['pro', 'mig', -1], ['lib', 'pro', -1], ['mil', 'int', -1], ['mil', 'lib', 1]];
  const S = { ejes: null, preg: null, fig: null, ideo: [], ver: null, modo: 'completa', qs: [], ans: [], i: 0, t0: 0, scores: null, cert: null, nresp: null, dist: null, lang: 'es', langElegido: false };
  const T = () => I18N[S.lang];
  const IDS = () => S.ejes.ejes.map(e => e.id);
  const IDS2 = () => (S.ejes.ejes2 || []).map(e => e.id);

  // ------------------------------------------------------------ cálculo (mismo criterio que procesar.py)
  /* Posición: 50 + 50 × Σ(respuesta × peso) / Σ(2 × |peso|). 0 = polo a, 100 = polo b.
     Certeza (0-100) = decisión × coherencia. Decisión: neutral 0, de acuerdo 0,75, muy de acuerdo 1.
     Coherencia (modelo acumulativo, como 12axes): una frase de nivel L (1 moderada … 4 extrema) la aceptan quienes están del
     lado de su polo al menos (L - 1) × 12,5 puntos más allá del centro; cada respuesta que coincide con eso suma y la que no, resta. */
  function calcular(qs, ans, idsElegidos) {
    const ids = idsElegidos || IDS(), Sm = {}, M = {}, D = {}, W = {}, sc = {}, cert = {};
    ids.forEach(k => { Sm[k] = 0; M[k] = 0; D[k] = 0; W[k] = 0 });
    qs.forEach((q, i) => {
      const a = ans[i] ?? 0;
      for (const [k, w] of Object.entries(q.e)) {
        if (!(k in Sm)) continue;
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
  // Afinidad: distancia ponderada por la certeza de cada eje (los ejes donde dudás pesan menos). keys opcional: sólo esos ejes.
  function afinidad(sc, pos, cert, keys) {
    let num = 0, den = 0;
    for (const k of keys || Object.keys(sc)) {
      const c = 0.3 + 0.7 * ((cert && cert[k] != null ? cert[k] : 50) / 100);
      num += c * Math.abs(sc[k] - pos[k]); den += c;
    }
    return Math.max(0, Math.round(100 - 2 * num / den));
  }
  const media = o => Math.round(Object.values(o).reduce((s, v) => s + v, 0) / Object.values(o).length);
  function eje(e) { const t = e[S.lang] || {}; return { id: e.id, nombre: t.nombre || e.nombre, a: t.a || e.a, b: t.b || e.b } }
  const EJES = () => S.ejes.ejes.map(eje);
  const EJES2 = () => (S.ejes.ejes2 || []).map(eje);
  const ejeK = k => eje(S.ejes.ejes.find(e => e.id === k) || (S.ejes.ejes2 || []).find(e => e.id === k));
  const polo = (e, s) => s < 50 ? e.a : e.b;
  function lectura(e, s) { // "Equilibrado" o "72% Mercado"
    if (Math.abs(s - 50) < 10) return T().equilibrado;
    return `${s > 50 ? s : 100 - s}% ${polo(e, s)}`;
  }
  const texto = q => (S.lang === 'pt' && q.t_pt) || (S.lang === 'en' && q.t_en) || q.t;
  const respuestas = () => S.ejes.respuestas.map((r, j) => ({ v: r.v, t: S.lang === 'pt' ? S.ejes.respuestas_pt[j] : S.lang === 'en' ? S.ejes.respuestas_en[j] : r.t }));
  // Banderas simplificadas (SVG en línea, 30×20).
  const BANDERA = {
    ar: '<rect width="30" height="20" fill="#74acdf"/><rect y="6.67" width="30" height="6.67" fill="#fff"/><circle cx="15" cy="10" r="2" fill="#f6b40e"/>',
    br: '<rect width="30" height="20" fill="#009c3b"/><path d="M15 2.5 27 10 15 17.5 3 10z" fill="#ffdf00"/><circle cx="15" cy="10" r="4.2" fill="#002776"/>',
    py: '<rect width="30" height="20" fill="#fff"/><rect width="30" height="6.67" fill="#d52b1e"/><rect y="13.33" width="30" height="6.67" fill="#0038a8"/>',
    pe: '<rect width="30" height="20" fill="#d91023"/><rect x="10" width="10" height="20" fill="#fff"/>',
    cl: '<rect width="30" height="20" fill="#fff"/><rect y="10" width="30" height="10" fill="#d52b1e"/><rect width="10" height="10" fill="#0039a6"/><circle cx="5" cy="5" r="1.6" fill="#fff"/>',
    co: '<rect width="30" height="20" fill="#ce1126"/><rect width="30" height="15" fill="#003893"/><rect width="30" height="10" fill="#fcd116"/>',
    uy: '<rect width="30" height="20" fill="#fff"/><g fill="#0038a8"><rect y="2.22" width="30" height="2.22"/><rect y="6.67" width="30" height="2.22"/><rect y="11.11" width="30" height="2.22"/><rect y="15.56" width="30" height="2.22"/></g><rect width="11" height="11.11" fill="#fff"/><circle cx="5.5" cy="5.5" r="2.4" fill="#fcd116"/>',
    mx: '<rect width="30" height="20" fill="#fff"/><rect width="10" height="20" fill="#006847"/><rect x="20" width="10" height="20" fill="#ce1126"/><circle cx="15" cy="10" r="2" fill="#8c6a2e"/>'
  };
  const bandera = id => BANDERA[id] ? `<span class="flag"><svg viewBox="0 0 30 20" aria-hidden="true">${BANDERA[id]}</svg></span>` : '';
  const nombreVer = id => (VER_NOMBRE[S.lang] || {})[id] || S.ejes.versiones[id].nombre;
  function figuras(ver, conHist) { const l = S.fig[(S.ejes.versiones[ver] || {}).figuras || 'latam'] || []; return conHist ? l : l.filter(f => !f.hist) }
  const figurasH = ver => figuras(ver, true).filter(f => f.hist);
  // Internacionales: el resto del mundo y de Latinoamérica (sin repetir a los del país elegido).
  function figurasInt(ver) {
    const nom = (S.ejes.versiones[ver] || {}).nombre, propios = new Set(figuras(ver, true).map(f => f.nombre));
    return [...(S.fig.mundo || []), ...(S.fig.latam || [])].filter(f => f.pais !== nom && !propios.has(f.nombre)).map(f => Object.assign({ int: 1 }, f));
  }
  const ideoNom = i => (i[S.lang] || i.es).nombre, ideoDesc = i => (i[S.lang] || i.es).desc;
  const iniciales = n => n.split(/\s+/).filter(w => /^[A-ZÁÉÍÓÚÑ]/.test(w)).slice(0, 2).map(w => w[0]).join('') || n[0];
  const apellido = n => n.split(' ').slice(-1)[0];
  function lista(arr) { const y = { es: ' y ', pt: ' e ', en: ' and ' }[S.lang]; return arr.length < 2 ? arr.join('') : arr.slice(0, -1).join(', ') + y + arr[arr.length - 1] }
  function ring(p, cls) {
    const r = 15.9, c = 2 * Math.PI * r;
    return `<div class="ring ${cls || ''}"><svg viewBox="0 0 36 36"><circle cx="18" cy="18" r="${r}" fill="none" stroke="var(--s3)" stroke-width="3.2"/>` +
      `<circle cx="18" cy="18" r="${r}" fill="none" stroke="var(--sig)" stroke-width="3.2" stroke-linecap="round" stroke-dasharray="${c * p / 100} ${c}"/></svg><b>${p}%</b></div>`;
  }
  const avatar = (f, cls) => `<span class="av ${cls || ''}" data-f="${esc(f.nombre)}">${esc(iniciales(f.nombre))}</span>`;

  // ------------------------------------------------------------ fotos (Wikipedia, desde el navegador de quien mira; si no hay, iniciales)
  const FOTOS = new Map(), FCACHE = {}, WIKI = {};
  try { Object.assign(FCACHE, JSON.parse(sessionStorage.getItem('brujula_fotos') || '{}')) } catch (e) { }
  // Para no mostrar la foto de un homónimo, la página tiene que describir a alguien de la política.
  const POLITICO = /pol[ií]tic|empresari|businessman|entrepreneur|psic[oó]log|psycholog|ling[uü]ist|fil[oó]sof|philosoph|papa |pope|dictator|revolutionar|monarch|emperor|primer ministro|primera ministra|prime minister|canciller|chancellor|leader|ayatol|dictador|ditador|caudill|pr[oó]cer|libertador|escritor|guerriller|revolucion|imperador|emperador|jurista|abolicion|antrop[oó]log|ambientalist|sacerdote|sindicalist|periodista|ide[oó]log|l[ií]der|militante|president|senador|diputad|deputad|gobernador|governador|ministr|alcalde|intendente|prefeit|vereador|congres|legislad|candidat|abogad|advogad|economist|activist|ativist|sindical|militar|jefe de gabinete|vocero|portavoz|porta-voz|politician|governor|mayor|senator/i;
  // cola: como mucho 4 consultas a Wikipedia a la vez (evita el límite de pedidos)
  let activas = 0; const espera = [];
  const turno = () => activas < 4 ? (activas++, Promise.resolve()) : new Promise(ok => espera.push(ok));
  const libre = () => { const sig = espera.shift(); if (sig) sig(); else activas-- };
  function foto(nombre) {
    if (nombre in FCACHE) return Promise.resolve(FCACHE[nombre]);
    if (FOTOS.has(nombre)) return FOTOS.get(nombre);
    const langs = S.ver === 'br' ? ['pt', 'es', 'en'] : ['es', 'pt', 'en'];
    const p = (async () => {
      await turno();
      let fallo = false;
      try {
      for (const l of langs) {
        try {
          const url = `https://${l}.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent((WIKI[nombre] || nombre).replace(/ /g, '_'))}`;
          let r = await fetch(url);
          if (r.status === 429) { await new Promise(ok => setTimeout(ok, 1500)); r = await fetch(url) }
          if (r.status === 429 || r.status >= 500) { fallo = true; continue }
          if (!r.ok) continue;
          const j = await r.json();
          if (j.type === 'disambiguation' || !j.thumbnail || !POLITICO.test((j.description || '') + ' ' + (j.extract || ''))) continue;
          return j.thumbnail.source;
        } catch (e) { fallo = true }
      }
      return fallo ? undefined : null;
      } finally { libre() }
    })().then(u => { if (u === undefined) { FOTOS.delete(nombre); return null } FCACHE[nombre] = u; try { sessionStorage.setItem('brujula_fotos', JSON.stringify(FCACHE)) } catch (e) { } return u });
    FOTOS.set(nombre, p);
    return p;
  }
  function fotos(root) {
    (root || document).querySelectorAll('.av[data-f]:not([data-ok])').forEach(el => {
      el.dataset.ok = '1';
      foto(el.dataset.f).then(u => { if (u) { const im = new Image(); im.alt = ''; im.onload = () => el.appendChild(im); im.src = u } });
    });
  }

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
    if (S.ejes) {
      portada();
      if ($('#s-preg').classList.contains('on')) pregunta();
      if ($('#s-demo').classList.contains('on')) opcionesDemo();
      if ($('#s-res').classList.contains('on')) resultado(S._enviado, S._link);
      if ($('#s-ejes').classList.contains('on')) guia();
      if ($('#s-mapa').classList.contains('on')) mapaPagina();
      if ($('#s-cara').classList.contains('on')) cara();
      if ($('#s-glos').classList.contains('on')) glosario();
      $('#hdr-ver').textContent = S.ver ? `${T().sub} · ${nombreVer(S.ver)}` : T().sub;
    }
  }

  // ------------------------------------------------------------ inicio
  function verInicial() {
    try { const g = JSON.parse(localStorage.getItem('brujula_res') || 'null'); if (g && g.ver && g.ver !== 'general' && S.ejes.versiones[g.ver]) return g.ver } catch (e) { }
    const reg = ((navigator.language || '').split('-')[1] || '').toUpperCase(), m = { AR: 'ar', BR: 'br', PY: 'py', PE: 'pe', CL: 'cl', CO: 'co', UY: 'uy' }[reg];
    if (m && S.ejes.versiones[m] && S.ejes.versiones[m].activa) return m;
    return S.lang === 'pt' ? 'br' : 'ar';
  }
  function portada() {
    const t = T(), act = Object.entries(S.ejes.versiones).filter(([id, v]) => v.activa && id !== 'general');
    const E = EJES();
    ejemplos();
    $('#pasos').innerHTML = t.pasos.map(([h, p], j) => `<div><i>0${j + 1}</i><b>${esc(h)}</b>${esc(p)}</div>`).join('');
    $('#ejlist').innerHTML = E.map(e => `<a href="#/ejes/${e.id}">${icb(e.id)}<span><b>${esc(e.nombre)}</b><small>${esc(e.a)} ↔ ${esc(e.b)}</small></span></a>`).join('');
    versiones();
  }
  // Tarjetas de ejemplo (estilo 12 ejes): un perfil parecido al de un dirigente real, su ideología más cercana y sus 12 ejes.
  // tarjetas en gris y azul: tonos de azul para unas familias, pizarra para otras
  const IDEO_COL = { libertarismo: ['#2563eb', '#0b1f4d'], lib_conservador: ['#1e40af', '#0a1433'], lib_progresista: ['#3b82c4', '#0e2a44'],
    socialdemocracia: ['#3b82c4', '#0e2a44'], socialismo_dem: ['#2563eb', '#0b1f4d'], comunismo: ['#1e40af', '#0a1433'], nacional_popular: ['#2563eb', '#0b1f4d'],
    desarrollismo: ['#5b6472', '#1b1f26'], centrismo: ['#5b6472', '#1b1f26'], democracia_cristiana: ['#3b82c4', '#0e2a44'], conservadurismo: ['#5b6472', '#1b1f26'],
    derecha_nacionalista: ['#1e40af', '#0a1433'], ecologismo: ['#3b82c4', '#0e2a44'], federalismo: ['#5b6472', '#1b1f26'], anarquismo: ['#5b6472', '#1b1f26'], tecnocracia: ['#2563eb', '#0b1f4d'] };
  const EJ_NOMBRES = ['Javier Milei', 'Luiz Inácio Lula da Silva', 'Axel Kicillof', 'Nayib Bukele', 'Gabriel Boric', 'Mauricio Macri'];
  let EJ_I = 0, EJ_T = null;
  function ejemplos() {
    const todos = Object.entries(S.fig).filter(([k, v]) => Array.isArray(v) && k !== 'latam').flatMap(([, v]) => v).concat(S.fig.latam || []), lista = [];
    EJ_NOMBRES.forEach(n => { const f = todos.find(x => x.nombre === n); if (f && !lista.includes(f)) lista.push(f) });
    if (!lista.length || !S.ideo.length) return;
    const el = $('#ejemplo'), t = T(), E = EJES();
    const pinta = () => {
      const f = lista[EJ_I % lista.length], sc = {};
      Object.keys(f.pos).forEach(k => { sc[k] = Math.round(f.pos[k] * 0.85 + 50 * 0.15) });
      const id = S.ideo.map(i => ({ i, af: afinidad(sc, Object.fromEntries(S.ejes.ejes.map((e, j) => [e.id, i.pos[j]]))) })).sort((a, b) => b.af - a.af)[0];
      const [c1, c2] = IDEO_COL[id.i.id] || ['#4a4e58', '#33363e'], pc = afinidad(sc, f.pos);
      el.style.setProperty('--c1', `color-mix(in srgb,${c1} 68%,${c2})`); el.style.setProperty('--c2', c2);
      el.innerHTML = `<div class="sch"><b><svg class="rose" viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="14.5"/><circle cx="16" cy="16" r="9"/><path d="M16 2v28M2 16h28"/><path class="n" d="M16 5l3 11h-6z"/><path class="s" d="M16 27l-3-11h6z"/></svg>${esc(t.sub)}</b><i></i><span>${esc(t.ej_tag)}</span></div>
        <div class="sct">${esc(t.ej_af)}</div><h3>${esc(ideoNom(id.i))}</h3>
        <div class="scg"><div class="scp"><span class="av scf" data-f="${esc(f.nombre)}">${esc(iniciales(f.nombre))}</span><div class="pc">${pc}%</div><small>${esc(t.ej_cerca)}</small><b>${esc(f.nombre)}</b><span>${esc(f.espacio || f.cargo || '')}</span></div>
        <div class="sca"><div class="t">${esc(t.ej_ejes)}</div>${E.map(e => { const v = sc[e.id], w = v > 50 ? v : 100 - v;
          return `<div class="scr"><span class="ib" style="--c0:${COLOR[e.id]}">${ic(e.id)}</span><span class="pn" title="${esc(e.nombre)}">${esc(polo(e, v))}</span><span class="xb2"><i style="width:${w}%;background:color-mix(in srgb,${COLOR[e.id]} 62%,#fff)"></i></span><em>${w}%</em></div>` }).join('')}</div></div>
        <div class="scd">${lista.map((x, j) => `<button aria-label="${esc(x.nombre)}" class="${j === EJ_I % lista.length ? 'on' : ''}" data-j="${j}"></button>`).join('')}</div>`;
      el.classList.remove('xin'); void el.offsetWidth; el.classList.add('xin');
      fotos(el);
    };
    el.onclick = ev => { const b = ev.target.closest('.scd button'); if (b) { EJ_I = +b.dataset.j; pinta(); reinicia() } };
    const reinicia = () => { clearInterval(EJ_T); EJ_T = setInterval(() => { if ($('#s-inicio').classList.contains('on') && !document.hidden) { EJ_I++; pinta() } }, 6500) };
    pinta(); reinicia();
  }
  function privacidad() {
    $('#priv-page').innerHTML = T().priv_t.map(x => `<li>${esc(x)}</li>`).join('');
  }
  function versiones() {
    const t = T();
    $('#versiones').innerHTML = Object.entries(S.ejes.versiones).filter(([id]) => id !== 'general').map(([id, v]) =>
      `<button class="ver${id === S.ver ? ' on' : ''}" data-v="${id}" ${v.activa ? '' : 'disabled'}>${bandera(id)}<b>${esc(nombreVer(id))}</b>${v.activa ? '' : `<span>${esc(t.pronto)}</span>`}</button>`).join('');
    $('#modos').innerHTML = ['rapida', 'completa', 'exhaustiva'].map(m => {
      const n = seleccion(S.ver, m).length;
      return `<div class="modo${m === 'completa' ? ' rec' : ''}">${m === 'completa' ? `<span class="tg">${esc(t.rec)}</span>` : ''}<b>${esc(t[m])}</b>
        <span class="n">${esc(t.modo_d(n, Math.max(2, Math.round(n * 9 / 60))))}</span><p>${esc(t['d_' + m])}</p>
        <button class="btn${m === 'completa' ? '' : ' ghost'}" data-m="${m}">${esc(t.empezar)} →</button></div>`;
    }).join('');
  }
  /* Express: las 4 frases originales por eje + 7 locales. Completa: 7 por eje (las 4 originales + 3 de la
     ampliación, alternando polos y prefiriendo intensidad media) + 11 locales. Exhaustiva: todas.
     Orden: eje por eje, con las locales intercaladas de forma pareja. */
  function seleccion(ver, modo) {
    const todas = S.preg.preguntas.filter(q => q.v.includes(ver));
    const extra = modo === 'rapida' ? 0 : modo === 'completa' ? 3 : 99, nLoc = modo === 'rapida' ? 7 : modo === 'completa' ? 11 : 999;
    const base = [];
    S.ejes.ejes.forEach(e => {
      const del = todas.filter(q => q.id[0] === 'x' && q.e[e.id]);
      const orig = del.filter(q => !q.extra), amp = del.filter(q => q.extra);
      const orden = s => amp.filter(q => Math.sign(q.e[e.id]) === s).sort((a, b) => Math.abs((a.nivel || 2) - 2.5) - Math.abs((b.nivel || 2) - 2.5));
      const pos = orden(1), neg = orden(-1), out = [];
      for (let j = 0; out.length < extra && (pos[j] || neg[j]); j++) { if (neg[j]) out.push(neg[j]); if (pos[j] && out.length < extra) out.push(pos[j]) }
      const sel = new Set([...orig, ...out]);
      base.push(...del.filter(q => sel.has(q)));
    });
    const pais = todas.filter(q => q.id[0] !== 'x' && q.id[0] !== 'g' && !q.nueva), gen = todas.filter(q => q.id[0] === 'g'), loc = [];
    for (let j = 0; loc.length < nLoc && (pais[2 * j] || pais[2 * j + 1] || gen[j]); j++) {
      [pais[2 * j], pais[2 * j + 1], gen[j]].forEach(q => { if (q && loc.length < nLoc) loc.push(q) });
    }
    // frases de los ejes complementarios (en Express, sólo las marcadas), mezcladas parejo con las locales
    const nuevas = todas.filter(q => q.nueva && (modo !== 'rapida' || q.rap)), locs = loc.splice(0);
    for (let j = 0; j < Math.max(locs.length, nuevas.length); j++) { if (locs[j]) loc.push(locs[j]); if (nuevas[j]) loc.push(nuevas[j]) }
    const out = [], paso = base.length / (loc.length + 1);
    let k = 0;
    base.forEach((q, j) => { out.push(q); while (k < loc.length && j + 1 >= Math.round(paso * (k + 1))) out.push(loc[k++]) });
    while (k < loc.length) out.push(loc[k++]);
    return out;
  }
  function show(id) {
    $$('.screen').forEach(s => s.classList.toggle('on', s.id === id));
    window.scrollTo({ top: 0 });
  }

  // ------------------------------------------------------------ preguntas
  function empezar(ver, modo) {
    S.ver = ver; S.modo = modo;
    S.qs = seleccion(ver, modo);
    if (location.hash && location.hash !== '#/') history.replaceState(null, '', location.pathname + location.search + '#/');
    S.ans = new Array(S.qs.length).fill(null);
    S.i = 0; S.t0 = Date.now();
    $('#hdr-ver').textContent = `${T().sub} · ${nombreVer(ver)}`;
    show('s-preg'); pregunta();
  }
  // Marca términos del glosario (primera aparición de cada uno) en un texto ya escapado.
  function glosar(html) {
    const usados = new Set();
    for (const [pat, term, def] of GLOS[S.lang] || []) {
      if (usados.has(term)) continue;
      const re = new RegExp(`(^|[^\\p{L}])(${pat})(?![\\p{L}])`, 'iu');
      if (re.test(html)) { html = html.replace(re, (m, pre, w) => `${pre}<span class="gt" tabindex="0" data-d="${esc(term)}|${esc(def)}">${w}</span>`); usados.add(term) }
    }
    return html;
  }
  function pregunta() {
    const q = S.qs[S.i], n = S.qs.length, t = T(), r = S.ans.filter(a => a !== null).length;
    const ks = Object.entries(q.e).filter(([, w]) => w).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1])), k0 = ks[0][0], e0 = ejeK(k0);
    $('#q-n').innerHTML = t.q_count(S.i + 1, n, r, n - r);
    $('#q-eje').style.color = COLOR[k0];
    $('#q-eje').innerHTML = `${ic(k0)}${esc(e0.nombre)}${ks.length > 1 ? ` <small>+ ${ks.slice(1).map(([k]) => esc(ejeK(k).nombre)).join(', ')}</small>` : ''}`;
    $('#q-t').innerHTML = glosar(esc(texto(q)));
    $('#prog-bar').style.width = (100 * r / n) + '%';
    $('#q-ops').innerHTML = respuestas().map((o, j) =>
      `<button class="op v${o.v}${S.ans[S.i] === o.v ? ' on' : ''}" data-v="${o.v}"><i>${j + 1}</i>${esc(o.t)}</button>`).join('');
    $('#q-back').disabled = S.i === 0;
    // ayuda "?": a qué polo te lleva estar de acuerdo o en desacuerdo, eje por eje
    const niv = q.nivel || (Math.abs(ks[0][1]) >= 2 ? 3 : 2);
    $('#q-ayuda').innerHTML = ks.map(([k, w]) => {
      const e = ejeK(k);
      return `<div>${t.ay_mide(esc(e.nombre))}</div><div class="pl"><div><small>${esc(t.ay_si)}</small><b style="color:${COLOR[k]}">${esc(w > 0 ? e.b : e.a)}</b></div><div><small>${esc(t.ay_no)}</small><b>${esc(w > 0 ? e.a : e.b)}</b></div></div>`;
    }).join('') + `<p class="meta" style="margin:10px 0 0">${esc(t.ay_niv(niv))}${$('#q-t .gt') ? ' ' + esc(t.ay_gl) : ''}</p>`;
    $('#q-lema').textContent = t.lemas[Math.floor(S.i / 7) % t.lemas.length];
    $('#q-reset').textContent = t.reiniciar; delete $('#q-reset').dataset.c;
    $('#pop').hidden = true;
  }
  function siguiente() {
    if (S.i < S.qs.length - 1) { S.i++; pregunta(); return }
    if (S.ans.some(a => a === null)) revision(); else terminar();
  }
  function responder(v) {
    if (S.lock) return;
    S.ans[S.i] = v; S.lock = true;
    $$('#q-ops .op').forEach(b => b.classList.toggle('on', +b.dataset.v === v));
    setTimeout(() => { S.lock = false; siguiente() }, 140);
  }
  function terminar() { $('#revision').hidden = true; $('#prog-bar').style.width = '100%'; demograficas() }
  function revision() {
    const r = S.ans.filter(a => a !== null).length;
    $('#rev-info').textContent = T().rev_info(r, S.qs.length);
    $('#rev').innerHTML = S.qs.map((q, j) => `<button class="${S.ans[j] !== null ? 'ok' : ''}${j === S.i ? ' cur' : ''}" data-j="${j}" title="${esc(texto(q))}">${j + 1}</button>`).join('');
    $('#revision').hidden = false;
  }

  // ------------------------------------------------------------ demográficas (opcionales)
  function opcionesDemo() {
    const f = $('#demo'), t = T();
    const opts = (a, sel) => `<option value="">${esc(t.elegi_op)}</option>` +
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
    const r2 = calcular(S.qs, S.ans, IDS2()); S.scores2 = r2.sc; S.cert2 = r2.cert;
    // respuestas por eje y distribución (para el análisis)
    S.nresp = {}; [...IDS(), ...IDS2()].forEach(k => { S.nresp[k] = 0 });
    S.qs.forEach((q, i) => { if (S.ans[i] !== null) Object.keys(q.e).forEach(k => { if (q.e[k] && k in S.nresp) S.nresp[k]++ }) });
    S.dist = [2, 1, 0, -1, -2].map(v => S.ans.filter(a => (a ?? 0) === v).length);
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
  function ranking(sc, cert) {
    const ids = IDS();
    const figs = figuras(S.ver).map(f => ({ f, af: afinidad(sc, f.pos, cert) })).sort((a, b) => b.af - a.af);
    S.hist = figurasH(S.ver).map(f => ({ f, af: afinidad(sc, f.pos, cert) })).sort((a, b) => b.af - a.af);
    S.intl = figurasInt(S.ver).map(f => ({ f, af: afinidad(sc, f.pos, cert) })).sort((a, b) => b.af - a.af);
    const ideo = S.ideo.map(i => { const pos = {}; ids.forEach((k, j) => { pos[k] = i.pos[j] }); return { i, pos, af: afinidad(sc, pos, cert) } }).sort((a, b) => b.af - a.af);
    return { figs, ideo };
  }
  const cercanos = (sc, pos, n) => IDS().map(k => ({ k, d: Math.abs(sc[k] - pos[k]) })).sort((a, b) => a.d - b.d).slice(0, n).map(x => ejeK(x.k).nombre);
  function resultado(enviado, desdeLink) {
    S._enviado = enviado; S._link = desdeLink;
    const t = T(), sc = S.scores, cert = S.cert, ver = S.ver, E = EJES(), rk = ranking(sc, cert);
    S.rk = rk;
    $('#hdr-ver').textContent = `${t.sub} · ${nombreVer(ver)}`;
    perfil(sc, cert, rk, desdeLink);
    barras(sc, cert, E);
    radar(sc, cert, E);
    brujula2d(sc, rk);
    ideologias(sc, rk);
    dirigentes(sc, cert, rk, ver);
    analisis(sc, cert, rk, E);
    complementarios();
    valoresYBandera();
    sobremesa();
    // compartir: versión, idioma, 12 posiciones y 12 certezas (+ los complementarios medidos, si hay)
    const ids = IDS(), ids2 = IDS2(), sc2 = S.scores2, ce2 = S.cert2;
    const ext = sc2 && ids2.every(k => sc2[k] != null) ? ['x', ...ids2.map(k => sc2[k]), ...ids2.map(k => ce2[k])] : [];
    const url = location.origin + location.pathname + '#r=' + [ver, S.lang, ...ids.map(k => sc[k]), ...ids.map(k => cert[k]), ...ext].join('-');
    const top = rk.figs[0];
    const txt = top ? t.share(top.af, top.f.nombre) : t.titulo;
    $('#share-wa').href = 'https://wa.me/?text=' + encodeURIComponent(txt + ' ' + url);
    $('#share-x').href = 'https://x.com/intent/post?text=' + encodeURIComponent(txt) + '&url=' + encodeURIComponent(url);
    $('#share').onclick = async () => {
      if (navigator.share) { try { await navigator.share({ title: t.titulo, text: txt, url }) } catch (e) { } }
      else copiar(txt + ' ' + url);
    };
    $('#copiar').textContent = t.copiar;
    $('#copiar').onclick = () => copiar(url);
    $('#descargar').onclick = descargar;
    $('#sent').textContent = enviado === true ? t.gracias : enviado === 'menor' ? t.menor : '';
    $('#again').textContent = desdeLink ? t.hacer : t.de_nuevo;
    $('#again').onclick = () => { history.replaceState(null, '', location.pathname + location.search + '#/'); show('s-inicio'); nav('quiz') };
    if (!desdeLink) { try { localStorage.setItem('brujula_res', JSON.stringify({ ver, sc, cert, sc2: S.scores2, cert2: S.cert2, n: S.nresp, dist: S.dist })) } catch (e) { } }
    show('s-res'); nav('quiz');
    fotos($('#s-res'));
    tarjeta();
  }
  // ------------------------------------------------------------ ejes complementarios, valores, bandera y sobremesa
  const L3 = o => o[S.lang] || o.es;
  // Posición de cualquier eje (12 principales o complementarios); null si no se midió.
  const pos = k => (S.scores && S.scores[k] != null) ? S.scores[k] : (S.scores2 && S.scores2[k] != null && (!S.nresp || S.nresp[k]) ? S.scores2[k] : null);
  const certK = k => (S.cert && S.cert[k] != null) ? S.cert[k] : (S.cert2 && S.cert2[k] != null ? S.cert2[k] : 0);
  const medidos2 = () => S.scores2 ? EJES2().filter(e => S.scores2[e.id] != null && (!S.nresp || S.nresp[e.id])) : [];

  function filaEje(e, s, c, n) {
    const t = T(), hw = (100 - c) / 4, lo = Math.max(0, s - hw), hi = Math.min(100, s + hw), col = COLOR[e.id] || 'var(--sig)';
    return `<div class="ec"><div class="h">${icb(e.id)}<b>${esc(e.nombre)}</b><small>${s}/100</small></div>
      <div class="pp"><span>${esc(e.a)}</span><span>${esc(e.b)}</span></div>
      <div class="trk" title="${esc(e.nombre)} · ${esc(t.certeza)} ${c}%"><span class="band" style="left:${lo}%;width:${hi - lo}%;background:${col}"></span>
        <span class="fill" style="left:${Math.min(s, 50)}%;width:${Math.abs(s - 50)}%;background:${col}"></span><span class="dot" style="left:${s}%;background:${col}"></span></div>
      <div class="ft"><span>${esc(lectura(e, s))}</span><span>${esc(t.certeza.toLowerCase())} ${c}%${n ? ' · ' + esc(t.resp(n)) : ''}</span></div></div>`;
  }
  function complementarios() {
    const t = T(), E2 = medidos2(), n = S._link ? null : S.nresp;
    $('#r-mas').hidden = !E2.length && !!S._link;
    $('#toc a[href="#r-mas"]').hidden = $('#r-mas').hidden;
    $('#ejes3').innerHTML = E2.length ? E2.map(e => filaEje(e, S.scores2[e.id], S.cert2[e.id], n && n[e.id])).join('')
      : `<p class="sub">${esc(t.mas_vacio)}</p>`;
  }

  // Polos más marcados de los 29 ejes (fuerza = distancia al centro, ponderada por certeza)
  function polosFuertes(min) {
    // los complementarios cuentan sólo con 2 o más respuestas y pesan un poco menos que los 12 principales
    const comp = new Set(IDS2()), ok = e => !comp.has(e.id) || !S.nresp || (S.nresp[e.id] || 0) >= 2;
    const todos = [...EJES(), ...EJES2()].filter(ok).map(e => ({ e, s: pos(e.id) })).filter(x => x.s != null);
    return todos.map(x => ({ ...x, lado: x.s < 50 ? 0 : 1, f: Math.abs(x.s - 50) * (0.5 + certK(x.e.id) / 200) * (comp.has(x.e.id) ? 0.85 : 1) }))
      .filter(x => Math.abs(x.s - 50) >= (min ?? 12)).sort((a, b) => b.f - a.f);
  }

  // Valores por tema: promedio con signo de varios ejes (positivo = el polo que nombra el primer rótulo)
  const TEMAS = [
    { k: { es: 'Política', pt: 'Política', en: 'Politics' }, ic: 'dem', ejes: [['dem', 1], ['ipe', -1], ['ges', -0.5]],
      r: { es: ['Mano firme en el poder', 'Liderazgo fuerte', 'Equilibrio de poderes', 'República con controles', 'Democracia participativa'],
           pt: ['Mão firme no poder', 'Liderança forte', 'Equilíbrio de poderes', 'República com controles', 'Democracia participativa'],
           en: ['Firm hand in power', 'Strong leadership', 'Balance of powers', 'Republic with checks', 'Participatory democracy'] } },
    { k: { es: 'Economía', pt: 'Economia', en: 'Economy' }, ic: 'pla', ejes: [['pla', 1], ['col', 1], ['dis', 0.5], ['bie', 0.5]],
      r: { es: ['Libre mercado', 'Mercado con reglas', 'Economía mixta', 'Estado presente', 'Economía planificada'],
           pt: ['Livre mercado', 'Mercado com regras', 'Economia mista', 'Estado presente', 'Economia planejada'],
           en: ['Free market', 'Market with rules', 'Mixed economy', 'Active state', 'Planned economy'] } },
    { k: { es: 'Mundo', pt: 'Mundo', en: 'World' }, ic: 'int', ejes: [['int', 1], ['glo', -1], ['uni', 0.5]],
      r: { es: ['Soberanismo', 'La nación primero', 'Pragmatismo exterior', 'Cooperación', 'Ciudadanía global'],
           pt: ['Soberanismo', 'A nação primeiro', 'Pragmatismo externo', 'Cooperação', 'Cidadania global'],
           en: ['Sovereigntism', 'Nation first', 'Pragmatic foreign policy', 'Cooperation', 'Global citizenship'] } },
    { k: { es: 'Sociedad', pt: 'Sociedade', en: 'Society' }, ic: 'pro', ejes: [['pro', 1], ['rel', 0.5], ['idc', 0.5]],
      r: { es: ['Muy tradicional', 'Tradicional', 'Moderado', 'Progresista', 'Muy progresista'],
           pt: ['Muito tradicional', 'Tradicional', 'Moderado', 'Progressista', 'Muito progressista'],
           en: ['Very traditional', 'Traditional', 'Moderate', 'Progressive', 'Very progressive'] } },
    { k: { es: 'Cultura y migración', pt: 'Cultura e migração', en: 'Culture & migration' }, ic: 'mig', ejes: [['mig', 1], ['uni', -0.5]],
      r: { es: ['Diversidad plena', 'Apertura', 'Balance', 'Integración selectiva', 'Asimilación'],
           pt: ['Diversidade plena', 'Abertura', 'Equilíbrio', 'Integração seletiva', 'Assimilação'],
           en: ['Full diversity', 'Openness', 'Balance', 'Selective integration', 'Assimilation'] } },
    { k: { es: 'Justicia', pt: 'Justiça', en: 'Justice' }, ic: 'lib', ejes: [['lib', -1], ['pen', 1]],
      r: { es: ['Mano dura', 'El orden primero', 'Equilibrio', 'Las garantías primero', 'Libertades y reinserción'],
           pt: ['Mão dura', 'A ordem primeiro', 'Equilíbrio', 'As garantias primeiro', 'Liberdades e reintegração'],
           en: ['Tough on crime', 'Order first', 'Balance', 'Rights first', 'Liberties and rehabilitation'] } },
    { k: { es: 'Ambiente', pt: 'Ambiente', en: 'Environment' }, ic: 'tec', ejes: [['ecl', 1], ['tec', -1]],
      r: { es: ['Producir primero', 'Desarrollo con cuidado', 'Equilibrio', 'El ambiente primero', 'Ecologismo profundo'],
           pt: ['Produzir primeiro', 'Desenvolvimento com cuidado', 'Equilíbrio', 'O ambiente primeiro', 'Ecologia profunda'],
           en: ['Production first', 'Careful development', 'Balance', 'Environment first', 'Deep ecology'] } },
    { k: { es: 'Forma de pensar', pt: 'Forma de pensar', en: 'Way of thinking' }, ic: 'epi', ejes: [['epi', 1], ['eti', 1]],
      r: { es: ['Convicciones firmes', 'Principios ante todo', 'Balance', 'Pragmatismo', 'Evidencia y resultados'],
           pt: ['Convicções firmes', 'Princípios acima de tudo', 'Equilíbrio', 'Pragmatismo', 'Evidência e resultados'],
           en: ['Firm convictions', 'Principles above all', 'Balance', 'Pragmatism', 'Evidence and results'] } },
  ];
  function temaVal(tm) {
    let num = 0, den = 0;
    tm.ejes.forEach(([k, w]) => { const s = pos(k); if (s != null) { num += w * (s - 50); den += Math.abs(w) } });
    if (!den) return null;
    const v = num / den, r = L3(tm.r);
    return { v, txt: v >= 30 ? r[0] : v >= 10 ? r[1] : v > -10 ? r[2] : v > -30 ? r[3] : r[4] };
  }

  // Bandera: colores de tus tres polos más marcados, diseño según el tema que más te define y escudo según tu polo principal.
  const PCOL = { fed: ['#2e7d4f', '#1f3f8f'], dem: ['#5aa0e6', '#2a2d33'], int: ['#3a7bd5', '#b03a2e'], mil: ['#5d6b3a', '#f4f4f4'], lib: ['#22355e', '#f0c419'],
    col: ['#c0392b', '#d4a52a'], rel: ['#a8b3bf', '#6b3fa0'], pro: ['#e0559a', '#7b4a2a'], mig: ['#7f8c8d', '#f39c12'], pla: ['#b71c1c', '#1e88e5'],
    glo: ['#8d6e63', '#26a69a'], tec: ['#00acc1', '#558b2f'], ecl: ['#2e7d32', '#616161'], dis: ['#d32f2f', '#ffb300'], bie: ['#ef6c00', '#455a64'],
    epi: ['#0288d1', '#4a148c'], ges: ['#37474f', '#fbc02d'], tra: ['#1565c0', '#c62828'], idc: ['#ffca28', '#6d4c41'], pen: ['#4db6ac', '#263238'],
    lab: ['#e53935', '#283593'], eti: ['#26c6da', '#5d4037'], tem: ['#ff7043', '#3949ab'], fut: ['#66bb6a', '#ffa726'], ind: ['#795548', '#29b6f6'],
    mon: ['#ab47bc', '#1a237e'], inf: ['#f5f5f5', '#212121'], ipe: ['#8e24aa', '#1565c0'], uni: ['#42a5f5', '#8d1d1d'] };
  const PEMB = { fed: ['ring', 'star'], dem: ['ring', 'shield'], int: ['ring', 'star'], mil: ['shield', 'leaf'], lib: ['shield', 'sun'], col: ['gear', 'chevron'],
    rel: ['sun', 'cross'], pro: ['sun', 'cross'], mig: ['star', 'ring'], pla: ['gear', 'chevron'], glo: ['star', 'ring'], tec: ['sun', 'leaf'], ecl: ['leaf', 'gear'],
    dis: ['scale', 'chevron'], bie: ['ring', 'chevron'], epi: ['sun', 'cross'], ges: ['gear', 'ring'], tra: ['scale', 'star'], idc: ['chevron', 'ring'],
    pen: ['scale', 'shield'], lab: ['ring', 'chevron'], eti: ['scale', 'cross'], tem: ['star', 'sun'], fut: ['leaf', 'sun'], ind: ['gear', 'ring'],
    mon: ['star', 'scale'], inf: ['ring', 'shield'], ipe: ['star', 'scale'], uni: ['ring', 'star'] };
  const FAM = { eco: ['pla', 'col', 'dis', 'bie', 'lab', 'mon', 'ind', 'glo'], pod: ['dem', 'ipe', 'ges', 'lib', 'inf', 'pen'], nac: ['int', 'uni', 'mil', 'fed'],
    val: ['pro', 'rel', 'idc', 'mig'], ide: ['tec', 'ecl', 'epi', 'eti', 'tem', 'fut', 'tra'] };
  function luz(hex) { const n = parseInt(hex.slice(1), 16); return (0.299 * (n >> 16) + 0.587 * (n >> 8 & 255) + 0.114 * (n & 255)) / 255 }
  function emblema(tipo, cx, cy, r, col) {
    const st = `fill="${col}"`, sk = `fill="none" stroke="${col}" stroke-width="${r * 0.16}" stroke-linecap="round" stroke-linejoin="round"`;
    const pt = (n, R, rot) => Array.from({ length: n }, (_, i) => { const a = rot + i * 2 * Math.PI / n; return [cx + R * Math.cos(a), cy + R * Math.sin(a)] });
    switch (tipo) {
      case 'star': return `<polygon ${st} points="${pt(10, r, -Math.PI / 2).map(([x, y], i) => i % 2 ? [cx + (x - cx) * 0.42, cy + (y - cy) * 0.42] : [x, y]).map(p => p.map(v => v.toFixed(1)).join(',')).join(' ')}"/>`;
      case 'sun': return `<circle cx="${cx}" cy="${cy}" r="${r * 0.45}" ${st}/>` + pt(12, r, 0).map(([x, y]) => `<line x1="${(cx + (x - cx) * 0.6).toFixed(1)}" y1="${(cy + (y - cy) * 0.6).toFixed(1)}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" ${sk}/>`).join('');
      case 'gear': return `<circle cx="${cx}" cy="${cy}" r="${r * 0.62}" ${sk}/><circle cx="${cx}" cy="${cy}" r="${r * 0.22}" ${st}/>` + pt(8, r, 0).map(([x, y]) => `<line x1="${(cx + (x - cx) * 0.66).toFixed(1)}" y1="${(cy + (y - cy) * 0.66).toFixed(1)}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" ${sk}/>`).join('');
      case 'leaf': return `<path ${st} d="M${cx - r * 0.8} ${cy + r * 0.8}C${cx - r * 0.8} ${cy - r * 0.3} ${cx - r * 0.1} ${cy - r} ${cx + r * 0.85} ${cy - r * 0.85}C${cx + r} ${cy + r * 0.1} ${cx + r * 0.3} ${cy + r * 0.8} ${cx - r * 0.8} ${cy + r * 0.8}z"/>`;
      case 'scale': return `<g ${sk}><line x1="${cx}" y1="${cy - r}" x2="${cx}" y2="${cy + r}"/><line x1="${cx - r}" y1="${cy - r * 0.55}" x2="${cx + r}" y2="${cy - r * 0.55}"/><line x1="${cx - r * 0.5}" y1="${cy + r}" x2="${cx + r * 0.5}" y2="${cy + r}"/><path d="M${cx - r} ${cy - r * 0.55}l-${r * 0.35} ${r * 0.75}h${r * 0.7}zM${cx + r} ${cy - r * 0.55}l-${r * 0.35} ${r * 0.75}h${r * 0.7}z"/></g>`;
      case 'cross': return `<g ${st}><rect x="${cx - r * 0.16}" y="${cy - r}" width="${r * 0.32}" height="${r * 2}"/><rect x="${cx - r * 0.65}" y="${cy - r * 0.5}" width="${r * 1.3}" height="${r * 0.32}"/></g>`;
      case 'shield': return `<path ${st} d="M${cx} ${cy - r}L${cx + r * 0.8} ${cy - r * 0.65}V${cy}C${cx + r * 0.8} ${cy + r * 0.55} ${cx + r * 0.4} ${cy + r * 0.85} ${cx} ${cy + r}C${cx - r * 0.4} ${cy + r * 0.85} ${cx - r * 0.8} ${cy + r * 0.55} ${cx - r * 0.8} ${cy}V${cy - r * 0.65}z"/>`;
      case 'chevron': return `<path ${sk} d="M${cx - r * 0.8} ${cy + r * 0.2}L${cx} ${cy - r * 0.6}L${cx + r * 0.8} ${cy + r * 0.2}M${cx - r * 0.8} ${cy + r * 0.8}L${cx} ${cy}L${cx + r * 0.8} ${cy + r * 0.8}"/>`;
      default: return pt(8, r * 0.78, 0).map(([x, y]) => `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r * 0.17}" ${st}/>`).join('') + `<circle cx="${cx}" cy="${cy}" r="${r * 0.3}" ${st}/>`;
    }
  }
  function banderaPersonal(fuertes) {
    const W = 300, H = 200, top = fuertes.slice(0, 3), cols = [];
    top.forEach(x => { const c = PCOL[x.e.id][x.lado]; if (!cols.includes(c)) cols.push(c) });
    while (cols.length < 3) cols.push(['#4f8ff7', '#e9edf2', '#2a2f37'][cols.length]);
    const [c1, c2, c3] = cols, p0 = top[0], fam = p0 ? Object.keys(FAM).find(f => FAM[f].includes(p0.e.id)) : 'val';
    const emb = p0 ? PEMB[p0.e.id][p0.lado] : 'ring';
    const conEmb = (bg, cx, cy, r) => emblema(emb, cx, cy, r, luz(bg) > 0.6 ? '#1b1f26' : '#ffffff');
    let g = '';
    if (fam === 'eco') g = `<rect width="${W}" height="${H}" fill="${c1}"/><rect y="${H / 3}" width="${W}" height="${H / 3}" fill="${c2}"/><rect y="${2 * H / 3}" width="${W}" height="${H / 3}" fill="${c3}"/>${conEmb(c2, W / 2, H / 2, 26)}`;
    else if (fam === 'pod') g = `<rect width="${W}" height="${H}" fill="${c2}"/><rect y="${H / 2}" width="${W}" height="${H / 2}" fill="${c3}"/><rect width="${W * 0.42}" height="${H / 2}" fill="${c1}"/>${conEmb(c1, W * 0.21, H / 4, 30)}`;
    else if (fam === 'nac') g = `<rect width="${W}" height="${H}" fill="${c1}"/><rect x="${W * 0.3}" width="${W * 0.16}" height="${H}" fill="${c2}"/><rect y="${H * 0.42}" width="${W}" height="${H * 0.16}" fill="${c2}"/><rect x="${W * 0.34}" width="${W * 0.08}" height="${H}" fill="${c3}"/><rect y="${H * 0.46}" width="${W}" height="${H * 0.08}" fill="${c3}"/>${conEmb(c1, W * 0.15, H * 0.21, 22)}`;
    else if (fam === 'ide') g = `<rect width="${W}" height="${H}" fill="${c1}"/><path d="M${W} 0V${H}H0z" fill="${c2}"/><path d="M${W} ${H * 0.45}V${H}H${W * 0.32}z" fill="${c3}"/>${conEmb(c1, W * 0.27, H * 0.33, 30)}`;
    else g = `<rect width="${W}" height="${H}" fill="${c1}"/><rect x="${W / 3}" width="${W / 3}" height="${H}" fill="${c2}"/><rect x="${2 * W / 3}" width="${W / 3}" height="${H}" fill="${c3}"/>${conEmb(c2, W / 2, H / 2, 32)}`;
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="${esc(T().band_k)}">${g}<rect width="${W}" height="${H}" fill="none" stroke="rgba(0,0,0,.18)" stroke-width="2"/></svg>`;
  }
  function descargarBandera() {
    const svg = $('#bandera svg'); if (!svg) return;
    const im = new Image(), url = URL.createObjectURL(new Blob([svg.outerHTML], { type: 'image/svg+xml' }));
    im.onload = () => {
      const cv = document.createElement('canvas'); cv.width = 1200; cv.height = 800;
      cv.getContext('2d').drawImage(im, 0, 0, 1200, 800); URL.revokeObjectURL(url);
      cv.toBlob(b => { const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = 'mi-bandera-brujula.png'; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 4000) }, 'image/png');
    };
    im.src = url;
  }
  function valoresYBandera() {
    const t = T(), f = polosFuertes(), top = f.slice(0, 5);
    const lema = f.slice(0, 3).map(x => x.lado ? x.e.b : x.e.a);
    $('#bandera').innerHTML = banderaPersonal(f) + `<p class="lema-b">${esc(lema.join(' · ') || t.equilibrado)}</p>`;
    $('#band-dl').textContent = t.band_dl; $('#band-dl').onclick = descargarBandera;
    $('#valoras').innerHTML = top.length ? top.map(x => `<span class="vchip">${icb(x.e.id)}<b>${esc(x.lado ? x.e.b : x.e.a)}</b><small>${Math.round(x.lado ? x.s : 100 - x.s)}%</small></span>`).join('')
      : `<p class="sub">${esc(t.centro)}</p>`;
    $('#temas').innerHTML = TEMAS.map(tm => { const r = temaVal(tm); return r ? `<div class="vt">${icb(tm.ic)}<small>${esc(L3(tm.k))}</small><b>${esc(r.txt)}</b></div>` : '' }).join('');
  }

  // Modo sobremesa: humor, no mide nada.
  const SOB = [
    { k: { es: 'Cuando llega la cuenta', pt: 'Quando chega a conta', en: 'When the bill comes' }, f: () => (pos('pla') ?? 50) - 50,
      r: { es: ['Cada uno paga lo suyo, con centavos', 'Se divide, pero el que pidió de más pone más', 'Partes iguales y no se habla más'],
           pt: ['Cada um paga o seu, com centavos', 'Divide, mas quem pediu mais paga mais', 'Partes iguais e assunto encerrado'],
           en: ['Everyone pays their own, to the cent', 'Split it, but whoever ordered more pays more', 'Equal shares, end of story'] } },
    { k: { es: 'En el grupo de la familia', pt: 'No grupo da família', en: 'In the family group chat' }, f: () => (pos('dem') ?? 50) - 50,
      r: { es: ['Sos admin y ponés las reglas', 'Opinás, pero sin armar lío', 'Proponés una encuesta para todo'],
           pt: ['Você é admin e dita as regras', 'Opina, mas sem criar confusão', 'Propõe enquete para tudo'],
           en: ['You are the admin and set the rules', 'You chime in without starting a fight', 'You propose a poll for everything'] } },
    { k: { es: 'Con el control remoto', pt: 'Com o controle remoto', en: 'With the remote' }, f: () => (pos('pro') ?? 50) - 50,
      r: { es: ['El mismo canal de siempre', 'Un clásico y algo nuevo', 'La serie que salió ayer'],
           pt: ['O mesmo canal de sempre', 'Um clássico e algo novo', 'A série que saiu ontem'],
           en: ['The same old channel', 'A classic and something new', 'The show that came out yesterday'] } },
    { k: { es: 'De vacaciones', pt: 'Nas férias', en: 'On holiday' }, f: () => (pos('int') ?? 50) - 50,
      r: { es: ['Recorrer el país, que hay mucho por ver', 'Un año acá, otro afuera', 'Pasaporte en mano y a conocer el mundo'],
           pt: ['Rodar o país, tem muito para ver', 'Um ano aqui, outro fora', 'Passaporte na mão e o mundo pela frente'],
           en: ['See your own country first', 'One year here, one abroad', 'Passport ready, the world awaits'] } },
  ];
  function sobremesa() {
    const t = T(), vals = Object.values(S.scores), cert = Object.values(S.cert);
    const conv = vals.reduce((a, v) => a + Math.abs(v - 50), 0) / vals.length, coh = cert.reduce((a, c) => a + c, 0) / cert.length;
    const T1 = conv >= 25 ? t.sat_c[0] : conv >= 16 ? t.sat_c[1] : conv >= 9 ? t.sat_c[2] : t.sat_c[3];
    const T2 = coh >= 65 ? t.sat_h[0] : coh >= 45 ? t.sat_h[1] : coh >= 25 ? t.sat_h[2] : t.sat_h[3];
    $('#sob').innerHTML = `<div class="sat"><div><small>${esc(t.sat_ck)}</small><b>${esc(T1)}</b></div><div><small>${esc(t.sat_hk)}</small><b>${esc(T2)}</b></div></div>
      <div class="vg">${SOB.map(x => { const v = x.f(), r = L3(x.r); return `<div class="vt"><small>${esc(L3(x.k))}</small><b>${esc(v > 12 ? r[0] : v < -12 ? r[2] : r[1])}</b></div>` }).join('')}</div>`;
  }

  async function copiar(s) { try { await navigator.clipboard.writeText(s); $('#copiar').textContent = T().copiado } catch (e) { } }

  function perfil(sc, cert, rk, desdeLink) {
    const t = T(), i0 = rk.ideo[0], i1 = rk.ideo[1], vals = Object.values(sc);
    const marc = vals.filter(v => Math.abs(v - 50) >= 25).length, cob = Object.values(cert).filter(c => c >= 40).length;
    const tot = S.dist ? S.dist.reduce((a, b) => a + b, 0) : 0;
    const op = tot && !desdeLink ? Math.round(100 * (1 - S.dist[2] / tot)) + '%' : '—';
    const dom = EJES().map(e => ({ e, d: Math.abs(sc[e.id] - 50) * (0.5 + cert[e.id] / 200) })).sort((a, b) => b.d - a.d);
    const fuertes = dom.filter(x => Math.abs(sc[x.e.id] - 50) >= 15).slice(0, 3).map(x => polo(x.e, sc[x.e.id]));
    $('#r-perfil').innerHTML = `${ring(i0.af)}<div><div class="k">${esc(desdeLink ? t.res_link : t.af_principal)} · ${esc(nombreVer(S.ver))}</div>
      <h2>${esc(ideoNom(i0.i))}</h2><p>${esc(ideoDesc(i0.i))}</p>
      <p>${esc(t.frase(ideoNom(i0.i), i1 && i1.af >= i0.af - 6 ? ideoNom(i1.i) : ''))} ${esc(fuertes.length ? t.define(lista(fuertes)) : t.centro)}</p></div>
      <div class="kpis"><div><b>${marc}/12</b><small>${esc(t.k_marc)}</small></div><div><b>${cob}/12</b><small>${esc(t.k_cob)}</small></div>
      <div><b>${op}</b><small>${esc(t.k_op)}</small></div><div><b>${media(cert)}%</b><small>${esc(t.k_cert)}</small></div></div>`;
  }
  function barras(sc, cert, E) {
    const t = T(), n = S._link ? null : S.nresp;
    $('#ejes').innerHTML = E.map(e => {
      const s = sc[e.id], c = cert[e.id], hw = (100 - c) / 4, lo = Math.max(0, s - hw), hi = Math.min(100, s + hw), col = COLOR[e.id];
      return `<div class="ec"><div class="h">${icb(e.id)}<b>${esc(e.nombre)}</b><small>${s}/100</small></div>
        <div class="pp"><span>${esc(e.a)}</span><span>${esc(e.b)}</span></div>
        <div class="trk" title="${esc(e.nombre)} · ${esc(t.certeza)} ${c}%"><span class="band" style="left:${lo}%;width:${hi - lo}%;background:${col}"></span>
          <span class="fill" style="left:${Math.min(s, 50)}%;width:${Math.abs(s - 50)}%;background:${col}"></span><span class="dot" style="left:${s}%;background:${col}"></span></div>
        <div class="ft"><span>${esc(lectura(e, s))}</span><span>${esc(t.certeza.toLowerCase())} ${c}%${n ? ' · ' + esc(t.resp(n[e.id])) : ''}</span></div></div>`;
    }).join('');
  }
  function radar(sc, cert, E) {
    const t = T(), W = 560, C = W / 2, R = 170, N = E.length, ang = j => -Math.PI / 2 + 2 * Math.PI * j / N;
    const pt = (j, v) => [C + R * v / 100 * Math.cos(ang(j)), C + R * v / 100 * Math.sin(ang(j))];
    let g = `<svg viewBox="0 0 ${W} ${W}" role="img" aria-label="Radar">`;
    [25, 50, 75, 100].forEach(v => { g += `<polygon class="rg" points="${E.map((e, j) => pt(j, v).join(',')).join(' ')}"/>` });
    E.forEach((e, j) => {
      const [x, y] = pt(j, 100), [lx, ly] = pt(j, 116), anc = Math.abs(lx - C) < 10 ? 'middle' : lx > C ? 'start' : 'end';
      g += `<line class="sp" x1="${C}" y1="${C}" x2="${x}" y2="${y}"/><text x="${lx}" y="${ly - 6}" text-anchor="${anc}"><tspan fill="${COLOR[e.id]}" font-weight="700">${esc(e.b)}</tspan><tspan x="${lx}" dy="12">${esc(e.nombre)}</tspan></text>`;
    });
    g += `<polygon class="ce" points="${E.map((e, j) => pt(j, cert[e.id]).join(',')).join(' ')}"/>`;
    g += `<polygon class="yo" points="${E.map((e, j) => pt(j, sc[e.id]).join(',')).join(' ')}"/>`;
    E.forEach((e, j) => { const [x, y] = pt(j, sc[e.id]); g += `<circle cx="${x}" cy="${y}" r="4" fill="${COLOR[e.id]}"><title>${esc(e.nombre)} ${sc[e.id]}</title></circle>` });
    $('#radar').innerHTML = g + '</svg>' + `<div class="leyenda"><span><i style="background:var(--sig)"></i>${esc(t.leg_pos)}</span><span><i style="background:var(--a)"></i>${esc(t.leg_cert)}</span></div>`;
  }
  // Brújula 2D: económico = (pla + col) / 2; poder = (dem + (100 - lib)) / 2 (arriba = autoridad).
  const bx = p => (p.pla + p.col) / 2, by = p => (p.dem + 100 - p.lib) / 2;
  function brujula2d(sc, rk) {
    const t = T(), W = 440, C = W / 2, R = 180, X = v => C + R * (v - 50) / 50, Y = v => C - R * (v - 50) / 50;
    let g = `<svg viewBox="0 0 ${W} ${W}" role="img" aria-label="${esc(t.t_brujula2)}"><defs><clipPath id="cc"><circle cx="${C}" cy="${C}" r="${R}"/></clipPath>
      <radialGradient id="rgc"><stop offset="0" stop-color="var(--s1)" stop-opacity=".95"/><stop offset="1" stop-color="var(--s1)" stop-opacity="0"/></radialGradient></defs>
      <g clip-path="url(#cc)" opacity=".4"><rect x="0" y="0" width="${C}" height="${C}" fill="${COLOR.col}"/><rect x="${C}" y="0" width="${C}" height="${C}" fill="${COLOR.dem}"/>
      <rect x="0" y="${C}" width="${C}" height="${C}" fill="${COLOR.pla}"/><rect x="${C}" y="${C}" width="${C}" height="${C}" fill="${COLOR.glo}"/></g>
      <circle cx="${C}" cy="${C}" r="${R}" fill="url(#rgc)"/><circle cx="${C}" cy="${C}" r="${R}" fill="none" stroke="var(--line2)"/>
      <circle cx="${C}" cy="${C}" r="${R / 2}" fill="none" stroke="var(--line2)" stroke-dasharray="3 4"/>
      <line x1="${C - R}" x2="${C + R}" y1="${C}" y2="${C}" stroke="var(--line2)"/><line y1="${C - R}" y2="${C + R}" x1="${C}" x2="${C}" stroke="var(--line2)"/>
      <text class="lb" x="${C}" y="${C - R - 10}" text-anchor="middle">▲ ${esc(t.b_aut)}</text><text class="lb" x="${C}" y="${C + R + 20}" text-anchor="middle">▼ ${esc(t.b_lib)}</text>
      <text class="lb" x="${C - R + 6}" y="${C - 6}">◀ ${esc(t.b_estado)}</text><text class="lb" x="${C + R - 6}" y="${C - 6}" text-anchor="end">${esc(t.b_mercado)} ▶</text>`;
    // sólo se rotulan la ideología y el dirigente más cercanos; el resto tiene tooltip (así no se pisan los nombres)
    rk.ideo.slice(0, 4).forEach(({ i, pos }, j) => { g += `<g class="id"><circle cx="${X(bx(pos))}" cy="${Y(by(pos))}" r="4"><title>${esc(ideoNom(i))}</title></circle>${j ? '' : `<text x="${X(bx(pos)) + 7}" y="${Y(by(pos)) - 6}">${esc(ideoNom(i))}</text>`}</g>` });
    rk.figs.slice(0, 3).forEach(({ f }, j) => { g += `<g class="fg"><circle cx="${X(bx(f.pos))}" cy="${Y(by(f.pos))}" r="4"><title>${esc(f.nombre)}</title></circle>${j ? '' : `<text x="${X(bx(f.pos)) + 7}" y="${Y(by(f.pos)) + 12}">${esc(apellido(f.nombre))}</text>`}</g>` });
    const ux = bx(sc), uy = by(sc), yo = { es: 'VOS', pt: 'VOCÊ', en: 'YOU' }[S.lang];
    g += `<g class="yo"><circle cx="${X(ux)}" cy="${Y(uy)}" r="9"/><text x="${X(ux) + 12}" y="${Y(uy) - 10}">${yo}</text></g></svg>`;
    const dx = ux - 50, dy = uy - 50, d = Math.round(Math.hypot(dx, dy));
    const q = d < 12 ? 'c' : (dy >= 0 ? 't' : 'b') + (dx < 0 ? 'l' : 'r'), [qn, qt] = t.cuad[q], ep = ejeK('pro'), sp = sc.pro;
    $('#bru').innerHTML = `<div>${g}</div><div class="interp"><b>${esc(qn)}</b><p>${esc(qt)} ${esc(t.dist_c(d))}</p>
      <div class="sld"><div class="k">${esc(t.b_pro)}</div><div class="pp"><span>${esc(ep.a)}</span><span>${esc(ep.b)}</span></div>
      <div class="trk"><span class="fill" style="left:${Math.min(sp, 50)}%;width:${Math.abs(sp - 50)}%;background:${COLOR.pro}"></span><span class="dot" style="left:${sp}%;background:${COLOR.pro}"></span></div>
      <p class="meta" style="margin-top:8px">${esc(lectura(ep, sp))}</p></div></div>`;
  }
  function ideologias(sc, rk) {
    const t = T();
    $('#ideo').innerHTML = `<div class="lst">${rk.ideo.slice(0, 5).map(({ i, pos, af }, j) => `<div class="it${j ? '' : ' first'}"><i>${String(j + 1).padStart(2, '0')}</i><b>${esc(ideoNom(i))}</b><span class="pc">${af}%</span>
      <p>${esc(ideoDesc(i))}</p><span class="bar"><i style="width:${af}%"></i></span><small>${esc(t.coinc)}: ${esc(lista(cercanos(sc, pos, 3)))}</small></div>`).join('')}</div>
      <div class="lejos">${esc(t.lejos_i)} ${rk.ideo.slice(-3).reverse().map(x => `<span>${esc(ideoNom(x.i))} · ${x.af}%</span>`).join('')}</div>`;
  }
  function dirigentes(sc, cert, rk, ver) {
    const t = T(), F = rk.figs;
    if (!F.length) { $('#dir').innerHTML = ''; $('#dir-sub').textContent = ''; return }
    $('#dir-sub').textContent = t.dir_sub(F.length, nombreVer(ver));
    const cmp = f => `#/cara/${encodeURIComponent(f.nombre)}`, top = F[0];
    const dims = Object.entries(DIMS).map(([d, ks]) => {
      const b = F.map(({ f }) => ({ f, af: afinidad(sc, f.pos, cert, ks) })).sort((a, b) => b.af - a.af)[0];
      return `<div>${avatar(b.f)}<span><small>${esc(t[d])}</small>${esc(b.f.nombre)} <em>${b.af}%</em></span></div>`;
    }).join('');
    $('#dir').innerHTML = `<div class="top1">${avatar(top.f, 'lg')}<div><small>${esc(top.f.cargo || '')}${top.f.espacio ? ' · ' + esc(top.f.espacio) : ''}</small><b>${esc(top.f.nombre)}</b>
        <p>${esc(t.coinc)}: ${esc(lista(cercanos(sc, top.f.pos, 3)))}</p><a href="${cmp(top.f)}">${esc(t.comparar)}</a></div>${ring(top.af)}</div>
      <div class="k" style="margin-top:16px">${esc(t.tambien)}</div><div class="dims">${dims}</div>
      <div class="fgrid">${F.slice(1, 9).map(({ f, af }) => `<div class="fc">${avatar(f)}<b>${esc(f.nombre)}</b><span class="pc">${af}%</span><small>${esc(f.cargo || f.pais || '')}${f.espacio ? ' · ' + esc(f.espacio) : ''}</small><a href="${cmp(f)}">${esc(t.comparar)}</a></div>`).join('')}</div>
      <div class="lejos">${esc(t.lejos_d)} ${F.slice(-3).reverse().map(x => `<span>${esc(x.f.nombre)} · ${x.af}%</span>`).join('')}</div>` +
      [[S.intl, t.int_k], [S.hist, t.hist_k]].map(([L, k]) => (L || []).length ? `<div class="k" style="margin-top:18px">${esc(k)}</div><div class="fgrid">${L.slice(0, 6).map(({ f, af }) => `<div class="fc">${avatar(f)}<b>${esc(f.nombre)}</b><span class="pc">${af}%</span><small>${esc(f.cargo || '')}${f.int && f.pais ? ' · ' + esc(f.pais) : ''}</small><a href="${cmp(f)}">${esc(t.comparar)}</a></div>`).join('')}</div>` : '').join('');
    fotos($('#dir'));
  }
  function analisis(sc, cert, rk, E) {
    const t = T(), n = S._link ? null : S.nresp;
    // 1. mapa de certeza: intensidad (distancia al centro × 2) contra certeza
    const W = 420, H = 280, P = 28, X = v => P + (W - 2 * P) * v / 100, Y = v => H - P - (H - 2 * P) * v / 100;
    let g = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(t.a_mapa)}"><rect x="${P}" y="${P}" width="${W - 2 * P}" height="${H - 2 * P}" fill="none" stroke="var(--line2)"/>
      <line x1="${X(50)}" x2="${X(50)}" y1="${P}" y2="${H - P}" stroke="var(--line2)" stroke-dasharray="3 4"/><line x1="${P}" x2="${W - P}" y1="${Y(50)}" y2="${Y(50)}" stroke="var(--line2)" stroke-dasharray="3 4"/>
      <text class="q" x="${W - P - 4}" y="${P + 12}" text-anchor="end">${esc(t.a_q[0])}</text><text class="q" x="${P + 4}" y="${P + 12}">${esc(t.a_q[1])}</text>
      <text class="q" x="${W - P - 4}" y="${H - P - 6}" text-anchor="end">${esc(t.a_q[2])}</text><text class="q" x="${P + 4}" y="${H - P - 6}">${esc(t.a_q[3])}</text>`;
    E.forEach(e => {
      const x = X(Math.min(100, 2 * Math.abs(sc[e.id] - 50))), y = Y(cert[e.id]), izq = x > W - 110;
      g += `<g><circle cx="${x}" cy="${y}" r="6" fill="${COLOR[e.id]}" stroke="var(--s1)" stroke-width="1.5"><title>${esc(e.nombre)} · ${sc[e.id]} · ${cert[e.id]}%</title></circle><text x="${izq ? x - 9 : x + 9}" y="${y + 3}" text-anchor="${izq ? 'end' : 'start'}">${esc(e.nombre)}</text></g>`;
    });
    g += '</svg>';
    // 2. tensiones
    const tens = PARES.map(([a, b, s]) => ({ a, b, gap: Math.abs(sc[a] - (s > 0 ? sc[b] : 100 - sc[b])), ok: Math.abs(sc[a] - 50) >= 12 && Math.abs(sc[b] - 50) >= 12 }))
      .filter(x => x.ok && x.gap >= 35).sort((p, q) => q.gap - p.gap).slice(0, 4);
    const tensH = tens.length ? tens.map(x => { const ea = ejeK(x.a), eb = ejeK(x.b); return `<div>${t.tension(esc(polo(ea, sc[x.a])), esc(ea.nombre), esc(polo(eb, sc[x.b])), esc(eb.nombre))}</div>` }).join('')
      : `<div class="ok">${esc(t.sin_tens)}</div>`;
    // 3. qué te separa del dirigente más cercano
    const top = rk.figs[0];
    let sep = '';
    if (top) {
      const ds = E.map(e => ({ e, d: sc[e.id] - top.f.pos[e.id] })).sort((p, q) => Math.abs(p.d) - Math.abs(q.d));
      const fila = (x, cls) => `<div class="dif"><span style="text-align:left;font:12.5px var(--body);color:var(--muted)">${esc(x.e.nombre)}</span><div class="t"><i class="${cls}" style="left:${Math.min(sc[x.e.id], top.f.pos[x.e.id])}%;width:${Math.max(2, Math.abs(x.d))}%"></i></div><span>${Math.round(Math.abs(x.d))}</span></div>`;
      sep = `<h4>${esc(t.a_sep(top.f.nombre))}</h4><div class="k">${esc(t.a_cerca)}</div>${ds.slice(0, 3).map(x => fila(x, 'c')).join('')}<div class="k" style="margin-top:10px">${esc(t.a_lejos)}</div>${ds.slice(-3).reverse().map(x => fila(x, '')).join('')}`;
    }
    // 4. cómo respondiste
    let dist;
    const tot = S.dist ? S.dist.reduce((a, b) => a + b, 0) : 0;
    if (tot && !S._link) {
      const cols = ['#3fbf7f', '#8fd6ae', 'var(--dim)', '#f0a0a0', '#ef5d5d'], R = respuestas();
      dist = `<h4>${esc(t.a_dist)}</h4><div class="dist">${S.dist.map((v, j) => `<i style="width:${100 * v / tot}%;background:${cols[j]}" title="${esc(R[j].t)}: ${v}"></i>`).join('')}</div>
        <div class="leyenda">${S.dist.map((v, j) => `<span><i style="background:${cols[j]}"></i>${esc(R[j].t)} ${v}</span>`).join('')}</div>
        <p class="meta">${esc(t.a_dist_t(Math.round(100 * (S.dist[0] + S.dist[4]) / tot), Math.round(100 * S.dist[2] / tot)))}</p>`;
    } else dist = `<p class="meta">${esc(t.sin_resp)}</p>`;
    // 5. tabla técnica
    const lect = c => c >= 60 ? t.lect[0] : c >= 35 ? t.lect[1] : t.lect[2];
    const tabla = `<table class="tt"><thead><tr>${t.th.map((h, j) => `<th${j && j < 4 ? ' class="n"' : ''}>${esc(h)}</th>`).join('')}</tr></thead><tbody>${E.map(e =>
      `<tr><td><span class="sw" style="background:${COLOR[e.id]}"></span>${esc(e.nombre)}</td><td class="n">${sc[e.id]}</td><td class="n">${cert[e.id]}%</td><td class="n">${n ? n[e.id] : '—'}</td><td>${esc(lect(cert[e.id]))}</td></tr>`).join('')}</tbody></table>`;
    $('#anal').innerHTML = `<div class="an"><div class="scat"><h4>${esc(t.a_mapa)}</h4>${g}<p class="meta">${esc(t.a_mapa_nota)}</p></div>
      <div><h4>${esc(t.a_tens)}</h4><div class="tens">${tensH}</div><div style="margin-top:16px">${dist}</div></div>
      <div>${sep}</div><div><h4>${esc(t.a_tabla)}</h4>${tabla}</div></div>`;
  }

  // ------------------------------------------------------------ tarjeta 1080 × 1920 (canvas, se arma en el navegador)
  function cargarImg(u) {
    return new Promise(res => { if (!u) return res(null); const im = new Image(); im.crossOrigin = 'anonymous'; im.onload = () => res(im); im.onerror = () => res(null); im.src = u });
  }
  function rrect(x, X, Y, w, h, r) { x.beginPath(); if (x.roundRect) x.roundRect(X, Y, w, h, r); else x.rect(X, Y, w, h) }
  async function tarjeta(sinFoto) {
    const cv = $('#tarjeta'), x = cv.getContext('2d'), t = T(), sc = S.scores, cert = S.cert, rk = S.rk, E = EJES();
    const light = document.documentElement.dataset.theme === 'light';
    const bg = light ? '#f2f4f7' : '#111316', s1 = light ? '#ffffff' : '#1a1d22', s3 = light ? '#e6e9ee' : '#2a2f37', txt = light ? '#16191d' : '#eceef1', mut = light ? '#4f5866' : '#a4abb6', sig = light ? '#2563eb' : '#4f8ff7';
    try { await document.fonts.ready } catch (e) { }
    const top = rk.figs[0], img = sinFoto || !top ? null : await cargarImg(await foto(top.f.nombre));
    if (S.rk !== rk) return; // cambió el resultado mientras cargaba
    const W = 1080, H = 1920, F = (w, s, f) => `${w} ${s}px ${f || '"Plus Jakarta Sans", sans-serif'}`, HEAD = '"Space Grotesk", sans-serif', MONO = '"JetBrains Mono", monospace';
    const caja = (Y, h) => { rrect(x, 60, Y, W - 120, h, 28); x.fillStyle = s1; x.fill() };
    const corta = (s, w) => { while (x.measureText(s).width > w && s.length > 4) s = s.slice(0, -2) + '…'; return s };
    x.clearRect(0, 0, W, H); x.fillStyle = bg; x.fillRect(0, 0, W, H);
    const gr = x.createRadialGradient(W, 0, 50, W, 0, 1000); gr.addColorStop(0, light ? 'rgba(37,99,235,.16)' : 'rgba(79,143,247,.2)'); gr.addColorStop(1, 'rgba(0,0,0,0)');
    x.fillStyle = gr; x.fillRect(0, 0, W, H);
    // encabezado
    x.fillStyle = sig; x.beginPath(); x.moveTo(92, 84); x.lineTo(104, 128); x.lineTo(80, 128); x.closePath(); x.fill();
    x.fillStyle = txt; x.font = F(800, 42, HEAD); x.textAlign = 'left'; x.fillText(t.titulo, 124, 124);
    x.fillStyle = mut; x.font = F(600, 26, MONO); x.textAlign = 'right'; x.fillText(nombreVer(S.ver).toUpperCase(), W - 80, 122); x.textAlign = 'left';
    // afinidad principal
    caja(180, 300);
    x.fillStyle = mut; x.font = F(600, 24, MONO); x.fillText(t.card_af, 100, 240);
    x.fillStyle = txt; let fs = 68; do { x.font = F(800, fs, HEAD); fs -= 4 } while (x.measureText(ideoNom(rk.ideo[0].i)).width > 640 && fs > 40); x.fillText(corta(ideoNom(rk.ideo[0].i), 640), 100, 326);
    x.fillStyle = mut; x.font = F(400, 28); wrap(x, ideoDesc(rk.ideo[0].i), 100, 384, 640, 38, 2);
    const arc = (cx, cy, r, p, w) => { x.lineWidth = w; x.lineCap = 'round'; x.strokeStyle = s3; x.beginPath(); x.arc(cx, cy, r, 0, 2 * Math.PI); x.stroke(); x.strokeStyle = sig; x.beginPath(); x.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + 2 * Math.PI * p / 100); x.stroke() };
    arc(900, 330, 90, rk.ideo[0].af, 18); x.fillStyle = txt; x.textAlign = 'center'; x.font = F(800, 50, HEAD); x.fillText(rk.ideo[0].af + '%', 900, 348); x.textAlign = 'left';
    // dirigente
    if (top) {
      caja(510, 220);
      x.save(); x.beginPath(); x.arc(170, 620, 80, 0, 2 * Math.PI); x.closePath(); x.fillStyle = s3; x.fill(); x.clip();
      if (img) { const r = Math.max(160 / img.width, 160 / img.height), w = img.width * r, h = img.height * r; x.drawImage(img, 170 - w / 2, 540 - Math.max(0, (h - 160) * .1), w, h) }
      else { x.fillStyle = mut; x.font = F(800, 56, HEAD); x.textAlign = 'center'; x.fillText(iniciales(top.f.nombre), 170, 640); x.textAlign = 'left' }
      x.restore();
      x.fillStyle = mut; x.font = F(600, 24, MONO); x.fillText(t.card_dir, 290, 585);
      x.fillStyle = txt; x.font = F(800, 50, HEAD); x.fillText(corta(top.f.nombre, 520), 290, 645);
      x.fillStyle = mut; x.font = F(400, 26); x.fillText(corta(top.f.espacio || top.f.cargo || '', 520), 290, 690);
      x.fillStyle = sig; x.font = F(700, 54, MONO); x.textAlign = 'right'; x.fillText(top.af + '%', W - 100, 650); x.textAlign = 'left';
    }
    // 12 ejes
    caja(760, 820);
    x.fillStyle = mut; x.font = F(600, 24, MONO); x.fillText(t.card_ejes, 100, 820);
    E.forEach((e, j) => {
      const y = 878 + j * 56, s = sc[e.id], c = COLOR[e.id], X0 = 440, Wt = 380;
      x.fillStyle = c; x.beginPath(); x.arc(108, y - 9, 9, 0, 2 * Math.PI); x.fill();
      x.fillStyle = txt; x.font = F(600, 27); x.fillText(corta(e.nombre, 290), 132, y);
      rrect(x, X0, y - 17, Wt, 14, 7); x.fillStyle = s3; x.fill();
      x.globalAlpha = .85; rrect(x, X0 + Wt * Math.min(s, 50) / 100, y - 17, Math.max(4, Wt * Math.abs(s - 50) / 100), 14, 7); x.fillStyle = c; x.fill(); x.globalAlpha = 1;
      x.beginPath(); x.arc(X0 + Wt * s / 100, y - 10, 12, 0, 2 * Math.PI); x.fillStyle = c; x.fill(); x.lineWidth = 5; x.strokeStyle = s1; x.stroke();
      x.fillStyle = mut; x.font = F(600, 21, MONO); x.textAlign = 'right';
      x.fillText(corta(lectura(e, s), 170), W - 90, y); x.textAlign = 'left';
    });
    x.fillStyle = mut; x.font = F(400, 21, MONO); x.fillText(`${t.certeza} ${media(cert)}%`, 100, 1555);
    // también cerca
    caja(1610, 170);
    x.fillStyle = mut; x.font = F(600, 24, MONO); x.fillText(t.card_otros, 100, 1665);
    x.fillStyle = txt; x.font = F(600, 27);
    const otros = [...rk.figs.slice(1, 3).map(o => `${o.f.nombre} ${o.af}%`), ...rk.ideo.slice(1, 3).map(o => `${ideoNom(o.i)} ${o.af}%`)];
    otros.forEach((o, j) => { x.fillText(corta(o, 420), 100 + (j % 2) * 460, 1715 + Math.floor(j / 2) * 44) });
    x.fillStyle = mut; x.font = F(500, 26, MONO); x.textAlign = 'center';
    x.fillText(`${t.card_cta} ${location.host || 'brujula'}`, W / 2, 1852); x.textAlign = 'left';
  }
  function wrap(x, s, X, Y, w, lh, max) {
    let l = '', n = 0;
    for (const p of s.split(' ')) { const tst = l ? l + ' ' + p : p; if (x.measureText(tst).width > w && l) { x.fillText(l, X, Y + n * lh); n++; l = p; if (n >= max) return } else l = tst }
    if (l && n < max) x.fillText(l, X, Y + n * lh);
  }
  function descargar() {
    const go = () => $('#tarjeta').toBlob(b => {
      if (!b) return;
      const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = 'brujula-' + S.ver + '.png'; document.body.appendChild(a); a.click();
      setTimeout(() => { URL.revokeObjectURL(a.href); a.remove() }, 1000);
    }, 'image/png');
    try { go() } catch (e) { tarjeta(true).then(() => { try { go() } catch (e2) { } }) } // si la foto "ensucia" el canvas, se rehace sin foto
  }

  // ------------------------------------------------------------ secciones: 12 ejes, mapa, mi resultado, cara a cara, glosario
  function guardado() { try { const r = JSON.parse(localStorage.getItem('brujula_res') || 'null'); return r && r.sc ? r : null } catch (e) { return null } }
  const verDef = () => S.ver || (guardado() || {}).ver || (S.lang === 'pt' ? 'br' : 'ar');
  function selVer(sel, fn) {
    const el = $(sel), v = el.value || verDef();
    el.innerHTML = Object.entries(S.ejes.versiones).filter(([id, x]) => x.activa && (id !== 'general' || id === v)).map(([id]) => `<option value="${id}"${id === v ? ' selected' : ''}>${esc(nombreVer(id))}</option>`).join('');
    el.onchange = fn;
    return el.value;
  }
  function guia(foco) {
    const ver = selVer('#ej-ver', () => guia()), figs = figuras(ver), r = guardado(), yo = r && r.sc;
    $('#ejes-guia').innerHTML = S.ejes.ejes.map(e0 => {
      const e = eje(e0), ord = figs.slice().sort((a, b) => a.pos[e.id] - b.pos[e.id]);
      const ex = arr => arr.map(f => esc(apellido(f.nombre))).join(', ');
      return `<div class="ejec" id="eje-${e.id}" style="border-top:3px solid ${COLOR[e.id]}"><div class="h">${icb(e.id)}<div><h3>${esc(e.nombre)}</h3><div class="k">${esc(e.a)} ↔ ${esc(e.b)}</div></div></div>
        <div class="polos"><div><b>${esc(e.a)}</b>${esc(e0.a_desc || '')}</div><div><b>${esc(e.b)}</b>${esc(e0.b_desc || '')}</div></div>
        <div class="strip" style="background:linear-gradient(90deg,var(--s3),${COLOR[e.id]}55 50%,var(--s3))">${figs.map(f => `<i style="left:${f.pos[e.id]}%" title="${esc(f.nombre)} · ${f.pos[e.id]}"></i>`).join('')}${yo ? `<i class="yo" style="left:${yo[e.id]}%" title="${esc(T().vos)} · ${yo[e.id]}"></i>` : ''}</div>
        <div class="ext"><div>${ex(ord.slice(0, 3))}</div><div>${ex(ord.slice(-3).reverse())}</div></div></div>`;
    }).join('');
    if (foco) { const el = $('#eje-' + foco); if (el) setTimeout(() => el.scrollIntoView({ block: 'start' }), 30) }
  }
  function mapaPagina() {
    const ver = selVer('#mp-ver', mapaPagina), E = EJES(), r = guardado();
    ['#mp-x', '#mp-y'].forEach((sel, i) => {
      const el = $(sel), v = el.value || (i ? 'pro' : 'pla');
      el.innerHTML = E.map(e => `<option value="${e.id}"${e.id === v ? ' selected' : ''}>${esc(e.nombre)} (${esc(e.a)} ↔ ${esc(e.b)})</option>`).join('');
      el.onchange = mapaPagina;
    });
    const sc = r && r.sc, cert = r && r.cert;
    const rk = figuras(ver, $('#mp-hist').checked).concat($('#mp-int').checked ? figurasInt(ver).filter(f => $('#mp-hist').checked || !f.hist) : []).map(f => ({ f, af: sc ? afinidad(sc, f.pos, cert) : null })).sort((a, b) => (b.af || 0) - (a.af || 0));
    $('#mp-hist').onchange = $('#mp-int').onchange = mapaPagina;
    svgMapa('#mapa-g', '#mapa-g-info', rk, $('#mp-x').value, $('#mp-y').value, sc, new Set(sc ? rk.slice(0, 5).map(x => x.f.nombre) : rk.filter(x => x.f.nivel === 1).map(x => x.f.nombre)));
  }
  // Mapa de dos ejes cualesquiera: puntos = dirigentes, "vos" si hay resultado.
  function svgMapa(sel, info, rk, xk, yk, sc, top) {
    const E = EJES(), ex = E.find(e => e.id === xk), ey = E.find(e => e.id === yk);
    const W = 420, H = 360, P = 30, X = v => P + (W - 2 * P) * v / 100, Yv = v => P + (H - 2 * P) * (1 - v / 100), U = s => esc(s.toUpperCase());
    let g = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(ex.nombre)} × ${esc(ey.nombre)}">`;
    for (let t = 0; t <= 100; t += 25) g += `<line class="gl" x1="${X(t)}" x2="${X(t)}" y1="${P}" y2="${H - P}"/><line class="gl" x1="${P}" x2="${W - P}" y1="${Yv(t)}" y2="${Yv(t)}"/>`;
    g += `<line class="ax" x1="${X(50)}" x2="${X(50)}" y1="${P}" y2="${H - P}"/><line class="ax" x1="${P}" x2="${W - P}" y1="${Yv(50)}" y2="${Yv(50)}"/>`;
    g += `<text class="q" x="${X(50)}" y="${P - 10}" text-anchor="middle">▲ ${U(ey.b)}</text><text class="q" x="${X(50)}" y="${H - 8}" text-anchor="middle">▼ ${U(ey.a)}</text>`;
    g += `<text class="q" x="${P + 3}" y="${Yv(50) - 6}">◀ ${U(ex.a)}</text><text class="q" x="${W - P - 3}" y="${Yv(50) - 6}" text-anchor="end">${U(ex.b)} ▶</text>`;
    rk.forEach(({ f, af }) => {
      const tp = top.has(f.nombre), cx = X(f.pos[xk]), cy = Yv(f.pos[yk]);
      g += `<g class="pt${tp ? ' top' : ''}${f.hist ? ' h' : ''}${f.int ? ' i' : ''}"><title>${esc(f.nombre)}${af != null ? ' · ' + af + '%' : ''}${f.cargo ? ' · ' + esc(f.cargo) : ''}</title><circle cx="${cx}" cy="${cy}" r="${tp ? 5 : 3.5}"/>${tp ? `<text x="${cx + 7}" y="${cy + 3}">${esc(apellido(f.nombre))}</text>` : ''}</g>`;
    });
    if (sc) {
      const yo = { es: 'VOS', pt: 'VOCÊ', en: 'YOU' }[S.lang];
      g += `<g class="yo"><circle cx="${X(sc[xk])}" cy="${Yv(sc[yk])}" r="8"/><text x="${X(sc[xk]) + 11}" y="${Yv(sc[yk]) - 8}">${yo}</text></g>`;
    }
    $(sel).innerHTML = g + '</svg>';
    $(sel).onclick = ev => { const p = ev.target.closest('.pt'); if (p) $(info).textContent = p.querySelector('title').textContent };
  }
  function cara(preB) {
    const ver = selVer('#cc-ver', () => { $('#cc-a').value = ''; $('#cc-b').value = ''; cara() }), figs = figuras(ver, true).concat(figurasInt(ver)), r = guardado(), t = T();
    if (!figs.length) { $('#cara-res').innerHTML = ''; return }
    const ok = preB && figs.some(f => f.nombre === preB);
    const ops = (sel, def, conVos, forzar) => {
      const el = $(sel), v = forzar || el.value || def;
      el.innerHTML = (conVos && r ? `<option value="__vos">${esc(t.vos)}</option>` : '') + [figs.filter(f => !f.hist && !f.int), figs.filter(f => f.hist && !f.int), figs.filter(f => f.int)].map((l, j) => l.length ? `<optgroup label="${esc([t.act_grp, t.hist_grp, t.int_grp][j])}">` + l.map(f => `<option${f.nombre === v ? ' selected' : ''}>${esc(f.nombre)}</option>`).join('') + '</optgroup>' : '').join('');
      if (v === '__vos' && r) el.value = '__vos';
      el.onchange = () => cara();
      return el.value;
    };
    const otra = figs.find(f => f.nombre !== preB).nombre;
    const va = ops('#cc-a', r ? '__vos' : figs[0].nombre, true, ok ? (r ? '__vos' : otra) : null);
    const vb = ops('#cc-b', figs[r ? 0 : 1].nombre, false, ok ? preB : null);
    const get = v => v === '__vos' ? { nombre: t.vos, pos: r.sc, cert: r.cert, vos: true } : figs.find(f => f.nombre === v);
    const A = get(va), B = get(vb), E = EJES();
    const filas = E.map(e => ({ e, a: Math.round(A.pos[e.id]), b: Math.round(B.pos[e.id]), d: Math.round(Math.abs(A.pos[e.id] - B.pos[e.id])) }));
    const af = afinidad(A.pos, B.pos, A.cert), ord = filas.slice().sort((x, y) => x.d - y.d), n = x => x.map(f => esc(f.e.nombre)).join(', ');
    const cab = (P, col) => `<div class="p">${P.vos ? `<span class="av md" style="background:var(--sig3);color:var(--sig)">★</span>` : avatar(P, 'md')}<div><b style="color:${col}">${esc(P.nombre)}</b><small>${esc(P.espacio || P.cargo || '')}</small></div></div>`;
    $('#cara-res').innerHTML = `<div class="ccab">${cab(A, 'var(--sig)')}${ring(af, 'sm')}${cab(B, 'var(--a)')}</div>
      <div class="resumen"><div><b>${af}%</b>${esc(t.afin)}</div><div>${esc(t.coinciden)}: ${n(ord.slice(0, 3))}</div><div>${esc(t.chocan)}: ${n(ord.slice(-3).reverse())}</div></div>` +
      filas.map(({ e, a, b, d }) => `<div class="fila"><div>${esc(e.nombre)}<small>${esc(e.a)} ↔ ${esc(e.b)}</small></div>
        <div class="tr"><span class="seg" style="left:${Math.min(a, b)}%;width:${d}%"></span><span class="p b" style="left:${b}%" title="${esc(B.nombre)} ${b}"></span><span class="p a" style="left:${a}%" title="${esc(A.nombre)} ${a}"></span></div>
        <div class="d">${d}</div></div>`).join('');
    fotos($('#cara-res'));
  }
  function glosario() {
    const g = (GLOS[S.lang] || []).slice().sort((a, b) => a[1].localeCompare(b[1], S.lang));
    $('#glos').innerHTML = g.map(([, term, def]) => `<div><b>${esc(term)}</b>${esc(def)}</div>`).join('');
  }
  const RUTAS = { ejes: ['s-ejes', guia], mapa: ['s-mapa', mapaPagina], cara: ['s-cara', cara], glosario: ['s-glos', glosario], privacidad: ['s-priv', privacidad] };
  function nav(r) { $$('.nav a').forEach(a => a.classList.toggle('on', a.dataset.r === r)) }
  function ruta() {
    const h = location.hash;
    if (h.startsWith('#r=')) return;
    const [r, arg] = h.replace(/^#\/?/, '').split('/');
    if (RUTAS[r]) { show(RUTAS[r][0]); RUTAS[r][1](arg ? decodeURIComponent(arg) : undefined); nav(r); return }
    if (r === 'mimapa') {
      const g = guardado();
      if (g) { S.ver = g.ver; S.scores = g.sc; S.cert = g.cert; S.scores2 = g.sc2 || null; S.cert2 = g.cert2 || null; S.nresp = g.n || null; S.dist = g.dist || null; resultado(null, false); nav('mimapa') } else { show('s-vacio'); nav('mimapa') }
      return;
    }
    nav('quiz');
    if (!$('#s-preg').classList.contains('on') && !$('#s-demo').classList.contains('on')) show('s-inicio');
  }
  function tema(t) {
    document.documentElement.dataset.theme = t;
    try { localStorage.setItem('brujula_tema', t) } catch (e) { }
    if ($('#s-res').classList.contains('on') && S.rk) tarjeta();
  }

  // ------------------------------------------------------------ eventos
  function eventos() {
    $('#q-ops').onclick = ev => { const b = ev.target.closest('.op'); if (b) responder(+b.dataset.v) };
    $('#q-back').onclick = () => { if (S.i > 0) { S.i--; pregunta() } };
    $('#q-next').onclick = siguiente;
    $('#q-rev').onclick = revision;
    $('#q-reset').onclick = () => {
      const b = $('#q-reset');
      if (!b.dataset.c) { b.dataset.c = '1'; b.textContent = T().seguro; return }
      S.ans.fill(null); S.i = 0; S.t0 = Date.now(); pregunta();
    };
    $('#q-help').onclick = () => { const a = $('#q-ayuda'); a.hidden = !a.hidden; $('#q-help').classList.toggle('on', !a.hidden) };
    $('#rev').onclick = ev => { const b = ev.target.closest('button'); if (b) { S.i = +b.dataset.j; $('#revision').hidden = true; pregunta() } };
    $('#rev-fin').onclick = terminar;
    $('#modos').onclick = ev => { const b = ev.target.closest('[data-m]'); if (b && S.ver) empezar(S.ver, b.dataset.m) };
    $('#versiones').onclick = ev => {
      const b = ev.target.closest('.ver'); if (!b || b.disabled) return;
      S.ver = b.dataset.v;
      const pref = S.ejes.versiones[S.ver].lang || 'es';
      if (!S.langElegido && pref !== S.lang) setLang(pref, false); else versiones();
    };
    $('#cta1').onclick = () => $('#elegir').scrollIntoView({ behavior: 'smooth' });
    $('#ejes-tog').onclick = ev => {
      const b = ev.target.closest('button'); if (!b) return;
      $$('#ejes-tog button').forEach(x => x.classList.toggle('on', x === b));
      $('#ejes').hidden = b.dataset.v !== 'barras'; $('#radar').hidden = b.dataset.v !== 'radar';
    };
    $('#toc').onclick = ev => { const a = ev.target.closest('a'); if (!a) return; ev.preventDefault(); $(a.getAttribute('href')).scrollIntoView({ behavior: 'smooth' }) };
    if ('IntersectionObserver' in window) {
      const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) $$('#toc a').forEach(a => a.classList.toggle('on', a.getAttribute('href') === '#' + e.target.id)) }), { rootMargin: '-30% 0px -60% 0px' });
      $$('#s-res .sec').forEach(s => io.observe(s));
    }
    $('.lang').onclick = ev => { const b = ev.target.closest('button'); if (b) setLang(b.dataset.l, true) };
    document.addEventListener('keydown', ev => {
      if (!$('#s-preg').classList.contains('on') || !$('#revision').hidden) return;
      const n = +ev.key; if (n >= 1 && n <= 5) responder(S.ejes.respuestas[n - 1].v);
      if ((ev.key === 'Backspace' || ev.key === 'ArrowLeft') && S.i > 0) { S.i--; pregunta() }
      if (ev.key === 'ArrowRight') siguiente();
    });
    // glosario: tocar un término muestra su definición; modales
    document.addEventListener('click', ev => {
      const g = ev.target.closest('.gt'), pop = $('#pop');
      if (g) {
        const [term, def] = g.dataset.d.split('|'), r = g.getBoundingClientRect(), m = $('main').getBoundingClientRect();
        pop.innerHTML = `<b>${esc(term)}</b>${esc(def)}`; pop.hidden = false;
        pop.style.left = Math.max(8, Math.min(r.left - m.left, m.width - 310)) + 'px'; pop.style.top = (r.bottom - m.top + 8) + 'px';
      } else if (!ev.target.closest('#pop')) pop.hidden = true;
      const o = ev.target.closest('[data-open]'); if (o) { ev.preventDefault(); $('#' + o.dataset.open).hidden = false }
      if (ev.target.matches('[data-close]') || ev.target.classList.contains('modal')) $$('.modal').forEach(m => m.hidden = true);
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
  }
  function desdeHash() {
    const m = location.hash.match(/^#r=([a-z]+)-(es|pt|en)((?:-\d{1,3}){24})(?:-x((?:-\d{1,3})+))?$/);
    if (!m || !S.ejes.versiones[m[1]] || !S.ejes.versiones[m[1]].activa) return false;
    const v = m[3].slice(1).split('-').map(Number), ids = IDS(), cl = x => Math.max(0, Math.min(100, x));
    S.ver = m[1]; S.scores = {}; S.cert = {}; S.nresp = null; S.dist = null; S.scores2 = null; S.cert2 = null;
    ids.forEach((k, i) => { S.scores[k] = cl(v[i]); S.cert[k] = cl(v[i + ids.length]) });
    const ids2 = IDS2(), v2 = m[4] ? m[4].slice(1).split('-').map(Number) : [];
    if (v2.length === 2 * ids2.length) { S.scores2 = {}; S.cert2 = {}; ids2.forEach((k, i) => { S.scores2[k] = cl(v2[i]); S.cert2[k] = cl(v2[i + ids2.length]) }) }
    if (!S.langElegido) setLang(m[2], false);
    resultado(null, true);
    return true;
  }

  try { const t = localStorage.getItem('brujula_tema'); if (t) document.documentElement.dataset.theme = t } catch (e) { }
  async function main() {
    const get = f => fetch(CFG.datos + f).then(r => r.json());
    let ideo;
    [S.ejes, S.preg, S.fig, ideo] = await Promise.all([get('ejes.json'), get('preguntas.json'), get('figuras.json'), get('ideologias.json').catch(() => ({ ideologias: [] }))]);
    S.ideo = ideo.ideologias || [];
    Object.values(S.fig).filter(Array.isArray).flat().forEach(f => { if (f.wiki) WIKI[f.nombre] = f.wiki });
    $('#foot-v').textContent = S.fig.fecha || '';
    S.lang = idiomaInicial();
    S.ver = verInicial();
    eventos();
    setLang(S.lang, false);
    $('#tema').onclick = () => tema(document.documentElement.dataset.theme === 'light' ? 'dark' : 'light');
    window.addEventListener('hashchange', () => { if (!desdeHash()) ruta() });
    if (!desdeHash()) ruta();
  }
  main();
})();
