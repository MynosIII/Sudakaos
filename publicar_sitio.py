"""Arma _site/ para GitHub Pages: cada tablero en una ruta secreta e imposible de adivinar.

    INDICE_RUTA=<secreto> python3 publicar_sitio.py <sha>

- Cada tablero vive en /<hash>/, donde hash sale del secret INDICE_RUTA y del nombre del
  tablero. El secret no está en el repo ni en el log (ambos públicos), así que las rutas
  no se pueden deducir. Cada carpeta lleva todo lo que su página necesita.
- La raíz no muestra ningún tablero: lleva a la landing institucional (web/).
- El índice interno se publica en /<INDICE_RUTA>/.
- Ningún tablero enlaza a otro; si aparece un link, la publicación se corta.
"""
import base64
import hashlib
import html
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fotos.subset import copiar as copiar_fotos  # noqa: E402

REPO = Path(__file__).resolve().parent
SITE = REPO / "_site"
SECRET = os.environ.get("INDICE_RUTA", "")
SHA = (sys.argv[1] if len(sys.argv) > 1 else "dev")[:8]
if not SECRET:
    sys.exit("Falta el secret INDICE_RUTA: sin él no se puede publicar con rutas secretas")
INDICE = re.sub(r"[^A-Za-z0-9_-]", "", SECRET)


# Nombre visible en la URL: /<nombre>/<clave>/. El nombre solo no muestra nada (no hay index.html ahí).
PUB = {"nacional": "nacional", "boca": "boca", "roca": "soria", "santacruz": "santacruz", "sanisidro": "sanisidro",
       "pagano": "pagano", "casielles": "casielles", "braillard": "braillard", "clark": "clark",
       "raverta": "raverta", "otermin": "otermin", "rehl": "rehl", "ramos": "ramos", "avila": "avila", "akirchner": "alicia", "zicarelli": "zicarelli", "presto": "presto", "danann": "danann",
       "brujula": "brujula"}


def carpeta(nombre):
    return SITE / PUB[nombre] / ruta(nombre)


def ruta(nombre):
    h = hashlib.sha256(f"{SECRET}:{nombre}".encode()).digest()
    return "t" + base64.b32encode(h).decode().lower().rstrip("=")[:19]


def cp(src, dst):
    src, dst = REPO / src, Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    elif src.exists():
        shutil.copy(src, dst)


def editar(path, *pares):
    s = path.read_text(encoding="utf8")
    for viejo, nuevo in pares:
        if viejo not in s:
            sys.exit(f"publicar: no encontré {viejo!r} en {path}")
        s = s.replace(viejo, nuevo)
    path.write_text(s, encoding="utf8")


shutil.rmtree(SITE, ignore_errors=True)
SITE.mkdir()
cp(".nojekyll", SITE / ".nojekyll")
cp("assets", SITE / "assets")
# Landing institucional 3D (Sudakaos LATAM): pública e indexable
cp("web", SITE / "web")
shutil.rmtree(SITE / "web" / "tools", ignore_errors=True)
(SITE / "index.html").write_text(
    '<!doctype html><meta charset="utf-8"><title>Sudakaos LATAM</title>'
    '<meta http-equiv="refresh" content="0; url=web/"><a href="web/">Sudakaos LATAM</a>\n', encoding="utf8")

tableros = {}  # nombre -> carpeta publicada

# Tablero nacional: lleva adentro todo lo que usa (radar, Massa, Meta, Instagram, resumen)
n = carpeta("nacional")
tableros["nacional"] = n
cp("dashboard.html", n / "index.html")
cp("assets", n / "assets")
cp("resumen.js", n / "resumen.js")
cp("massa/panel.js", n / "massa" / "panel.js")
cp("massa/data", n / "massa" / "data")
cp("meta/data", n / "meta" / "data")
cp("ig/data/nacional.json", n / "ig" / "data" / "nacional.json")
cp("radar/index.html", n / "radar" / "index.html")
for f in (REPO / "radar" / "data").glob("*.json"):
    cp(f.relative_to(REPO), n / "radar" / "data" / f.name)
cp("radar/data/fuentes", n / "radar" / "data" / "fuentes")
editar(n / "radar" / "index.html", ('href="../dashboard.html"', 'href="../"'))
editar(n / "index.html", ('massa/panel.js"', f'massa/panel.js?v={SHA}"'), ('resumen.js"', f'resumen.js?v={SHA}"'))

# Tableros de cliente: cada uno con sus datos y su reporte de Instagram adentro
for b in ("boca", "roca", "santacruz", "sanisidro"):
    d = carpeta(b)
    tableros[b] = d
    cp(f"{b}/index.html", d / "index.html")
    cp(f"{b}/data", d / "data")
    if (REPO / "ig" / "data" / f"{b}.json").exists():
        cp(f"ig/data/{b}.json", d / "ig.json")
    editar(d / "index.html", (f"'../ig/data/{b}.json'", "'ig.json'"))
cp("radar/data/positions.json", tableros["roca"] / "positions.json")
editar(tableros["roca"] / "index.html", ("'../radar/data/positions.json'", "'positions.json'"))

DIRIGENTES = ("pagano", "casielles", "braillard", "clark",
              "raverta", "otermin", "rehl", "ramos", "avila", "akirchner", "zicarelli", "presto", "danann")
