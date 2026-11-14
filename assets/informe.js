/* Resumen accionable para los tableros locales (Boca, Santa Cruz, General Roca, San Isidro).
   Cada tablero llama a Informe.init({...}) con un "build(nombre)" que devuelve la figura en el formato común
   (n, share, last7, prev7, tone, emotions, intenciones, balance, narrativas, co, cloud, frases, headlines),
   sus pares y acciones o secciones propias. El motor:
     - agrega la pestaña "Resumen accionable" al final de la barra y su sección,
     - arma el informe (resumen "X tiene que Y porque… O, P y Q", acciones con su métrica, análisis, conclusión),
     - lo descarga como PDF con la impresión del navegador,
     - deja un prompt para videos que no se ve: Alt+Shift+P o el "·" al pie del informe (window.Informe.prompt()). */
(function () {
  const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const fmt = n => n == null ? '—' : Number(n).toLocaleString('es-AR');
  const pct = (x, d = 0) => x == null || isNaN(x) ? '—' : Number(x).toLocaleString('es-AR', { maximumFractionDigits: d }) + '%';
  const med = a => { const b = a.filter(x => x != null && !isNaN(x)).sort((x, y) => x - y); if (!b.length) return null; const m = b.length >> 1; return b.length % 2 ? b[m] : (b[m - 1] + b[m]) / 2 };
  const list = a => a.length <= 1 ? (a[0] || '') : a.slice(0, -1).join(', ') + ' y ' + a[a.length - 1];
  const cap = s => s ? s[0].toUpperCase() + s.slice(1) : s;
  const EMO = { ira: 'enojo', asco: 'rechazo', miedo: 'miedo', tristeza: 'tristeza', alegria: 'alegría', sorpresa: 'sorpresa' };
  const S = { cfg: null, sel: null, prompt: '' };

  const CSS = `
.inf-bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:14px}
.inf-bar select{background:var(--s2,var(--panel2,#1a1e27));border:1px solid var(--line2,#323848);border-radius:8px;padding:9px 10px;color:var(--txt);font:inherit}
.inf-bar button{border:1px solid #3987e5;background:#3987e5;color:#fff;border-radius:999px;padding:8px 16px;font:inherit;font-size:13px;cursor:pointer}
.inf-doc{background:var(--s1,var(--panel,#13161d));border:1px solid var(--line,#272c38);border-top:3px solid #3987e5;border-radius:8px;padding:26px 30px;max-width:900px;margin:0 auto 30px;font-size:14.5px;line-height:1.6;color:var(--txt)}
.inf-k{font:600 11px var(--mono,monospace);letter-spacing:1.4px;color:#3987e5;text-transform:uppercase}.inf-doc h2{margin:2px 0;font-size:28px;letter-spacing:-.4px}.inf-m{color:var(--dim);font-size:12.5px}
.inf-sum{margin:18px 0 6px;background:var(--s2,var(--panel2,#1a1e27));border-left:3px solid #3987e5;border-radius:4px;padding:14px 18px;font-size:15.5px}.inf-sum p{margin:0}
.inf-t{font:600 11px var(--mono,monospace);letter-spacing:1.4px;color:var(--dim);text-transform:uppercase;margin:24px 0 8px;display:flex;gap:10px;align-items:center}.inf-t::after{content:"";flex:1;height:1px;background:var(--line,#272c38)}
.inf-acc{margin:0;padding-left:22px}.inf-acc li{margin:8px 0;color:var(--muted)}.inf-acc b{color:var(--txt)}.inf-kpi{display:block;font-size:12.5px;color:var(--dim)}
.inf-s h4{margin:14px 0 2px;font-size:14px}.inf-s p{margin:4px 0;color:var(--muted)}.inf-s b{color:var(--txt)}.inf-s ul{margin:4px 0;padding-left:20px;color:var(--muted);font-size:13.5px}.inf-s small{color:var(--dim)}
.inf-doc>p{color:var(--muted)}.inf-doc>p b{color:var(--txt)}.inf-doc a{color:#7fb3f0}
.inf-f{margin-top:24px;border-top:1px solid var(--line,#272c38);padding-top:10px;color:var(--dim);font-size:11.5px}.inf-x{cursor:default;padding:0 4px}
#inf-modal{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:80;display:grid;place-items:center;padding:16px}
.inf-mb{background:var(--s1,var(--panel,#13161d));border:1px solid var(--line2,#323848);border-radius:8px;width:min(820px,100%);padding:14px 16px;color:var(--txt)}
.inf-mh{display:flex;gap:10px;align-items:center;margin-bottom:8px}.inf-mh span{color:#3fbf6f;font-size:12px}.inf-mh button{margin-left:auto;background:none;border:0;color:var(--dim);font-size:20px;cursor:pointer}
#inf-mt{width:100%;height:60vh;background:#0b0d12;color:var(--txt);border:1px solid var(--line,#272c38);border-radius:6px;padding:10px;font:12.5px/1.5 var(--mono,monospace)}
@media(max-width:760px){.inf-doc{padding:18px 16px}.inf-doc h2{font-size:23px}}
@media print{
  @page{margin:16mm 14mm}
  html,body{background:#fff!important;color:#111!important}
  body>*:not(main),header,nav,footer,.inf-bar,#inf-modal,.tab:not(#t-resumen),#warn{display:none!important}
  main>*:not(#t-resumen){display:none!important}#t-resumen{display:block!important}main{padding:0!important;max-width:none!important;margin:0!important}
  .inf-doc{background:#fff;border:0;border-top:4px solid #1f5fae;padding:0;max-width:none;color:#111;font-size:11.5pt;margin:0}
  .inf-sum{background:#eef3fa;border-left-color:#1f5fae;color:#111}.inf-k{color:#1f5fae}
  .inf-doc b,.inf-doc>p b,.inf-acc b,.inf-s b,.inf-s h4,.inf-doc h2{color:#111}.inf-acc li,.inf-s p,.inf-s ul,.inf-doc>p{color:#333}.inf-m,.inf-kpi,.inf-f,.inf-s small,.inf-t{color:#666}
  .inf-t::after{background:#ccc}.inf-f{border-top-color:#ccc}.inf-x{visibility:hidden}.inf-doc a{color:#1f5fae}.inf-acc li,.inf-s{break-inside:avoid}
}`;

  /* ---------------- diagnóstico genérico sobre una figura ---------------- */
  function diagnose(b) {
    const a = b.a || {}, pares = (b.pares || []).filter(p => p && p.n >= 3), acts = [], facts = {};
    const add = (k, score, titulo, porque, kpi, video) => acts.push({ k, score: Math.round(Math.max(0, Math.min(100, score))), titulo, porque, kpi, video });
    const unidad = b.unidad || 'menciones';
    if (a.n) {
      const ms = med(pares.map(p => p.share)), d = a.prev7 ? Math.round(100 * (a.last7 - a.prev7) / a.prev7) : null;
      Object.assign(facts, { ms, d });
      if (ms != null && a.share < ms * 0.7) add('vis', 55 + 30 * (1 - a.share / Math.max(ms, .01)), 'ganar conversación propia',
        `tiene ${fmt(a.n)} ${unidad} (${pct(a.share, 1)} de la conversación del tablero), contra ${pct(ms, 1)} de la mediana de las demás figuras`, `subir su participación por encima de ${pct(ms, 1)}`, 'una idea propia, fuerte y repetible');
      if (d != null && d >= 30 && a.last7 >= 8 && a.prev7 >= 4) add('mom', 50 + Math.min(35, d / 4), 'aprovechar la suba de esta semana',
        `sus ${unidad} subieron ${d}% en 7 días (${fmt(a.last7)} contra ${fmt(a.prev7)})`, `sostener más de ${fmt(a.last7)} ${unidad} por semana`, 'reacción rápida al tema del momento, con postura clara');
      if (d != null && d <= -30 && a.prev7 >= 8) add('caida', 45 + Math.min(35, -d / 3), 'reactivar su presencia',
        `sus ${unidad} cayeron ${-d}% en 7 días (${fmt(a.last7)} contra ${fmt(a.prev7)})`, `volver a ${fmt(a.prev7)} ${unidad} por semana`, 'anuncio o propuesta que dé un motivo nuevo para nombrarlo');
      const t = a.tone || {}, neg = t.NEG, mneg = med(pares.map(p => p.tone && p.tone.NEG));
      const emo = a.emotions ? Object.entries(a.emotions).sort((x, y) => y[1] - x[1])[0] : null; facts.emo = emo;
      if (neg != null && neg >= 35 && a.n >= 10) add('tono', 40 + (neg - 35) * 1.2 + (mneg != null && neg > mneg ? 10 : 0), 'bajar el tono negativo',
        `${pct(neg)} de ${a.tone_base === 'comentarios' || a.tone_base === 'redes' ? 'los comentarios' : 'los textos'} sobre su figura son negativos${mneg != null ? ` (las demás figuras: ${pct(mneg)})` : ''}${emo && emo[1] > 30 && emo[0] !== 'alegria' ? ` y la emoción que más aparece es ${EMO[emo[0]] || emo[0]} (${pct(emo[1])})` : ''}`,
        `negatividad por debajo de ${pct(Math.max(20, neg - 10))}`, emo && emo[0] === 'ira' ? 'empatía con el enojo y una solución concreta, sin confrontar' : 'respuesta directa y cercana a la crítica más repetida');
      if (a.balance != null && a.balance <= -10 && a.intenciones) { const fc = (a.frases_critica || []).slice(0, 4).map(f => f[0]);
        add('bal', 45 + Math.min(35, -a.balance), 'convertir la crítica en apoyo',
          `en los comentarios la crítica le gana al apoyo por ${-a.balance} puntos (${pct(a.intenciones.critica)} critica, ${pct(a.intenciones.apoya)} apoya)${fc.length ? `; lo que más se repite en la crítica: ${fc.join(', ')}` : ''}`,
          'balance apoyo−crítica en positivo', 'tomar la crítica principal de frente y mostrar qué se hizo') }
      if (a.balance != null && a.balance >= 15) add('bal+', 30 + Math.min(25, a.balance / 2), 'capitalizar el apoyo que ya tiene',
        `en los comentarios el apoyo le gana a la crítica por ${a.balance} puntos`, 'más comentarios de apoyo por semana', 'agradecimiento y convocatoria a la comunidad que lo apoya');
      const nar = (a.narrativas || [])[0];
      if (nar && nar.pct >= 45) add('narr', 30 + (nar.pct - 45) * .8, 'ampliar su agenda',
        `${pct(nar.pct)} de lo que se dice sobre su figura gira alrededor de «${nar.n}»`, 'una segunda narrativa que supere el 20% de sus menciones', 'un tema propio distinto de «' + nar.n + '»');
      const co = (a.co || [])[0];
      if (co && co.n >= Math.max(5, a.n * 0.15) && (b.rivales || []).includes(co.a)) add('co', 35 + Math.min(25, 100 * co.n / a.n / 2), `marcar diferencia con ${co.a}`,
        `aparece junto a ${co.a} en ${fmt(co.n)} textos (${pct(100 * co.n / a.n)} de sus ${unidad})`, 'menciones propias sin el rival', 'contraste de propuestas, sin nombrar al rival');
    }
    (b.extra || []).forEach(x => add(x.k || 'x', x.score, x.titulo, x.porque, x.kpi, x.video));
    if (!acts.length) add('base', 30, 'sostener lo que funciona', 'no hay señales de alarma en la conversación', 'mantener tono y volumen actuales', 'contenido de gestión, cercano');
    acts.sort((x, y) => y.score - x.score);
    return { acts, facts };
  }
  // El objetivo sale de la acción con más peso, así el párrafo inicial es coherente con su dato
  const OBJ = [
    [['tono', 'bal'], { y: 'cambiar el clima de la conversación sobre su figura', why: 'hoy pesa más la crítica que el apoyo' }],
    [['reclamo'], { y: 'mostrar respuestas a lo que reclaman los vecinos', why: 'los reclamos marcan la agenda local' }],
    [['vis', 'caida'], { y: 'ganar visibilidad con una agenda propia', why: 'hoy tiene poca presencia frente a las demás figuras' }],
    [['tema'], { y: 'ponerse al frente de los temas que están creciendo', why: 'hay temas que crecen rápido y todavía no tienen una postura clara' }],
    [['narr', 'co'], { y: 'construir una identidad propia', why: 'la conversación lo ubica en un solo tema o al lado de otros' }],
    [['mom', 'bal+'], { y: 'convertir la atención y el apoyo en posicionamiento', why: 'tiene un buen momento que se puede aprovechar' }]];
  function objetivo(k, b) {
    if (b.objetivo) return b.objetivo;
    const hit = OBJ.find(([ks]) => ks.includes(k));
    return hit ? hit[1] : { y: 'consolidar y ampliar lo que ya le funciona', why: 'los indicadores no muestran alarmas' };
  }

  function informe(name) {
    const b = S.cfg.build(name) || {}, a = b.a || {}, dx = diagnose(b), top = dx.acts.slice(0, 3), [O] = top, ob = objetivo(O.k, b), f = dx.facts;
    const today = new Date().toLocaleDateString('es-AR', { day: 'numeric', month: 'long', year: 'numeric' });
    const resumen = `<b>${esc(name)} tiene que ${esc(ob.y)}.</b> Los datos lo muestran con claridad: ${esc(O.porque)}. ` +
      (top.length > 1 ? `Por eso las ${top.length === 2 ? 'dos' : 'tres'} acciones que más rinden ahora son <b>${esc(list(top.map(x => x.titulo)))}</b>: la primera ataca directamente ese punto; ` + top.slice(1).map(x => `${esc(x.titulo)}, porque ${esc(x.porque)}`).join('; y ') + '.' : '');
    const sec = [], u = b.unidad || 'menciones';
    if (a.n) {
      sec.push(['Conversación', `<p>En ${esc(b.ventana || 'el período medido')}, ${esc(name)} sumó <b>${fmt(a.n)} ${esc(u)}</b>${a.n_news != null ? ` (${fmt(a.n_news)} notas${a.n_comments ? ` y ${fmt(a.n_comments)} comentarios` : ''})` : ''}${a.share != null ? `, el ${pct(a.share, 1)} de la conversación del tablero` : ''}${f.ms != null ? `; la mediana de las demás figuras es ${pct(f.ms, 1)}` : ''}. ${f.d != null ? `En la última semana ${f.d >= 0 ? 'subió' : 'bajó'} ${Math.abs(f.d)}% (${fmt(a.last7)} contra ${fmt(a.prev7)}).` : ''}</p>`]);
      const t = a.tone || {}, em = Object.entries(a.emotions || {}).filter(e => e[1] > 0).sort((x, y) => y[1] - x[1]).slice(0, 3);
      if (t.NEG != null) sec.push(['Tono y emociones', `<p><b>${pct(t.NEG)} negativo</b>, ${pct(t.NEU)} neutro y ${pct(t.POS)} positivo${a.tone_news && a.tone_base !== 'todos' ? `; en las notas de prensa, ${pct(a.tone_news.NEG)} negativo y ${pct(a.tone_news.POS)} positivo` : ''}. ${em.length ? `Emociones que más aparecen: ${esc(list(em.map(([k, v]) => `${EMO[k] || k} (${pct(v)})`)))}.` : ''}${a.intenciones ? ` En los comentarios, ${pct(a.intenciones.apoya)} apoya, ${pct(a.intenciones.critica)} critica, ${pct(a.intenciones.quiere)} pide algo y ${pct(a.intenciones.espera)} espera algo.` : ''}</p>`]);
      const nar = (a.narrativas || []).slice(0, 4), co = (a.co || []).slice(0, 4), tm = (a.temas || []).slice(0, 4);
      if (nar.length || co.length || tm.length) sec.push(['Narrativas y compañía', `<p>${nar.length ? `Narrativas: ${esc(list(nar.map(n => `«${n.n}» (${pct(n.pct)})`)))}.` : ''} ${tm.length ? `Temas: ${esc(list(tm.map(x => `${x[0]} (${fmt(x[1])})`)))}.` : ''} ${co.length ? `Aparece junto a ${esc(list(co.map(c => `${c.a} (${fmt(c.n)})`)))}.` : ''}</p>${(a.cloud || []).length ? `<p>Palabras más asociadas: ${esc(a.cloud.slice(0, 12).map(w => w.w).join(', '))}.</p>` : ''}`]);
      if ((a.frases_apoya || []).length || (a.frases_critica || []).length) sec.push(['Qué dicen los comentarios', `<p>${(a.frases_apoya || []).length ? `Cuando apoyan: ${esc(a.frases_apoya.slice(0, 6).map(x => x[0]).join(', '))}.` : ''} ${(a.frases_critica || []).length ? `Cuando critican: ${esc(a.frases_critica.slice(0, 6).map(x => x[0]).join(', '))}.` : ''}</p>`]);
    } else sec.push(['Conversación', `<p>Todavía no hay menciones suficientes de ${esc(name)} en el período: el informe se completa con las próximas actualizaciones.</p>`]);
    (b.secciones || []).forEach(s => sec.push(s));
    const hl = (a.headlines || []).slice(0, 3);
    if (hl.length) sec.push(['Últimos titulares', `<ul>${hl.map(h => `<li>${h.u ? `<a href="${esc(h.u)}" target="_blank" rel="noopener">${esc(h.t)}</a>` : esc(h.t)} <small>${esc(h.o || '')}</small></li>`).join('')}</ul>`]);
    const concl = `<p>El diagnóstico es consistente: ${esc(ob.why)}. La prioridad para las próximas dos semanas es <b>${esc(O.titulo)}</b>${top.length > 1 ? `, apoyada en ${esc(list(top.slice(1).map(x => x.titulo)))}` : ''}. Si en ese plazo se alcanza la meta (${esc(O.kpi)}), la estrategia está funcionando y conviene profundizarla; si no, hay que revisar el mensaje antes que la frecuencia.</p>`;
    const html = `<article class="inf-doc">
      <div class="inf-k">Resumen accionable · ${esc(S.cfg.titulo)}</div><h2>${esc(name)}</h2><div class="inf-m">${esc([b.sub, today].filter(Boolean).join(' · '))}</div>
      <section class="inf-sum"><p>${resumen}</p></section>
      <h3 class="inf-t">Acciones recomendadas</h3><ol class="inf-acc">${top.map(x => `<li><b>${esc(cap(x.titulo))}.</b> ${esc(cap(x.porque))}. <span class="inf-kpi">Cómo se mide: ${esc(x.kpi)}.</span></li>`).join('')}</ol>
      <h3 class="inf-t">Análisis</h3>${sec.map(([t, h]) => `<div class="inf-s"><h4>${esc(t)}</h4>${h}</div>`).join('')}
      <h3 class="inf-t">Conclusión</h3>${concl}
      <footer class="inf-f">Fuentes: ${esc(list(S.cfg.fuentes || []))}. Tono y emociones estimados con modelos automáticos; los comentarios se miden solo en agregado. <span class="inf-x" id="inf-x" aria-hidden="true">·</span></footer>
    </article>`;
    return { html, b, a, top, ob, f };
  }

  function videoPrompt(r, name) {
    const { b, a, top, ob, f } = r;
    const words = (a.frases_apoya || []).slice(0, 8).map(x => x[0]).concat((a.cloud || []).filter(w => w.neg < 30).slice(0, 6).map(w => w.w)).filter((x, i, s) => s.indexOf(x) === i).slice(0, 10);
    const avoid = (a.cloud || []).filter(w => w.neg >= 50).slice(0, 8).map(w => w.w);
    return `Actuá como director creativo y guionista de campaña en Argentina. Con los datos de abajo, escribí 3 guiones de video corto para ${name}${b.rol ? `, ${b.rol.replace(/\s*\([^)]*\)/g, '').toLowerCase()}` : ''}.

OBJETIVO
${cap(ob.y)}. Motivo: ${ob.why}.

DATOS DEL TABLERO «${S.cfg.titulo}» (no inventes otros)
${a.n ? `- Conversación: ${a.n} ${b.unidad || 'menciones'}${a.share != null ? ` (${pct(a.share, 1)} del tablero)` : ''}${f.d ? `, ${f.d > 0 ? '+' : ''}${f.d}% en la última semana` : ''}.` : '- Conversación: todavía con poco volumen.'}
${a.tone && a.tone.NEG != null ? `- Tono: ${pct(a.tone.NEG)} negativo, ${pct(a.tone.POS)} positivo${f.emo ? `; emoción dominante: ${EMO[f.emo[0]] || f.emo[0]} (${pct(f.emo[1])})` : ''}.` : ''}
${a.intenciones ? `- Comentarios: ${pct(a.intenciones.apoya)} apoya, ${pct(a.intenciones.critica)} critica.` : ''}
${(a.narrativas || [])[0] ? `- Narrativa principal: «${a.narrativas[0].n}» (${pct(a.narrativas[0].pct)}).` : ''}
${(b.contexto || []).map(x => '- ' + x).join('\n')}

UN VIDEO POR ACCIÓN
${top.map((x, i) => `${i + 1}. ${cap(x.titulo)}. Por qué: ${x.porque}.${x.video ? ` Enfoque: ${x.video}.` : ''} Éxito si: ${x.kpi}.`).join('\n')}

FORMATO
- Vertical 9:16, 30 a 45 segundos, con subtítulos quemados (se mira sin sonido).
- Gancho en los primeros 3 segundos: una frase o imagen que nombre el problema, no a la persona.
- Estructura: gancho → problema con un dato real del tablero → propuesta o respuesta concreta → cierre con llamada a la acción.
- Público: ${b.publico || 'la comunidad que sigue este tablero'}.
${words.length ? `- Palabras que conviene usar (aparecen en el apoyo o en contextos no negativos): ${words.join(', ')}.` : ''}
${avoid.length ? `- Palabras a evitar (aparecen en contextos negativos): ${avoid.join(', ')}.` : ''}

PARA CADA GUION ENTREGÁ
Título interno, gancho, guion segundo a segundo (voz en off y texto en pantalla), indicaciones de imagen y plano, música sugerida, texto del posteo con hasta 3 hashtags y la métrica con la que se va a evaluar.

REGLAS
- Usá solo los datos de arriba; si necesitás uno que no está, marcalo como [DATO A CONFIRMAR].
- No muestres ni imites a otras personas, ni generes con IA la cara o la voz de personas reales. Si se usa IA en imágenes, va rotulada.
- No uses comentarios de usuarios con nombre ni datos personales.
- Español rioplatense, frases cortas, sin jerga técnica.`.replace(/\n{2,}(?=- |\d\. )/g, '\n').replace(/\n{3,}/g, '\n\n');
  }

  function showPrompt() {
    if (!S.prompt) return;
    let m = $('#inf-modal');
    if (!m) { m = document.createElement('div'); m.id = 'inf-modal'; m.innerHTML = `<div class="inf-mb"><div class="inf-mh"><b>Prompt para videos</b><span id="inf-ok"></span><button id="inf-c" aria-label="Cerrar">×</button></div><textarea id="inf-mt" readonly></textarea><div style="margin-top:8px;text-align:right"><button id="inf-cp" class="inf-cpb" style="border:1px solid #3987e5;background:#3987e5;color:#fff;border-radius:999px;padding:6px 14px;cursor:pointer">Copiar</button></div></div>`;
      document.body.appendChild(m); m.addEventListener('click', e => { if (e.target === m || e.target.id === 'inf-c') m.remove() }); $('#inf-cp').onclick = copy }
    $('#inf-mt').value = S.prompt; copy();
  }
  function copy() { try { navigator.clipboard.writeText(S.prompt).then(() => { const s = $('#inf-ok'); if (s) s.textContent = 'copiado al portapapeles' }, () => { }) } catch (e) { } }

  function draw() {
    const s = $('#inf-sel'), opts = S.cfg.opciones();
    if (!opts.length) { $('#inf-body').innerHTML = '<div class="empty">Cargando…</div>'; return }
    if (!s.options.length) {
      const g = [...new Set(opts.map(o => o.grupo || ''))];
      s.innerHTML = g.map(gr => { const o = opts.filter(x => (x.grupo || '') === gr).map(x => `<option>${esc(x.name)}</option>`).join(''); return gr ? `<optgroup label="${esc(gr)}">${o}</optgroup>` : o }).join('');
    }
    if (!S.sel || !opts.some(o => o.name === S.sel)) S.sel = S.cfg.def && opts.some(o => o.name === S.cfg.def) ? S.cfg.def : opts[0].name;
    s.value = S.sel;
    const r = informe(S.sel);
    $('#inf-body').innerHTML = r.html;
    S.prompt = videoPrompt(r, S.sel);
    $('#inf-x').onclick = showPrompt;
  }

  function init(cfg) {
    S.cfg = cfg;
    const st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
    const nav = $('#tabs'), main = $('main');
    if (!nav || !main) return;
    const btn = document.createElement('button'); btn.dataset.t = 'resumen'; btn.textContent = 'Resumen accionable'; nav.appendChild(btn);
    const sec = document.createElement('section'); sec.className = 'tab'; sec.id = 't-resumen';
    sec.innerHTML = `<div class="inf-bar"><select id="inf-sel" aria-label="Figura"></select><button id="inf-pdf">Descargar PDF</button></div><div id="inf-body"><div class="empty">Cargando…</div></div>`;
    main.appendChild(sec);
    const open = () => { $$('#tabs button').forEach(x => x.classList.toggle('on', x === btn)); $$('.tab').forEach(t => t.classList.toggle('on', t === sec)); draw(); try { history.replaceState(null, '', '#resumen') } catch (e) { } window.scrollTo({ top: 0 }) };
    btn.addEventListener('click', e => { e.stopImmediatePropagation(); open() }, true);
    $('#inf-sel').onchange = e => { S.sel = e.target.value; draw() };
    $('#inf-pdf').onclick = () => { const t = document.title; document.title = `Resumen accionable - ${S.sel}`; window.print(); setTimeout(() => document.title = t, 500) };
    document.addEventListener('keydown', e => { if (e.altKey && e.shiftKey && e.code === 'KeyP') { e.preventDefault(); if (!S.prompt) draw(); showPrompt() } if (e.key === 'Escape' && $('#inf-modal')) $('#inf-modal').remove() });
    if (location.hash === '#resumen') cfg.ready.then(open);
    cfg.ready.then(() => { if (sec.classList.contains('on')) draw() });
  }
  window.Informe = { init, prompt: () => S.prompt, pct, fmt, med, list };
})();
