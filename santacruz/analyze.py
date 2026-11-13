"""Agrega el almacén de Santa Cruz en santacruz/data/santacruz.json (lo que se publica) y santacruz/data/textos.json.

Bloques:
  - Cara a cara: Juan Carlos Molina vs. Pablo Grasso como posibles candidatos a gobernador (volumen, tono,
    balance apoyo/crítica, temas que "posee" cada uno, narrativas, interés en Wikipedia y Google Trends).
  - Figuras: menciones de los dos candidatos y del resto de la oferta (Vidal, LLA, Moveré, UCR, internas del PJ),
    tono/emoción/agresividad (pysentimiento si está instalado, si no diccionarios: ver radar/nlp.py), nubes, co-menciones.
  - Voz de la gente: qué QUIERE, ESPERA, CRITICA y APOYA la gente en comentarios de YouTube, por tema provincial.
  - Hacia 2027: conversación sobre la gobernación y peso de cada figura.
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
OUT = HERE / "data" / "santacruz.json"
TRENDS = HERE / ".store" / "trends.json"
TEXTOS = HERE / "data" / "textos.json"
FOCOS = CONFIG["focos"]
FOCO = FOCOS[0]
INTS = ["quiere", "espera", "critica", "apoya"]
STOP = set("""que los las del por con una para como mas pero sus les este esta esto eso esa son hay fue ser muy todo todos
todas nos ese hace hacer sin sobre entre cuando donde porque tambien solo ya asi aca alli ahi tiene tienen estan esta
era han cada otro otra otros nada algo uno dos tan bien mal quien cual desde hasta hoy aqui ver van vez fueron
sera seria puede pueden tras ante segun durante anos ano dia dias semana mes meses parte hacia luego antes despues
the and you jaja jajaja jajajaja jajajajaja gente video videos nota notas diario noticias noticia leer fue sido estar
estuvo dijo afirmo aseguro senalo sostuvo explico ademas mientras sino aunque mismo misma quienes cuales eso esos
santa cruz provincia provincial santacruceno santacrucena gobierno vos sos tenes son asi pero porque igual siempre nunca todo nada tambien ese esa eso los las
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
CTX = rx(CONFIG["contexto"] + [a for v in FIG.values() if v.get("bando") != "Nacional" for a in v["alias"] if len(a) > 6])
SHOW_COMMENTS = CONFIG.get("textos_comentarios") == "extracto"
MASK = [(re.compile(r"@[\w.\-]{2,}"), "@…"), (re.compile(r"\S+@\S+\.\w+"), "[correo]"),
        (re.compile(r"(?:\+?54)?[\s\-]?\d{3,4}[\s\-]?\d{6,7}\b"), "[tel]")]
