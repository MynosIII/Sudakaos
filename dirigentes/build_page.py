"""Arma el tablero publicado de un solo dirigente: python dirigentes/build_page.py <slug> <carpeta_salida>

Cada tablero se comparte por separado con su dirigente, así que la página publicada
no puede nombrar a los otros: ni en el título o la vista previa del link (description,
og:, twitter:), ni en el código (selector, rutas de datos).
"""
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
slug, out = sys.argv[1], Path(sys.argv[2])
cfg = json.loads((ROOT / slug / "config.json").read_text(encoding="utf8"))
perfil = cfg.get("perfil", {})
nombre = perfil.get("nombre") or cfg["nombre"]
color = cfg.get("color", "#e2557b")
distrito = cfg.get("distrito", "")

src = (ROOT / "index.html").read_text(encoding="utf8")
title = f"Monitor {nombre}"
desc = (f"{nombre}: qué dice, espera y critica la gente, temas que le convienen, flancos "
        f"y comparación con su competencia" + (f" en {distrito}" if distrito else "") + ".")
t, d = html.escape(title), html.escape(desc)
meta = (f'<meta name="description" content="{d}">\n'
        f'<meta property="og:type" content="website">\n'
        f'<meta property="og:title" content="{t}">\n'
        f'<meta property="og:description" content="{d}">\n'
        f'<meta name="twitter:card" content="summary">\n'
        f'<meta name="twitter:title" content="{t}">\n'
        f'<meta name="twitter:description" content="{d}">\n'
        f'<meta name="robots" content="noindex,nofollow">')


def sub1(pat, repl, s):
    s2, n = re.subn(pat, lambda m: repl, s, count=1)
    if n != 1:
        sys.exit(f"build_page: no encontré {pat!r} en index.html")
    return s2


s = src
s = sub1(r'<html lang="es">', f'<html lang="es" data-slug="{slug}">', s)
s = sub1(r"<title>[^<]*</title>", f"<title>{t}</title>", s)
s = sub1(r'<meta name="description" content="[^"]*">', meta, s)
s = sub1(r'<span id="lg-n">[^<]*</span>', f'<span id="lg-n">{html.escape("Monitor " + nombre.split()[-1])}</span>', s)
who = json.dumps([{"s": slug, "n": nombre, "c": color}], ensure_ascii=False)
s = sub1(r"const WHO=\[.*?\];", f"const WHO={who};", s)
s = sub1(r"IGReporte\.init\(\{data:.*?\}\)", "IGReporte.init({data:'ig.json'})", s)
if cfg.get("pais", {}).get("nombre"):
    s = sub1(r'<span id="d-pais">[^<]*</span>', f'<span id="d-pais">{html.escape(cfg["pais"]["nombre"])}</span>', s)

# Ningún otro dirigente del módulo puede quedar nombrado en la página
otros = [p for p in sorted(x.name for x in ROOT.iterdir() if (x / "config.json").exists()) if p != slug]
for o in otros:
    oc = json.loads((ROOT / o / "config.json").read_text(encoding="utf8"))
    on = (oc.get("perfil") or {}).get("nombre") or oc["nombre"]
    for marca in {o, on, on.split()[-1]}:
        if marca.lower() in s.lower():
            sys.exit(f"build_page: la página de {slug} todavía nombra a {marca!r}")

out.mkdir(parents=True, exist_ok=True)
(out / "index.html").write_text(s, encoding="utf8")
if (ROOT / slug / "data").is_dir():
    shutil.copytree(ROOT / slug / "data", out / "data", dirs_exist_ok=True)
ig = ROOT.parent / "ig" / "data" / f"dirigentes-{slug}.json"
if ig.exists():
    shutil.copy(ig, out / "ig.json")
print(f"{slug}: {title} -> {out}")
