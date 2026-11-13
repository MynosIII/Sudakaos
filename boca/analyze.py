"""Agrega el almacén de Boca en boca/data/boca.json (lo que se publica) y boca/data/textos.json.

Bloques:
  - Figuras: menciones de Riquelme, la dirigencia, la oposición, el fútbol y referentes externos; tono/emoción/
    agresividad (pysentimiento si está instalado, si no diccionarios: ver radar/nlp.py), narrativas, nube de palabras,
    co-menciones, medios y balance apoyo/crítica en comentarios.
  - Voz de la gente: qué QUIERE, qué ESPERA, qué CRITICA y qué APOYA la gente en comentarios de YouTube,
    por tema (plantel, DT, estadio, elecciones, SAD…), con pedidos y frases repetidas.
  - Hacia 2027: conversación sobre las elecciones del club y peso de cada figura.
  - Aspirante: una figura que busca un rol (Walter Klix como posible vice): cuánto se lo asocia al rol, encuadres,
    con quién se lo nombra y cómo está frente al resto de la oposición (config "aspirante").
  - Mapa de poder: posición editorial de cada figura + volumen y balance medidos.

Textos publicados: titulares de medios y, de los comentarios, un extracto sin autor con link al original
(config "textos_comentarios": "extracto"). Usuarios, correos y teléfonos se enmascaran.
"""
from __future__ import annotations

import json
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
STATUS = HERE / ".store" / "status.json"
WIKI = HERE / ".store" / "wiki.json"
NLP_CACHE = HERE / ".store" / "nlp.jsonl.gz"
OUT = HERE / "data" / "boca.json"
TEXTOS = HERE / "data" / "textos.json"
FOCO = CONFIG["foco"]
INTS = ["quiere", "espera", "critica", "apoya"]
STOP = set("""que los las del por con una para como mas pero sus les este esta esto eso esa son hay fue ser muy todo todos
todas nos ese hace hacer sin sobre entre cuando donde porque tambien solo ya asi aca alli ahi tiene tienen estan esta
era han cada otro otra otros nada algo uno dos tan bien mal quien cual desde hasta hoy aqui ver van vez fueron
sera seria puede pueden tras ante segun durante anos ano dia dias semana mes meses parte hacia luego antes despues
the and you jaja jajaja jajajaja jajajajaja gente video videos nota notas diario noticias noticia leer fue sido estar
estuvo dijo afirmo aseguro senalo sostuvo explico ademas mientras sino aunque mismo misma quienes cuales eso esos
boca juniors club xeneize vos sos tenes son asi pero porque igual siempre nunca todo nada tambien ese esa eso los las
cuando como mas menos hay ahora despues bueno buena tipo dale che vaya vayan sea""".split())
WORD = re.compile(r"[a-zñ]{4,}")


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def rx(terms):
    """Prefijo para raíces largas ('clasific' → clasificó); palabra exacta para términos de ≤4 letras ('afa', 'var')."""
    terms = sorted({fold(t) for t in terms}, key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(re.escape(t) + (r"\b" if len(t) <= 4 else "") for t in terms) + ")", re.I)


def rx_exact(terms):
    terms = sorted({fold(t) for t in terms}, key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(re.escape(t) for t in terms) + r")\b", re.I)


FIG = CONFIG["figuras"]
POLS = {k: rx_exact(v["alias"]) for k, v in FIG.items()}
TEMAS = {k: rx(v) for k, v in CONFIG["temas"].items()}
NARR = {k: rx(v) for k, v in CONFIG["narrativas"].items()}
INT_RX = {k: rx(v) for k, v in CONFIG["intenciones"].items()}
POS, NEG = rx(CONFIG["positivo"]), rx(CONFIG["negativo"])
CTX = rx(CONFIG["contexto"] + [a for v in FIG.values() for a in v["alias"] if len(a) > 6])
SHOW_COMMENTS = CONFIG.get("textos_comentarios") == "extracto"
MASK = [(re.compile(r"@[\w.\-]{2,}"), "@…"), (re.compile(r"\S+@\S+\.\w+"), "[correo]"),
        (re.compile(r"(?:\+?54)?[\s\-]?\d{3,4}[\s\-]?\d{6,7}\b"), "[tel]")]
EMOS = ["ira", "miedo", "tristeza", "alegria", "asco", "sorpresa"]
# Pedidos y deseos: categoría del disparador + la palabra que sigue (saltando artículos): «Que se vaya: vasco», «Que traigan: 9»
PED_CAT = [
    ("Que se vaya", r"que se vayan?|se tienen? que ir|que renuncien?|fuera|saquen|saquenlo|echen|rajen"),
    ("Que traigan", r"traigan|compren|contraten"),
    ("Queremos", r"queremos|quiero|necesitamos|necesita|hace falta|nos falta|falta un|falta una"),
    ("Que vuelva", r"que vuelvan?|volve|vuelva"),
    ("Que juegue", r"que juegue|que jueguen|pongan a|pongan al|que pongan|denle"),
    ("Hay que", r"hay que|pedimos|exigimos"),
]
DES_CAT = [("Ojalá", r"ojala|ojala que"), ("Espero", r"espero que|esperemos que|espero"), ("A ver si", r"a ver si"),
           ("Tengo fe en", r"tengo fe en|tengo fe que|confio en|confiamos en"), ("Se viene", r"se viene|se vienen")]