EMOS = ["ira", "miedo", "tristeza", "alegria", "asco", "sorpresa"]
# Pedidos y deseos: categoría del disparador + la palabra que sigue (saltando artículos): «Que se vaya: vasco», «Que traigan: 9»
PED_CAT = [
    ("Que se vaya", r"que se vayan?|se tienen? que ir|que renuncien?|fuera|saquen|saquenlo|echen|rajen"),
    ("Que paguen", r"que paguen|paguen|aumenten|que aumenten"),
    ("Que arreglen", r"que arreglen|arreglen|que hagan|hagan"),
    ("Queremos", r"queremos|quiero|necesitamos|necesita|hace falta|nos falta|falta un|falta una"),
    ("Que vuelva", r"que vuelvan?|volve|vuelva"),
    ("Que se presente", r"que se presente|que sea candidato|candidato a|para gobernador|lo voto a|voto a"),
    ("Hay que", r"hay que|pedimos|exigimos"),
]
DES_CAT = [("Ojalá", r"ojala|ojala que"), ("Espero", r"espero que|esperemos que|espero"), ("A ver si", r"a ver si"),
           ("Tengo fe en", r"tengo fe en|tengo fe que|confio en|confiamos en"), ("Se viene", r"se viene|se vienen"), ("Que gane", r"que gane|va a ganar|gana")]
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
OBJ_FIG = {"grasso": "Grasso", "pablo": "Grasso", "molina": "Molina", "cura": "Molina", "padre": "Molina", "vidal": "Vidal",
           "claudio": "Vidal", "guzman": "Guzmán", "jairo": "Guzmán", "carambia": "Carambia", "reyes": "Reyes", "belloni": "Belloni",
           "milei": "Milei", "cristina": "Cristina", "alicia": "Alicia", "kirchner": "Kirchner", "garrido": "Garrido"}


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
    seen, dedup = set(), []
    for i in sorted(items, key=lambda x: x.get("query") == "rss"):
        key = (i["kind"], fold(i.get("title") or i.get("text", ""))[:120]) if i["kind"] == "news" else (i["kind"], i["id"])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(i)
    items = dedup
    vinfo = {i["video_id"]: i for i in items if i["kind"] == "video"}
    texts = [i for i in items if i["kind"] != "video"]
    # Notas: solo las que tienen contexto santacruceño o nombran a una figura provincial (Google News trae ruido con apellidos comunes)
    # Una nota que salió de una búsqueda por el nombre de un candidato y lo nombra también vale aunque no diga "Santa Cruz"
    FOCO_Q = {f: [fold(a) for a in FIG[f]["alias"] if len(a) > 5] for f in FOCOS}

    def pertinente(r):
        t = fold(r.get("text", ""))
        if CTX.search(t):
            return True
        q = fold(r.get("query", ""))
        return any(any(a in q for a in al) and POLS[f].search(t) for f, al in FOCO_Q.items())
    texts = [r for r in texts if r["kind"] == "comment" or pertinente(r)]
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

    def semanal(rows):
        w = {t: [0] * len(semanas) for t in ("NEG", "NEU", "POS")}
        it = {k: [0] * len(semanas) for k in INTS}
        na = {n: [0] * len(semanas) for n in CONFIG["narrativas"]}
        for r in rows:
            i = wpos.get(week(r["created_at"]))
            if i is None:
                continue
            w[r["tono"]][i] += 1
            for k in r["int"]:
                it[k][i] += 1
            for n in r["narr"]:
                na[n][i] += 1
        bal = [round(100 * (it["apoya"][i] - it["critica"][i]) / (it["apoya"][i] + it["critica"][i]))
               if it["apoya"][i] + it["critica"][i] >= 5 else None for i in range(len(semanas))]
        return {"tono": w, "intenciones": it, "balance": bal, "narrativas": na}
    foco_rows_by = {f: [r for r in conv if f in r["pols"]] for f in FOCOS}
    foco_semanal = {f: semanal(rs) for f, rs in foco_rows_by.items()}

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
    EL = "Elecciones 2027 y candidaturas"
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

    # ------------------------------------------------ hitos y alertas (por candidato)
    hitos, alertas = [], []
    cut4, cut12 = iso(now - timedelta(days=28)), iso(now - timedelta(days=84))
    for FC in FOCOS:
        fo = fby.get(FC, {})
        foco_rows = foco_rows_by[FC]
        corto = FC.split()[-1]
        fw = fo.get("weekly") or [0] * len(semanas)
        hs = []
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
                hs.append({"foco": FC, "semana": semanas[i], "n": v,
                           "neg": pct(sum(1 for r in wrows if r["tono"] == "NEG") / len(wrows)) if wrows else None,
                           "temas": [n for n, _ in Counter(t for r in wrows for t in r["temas"]).most_common(2)],
                           "titular": ({"t": wnews[best]["title"], "o": wnews[best].get("outlet", ""), "u": wnews[best]["url"]}
                                       if best is not None else None)})
            hitos += sorted(hs, key=lambda h: -h["n"])[:6]
        d = fo.get("delta")
        if d is not None and abs(d) >= 30:
            alertas.append({"tipo": "volumen", "dir": "up" if d > 0 else "down", "foco": FC,
                            "texto": f"Las menciones de {corto} {'subieron' if d > 0 else 'bajaron'} {abs(d)}% esta semana ({fo['last7']} vs. {fo['prev7']})."})
        rec = [r for r in foco_rows if r["kind"] == "comment" and r["created_at"] >= cut4]
        base = [r for r in foco_rows if r["kind"] == "comment" and cut12 <= r["created_at"] < cut4]
        b1, b0 = balance(rec), balance(base)
        if b1 is not None and b0 is not None and abs(b1 - b0) >= 10:
            alertas.append({"tipo": "balance", "dir": "up" if b1 > b0 else "down", "foco": FC,
                            "texto": f"El balance apoyo−crítica hacia {corto} en comentarios pasó de {b0:+d} a {b1:+d} en las últimas 4 semanas."})
    hitos.sort(key=lambda h: h["semana"])
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
        alertas.append({"tipo": "eleccion", "dir": "flat", "texto": f"Faltan {elecciones['dias']} días para la fecha de referencia; {elecciones['n']} textos hablan de la gobernación"
                        + (f", con {top} como figura más nombrada." if top else ".")})

    # ------------------------------------------------ medios
    def share_neg(rows):
        return sum(1 for r in rows if r["tono"] == "NEG") / len(rows) if rows else None
    medios_tono = {}
    for FC in FOCOS:
        by_out = defaultdict(list)
        for r in foco_rows_by[FC]:
            if r["kind"] == "news" and r.get("outlet"):
                by_out[r["outlet"]].append(r)
        medios_tono[FC] = sorted(({"medio": o, "n": len(rs), "neg": pct(share_neg(rs)), "pos": pct(sum(1 for r in rs if r["tono"] == "POS") / len(rs))}
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
        perfiles = {f: {"extract": (W.get("personas", {}).get(f) or {}).get("extract"), "url": (W.get("personas", {}).get(f) or {}).get("url")}
                    for f in FOCOS if W.get("personas", {}).get(f)}
        wiki_out = {"semanas": semanas, "series": series, "total_90": tot90,
                    "articulos": {k: v.get("url") for k, v in W.get("personas", {}).items()},
                    "perfiles": perfiles, "provincia": W.get("provincia"), "fetched_at": W.get("fetched_at")}

    # ------------------------------------------------ Google Trends
    trends_out = None
    if TRENDS.exists():
        T = json.loads(TRENDS.read_text(encoding="utf8"))
        geos = CONFIG.get("trends", {}).get("geos", {})
        tser, tprom = {}, {}
        for geo, serie in (T.get("series") or {}).items():
            tser[geo], tprom[geo] = {}, {}
            for term, pts in serie.items():
                wc, wn = Counter(), Counter()
                for dd, v in pts.items():
                    k = week(dd + "T00:00:00Z")
                    wc[k] += v
                    wn[k] += 1
                tser[geo][term] = [round(wc[x] / wn[x], 1) if wn.get(x) else None for x in semanas]
                c90 = (now - timedelta(days=90)).strftime("%Y-%m-%d")
                vals = [v for dd, v in pts.items() if dd >= c90]
                tprom[geo][term] = round(sum(vals) / len(vals), 1) if vals else None
        trends_out = {"semanas": semanas, "series": tser, "promedio_90": tprom, "geos": geos,
                      "terminos": T.get("terminos"), "errores": T.get("errores"), "fetched_at": T.get("fetched_at")}

    # ------------------------------------------------ cara a cara (Molina vs. Grasso)
    LOC = [fold(x) for x in CONFIG.get("medios_locales", [])]
    es_local = lambda o: any(l in fold(o or "") for l in LOC)
    A, B = FOCOS[0], FOCOS[1]
    duo = {}
    for FC in FOCOS:
        f = fby.get(FC, {})
        rs = foco_rows_by[FC]
        nw = [r for r in rs if r["kind"] == "news"]
        loc = [r for r in nw if es_local(r.get("outlet"))]
        duo[FC] = {k: f.get(k) for k in ("n", "share", "last7", "prev7", "delta", "balance", "tone", "intenciones", "n_news", "n_comments",
                                           "agresivo", "cargo")}
        duo[FC].update({"locales": len(loc), "nacionales": len(nw) - len(loc),
                        "pct_local": pct(len(loc) / len(nw)) if nw else None,
                        "tono_local": tone(loc), "tono_nacional": tone([r for r in nw if r not in loc]),
                        "wiki_90": (wiki_out or {}).get("total_90", {}).get(FC),
                        "trends_sc": ((trends_out or {}).get("promedio_90", {}).get("AR-Z", {}) or {}).get(FC),
                        "trends_ar": ((trends_out or {}).get("promedio_90", {}).get("AR", {}) or {}).get(FC),
                        "con_vidal": sum(1 for r in rs if "Claudio Vidal" in r["pols"]),
                        "con_milei": sum(1 for r in rs if "Javier Milei" in r["pols"]),
                        "con_cristina": sum(1 for r in rs if "Cristina Kirchner" in r["pols"])})
    ambos = [r for r in conv if A in r["pols"] and B in r["pols"]]
    temas_duo = []
    for t in temas:
        ra = [r for r in foco_rows_by[A] if t in r["temas"]]
        rb = [r for r in foco_rows_by[B] if t in r["temas"]]
        if not ra and not rb:
            continue
        ca, cb = [r for r in ra if r["kind"] == "comment"], [r for r in rb if r["kind"] == "comment"]
        na, nb = len(ra), len(rb)
        # "dueño" del tema: quién concentra más textos, ponderado por el tamaño de cada conversación
        pa = na / max(len(foco_rows_by[A]), 1)
        pb = nb / max(len(foco_rows_by[B]), 1)
        temas_duo.append({"tema": t, A: na, B: nb, "pct_" + A: pct(pa), "pct_" + B: pct(pb),
                          "bal_" + A: balance(ca), "bal_" + B: balance(cb),
                          "neg_" + A: (tone(ra) or {}).get("NEG"), "neg_" + B: (tone(rb) or {}).get("NEG"),
                          "duenio": A if pa > pb * 1.25 else B if pb > pa * 1.25 else "parejo"})
    temas_duo.sort(key=lambda x: -(x[A] + x[B]))
    def lider(k, mayor=True):
        va, vb = duo[A].get(k), duo[B].get(k)
        if va is None or vb is None or va == vb:
            return None
        return (A if va > vb else B) if mayor else (A if va < vb else B)
    duelo = {"a": A, "b": B, "candidatos": duo, "temas": temas_duo,
             "ambos": {"n": len(ambos), "tono": tone(ambos),
                       "titulares": [{"t": r["title"], "o": r.get("outlet", ""), "u": r["url"], "d": r["created_at"][:10], "tono": r["tono"]}
                                     for r in sorted([r for r in ambos if r["kind"] == "news"], key=lambda r: r["created_at"], reverse=True)[:20]]},
             "lider": {"volumen": lider("n"), "balance": lider("balance"), "wikipedia": lider("wiki_90"), "trends_sc": lider("trends_sc"),
                       "medios_locales": lider("locales"), "menos_negativo": None}}
    ta, tb = (duo[A].get("tone") or {}).get("NEG"), (duo[B].get("tone") or {}).get("NEG")
    if ta is not None and tb is not None and ta != tb:
        duelo["lider"]["menos_negativo"] = A if ta < tb else B

    # ------------------------------------------------ textos de origen (extracto sin autor + link)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pub, order = [], []
    seen_ids = set()
    for r in sorted(recent, key=lambda r: r["created_at"], reverse=True):
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
    for f in figs:
        for c in f.get("cloud", []):
            c["ids"] = ids(c.pop("_rid", []))
    for grp in [voz["pedidos"], voz["deseos"], elecciones["pedidos"]] + [t["pedidos"] for t in tema_out]:
        for p in grp:
            p["ids"] = ids(p.pop("_rid", []))
    TEXTOS.write_text(json.dumps({"updated_at": iso(now), "items": pub}, ensure_ascii=False, separators=(",", ":")), encoding="utf8")

    status = json.loads(STATUS.read_text(encoding="utf8")) if STATUS.exists() else {}
    news_all = [r for r in texts if r["kind"] == "news"]
    out = {
        "updated_at": iso(now), "nombre": CONFIG["nombre"], "focos": FOCOS, "eleccion_nota": CONFIG.get("eleccion_nota", ""), "window_days": CONFIG["window_days"],
        "conversacion_dias": CONFIG["conversacion_dias"], "status": status,
        "totales": {"textos": len(texts), "comentarios": sum(1 for r in texts if r["kind"] == "comment"), "videos": len(vinfo),
                    "noticias": len(news_all), "medios": len({r.get("outlet") for r in news_all if r.get("outlet")}),
                    "menciones": sum(len(r["pols"]) for r in conv), "menciones_foco": {f: len(rs) for f, rs in foco_rows_by.items()},
                    "comentarios_periodo": len(coms), "con_intencion": voz["con_intencion"],
                    "metodo_nlp": Counter(r["metodo_nlp"] for r in texts).most_common(1)[0][0] if texts else "lexico"},
        "semanas": semanas, "figuras": figs,
        "foco_semanal": foco_semanal, "duelo": duelo, "trends": trends_out,
        "voz": voz, "elecciones": elecciones, "mapa_poder": mapa, "hitos": hitos, "alertas": alertas,
        "medios_tono": medios_tono, "medios_matriz": medios_matriz, "videos": videos, "wiki": wiki_out,
        "metodo": {
            "temas": CONFIG["temas"], "narrativas": CONFIG["narrativas"], "intenciones": CONFIG["intenciones"],
            "figuras": {k: v["alias"] for k, v in FIG.items()},
            "intencion": "Cada comentario de YouTube se clasifica con diccionarios explicables: QUIERE (pedidos: 'queremos', 'hay que', 'que paguen', 'que se vaya'…), ESPERA ('ojalá', 'a ver si', 'tengo fe', 'se viene'…), CRITICA (marcadores de crítica, o tono negativo sin elogios) y APOYA (elogios, o tono positivo sin crítica). Un comentario puede tener más de una intención; si tiene crítica y apoyo a la vez, desempata el tono.",
            "balance": "Balance = (comentarios que apoyan − comentarios que critican) / (ambos) × 100, entre −100 y +100. Se muestra con al menos 5 comentarios.",
            "tono": "Tono, emoción y agresividad con pysentimiento (modelos entrenados con tuits en español) cuando corre en GitHub Actions; si no, diccionarios. Es el tono del texto que menciona a la figura, no necesariamente la postura hacia ella.",
            "menciones": "Un texto menciona a una figura si contiene alguno de sus alias. Los comentarios de un video sobre una sola figura (o un solo tema) se le atribuyen aunque no la nombren.",
            "pedidos": "Pedidos y deseos: disparador ('queremos', 'que paguen', 'que se vaya', 'ojalá', 'a ver si'…) más las palabras que siguen, contados cuando se repiten en al menos 3 comentarios.",
        },
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf8")
    print(json.dumps(out["totales"], ensure_ascii=False))


if __name__ == "__main__":
    main()
