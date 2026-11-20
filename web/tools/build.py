"""Arma la landing (web/index.html) y las páginas de capacidades (web/<slug>/index.html).

Uso: python3 web/tools/build.py   (desde la raíz del repo)
"""
import html, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from content import CAPS

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.dirname(HERE)
e = html.escape

# 1) Landing con el globo
tpl = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
geo = open(os.path.join(HERE, 'geo.json'), encoding='utf-8').read()
open(os.path.join(WEB, 'index.html'), 'w', encoding='utf-8').write(tpl.replace('/*GEO*/', geo))
open(os.path.join(WEB, 'assets', 'geo.js'), 'w', encoding='utf-8').write('window.SUDAKAOS_GEO=' + geo + ';\n')

# 2) Páginas de capacidades
HEAD = '''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="{theme}">
<meta name="description" content="{desc}">
<title>{title} — Sudakaos LATAM</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400..600;1,6..72,400..600&family=Schibsted+Grotesk:wght@400..700&display=swap">
<link rel="stylesheet" href="../assets/site.css">
</head>
<body{bodycls}>
<header><div class="wrap nav"><a class="brand" href="../" aria-label="Sudakaos LATAM inicio">Sudakaos<span>●</span> LATAM</a><button class="menu" aria-expanded="false" aria-controls="nav">Menú</button><nav id="nav"><a href="../#soluciones">Soluciones</a><a href="../#metodo">Cómo trabajamos</a><a href="../paises/">Países</a><a href="../situacion/">Situación</a><a href="../#canal">Canal digital</a><a class="nav-cta" href="#contacto">Hablemos</a></nav></div></header>
<main>'''

def fig(kind, cap, n, cls=''):
    return (f'<figure class="fig {cls}"><div class="fig-head"><span class="num">Fig. {n}</span>'
            f'<span class="tag">Ilustrativo, con datos simulados</span></div>'
            f'<canvas data-chart="{kind}" role="img" aria-label="{e(cap)}"></canvas>'
            f'<figcaption>{e(cap)}</figcaption></figure>')

for i, c in enumerate(CAPS):
    prev, nxt = CAPS[i - 1], CAPS[(i + 1) % len(CAPS)]
    tabs = ''.join(f'<a href="../{o["slug"]}/"' + (' aria-current="page"' if o is c else '') + f'>{e(o["tag"])}</a>' for o in CAPS)
    items = ''.join(f'<article class="item"><b>{int(c["num"])}.{k + 1}</b><h3>{e(t)}</h3><p>{e(d)}</p></article>' for k, (t, d) in enumerate(c['items']))
    deliver = ''.join(f'<li>{e(d)}</li>' for d in c['deliver'])
    body = f'''
<div class="wrap crumb"><a href="../">Inicio</a> / <a href="../#soluciones">Capacidades</a> / {e(c["tag"])}</div>
<section class="cap-hero"><div class="wrap">
<p class="kicker">{e(c["tag"])}</p>
<h1>{e(c["title"])}</h1>
<div class="cols"><p class="lead">{e(c["lead"])}</p><p class="intro">{e(c["intro"])}</p></div>
</div></section>
<div class="wrap"><nav class="tabs" aria-label="Capacidades">{tabs}</nav></div>
<div class="wrap">{fig(c["fig1"][0], c["fig1"][1], 1)}</div>
<section class="section"><div class="wrap">
<h2>Qué incluye</h2>
<div class="items">{items}</div>
</div></section>
<section class="section" style="padding-top:0"><div class="wrap split">
{fig(c["fig2"][0], c["fig2"][1], 2, "sm")}
<aside class="side"><h3>Entregables habituales</h3><ol>{deliver}</ol><h3>Límites</h3><p class="limits">{e(c["limits"])}</p></aside>
</div>
<div class="wrap"><nav class="pager" aria-label="Otras capacidades"><a href="../{prev["slug"]}/"><span>Anterior</span><strong>{e(prev["title"])}</strong></a><a href="../{nxt["slug"]}/"><span>Siguiente</span><strong>{e(nxt["title"])}</strong></a></nav></div>
</section>
<section class="contact" id="contacto"><div class="wrap contact-grid"><div><h2>¿Qué necesitás entender mejor?</h2><p>Conversemos sobre el desafío, el contexto y la evidencia disponible. El primer intercambio sirve para delimitar una evaluación, no implica una promesa de resultado.</p></div><div><a class="button" href="mailto:lab@sudakaos.com?subject=Consulta%20{e(c["tag"])}%20-%20Sudakaos%20LATAM">Escribir al equipo</a><small>Alcance, fuentes, entregables y condiciones se acuerdan antes de iniciar cada proyecto.</small></div></div></section>
</main><footer><div class="wrap foot"><a href="../"><strong>Sudakaos<span>●</span> LATAM</strong></a><span>Inteligencia, comunicación y tecnología</span><a href="#">Volver arriba</a></div></footer>
<script>
(function(){{var m=document.querySelector('.menu'),n=document.querySelector('#nav');m.addEventListener('click',function(){{var o=m.getAttribute('aria-expanded')!=='true';m.setAttribute('aria-expanded',String(o));n.classList.toggle('open',o)}});}})();
</script>
<script src="../assets/charts.js" defer></script>
</body></html>
'''
    out = HEAD.format(desc=e(c['lead']), title=e(c['title']), theme='#ffffff', bodycls='') + body
    d = os.path.join(WEB, c['slug']); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(out)
from pages_data import build_data_pages
build_data_pages(HEAD, WEB, e)
print('ok', len(CAPS), 'páginas + países + situación')
