"""Copia a un tablero publicado solo las fotos de las personas que ese tablero ya nombra.

    from fotos.subset import copiar; copiar(carpeta_publicada)

Busca cada nombre de fotos/lista.json en los archivos de texto de la carpeta (html, js, json) y
deja <carpeta>/fotos/<clave>.jpg + <carpeta>/fotos/i.json con esas claves. Así un cliente no puede
ver, ni enumerando assets, la cara de alguien que su tablero no muestra. sala.js busca primero
fotos/ junto a la página y después assets/fotos/ (desarrollo local).
"""
import json
import re
import shutil
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "fotos"


def norm(n):
    n = re.sub(r"\(.*?\)", " ", n)
    n = unicodedata.normalize("NFD", n)
    n = "".join(c for c in n if unicodedata.category(c) != "Mn").lower()
    n = re.sub(r"[^a-z0-9 ]+", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def clave(n):
    h = 0x811C9DC5
    for b in norm(n).encode("utf8"):
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


def copiar(carpeta):
    carpeta = Path(carpeta)
    idx_path = SRC / "i.json"
    if not idx_path.exists():
        return 0
    idx = json.loads(idx_path.read_text(encoding="utf8"))
    lista = json.loads((ROOT / "fotos" / "lista.json").read_text(encoding="utf8"))
    texto = []
    for f in carpeta.rglob("*"):
        if f.is_file() and f.suffix in (".html", ".js", ".json") and "fotos" not in f.parts:
            texto.append(f.read_text(encoding="utf8", errors="ignore"))
    texto = "\n".join(texto)
    sub = {}
    for nombre in lista:
        k = clave(nombre)
        if k not in idx:
            continue
        variantes = {nombre, json.dumps(nombre)[1:-1], re.sub(r"\s*\(.*?\)", "", nombre).strip()}
        if any(v and v in texto for v in variantes):
            sub[k] = idx[k]
    if not sub:
        return 0
    out = carpeta / "fotos"
    out.mkdir(parents=True, exist_ok=True)
    for k in sub:
        shutil.copy(SRC / f"{k}.jpg", out / f"{k}.jpg")
    (out / "i.json").write_text(json.dumps(sub, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf8")
    return len(sub)
