"""Baja las fotos de las personas que muestran los tableros: python fotos/bajar.py

- Lee fotos/lista.json: {"Nombre visible": {"wiki": "Título en es.wikipedia", "ig": "usuario"}}.
  Sin "wiki" se busca el artículo con el mismo nombre; "wiki": "" lo saltea.
- Fuente principal: la foto principal del artículo de Wikipedia, que vive en Wikimedia Commons
  (licencias libres; es.wikipedia no admite fotos no libres). Se guarda autor y licencia.
- Respaldo: la foto de perfil pública de Instagram (Graph API, business_discovery) si hay
  META_TOKEN y META_IG_USER_ID. Se acredita como "Instagram @usuario".
- Cada foto se guarda recortada en cuadrado (240 px, JPEG) en assets/fotos/<clave>.jpg, donde
  la clave es un hash del nombre: así ningún tablero ve los nombres de las demás personas.
  assets/fotos/i.json lleva clave -> [autor, licencia]. fotos/CREDITOS.md queda como registro.
- No vuelve a bajar lo que ya está, salvo FOTOS_FORZAR=1.
"""
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
LISTA = ROOT / "fotos" / "lista.json"
OUT = ROOT / "assets" / "fotos"
CRED = ROOT / "fotos" / "CREDITOS.md"
UA = "SudakaosFotos/1.0 (https://github.com/MynosIII/Sudakaos; fotos de perfil para tableros)"
SIZE = 240
FORZAR = os.environ.get("FOTOS_FORZAR") == "1"


def norm(n):
    n = re.sub(r"\(.*?\)", " ", n)
    n = unicodedata.normalize("NFD", n)
    n = "".join(c for c in n if unicodedata.category(c) != "Mn").lower()
    n = re.sub(r"[^a-z0-9 ]+", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def clave(n):
    """FNV-1a de 32 bits sobre el nombre normalizado (el mismo cálculo está en assets/sala.js)."""
    h = 0x811C9DC5
    for b in norm(n).encode("utf8"):
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def api(host, **params):
    params.update(format="json", formatversion="2")
    return json.loads(get(f"https://{host}/w/api.php?" + urllib.parse.urlencode(params)))


def limpiar(html):
    t = re.sub(r"<[^>]+>", "", html or "")
    t = re.sub(r"\s+", " ", t).strip()
    return t[:120].replace("|", "/")


def desde_wiki(titulo, lang="es"):
    d = api(f"{lang}.wikipedia.org", action="query", prop="pageimages|pageprops", piprop="name",
            redirects=1, titles=titulo)
    pages = d.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing") or "pageimage" not in pages[0]:
        return None
    if "disambiguation" in (pages[0].get("pageprops") or {}):
        return None
    archivo = pages[0]["pageimage"]
    info = api("commons.wikimedia.org", action="query", prop="imageinfo", titles="File:" + archivo,
               iiprop="url|extmetadata", iiurlwidth=480)
    p = info["query"]["pages"][0]
    if "imageinfo" not in p:
        return None
    ii = p["imageinfo"][0]
    md = ii.get("extmetadata", {})
    lic = (md.get("LicenseShortName") or {}).get("value", "")
    if not lic or re.search(r"fair|non-free|copyright", lic, re.I):
        return None
    autor = limpiar((md.get("Artist") or {}).get("value", "")) or "Wikimedia Commons"
    return {"url": ii.get("thumburl") or ii["url"], "autor": autor, "licencia": lic,
            "fuente": ii.get("descriptionurl", "")}


def desde_ig(usuario):
    tok, uid = os.environ.get("META_TOKEN"), os.environ.get("META_IG_USER_ID")
    if not (tok and uid and usuario):
        return None
    q = urllib.parse.urlencode({
        "fields": f"business_discovery.username({usuario}){{profile_picture_url}}", "access_token": tok})
    try:
        d = json.loads(get(f"https://graph.facebook.com/v21.0/{uid}?{q}", tries=1))
    except Exception:  # noqa: BLE001
        return None
    url = (d.get("business_discovery") or {}).get("profile_picture_url")
    if not url:
        return None
    return {"url": url, "autor": f"Instagram @{usuario}", "licencia": "perfil público", "fuente": f"https://www.instagram.com/{usuario}/"}


def recorte(raw):
    im = Image.open(io.BytesIO(raw))
    im = ImageOps.exif_transpose(im).convert("RGB")
    w, h = im.size
    s = min(w, h)
    x = (w - s) // 2
    # retratos verticales: la cara suele estar en el tercio superior
    y = 0 if h <= w else min(int(h * 0.06), h - s)
    im = im.crop((x, y, x + s, y + s)).resize((SIZE, SIZE), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=84, optimize=True, progressive=True)
    return buf.getvalue()


def main():
    lista = json.loads(LISTA.read_text(encoding="utf8"))
    OUT.mkdir(parents=True, exist_ok=True)
    idx_path = OUT / "i.json"
    idx = json.loads(idx_path.read_text(encoding="utf8")) if idx_path.exists() else {}
    cred = {}
    if CRED.exists():
        for line in CRED.read_text(encoding="utf8").splitlines():
            m = re.match(r"\| (.+?) \| `(\w{8})` \| (.*?) \| (.*?) \| (.*?) \|$", line)
            if m:
                cred[m.group(2)] = [m.group(1), m.group(3), m.group(4), m.group(5)]
    faltan = []
    for nombre, op in lista.items():
        k = clave(nombre)
        if k in idx and (OUT / f"{k}.jpg").exists() and not FORZAR:
            continue
        res = None
        wiki = op.get("wiki", nombre)
        try:
            if wiki:
                res = desde_wiki(wiki)
            if not res and op.get("ig"):
                res = desde_ig(op["ig"])
            if not res:
                faltan.append(nombre)
                continue
            (OUT / f"{k}.jpg").write_bytes(recorte(get(res["url"])))
        except Exception as e:  # noqa: BLE001
            print(f"  error {nombre}: {e}", file=sys.stderr)
            faltan.append(nombre)
            continue
        idx[k] = [res["autor"], res["licencia"]]
        cred[k] = [nombre, res["autor"], res["licencia"], res["fuente"]]
        print(f"ok {nombre} -> {k}.jpg ({res['licencia']})")
        time.sleep(0.4)
    idx_path.write_text(json.dumps(dict(sorted(idx.items())), ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf8")
    filas = sorted(cred.items(), key=lambda kv: norm(kv[1][0]))
    CRED.write_text(
        "# Créditos de las fotos\n\nGenerado por `fotos/bajar.py`. Fotos de Wikimedia Commons (licencia libre, "
        "se respeta autor y licencia) o, si no hay, la foto de perfil pública de Instagram.\n\n"
        "| Persona | Clave | Autor | Licencia | Fuente |\n|---|---|---|---|---|\n"
        + "".join(f"| {v[0]} | `{k}` | {v[1]} | {v[2]} | {v[3]} |\n" for k, v in filas)
        + ("\n## Sin foto\n\n" + "".join(f"- {n}\n" for n in faltan) if faltan else ""),
        encoding="utf8")
    print(f"{len(idx)} fotos; sin foto: {len(faltan)}")


if __name__ == "__main__":
    main()
