"""Páginas con datos reales: tablero por país (web/paises/) y sala de situación (web/situacion/).
El contenido se dibuja en el navegador con web/assets/paises.js y situacion.js a partir de web/data/*.json."""
import os

CONTACT = ('<section class="contact" id="contacto"><div class="wrap contact-grid"><div><h2>¿Qué necesitás entender mejor?</h2>'
           '<p>Conversemos sobre el desafío, el contexto y la evidencia disponible. El primer intercambio sirve para delimitar una evaluación, no implica una promesa de resultado.</p></div>'
           '<div><a class="button" href="mailto:lab@sudakaos.com?subject=Consulta%20Sudakaos%20LATAM">Escribir al equipo</a>'
           '<small>Alcance, fuentes, entregables y condiciones se acuerdan antes de iniciar cada proyecto.</small></div></div></section>')
FOOT = ('</main><footer><div class="wrap foot"><a href="../"><strong>Sudakaos<span>●</span> LATAM</strong></a><span>Inteligencia, comunicación y tecnología</span><a href="#">Volver arriba</a></div></footer>\n'
        "<script>\n(function(){var m=document.querySelector('.menu'),n=document.querySelector('#nav');m.addEventListener('click',function(){var o=m.getAttribute('aria-expanded')!=='true';m.setAttribute('aria-expanded',String(o));n.classList.toggle('open',o)});})();\n</script>\n")

PAISES = """
<div class="wrap crumb"><a href="../">Inicio</a> / Países</div>
<section class="cap-hero" style="padding-bottom:28px"><div class="wrap">
<p class="kicker">Tablero por país · datos públicos reales</p>
<h1 id="pName">Países</h1>
<div class="cols"><p class="lead" id="pLead">Cargando datos…</p><p class="intro">Indicadores macro del Banco Mundial (cada cifra con su año), tipo de cambio diario, tono de la cobertura internacional según GDELT y alertas detectadas en medios, sismos y desastres. <span class="upd" id="pUpd"></span></p></div>
</div></section>
<div class="wrap"><nav class="tabs" id="pTabs" aria-label="Países"></nav>
<div class="kpis" id="pKpis"></div>
<div class="grid2">
<section class="panel"><h2>Inflación anual</h2><p class="sub">Precios al consumidor, % anual · Banco Mundial</p><canvas id="cInf" role="img" aria-label="Serie de inflación anual"></canvas></section>
<section class="panel"><h2>Crecimiento del PIB</h2><p class="sub">Variación real, % anual · Banco Mundial</p><canvas id="cGdp" role="img" aria-label="Serie de crecimiento del PIB"></canvas></section>
<section class="panel"><h2>Tipo de cambio</h2><p class="sub" id="fxSub"></p><canvas id="cFx" role="img" aria-label="Serie de tipo de cambio"></canvas></section>
<section class="panel"><h2>Tono de la cobertura</h2><p class="sub">Promedio diario, 7 días · GDELT (negativo = cobertura desfavorable)</p><canvas id="cTone" role="img" aria-label="Tono diario de la cobertura"></canvas></section>
<section class="panel"><h2>Alertas</h2><p class="sub">Últimas 48 horas · titulares clasificados, USGS y GDACS</p><ul class="news" id="pAlerts"></ul></section>
<section class="panel"><h2>Titulares</h2><p class="sub">Últimas 24 horas · Google News</p><ul class="news" id="pNews"></ul></section>
</div>
<section style="padding:84px 0 0"><h2 style="font-size:clamp(32px,3.6vw,48px);line-height:1.05">Comparación regional</h2><p style="color:var(--muted);font-size:14px;margin:8px 0 0">Tocá una columna para ordenar y una fila para abrir el país.</p>
<div class="tbl-wrap"><table class="cmp"><thead id="pHead"></thead><tbody id="pRows"></tbody></table></div></section>
<p class="srcs">Fuentes: Banco Mundial (último dato disponible de cada indicador; algunos países publican con atraso), currency-api de código abierto (tipo de cambio de referencia), GDELT Project (tono de noticias), Google News, USGS y GDACS. Las alertas se clasifican automáticamente por palabras clave y enlazan a la fuente original: requieren lectura humana antes de cualquier decisión. Se actualiza cada 3 horas.</p>
</div>
"""

SITUACION = """
<div class="wrap"><div class="sit-top"><h1>Sala de situación</h1><span class="clock" id="sClock">UTC --:--:--</span></div>
<p style="font:400 21px/1.4 var(--serif);color:var(--ink-2);max-width:760px;margin:14px 0 0">Alertas reales en Sudamérica, México, Estados Unidos, España, Reino Unido y la Unión Europea: titulares de medios clasificados por tema, sismos y desastres. <span class="upd" id="sUpd"></span></p>
<div class="kpis" id="sKpis"></div>
<div class="sit-grid">
<div><div class="map-wrap"><canvas id="map" role="img" aria-label="Mapa de alertas recientes"></canvas><div class="mtip" id="mtip"></div></div>
<div class="legend"><span><i style="background:#ef3b52"></i>Severidad alta</span><span><i style="background:#f2a33a"></i>Media</span><span><i style="background:#9d9c94"></i>Baja</span><span>El tono de cada país indica cuántas alertas tuvo en 24 h.</span></div></div>
<aside><h2 class="side-h">Alertas por país, 24 h</h2><ul class="levels" id="sLevels"></ul></aside>
</div>
<div class="filters" id="sFilters"></div>
<p class="upd" id="sCount" style="margin:10px 0 0"></p>
<ol class="sfeed" id="sFeed"></ol>
<p class="srcs">Cómo se arma: cada 3 horas se consultan Google News (por país e idioma), el feed de sismos M4.5+ del USGS y las alertas de GDACS. Un titular entra como alerta si menciona términos de seguridad, desastres, protestas, hechos institucionales, economía o elecciones. Es una clasificación automática: cada alerta enlaza a su fuente y requiere verificación humana.</p>
</div>
"""


def build_data_pages(HEAD, WEB, e):
    for slug, title, desc, body, js, theme, cls in [
        ('paises', 'Tablero por país', 'Indicadores, tipo de cambio, tono de medios y alertas reales por país.', PAISES, 'paises.js', '#ffffff', ''),
        ('situacion', 'Sala de situación', 'Alertas reales de medios, sismos y desastres en las Américas y Europa.', SITUACION, 'situacion.js', '#0c0c0b', ' class="dark"'),
    ]:
        extra = '<script src="../assets/geo.js"></script>\n' if slug == 'situacion' else ''
        out = (HEAD.format(desc=e(desc), title=e(title), theme=theme, bodycls=cls) + body + CONTACT + FOOT + extra
               + f'<script src="../assets/{js}" defer></script>\n</body></html>\n')
        d = os.path.join(WEB, slug)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(out)
