"""Agrega el almacén de General Roca en roca/data/roca.json (lo único que se publica).

Dos bloques:
  - Conversación política: menciones de María Emilia Soria y de sus competidores, tono/emoción/agresividad
    (pysentimiento si está instalado, si no diccionarios: ver radar/nlp.py), narrativas por diccionario,
    nube de palabras, co-menciones, medios que más los nombran y cubo político (posiciones editoriales).
  - Radar vecinal: reclamos por tema y por barrio/localidad del ejido, con mapa de OpenStreetMap.

No publica autores ni textos de comentarios: de los comentarios solo salen conteos, porcentajes y palabras
o frases repetidas (mínimo 3 apariciones). Los únicos textos publicados son titulares de medios.
"""
from __future__ import annotations

import json
import math
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "radar"))
import nlp  # noqa: E402  (tono/emoción/agresividad compartidos con el Radar)

CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf8"))
STORE = HERE / ".store" / "items.jsonl"
GEO = HERE / ".store" / "osm.json"
STATUS = HERE / ".store" / "status.json"
WIKI = HERE / ".store" / "wiki.json"
NLP_CACHE = HERE / ".store" / "nlp.jsonl.gz"
OUT = HERE / "data" / "roca.json"
FOCO = CONFIG["foco"]
STOP = set("""que los las del por con una para como mas pero sus les este esta esto eso esa son hay fue ser muy todo todos
todas nos ese hace hacer sin sobre entre cuando donde porque tambien solo ya asi aca alli ahi tiene tienen estan esta
era han cada otro otra otros nada algo uno dos tan bien mal quien cual desde hasta hoy aqui ver van vez fueron
sera seria puede pueden tras ante segun durante anos ano dia dias semana mes meses parte hacia luego antes despues
the and you jaja jajaja jajajaja gente video videos general roca rio negro negro rionegro rionegrino rionegrina
nota notas diario noticias noticia leer mas lmcipolletti lmneuquen letrap fue sido ser estar estuvo dijo afirmo
aseguro senalo sostuvo explico tambien ademas mientras sino aunque otro donde quienes cual cuales mismo misma
emilia maria soria intendenta""".split())
WORD = re.compile(r"[a-zñ]{4,}")


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def rx(terms):
    terms = sorted({fold(t) for t in terms}, key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(re.escape(t) for t in terms) + ")", re.I)


def rx_exact(terms):
    terms = sorted({fold(t) for t in terms}, key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(re.escape(t) for t in terms) + r")\b", re.I)


TEMAS = {k: rx(v) for k, v in CONFIG["temas"].items()}
NARR = {k: rx([t.strip() for t in v]) for k, v in CONFIG["narrativas"].items()}
RECLAMO = rx(CONFIG["marcadores_reclamo"])
POS, NEG = rx(CONFIG["positivo"]), rx(CONFIG["negativo"])
POLS = {k: rx_exact(v["alias"]) for k, v in CONFIG["politicos"].items()}
INTEND = {k: rx_exact(v["alias"]) for k, v in CONFIG.get("intendentes", {}).items()}
CTX = rx_exact(CONFIG["contexto"] + [a for v in CONFIG["localidades"].values() for a in v["alias"]])
MASK = [(re.compile(r"@[\w.\-]{2,}"), "@…"), (re.compile(r"\S+@\S+\.\w+"), "[correo]"),
        (re.compile(r"(?:\+?54)?[\s\-]?\d{3,4}[\s\-]?\d{6,7}\b"), "[tel]")]
EMOS = ["ira", "miedo", "tristeza", "alegria", "asco", "sorpresa"]


def pct(x):
    return round(100 * x, 1)


def excerpt(text: str, n=240) -> str:
    for r, rep in MASK:
        text = r.sub(rep, text)
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"


def week(s):
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return (d - timedelta(days=d.weekday())).strftime("%Y-%m-%d")


# ---------------------------------------------------------------- geometría (igual que San Isidro)
def rings_from_relation(rel):
    segs = [[(p["lon"], p["lat"]) for p in m["geometry"]] for m in rel.get("members", [])
            if m.get("type") == "way" and m.get("role", "outer") in ("outer", "") and m.get("geometry")]
    rings = []
    while segs:
        ring = segs.pop(0)
        changed = True
        while ring[0] != ring[-1] and changed:
            changed = False
            for i, s in enumerate(segs):
                if s[0] == ring[-1]:
                    ring += s[1:]
                elif s[-1] == ring[-1]:
                    ring += s[::-1][1:]
                elif s[-1] == ring[0]:
                    ring = s[:-1] + ring
                elif s[0] == ring[0]:
                    ring = s[::-1][:-1] + ring
                else:
                    continue
                segs.pop(i)
                changed = True
                break
        if len(ring) > 3:
            rings.append(ring)
    return rings


