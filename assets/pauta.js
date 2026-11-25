/* Pauta en Meta (Biblioteca de Anuncios) para los tableros del módulo dirigentes.
   Uso: <script src="../assets/pauta.js"></script><script>MetaPauta.init({data:'data/meta.json'})</script>
   Agrega la pestaña "Pauta en Meta" (antes de "Instagram" o "Fuentes y método") solo si el tablero tiene datos.
   Datos: dirigentes/<slug>/data/meta.json, que arma meta/collect.py: avisos políticos del dirigente y de su
   competencia en Argentina, con gasto, impresiones, regiones, edad, género y plataformas. */
(function () {
  const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const num = n => n == null || isNaN(n) ? '—' : Math.round(n).toLocaleString('es-AR');
  const big = n => n == null || isNaN(n) ? '—' : n >= 1e6 ? (n / 1e6).toLocaleString('es-AR', { maximumFractionDigits: 1 }) + ' M' : n >= 1e4 ? Math.round(n / 1e3).toLocaleString('es-AR') + ' mil' : num(n);
  const rng = r => !r ? '—' : r[0] === r[1] ? big(r[0]) : `${big(r[0])} a ${big(r[1])}`;
  const mid = r => r ? (r[0] + r[1]) / 2 : 0;
  const GEN = { male: 'Varones', female: 'Mujeres', unknown: 'Sin dato' };
  const CSS = `
.mp{color:var(--txt,#eef0f4)}.mp *{box-sizing:border-box}
.mp-g{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:14px}.mp-c4{grid-column:span 4}.mp-c6{grid-column:span 6}.mp-c12{grid-column:span 12}
@media(max-width:900px){.mp-c4,.mp-c6{grid-column:span 12}}
.mp-card{background:var(--s1,#13161d);border:1px solid var(--line,#272c38);padding:14px 16px;min-width:0}
.mp-card h3{margin:0 0 12px;font-size:14px;font-weight:600}.mp-card h3 small{font-weight:500;color:var(--dim,#717887);margin-left:6px}
.mp-k{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}@media(max-width:700px){.mp-k{grid-template-columns:repeat(2,minmax(0,1fr))}}
.mp-k div{border:1px solid var(--line,#272c38);background:var(--s2,#1a1e27);padding:10px 12px}.mp-k b{display:block;font:600 20px var(--mono,ui-monospace,monospace)}.mp-k span{font-size:11.5px;color:var(--dim,#717887)}
.mp-w{overflow-x:auto}.mp-t{width:100%;border-collapse:collapse;font-size:12.5px}.mp-t th{text-align:left;font-weight:500;color:var(--dim,#717887);border-bottom:1px solid var(--line,#272c38);padding:6px 8px}
.mp-t td{border-bottom:1px solid var(--line,#272c38);padding:7px 8px;color:var(--muted,#a6adbb)}.mp-t td.n,.mp-t th.n{text-align:right;font-family:var(--mono,ui-monospace,monospace);white-space:nowrap}.mp-t tr.me td{color:var(--txt,#eef0f4);background:var(--s2,#1a1e27)}
.mp-b .r{display:grid;grid-template-columns:130px 1fr 52px;gap:8px;align-items:center;font-size:12.5px;color:var(--muted,#a6adbb);margin:6px 0}
.mp-b .r i{display:block;height:9px;background:var(--foco,#3987e5)}.mp-b .r b{font:600 12px var(--mono,ui-monospace,monospace);text-align:right}
.mp-a{display:block;border:1px solid var(--line,#272c38);border-left:3px solid var(--foco,#3987e5);padding:8px 10px;margin:0 0 8px;background:var(--s2,#1a1e27);color:var(--txt,#eef0f4);font-size:12.5px}
.mp-a small{display:block;color:var(--dim,#717887);font-size:11px;margin-top:3px}.mp-e{color:var(--dim,#717887);font-size:12.5px;padding:6px 0}.mp-n{font-size:12px;color:var(--dim,#717887);margin-top:10px}`;
  const S = { D: null, drawn: false };

  function bars(obj, fmt = k => k) {
    const e = Object.entries(obj || {}).filter(([, v]) => v > 0);
    if (!e.length) return '<div class="mp-e">Sin datos.</div>';
    const mx = Math.max(...e.map(([, v]) => v));
    return '<div class="mp-b">' + e.map(([k, v]) => `<div class="r"><span>${esc(fmt(k))}</span><i style="width:${(100 * v / mx).toFixed(1)}%"></i><b>${v.toLocaleString('es-AR', { maximumFractionDigits: 1 })}%</b></div>`).join('') + '</div>';
  }

  function draw() {
    const D = S.D, sec = $('#t-pauta'), F = D.figuras || [];
    const me = F.find(f => f.foco) || F[0], A = me.ads || {};
    const days = D.ads_days || 90;
    const rows = [...F].sort((a, b) => mid((b.ads || {}).gasto) - mid((a.ads || {}).gasto) || ((b.ads || {}).n || 0) - ((a.ads || {}).n || 0));
    const rank = rows.indexOf(me) + 1;
    const err = D.estado === 'error' ? `<div class="mp-card mp-c12" style="border-color:#c98500">Meta no devolvió avisos en la última corrida (${esc(D.error || 'sin acceso')}).</div>` : '';
    sec.innerHTML = `<div class="mp"><div class="mp-g">${err}
      <div class="mp-card mp-c12"><h3>Pauta política de ${esc(me.name)} en Facebook e Instagram<small>Biblioteca de Anuncios de Meta · últimos ${days} días · actualizado ${esc((D.updated_at || '').replace('T', ' ').slice(0, 16))}</small></h3>
        <div class="mp-k"><div><b>${num(A.n || 0)}</b><span>avisos publicados</span></div><div><b>${num(A.activos || 0)}</b><span>avisos activos hoy</span></div>
        <div><b>${A.n ? rng(A.gasto) : '—'}</b><span>gasto estimado (${esc(A.moneda || 'ARS')})</span></div><div><b>${A.n ? rng(A.impresiones) : '—'}</b><span>impresiones estimadas</span></div></div>
        ${A.n ? '' : `<p class="mp-n">No hay avisos políticos firmados por ${esc(me.name)} ni por sus páginas en los últimos ${days} días. Abajo, qué hace la competencia.</p>`}</div>
      <div class="mp-card mp-c12"><h3>Frente a la competencia<small>${A.n ? `puesto ${rank} de ${rows.length} por gasto` : 'quién está pautando'}</small></h3><div class="mp-w">
        <table class="mp-t"><thead><tr><th>Figura</th><th class="n">Avisos</th><th class="n">Activos</th><th class="n">Gasto estimado</th><th class="n">Impresiones</th><th>Dónde se vio más</th></tr></thead><tbody>
        ${rows.map(f => { const a = f.ads || {}; const r = Object.keys(a.regiones || {})[0]; return `<tr class="${f === me ? 'me' : ''}"><td>${esc(f.name)}</td><td class="n">${num(a.n || 0)}</td><td class="n">${num(a.activos || 0)}</td><td class="n">${a.n ? rng(a.gasto) : '—'}</td><td class="n">${a.n ? rng(a.impresiones) : '—'}</td><td>${r ? esc(r) + ' · ' + a.regiones[r] + '%' : '—'}</td></tr>` }).join('')}
        </tbody></table></div><p class="mp-n">Meta informa gasto e impresiones en rangos: se muestran sumados, de mínimo a máximo. Solo cuentan avisos de páginas o firmantes con el apellido de cada figura.</p></div>
      ${A.n ? `<div class="mp-card mp-c4"><h3>Dónde se vieron sus avisos</h3>${bars(A.regiones)}</div>
      <div class="mp-card mp-c4"><h3>Edad del público alcanzado</h3>${bars(A.edades)}</div>
      <div class="mp-card mp-c4"><h3>Género</h3>${bars(A.genero, k => GEN[k] || k)}
        <h3 style="margin-top:16px">Plataformas<small>avisos</small></h3>${Object.entries(A.plataformas || {}).map(([k, v]) => `<span class="mp-n" style="display:inline-block;margin:0 12px 0 0">${esc(k)} <b>${v}</b></span>`).join('') || '<div class="mp-e">Sin datos.</div>'}</div>
      <div class="mp-card mp-c6"><h3>Avisos con más alcance</h3>${(A.avisos || []).map(x => `<a class="mp-a" href="${esc(x.u)}" target="_blank" rel="noopener">${esc(x.t)}<small>${esc(x.d)} · ver en la Biblioteca de Anuncios</small></a>`).join('') || '<div class="mp-e">Sin textos de avisos.</div>'}</div>
      <div class="mp-card mp-c6"><h3>Páginas que pautan<small>% de sus avisos</small></h3>${bars(Object.fromEntries(Object.entries(A.paginas || {}).map(([k, v]) => [k, Math.round(1000 * v / (A.n || 1)) / 10])))}</div>` : ''}
    </div></div>`;
    S.drawn = true;
  }

  function init(cfg) {
    fetch(cfg.data, { cache: 'no-store' }).then(r => r.ok ? r.json() : null).then(d => {
      if (!d || !(d.figuras || []).length) return;
      S.D = d;
      const st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
      const nav = $('#tabs'), main = $('main'); if (!nav || !main) return;
      const btn = document.createElement('button'); btn.dataset.t = 'pauta'; btn.textContent = cfg.etiqueta || 'Pauta en Meta';
      const before = ['instagram', 'metodo'].map(t => $(`#tabs button[data-t="${t}"]`)).find(Boolean);
      nav.insertBefore(btn, before || null);
      const sec = document.createElement('section'); sec.className = 'tab'; sec.id = 't-pauta'; main.appendChild(sec);
      const open = () => { $$('#tabs button').forEach(x => x.classList.toggle('on', x === btn)); $$('.tab').forEach(t => t.classList.toggle('on', t === sec)); if (!S.drawn) draw(); try { history.replaceState(null, '', location.search + '#pauta') } catch (e) { } };
      btn.addEventListener('click', open);
      if (location.hash === '#pauta') open();
    }).catch(e => console.warn('pauta', e));
  }
  window.MetaPauta = { init, _S: S };
})();
