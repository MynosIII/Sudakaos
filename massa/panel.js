/* Pestaña "Massa · Galmarini" del tablero nacional. Lee massa/data/massa.json (lo genera massa/analyze.py). */
(function(){
const C={s1:'#13161d',s2:'#1a1e27',line:'#272c38',grid:'#232834',txt:'#eef0f4',muted:'#a6adbb',dim:'#717887',neg:'#e66767',neu:'#5d6470',pos:'#3987e5'};
const COL={'Sergio Massa':'#3987e5','Malena Galmarini':'#d55181'};
const PAL=['#199e70','#c98500','#9085e9','#5fb3c9','#d95926','#8aa1c1','#b38f3e','#5c9e5c','#c47fb0','#6f7fd6'];
const CFG={displayModeBar:false,responsive:true};
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fmt=n=>n==null?'–':Number(n).toLocaleString('es-AR');
const ini=n=>n.split(/\s+/).map(w=>w[0]).slice(0,2).join('').toUpperCase();
const base=x=>Object.assign({paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',font:{color:C.muted,family:'Inter,system-ui,sans-serif',size:12},
  margin:{l:40,r:10,t:10,b:40},hoverlabel:{bgcolor:'#0b0d12',bordercolor:C.line,font:{color:C.txt}},xaxis:{gridcolor:C.grid,zerolinecolor:C.line},yaxis:{gridcolor:C.grid,zerolinecolor:C.line},legend:{orientation:'h',y:-.18}},x||{});
const plot=(id,data,lay)=>{const el=document.getElementById(id);if(!el)return;if(!data.length){el.innerHTML='<div class="empty">Sin datos todavía.</div>';return}Plotly.react(el,data,base(lay),CFG)};
const hb=(arr,col,w,em)=>{if(!arr.length)return `<div class="empty" style="padding:10px 0">${em||'Sin datos todavía.'}</div>`;const m=Math.max(...arr.map(a=>a[1]),1);
  return arr.map(a=>`<div class="hbar" style="grid-template-columns:minmax(0,1fr) ${w||120}px 64px"><span>${esc(a[0])}</span><div class="meter"><i style="width:${Math.max(3,a[1]/m*100)}%;background:${a[2]||col}"></i></div><span class="num">${a[3]??fmt(a[1])}</span></div>`).join('')};
const tbar=t=>t?`<div class="mg-tone"><i style="width:${t.NEG}%;background:${C.neg}"></i><i style="width:${t.NEU}%;background:${C.neu}"></i><i style="width:${t.POS}%;background:${C.pos}"></i></div>`:'<span style="color:var(--dim)">s/d</span>';
const heads=h=>h&&h.length?'<ul class="list">'+h.map(x=>`<li><span class="mg-dot ${esc(x.tono||'')}"></span><a href="${esc(x.u)}" target="_blank" rel="noopener" style="color:var(--txt)">${esc(x.t)}</a><small>${esc(x.o)} · ${esc(x.d)}${(x.narr||x.dir||[]).length?' · '+(x.narr||x.dir).map(esc).join(' · '):''}</small></li>`).join('')+'</ul>':'<div class="empty">Sin titulares todavía.</div>';
let D=null,drawn=new Set(),sub='dupla';

function load(){if(D)return Promise.resolve(D);return fetch('massa/data/massa.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw 0;return r.json()}).then(d=>D=d)}
function draw(){const box=$('#t-massa');if(!box)return;
  load().then(()=>{if(!drawn.has('nav')){drawn.add('nav');
      $$('#mg-sub .pill').forEach(b=>b.onclick=()=>{sub=b.dataset.s;$$('#mg-sub .pill').forEach(x=>x.classList.toggle('on',x===b));$$('.mg-p').forEach(p=>p.hidden=p.id!=='mg-'+sub);drawSub();setTimeout(()=>window.dispatchEvent(new Event('resize')),60)});
      const age=(Date.now()-new Date(D.updated_at))/36e5;
      $('#mg-upd').textContent=`Actualizado ${new Date(D.updated_at).toLocaleString('es-AR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})}${age>36?' · datos de hace '+Math.round(age/24)+' días':''} · ${fmt(D.totales.noticias)} notas de ${fmt(D.totales.medios)} medios · ${fmt(D.totales.comentarios)} comentarios de YouTube`;
      if(!D.totales.textos)$('#mg-warn').innerHTML='<div class="mg-warn">Todavía no hay textos recolectados: la primera corrida diaria completa esta sección.</div>'}
    drawSub()}).catch(()=>{$('#mg-warn').innerHTML='<div class="mg-warn">Todavía no hay datos de esta sección: se generan con la primera corrida del recolector.</div>'})}
function drawSub(){if(drawn.has(sub))return;drawn.add(sub);({dupla,agenda,datos}[sub])()}

// ---------------------------------------------------------------- la dupla
function dupla(){const P=D.politicos,M=P.find(p=>p.name===D.foco)||{},G=P.find(p=>p.name===D.foco2)||{},V=D.voz_propia||{};
  const rank=[...P].filter(p=>p.n).sort((a,b)=>b.n-a.n);
  P.forEach((p,i)=>{if(!COL[p.name])COL[p.name]=PAL[i%PAL.length]});
  const card=p=>`<div class="mg-who"><span class="av" style="background:${COL[p.name]};width:52px;height:52px;font-size:18px">${ini(p.name||'')}</span><div><h2>${esc(p.name)}</h2><div class="k">${esc(p.cargo)} · ${esc(p.espacio)}</div>
    <div class="k"><a href="#${encodeURIComponent(p.name)}" data-goprof="${esc(p.name)}">perfil en el tablero →</a></div></div></div>`;
  const F=[];
  if(M.n&&G.n)F.push(`En los últimos ${D.conversacion_dias} días, <b>${esc(G.name)}</b> tuvo ${fmt(G.n)} menciones y <b>${esc(M.name)}</b> ${fmt(M.n)}.`);
  if(V.pct_con_massa!=null)F.push(`<b>${V.pct_con_massa}%</b> de lo que se dice de Galmarini también nombra a Massa: ${V.pct_con_massa<35?'ya tiene <b>voz propia</b> en la conversación':V.pct_con_massa<60?'la voz propia está en construcción':'todavía se la lee <b>como parte de Massa</b>'}.`);
  const gn=(G.narrativas||[])[0],mn=(M.narrativas||[])[0];
  if(gn)F.push(`A Galmarini se la nombra sobre todo en clave de <b>${esc(gn.n)}</b>${mn?`; a Massa, de <b>${esc(mn.n)}</b>`:''}.`);
  if(G.tone&&M.tone)F.push(`Tono negativo: ${G.tone.NEG}% para Galmarini y ${M.tone.NEG}% para Massa.`);
  const vac=(D.agenda||[]).filter(t=>t.n).sort((a,b)=>(b.pct_sin_dirigente??0)-(a.pct_sin_dirigente??0))[0];
  if(vac)F.push(`Tema con la bandera más libre: <b>${esc(vac.tema)}</b> (${vac.pct_sin_dirigente}% de las notas sin ningún dirigente).`);
  $('#mg-hero').innerHTML=`<div class="mg-pair">${card(M)}${card(G)}</div><ul class="brief">${F.map(x=>'<li>'+x+'</li>').join('')||'<li>Sin datos suficientes todavía.</li>'}</ul>`;
  const d=x=>x==null?'':(x>0?'+':'')+x+'% vs. semana anterior';
  $('#mg-kpis').innerHTML=[['Menciones de Massa',fmt(M.n),d(M.delta)||`${fmt(M.last7||0)} esta semana`],['Menciones de Galmarini',fmt(G.n),d(G.delta)||`${fmt(G.last7||0)} esta semana`],
    ['Galmarini junto a Massa',V.pct_con_massa!=null?V.pct_con_massa+'%':'–','de sus menciones'],['Tono negativo Massa',M.tone?M.tone.NEG+'%':'–','base: '+(M.tone_base||'–')],
    ['Tono negativo Galmarini',G.tone?G.tone.NEG+'%':'–','base: '+(G.tone_base||'–')],['Wikipedia 90 días',D.wiki?fmt(D.wiki.total_90[D.foco2]):'–','visitas al artículo de Galmarini']]
    .map(k=>`<div class="kpi"><div class="l">${k[0]}</div><div class="v">${k[1]}</div><div class="d">${k[2]}</div></div>`).join('');
  const top=[M,G,...rank.filter(p=>!p.foco).slice(0,4)].filter(p=>p&&p.weekly);
  plot('mg-weekly',top.map(p=>({x:D.semanas,y:p.weekly,name:p.name,type:'scatter',mode:'lines',line:{color:COL[p.name],width:p.foco?3:1.4,shape:'spline'}})),{hovermode:'x unified',margin:{l:40,r:10,t:10,b:50}});
  plot('mg-voz',V.n?[{x:D.semanas,y:V.semanal_sola,name:'Galmarini sola',type:'bar',marker:{color:COL[D.foco2]}},{x:D.semanas,y:V.semanal_con_massa,name:'Galmarini con Massa',type:'bar',marker:{color:COL[D.foco]}}]:[],{barmode:'stack',margin:{l:40,r:10,t:10,b:50}});
  const A=D.alertas||[],AI={volumen:'▲',dupla:'⇄',agenda:'◆',vacante:'○',competidor:'⚑'};
  $('#mg-alert').innerHTML=A.length?A.map(a=>`<div class="al baja"><div class="h">${AI[a.tipo]||'•'} ${esc(a.tipo)}</div><div class="t">${esc(a.texto)}</div></div>`).join(''):'<div class="empty">Sin cambios fuertes esta semana.</div>';
  const ks=[...new Set([...(M.narrativas||[]),...(G.narrativas||[])].map(x=>x.n))],v=(p,k)=>((p.narrativas||[]).find(x=>x.n===k)||{}).pct||0;
  ks.sort((x,y)=>(v(M,x)+v(G,x))-(v(M,y)+v(G,y)));
  plot('mg-narr',ks.length?[M,G].map(p=>({type:'bar',orientation:'h',y:ks,x:ks.map(k=>v(p,k)),name:p.name,marker:{color:COL[p.name]},hovertemplate:'%{y}: %{x}%<extra>'+esc(p.name)+'</extra>'})):[],{barmode:'group',margin:{l:200,r:10,t:10,b:40},xaxis:{gridcolor:C.grid,ticksuffix:'%'}});
  $('#mg-cl1').innerHTML=cloud(M.cloud,COL[D.foco]);$('#mg-cl2').innerHTML=cloud(G.cloud,COL[D.foco2]);
  const rows=[...P].sort((a,b)=>b.n-a.n);
  $('#mg-tab').innerHTML='<thead><tr><th>Político</th><th>Espacio</th><th class="num">Menciones</th><th class="num">Part.</th><th class="num">7 días</th><th>Tono</th><th class="num">% neg.</th><th>Narrativa principal</th></tr></thead><tbody>'+
    rows.map(p=>`<tr${p.foco?' class="mg-sel"':''}><td><div class="who"><span class="av" style="background:${COL[p.name]}">${ini(p.name)}</span><div><b style="color:var(--txt)">${esc(p.name)}</b><small>${esc(p.cargo)}</small></div></div></td><td>${esc(p.espacio)}</td><td class="num">${fmt(p.n)}</td><td class="num">${p.share!=null?p.share+'%':'–'}</td><td class="num">${fmt(p.last7)}</td><td style="min-width:110px">${tbar(p.tone)}</td><td class="num">${p.tone?p.tone.NEG+'%':'–'}</td><td>${p.narrativas&&p.narrativas[0]?esc(p.narrativas[0].n):'–'}</td></tr>`).join('')+'</tbody>';
  const W=D.wiki;
  plot('mg-wiki',W?[D.foco,D.foco2,'Axel Kicillof'].filter(k=>W.series[k]).map(k=>({x:D.semanas,y:W.series[k],name:k,type:'scatter',mode:'lines',line:{color:COL[k],width:k===D.foco2?3:1.6,shape:'spline'}})):[],{hovermode:'x unified',margin:{l:50,r:10,t:10,b:50}});
  $('#mg-co').innerHTML=hb((G.co||[]).map(c=>[c.a,c.n,COL[c.a]]));
  $('#mg-h1').innerHTML=heads(M.headlines);$('#mg-h2').innerHTML=heads(G.headlines);
  const vids=D.videos||[];
  $('#mg-vid').innerHTML=vids.length?'<table class="rank"><thead><tr><th>Video</th><th class="num">Coment.</th><th class="num">% neg.</th></tr></thead><tbody>'+vids.map(v=>`<tr><td><a href="${esc(v.url)}" target="_blank" rel="noopener">${esc(v.titulo)}</a><small style="display:block;color:var(--dim)">${esc(v.canal)} · ${esc(v.fecha)}</small></td><td class="num">${fmt(v.comentarios)}</td><td class="num">${v.neg}%</td></tr>`).join('')+'</tbody></table>':'<div class="empty">Sin videos con comentarios todavía.</div>';
}
const mctx=document.createElement('canvas').getContext('2d');
function cloud(list,col){list=(list||[]).filter(x=>x.s>0).slice(0,55);if(list.length<3)return '<div class="empty">Pocos textos todavía.</div>';
  const W=560,H=280,maxF=36,minF=11,smax=Math.max(...list.map(x=>x.s)),smin=Math.min(...list.map(x=>x.s)),placed=[],out=[];
  for(const x of list){const f=Math.round(minF+(maxF-minF)*Math.pow((x.s-smin)/Math.max(smax-smin,1e-9),.6));mctx.font=`600 ${f}px Inter, system-ui, sans-serif`;
    const w=mctx.measureText(x.w).width+4,h=f*1.02;let ok=null;
    for(let t=0;t<900;t+=.18){const r=1.6*t,cx=W/2+r*Math.cos(t)*1.35-w/2,cy=H/2+r*Math.sin(t)-h/2;if(r>Math.max(W,H))break;if(cx<2||cy<2||cx+w>W-2||cy+h>H-2)continue;
      if(!placed.some(p=>cx<p.x+p.w&&cx+w>p.x&&cy<p.y+p.h&&cy+h>p.y)){ok={x:cx,y:cy,w,h};break}}
    if(!ok)continue;placed.push(ok);const c=x.neg>=55?C.neg:x.neg<=25?col:C.muted;
    out.push(`<text x="${(ok.x+ok.w/2).toFixed(1)}" y="${(ok.y+ok.h*.8).toFixed(1)}" text-anchor="middle" font-size="${f}" font-weight="600" fill="${c}"><title>${esc(x.w)} · ${fmt(x.n)} textos · ${x.neg}% en textos negativos</title>${esc(x.w)}</text>`)}
  return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block" role="img" aria-label="Nube de palabras">${out.join('')}</svg>`}

// ---------------------------------------------------------------- agenda vacante
function agenda(){const T=D.agenda||[],all=[...T,D.datos].filter(Boolean);
  const wk=t=>Object.values(t.wiki||{}).reduce((a,w)=>a+(w.total_90||0),0);
  const mx=Math.max(1,...all.map(wk));
  plot('mg-op',all.filter(t=>t.n).length?[{type:'scatter',mode:'markers+text',x:all.map(t=>t.n),y:all.map(t=>t.pct_sin_dirigente??0),text:all.map(t=>t.corto||t.tema),textposition:'bottom center',textfont:{color:C.txt,size:11.5},
    marker:{size:all.map(t=>16+44*Math.sqrt(wk(t)/mx)),color:all.map(t=>t.color||'#5fb3c9'),opacity:.85,line:{color:'#0b0d12',width:1}},
    hovertext:all.map(t=>`<b>${esc(t.tema)}</b><br>${fmt(t.n)} notas en ${D.conversacion_dias} días<br>${t.pct_sin_dirigente??'–'}% sin ningún dirigente<br>${t.dirigente_top?'Más asociado: '+esc(t.dirigente_top.name)+' ('+t.dirigente_top.pct+'%)':'Ningún dirigente asociado'}<br>${fmt(wk(t))} visitas en Wikipedia (90 días)`),hoverinfo:'text'}]:[],
    {margin:{l:60,r:20,t:30,b:50},xaxis:{title:{text:'Cobertura en medios (notas)'},gridcolor:C.grid,range:[0,Math.max(10,...all.map(t=>t.n))*1.15]},yaxis:{title:{text:'% de notas sin ningún dirigente'},gridcolor:C.grid,range:[-12,118],ticksuffix:'%'}});
  $('#mg-agenda-list').innerHTML=T.map((t,i)=>dossier(t,i)).join('');
  T.forEach((t,i)=>dossierPlots(t,i));
}
function dossier(t,i){const top=t.dirigente_top;
  return `<div class="sect" style="margin-top:26px"><span class="mg-sw" style="background:${t.color}"></span>${esc(t.tema)}</div>
  <div class="g">
    <div class="card c12"><div class="mg-facts">${(t.datos||[]).map(x=>`<div class="mg-fact" style="border-top-color:${t.color}"><b>${esc(x.v)}</b><span>${esc(x.l)}</span><a href="${esc(x.u)}" target="_blank" rel="noopener">${esc(x.f)} ↗</a></div>`).join('')}</div></div>
    <div class="card c4"><h3>Quién tiene la bandera <span class="tag">${D.conversacion_dias} días</span></h3>
      <div class="mg-big"><b>${t.pct_sin_dirigente??'–'}${t.pct_sin_dirigente!=null?'%':''}</b><span>de ${fmt(t.n)} notas no nombra a ningún dirigente</span></div>
      <div class="mg-big"><b>${top?esc(top.name):'Nadie'}</b><span>${top?`es el más asociado: aparece en ${top.pct}% de las notas`:'ningún dirigente aparece asociado al tema'}</span></div>
      <div class="mg-big"><b>${fmt(t.foco[D.foco2]||0)} · ${fmt(t.foco[D.foco]||0)}</b><span>notas que nombran a Galmarini · a Massa</span></div>
      <div class="sect">Dirigentes nombrados</div>${hb((t.dirigentes||[]).map(x=>[x.name,x.n,COL[x.name]||'#8aa1c1']),null,90,'Ningún dirigente nombrado en estas notas.')}</div>
    <div class="card c8"><h3>Cobertura e interés <span class="tag">notas por semana · visitas a Wikipedia</span></h3><div id="mg-ag${i}" style="height:300px"></div>
      <p class="note">${t.delta4!=null?`Últimas 4 semanas: ${fmt(t.ultimas4)} notas (${t.delta4>0?'+':''}${t.delta4}% vs. las 4 anteriores). `:''}${t.medios?`${fmt(t.medios)} medios distintos.`:''}</p></div>
    <div class="card c4"><h3>Marco vigente</h3><ul class="list">${(t.marco||[]).map(x=>`<li>${esc(x)}</li>`).join('')}</ul>
      <div class="sect">Para leer</div><ul class="list">${(t.fuentes||[]).map(x=>`<li><a href="${esc(x.u)}" target="_blank" rel="noopener">${esc(x.t)} ↗</a></li>`).join('')}</ul></div>
    <div class="card c4"><h3>Cómo tomar la bandera <span class="tag">propuestas para discutir</span></h3><ol class="mg-ol">${(t.propuestas||[]).map(x=>`<li>${esc(x)}</li>`).join('')}</ol></div>
    <div class="card c4"><h3>Últimos titulares</h3><div style="max-height:330px;overflow:auto">${heads((t.titulares||[]).slice(0,12))}</div></div>
  </div>`}
function dossierPlots(t,i){const tr=[{x:D.semanas,y:t.semanal,name:'Notas',type:'bar',marker:{color:t.color||'#5fb3c9'},hovertemplate:'%{x}: %{y} notas<extra></extra>'}];
  Object.entries(t.wiki||{}).forEach(([a,w],j)=>tr.push({x:D.semanas,y:w.semanal,name:'Wikipedia: '+a,type:'scatter',mode:'lines',yaxis:'y2',line:{color:j?'#8aa1c1':'#eef0f4',width:1.6,shape:'spline'},hovertemplate:'%{x}: %{y} visitas<extra>'+esc(a)+'</extra>'}));
  plot('mg-ag'+i,t.n||Object.keys(t.wiki||{}).length?tr:[],{margin:{l:40,r:50,t:10,b:50},yaxis2:{overlaying:'y',side:'right',gridcolor:'rgba(0,0,0,0)',showgrid:false},hovermode:'x unified'})}

// ---------------------------------------------------------------- soberanía y seguridad de datos
function datos(){const T=D.datos;if(!T){$('#mg-datos').innerHTML='<div class="empty">Sin datos todavía.</div>';return}
  const S=T.sitios||[],ok=S.filter(s=>s.https===true),fuera=ok.filter(s=>s.pais_ip&&s.pais_ip!=='AR'),rast=ok.filter(s=>s.rastreadores&&Object.keys(s.rastreadores).length),
    dm=ok.filter(s=>!['reject','quarantine'].includes(s.dmarc));
  $('#mg-dkpi').innerHTML=[['Sitios públicos revisados',fmt(ok.length),`de ${fmt(S.length)} en la lista`],['Con rastreadores de terceros',fmt(rast.length),'Google, Meta, etc. en la portada'],
    ['Sin DMARC estricto',fmt(dm.length),'su correo se puede suplantar'],['Alojados fuera del país',fmt(fuera.length),'según el registro de la IP'],
    ['Filtraciones .ar conocidas',fmt((T.filtraciones||[]).length),'catálogo Have I Been Pwned'],['Notas sobre el tema',fmt(T.n),`${T.pct_sin_dirigente??'–'}% sin dirigente`]]
    .map(k=>`<div class="kpi"><div class="l">${k[0]}</div><div class="v">${k[1]}</div><div class="d">${k[2]}</div></div>`).join('');
  const H=['HSTS','CSP','Anti-clickjacking','nosniff','Referrer-Policy','Permissions-Policy'];
  const mk=v=>v===true?'<span class="mg-y" title="sí">●</span>':v===false?'<span class="mg-n" title="no">○</span>':'<span style="color:var(--dim)">–</span>';
  const ord=[...S].sort((a,b)=>((b.puntaje||{}).ok??-1)/((b.puntaje||{}).total||1)-((a.puntaje||{}).ok??-1)/((a.puntaje||{}).total||1));
  $('#mg-sitios').innerHTML=S.length?`<thead><tr><th>Sitio</th><th class="num">Puntaje</th><th>HTTPS</th>${H.map(h=>`<th>${h}</th>`).join('')}<th>Correo</th><th>Certificado</th><th>Alojamiento</th><th>Terceros y rastreadores</th></tr></thead><tbody>`+
    ord.map(s=>{const p=s.puntaje,r=s.rastreadores||{};return `<tr><td><b style="color:var(--txt)">${esc(s.nombre)}</b><small style="display:block;color:var(--dim)">${esc(s.dominio)}</small></td>
      <td class="num">${p?`<div class="meter" style="min-width:60px"><i style="width:${p.ok/p.total*100}%;background:#3987e5"></i></div>${p.ok}/${p.total}`:'–'}</td>
      <td>${s.https?mk(s.http_a_https)+' <small>redirige</small>':`<span style="color:var(--dim)">${esc(s.error||'sin HTTPS')}</span>`}</td>
      ${H.map(h=>`<td>${s.cabeceras?mk(s.cabeceras[h]):'–'}</td>`).join('')}
      <td>${s.https?`SPF ${mk(s.spf)} DMARC ${s.dmarc?esc(s.dmarc):'○'}`:'–'}</td>
      <td>${s.dias_cert!=null?`${fmt(s.dias_cert)} días<small style="display:block;color:var(--dim)">${esc(s.emisor||'')} · ${esc(s.tls||'')}</small>`:'–'}</td>
      <td>${s.pais_ip?`${esc(s.pais_ip)}<small style="display:block;color:var(--dim)">${esc(s.org||s.red||'')}</small>`:'–'}</td>
      <td>${s.https?`${fmt(s.n_terceros)} dominios externos${Object.keys(r).length?'<br>'+Object.keys(r).map(e=>`<span class="tag2">${esc(e)}</span>`).join(' '):''}${s.software_expuesto?`<small style="display:block;color:var(--dim)">expone versión: ${esc(s.software_expuesto)}</small>`:''}`:'–'}</td></tr>`}).join('')+'</tbody>':'<tr><td class="empty">El chequeo de sitios corre en la próxima actualización diaria.</td></tr>';
  $('#mg-rast').innerHTML=hb((T.rastreadores_por_empresa||[]).map(([e,n])=>[e,n,'#d95926',n+(n>1?' sitios':' sitio')]),null,110,'Ningún rastreador detectado.');
  $('#mg-inc').innerHTML=heads(T.incidentes);
  const B=T.filtraciones||[];
  $('#mg-hibp').innerHTML=B.length?'<table class="rank"><thead><tr><th>Filtración</th><th>Fecha</th><th class="num">Cuentas</th><th>Qué datos</th></tr></thead><tbody>'+B.map(b=>`<tr><td><b style="color:var(--txt)">${esc(b.titulo)}</b><small style="display:block;color:var(--dim)">${esc(b.dominio||'')}</small></td><td>${esc(b.fecha||'')}</td><td class="num">${fmt(b.cuentas)}</td><td style="font-size:12px">${(b.datos||[]).map(esc).join(', ')}</td></tr>`).join('')+'</tbody></table>':`<div class="empty">${T.hibp_error?'El catálogo no respondió en la última corrida.':'Sin filtraciones de dominios argentinos en el catálogo todavía.'}</div>`;
  const tr=[{x:D.semanas,y:T.semanal,name:'Notas',type:'bar',marker:{color:'#5fb3c9'}}];
  Object.entries(T.wiki||{}).forEach(([a,w],j)=>tr.push({x:D.semanas,y:w.semanal,name:'Wikipedia: '+a,type:'scatter',mode:'lines',yaxis:'y2',line:{color:PAL[j+1],width:1.6,shape:'spline'}}));
  plot('mg-dcov',T.n||Object.keys(T.wiki||{}).length?tr:[],{margin:{l:40,r:50,t:10,b:60},yaxis2:{overlaying:'y',side:'right',showgrid:false},hovermode:'x unified'});
  $('#mg-dban').innerHTML=`<div class="mg-big"><b>${T.pct_sin_dirigente??'–'}${T.pct_sin_dirigente!=null?'%':''}</b><span>de ${fmt(T.n)} notas sobre datos no nombra a ningún dirigente</span></div><div class="mg-big"><b>${T.dirigente_top?esc(T.dirigente_top.name):'Nadie'}</b><span>${T.dirigente_top?'es el más asociado ('+T.dirigente_top.pct+'%)':'tiene hoy la bandera'}</span></div>`+hb((T.dirigentes||[]).slice(0,6).map(x=>[x.name,x.n,COL[x.name]||'#8aa1c1']),null,90,'Ningún dirigente nombrado en estas notas.');
  $('#mg-marco').innerHTML='<ul class="list">'+(T.marco_ext||[]).map(m=>`<li><b style="color:var(--txt)">${esc(m.t)}</b><small>${esc(m.d)}</small></li>`).join('')+'</ul>';
  const G={};(T.herramientas||[]).forEach(h=>(G[h.g]=G[h.g]||[]).push(h));
  $('#mg-tools').innerHTML=Object.entries(G).map(([g,hs])=>`<div class="mg-tg"><div class="sect" style="margin-top:4px">${esc(g)}</div>${hs.map(h=>`<a class="mg-tool" href="${esc(h.u)}" target="_blank" rel="noopener"><b>${esc(h.t)} ↗</b><span>${esc(h.d)}</span></a>`).join('')}</div>`).join('');
  $('#mg-prop').innerHTML='<ol class="mg-ol">'+(T.propuestas||[]).map(x=>`<li>${esc(x)}</li>`).join('')+'</ol>';
  $('#mg-dmet').textContent=(D.metodo||{}).sitios||'';
}
window.MassaPanel={draw};
})();