def area_km2(ring):
    lat0 = math.radians(sum(p[1] for p in ring) / len(ring))
    xy = [(math.radians(p[0]) * 6371 * math.cos(lat0), math.radians(p[1]) * 6371) for p in ring]
    return abs(sum(xy[i][0] * xy[i - 1][1] - xy[i - 1][0] * xy[i][1] for i in range(len(xy)))) / 2


def inside(lon, lat, ring):
    c, j = False, len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-15) + xi:
            c = not c
        j = i
    return c


def simplify(ring, step=0.0004):
    out = [ring[0]]
    for p in ring[1:]:
        if abs(p[0] - out[-1][0]) + abs(p[1] - out[-1][1]) >= step:
            out.append(p)
    out.append(ring[-1])
    return [[round(x, 5), round(y, 5)] for x, y in out]


GENERIC = {"barrio", "centro", "norte", "sur", "este", "oeste", "chacra", "chacras", "zona", "loteo", "plan", "viviendas"}


def build_geo():
    """Ejido, barrios con nombre de OSM y equipamiento. Devuelve (localidades, ejido, puntos, barrios_osm)."""
    locs = {k: dict(v, nombre=k, fuente_geo="config" if v.get("centro") else None) for k, v in CONFIG["localidades"].items()}
    if not GEO.exists():
        return locs, [], {}
    g = json.loads(GEO.read_text(encoding="utf8"))
    ejido, ejido_rank = None, 9
    for el in g.get("boundaries", []):
        tags = el.get("tags", {})
        name = fold(tags.get("name", ""))
        rings = rings_from_relation(el)
        if not rings:
            continue
        lvl = tags.get("admin_level")
        if "roca" in name and lvl in ("7", "8", "9"):
            # Preferir el municipio (nivel 8); si no, el nivel más cercano
            rank = {"8": 0, "7": 1, "9": 2}[lvl]
            if ejido is None or rank < ejido_rank:
                ejido, ejido_rank = rings, rank
            continue
        if lvl in ("9", "10"):
            for k, l in locs.items():
                if name == fold(k) or any(name == fold(a) for a in l["alias"]):
                    l["poligono"] = rings
                    c = rings[0]
                    l["centro"] = [sum(p[1] for p in c) / len(c), sum(p[0] for p in c) / len(c)]
                    l["fuente_geo"] = "OSM (límite)"
    for p in g.get("places", []):
        if p["kind"] in ("city", "town") and "roca" in fold(p["name"]):
            continue
        nf = fold(p["name"]).replace("barrio ", "").strip()
        in_ejido = not ejido or any(inside(p["lon"], p["lat"], r) for r in ejido)
        hit = None
        for k, l in locs.items():
            names = {fold(k)} | {fold(a).replace("barrio ", "") for a in l["alias"]}
            if nf in names:
                hit = l
                break
        if hit:
            if hit.get("fuente_geo") in (None, "config"):
                hit["centro"] = [p["lat"], p["lon"]]
                hit["fuente_geo"] = "OSM"
            continue
        # Lugar con nombre en OSM que no estaba en la lista: se suma con alias seguros ("barrio X" o nombre largo)
        if not in_ejido or len(nf) < 5 or nf in GENERIC:
            continue
        alias = [f"barrio {nf}"] + ([nf] if (" " in nf and len(nf) >= 10) or re.search(r"\d", nf) else [])
        locs[p["name"]] = {"nombre": p["name"], "alias": alias, "centro": [p["lat"], p["lon"]], "fuente_geo": "OSM", "osm_extra": True}
    pts = {}
    for k, arr in (g.get("pois") or {}).items():
        keep = [[round(lon, 5), round(lat, 5)] for lat, lon, _ in arr if not ejido or any(inside(lon, lat, r) for r in ejido)]
        pts[k] = keep
    return locs, ejido or [], pts


# ---------------------------------------------------------------- principal
def load_items():
    items = []
    if STORE.exists():
        for line in STORE.read_text(encoding="utf8").splitlines():
            if line.strip():
                try:
                    items.append(json.loads(line))
                except ValueError:
                    pass
    return items


