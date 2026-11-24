/* Sala de situación: comportamiento común de todos los tableros (va justo después de plotly.min.js).
   Solo piel: no cambia datos, rutas ni lógica de la página. Hace tres cosas: viste los gráficos de
   Plotly, dibuja la tira "Señal" con la serie más larga de la página y pone la foto de cada persona
   ([data-foto]) desde assets/fotos/, buscada por un hash del nombre (fotos/bajar.py). */
(function(){
  'use strict';
  var MONO='"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace', SANS='"IBM Plex Sans",system-ui,sans-serif';
  var GRID='rgba(160,170,185,.08)', AXL='#2a303b', ZERO='rgba(160,170,185,.25)', SIG='#d9a04a';
  var BASE=(function(){var c=document.currentScript;return c&&c.src?c.src.replace(/[^\/]*$/,''):'assets/'})();
  var stats={series:0,puntos:0,graficos:new WeakSet(),n:0};

  /* ---------- Plotly con piel de consola ---------- */
  function cat(v){return typeof v==='string'&&!/^\d{4}-\d{2}/.test(v)}
  function axisSkin(ax,mono){
    ax.gridcolor=GRID;ax.zerolinecolor=ZERO;ax.linecolor=AXL;ax.tickcolor=AXL;
    if(ax.ticks===undefined)ax.ticks='outside';if(ax.ticklen===undefined)ax.ticklen=3;
    var tf=Object.assign({},ax.tickfont||{});if(mono)tf.family=MONO;if(!tf.size||tf.size>11)tf.size=mono?10:11;
    if(!tf.color)tf.color='#868d99';ax.tickfont=tf;
    if(ax.title&&typeof ax.title==='object'){ax.title.font=Object.assign({color:'#7d8797',size:10.5,family:MONO},ax.title.font||{},{family:MONO})}
  }
  function skin(data,lay){
    lay=lay||{};data=data||[];
    lay.paper_bgcolor='rgba(0,0,0,0)';
    if(!lay.plot_bgcolor||/^#(0|1)/.test(lay.plot_bgcolor)||/^rgba\(0,\s*0,\s*0/.test(lay.plot_bgcolor))lay.plot_bgcolor='rgba(0,0,0,0)';
    lay.font=Object.assign({},lay.font||{});lay.font.family=SANS;if(!lay.font.color||lay.font.color==='#eef0f4')lay.font.color='#a3a9b3';
    lay.hoverlabel=Object.assign({},lay.hoverlabel||{},{bgcolor:'#0b0d10',bordercolor:'#3a414d',font:{family:SANS,size:12,color:'#e6e8eb'},align:'left'});
    if(lay.legend!==undefined||data.length>1)lay.legend=Object.assign({},lay.legend||{},{font:Object.assign({color:'#98a2b2',size:10.5},(lay.legend&&lay.legend.font)||{})});
    var t0=data[0]||{}, horiz=data.some(function(t){return t&&t.orientation==='h'});
    var xcat=t0.x&&t0.x.length&&cat(t0.x[0]), ycat=t0.y&&t0.y.length&&cat(t0.y[0]);
    Object.keys(lay).forEach(function(k){
      if(/^xaxis\d*$/.test(k))axisSkin(lay[k],!xcat);
      else if(/^yaxis\d*$/.test(k))axisSkin(lay[k],!ycat&&!horiz);
      else if(/^polar\d*$/.test(k)){var p=lay[k];p.bgcolor='rgba(0,0,0,0)';['radialaxis','angularaxis'].forEach(function(a){if(p[a]){p[a].gridcolor=GRID;p[a].linecolor=AXL}})}
      else if(/^scene\d*$/.test(k)){var sc=lay[k];sc.bgcolor='rgba(0,0,0,0)';['xaxis','yaxis','zaxis'].forEach(function(a){if(sc[a]){sc[a].backgroundcolor='#0a0e14';sc[a].gridcolor='#1f2836';sc[a].zerolinecolor='#2a3444';sc[a].linecolor='#2a3444'}})}
      else if(/^geo\d*$/.test(k)){var g=lay[k];g.bgcolor='rgba(0,0,0,0)';
        if(g.showocean!==false){g.showocean=true;g.oceancolor='rgba(11,13,16,.6)'}
        if(g.landcolor&&/^#[0-3]/.test(g.landcolor))g.landcolor='#151920';
        if(g.countrycolor)g.countrycolor='#2e3a4b';if(g.coastlinecolor)g.coastlinecolor='#3d4a5e';if(g.subunitcolor)g.subunitcolor='#243041';
        ['lataxis','lonaxis'].forEach(function(a){g[a]=Object.assign({},g[a]||{},{showgrid:true,gridcolor:'rgba(160,170,185,.07)',dtick:5})})}
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

  /* ---------- marca estática (sin animación) ---------- */
  function mark(){
    return '<svg class="sl-mark" viewBox="0 0 26 26" aria-hidden="true"><rect x=".5" y=".5" width="25" height="25" fill="none" stroke="#2a303b"/>'+
      '<circle cx="13" cy="13" r="8" fill="none" stroke="#3a414d"/><path d="M13 3v20M3 13h20" stroke="#2a303b"/><rect x="15.5" y="8.5" width="3" height="3" fill="#d9a04a"/></svg>';
  }
  function activeTab(){}
  function fmt(n){return n.toLocaleString('es-AR')}
  function paint(){}

  /* ---------- fotos de las personas ---------- */
  function norm(n){return String(n||'').replace(/\(.*?\)/g,' ').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9 ]+/g,' ').replace(/\s+/g,' ').trim()}
  function clave(n){var b=unescape(encodeURIComponent(norm(n))),h=0x811c9dc5;for(var i=0;i<b.length;i++){h^=b.charCodeAt(i);h=Math.imul(h,0x01000193)>>>0}return ('0000000'+h.toString(16)).slice(-8)}
  var FOT=null,FDIR='',fotPend=false,usados={};
  function fotos(){
    if(FOT===null){if(fotPend)return;fotPend=true;
      var get=function(u){return fetch(u+'i.json').then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(j){FDIR=u;return j})};
      get('fotos/').catch(function(){return get(BASE+'fotos/')}).catch(function(){return {}}).then(function(j){FOT=j||{};fotos()});return}
    document.querySelectorAll('[data-foto]').forEach(function(el){
      var n=el.getAttribute('data-foto');if(el.__fn===n)return;el.__fn=n;
      var k=clave(n),c=FOT[k];
      if(!c){if(el.classList.contains('sl-foto')){el.classList.remove('sl-foto');el.style.backgroundImage=''}return}
      var col=getComputedStyle(el).backgroundColor;
      el.style.backgroundImage='url("'+FDIR+k+'.jpg")';el.classList.add('sl-foto');
      if(col&&!/rgba\(0, 0, 0, 0\)|transparent/.test(col))el.style.boxShadow='inset 0 -3px 0 '+col;
      el.setAttribute('role','img');el.setAttribute('aria-label',n);el.title=n+' · Foto: '+c[0]+' ('+c[1]+')';
      if(!usados[k]){usados[k]=c;credit()}
    });
  }
  var credT=0;
  function credit(){clearTimeout(credT);credT=setTimeout(function(){
    var host=document.querySelector('footer')||document.querySelector('main');if(!host)return;
    var el=document.getElementById('sl-cred');if(!el){el=document.createElement('small');el.id='sl-cred';el.className='sl-cred';host.appendChild(el)}
    var seen={},items=[];Object.keys(usados).forEach(function(k){var t=usados[k][0]+' ('+usados[k][1]+')';if(!seen[t]){seen[t]=1;items.push(t)}});
    el.textContent='Fotos: '+items.join(' · ')+'.';
  },400)}

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
      host.innerHTML='<span class="sl-wl">Tendencia · '+(best.name?String(best.name).replace(/[<>&]/g,'')+' · ':'')+String(best.x[0]).slice(0,10)+' → '+String(best.x[n-1]).slice(0,10)+'</span>'+
        '<span class="sl-wr">pico <b>'+fmt(Math.round(mx))+'</b> · último <b>'+fmt(Math.round(last))+'</b></span>'+
        '<svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="none"><polyline points="'+pts+'" fill="none" stroke="#d9a04a" stroke-width="1" vector-effect="non-scaling-stroke"/>'+
        '<circle cx="'+(im/(n-1)*W)+'" cy="2" r="0"/></svg>';
    },200);
  }

  function kpiText(){
    document.querySelectorAll('.kpi .v, .kpi>b').forEach(function(el){
      var t=el.textContent.trim();el.classList.toggle('sl-txt',/[A-Za-zÁÉÍÓÚáéíóúñ]{4,}/.test(t)&&t.replace(/[\d.,%\s+-]/g,'').length>4);
    });
  }
  function init(){
    document.documentElement.classList.add('sl-on');
    var li=document.querySelector('.logo i');
    if(li&&/^[◉·\s]*$/.test(li.textContent)&&!li.id){li.outerHTML=mark()}
    else if(!li){var lg=document.querySelector('.logo,.brand');if(lg)lg.insertAdjacentHTML('afterbegin',mark())}
    kpiText();fotos();
    new MutationObserver(function(){
      if(pend)return;pend=1;requestAnimationFrame(function(){pend=0;kpiText();fotos()});
    }).observe(document.body,{attributes:true,attributeFilter:['data-foto'],subtree:true,childList:true});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
