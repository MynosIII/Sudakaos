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

# 2) Páginas de capacidades
HEAD = '''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#f5f4ef">
<meta name="description" content="{desc}">
<title>{title} — Sudakaos LATAM</title>
<link rel="stylesheet" href="../assets/site.css">
</head>
<body>
<header><div class="wrap nav"><a class="brand" href="../" aria-label="Sudakaos LATAM inicio">Sudakaos<span>●</span>&nbsp;LATAM</a><button class="menu" aria-expanded="false" aria-controls="nav">MENÚ</button><nav id="nav"><a href="../#soluciones">Soluciones</a><a href="../#metodo">Cómo trabajamos</a><a href="../#respuesta">Sala de situación</a><a href="../#canal">Canal digital</a><a class="nav-cta" href="#contacto">Hablemos ↗</a></nav></div></header>
<main>'''

def fig(kind, cap, n, cls=''):
    return (f'<figure class="fig {cls} reveal"><div class="fig-head"><span class="mono">Fig. {n}</span>'
            f'<span class="mono tag">Ilustrativo · datos simulados</span></div>'
            f'<canvas data-chart="{kind}" role="img" aria-label="{e(cap)}"></canvas>'
            f'<figcaption><span class="mono">Lectura</span><span>{e(cap)}</span></figcaption></figure>')

for i, c in enumerate(CAPS):
    prev, nxt = CAPS[i - 1], CAPS[(i + 1) % len(CAPS)]
    tabs = ''.join(f'<a href="../{o["slug"]}/"' + (' aria-current="page"' if o is c else '') + f'>{o["num"]}<b>{e(o["tag"])}</b></a>' for o in CAPS)
    items = ''.join(f'<article class="item reveal"><b>{c["num"]}.{k + 1}</b><h3>{e(t)}</h3><p>{e(d)}</p></article>' for k, (t, d) in enumerate(c['items']))
    deliver = ''.join(f'<li>{e(d)}</li>' for d in c['deliver'])
    body = f'''
<div class="wrap crumb mono"><a href="../">Sudakaos LATAM</a> / <a href="../#soluciones">Capacidades</a> / <span class="red">{c["num"]} {e(c["tag"])}</span></div>
<section class="cap-hero"><div class="wrap">
<p class="eyebrow red">{c["num"]} / {e(c["tag"].upper())}</p>
<h1>{e(c["title"])}</h1>
<div class="cols"><p class="lead">{e(c["lead"])}</p><p class="intro">{e(c["intro"])}</p></div>
</div></section>
<div class="wrap"><nav class="tabs" aria-label="Capacidades">{tabs}</nav></div>
<div class="wrap">{fig(c["fig1"][0], c["fig1"][1], 1)}</div>
<section class="section"><div class="wrap">
<div class="sec-head reveal"><p class="eyebrow red">Qué incluye</p><h2>Cuatro líneas de trabajo, un mismo criterio.</h2></div>
<div class="items">{items}</div>
</div></section>
<section class="section" style="padding-top:0"><div class="wrap split">
{fig(c["fig2"][0], c["fig2"][1], 2, "sm")}
<aside class="side reveal"><h3>Entregables habituales</h3><ul>{deliver}</ul><h3>Límites</h3><p class="limits">{e(c["limits"])}</p></aside>
</div>
<div class="wrap"><nav class="pager" aria-label="Otras capacidades"><a href="../{prev["slug"]}/"><span>← Anterior · {prev["num"]}</span><strong>{e(prev["title"])}</strong></a><a href="../{nxt["slug"]}/"><span>Siguiente · {nxt["num"]} →</span><strong>{e(nxt["title"])}</strong></a></nav></div>
</section>
<section class="contact" id="contacto"><div class="wrap contact-grid"><div><p class="eyebrow">SUDAKAOS LATAM / PRÓXIMO PASO</p><h2>¿Qué necesitás<br>entender mejor?</h2><p>Conversemos sobre el desafío, el contexto y la evidencia disponible. El primer intercambio sirve para delimitar una evaluación, no implica una promesa de resultado.</p></div><div><a class="button" href="mailto:lab@sudakaos.com?subject=Consulta%20{e(c["tag"])}%20-%20Sudakaos%20LATAM">Escribir al equipo ↗</a><p class="mono" style="font-size:9px;color:#ffe4e7;margin-top:19px">Alcance, fuentes, entregables y condiciones se acuerdan antes de iniciar cada proyecto.</p></div></div></section>
</main><footer><div class="wrap foot"><a href="../"><strong>Sudakaos<span>●</span> LATAM</strong></a><span>INTELIGENCIA · COMUNICACIÓN · TECNOLOGÍA</span><a href="#">VOLVER ARRIBA ↑</a></div></footer>
<script>
(function(){{var m=document.querySelector('.menu'),n=document.querySelector('#nav');m.addEventListener('click',function(){{var o=m.getAttribute('aria-expanded')!=='true';m.setAttribute('aria-expanded',String(o));n.classList.toggle('open',o)}});
var io=new IntersectionObserver(function(es){{es.forEach(function(x){{if(x.isIntersecting){{x.target.classList.add('in');io.unobserve(x.target)}}}})}},{{rootMargin:'0px 0px -6% 0px'}});document.querySelectorAll('.reveal').forEach(function(el){{io.observe(el)}})}})();
</script>
<script src="../assets/charts.js" defer></script>
</body></html>
'''
    out = HEAD.format(desc=e(c['lead']), title=e(c['title'])) + body
    d = os.path.join(WEB, c['slug']); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(out)
print('ok', len(CAPS), 'páginas')