# Dirigentes del módulo dirigentes: build_page.py arma cada uno nombrando solo a su dirigente
for slug in DIRIGENTES:
    d = carpeta(slug)
    tableros[slug] = d
    subprocess.run([sys.executable, str(REPO / "dirigentes" / "build_page.py"), slug, str(d)], check=True,
                   stdout=subprocess.DEVNULL)

# Brújula: tablero opinión × conversación (ruta secreta) y quiz público (/quiz/, indexable)
d = carpeta("brujula")
tableros["brujula"] = d
for f in ("index.html", "panel.js", "data", "datos/ejes.json", "datos/figuras.json"):
    cp(f"brujula/{f}", d / f)
editar(d / "index.html", ('panel.js"', f'panel.js?v={SHA}"'))
q = SITE / "quiz"
for f in ("index.html", "quiz.js", "quiz.css", "i18n.js"):
    cp(f"brujula/quiz/{f}", q / f)
for f in ("ejes.json", "preguntas.json", "figuras.json", "ideologias.json"):
    cp(f"brujula/datos/{f}", q / "datos" / f)
ep = os.environ.get("QUIZ_ENDPOINT", "").strip()
if ep and not re.fullmatch(r"https://script\.google\.com/macros/s/[A-Za-z0-9_-]+/exec", ep):
    sys.exit("publicar: QUIZ_ENDPOINT no parece una URL de Apps Script (/exec)")
(q / "config.js").write_text("window.BRUJULA = { datos: 'datos/', endpoint: %s };\n" % repr(ep), encoding="utf8")
editar(q / "index.html", ('quiz.js"', f'quiz.js?v={SHA}"'), ('quiz.css"', f'quiz.css?v={SHA}"'), ('config.js"', f'config.js?v={SHA}"'), ('i18n.js"', f'i18n.js?v={SHA}"'))

# Demo pública de Trump (free trial): ruta abierta web/demo/trump/, fuera del índice secreto
subprocess.run([sys.executable, str(REPO / "trump" / "build_demo.py"), str(SITE / "web" / "demo" / "trump")], check=True,
               stdout=subprocess.DEVNULL)

# Fotos: cada tablero lleva solo las de las personas que ya nombra (nunca la carpeta completa)
shutil.rmtree(SITE / "assets" / "fotos", ignore_errors=True)
shutil.rmtree(tableros["nacional"] / "assets" / "fotos", ignore_errors=True)
for nombre, d in tableros.items():
    copiar_fotos(d)

# Cache del navegador, noindex y control: ningún tablero enlaza a otro ni a la raíz
otros_nombres = {"dashboard.html", "indice/", "../ig/data/", "../radar/"}
for nombre, d in tableros.items():
    for page in d.rglob("index.html"):
        s = page.read_text(encoding="utf8")
        s = s.replace('assets/ig.js"', f'assets/ig.js?v={SHA}"')
        if nombre != "nacional":
            s = s.replace('"../assets/', '"../../assets/')  # un nivel más: /<nombre>/<clave>/
        # Vista previa de WhatsApp y redes: título y descripción del propio tablero
        if 'property="og:title"' not in s:
            t = re.search(r"<title>([^<]*)</title>", s)
            dsc = re.search(r'<meta name="description" content="([^"]*)">', s)
            og = ""
            if t:
                og += f'\n<meta property="og:title" content="{t.group(1)}">'
            if dsc:
                og += f'\n<meta property="og:description" content="{dsc.group(1)}">'
            s = s.replace("<head>", "<head>" + og, 1)
        if 'name="robots"' not in s:
            s = s.replace("<head>", '<head>\n<meta name="robots" content="noindex,nofollow">\n<meta name="referrer" content="no-referrer">', 1)
        for b in ("boca", "roca", "santacruz", "sanisidro", "pagano", "casielles", "braillard", "clark", *DIRIGENTES[4:], "trump", "dirigentes", "radar", "web"):
            if b == nombre or (nombre == "nacional" and b == "radar"):
                continue
            if re.search(rf'href="(\.\./)+{b}/?"', s):
                sys.exit(f"publicar: {page.relative_to(SITE)} enlaza al tablero {b}")
        for x in otros_nombres:
            if x in s:
                sys.exit(f"publicar: {page.relative_to(SITE)} todavía usa {x!r}")
        page.write_text(s, encoding="utf8")

# Índice interno, solo en la ruta del secret
items = []
for nombre, d in tableros.items():
    t = re.search(r"<title>([^<]*)", (d / "index.html").read_text(encoding="utf8"))
    titulo = t.group(1) if t else nombre
    if nombre == "nacional":
        titulo += " (nacional)"
    items.append(f'<li><a href="../{d.parent.name}/{d.name}/">{html.escape(titulo)}</a></li>')
(SITE / INDICE).mkdir()
(SITE / INDICE / "index.html").write_text(
    '<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    '<meta name="robots" content="noindex,nofollow"><meta name="referrer" content="no-referrer"><title>Índice</title></head>'
    '<body><h1>Índice</h1><ul>' + "".join(items) + '</ul></body></html>\n', encoding="utf8")
print(f"Sitio armado: {len(tableros)} tableros en rutas secretas + índice")
