"""Agrega el almacén del paquete Massa · Galmarini en massa/data/massa.json (lo único que se publica).

Bloques:
  - Dupla: menciones, tono, narrativas, nube de palabras, co-menciones y titulares de Sergio Massa y
    Malena Galmarini frente a sus competidores; cuánto de la conversación de Galmarini depende de Massa.
  - Agenda vacante: temas con poca bandera dirigencial (salud mental adolescente, apuestas online,
    grooming). Para cada uno: cobertura semanal, qué parte de las notas no nombra a ningún dirigente,
    quién aparece asociado, interés en Wikipedia y datos de referencia con fuente.
  - Soberanía y seguridad de datos: cobertura del tema, incidentes recientes en medios, filtraciones
    conocidas de dominios argentinos (Have I Been Pwned) y chequeo pasivo de sitios públicos.

No publica autores ni textos de comentarios: de los comentarios solo salen conteos y porcentajes.
Los únicos textos publicados son titulares de medios.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "radar"))
import nlp  # noqa: E402  (tono/emoción/agresividad compartidos con el Radar)

CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf8"))
RADAR_CFG = HERE.parent / "radar" / "config.json"
STORE = HERE / ".store" / "items.jsonl"
STATUS = HERE / ".store" / "status.json"
WIKI = HERE / ".store" / "wiki.json"
SEG = HERE / ".store" / "seguridad.json"
NLP_CACHE = HERE / ".store" / "nlp.jsonl.gz"
OUT = HERE / "data" / "massa.json"
FOCO, FOCO2 = CONFIG["foco"], CONFIG["foco2"]
STOP = set("""que los las del por con una para como mas pero sus les este esta esto eso esa son hay fue ser muy todo todos
todas nos ese hace hacer sin sobre entre cuando donde porque tambien solo ya asi aca alli ahi tiene tienen estan esta
era han cada otro otra otros nada algo uno dos tan bien mal quien cual desde hasta hoy aqui ver van vez fueron
sera seria puede pueden tras ante segun durante anos ano dia dias semana mes meses parte hacia luego antes despues
the and you jaja jajaja jajajaja gente video videos nota notas diario noticias noticia leer fue sido ser estar estuvo
dijo afirmo aseguro senalo sostuvo explico ademas mientras sino aunque donde quienes cual cuales mismo misma
sergio massa malena galmarini argentina buenos aires infobae clarin nacion perfil pagina""".split())
WORD = re.compile(r"[a-zñ]{4,}")
DIAS: list[str] = []
EMOS = ["ira", "miedo", "tristeza", "alegria", "asco", "sorpresa"]


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def rx(terms):
    terms = sorted({fold(t) for t in terms if t}, key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(re.escape(t) for t in terms) + ")", re.I)


def rx_exact(terms):
    terms = sorted({fold(t) for t in terms if t}, key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(re.escape(t) for t in terms) + r")\b", re.I)


def pct(x):
    return round(100 * x, 1)


def week(s):
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return (d - timedelta(days=d.weekday())).strftime("%Y-%m-%d")


def ts(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


class Matcher:
    """Alias exactos de un político, sacando antes frases que lo confunden (p. ej. 'Sebastián Galmarini')."""

    def __init__(self, alias, excluir=()):
        self.rx = rx_exact(alias)
        self.ex = rx_exact(excluir) if excluir else None

    def search(self, t):
        if self.ex:
            t = self.ex.sub(" ", t)
        return self.rx.search(t)

    def sub(self, rep, t):
        if self.ex:
            t = self.ex.sub(rep, t)
        return self.rx.sub(rep, t)


NARR = {k: rx(v) for k, v in CONFIG["narrativas"].items()}
POS, NEG = rx(CONFIG["positivo"]), rx(CONFIG["negativo"])
POLS = {k: Matcher(v["alias"], v.get("excluir", ())) for k, v in CONFIG["politicos"].items()}


CARGO = re.compile(r"\b(?:[Ee]l|[Ll]a|[Ll]os|[Ll]as|[Dd]el)\s+(diputad[oa]s?|senador(?:a|es)?|legislador(?:a|es)?|concejal(?:a|es)?|intendent[ea]s?|ministr[oa]|gobernador(?:a)?|vicegobernador(?:a)?|defensor(?:a)? del pueblo)"
                   r"(?:\s+(?:nacional|provincial|bonaerense|porteñ[oa]|del [A-Z][a-záéíóú]+|de la [A-Z][a-záéíóú]+|de [A-Z][a-záéíóú]+))?,?\s+"
                   r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+(?:de\s+)?[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,2})")
NO_NOMBRE = {"Buenos Aires", "La Plata", "Mar Del Plata", "Provincia", "Nación", "Ciudad"}


def cargos(texto):
    """Dirigentes que no seguimos pero que el titular presenta por su cargo ("la diputada Ana Pérez")."""
    out = []
    for m in CARGO.finditer(texto or ""):
        nombre = m.group(2).strip()
        if nombre in NO_NOMBRE or len(nombre) < 6:
            continue
        out.append((nombre, m.group(1).lower().rstrip("s")))
    return out


def dirigentes(meta_out=None):
    """Todos los dirigentes que se buscan para medir si un tema 'tiene dueño': los del paquete y los del tablero nacional."""
    d = {k: Matcher(v["alias"], v.get("excluir", ())) for k, v in CONFIG["politicos"].items()}
    if meta_out is not None:
        meta_out.update({k: v.get("espacio", "") for k, v in CONFIG["politicos"].items()})
    try:
        rc = json.loads(RADAR_CFG.read_text(encoding="utf8"))
        for k, al in rc.get("actors", {}).items():
            if k in d or (rc.get("actor_meta", {}).get(k, {}).get("pais", "AR") != "AR"):
                continue
            al = [a for a in al if len(a) >= 5]  # apellidos cortos dan falsos positivos
            if al:
                d[k] = Matcher(al)
                if meta_out is not None:
                    meta_out[k] = rc.get("actor_meta", {}).get(k, {}).get("espacio", "")
    except (OSError, ValueError):
        pass
    return d


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
    try:
        import pandas as pd
        df = pd.DataFrame({"id": [r["id"] for r in rows], "text": [r.get("text", "") for r in rows],
                           "clean": [fold(r.get("text", "")) for r in rows], "lang": ["es"] * len(rows),
                           "ts": pd.to_datetime([r["created_at"] for r in rows], utc=True)})
        df = nlp.label(df, NLP_CACHE)
        for r, t, e, a, m in zip(rows, df["tono"], df["emocion"], df["agresivo"], df["metodo_nlp"]):
            r.update(tono=t, emocion=e, agresivo=bool(a), metodo_nlp=m)
    except Exception as e:
        print(f"nlp: uso diccionario ({str(e)[:80]})", flush=True)
        for r in rows:
            lab = nlp.lexicon(fold(r.get("text", "")))
            r.update(tono=lab["tono"], emocion=lab["emocion"], agresivo=lab["agresivo"], metodo_nlp="lexico")


def tone(rs):
    return {t: pct(sum(1 for r in rs if r["tono"] == t) / len(rs)) for t in ("NEG", "NEU", "POS")} if rs else None


def head(r, extra=None):
    h = {"t": r.get("title") or r.get("text", "")[:200], "o": r.get("outlet", ""), "u": r.get("url", ""), "d": r["created_at"][:10],
         "tono": r.get("tono")}
    return h | (extra or {})


def weeks_since(since, now):
    out, w = [], datetime.fromisoformat(week(ts(since)).replace("Z", ""))
    while w <= now.replace(tzinfo=None):
        out.append(w.strftime("%Y-%m-%d"))
        w += timedelta(days=7)
    return out


def wiki_weekly(vistas, semanas):
    wc = Counter()
    for dd, n in (vistas or {}).items():
        wc[week(f"{dd[:4]}-{dd[4:6]}-{dd[6:]}T00:00:00Z")] += n
    return [wc.get(x, 0) for x in semanas]


# ---------------------------------------------------------------- bloques
def dupla(texts, vinfo, now, semanas, conv_since):
    conv = [r for r in texts if r["created_at"] >= ts(conv_since) and r["pols"]]
    total_m = sum(len(r["pols"]) for r in conv) or 1
    word_sets = [set(w for w in WORD.findall(r["_f"]) if w not in STOP) for r in conv]
    total_words = Counter(w for ws in word_sets for w in ws)
    alias_words = set(WORD.findall(" ".join(fold(a) + " " + fold(k) for k, v in CONFIG["politicos"].items() for a in v["alias"])))
    last, prev = ts(now - timedelta(days=7)), ts(now - timedelta(days=14))
    out = []
    for k, meta in CONFIG["politicos"].items():
        idx = [i for i, r in enumerate(conv) if k in r["pols"]]
        m = [conv[i] for i in idx]
        info = {"name": k, "espacio": meta.get("espacio", ""), "cargo": meta.get("cargo", ""), "foco": bool(meta.get("foco")),
                "alias": meta["alias"], "n": len(m)}
        if not m:
            out.append(info)
            continue
        news = [r for r in m if r["kind"] == "news"]
        com = [r for r in m if r["kind"] == "comment"]
        wk = Counter(week(r["created_at"]) for r in m)
        dc = Counter(r["created_at"][:10] for r in m)
        tone_src = com if len(com) >= 15 else m
        emo = [r["emocion"] for r in tone_src if r["emocion"] in EMOS]
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
        l7 = sum(1 for r in m if r["created_at"] >= last)
        p7 = sum(1 for r in m if prev <= r["created_at"] < last)
        info.update({
            "n_news": len(news), "n_comments": len(com), "share": round(len(m) / total_m * 100, 1),
            "last7": l7, "prev7": p7, "delta": round((l7 - p7) / p7 * 100) if p7 >= 3 else None,
            "weekly": [wk.get(s, 0) for s in semanas], "daily": [dc.get(x, 0) for x in DIAS],
            "tone": tone(tone_src), "tone_base": "comentarios" if tone_src is com else "todos", "tone_news": tone(news), "tone_comments": tone(com),
            "emotions": {e: pct(emo.count(e) / len(emo)) for e in EMOS} if len(emo) >= 5 else None,
            "agresivo": pct(sum(r["agresivo"] for r in tone_src) / len(tone_src)),
            "narrativas": [{"n": a, "c": c, "pct": pct(c / nn)} for a, c in narr.most_common()],
            "cloud": [{"w": w, "n": mine[w], "s": round(v, 1), "neg": pct(negc[w] / mine[w])} for w, v in cloud],
            "co": [{"a": a, "n": c} for a, c in co.most_common(8)],
            "outlets": [{"o": o, "n": c} for o, c in outlets.most_common(10)],
            "headlines": [head(r, {"narr": [n for n, p in NARR.items() if p.search(" " + own.sub(" ", r["_f"]) + " ")][:3]})
                          for r in sorted(news, key=lambda r: r["created_at"], reverse=True)[:14]],
        })
        out.append(info)
    # Voz propia de Galmarini: qué parte de sus menciones también nombra a Massa
    g = [r for r in conv if FOCO2 in r["pols"]]
    juntos = sum(1 for r in g if FOCO in r["pols"])
    gm = Counter(week(r["created_at"]) for r in g if FOCO in r["pols"])
    gs = Counter(week(r["created_at"]) for r in g if FOCO not in r["pols"])
    voz = {"n": len(g), "con_massa": juntos, "pct_con_massa": pct(juntos / len(g)) if g else None,
           "semanal_con_massa": [gm.get(s, 0) for s in semanas], "semanal_sola": [gs.get(s, 0) for s in semanas]}
    vids = Counter(r["video_id"] for r in texts if r["kind"] == "comment" and (FOCO in r["pols"] or FOCO2 in r["pols"]))
    videos = [{"titulo": vinfo[v]["title"], "canal": vinfo[v]["channel"], "fecha": vinfo[v]["created_at"][:10], "url": vinfo[v]["url"], "comentarios": n,
               "neg": pct(sum(1 for r in texts if r.get("video_id") == v and r["kind"] == "comment" and r["tono"] == "NEG") / n)}
              for v, n in vids.most_common(10) if v in vinfo]
    return conv, out, voz, videos


def tema_block(nombre, cfg, news, dirig, semanas, now, conv_since, wiki_t, dmeta=None):
    trx = rx(cfg["terms"])
    rows = [r for r in news if trx.search(r["_f"])]
    rec = [r for r in rows if r["created_at"] >= ts(conv_since)]
    for r in rec:
        r["_dir"] = [k for k, m in dirig.items() if m.search(r["_f"])]
    # Voces: dirigentes seguidos más los que el titular presenta por su cargo
    voces = {}
    for r in sorted(rec, key=lambda r: r["created_at"], reverse=True):
        found = [(k, dmeta.get(k, "") if dmeta else "", "seguido") for k in r["_dir"]]
        for quien_c, cargo in cargos(r.get("title") or r.get("text", "")):
            if not any(fold(quien_c) in fold(k) or fold(k) in fold(quien_c) for k, _, _ in found):
                found.append((quien_c, cargo, "por cargo"))
        r["_voz"] = [f[0] for f in found]
        for k, esp, tipo in found:
            v = voces.setdefault(k, {"name": k, "espacio": esp, "tipo": tipo, "n": 0, "notas": []})
            v["n"] += 1
            if len(v["notas"]) < 3:
                v["notas"].append(head(r))
    con = [r for r in rec if r["_voz"]]
    quien = Counter(k for r in rec for k in r["_voz"])
    top = quien.most_common(1)[0] if quien else None
    wk = Counter(week(r["created_at"]) for r in rec)
    c90 = ts(now - timedelta(days=90))
    l4, p4 = ts(now - timedelta(days=28)), ts(now - timedelta(days=56))
    n4, np4 = sum(1 for r in rec if r["created_at"] >= l4), sum(1 for r in rec if p4 <= r["created_at"] < l4)
    arts = {}
    for art, w in (wiki_t or {}).items():
        v = w.get("vistas") or {}
        arts[art] = {"url": w.get("url"), "semanal": wiki_weekly(v, semanas),
                     "total_90": sum(n for dd, n in v.items() if dd >= c90.replace("-", "")[:8])}
    return {
        "tema": nombre, "corto": cfg.get("corto", nombre), "color": cfg.get("color"), "n": len(rec), "medios": len({r.get("outlet") for r in rec if r.get("outlet")}),
        "ultimas4": n4, "previas4": np4, "delta4": round((n4 - np4) / np4 * 100) if np4 >= 3 else None,
        "pct_sin_dirigente": pct(1 - len(con) / len(rec)) if rec else None,
        "dirigente_top": {"name": top[0], "n": top[1], "pct": pct(top[1] / len(rec))} if top else None,
        "dirigentes": [{"name": k, "n": c, "pct": pct(c / len(rec))} for k, c in quien.most_common(10)],
        "voces": [voces[k] | {"pct": pct(voces[k]["n"] / len(rec))} for k, _ in quien.most_common(15)],
        "foco": {k: sum(1 for r in rec if k in r["_dir"]) for k in (FOCO, FOCO2)},
        "tono": tone(rec), "semanal": [wk.get(s, 0) for s in semanas],
        "outlets": [{"o": o, "n": c} for o, c in Counter(r.get("outlet") for r in rec if r.get("outlet")).most_common(8)],
        "titulares": [head(r, {"dir": r["_voz"][:3]}) for r in sorted(rec, key=lambda r: r["created_at"], reverse=True)[:25]],
        "wiki": arts,
        "datos": cfg.get("datos", []), "marco": cfg.get("marco", []), "propuestas": cfg.get("propuestas", []), "fuentes": cfg.get("fuentes", []),
    }


def sitio_score(s):
    if not s.get("https"):
        return None
    checks = [bool(s.get("http_a_https"))] + [bool(v) for v in (s.get("cabeceras") or {}).values()] + \
             [s.get("dias_cert", 0) > 14, s.get("tls") in ("TLSv1.2", "TLSv1.3"), bool(s.get("spf")),
              s.get("dmarc") in ("reject", "quarantine"), not s.get("software_expuesto"), not s.get("rastreadores")]
    return {"ok": sum(checks), "total": len(checks)}


def main():
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=CONFIG["window_days"])
    conv_since = now - timedelta(days=CONFIG["conversacion_dias"])
    items = [i for i in load_items() if i.get("created_at", "") >= ts(since)]
    seen, dedup = set(), []
    for i in items:
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
        r["_f"] = fold(r.get("text", ""))
        r["pols"] = [k for k, p in POLS.items() if p.search(r["_f"])]
        r["narr"] = [k for k, p in NARR.items() if p.search(" " + r["_f"] + " ")]
    vpols = {v: [k for k, p in POLS.items() if p.search(fold(i.get("text", "")))] for v, i in vinfo.items()}
    for r in texts:
        if r["kind"] == "comment" and not r["pols"] and len(vpols.get(r.get("video_id"), [])) == 1:
            r["pols"] = list(vpols[r["video_id"]])
    semanas = weeks_since(conv_since, now)
    DIAS[:] = [(conv_since + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((now - conv_since).days + 1)]
    conv, pols_out, voz, videos = dupla(texts, vinfo, now, semanas, conv_since)

    # ------------------------------------------------ agenda vacante y datos
    news = [r for r in texts if r["kind"] == "news"]
    dmeta = {}
    dirig = dirigentes(dmeta)
    W = json.loads(WIKI.read_text(encoding="utf8")) if WIKI.exists() else {}
    agenda = [tema_block(k, v, news, dirig, semanas, now, conv_since, (W.get("temas") or {}).get(k), dmeta)
              for k, v in CONFIG.get("agenda", {}).items()]
    D = CONFIG["datos"]
    datos = tema_block(D["tema"], D, news, dirig, semanas, now, conv_since, (W.get("temas") or {}).get(D["tema"]), dmeta)
    inc = rx(D["incidente"])
    datos["incidentes"] = [head(r) for r in sorted((r for r in news if r["created_at"] >= ts(conv_since) and rx(D["terms"]).search(r["_f"])
                                                   and inc.search(r["_f"])), key=lambda r: r["created_at"], reverse=True)[:30]]
    seg = json.loads(SEG.read_text(encoding="utf8")) if SEG.exists() else {}
    sitios = []
    for s in seg.get("sitios", []):
        s = dict(s)
        s["puntaje"] = sitio_score(s)
        sitios.append(s)
    emp = Counter(e for s in sitios for e in (s.get("rastreadores") or {}))
    datos.update({"sitios": sitios, "sitios_fecha": seg.get("fetched_at"),
                  "rastreadores_por_empresa": emp.most_common(),
                  "filtraciones": sorted(seg.get("filtraciones", []), key=lambda b: b.get("fecha") or "", reverse=True),
                  "hibp_error": seg.get("hibp_error"), "herramientas": D.get("herramientas", []),
                  "marco_ext": D.get("marco", []), "propuestas": D.get("propuestas", [])})

    # ------------------------------------------------ alertas
    alertas = []
    for p in pols_out:
        if p["name"] in (FOCO, FOCO2) and p.get("delta") is not None and abs(p["delta"]) >= 30:
            alertas.append({"tipo": "volumen", "dir": "up" if p["delta"] > 0 else "down",
                            "texto": f"Las menciones de {p['name']} {'subieron' if p['delta'] > 0 else 'bajaron'} {abs(p['delta'])}% esta semana ({p['last7']} vs. {p['prev7']})."})
    if voz["pct_con_massa"] is not None and voz["n"] >= 10:
        alertas.append({"tipo": "dupla", "dir": "flat",
                        "texto": f"{voz['pct_con_massa']}% de las menciones de {FOCO2} también nombran a {FOCO}."})
    for t in agenda + [datos]:
        if t["delta4"] is not None and t["delta4"] >= 30:
            alertas.append({"tipo": "agenda", "dir": "up", "texto": f"Crece la cobertura de «{t['tema']}»: {t['ultimas4']} notas en 4 semanas (+{t['delta4']}%)."})
        if t["n"] >= 10 and t["pct_sin_dirigente"] is not None and t["pct_sin_dirigente"] >= 70:
            alertas.append({"tipo": "vacante", "dir": "flat", "texto": f"«{t['tema']}»: {t['pct_sin_dirigente']}% de las notas no nombra a ningún dirigente."})
    riv = sorted((p for p in pols_out if not p["foco"] and p.get("delta") is not None and p.get("last7", 0) >= 5), key=lambda p: -p["delta"])
    if riv and riv[0]["delta"] >= 50:
        alertas.append({"tipo": "competidor", "dir": "up", "texto": f"{riv[0]['name']} crece {riv[0]['delta']}% en menciones esta semana."})

    # ------------------------------------------------ Wikipedia de personas
    wiki_out = None
    if W.get("personas"):
        c90 = (now - timedelta(days=90)).strftime("%Y%m%d")
        wiki_out = {"series": {k: wiki_weekly(v.get("vistas"), semanas) for k, v in W["personas"].items()},
                    "total_90": {k: sum(n for dd, n in (v.get("vistas") or {}).items() if dd >= c90) for k, v in W["personas"].items()},
                    "perfil": {k: {"extract": v.get("extract"), "url": v.get("url")} for k, v in W["personas"].items() if k in (FOCO, FOCO2)},
                    "fetched_at": W.get("fetched_at")}

    status = json.loads(STATUS.read_text(encoding="utf8")) if STATUS.exists() else {}
    out = {
        "updated_at": ts(now), "foco": FOCO, "foco2": FOCO2, "window_days": CONFIG["window_days"], "conversacion_dias": CONFIG["conversacion_dias"],
        "status": status, "semanas": semanas, "dias": DIAS,
        "totales": {"textos": len(texts), "comentarios": sum(1 for r in texts if r["kind"] == "comment"), "videos": len(vinfo),
                    "noticias": len(news), "medios": len({r.get("outlet") for r in news if r.get("outlet")}),
                    "metodo_nlp": Counter(r["metodo_nlp"] for r in texts).most_common(1)[0][0] if texts else "lexico"},
        "politicos": pols_out, "voz_propia": voz, "videos": videos, "alertas": alertas, "wiki": wiki_out,
        "agenda": agenda, "datos": datos,
        "metodo": {
            "politicos": {k: v["alias"] for k, v in CONFIG["politicos"].items()}, "narrativas": CONFIG["narrativas"],
            "agenda": {k: v["terms"] for k, v in CONFIG.get("agenda", {}).items()} | {D["tema"]: D["terms"]},
            "vacancia": "Para cada tema se cuentan las notas de medios de los últimos días que usan alguno de sus términos y se busca en ellas a "
                        "cualquier dirigente seguido (los de este paquete y los argentinos del tablero nacional). 'Sin dirigente' es la parte de "
                        "las notas que no nombra a ninguno: cuanto más alta, más libre está la bandera.",
            "sitios": "Chequeo pasivo: una visita a la portada, como la de cualquier navegador. Se leen encabezados de seguridad, certificado, "
                      "redirección a HTTPS, software expuesto, terceros que carga la página y registros de correo SPF/DMARC (DNS público). "
                      "No se prueba ni se explota ninguna vulnerabilidad.",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf8")
    print(json.dumps(out["totales"], ensure_ascii=False))


if __name__ == "__main__":
    main()
