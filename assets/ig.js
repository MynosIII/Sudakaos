/* Reporte mensual de Instagram para cualquier tablero.
   Uso: <script src="../assets/ig.js"></script><script>IGReporte.init({data:'../ig/data/boca.json'})</script>
   Agrega la pestaña "Instagram" a la barra #tabs (antes de "Fuentes y método" si existe) y su sección en <main>.
   Datos: ig/data/<tablero>.json, que arma ig/collect.py con Instagram Business Discovery (solo cuentas profesionales).
   "Descargar reporte" baja un HTML autocontenido con todos los meses abiertos. */
(function () {
  const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const MES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
  const MESL = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
  const COL = ['#e1306c', '#3987e5', '#f5a623', '#199e70', '#9085e9', '#5fb3c9', '#d95926', '#c3d65a', '#e66767', '#b0b6c3', '#ff7eb6', '#4dd0a1'];
  const num = n => n == null || isNaN(n) ? '—' : Math.round(n).toLocaleString('es-AR');
  const big = n => n == null || isNaN(n) ? '—' : n >= 1e6 ? (n / 1e6).toLocaleString('es-AR', { maximumFractionDigits: 1 }) + 'M' : n >= 1e4 ? Math.round(n / 1e3).toLocaleString('es-AR') + 'K' : num(n);
  const pc = (x, d = 2) => x == null || isNaN(x) ? '—' : x.toLocaleString('es-AR', { minimumFractionDigits: d, maximumFractionDigits: d }) + '%';
  const sg = n => n == null ? '—' : (n > 0 ? '+' : '') + big(n);
  const S = { cfg: null, D: null, M: [], F: [], metric: 'likes', rank: 'likes', mes: null, drawn: false };

  const CSS = `
.igr{--ig1:#f58529;--ig2:#dd2a7b;--ig3:#8134af;--igc:#e1306c;--bg1:var(--s1,var(--panel,#13161d));--bg2:var(--s2,var(--panel2,#1a1e27));--bg3:var(--s3,#222734);--ln:var(--line,#272c38);--ln2:var(--line2,#323848);--tx:var(--txt,#eef0f4);--mu:var(--muted,#a6adbb);--di:var(--dim,#717887);--mo:var(--mono,ui-monospace,Menlo,monospace);color:var(--tx)}
.igr *{box-sizing:border-box}
.igr-head{position:relative;display:flex;gap:16px;align-items:flex-end;flex-wrap:wrap;background:linear-gradient(100deg,#1d0f1c,var(--bg1) 60%);border:1px solid var(--ln2);border-radius:8px;padding:18px 20px 16px;margin-bottom:14px;overflow:hidden}
.igr-head::before{content:"";position:absolute;left:0;top:0;right:0;height:3px;background:linear-gradient(90deg,var(--ig1),var(--ig2),var(--ig3))}
.igr-k{font:600 11px var(--mo);letter-spacing:1.4px;color:var(--igc);text-transform:uppercase}
.igr-head h2{margin:3px 0 2px;font-size:26px;letter-spacing:-.5px;line-height:1.15}.igr-head h2 span{background:linear-gradient(90deg,var(--ig1),var(--ig2));-webkit-background-clip:text;background-clip:text;color:transparent}
.igr-m{color:var(--di);font:12px var(--mo)}
.igr-act{margin-left:auto;display:flex;gap:8px}
.igr-btn{border:1px solid var(--igc);background:var(--igc);color:#fff;border-radius:999px;padding:8px 16px;font:inherit;font-size:13px;cursor:pointer}
.igr-btn.o{background:none;color:var(--tx);border-color:var(--ln2)}
.igr-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-bottom:14px}
.igr-st{background:#07080b;border:1px solid var(--ln);border-radius:8px;padding:12px 14px;position:relative;overflow:hidden}
.igr-st::before{content:"";position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--ig1),var(--ig2))}
.igr-st span{display:block;color:var(--di);font:600 10px var(--mo);letter-spacing:1px;text-transform:uppercase}
.igr-st b{display:block;font-size:24px;letter-spacing:-.5px;margin-top:2px}
.igr-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:10px;margin-bottom:14px}
.igr-c{background:var(--bg1);border:1px solid var(--ln);border-left:3px solid var(--c);border-radius:8px;padding:12px 14px}
.igr-c.foco{background:linear-gradient(180deg,#1f1220,var(--bg1) 70%);border-color:#4a2342;border-left-color:var(--c)}
.igr-c h4{margin:0;font-size:15px;line-height:1.25}.igr-c a.h{color:var(--c);font:12px var(--mo);text-decoration:none}
.igr-r{display:flex;justify-content:space-between;gap:8px;padding:3px 0;font-size:12.5px;border-bottom:1px solid var(--ln)}.igr-r:last-of-type{border-bottom:0}
.igr-r span{color:var(--mu)}.igr-r b{font-family:var(--mo);font-weight:600}.igr-r b.up{color:#3fbf6f}.igr-r b.dn{color:#e66767}
.igr-bar{height:4px;background:var(--bg3);border-radius:2px;margin-top:8px;overflow:hidden}.igr-bar i{display:block;height:100%;background:var(--c);border-radius:2px}
.igr-card{background:var(--bg1);border:1px solid var(--ln);border-radius:8px;padding:14px 16px;margin-bottom:14px;min-width:0}
.igr-card>h3{margin:0 0 10px;font-size:16px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.igr-chips{display:flex;gap:6px;flex-wrap:wrap;margin-left:auto}
.igr-chip{border:1px solid var(--ln2);background:none;color:var(--mu);border-radius:999px;padding:4px 11px;font:inherit;font-size:12.5px;cursor:pointer}
.igr-chip.on{background:var(--igc);border-color:var(--igc);color:#fff}
.igr-chip.mo{font-family:var(--mo);font-size:12px}
.igr-svg{width:100%;height:auto;display:block}
.igr-leg{display:flex;flex-wrap:wrap;gap:4px 14px;margin:6px 0 10px;font-size:12px;color:var(--mu)}.igr-leg i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.igr-tw{overflow-x:auto;-webkit-overflow-scrolling:touch;border:1px solid var(--ln);border-radius:6px}
.igr table{width:100%;border-collapse:collapse;font-size:12.5px;font-variant-numeric:tabular-nums}
.igr th{background:#07080b;color:var(--mu);font:600 10.5px var(--mo);letter-spacing:.6px;text-transform:uppercase;padding:7px 8px;text-align:left;white-space:nowrap;border-bottom:2px solid var(--igc)}
.igr td{padding:6px 8px;border-bottom:1px solid var(--ln);color:var(--mu);white-space:nowrap}
.igr td.n,.igr th.n{text-align:right;font-family:var(--mo);color:var(--tx)}
.igr td.hm{text-align:right;font-family:var(--mo);color:var(--tx)}
.igr td.tt{white-space:normal;min-width:220px;max-width:420px;color:var(--mu);font-size:12px}
.igr td b{color:var(--tx)}
.igr a.v{color:var(--igc);font-weight:600;text-decoration:none}
.igr-rank{display:grid;grid-template-columns:22px minmax(110px,190px) 1fr 74px;gap:8px;align-items:center;padding:4px 0}
.igr-rank .p{font:800 13px var(--mo);color:var(--igc);text-align:center}.igr-rank .n{font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.igr-rank .b{height:16px;background:var(--bg3);border-radius:4px;overflow:hidden}.igr-rank .b i{display:block;height:100%;border-radius:4px}
.igr-rank .v{font:600 12.5px var(--mo);text-align:right}
.igr-g2{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,7fr);gap:14px}
.igr h5{margin:4px 0 8px;font:600 11px var(--mo);letter-spacing:1.2px;color:var(--di);text-transform:uppercase}
.igr details{border:1px solid var(--ln);border-radius:6px;margin-top:8px;background:var(--bg2)}
.igr summary{cursor:pointer;padding:8px 12px;font-size:13.5px;list-style:none;display:flex;gap:10px;align-items:center}
.igr summary::-webkit-details-marker{display:none}.igr summary::before{content:"▸";color:var(--igc)}.igr details[open] summary::before{content:"▾"}
.igr summary small{color:var(--di);font-family:var(--mo);margin-left:auto}
.igr details .igr-tw{border:0;border-top:1px solid var(--ln);border-radius:0}
.igr-note{color:var(--di);font-size:12.5px;margin:4px 0 14px}.igr-note b{color:var(--mu)}
.igr-empty{color:var(--di);padding:20px;text-align:center}
.igr-k2{display:inline-block;font:600 10.5px var(--mo);padding:1px 6px;border-radius:4px;background:var(--bg3);color:var(--mu)}
@media(max-width:860px){.igr-g2{grid-template-columns:1fr}.igr-head h2{font-size:22px}.igr-rank{grid-template-columns:20px 110px 1fr 62px}}`;

  /* ---------------- cálculo ---------------- */
  function prep(D) {
    const end = new Date((D.updated_at || new Date().toISOString()).slice(0, 10) + 'T12:00:00');
    const st = new Date((D.desde || '2026-01-01') + 'T12:00:00');
    const M = [];
    for (let y = st.getFullYear(), m = st.getMonth(); y < end.getFullYear() || (y === end.getFullYear() && m <= end.getMonth()); m++) {
      if (m > 11) { m = 0; y++ }
      M.push({ k: `${y}-${String(m + 1).padStart(2, '0')}`, c: MES[m], l: `${MESL[m]} ${y}` });
    }
    const ok = D.figuras.filter(f => f.usuario);
    ok.forEach((f, i) => {
      f.color = COL[i % COL.length];
      f.P = (f.posts || []).map(p => ({ t: p[0], m: p[0].slice(0, 7), l: p[1], lk: p[1] || 0, c: p[2] || 0, k: p[3], u: p[4], x: p[5] || '', f }));
      const fol = f.followers || 0;
      f.mes = {};
      M.forEach(mm => {
        const ps = f.P.filter(p => p.m === mm.k);
        const likes = ps.reduce((a, p) => a + p.lk, 0), com = ps.reduce((a, p) => a + p.c, 0);
        f.mes[mm.k] = { posts: ps.length, likes, com, prom: ps.length ? likes / ps.length : null, er: ps.length && fol ? 100 * (likes + com) / ps.length / fol : null, ps };
      });
      const all = f.P.filter(p => M.some(mm => mm.k === p.m));
      f.tot = { posts: all.length, likes: all.reduce((a, p) => a + p.lk, 0), com: all.reduce((a, p) => a + p.c, 0) };
      f.tot.prom = all.length ? f.tot.likes / all.length : null;
      f.tot.er = all.length && fol ? 100 * (f.tot.likes + f.tot.com) / all.length / fol : null;
      const ks = {}; all.forEach(p => { (ks[p.k] = ks[p.k] || []).push(p.lk + p.c) });
      const mk = Object.entries(ks).filter(e => e[1].length >= 3).map(e => [e[0], e[1].reduce((a, b) => a + b, 0) / e[1].length]).sort((a, b) => b[1] - a[1])[0];
      f.mejor = mk ? mk[0] : null;
    });
    S.M = M; S.F = ok;
  }

  const METR = {
    posts: { l: 'Posts', v: (f, k) => f.mes[k].posts, t: f => f.tot.posts, tl: 'Total', fmt: num },
    likes: { l: 'Likes', v: (f, k) => f.mes[k].likes, t: f => f.tot.likes, tl: 'Total', fmt: big },
    prom: { l: 'Prom. likes/post', v: (f, k) => f.mes[k].prom, t: f => f.tot.prom, tl: 'Prom.', fmt: big },
    er: { l: 'Engagement %', v: (f, k) => f.mes[k].er, t: f => f.tot.er, tl: 'Prom.', fmt: x => pc(x) },
    com: { l: 'Comentarios', v: (f, k) => f.mes[k].com, t: f => f.tot.com, tl: 'Total', fmt: big },
  };

  /* ---------------- piezas (devuelven HTML: sirven para la pestaña y para el reporte descargable) ---------------- */
  function head(D, dl) {
    const M = S.M, per = M.length ? `${M[0].c}–${M[M.length - 1].c} ${M[M.length - 1].k.slice(0, 4)}` : '';
    const upd = D.updated_at ? new Date(D.updated_at).toLocaleString('es-AR', { dateStyle: 'medium', timeStyle: 'short' }) : '—';
    return `<div class="igr-head"><div><div class="igr-k">Instagram · cuentas profesionales</div><h2>Reporte de Instagram <span>· ${esc(D.titulo || '')}</span></h2>
      <div class="igr-m">${esc(per)} · ${S.F.length} cuentas · actualizado ${esc(upd)}</div></div>${dl ? '<div class="igr-act"><button class="igr-btn" data-igdl>Descargar reporte</button></div>' : ''}</div>`;
  }
  function stats() {
    const F = S.F, t = k => F.reduce((a, f) => a + (f.tot[k] || 0), 0), ers = F.map(f => f.tot.er).filter(x => x != null);
    const items = [['Cuentas', F.length], ['Meses', S.M.length], ['Posts', num(t('posts'))], ['Likes', big(t('likes'))], ['Comentarios', big(t('com'))], ['Engagement medio', ers.length ? pc(ers.reduce((a, b) => a + b, 0) / ers.length) : '—']];
    return `<div class="igr-stats">${items.map(([l, v]) => `<div class="igr-st"><span>${l}</span><b>${v}</b></div>`).join('')}</div>`;
  }
  function cards() {
    const mx = Math.max(1, ...S.F.map(f => f.tot.likes));
    return `<div class="igr-cards">${S.F.map((f, i) => `<div class="igr-c${i === 0 ? ' foco' : ''}" style="--c:${f.color}">
      <h4>${esc(f.name)}</h4><a class="h" href="https://www.instagram.com/${esc(f.usuario)}/" target="_blank" rel="noopener">@${esc(f.usuario)}</a>
      <div style="margin-top:8px">
      <div class="igr-r"><span>Seguidores</span><b>${big(f.followers)}</b></div>
      <div class="igr-r"><span>Δ 30 días</span><b class="${f.delta30 > 0 ? 'up' : f.delta30 < 0 ? 'dn' : ''}">${sg(f.delta30)}</b></div>
      <div class="igr-r"><span>Posts</span><b>${num(f.tot.posts)}</b></div>
      <div class="igr-r"><span>Likes</span><b>${big(f.tot.likes)}</b></div>
      <div class="igr-r"><span>Prom. likes/post</span><b>${big(f.tot.prom)}</b></div>
      <div class="igr-r"><span>Engagement</span><b>${pc(f.tot.er)}</b></div>
      <div class="igr-r"><span>Mejor formato</span><b>${esc(f.mejor || '—')}</b></div></div>
      <div class="igr-bar"><i style="width:${(100 * f.tot.likes / mx).toFixed(1)}%"></i></div></div>`).join('')}</div>`;
  }
  function chart(mk) {
    const M = S.M, F = S.F, me = METR[mk], W = 900, H = 260, L = 54, R = 12, T = 12, B = 28;
    const vals = F.flatMap(f => M.map(m => me.v(f, m.k))).filter(v => v != null);
    const mx = Math.max(1e-9, ...vals) * 1.08, x = i => L + (M.length > 1 ? i * (W - L - R) / (M.length - 1) : (W - L - R) / 2), y = v => T + (H - T - B) * (1 - v / mx);
    let g = '';
    for (let j = 0; j <= 4; j++) { const v = mx * j / 4, yy = y(v); g += `<line x1="${L}" x2="${W - R}" y1="${yy}" y2="${yy}" stroke="#272c38"/><text x="${L - 6}" y="${yy + 4}" text-anchor="end" fill="#717887" font-size="11">${esc(me.fmt(v))}</text>` }
    M.forEach((m, i) => { g += `<text x="${x(i)}" y="${H - 8}" text-anchor="middle" fill="#717887" font-size="11">${m.c}</text>` });
    F.forEach(f => {
      const pts = M.map((m, i) => [i, me.v(f, m.k)]).filter(p => p[1] != null);
      if (!pts.length) return;
      g += `<polyline fill="none" stroke="${f.color}" stroke-width="2.2" stroke-linejoin="round" points="${pts.map(p => `${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`).join(' ')}"/>`;
      g += pts.map(p => `<circle cx="${x(p[0]).toFixed(1)}" cy="${y(p[1]).toFixed(1)}" r="3" fill="${f.color}"><title>${esc(f.name)} · ${M[p[0]].c}: ${esc(me.fmt(p[1]))}</title></circle>`).join('');
    });
    return `<svg class="igr-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(me.l)} por mes">${g}</svg>
      <div class="igr-leg">${F.map(f => `<span><i style="background:${f.color}"></i>${esc(f.name)}</span>`).join('')}</div>`;
  }
  function heat(mk) {
    const M = S.M, F = S.F, me = METR[mk], vals = F.flatMap(f => M.map(m => me.v(f, m.k))).filter(v => v != null), mx = Math.max(1e-9, ...vals);
    const bg = v => v == null ? '' : `background:rgba(225,48,108,${(0.06 + 0.5 * v / mx).toFixed(3)})`;
    return `<div class="igr-tw"><table><thead><tr><th>Cuenta</th>${M.map(m => `<th class="n">${m.c}</th>`).join('')}<th class="n">${me.tl}</th></tr></thead><tbody>${F.map(f => `<tr><td><b>@${esc(f.usuario)}</b></td>${M.map(m => { const v = me.v(f, m.k); return `<td class="hm" style="${bg(v)}">${v == null ? '—' : esc(me.fmt(v))}</td>` }).join('')}<td class="n"><b>${esc(me.fmt(me.t(f)))}</b></td></tr>`).join('')}</tbody></table></div>`;
  }
  function bars(rows, fmt) {
    const mx = Math.max(1e-9, ...rows.map(r => r.v || 0));
    return rows.map((r, i) => `<div class="igr-rank"><span class="p">${i + 1}</span><span class="n" title="${esc(r.f.name)}">${esc(r.f.name)}</span><span class="b"><i style="width:${(100 * (r.v || 0) / mx).toFixed(1)}%;background:${r.f.color}"></i></span><span class="v">${esc(fmt(r.v))}</span></div>`).join('');
  }
  function ranking(mk) {
    const me = METR[mk];
    return bars(S.F.map(f => ({ f, v: me.t(f) })).filter(r => r.v != null).sort((a, b) => b.v - a.v), me.fmt);
  }
  const postRow = (p, i, who) => `<tr><td class="n">${i + 1}</td>${who ? `<td><b style="color:${p.f.color}">@${esc(p.f.usuario)}</b></td>` : ''}<td>${p.t.slice(8, 10)}/${p.t.slice(5, 7)} ${p.t.slice(11, 16)}</td><td><span class="igr-k2">${esc(p.k)}</span></td><td class="n">${p.l == null ? 'oculto' : num(p.l)}</td><td class="n">${num(p.c)}</td><td class="tt">${esc(p.x)}</td><td><a class="v" href="${esc(p.u)}" target="_blank" rel="noopener">ver</a></td></tr>`;
  const postTable = (ps, who) => `<div class="igr-tw"><table><thead><tr><th class="n">#</th>${who ? '<th>Cuenta</th>' : ''}<th>Fecha</th><th>Formato</th><th class="n">Likes</th><th class="n">Coment.</th><th>Texto</th><th>Link</th></tr></thead><tbody>${ps.map((p, i) => postRow(p, i, who)).join('')}</tbody></table></div>`;
  function month(k, open) {
    const F = S.F, all = F.flatMap(f => f.mes[k].ps);
    if (!all.length) return '<div class="igr-empty">Sin publicaciones registradas en este mes.</div>';
    const top = [...all].sort((a, b) => (b.lk + b.c) - (a.lk + a.c)).slice(0, 10);
    const rk = F.map(f => ({ f, v: f.mes[k].likes })).sort((a, b) => b.v - a.v);
    const tot = { p: all.length, l: all.reduce((a, p) => a + p.lk, 0), c: all.reduce((a, p) => a + p.c, 0) };
    return `<div class="igr-stats" style="margin-bottom:12px"><div class="igr-st"><span>Posts del mes</span><b>${num(tot.p)}</b></div><div class="igr-st"><span>Likes</span><b>${big(tot.l)}</b></div><div class="igr-st"><span>Comentarios</span><b>${big(tot.c)}</b></div><div class="igr-st"><span>Cuenta con más likes</span><b style="font-size:17px;line-height:1.5">${esc(rk[0].v ? rk[0].f.name : '—')}</b></div></div>
      <div class="igr-g2"><div><h5>Ranking de likes</h5>${bars(rk, big)}</div><div><h5>Top 10 publicaciones del mes</h5>${postTable(top, true)}</div></div>
      <h5 style="margin-top:16px">Todas las publicaciones, por cuenta</h5>
      ${F.filter(f => f.mes[k].posts).sort((a, b) => b.mes[k].likes - a.mes[k].likes).map(f => `<details${open ? ' open' : ''}><summary><b style="color:${f.color}">@${esc(f.usuario)}</b> ${esc(f.name)}<small>${f.mes[k].posts} posts · ${big(f.mes[k].likes)} likes · ${pc(f.mes[k].er)}</small></summary>${postTable([...f.mes[k].ps].sort((a, b) => b.lk - a.lk), false)}</details>`).join('')}`;
  }
  function missing(D) {
    const no = D.figuras.filter(f => !f.usuario), pend = S.F.filter(f => !f.completo);
    let h = '';
    if (no.length) h += `<p class="igr-note"><b>Sin cuenta profesional encontrada:</b> ${no.map(f => esc(f.name)).join(', ')}. Instagram solo deja leer cuentas profesionales (empresa o creador); si alguna tiene usuario, se corrige en ig/config.json.</p>`;
    if (pend.length) h += `<p class="igr-note"><b>Historial todavía cargándose:</b> ${pend.map(f => esc(f.name)).join(', ')}. Se completa solo en las próximas corridas diarias.</p>`;
    return h;
  }
  const metodo = () => `<p class="igr-note">Fuente: Instagram Business Discovery (Graph API de Meta, gratis): seguidores, likes y comentarios públicos de cada publicación propia. Engagement = (likes + comentarios) ÷ seguidores actuales, promedio por publicación. Las publicaciones con likes ocultos cuentan 0 likes. No se leen comentarios de usuarios.</p>`;

  /* ---------------- pestaña ---------------- */
  function draw() {
    const sec = $('#t-instagram'), D = S.D;
    if (!D) { sec.innerHTML = '<div class="igr"><div class="igr-empty">Cargando…</div></div>'; return }
    if (!S.F.length) {
      sec.innerHTML = `<div class="igr">${head(D, false)}<div class="igr-card"><div class="igr-empty">${D.estado === 'sin datos' && D.corte ? 'Instagram todavía no devolvió datos (' + esc(D.corte) + ').' : 'Todavía no hay datos de Instagram para este tablero: se cargan en la próxima corrida diaria.'}</div>${missing(D)}</div></div>`;
      return;
    }
    if (!S.mes) { const withP = S.M.filter(m => S.F.some(f => f.mes[m.k].posts)); S.mes = (withP[withP.length - 1] || S.M[S.M.length - 1]).k }
    const chips = (grp, cur, keys) => `<div class="igr-chips">${keys.map(k => `<button class="igr-chip${k === cur ? ' on' : ''}" data-${grp}="${k}">${METR[k].l}</button>`).join('')}</div>`;
    sec.innerHTML = `<div class="igr">${head(D, true)}${stats()}${missing(D)}${cards()}
      <div class="igr-card"><h3>Evolución mensual ${chips('igm', S.metric, Object.keys(METR))}</h3><div id="igr-ch">${chart(S.metric)}</div><div id="igr-hm">${heat(S.metric)}</div></div>
      <div class="igr-card"><h3>Ranking acumulado ${chips('igk', S.rank, ['likes', 'posts', 'prom', 'er', 'com'])}</h3><div id="igr-rk">${ranking(S.rank)}</div></div>
      <div class="igr-card"><h3>Mes por mes <div class="igr-chips">${S.M.map(m => `<button class="igr-chip mo${m.k === S.mes ? ' on' : ''}" data-igmes="${m.k}">${m.c}</button>`).join('')}</div></h3><div id="igr-mes">${month(S.mes)}</div></div>
      ${metodo()}</div>`;
    S.drawn = true;
  }
  function onClick(e) {
    const t = e.target.closest('[data-igm],[data-igk],[data-igmes],[data-igdl]');
    if (!t || !t.closest('#t-instagram')) return;
    const grp = t.parentElement;
    if (t.dataset.igdl != null) return download();
    $$('.igr-chip', grp).forEach(b => b.classList.toggle('on', b === t));
    if (t.dataset.igm) { S.metric = t.dataset.igm; $('#igr-ch').innerHTML = chart(S.metric); $('#igr-hm').innerHTML = heat(S.metric) }
    if (t.dataset.igk) { S.rank = t.dataset.igk; $('#igr-rk').innerHTML = ranking(S.rank) }
    if (t.dataset.igmes) { S.mes = t.dataset.igmes; $('#igr-mes').innerHTML = month(S.mes) }
  }

  /* ---------------- reporte descargable (HTML autocontenido, todos los meses) ---------------- */
  function download() {
    const D = S.D, M = S.M.filter(m => S.F.some(f => f.mes[m.k].posts));
    const nav = `<nav class="igx-nav"><a href="#resumen">Resumen</a>${M.map(m => `<a href="#m${m.k}">${m.c}</a>`).join('')}</nav>`;
    const body = `<div class="igr">${head(D, false)}${nav}<section id="resumen">${stats()}${missing(D)}${cards()}
      ${Object.keys(METR).map(k => `<div class="igr-card"><h3>${METR[k].l} por mes</h3>${chart(k)}${heat(k)}</div>`).join('')}
      <div class="igr-card"><h3>Ranking acumulado · likes</h3>${ranking('likes')}</div><div class="igr-card"><h3>Ranking acumulado · posts</h3>${ranking('posts')}</div></section>
      ${M.map(m => `<section id="m${m.k}" class="igr-card"><h3>${esc(m.l)}</h3>${month(m.k, true)}</section>`).join('')}${metodo()}</div>`;
    const css = `:root{--s1:#13161d;--s2:#1a1e27;--s3:#222734;--line:#272c38;--line2:#323848;--txt:#eef0f4;--muted:#a6adbb;--dim:#717887;--mono:ui-monospace,Menlo,Consolas,monospace}
body{margin:0;background:#0b0d12;color:#eef0f4;font:14px/1.5 Inter,system-ui,-apple-system,"Segoe UI",sans-serif}.wrap{max-width:1180px;margin:0 auto;padding:18px 16px 40px}
.igx-nav{position:sticky;top:0;z-index:5;display:flex;gap:4px;overflow-x:auto;background:#0b0d12;border-bottom:1px solid #272c38;margin:0 0 14px;padding:6px 0}.igx-nav a{color:#a6adbb;text-decoration:none;padding:6px 12px;border-radius:999px;font-size:13px;white-space:nowrap}.igx-nav a:hover{background:#e1306c;color:#fff}
section{scroll-margin-top:56px}` + CSS;
    const html = `<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Reporte Instagram · ${esc(D.titulo || '')}</title><style>${css}</style></head><body><div class="wrap">${body}</div></body></html>`;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([html], { type: 'text/html' }));
    a.download = `reporte_ig_${(D.tablero || 'tablero')}_${(D.updated_at || '').slice(0, 10)}.html`;
    document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove() }, 500);
  }

  function load() {
    if (S.D || S.loading) return S.loading;
    S.loading = fetch(S.cfg.data, { cache: 'no-cache' }).then(r => { if (!r.ok) throw new Error(r.status); return r.json() })
      .then(d => { S.D = d; prep(d); draw() })
      .catch(e => { console.warn('IG', e); $('#t-instagram').innerHTML = '<div class="igr"><div class="igr-empty">Todavía no hay datos de Instagram para este tablero.</div></div>' });
    return S.loading;
  }

  function init(cfg) {
    S.cfg = cfg;
    const st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
    const nav = $('#tabs'), main = $('main');
    if (!nav || !main) return;
    const btn = document.createElement('button'); btn.dataset.t = 'instagram'; btn.textContent = cfg.etiqueta || 'Instagram';
    const before = (cfg.antes || ['metodo', 'fuentes']).map(t => $(`#tabs button[data-t="${t}"]`)).find(Boolean);
    nav.insertBefore(btn, before || null);
    const sec = document.createElement('section'); sec.className = 'tab'; sec.id = 't-instagram';
    main.appendChild(sec);
    const open = () => { $$('#tabs button').forEach(x => x.classList.toggle('on', x === btn)); $$('.tab').forEach(t => t.classList.toggle('on', t === sec)); if (!S.drawn) draw(); load(); try { history.replaceState(null, '', location.search + '#instagram') } catch (e) { } };
    btn.addEventListener('click', open);
    document.addEventListener('click', onClick);
    if (location.hash === '#instagram') setTimeout(open, 0);
  }

  window.IGReporte = { init, _S: S };
})();