def label_tone(rows):
    """Tono/emoción/agresividad: modelo de radar/nlp.py si hay pandas+pysentimiento, si no diccionario."""
    try:
        import pandas as pd
        df = pd.DataFrame({"id": [r["id"] for r in rows], "text": [r.get("text", "") for r in rows],
                           "clean": [fold(r.get("text", "")) for r in rows], "lang": ["es"] * len(rows),
                           "ts": pd.to_datetime([r["created_at"] for r in rows], utc=True)})
        df = nlp.label(df, NLP_CACHE)
        for r, t, e, a, m in zip(rows, df["tono"], df["emocion"], df["agresivo"], df["metodo_nlp"]):
            r.update(tono=t, emocion=e, agresivo=bool(a), metodo_nlp=m)
    except Exception as e:  # sin pandas o sin modelo: diccionario
        print(f"nlp: uso diccionario ({str(e)[:80]})", flush=True)
        for r in rows:
            lab = nlp.lexicon(fold(r.get("text", "")))
            r.update(tono=lab["tono"], emocion=lab["emocion"], agresivo=lab["agresivo"], metodo_nlp="lexico")


def frases(rs, n=14):
    c = Counter()
    for r in rs:
        toks = [w for w in re.findall(r"[a-zñ]{3,}", fold(r["text"])) if w not in STOP]
        c.update(set(toks) | {a + " " + b for a, b in zip(toks, toks[1:])})
    out = [(g, k) for g, k in c.most_common(300) if k >= 3 and (" " in g or k >= 5)]
    bi = [x for x in out if " " in x[0]][: n // 2 + 2]
    uni = [x for x in out if " " not in x[0]][: n - len(bi)]
    return sorted(bi + uni, key=lambda x: -x[1])


def main():
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=CONFIG["window_days"])).strftime("%Y-%m-%dT%H:%M:%SZ")
    items = [i for i in load_items() if i.get("created_at", "") >= since]
    # Un mismo titular puede llegar por Google News y por el RSS del medio: deduplicar por título
    seen, dedup = set(), []
    for i in sorted(items, key=lambda x: x.get("query") == "rss"):
        key = (i["kind"], fold(i.get("title") or i.get("text", ""))[:120]) if i["kind"] == "news" else (i["kind"], i["id"])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(i)
    items = dedup
    texts = [i for i in items if i["kind"] != "video"]
    vinfo = {i["video_id"]: i for i in items if i["kind"] == "video"}
    label_tone(texts)

    for r in texts:
        t = fold(r.get("text", ""))
        r["_f"] = t
        r["pols"] = [k for k, p in POLS.items() if p.search(t)]
        r["narr"] = [k for k, p in NARR.items() if p.search(" " + t + " ")]
        r["temas"] = [k for k, p in TEMAS.items() if p.search(t)]
        pos, neg = len(POS.findall(t)), len(NEG.findall(t))
        marker = bool(RECLAMO.search(t))
        r["reclamo"] = bool(r["temas"]) and ((marker or neg >= pos) if r["kind"] == "comment" else (marker or neg > pos or r["tono"] == "NEG"))
    # Comentarios heredan el político y el contexto del video cuando el video es sobre uno solo
    vpols = {v: [k for k, p in POLS.items() if p.search(fold(i.get("text", "")))] for v, i in vinfo.items()}
    vctx = {v: bool(CTX.search(fold(i.get("text", "")))) for v, i in vinfo.items()}
    for r in texts:
        if r["kind"] == "comment" and not r["pols"] and len(vpols.get(r.get("video_id"), [])) == 1:
            r["pols"] = list(vpols[r["video_id"]])
            r["pol_inferido"] = True

    # ------------------------------------------------ conversación política
    conv_since = (now - timedelta(days=CONFIG["conversacion_dias"])).strftime("%Y-%m-%dT%H:%M:%SZ")
    conv = [r for r in texts if r["created_at"] >= conv_since and r["pols"]]
    first_week = datetime.fromisoformat(week(conv_since))
    semanas = []
    w = first_week
    while w <= now.replace(tzinfo=None):
        semanas.append(w.strftime("%Y-%m-%d"))
        w += timedelta(days=7)
    total_m = sum(len(r["pols"]) for r in conv) or 1
    word_sets = [set(w for w in WORD.findall(r["_f"]) if w not in STOP) for r in conv]
    total_words = Counter(w for ws in word_sets for w in ws)
    alias_words = set(WORD.findall(" ".join(fold(a) + " " + fold(k) for k, v in CONFIG["politicos"].items() for a in v["alias"])))
    last = now - timedelta(days=7)
    prev = now - timedelta(days=14)
    pols_out = []
    for k, meta in CONFIG["politicos"].items():
        idx = [i for i, r in enumerate(conv) if k in r["pols"]]
        m = [conv[i] for i in idx]
        info = {"name": k, "espacio": meta.get("espacio", ""), "cargo": meta.get("cargo", ""), "foco": bool(meta.get("foco")),
                "alias": meta["alias"], "n": len(m)}
        if not m:
            pols_out.append(info)
            continue
        news = [r for r in m if r["kind"] == "news"]
        com = [r for r in m if r["kind"] == "comment"]
        wk = Counter(week(r["created_at"]) for r in m)
        wk_n = Counter(week(r["created_at"]) for r in news)
        tone_src = com if len(com) >= 15 else m

        def tone(rs):
            return {t: pct(sum(1 for r in rs if r["tono"] == t) / len(rs)) for t in ("NEG", "NEU", "POS")} if rs else None
        emo = [r["emocion"] for r in tone_src if r["emocion"] in EMOS]
        # Narrativas sin contar el propio nombre (si no, "Weretilneck" siempre cae en "Relación con la Provincia")
        own = POLS[k]
        narr_m = [[n for n, p in NARR.items() if p.search(" " + own.sub(" ", r["_f"]) + " ")] for r in m]
        narr = Counter(n for ns in narr_m for n in ns)
        nn = sum(1 for ns in narr_m if ns) or 1
        mine = Counter(w for i in idx for w in word_sets[i])
        negc = Counter(w for i in idx if conv[i]["tono"] == "NEG" for w in word_sets[i])
        nm, nall = len(idx), len(conv)
        lift = {w: (c / nm) / ((total_words[w] - c + 1) / max(nall - nm, 1)) for w, c in mine.items()}
        cloud = sorted(((w, c * min(lift[w], 4) ** 0.5) for w, c in mine.items() if c >= 3 and w not in alias_words),
                       key=lambda x: -x[1])[:60]
        co = Counter(p for r in m for p in r["pols"] if p != k)
        outlets = Counter(r.get("outlet") for r in news if r.get("outlet"))
        heads = sorted(news, key=lambda r: r["created_at"], reverse=True)[:12]
        l7 = sum(1 for r in m if r["created_at"] >= last.strftime("%Y-%m-%dT%H:%M:%SZ"))
        p7 = sum(1 for r in m if prev.strftime("%Y-%m-%dT%H:%M:%SZ") <= r["created_at"] < last.strftime("%Y-%m-%dT%H:%M:%SZ"))
        info.update({
            "n_news": len(news), "n_comments": len(com), "share": round(len(m) / total_m * 100, 1),
            "last7": l7, "prev7": p7, "delta": round((l7 - p7) / p7 * 100) if p7 >= 3 else None,
            "weekly": [wk.get(s, 0) for s in semanas], "weekly_news": [wk_n.get(s, 0) for s in semanas],
            "tone": tone(tone_src), "tone_base": "comentarios" if tone_src is com else "todos", "tone_news": tone(news),
            "tone_comments": tone(com),
            "emotions": {e: pct(emo.count(e) / len(emo)) for e in EMOS} if len(emo) >= 5 else None,
            "agresivo": pct(sum(r["agresivo"] for r in tone_src) / len(tone_src)),
            "narrativas": [{"n": a, "c": c, "pct": pct(c / nn)} for a, c in narr.most_common()],
            "cloud": [{"w": w, "n": mine[w], "s": round(v, 1), "neg": pct(negc[w] / mine[w])} for w, v in cloud],
            "co": [{"a": a, "n": c} for a, c in co.most_common(8)],
            "outlets": [{"o": o, "n": c} for o, c in outlets.most_common(10)],
            "temas_reclamo": Counter(t for r in m if r["reclamo"] for t in r["temas"]).most_common(5),
            "headlines": [{"t": r["title"], "o": r.get("outlet", ""), "u": r["url"], "d": r["created_at"][:10], "tono": r["tono"],
                           "narr": [n for n, p in NARR.items() if p.search(" " + own.sub(" ", r["_f"]) + " ")][:3]} for r in heads],
            "metodo_nlp": Counter(r["metodo_nlp"] for r in m).most_common(1)[0][0],
        })
        pols_out.append(info)

    # Narrativas de Soria por semana (para ver qué marco crece)
    foco_rows = [r for r in conv if FOCO in r["pols"]]
    narr_serie = {n: [0] * len(semanas) for n in CONFIG["narrativas"]}
    pos_w = {s: i for i, s in enumerate(semanas)}
    tone_w = {t: [0] * len(semanas) for t in ("NEG", "NEU", "POS")}
    for r in foco_rows:
        i = pos_w.get(week(r["created_at"]))
        if i is None:
            continue
        tone_w[r["tono"]][i] += 1
        for n in r["narr"]:
            narr_serie[n][i] += 1

    # ------------------------------------------------ radar vecinal
    locs, ejido, pts = build_geo()
    loc_rx = []
    for k, l in locs.items():
        loc_rx.append((k, rx_exact(l["alias"])))
    vec = [r for r in texts if CTX.search(r["_f"]) or (r["kind"] == "comment" and vctx.get(r.get("video_id")))]
    video_loc = {}
    for v, i in vinfo.items():
        f = fold(i.get("text", ""))
        video_loc[v] = [k for k, p in loc_rx if p.search(f)]
    for r in vec:
        found = [k for k, p in loc_rx if p.search(r["_f"])]
        inferred = False
        if not found and r["kind"] == "comment" and len(video_loc.get(r.get("video_id"), [])) == 1:
            found, inferred = video_loc[r["video_id"]], True
        r["loc"] = found[0] if len(found) == 1 else ("Varias" if found else "Sin barrio")
        r["loc_inferida"] = inferred
    reclamos = [r for r in vec if r["reclamo"]]
    temas = list(CONFIG["temas"])
    names = list(locs)
    loc_keys = names + ["Varias", "Sin barrio"]
    news_vec = [r for r in vec if r["kind"] == "news"]
    tema_tbl = []
    for t in temas:
        rv = [r for r in reclamos if t in r["temas"]]
        tema_tbl.append({"tema": t, "reclamos": len(rv), "vecinos": sum(1 for r in rv if r["kind"] == "comment"),
                         "medios_reclamo": sum(1 for r in rv if r["kind"] == "news"),
                         "agenda_medios": sum(1 for r in news_vec if t in r["temas"]),
                         "apoyo": sum(int(r.get("engagement") or 0) for r in rv)})
    tema_tbl.sort(key=lambda x: -x["reclamos"])
    matriz = {l: {t: 0 for t in temas} for l in loc_keys}
    for r in reclamos:
        for t in r["temas"]:
            matriz[r["loc"]][t] += 1
    serie = defaultdict(Counter)
    for r in reclamos:
        for t in r["temas"]:
            serie[week(r["created_at"])][t] += 1
    sem_v = sorted(serie)
    locs_out = []
    for k, l in locs.items():
        rv = [r for r in reclamos if r["loc"] == k]
        men = [r for r in vec if r["loc"] == k]
        if l.get("osm_extra") and not men:
            continue  # lugares de OSM que nadie nombra: no ensuciar la lista
        poly = l.get("poligono") or []
        locs_out.append({"nombre": k, "centro": l.get("centro"), "fuente_geo": l.get("fuente_geo"), "osm_extra": bool(l.get("osm_extra")),
                         "poligono": [simplify(rg, 0.0002) for rg in poly],
                         "area_km2": round(sum(area_km2(rg) for rg in poly), 2) if poly else None,
                         "reclamos": len(rv), "inferidos": sum(1 for r in rv if r["loc_inferida"]), "menciones": len(men),
                         "tono_neg": pct(sum(1 for r in men if r["tono"] == "NEG") / len(men)) if len(men) >= 5 else None,
                         "tema_top": Counter(t for r in rv for t in r["temas"]).most_common(3)})
    kept = {l["nombre"] for l in locs_out}
    loc_keys = [l for l in loc_keys if l in kept or l in ("Varias", "Sin barrio")]
    vec_com = [r for r in reclamos if r["kind"] == "comment"]
    ejemplos = []
    for t in temas:
        pool = sorted([r for r in reclamos if t in r["temas"] and r["kind"] == "news"], key=lambda r: r["created_at"], reverse=True)
        for r in pool[:10]:
            if any(e["url"] == r.get("url") for e in ejemplos):
                continue
            ejemplos.append({"tema": t, "temas": r["temas"], "localidad": r["loc"], "fuente": r.get("outlet") or "Medio",
                             "fecha": r["created_at"][:10], "texto": excerpt(r.get("title") or r["text"]), "url": r.get("url", "")})
    videos = Counter(r["video_id"] for r in reclamos if r["kind"] == "comment")
    top_videos = [{"titulo": vinfo[v]["title"], "canal": vinfo[v]["channel"], "fecha": vinfo[v]["created_at"][:10], "url": vinfo[v]["url"],
                   "reclamos": n, "comentarios": sum(1 for r in vec if r["kind"] == "comment" and r.get("video_id") == v)}
                  for v, n in videos.most_common(12) if v in vinfo]
    soria_videos = Counter(r["video_id"] for r in texts if r["kind"] == "comment" and FOCO in r["pols"])
    top_soria_videos = [{"titulo": vinfo[v]["title"], "canal": vinfo[v]["channel"], "fecha": vinfo[v]["created_at"][:10], "url": vinfo[v]["url"],
                         "comentarios": n,
                         "neg": pct(sum(1 for r in texts if r.get("video_id") == v and r["kind"] == "comment" and r["tono"] == "NEG") / n)}
                        for v, n in soria_videos.most_common(10) if v in vinfo]
    titulares = sorted(news_vec, key=lambda r: r["created_at"], reverse=True)[:100]
    titulares = [{"titulo": r["title"], "medio": r.get("outlet", ""), "fecha": r["created_at"][:10], "url": r["url"], "temas": r["temas"],
                  "localidad": r["loc"], "reclamo": r["reclamo"], "pols": r["pols"], "tono": r["tono"]} for r in titulares]

    # ------------------------------------------------ intendentes de la región (comparación de visibilidad)
    conv_all = [r for r in texts if r["created_at"] >= conv_since]
    intend_out = []
    for k, meta in CONFIG.get("intendentes", {}).items():
        m = [r for r in conv_all if (FOCO in r["pols"] if meta.get("foco") else INTEND[k].search(r["_f"]))]
        news = [r for r in m if r["kind"] == "news"]
        wk = Counter(week(r["created_at"]) for r in m)
        l7 = sum(1 for r in m if r["created_at"] >= last.strftime("%Y-%m-%dT%H:%M:%SZ"))
        intend_out.append({
            "name": k, "ciudad": meta.get("ciudad", ""), "espacio": meta.get("espacio", ""), "foco": bool(meta.get("foco")),
            "n": len(m), "n_news": len(news), "last7": l7, "weekly": [wk.get(x, 0) for x in semanas],
            "medios": len({r.get("outlet") for r in news if r.get("outlet")}),
            "tone": {t: pct(sum(1 for r in m if r["tono"] == t) / len(m)) for t in ("NEG", "NEU", "POS")} if m else None,
            "temas": Counter(t for r in m for t in r["temas"]).most_common(4),
            "titular": next(({"t": r["title"], "o": r.get("outlet", ""), "u": r["url"], "d": r["created_at"][:10]}
                             for r in sorted(news, key=lambda r: r["created_at"], reverse=True)), None),
        })

    # ------------------------------------------------ hitos (semanas pico) y alertas
    foco_info = next((p for p in pols_out if p["foco"]), {})
    fw = foco_info.get("weekly") or [0] * len(semanas)
    hitos = []
    if any(fw):
        nz = [v for v in fw if v] or [0]
        mu = sum(nz) / len(nz)
        sd = (sum((v - mu) ** 2 for v in nz) / len(nz)) ** 0.5
        thr = max(3, mu + 0.5 * sd)
        for i, v in enumerate(fw):
            if v < thr:
                continue
            wrows = [r for r in foco_rows if week(r["created_at"]) == semanas[i]]
            wnews = [r for r in wrows if r["kind"] == "news"]
            # titular representativo: el que comparte más palabras con el resto de la semana
            wsets = [set(WORD.findall(r["_f"])) - STOP for r in wnews]
            best = max(range(len(wnews)), key=lambda j: sum(len(wsets[j] & o) for o in wsets), default=None)
            nar = Counter(n for r in wrows for n in r["narr"]).most_common(2)
            hitos.append({"semana": semanas[i], "n": v, "neg": pct(sum(1 for r in wrows if r["tono"] == "NEG") / len(wrows)) if wrows else None,
                          "narrativas": [n for n, _ in nar],
                          "titular": ({"t": wnews[best]["title"], "o": wnews[best].get("outlet", ""), "u": wnews[best]["url"]}
                                      if best is not None else None)})
        hitos = sorted(sorted(hitos, key=lambda h: -h["n"])[:8], key=lambda h: h["semana"])

    def share_neg(rows):
        return sum(1 for r in rows if r["tono"] == "NEG") / len(rows) if rows else None
    alertas = []
    d = foco_info.get("delta")
    if d is not None and abs(d) >= 30:
        alertas.append({"tipo": "volumen", "dir": "up" if d > 0 else "down",
                        "texto": f"Las menciones de {FOCO} {'subieron' if d > 0 else 'bajaron'} {abs(d)}% esta semana ({foco_info['last7']} vs. {foco_info['prev7']})."})
    cut4 = (now - timedelta(days=28)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cut12 = (now - timedelta(days=84)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rec, base_r = [r for r in foco_rows if r["created_at"] >= cut4], [r for r in foco_rows if cut12 <= r["created_at"] < cut4]
    if len(rec) >= 8 and len(base_r) >= 8:
        a, b = share_neg(rec), share_neg(base_r)
        if abs(a - b) >= 0.08:
            alertas.append({"tipo": "tono", "dir": "up" if a > b else "down",
                            "texto": f"El tono negativo sobre {FOCO} {'subió' if a > b else 'bajó'} de {pct(b)}% a {pct(a)}% en las últimas 4 semanas."})
        nr, nb = Counter(n for r in rec for n in r["narr"]), Counter(n for r in base_r for n in r["narr"])
        grow = sorted(((n, c / len(rec) - nb[n] / len(base_r)) for n, c in nr.items() if c >= 3), key=lambda x: -x[1])
        if grow and grow[0][1] >= 0.08:
            alertas.append({"tipo": "narrativa", "dir": "up",
                            "texto": f"Gana peso la narrativa «{grow[0][0]}»: {pct(nr[grow[0][0]] / len(rec))}% de los textos recientes vs. {pct(nb[grow[0][0]] / len(base_r))}% antes."})
    riv = sorted((p for p in pols_out if not p["foco"] and p.get("delta") is not None and p.get("last7", 0) >= 5), key=lambda p: -p["delta"])
    if riv and riv[0]["delta"] >= 50:
        alertas.append({"tipo": "competidor", "dir": "up",
                        "texto": f"{riv[0]['name']} crece {riv[0]['delta']}% en menciones esta semana ({riv[0]['last7']} textos)."})
    rec_v = [r for r in reclamos if r["created_at"] >= cut4]
    old_v = [r for r in reclamos if cut12 <= r["created_at"] < cut4]
    if len(rec_v) >= 6:
        cr, co_ = Counter(t for r in rec_v for t in r["temas"]), Counter(t for r in old_v for t in r["temas"])
        t, c = cr.most_common(1)[0]
        alertas.append({"tipo": "reclamo", "dir": "up" if c / len(rec_v) > (co_[t] / len(old_v) if old_v else 0) else "flat",
                        "texto": f"Reclamo más repetido del último mes: {t} ({c} de {len(rec_v)} reclamos)."})
    co_s = Counter(p for r in rec for p in r["pols"] if p != FOCO)
    if co_s:
        p_, c = co_s.most_common(1)[0]
        alertas.append({"tipo": "cruce", "dir": "flat", "texto": f"En el último mes aparece junto a {p_} en {c} textos."})

    # ------------------------------------------------ medios: tono por medio y matriz medio × político
    foco_news = [r for r in foco_rows if r["kind"] == "news"]
    by_out = defaultdict(list)
    for r in foco_news:
        if r.get("outlet"):
            by_out[r["outlet"]].append(r)
    medios_tono = sorted(({"medio": o, "n": len(rs), "neg": pct(share_neg(rs)), "pos": pct(sum(1 for r in rs if r["tono"] == "POS") / len(rs))}
                          for o, rs in by_out.items() if len(rs) >= 2), key=lambda x: -x["n"])[:16]
    conv_news = [r for r in conv if r["kind"] == "news" and r.get("outlet")]
    top_out = [o for o, _ in Counter(r["outlet"] for r in conv_news).most_common(14)]
    top_pol = [p["name"] for p in sorted(pols_out, key=lambda p: -p["n"]) if p["n"]][:9]
    mm = Counter((r["outlet"], p) for r in conv_news for p in r["pols"])
    medios_matriz = {"medios": top_out, "politicos": top_pol, "valores": [[mm[(o, p)] for p in top_pol] for o in top_out]}

    # ------------------------------------------------ Wikipedia: interés de búsqueda y ficha del municipio
    wiki_out = None
    if WIKI.exists():
        W = json.loads(WIKI.read_text(encoding="utf8"))
        wsem = semanas
        series, tot90 = {}, {}
        c90 = (now - timedelta(days=90)).strftime("%Y%m%d")
        for k, v in W.get("personas", {}).items():
            vw = v.get("vistas") or {}
            if not vw:
                continue
            wc = Counter()
            for dd, n in vw.items():
                wc[week(f"{dd[:4]}-{dd[4:6]}-{dd[6:]}T00:00:00Z")] += n
            series[k] = [wc.get(x, 0) for x in wsem]
            tot90[k] = sum(n for dd, n in vw.items() if dd >= c90)
        fp = W.get("personas", {}).get(FOCO) or {}
        wiki_out = {"semanas": wsem, "series": series, "total_90": tot90,
                    "articulos": {k: v.get("url") for k, v in W.get("personas", {}).items()},
                    "perfil": {"extract": fp.get("extract"), "url": fp.get("url")} if fp else None,
                    "municipio": W.get("municipio"), "fetched_at": W.get("fetched_at")}

    status = json.loads(STATUS.read_text(encoding="utf8")) if STATUS.exists() else {}
    news_all = [r for r in texts if r["kind"] == "news"]
    out = {
        "updated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "municipio": CONFIG["municipio"], "provincia": CONFIG["provincia"],
        "foco": FOCO, "window_days": CONFIG["window_days"], "conversacion_dias": CONFIG["conversacion_dias"], "status": status,
        "totales": {"textos": len(texts), "comentarios": sum(1 for r in texts if r["kind"] == "comment"), "videos": len(vinfo),
                    "noticias": len(news_all), "medios": len({r.get("outlet") for r in news_all if r.get("outlet")}),
                    "menciones_politicas": sum(len(r["pols"]) for r in conv), "menciones_foco": len(foco_rows),
                    "vecinales": len(vec), "reclamos": len(reclamos),
                    "reclamos_con_barrio": sum(1 for r in reclamos if r["loc"] in kept),
                    "metodo_nlp": Counter(r["metodo_nlp"] for r in texts).most_common(1)[0][0] if texts else "lexico"},
        "semanas": semanas,
        "politicos": pols_out,
        "foco_semanal": {"tono": tone_w, "narrativas": narr_serie},
        "foco_videos": top_soria_videos,
        "cubo": CONFIG["posiciones"],
        "intendentes": intend_out, "hitos": hitos, "alertas": alertas,
        "medios_tono": medios_tono, "medios_matriz": medios_matriz, "wiki": wiki_out,
        "vecinal": {
            "temas": tema_tbl,
            "matriz": {"localidades": loc_keys, "temas": temas, "valores": [[matriz[l][t] for t in temas] for l in loc_keys]},
            "serie": {"semanas": sem_v, "temas": {t: [serie[w][t] for w in sem_v] for t in temas}},
            "localidades": locs_out, "ejido_poligono": [simplify(rg) for rg in ejido], "centro": CONFIG["centro"],
            "equipamiento_puntos": pts, "ejemplos": ejemplos,
            "frases_tema": {t: frases([r for r in vec_com if t in r["temas"]]) for t in temas},
            "frases_localidad": {l: frases([r for r in vec_com if r["loc"] == l]) for l in kept},
            "videos": top_videos, "titulares": titulares,
        },
        "metodo": {
            "temas": CONFIG["temas"], "narrativas": CONFIG["narrativas"],
            "politicos": {k: v["alias"] for k, v in CONFIG["politicos"].items()},
            "regla": "Un comentario es reclamo si menciona al menos un tema y no es claramente elogioso (tiene un marcador de queja o no más términos positivos que negativos). Una nota de medio es reclamo si menciona un tema y tiene un marcador de queja o tono negativo.",
            "localidad": "Se busca el nombre del barrio o localidad del ejido (lista propia más los lugares con nombre de OpenStreetMap, exigiendo 'barrio X' para nombres ambiguos). Si un comentario no nombra ninguno, hereda el del video cuando el video nombra uno solo (se marca como inferido).",
            "tono": "Tono, emoción y agresividad con pysentimiento (modelos entrenados con tuits en español) cuando corre en GitHub Actions; si no, diccionarios. Es el tono del texto que menciona al político, no necesariamente la postura hacia él.",
            "menciones": "Un texto menciona a un político si contiene alguno de sus alias. Los comentarios de un video sobre un único político se le atribuyen aunque no lo nombren (inferido).",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf8")
    print(json.dumps(out["totales"], ensure_ascii=False))


if __name__ == "__main__":
    main()
