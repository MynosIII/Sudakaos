# Landing 3D (web/)

`web/index.html` es un HTML único (Three.js 0.160 por CDN; si no hay WebGL o falla el CDN, dibuja el globo en 2D).

Para regenerar los puntos del globo:

```
npm pack world-atlas@2.0.2 && tar xzf world-atlas-2.0.2.tgz
python3 web/tools/prep_geo.py package/countries-50m.json geo.json 110000
python3 -c "s=open('web/tools/template.html').read();open('web/index.html','w').write(s.replace('/*GEO*/',open('geo.json').read()))"
```

## Páginas de capacidades

`web/<slug>/index.html` (inteligencia, prospectiva, comunicacion, sistemas, ciberseguridad, comunidad) se generan con
`python3 web/tools/build.py`, que también rearma `web/index.html` desde `template.html` + `geo.json`.
El texto está en `content.py`; los gráficos ilustrativos (datos simulados) en `web/assets/charts.js`.

## Datos reales (países y situación)

`web/data/paises.json` y `web/data/situacion.json` los genera `python3 web/tools/datos.py` (solo librería estándar).
Fuentes gratuitas y sin clave: Banco Mundial, currency-api (fawazahmed0), Google News RSS, GDELT, USGS y GDACS.
El workflow `landing-datos.yml` lo corre cada 3 horas; al terminar, Pages y Cloudflare (sudakaoslatam.com) publican solos.
`web/paises/` y `web/situacion/` se arman con `build.py` (texto en `pages_data.py`) y se dibujan con
`web/assets/paises.js` y `situacion.js`. Los puntos por país del globo salen de `prep_geo.py` (campo `cc` de geo.json).
