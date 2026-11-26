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
    if(movil())chico(data,lay,cart);
    return lay;
  }

  /* ---------- celular: gráficos que entran en la pantalla y no secuestran el scroll ---------- */
  var MQ=window.matchMedia?window.matchMedia('(max-width:760px)'):{matches:false};
  function movil(){return MQ.matches}
  function corta(v,n){v=String(v);return v.length>n?v.slice(0,n-1)+'…':v}
  function chico(data,lay,cart){
    var m=Object.assign({},lay.margin||{});
    // márgenes de escritorio (60-200px) se comen medio gráfico en 390px: se achican y Plotly agranda lo justo
    if(m.l==null||m.l>48)m.l=cart?36:8;if(m.r==null||m.r>16)m.r=cart?10:8;
    if(m.t==null||m.t>36)m.t=lay.title&&lay.title.text?36:18;if(m.b==null||m.b>44)m.b=cart?34:8;
    // barras horizontales con la cifra afuera: dejar lugar para que no se corte
    if(data.some(function(t){return t&&t.orientation==='h'&&(t.text||t.texttemplate)&&t.textposition!=='inside'}))m.r=Math.max(m.r,44);
    lay.margin=m;
    Object.keys(lay).forEach(function(k){
      if(!/^[xy]axis\d*$/.test(k))return;var ax=lay[k];ax.automargin=true;
      if(ax.title){if(typeof ax.title==='string')ax.title={text:ax.title};ax.title.font=Object.assign({},ax.title.font||{},{size:9.5});ax.title.standoff=4}
      if(ax.tickfont&&ax.tickfont.size>10)ax.tickfont.size=10;
    });
    // etiquetas de categorías largas en barras horizontales: se recortan en pantalla (el tooltip conserva el texto completo)
    data.forEach(function(t){
      if(!t||t.orientation!=='h'||!Array.isArray(t.y)||!t.y.length||!cat(t.y[0]))return;
      var largo=t.y.some(function(v){return String(v).length>22});if(!largo)return;

      var ya=lay[(t.yaxis||'y').replace('y','yaxis')]||(lay.yaxis=lay.yaxis||{});
      if(!ya.tickvals){ya.tickmode='array';ya.tickvals=t.y.slice();ya.ticktext=t.y.map(function(v){return corta(v,22)})}
    });
    // leyenda vertical a la derecha: pasa abajo y en horizontal
    var hayLeg=lay.showlegend!==false&&(lay.legend!==undefined||data.filter(function(t){return t&&t.showlegend!==false}).length>1);
    var pie=data.some(function(t){return t&&/^(pie|sunburst|treemap)$/.test(t.type)});
    if(hayLeg&&!pie){var L=lay.legend||{};
      if(L.orientation!=='h'){lay.legend=Object.assign({},L,{orientation:'h',x:0,xanchor:'left',y:-0.14,yanchor:'top'})}
      lay.legend.font=Object.assign({},lay.legend.font||{},{size:10});lay.legend.itemwidth=30}
    if(pie&&hayLeg)lay.legend=Object.assign({},lay.legend||{},{orientation:'h',x:0,y:-0.05,yanchor:'top',font:{size:10,color:'#98a2b2'}});
    // barras de color de mapas y heatmaps más finas
    data.forEach(function(t){if(t&&t.colorbar){t.colorbar=Object.assign({},t.colorbar,{thickness:8,len:.7,tickfont:{size:9}})}
      if(t&&t.marker&&t.marker.colorbar){t.marker.colorbar=Object.assign({},t.marker.colorbar,{thickness:8,len:.7,tickfont:{size:9}})}});
    // arrastrar con el dedo desplaza la página, no el gráfico (salvo el cubo 3D, que se gira)
    var tres=Object.keys(lay).some(function(k){return /^scene\d*$/.test(k)})||data.some(function(t){return t&&/3d$/.test(t.type||'')});
    if(!tres)lay.dragmode=false;
  }
  function cfgMovil(cfg){
    if(!movil())return cfg;
    cfg=Object.assign({},cfg||{});cfg.displayModeBar=false;cfg.scrollZoom=false;cfg.responsive=true;
    if(cfg.doubleClick===undefined)cfg.doubleClick=false;return cfg;
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
  /* ---------- entrada de los datos: líneas que se trazan, barras que crecen ---------- */
  var QUIETO=window.matchMedia&&window.matchMedia('(prefers-reduced-motion:reduce)').matches;
  function prep(el,res,data){
    if(QUIETO||!res||!res.then)return res;
    res.then(function(gd){try{
      gd=gd||(typeof el==='string'?document.getElementById(el):el);if(!gd)return;
      if((data||[]).some(function(t){return t&&t.orientation==='h'}))gd.setAttribute('data-slh','');else gd.removeAttribute('data-slh');
      var panel=gd.closest('.sl-rv');if(panel&&panel.classList.contains('sl-in')&&panel.__slv)return;  // ya se vio: no repetir
      gd.querySelectorAll('.scatterlayer path.js-line').forEach(function(pa){pa.setAttribute('pathLength','1')});
    }catch(e){}});
    return res;
  }
  var io=null,cola=[],colaT=0;
  function revelar(){
    if(QUIETO||!('IntersectionObserver' in window))return;
    if(!io)io=new IntersectionObserver(function(es){
      es.forEach(function(e){if(!e.isIntersecting)return;io.unobserve(e.target);cola.push(e.target)});
      clearTimeout(colaT);colaT=setTimeout(function(){
        cola.sort(function(a,b){return a.getBoundingClientRect().top-b.getBoundingClientRect().top||a.getBoundingClientRect().left-b.getBoundingClientRect().left});
        cola.forEach(function(c,i){c.style.setProperty('--sl-d',Math.min(i*.07,.42)+'s');c.classList.add('sl-in');c.__slv=1;
          setTimeout(function(){c.querySelectorAll('path.js-line[pathLength]').forEach(function(pa){pa.removeAttribute('pathLength')})},2600)});
        cola=[];
      },16);
    },{rootMargin:'0px 0px -8% 0px',threshold:.06});
    document.querySelectorAll('main .card, main .kpis, main .hero, main .hero2, main .duel, .tab .card').forEach(function(c){
      if(c.__slr)return;c.__slr=1;
      var r=c.getBoundingClientRect();if(r.height&&r.top<innerHeight*.9&&r.bottom>0&&document.readyState==='complete'&&performance.now()>4000)return; // ya visible tras la carga: sin salto
      c.classList.add('sl-rv');io.observe(c);
    });
  }
  function wrap(P){
    if(!P||P.__sala)return;P.__sala=1;
    ['newPlot','react'].forEach(function(fn){
      var orig=P[fn];if(!orig)return;
      P[fn]=function(el,data,lay,cfg){
        if(data&&typeof data==='object'&&!Array.isArray(data)&&data.data){var f=data;f.layout=skin(f.data,f.layout);f.config=cfgMovil(f.config);count(el,f.data);try{consider(f.data)}catch(e){}return prep(el,orig.call(P,el,f),f.data)}
        try{lay=skin(data,lay)}catch(e){}
        try{cfg=cfgMovil(cfg)}catch(e){}
        count(el,data);try{consider(data)}catch(e){}
        return prep(el,orig.call(P,el,data,lay,cfg),data);
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
  /* ---------- celular: tablas que se deslizan y pestaña activa siempre a la vista ---------- */
  function tablas(){
    if(!movil())return;
    document.querySelectorAll('main table, .tab table, section table').forEach(function(t){
      var fila=t.querySelector('tr'),cols=0;if(fila)Array.prototype.forEach.call(fila.children,function(c){cols+=c.colSpan||1});
      if(cols!==t.__slc){t.__slc=cols;t.classList.toggle('sl-ancha',cols>=5);if(cols>=5)t.style.setProperty('--sl-min',Math.min(cols*92,900)+'px')}
      // en tablas anchas, las celdas de texto largo (titulares, narrativas) piden lugar en vez de estirar la fila
      if(cols>=5)t.querySelectorAll('td').forEach(function(td){if(td.__sll!==td.textContent.length){td.__sll=td.textContent.length;td.classList.toggle('sl-largo',td.__sll>60)}});
      if(t.__slt)return;t.__slt=1;
      for(var q=t.parentElement;q&&q!==document.body;q=q.parentElement){
        var o=getComputedStyle(q).overflowX;if(o==='auto'||o==='scroll'){q.classList.add('sl-tw');return}
        if(q.classList.contains('card')||q.tagName==='MAIN')break;
      }
      var w=document.createElement('div');w.className='sl-tw';t.parentNode.insertBefore(w,t);w.appendChild(t);
    });
  }
  var navTop=null;
  function pestana(e){
    var b=e.target.closest&&e.target.closest('nav button, nav .navlink');if(!b||!movil())return;
    var n=b.parentElement;
    if(navTop===null){var nv=b.closest('nav');navTop=nv?Math.max(0,nv.getBoundingClientRect().top+window.scrollY):0}
    var y=window.scrollY,tope=navTop;
    setTimeout(function(){
      var x=b.offsetLeft-(n.clientWidth-b.offsetWidth)/2;try{n.scrollTo({left:x,behavior:'smooth'})}catch(_){n.scrollLeft=x}
      if(y>tope&&window.scrollY>tope)window.scrollTo(0,tope);   // la pestaña nueva empieza arriba, con las pestañas a la vista
    },30);
  }
  function init(){
    document.documentElement.classList.add('sl-on');
    var li=document.querySelector('.logo i');
    if(li&&/^[◉·\s]*$/.test(li.textContent)&&!li.id){li.outerHTML=mark()}
    else if(!li){var lg=document.querySelector('.logo,.brand');if(lg)lg.insertAdjacentHTML('afterbegin',mark())}
    kpiText();fotos();tablas();revelar();
    document.addEventListener('click',pestana,true);
    new MutationObserver(function(){
      if(pend)return;pend=1;requestAnimationFrame(function(){pend=0;kpiText();fotos();tablas();revelar()});
    }).observe(document.body,{attributes:true,attributeFilter:['data-foto'],subtree:true,childList:true});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
