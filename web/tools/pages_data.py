"""Páginas con datos reales: tablero por país (web/paises/) y sala de situación (web/situacion/).
El contenido se dibuja en el navegador con web/assets/paises.js y situacion.js a partir de web/data/*.json."""
import os

CONTACT = ('<section class="contact" id="contacto"><div class="wrap contact-grid"><div><h2>¿Qué necesitás entender mejor?</h2>'
           '<p>Contanos el desafío. Te decimos cómo lo ganamos.</p></div>'
           '<div><a class="button" href="mailto:contacto@sudakaoslatam.com?subject=Consulta%20Sudakaos%20LATAM">Escribir al equipo</a>'
           '<small>Alcance, fuentes, entregables y condiciones se acuerdan antes de iniciar cada proyecto.</small></div></div></section>')
FOOT = ('</main><footer><div class="wrap foot"><a href="../"><strong>Sudakaos<span>●</span> LATAM</strong></a><span>Inteligencia, comunicación y tecnología</span><a href="#">Volver arriba</a></div></footer>\n'
        "<script>\n(function(){var m=document.querySelector('.menu'),n=document.querySelector('#nav');m.addEventListener('click',function(){var o=m.getAttribute('aria-expanded')!=='true';m.setAttribute('aria-expanded',String(o));n.classList.toggle('open',o)});})();\n</script>\n")

PAISES = """
<div class="wrap crumb"><a href="../">Inicio</a> / Países</div>
<section class="cap-hero" style="padding-bottom:24px"><div class="wrap">
<p class="kicker">Tablero por país · política, encuestas y coyuntura</p>
<h1 id="pName">Países</h1>
<div class="cols"><div class="gobrow"><div id="pGob"></div><p class="lead" id="pLead">Cargando datos…</p></div><p class="intro"><span id="pCtx"></span> <span class="upd" id="pUpd"></span></p></div>
</div></section>
<div class="wrap"><nav class="tabs" id="pTabs" aria-label="Países"></nav>
<div id="polSec">
<div class="polgrid">
<section class="panel"><h2 id="imgH">Imagen del presidente</h2><div id="pImg"></div>
<div id="cImgWrap"><canvas id="cImg" class="tall" role="img" aria-label="Evolución de la aprobación por encuestadora"></canvas><p class="leg" id="imgLeg"></p></div>
<div id="pPolls"></div></section>
<section class="panel"><h2>Compás político</h2><p class="sub">Eje horizontal: economía (izquierda a derecha). Eje vertical: autoridad (libertario a autoritario). En rojo, quien gobierna.</p>
<canvas id="cComp" class="sq" role="img" aria-label="Ubicación de los principales actores en un compás político"></canvas>
<p class="pnote">Lectura del equipo de Sudakaos.</p></section>
</div>
<div class="grid2">
<section class="panel"><h2>Actores y candidatos</h2><ul class="actors" id="pActors"></ul><div class="elec" id="pElec"></div>
<h3 class="h3s">Partidos</h3><ul class="parties" id="pParties"></ul></section>
<section class="panel" id="pExtraP"><div id="pExtra"></div></section>
</div>
</div>
<section style="padding:72px 0 0"><h2 style="font-size:clamp(28px,3vw,40px);line-height:1.05">Economía y coyuntura</h2><p style="color:var(--muted);font-size:14px;margin:8px 0 0">El dato más fresco disponible de cada fuente, siempre con su fecha.</p></section>
<div class="kpis" id="pKpis"></div>
<div class="grid2">
<section class="panel"><h2>Tipo de cambio</h2><p class="sub" id="fxSub"></p><canvas id="cFx" role="img" aria-label="Serie de tipo de cambio"></canvas></section>
<section class="panel"><h2>Inflación</h2><p class="sub" id="infSub"></p><canvas id="cInf" role="img" aria-label="Serie de inflación interanual"></canvas></section>
<section class="panel"><h2>Alertas</h2><p class="sub">Últimos 30 días · titulares clasificados, USGS y GDACS</p><ul class="news" id="pAlerts"></ul></section>
<section class="panel"><h2>Titulares</h2><p class="sub">Últimas 24 horas · Google News</p><ul class="news" id="pNews"></ul></section>
</div>
<section style="padding:84px 0 0"><h2 style="font-size:clamp(32px,3.6vw,48px);line-height:1.05">Comparación regional</h2><p style="color:var(--muted);font-size:14px;margin:8px 0 0">Aprobación: promedio de las encuestas de los últimos 45 días. Tocá una columna para ordenar y una fila para abrir el país.</p>
<div class="tbl-wrap"><table class="cmp"><thead id="pHead"></thead><tbody id="pRows"></tbody></table></div></section>
<p class="srcs">Fuentes: CB Consultora, AtlasIntel, Cadem, Ipsos, YouGov, Equipos, Zentrix y otras encuestadoras; OCDE, Banco Mundial y currency-api; Google News, USGS y GDACS. Fotos: Wikipedia / Wikimedia Commons. Banderas: flagcdn.</p>
</div>
"""

SITUACION = """
<div class="wrap"><div class="sit-top"><h1>Sala de situación</h1><span class="clock" id="sClock">UTC --:--:--</span></div>
<p style="font:400 21px/1.4 var(--serif);color:var(--ink-2);max-width:760px;margin:14px 0 0">Alertas en vivo en Sudamérica, México, Estados Unidos, España, Reino Unido y la Unión Europea: titulares de medios clasificados por tema, sismos y desastres. <span class="upd" id="sUpd"></span></p>
<div class="kpis" id="sKpis"></div>
<div class="sit-grid">
<div><div class="map-wrap"><canvas id="map" role="img" aria-label="Mapa de alertas recientes"></canvas><div class="mtip" id="mtip"></div></div>
<div class="legend"><span><i style="background:#ef3b52"></i>Severidad alta</span><span><i style="background:#f2a33a"></i>Media</span><span><i style="background:#9d9c94"></i>Baja</span><span>El tono de cada país indica cuántas alertas tuvo en 24 h.</span></div></div>
<aside><h2 class="side-h">Alertas por país, 24 h</h2><ul class="levels" id="sLevels"></ul></aside>
</div>
<div class="filters" id="sFilters"></div>
<p class="upd" id="sCount" style="margin:10px 0 0"></p>
<ol class="sfeed" id="sFeed"></ol>
<p class="srcs">Fuentes: Google News, USGS y GDACS, actualizadas cada 3 horas. Cada alerta enlaza a su fuente.</p>
</div>
"""


def build_data_pages(HEAD, WEB, e):
    for slug, title, desc, body, js, theme, cls in [
        ('paises', 'Tablero por país', 'Quién gobierna, imagen del presidente, candidatos, compás político y coyuntura de cada país.', PAISES, 'paises.js', '#ffffff', ''),
        ('situacion', 'Sala de situación', 'Alertas reales de medios, sismos y desastres en las Américas y Europa.', SITUACION, 'situacion.js', '#0c0c0b', ' class="dark"'),
    ]:
        extra = '<script src="../assets/geo.js"></script>\n' if slug == 'situacion' else ''
        out = (HEAD.format(desc=e(desc), title=e(title), theme=theme, bodycls=cls) + body + CONTACT + FOOT + extra
               + f'<script src="../assets/{js}" defer></script>\n</body></html>\n')
        d = os.path.join(WEB, slug)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(out)
