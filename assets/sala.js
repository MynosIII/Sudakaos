/* Sala de situación: comportamiento común de todos los tableros (va justo después de plotly.min.js).
   Solo piel: no cambia datos, rutas ni lógica de la página. Todo lo que muestra la barra de estado
   sale de la propia página (pestaña, paneles, series y puntos graficados, hora). */
(function(){
  'use strict';
  var MONO='"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace';
  var GRID='rgba(130,150,180,.085)', AXL='#263040', ZERO='rgba(130,150,180,.25)', SIG='#e8a33d';
  var stats={series:0,puntos:0,graficos:new WeakSet(),n:0};

  /* ---------- Plotly con piel de consola ---------- */
  function cat(v){return typeof v==='string'&&!/^\d{4}-\d{2}/.test(v)}
  function axisSkin(ax,mono){
    ax.gridcolor=GRID;ax.griddash='dot';ax.zerolinecolor=ZERO;ax.linecolor=AXL;ax.tickcolor=AXL;
    if(ax.ticks===undefined)ax.ticks='outside';if(ax.ticklen===undefined)ax.ticklen=3;
    var tf=Object.assign({},ax.tickfont||{});if(mono)tf.family=MONO;if(!tf.size||tf.size>11)tf.size=mono?10:11;
    if(!tf.color)tf.color='#7d8797';ax.tickfont=tf;
    if(ax.title&&typeof ax.title==='object'){ax.title.font=Object.assign({color:'#7d8797',size:10.5,family:MONO},ax.title.font||{},{family:MONO})}
  }
  function skin(data,lay){
    lay=lay||{};data=data||[];
    lay.paper_bgcolor='rgba(0,0,0,0)';
    if(!lay.plot_bgcolor||/^#(0|1)/.test(lay.plot_bgcolor)||/^rgba\(0,\s*0,\s*0/.test(lay.plot_bgcolor))lay.plot_bgcolor='rgba(0,0,0,0)';
    lay.font=Object.assign({},lay.font||{});if(!lay.font.color||lay.font.color==='#eef0f4')lay.font.color='#aab3c2';
    lay.hoverlabel=Object.assign({},lay.hoverlabel||{},{bgcolor:'#05070a',bordercolor:SIG,font:{family:MONO,size:11,color:'#e4e8ee'},align:'left'});
    if(lay.legend!==undefined||data.length>1)lay.legend=Object.assign({},lay.legend||{},{font:Object.assign({color:'#98a2b2',size:10.5},(lay.legend&&lay.legend.font)||{})});
    var t0=data[0]||{}, horiz=data.some(function(t){return t&&t.orientation==='h'});
    var xcat=t0.x&&t0.x.length&&cat(t0.x[0]), ycat=t0.y&&t0.y.length&&cat(t0.y[0]);
    Object.keys(lay).forEach(function(k){
      if(/^xaxis\d*$/.test(k))axisSkin(lay[k],!xcat);
      else if(/^yaxis\d*$/.test(k))axisSkin(lay[k],!ycat&&!horiz);
      else if(/^polar\d*$/.test(k)){var p=lay[k];p.bgcolor='rgba(0,0,0,0)';['radialaxis','angularaxis'].forEach(function(a){if(p[a]){p[a].gridcolor=GRID;p[a].linecolor=AXL}})}
      else if(/^scene\d*$/.test(k)){var sc=lay[k];sc.bgcolor='rgba(0,0,0,0)';['xaxis','yaxis','zaxis'].forEach(function(a){if(sc[a]){sc[a].backgroundcolor='#0a0e14';sc[a].gridcolor='#1f2836';sc[a].zerolinecolor='#2a3444';sc[a].linecolor='#2a3444'}})}
      else if(/^geo\d*$/.test(k)){var g=lay[k];g.bgcolor='rgba(0,0,0,0)';
        if(g.showocean!==false){g.showocean=true;g.oceancolor='rgba(6,9,13,.6)'}
        if(g.landcolor&&/^#[0-3]/.test(g.landcolor))g.landcolor='#10151d';
        if(g.countrycolor)g.countrycolor='#2e3a4b';if(g.coastlinecolor)g.coastlinecolor='#3d4a5e';if(g.subunitcolor)g.subunitcolor='#243041';
        ['lataxis','lonaxis'].forEach(function(a){g[a]=Object.assign({},g[a]||{},{showgrid:true,gridcolor:'rgba(232,163,61,.09)',griddash:'dot',dtick:5})})}
    });
    var cart=!t0.type||/^(scatter|bar|histogram|box|heatmap|violin)$/.test(t0.type);
    if(cart&&!lay.xaxis&&t0.x){lay.xaxis={};axisSkin(lay.xaxis,!xcat)}
    if(cart&&!lay.yaxis&&t0.y){lay.yaxis={};axisSkin(lay.yaxis,!ycat&&!horiz)}
    return lay;
  }
  function count(el,data){
    try{
      var node=typeof el==='string'?document.getElementById(el):el;if(!node)return;
      var s=0,p=0;(data||[]).forEach(function(t){if(!t)return;s++;var v=t.z||t.y||t.x||t.values||t.lat||t.r||[];p+=v.length||0;if(t.z&&t.z[0]&&t.z[0].length)p+=(t.z.length*t.z[0].length)-t.z.length});
      var prev=node.__sl||{s:0,p:0};stats.series+=s-prev.s;stats.puntos+=p-prev.p;node.__sl={s:s,p:p};
      if(!stats.graficos.has(node)){stats.graficos.add(node);stats.n++}
      paint();
    }catch(e){}
  }
  function wrap(P){
    if(!P||P.__sala)return;P.__sala=1;
    ['newPlot','react'].forEach(function(fn){
      var orig=P[fn];if(!orig)return;
      P[fn]=function(el,data,lay,cfg){
        if(data&&typeof data==='object'&&!Array.isArray(data)&&data.data){var f=data;f.layout=skin(f.data,f.layout);count(el,f.data);try{consider(f.data)}catch(e){}return orig.call(P,el,f)}
        try{lay=skin(data,lay)}catch(e){}
        count(el,data);try{consider(data)}catch(e){}
        return orig.call(P,el,data,lay,cfg);
      };
    });
  }
  if(window.Plotly)wrap(window.Plotly);
  else{var _P;try{Object.defineProperty(window,'Plotly',{configurable:true,get:function(){return _P},set:function(v){_P=v;wrap(v)}})}catch(e){}}

  /* ---------- radar del logo ---------- */
  function radar(){
    return '<svg class="sl-radar" viewBox="0 0 30 30" aria-hidden="true"><defs><linearGradient id="slsw" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#e8a33d" stop-opacity="0"/><stop offset="1" stop-color="#e8a33d" stop-opacity=".55"/></linearGradient></defs>'+
      '<rect x=".5" y=".5" width="29" height="29" fill="#07090d" stroke="#263040"/>'+
      '<circle cx="15" cy="15" r="11" fill="none" stroke="#263040"/><circle cx="15" cy="15" r="6.5" fill="none" stroke="#1c2430"/>'+
      '<path d="M15 3v24M3 15h24" stroke="#1c2430"/>'+
      '<g><path d="M15 15L15 4A11 11 0 0 1 24.5 9.5Z" fill="url(#slsw)"/><line x1="15" y1="15" x2="24.5" y2="9.5" stroke="#e8a33d" stroke-width="1"/>'+
      (matchMedia('(prefers-reduced-motion: reduce)').matches?'':'<animateTransform attributeName="transform" type="rotate" from="0 15 15" to="360 15 15" dur="4s" repeatCount="indefinite"/>')+'</g>'+
      '<rect x="19" y="18" width="2" height="2" fill="#ff4d4f"/><rect x="9" y="10" width="2" height="2" fill="#43d17a"/></svg>';
  }

  /* ---------- paneles: código, barrido, estado ---------- */
  var tabName='', hoverPan='';
  function code(s){return (s||'').replace(/^t-/,'').normalize('NFD').replace(/[^A-Za-z]/g,'').slice(0,3).toUpperCase()||'GEN'}
  function tagPanels(root){
    var secs=root.querySelectorAll('section.tab,.tab');
    var groups=secs.length?Array.prototype.slice.call(secs):[root];
    groups.forEach(function(sec){
      var c=code(sec.id),i=0;
      sec.querySelectorAll('.card').forEach(function(card){
        var h=card.firstElementChild;i++;
        if(!h||h.tagName!=='H3'||h.querySelector('.sl-id'))return;
        var id=document.createElement('span');id.className='sl-id';
        var o=card.getAttribute('data-o');
        id.innerHTML=(o?o.replace(/[<>&]/g,'')+' · ':'')+c+'-'+(i<10?'0':'')+i+'<i></i>';
        h.appendChild(id);
        card.addEventListener('mouseenter',function(){hoverPan=c+'-'+(i<10?'0':'')+i+' '+(h.firstChild&&h.firstChild.textContent||'').trim();paint()});
        card.addEventListener('mouseleave',function(){hoverPan='';paint()});
      });
    });
  }
  function scan(sec){
    kpiText();countUp(sec);
    if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;
    var cards=sec.querySelectorAll('.card,.kpi');
    Array.prototype.forEach.call(cards,function(card,k){
      if(k>40)return;
      var h=card.offsetHeight;if(!h)return;
      var s=document.createElement('i');s.className='sl-scan';s.style.setProperty('--h',h+'px');s.style.animationDelay=(k*35)+'ms';
      if(getComputedStyle(card).position==='static')card.style.position='relative';
      card.appendChild(s);setTimeout(function(){s.remove()},1100+k*35);
    });
  }
  function activeTab(){
    var b=document.querySelector('#tabs button.on, nav button.on');
    tabName=b?(b.childNodes[0]&&b.childNodes[0].textContent||b.textContent).trim():'';
  }

  var bar,t0=Date.now();
  function pad(n){return (n<10?'0':'')+n}
  function fmt(n){return n.toLocaleString('es-AR')}
  function paint(){
    if(!bar)return;
    var d=new Date(),up=Math.floor((Date.now()-t0)/1000);
    var vis=document.querySelector('.tab.on')?document.querySelectorAll('.tab.on .card').length:document.querySelectorAll('.card').length;
    bar.querySelector('[data-k=tab]').innerHTML='Pestaña <b>'+(tabName||'—').replace(/[<>&]/g,'')+'</b>';
    bar.querySelector('[data-k=pan]').innerHTML='Paneles <b>'+vis+'</b>';
    bar.querySelector('[data-k=ser]').innerHTML='Series <b>'+fmt(stats.series)+'</b>';
    bar.querySelector('[data-k=pts]').innerHTML='Puntos graficados <b>'+fmt(stats.puntos)+'</b>';
    bar.querySelector('[data-k=fill]').textContent=hoverPan?('▸ '+hoverPan):'';
    bar.querySelector('[data-k=fill]').className='sl-fill'+(hoverPan?' sl-pan':'');
    bar.querySelector('[data-k=utc]').innerHTML='UTC <b>'+pad(d.getUTCHours())+':'+pad(d.getUTCMinutes())+':'+pad(d.getUTCSeconds())+'</b>';
    bar.querySelector('[data-k=ses]').innerHTML='Sesión <b>'+pad(Math.floor(up/60))+':'+pad(up%60)+'</b>';
  }
  function statusBar(){
    bar=document.createElement('div');bar.id='sl-status';bar.setAttribute('aria-hidden','true');
    bar.innerHTML='<span class="sl-ok">Enlace</span><span data-k="tab"></span><span data-k="pan" class="sl-x"></span><span data-k="ser" class="sl-x"></span><span data-k="pts" class="sl-x"></span><span data-k="fill" class="sl-fill"></span><span data-k="utc"></span><span data-k="ses" class="sl-x"></span>';
    document.body.appendChild(bar);paint();setInterval(paint,1000);
  }

  var pend=0;

  /* ---------- tira de señal: la serie temporal más larga que grafica la propia página ---------- */
  var best=null;
  function consider(data){
    (data||[]).forEach(function(t){
      if(!t||!Array.isArray(t.x)||!Array.isArray(t.y)||t.orientation==='h'||t.type==='pie')return;
      if(!(typeof t.x[0]==='string'&&/^\d{4}-\d{2}/.test(t.x[0])))return;
      var y=t.y.map(Number);if(y.some(isNaN)||y.length<8)return;
      var sum=y.reduce(function(a,b){return a+Math.abs(b)},0);
      if(!best||y.length>best.y.length||(y.length===best.y.length&&sum>best.sum))best={x:t.x,y:y,sum:sum,name:t.name||''};
    });
    if(best)wave();
  }
  var waveT=0;
  function wave(){
    clearTimeout(waveT);waveT=setTimeout(function(){
      var host=document.getElementById('sl-wave');
      if(!host){host=document.createElement('div');host.id='sl-wave';var top=document.querySelector('.top,header');if(!top)return;top.appendChild(host)}
      var y=best.y,n=y.length,mx=Math.max.apply(null,y),mn=Math.min(0,Math.min.apply(null,y)),W=1000,H=30;
      var pts=y.map(function(v,i){return (i/(n-1)*W).toFixed(1)+','+(H-2-(v-mn)/((mx-mn)||1)*(H-6)).toFixed(1)}).join(' ');
      var last=y[n-1],im=y.indexOf(mx);
      host.innerHTML='<span class="sl-wl">Señal · '+(best.name?String(best.name).replace(/[<>&]/g,'')+' · ':'')+String(best.x[0]).slice(0,10)+' → '+String(best.x[n-1]).slice(0,10)+'</span>'+
        '<span class="sl-wr">pico <b>'+fmt(Math.round(mx))+'</b> · último <b>'+fmt(Math.round(last))+'</b></span>'+
        '<svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="none"><defs><linearGradient id="slwf" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e8a33d" stop-opacity=".28"/><stop offset="1" stop-color="#e8a33d" stop-opacity="0"/></linearGradient></defs>'+
        '<polygon points="0,'+H+' '+pts+' '+W+','+H+'" fill="url(#slwf)"/><polyline points="'+pts+'" fill="none" stroke="#e8a33d" stroke-width="1.2" vector-effect="non-scaling-stroke"/>'+
        '<line x1="'+(im/(n-1)*W)+'" x2="'+(im/(n-1)*W)+'" y1="0" y2="'+H+'" stroke="#ff4d4f" stroke-width="1" vector-effect="non-scaling-stroke" stroke-dasharray="2 2"/></svg>';
    },200);
  }

  /* ---------- lecturas que cuentan hasta su valor ---------- */
  function countUp(sec){
    if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;
    sec.querySelectorAll('.kpi .v, .kpi>b').forEach(function(el){
      if(el.__sl||el.children.length)return;el.__sl=1;
      var tx=el.textContent.trim(),m=tx.match(/^([-+−]?)(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d+))?(.*)$/);
      if(!m||m[4].length>8)return;
      var whole=+m[2].replace(/\./g,''),dec=m[3]?+('0.'+m[3]):0,target=whole+dec,nd=m[3]?m[3].length:0,t1=performance.now(),D=750;
      (function step(now){var k=Math.min(1,(now-t1)/D),e=1-Math.pow(1-k,3),v=target*e;
        el.textContent=m[1]+v.toLocaleString('es-AR',{minimumFractionDigits:nd,maximumFractionDigits:nd,useGrouping:/\./.test(m[2])})+m[4];
        if(k<1)requestAnimationFrame(step);else el.textContent=tx})(t1);
    });
  }
  function kpiText(){
    document.querySelectorAll('.kpi .v, .kpi>b').forEach(function(el){
      var t=el.textContent.trim();el.classList.toggle('sl-txt',/[A-Za-zÁÉÍÓÚáéíóúñ]{4,}/.test(t)&&t.replace(/[\d.,%\s+-]/g,'').length>4);
    });
  }
  function init(){
    document.documentElement.classList.add('sl-on');
    var li=document.querySelector('.logo i');
    if(li&&/^[◉·\s]*$/.test(li.textContent)&&!li.id){li.outerHTML=radar()}
    else{var lg=document.querySelector('.logo,.brand');if(lg)lg.insertAdjacentHTML('afterbegin',radar())}
    tagPanels(document);activeTab();statusBar();
    var first=document.querySelector('.tab.on');if(first)setTimeout(function(){scan(first)},250);
    new MutationObserver(function(ms){
      ms.forEach(function(m){
        var el=m.target;
        if(m.type==='attributes'&&el.classList&&el.classList.contains('tab')&&el.classList.contains('on')&&m.oldValue&&!/\bon\b/.test(m.oldValue)){activeTab();setTimeout(function(){scan(el)},30);paint()}
        if(m.type==='childList'&&!pend){pend=1;requestAnimationFrame(function(){pend=0;tagPanels(document);kpiText()})}
      });
    }).observe(document.querySelector('main')||document.body,{attributes:true,attributeFilter:['class'],attributeOldValue:true,subtree:true,childList:true});
    var tabs=document.getElementById('tabs');if(tabs)tabs.addEventListener('click',function(){setTimeout(function(){activeTab();paint()},0)});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