ART = set("el la los las un una unos unas al a de del lo le les que se nos me te mi su".split())
CUT = set("de la el los las y o a en que con por para un una al del se le lo me te mas muy ya no si es".split())


def pct(x):
    return round(100 * x, 1)


def excerpt(text: str, n=240) -> str:
    for r, rep in MASK:
        text = r.sub(rep, text)
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"


def week(s):
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return (d - timedelta(days=d.weekday())).strftime("%Y-%m-%d")


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


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


def toks(r):
    return [w for w in re.findall(r"[a-zñ]{3,}", r["_f"]) if w not in STOP]


def frases(rs, n=16, extra_stop=()):
    c = Counter()
    for r in rs:
        t = [w for w in toks(r) if w not in extra_stop]
        c.update(set(t) | {a + " " + b for a, b in zip(t, t[1:])})
    out = [(g, k) for g, k in c.most_common(400) if k >= 3 and (" " in g or k >= 5)]
    bi = [x for x in out if " " in x[0]][: n // 2 + 2]
    uni = [x for x in out if " " not in x[0]][: n - len(bi)]
    return sorted(bi + uni, key=lambda x: -x[1])


INT_WORDS = {k: set(re.findall(r"[a-zñ]{3,}", fold(" ".join(v)))) for k, v in CONFIG["intenciones"].items()}
NAME_WORDS = set(re.findall(r"[a-zñ]{3,}", fold(" ".join(a for v in FIG.values() for a in v["alias"]))))


def trim(words):
    w = words.split()
    while w and w[-1] in CUT:
        w.pop()
    return " ".join(w)


PED_RX = [(n, re.compile(r"\b(?:" + t + r")\b((?: [a-zñ0-9]+){1,4})")) for n, t in PED_CAT]
DES_RX = [(n, re.compile(r"\b(?:" + t + r")\b((?: [a-zñ0-9]+){1,4})")) for n, t in DES_CAT]
VERBOS_VACIOS = set("ser estar hacer tener haber ir ver poder dar mucho muchos mucha poco buscar traer poner sacar cambiar seguir "
                    "mas ahora ya todo todos nada algo alguien".split())
# palabra suelta → figura ("mauricio" en «que vuelva Mauricio» es Macri)
OBJ_FIG = {"riquelme": "Riquelme", "roman": "Riquelme", "macri": "Macri", "mauricio": "Macri", "vasco": "Arruabarrena",
           "arruabarrena": "Arruabarrena", "ibarra": "Ibarra", "angelici": "Angelici", "tano": "Angelici", "ameal": "Ameal",
           "beraldi": "Beraldi", "paredes": "Paredes", "tapia": "Tapia", "chiqui": "Tapia", "milei": "Milei", "pergolini": "Pergolini"}


def pedidos(rs, cats, n=24):
    """Pedidos/deseos repetidos: «Que se vaya: vasco», «Que traigan: nueve», «Ojalá: libertadores» (≥3 comentarios)."""
    c, ids = Counter(), defaultdict(list)
    for r in rs:
        t = re.sub(r"[^a-zñ0-9 ]+", " | ", r["_f"])
        seen = set()
        for name, rgx in cats:
            for m in rgx.finditer(t):
                obj = next((w for w in m.group(1).split() if w not in ART and w not in VERBOS_VACIOS), None)
                if not obj or obj in STOP or obj in CUT or len(obj) < 2:
                    continue
                obj = OBJ_FIG.get(obj, obj)
                k = f"{name}: {obj}"
                if k not in seen:
                    seen.add(k)
                    c[k] += 1
                    ids[k].append(r["id"])
    return [{"p": k, "n": v, "_rid": ids[k]} for k, v in c.most_common(n) if v >= 3]


def tone(rs):
    return {t: pct(sum(1 for r in rs if r["tono"] == t) / len(rs)) for t in ("NEG", "NEU", "POS")} if rs else None


def intents(rs):
    if not rs:
        return None
    return {k: pct(sum(1 for r in rs if k in r["int"]) / len(rs)) for k in INTS}


def balance(rs):
    a, c = sum(1 for r in rs if "apoya" in r["int"]), sum(1 for r in rs if "critica" in r["int"])
    return round(100 * (a - c) / (a + c)) if a + c >= 5 else None


def main():
    now = datetime.now(timezone.utc)
    since = iso(now - timedelta(days=CONFIG["window_days"]))
    items = [i for i in load_items() if i.get("created_at", "") >= since]
    raw = items
    seen, dedup = set(), []
    for i in sorted(items, key=lambda x: x.get("query") == "rss"):
        key = (i["kind"], fold(i.get("title") or i.get("text", ""))[:120]) if i["kind"] == "news" else (i["kind"], i["id"])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(i)
    items = dedup
    # Aspirante: muchos titulares sobre él no dicen su nombre ("un funcionario de Bullrich denunció a Riquelme").
    # Las notas que trajeron sus búsquedas propias (aspirante.atribuir_queries) se le atribuyen igual.
    ASP = CONFIG.get("aspirante") or {}
    asp_q = set(ASP.get("atribuir_queries", []))
    asp_titles = {fold(i.get("title") or i.get("text", ""))[:120] for i in raw
                  if i["kind"] == "news" and asp_q & set(i.get("queries") or [i.get("query")])}
    vinfo = {i["video_id"]: i for i in items if i["kind"] == "video"}
    texts = [i for i in items if i["kind"] != "video"]
    # Notas: solo las que hablan de Boca o de alguna figura (Google News trae ruido con apellidos comunes)
    texts = [r for r in texts if r["kind"] == "comment" or CTX.search(fold(r.get("text", "")))]
    label_tone(texts)

    for r in texts:
        t = fold(re.sub(r"@[\w.\-]+", " ", r.get("text", "")))
        r["_f"] = t
        r["pols"] = [k for k, p in POLS.items() if p.search(t)]
        r["narr"] = [k for k, p in NARR.items() if p.search(t)]
        r["temas"] = [k for k, p in TEMAS.items() if p.search(t)]
        hits = {k for k, p in INT_RX.items() if p.search(t)}
        if r["kind"] == "comment":
            pos, neg = len(POS.findall(t)), len(NEG.findall(t))
            if "critica" not in hits and r["tono"] == "NEG" and "apoya" not in hits and neg >= pos:
                hits.add("critica")
            if "apoya" not in hits and r["tono"] == "POS" and "critica" not in hits and pos >= neg:
                hits.add("apoya")
            if "critica" in hits and "apoya" in hits:  # el tono desempata
                hits.discard("apoya" if r["tono"] == "NEG" else "critica" if r["tono"] == "POS" else "")
        r["int"] = sorted(hits) if r["kind"] == "comment" else []
    if ASP.get("figura") in FIG:
        ka, pa = ASP["figura"], POLS[ASP["figura"]]
        asp_vid = {v for v, i in vinfo.items() if pa.search(fold(i.get("text", "")))}
        for r in texts:
            if ka in r["pols"]:
                continue
            if (r["kind"] == "news" and fold(r.get("title") or r.get("text", ""))[:120] in asp_titles) or \
               (r["kind"] == "comment" and r.get("video_id") in asp_vid):
                r["pols"].append(ka)
                r["pol_inferido"] = True
    # Comentarios heredan la figura del video cuando el video es sobre una sola
    vpols = {v: [k for k, p in POLS.items() if p.search(fold(i.get("text", "")))] for v, i in vinfo.items()}
    vtem = {v: [k for k, p in TEMAS.items() if p.search(fold(i.get("text", "")))] for v, i in vinfo.items()}
    for r in texts:
        if r["kind"] == "comment":
            if not r["pols"] and len(vpols.get(r.get("video_id"), [])) == 1:
                r["pols"] = list(vpols[r["video_id"]])
                r["pol_inferido"] = True
            if not r["temas"] and len(vtem.get(r.get("video_id"), [])) == 1:
                r["temas"] = list(vtem[r["video_id"]])
                r["tema_inferido"] = True

    conv_since = iso(now - timedelta(days=CONFIG["conversacion_dias"]))
    recent = [r for r in texts if r["created_at"] >= conv_since]
    conv = [r for r in recent if r["pols"]]
    coms = [r for r in recent if r["kind"] == "comment"]
    semanas, w = [], datetime.fromisoformat(week(conv_since))
    while w <= now.replace(tzinfo=None):
        semanas.append(w.strftime("%Y-%m-%d"))
        w += timedelta(days=7)
    wpos = {s: i for i, s in enumerate(semanas)}
    last, prev = iso(now - timedelta(days=7)), iso(now - timedelta(days=14))

    # ------------------------------------------------ figuras
    total_m = sum(len(r["pols"]) for r in conv) or 1
    word_sets = [set(w for w in WORD.findall(r["_f"]) if w not in STOP) for r in conv]
    total_words = Counter(w for ws in word_sets for w in ws)
    alias_words = set(WORD.findall(" ".join(fold(a) + " " + fold(k) for k, v in FIG.items() for a in v["alias"])))
    figs = []
    for k, meta in FIG.items():
        idx = [i for i, r in enumerate(conv) if k in r["pols"]]
        m = [conv[i] for i in idx]
        info = {"name": k, "bando": meta.get("bando", ""), "espacio": meta.get("bando", ""), "cargo": meta.get("cargo", ""),
                "foco": bool(meta.get("foco")), "alias": meta["alias"], "n": len(m)}
        if not m:
            figs.append(info)
            continue
        news = [r for r in m if r["kind"] == "news"]
        com = [r for r in m if r["kind"] == "comment"]
        wk, wk_n = Counter(week(r["created_at"]) for r in m), Counter(week(r["created_at"]) for r in news)
        tone_src = com if len(com) >= 15 else m
        emo = [r["emocion"] for r in tone_src if r["emocion"] in EMOS]
        own = POLS[k]
        narr_m = [[n for n, p in NARR.items() if p.search(own.sub(" ", r["_f"]))] for r in m]
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
        l7 = sum(1 for r in m if r["created_at"] >= last)
        p7 = sum(1 for r in m if prev <= r["created_at"] < last)
        stop_own = set(WORD.findall(" ".join(fold(a) for a in meta["alias"]) + " " + fold(k)))
        info.update({
            "n_news": len(news), "n_comments": len(com), "share": round(len(m) / total_m * 100, 1),
            "last7": l7, "prev7": p7, "delta": round((l7 - p7) / p7 * 100) if p7 >= 3 else None,
            "weekly": [wk.get(s, 0) for s in semanas], "weekly_news": [wk_n.get(s, 0) for s in semanas],
            "tone": tone(tone_src), "tone_base": "comentarios" if tone_src is com else "todos",
            "tone_news": tone(news), "tone_comments": tone(com),
            "emotions": {e: pct(emo.count(e) / len(emo)) for e in EMOS} if len(emo) >= 5 else None,
            "agresivo": pct(sum(r["agresivo"] for r in tone_src) / len(tone_src)),
            "intenciones": intents(com) if len(com) >= 5 else None, "balance": balance(com),
            "narrativas": [{"n": a, "c": c, "pct": pct(c / nn)} for a, c in narr.most_common()],
            "temas": Counter(t for r in m for t in r["temas"]).most_common(6),
            "cloud": [{"w": w, "n": mine[w], "s": round(v, 1), "neg": pct(negc[w] / mine[w]),
                       "_rid": [conv[i]["id"] for i in idx if w in word_sets[i]]} for w, v in cloud],
            "frases_critica": frases([r for r in com if "critica" in r["int"]], 12, stop_own),
            "frases_apoya": frases([r for r in com if "apoya" in r["int"]], 12, stop_own),
            "co": [{"a": a, "n": c} for a, c in co.most_common(8)],
            "outlets": [{"o": o, "n": c} for o, c in outlets.most_common(10)],
            "headlines": [{"t": r["title"], "o": r.get("outlet", ""), "u": r["url"], "d": r["created_at"][:10], "tono": r["tono"],
                           "narr": [n for n, p in NARR.items() if p.search(own.sub(" ", r["_f"]))][:3]} for r in heads],
            "metodo_nlp": Counter(r["metodo_nlp"] for r in m).most_common(1)[0][0],
        })
        figs.append(info)

    foco_rows = [r for r in conv if FOCO in r["pols"]]
    foco_w = {t: [0] * len(semanas) for t in ("NEG", "NEU", "POS")}
    foco_int = {k: [0] * len(semanas) for k in INTS}
    foco_narr = {n: [0] * len(semanas) for n in CONFIG["narrativas"]}
    for r in foco_rows:
        i = wpos.get(week(r["created_at"]))
        if i is None:
            continue
        foco_w[r["tono"]][i] += 1
        for k in r["int"]:
            foco_int[k][i] += 1
        for n in r["narr"]:
            foco_narr[n][i] += 1
    foco_bal = []
    for i in range(len(semanas)):
        a, c = foco_int["apoya"][i], foco_int["critica"][i]
        foco_bal.append(round(100 * (a - c) / (a + c)) if a + c >= 5 else None)

    # ------------------------------------------------ voz de la gente
    temas = list(CONFIG["temas"])
    int_w = {k: [0] * len(semanas) for k in INTS}
    for r in coms:
        i = wpos.get(week(r["created_at"]))
        if i is not None:
            for k in r["int"]:
                int_w[k][i] += 1
    tema_out = []
    for t in temas:
        rs = [r for r in recent if t in r["temas"]]
        rc = [r for r in rs if r["kind"] == "comment"]
        wk = Counter(week(r["created_at"]) for r in rs)
        l28 = sum(1 for r in rs if r["created_at"] >= iso(now - timedelta(days=28)))
        p28 = sum(1 for r in rs if iso(now - timedelta(days=56)) <= r["created_at"] < iso(now - timedelta(days=28)))
        tema_out.append({
            "tema": t, "n": len(rs), "comentarios": len(rc), "notas": len(rs) - len(rc),
            "intenciones": intents(rc), "balance": balance(rc), "tono": tone(rc or rs),
            "apoyo_likes": sum(int(r.get("engagement") or 0) for r in rc),
            "weekly": [wk.get(s, 0) for s in semanas], "last28": l28, "prev28": p28,
            "figuras": Counter(p for r in rs for p in r["pols"]).most_common(5),
            "frases": frases(rc, 14),
            "pedidos": pedidos(rc, PED_RX, 8),
        })
    tema_out.sort(key=lambda x: -x["n"])
    voz = {
        "comentarios": len(coms),
        "con_intencion": sum(1 for r in coms if r["int"]),
        "intenciones": {k: sum(1 for r in coms if k in r["int"]) for k in INTS},
        "semanal": int_w,
        "matriz": {"temas": temas, "valores": [[sum(1 for r in coms if t in r["temas"] and k in r["int"]) for k in INTS] for t in temas]},
        "pedidos": pedidos(coms, PED_RX, 30),
        "deseos": pedidos(coms, DES_RX, 24),
        "frases": {k: frases([r for r in coms if k in r["int"]], 18, INT_WORDS[k] | NAME_WORDS) for k in INTS},
        "temas": tema_out,
    }

    # ------------------------------------------------ hacia 2027
    EL = "Elecciones 2027 y oposición"
    el_rows = [r for r in recent if EL in r["temas"]]
    el_figs = Counter(p for r in el_rows for p in r["pols"])
    el_wk = Counter(week(r["created_at"]) for r in el_rows)
    el_date = datetime.fromisoformat(CONFIG["eleccion"]).replace(tzinfo=timezone.utc)
    el_heads = sorted([r for r in el_rows if r["kind"] == "news"], key=lambda r: r["created_at"], reverse=True)[:40]
    el_com = [r for r in el_rows if r["kind"] == "comment"]
    elecciones = {
        "fecha": CONFIG["eleccion"], "dias": (el_date - now).days, "n": len(el_rows), "comentarios": len(el_com),
        "weekly": [el_wk.get(s, 0) for s in semanas],
        "figuras": [{"name": k, "n": c, "bando": FIG[k].get("bando", ""),
                     "tono": tone([r for r in el_rows if k in r["pols"]]),
                     "balance": balance([r for r in el_com if k in r["pols"]])} for k, c in el_figs.most_common(12)],
        "bandos": Counter(FIG[p].get("bando", "") for r in el_rows for p in r["pols"]).most_common(),
        "intenciones": intents(el_com) if el_com else None,
        "frases": frases(el_com, 16), "pedidos": pedidos(el_com, PED_RX, 10),
        "titulares": [{"t": r["title"], "o": r.get("outlet", ""), "u": r["url"], "d": r["created_at"][:10], "tono": r["tono"],
                       "pols": r["pols"]} for r in el_heads],
    }

    # ------------------------------------------------ mapa de poder
    MP = CONFIG["mapa_poder"]
    fby = {f["name"]: f for f in figs}
    mapa = {"metodo": MP["metodo"], "puntos": [dict(name=k, **v, n=fby.get(k, {}).get("n", 0), bando=FIG[k].get("bando", ""),
                                                      balance=fby.get(k, {}).get("balance"),
                                                      neg=(fby.get(k, {}).get("tone") or {}).get("NEG")) for k, v in MP["puntos"].items()]}

    # ------------------------------------------------ aspirante (p. ej. Walter Klix como posible vice)
    # Ventana propia (config aspirante.dias, por defecto la de almacenamiento): una figura chica tiene pocas
    # menciones y con 180 días puede quedar en cero aunque haya sido noticia hace unos meses.
    aspirante, asp_rows = None, []
    AS = CONFIG.get("aspirante")
    if AS and AS["figura"] in FIG:
        k = AS["figura"]
        a_days = AS.get("dias", CONFIG["window_days"])
        a_since = iso(now - timedelta(days=a_days))
        abase = [r for r in texts if r["created_at"] >= a_since]
        a_sem, w = [], datetime.fromisoformat(week(a_since))
        while w <= now.replace(tzinfo=None):
            a_sem.append(w.strftime("%Y-%m-%d"))
            w += timedelta(days=7)
        a_pos = {s: i for i, s in enumerate(a_sem)}
        ROL = rx(AS["rol_terms"])
        ENC = {n: rx(v) for n, v in AS["encuadres"].items()}
        own = POLS[k]
        arows = [r for r in abase if k in r["pols"]]
        asp_rows = arows
        for r in arows:
            t = own.sub(" ", r["_f"])
            r["_rol"] = bool(ROL.search(t))
            r["_enc"] = [n for n, p in ENC.items() if p.search(t)]
        rol = [r for r in arows if r["_rol"]]
        acom = [r for r in arows if r["kind"] == "comment"]
        anews = [r for r in arows if r["kind"] == "news"]
        rcom = [r for r in rol if r["kind"] == "comment"]
        ne = sum(1 for r in arows if r["_enc"]) or 1
        enc_c = Counter(n for r in arows for n in r["_enc"])
        enc_w = {n: [0] * len(a_sem) for n in AS["encuadres"]}
        rol_w, all_w = [0] * len(a_sem), [0] * len(a_sem)
        for r in arows:
            i = a_pos.get(week(r["created_at"]))
            if i is None:
                continue
            all_w[i] += 1
            for n in r["_enc"]:
                enc_w[n][i] += 1
            if r["_rol"]:
                rol_w[i] += 1
        # Oposición en la misma ventana, para comparar con la misma vara
        opos = [n for n, v in FIG.items() if v.get("bando") == "Oposición"]
        a_men = [r for r in abase if r["pols"]]
        tot = sum(len(r["pols"]) for r in a_men) or 1
        el_a = [r for r in abase if "Elecciones 2027 y oposición" in r["temas"]]
        el_c = Counter(p for r in el_a for p in r["pols"])
        op_rows = []
        for n in opos:
            rs = [r for r in a_men if n in r["pols"]]
            if rs:
                op_rows.append({"name": n, "n": len(rs), "share": round(len(rs) / tot * 100, 1),
                                "balance": balance([r for r in rs if r["kind"] == "comment"]),
                                "neg": tone(rs)["NEG"], "elecciones": el_c.get(n, 0)})
        op_rows.sort(key=lambda x: -x["n"])
        el_opos = sorted(((n, el_c[n]) for n in opos if el_c.get(n)), key=lambda x: -x[1])
        co_rol = Counter(p for r in rol for p in r["pols"] if p != k)
        stop_own = set(WORD.findall(" ".join(fold(a) for a in FIG[k]["alias"]) + " " + fold(k)))
        wsets = [set(w for w in WORD.findall(r["_f"]) if w not in STOP and w not in stop_own) for r in arows]
        wc = Counter(w for ws in wsets for w in ws)
        negc = Counter(w for ws, r in zip(wsets, arows) if r["tono"] == "NEG" for w in ws)
        cloud = [{"w": w, "n": c, "s": c, "neg": pct(negc[w] / c), "_rid": [r["id"] for ws, r in zip(wsets, arows) if w in ws]}
                 for w, c in wc.most_common(60) if c >= 2]
        heads_r = sorted([r for r in rol if r["kind"] == "news"], key=lambda r: r["created_at"], reverse=True)[:20]
        heads_a = sorted(anews, key=lambda r: r["created_at"], reverse=True)[:20]
        hd = lambda rs: [{"t": r["title"], "o": r.get("outlet", ""), "u": r["url"], "d": r["created_at"][:10], "tono": r["tono"],
                          "narr": r["_enc"][:3]} for r in rs]
        pos = next((i + 1 for i, x in enumerate(op_rows) if x["name"] == k), None)
        b_all = balance(acom)
        aspirante = {
            "name": k, "rol": AS["rol"], "rol_terms": AS["rol_terms"], "dias": a_days, "semanas": a_sem,
            "n": len(arows), "n_news": len(anews), "n_comments": len(acom), "weekly": all_w,
            "share": next((x["share"] for x in op_rows if x["name"] == k), 0),
            "tone": tone(arows), "balance": b_all,
            "rol_n": len(rol), "rol_pct": pct(len(rol) / len(arows)) if arows else None, "rol_comments": len(rcom),
            "rol_weekly": rol_w, "tone_rol": tone(rol), "balance_rol": balance(rcom), "int_rol": intents(rcom) if len(rcom) >= 5 else None,
            "encuadres": [{"n": n, "c": c, "pct": pct(c / ne)} for n, c in enc_c.most_common()],
            "encuadres_semanal": enc_w,
            "co_rol": [{"a": a, "n": c, "bando": FIG[a].get("bando", "")} for a, c in co_rol.most_common(8)],
            "rank_oposicion": {"pos": pos, "de": len(op_rows)},
            "oposicion": op_rows,
            "rank_elecciones": next((i + 1 for i, (p, _) in enumerate(el_opos) if p == k), None), "elecciones_n": el_c.get(k, 0),
            "frases_rol": frases(rcom, 12, stop_own),
            "frases_critica": frases([r for r in acom if "critica" in r["int"]], 12, stop_own),
            "frases_apoya": frases([r for r in acom if "apoya" in r["int"]], 12, stop_own),
            "cloud": cloud,
            "titulares_rol": hd(heads_r), "titulares": hd(heads_a),
            "ultima": max((r["created_at"][:10] for r in arows), default=None),
        }
        # Lectura automática: frases cortas a partir de los números (no es una opinión editorial)
        L = []
        if not arows:
            L.append(f"Todavía no hay textos que nombren a {k} en los últimos {a_days} días: el recolector diario suma sus búsquedas propias.")
        else:
            L.append(f"{k} aparece en {len(arows)} textos de los últimos {a_days} días ({len(anews)} notas, {len(acom)} comentarios); "
                     f"es la figura opositora n.º {pos} de {len(op_rows)} por volumen ({aspirante['share']}% de las menciones). Última mención: {aspirante['ultima']}.")
            if rol:
                L.append(f"En {aspirante['rol_pct']}% de esos textos se lo vincula con elecciones, candidaturas, fórmulas o la vicepresidencia ({len(rol)} textos).")
            else:
                L.append("Todavía nadie lo asocia a una candidatura: lo que se dice de él no habla de fórmulas ni de la vicepresidencia.")
            if enc_c:
                n0, c0 = enc_c.most_common(1)[0]
                L.append(f"El encuadre dominante es «{n0}» ({pct(c0 / ne)}% de los textos con encuadre).")
            if co_rol:
                a0, c0 = co_rol.most_common(1)[0]
                L.append(f"Cuando se habla de él como candidato, la figura que más aparece al lado es {a0} ({c0} textos).")
            if b_all is not None:
                L.append(f"En comentarios de hinchas el balance apoyo−crítica es {b_all:+d} ({'pesa más el apoyo' if b_all >= 0 else 'pesa más la crítica'}).")
            elif acom:
                L.append(f"Hay {len(acom)} comentarios que lo nombran: todavía pocos para medir el balance (mínimo 5 con apoyo o crítica).")
        aspirante["lectura"] = L

    # ------------------------------------------------ hitos y alertas (Riquelme)
    fo = fby.get(FOCO, {})
    fw = fo.get("weekly") or [0] * len(semanas)
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
            wsets = [set(WORD.findall(r["_f"])) - STOP for r in wnews]
            best = max(range(len(wnews)), key=lambda j: sum(len(wsets[j] & o) for o in wsets), default=None)
            hitos.append({"semana": semanas[i], "n": v, "neg": pct(sum(1 for r in wrows if r["tono"] == "NEG") / len(wrows)) if wrows else None,
                          "temas": [n for n, _ in Counter(t for r in wrows for t in r["temas"]).most_common(2)],
                          "titular": ({"t": wnews[best]["title"], "o": wnews[best].get("outlet", ""), "u": wnews[best]["url"]}
                                      if best is not None else None)})
        hitos = sorted(sorted(hitos, key=lambda h: -h["n"])[:8], key=lambda h: h["semana"])

    alertas = []
    d = fo.get("delta")
    if d is not None and abs(d) >= 30:
        alertas.append({"tipo": "volumen", "dir": "up" if d > 0 else "down",
                        "texto": f"Las menciones de Riquelme {'subieron' if d > 0 else 'bajaron'} {abs(d)}% esta semana ({fo['last7']} vs. {fo['prev7']})."})
    cut4, cut12 = iso(now - timedelta(days=28)), iso(now - timedelta(days=84))
    rec = [r for r in foco_rows if r["kind"] == "comment" and r["created_at"] >= cut4]
    base = [r for r in foco_rows if r["kind"] == "comment" and cut12 <= r["created_at"] < cut4]
    b1, b0 = balance(rec), balance(base)
    if b1 is not None and b0 is not None and abs(b1 - b0) >= 10:
        alertas.append({"tipo": "balance", "dir": "up" if b1 > b0 else "down",
                        "texto": f"El balance apoyo−crítica hacia Riquelme en comentarios pasó de {b0:+d} a {b1:+d} en las últimas 4 semanas."})
    tr = sorted((t for t in tema_out if t["last28"] >= 10 and t["prev28"] >= 5), key=lambda t: -(t["last28"] / t["prev28"]))
    if tr and tr[0]["last28"] / tr[0]["prev28"] >= 1.4:
        t = tr[0]
        alertas.append({"tipo": "tema", "dir": "up", "texto": f"Crece la conversación sobre «{t['tema']}»: {t['last28']} textos en 4 semanas vs. {t['prev28']} antes."})
    if voz["pedidos"]:
        p = voz["pedidos"][0]
        alertas.append({"tipo": "pedido", "dir": "flat", "texto": f"El pedido más repetido en comentarios: «{p['p']}» ({p['n']} veces)."})
    riv = sorted((f for f in figs if not f["foco"] and f.get("delta") is not None and f.get("last7", 0) >= 5), key=lambda f: -f["delta"])
    if riv and riv[0]["delta"] >= 50:
        alertas.append({"tipo": "figura", "dir": "up", "texto": f"{riv[0]['name']} crece {riv[0]['delta']}% en menciones esta semana ({riv[0]['last7']} textos)."})
    if elecciones["n"] >= 5:
        top = elecciones["figuras"][0]["name"] if elecciones["figuras"] else None
        alertas.append({"tipo": "eleccion", "dir": "flat", "texto": f"Faltan {elecciones['dias']} días para las elecciones; {elecciones['n']} textos hablan de ellas"
                        + (f", con {top} como figura más nombrada." if top else ".")})

    # ------------------------------------------------ medios
    def share_neg(rows):
        return sum(1 for r in rows if r["tono"] == "NEG") / len(rows) if rows else None
    by_out = defaultdict(list)
    for r in foco_rows:
        if r["kind"] == "news" and r.get("outlet"):
            by_out[r["outlet"]].append(r)
    medios_tono = sorted(({"medio": o, "n": len(rs), "neg": pct(share_neg(rs)), "pos": pct(sum(1 for r in rs if r["tono"] == "POS") / len(rs))}
                          for o, rs in by_out.items() if len(rs) >= 2), key=lambda x: -x["n"])[:16]
    conv_news = [r for r in conv if r["kind"] == "news" and r.get("outlet")]
    top_out = [o for o, _ in Counter(r["outlet"] for r in conv_news).most_common(14)]
    top_pol = [f["name"] for f in sorted(figs, key=lambda f: -f["n"]) if f["n"]][:10]
    mm = Counter((r["outlet"], p) for r in conv_news for p in r["pols"])
    medios_matriz = {"medios": top_out, "politicos": top_pol, "valores": [[mm[(o, p)] for p in top_pol] for o in top_out]}
    vcount = Counter(r["video_id"] for r in coms)
    videos = [{"titulo": vinfo[v]["title"], "canal": vinfo[v]["channel"], "fecha": vinfo[v]["created_at"][:10], "url": vinfo[v]["url"],
               "comentarios": n, "critica": pct(sum(1 for r in coms if r.get("video_id") == v and "critica" in r["int"]) / n),
               "apoya": pct(sum(1 for r in coms if r.get("video_id") == v and "apoya" in r["int"]) / n)}
              for v, n in vcount.most_common(15) if v in vinfo]

    # ------------------------------------------------ Wikipedia
    wiki_out = None
    if WIKI.exists():
        W = json.loads(WIKI.read_text(encoding="utf8"))
        series, tot90 = {}, {}
        c90 = (now - timedelta(days=90)).strftime("%Y%m%d")
        for k, v in W.get("personas", {}).items():
            vw = v.get("vistas") or {}
            if not vw:
                continue
            wc = Counter()
            for dd, n in vw.items():
                wc[week(f"{dd[:4]}-{dd[4:6]}-{dd[6:]}T00:00:00Z")] += n
            series[k] = [wc.get(x, 0) for x in semanas]
            tot90[k] = sum(n for dd, n in vw.items() if dd >= c90)
        fp = W.get("personas", {}).get(FOCO) or {}
        wiki_out = {"semanas": semanas, "series": series, "total_90": tot90,
                    "articulos": {k: v.get("url") for k, v in W.get("personas", {}).items()},
                    "perfil": {"extract": fp.get("extract"), "url": fp.get("url")} if fp else None,
                    "club": W.get("club"), "fetched_at": W.get("fetched_at")}

    # ------------------------------------------------ textos de origen (extracto sin autor + link)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pub, order = [], []
    seen_ids = set()
    rid = {r["id"] for r in recent}
    for r in sorted(recent + [r for r in asp_rows if r["id"] not in rid], key=lambda r: r["created_at"], reverse=True):
        if r["id"] in seen_ids or not (r["pols"] or r["temas"] or r["int"]):
            continue
        seen_ids.add(r["id"])
        order.append(r["id"])
        com = r["kind"] == "comment"
        txt = (excerpt(r.get("text", ""), 600) if SHOW_COMMENTS else "") if com else (r.get("title") or r.get("text", ""))
        pub.append({"k": "c" if com else "n", "t": txt, "o": (r.get("video_title") or "YouTube") if com else r.get("outlet", ""),
                    "d": r["created_at"][:10], "u": r.get("url", ""), "tono": r.get("tono"), "temas": r.get("temas", []),
                    "pols": r.get("pols", []), "int": r.get("int", []), "lk": int(r.get("engagement") or 0) if com else 0})
    pidx = {x: i for i, x in enumerate(order)}

    def ids(lst):
        return [pidx[x] for x in lst if x in pidx][:150]
    for f in figs + ([aspirante] if aspirante else []):
        for c in f.get("cloud", []):
            c["ids"] = ids(c.pop("_rid", []))
    for grp in [voz["pedidos"], voz["deseos"], elecciones["pedidos"]] + [t["pedidos"] for t in tema_out]:
        for p in grp:
            p["ids"] = ids(p.pop("_rid", []))
    TEXTOS.write_text(json.dumps({"updated_at": iso(now), "items": pub}, ensure_ascii=False, separators=(",", ":")), encoding="utf8")

    status = json.loads(STATUS.read_text(encoding="utf8")) if STATUS.exists() else {}
    news_all = [r for r in texts if r["kind"] == "news"]
    out = {
        "updated_at": iso(now), "nombre": CONFIG["nombre"], "foco": FOCO, "window_days": CONFIG["window_days"],
        "conversacion_dias": CONFIG["conversacion_dias"], "status": status,
        "totales": {"textos": len(texts), "comentarios": sum(1 for r in texts if r["kind"] == "comment"), "videos": len(vinfo),
                    "noticias": len(news_all), "medios": len({r.get("outlet") for r in news_all if r.get("outlet")}),
                    "menciones": sum(len(r["pols"]) for r in conv), "menciones_foco": len(foco_rows),
                    "comentarios_periodo": len(coms), "con_intencion": voz["con_intencion"],
                    "metodo_nlp": Counter(r["metodo_nlp"] for r in texts).most_common(1)[0][0] if texts else "lexico"},
        "semanas": semanas, "figuras": figs,
        "foco_semanal": {"tono": foco_w, "intenciones": foco_int, "balance": foco_bal, "narrativas": foco_narr},
        "voz": voz, "elecciones": elecciones, "aspirante": aspirante, "mapa_poder": mapa, "hitos": hitos, "alertas": alertas,
        "medios_tono": medios_tono, "medios_matriz": medios_matriz, "videos": videos, "wiki": wiki_out,
        "metodo": {
            "temas": CONFIG["temas"], "narrativas": CONFIG["narrativas"], "intenciones": CONFIG["intenciones"],
            "figuras": {k: v["alias"] for k, v in FIG.items()},
            "aspirante_encuadres": (CONFIG.get("aspirante") or {}).get("encuadres", {}),
            "aspirante": "Aspirante: textos que nombran a la figura. «Asociado a candidatura» = el texto también habla de vice, fórmula, lista, candidatura o elecciones 2027 (sin contar su propio nombre). Encuadres por diccionario; un texto puede tener varios.",
            "intencion": "Cada comentario de YouTube se clasifica con diccionarios explicables: QUIERE (pedidos: 'queremos', 'que traigan', 'que se vaya', 'hay que'…), ESPERA ('ojalá', 'a ver si', 'tengo fe', 'se viene'…), CRITICA (marcadores de crítica, o tono negativo sin elogios) y APOYA (elogios, o tono positivo sin crítica). Un comentario puede tener más de una intención; si tiene crítica y apoyo a la vez, desempata el tono.",
            "balance": "Balance = (comentarios que apoyan − comentarios que critican) / (ambos) × 100, entre −100 y +100. Se muestra con al menos 5 comentarios.",
            "tono": "Tono, emoción y agresividad con pysentimiento (modelos entrenados con tuits en español) cuando corre en GitHub Actions; si no, diccionarios. Es el tono del texto que menciona a la figura, no necesariamente la postura hacia ella.",
            "menciones": "Un texto menciona a una figura si contiene alguno de sus alias. Los comentarios de un video sobre una sola figura (o un solo tema) se le atribuyen aunque no la nombren.",
            "pedidos": "Pedidos y deseos: disparador ('queremos', 'traigan', 'que se vaya', 'ojalá', 'a ver si'…) más las palabras que siguen, contados cuando se repiten en al menos 3 comentarios.",
        },
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf8")
    print(json.dumps(out["totales"], ensure_ascii=False))


if __name__ == "__main__":
    main()
