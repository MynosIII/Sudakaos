"""Brújula · cruce quiz × conversación -> brujula/data/cruce.json (+ alertas y resumen accionable).

    python brujula/cruce.py [--quiz data/quiz.json] [--listener data/listener.json] [--out data/cruce.json]

- Brecha de figura: afinidad en el quiz (% de quienes tienen a esa figura como la más cercana) vs. share of voice.
- Brecha de postura: hacia qué polo se inclina la gente en el quiz vs. hacia qué polo se encuadra la conversación.
- Agenda: cuánto divide cada eje en el quiz vs. cuánto se habla de él.
- Plataformas: perfil en el quiz de quienes se informan por cada red vs. tono de la conversación en esa red.
- Anuncios: a quién le llegan los avisos políticos de cada tema (Meta) y cómo piensa ese público según el quiz.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
EJES = {e["id"]: e for e in json.loads((HERE / "datos" / "ejes.json").read_text(encoding="utf8"))["ejes"]}
# Solo redes con conversación orgánica escuchada (Instagram y Facebook no tienen búsqueda abierta: sin tono)
RED_A_PLAT = {"YouTube": "YouTube", "X (Twitter)": "X", "Ninguna: medios tradicionales": "Medios"}
AD_EDAD = {"13-17": "16-24", "18-24": "16-24", "25-34": "25-34", "35-44": "35-49", "45-54": "35-49", "55-64": "50+", "65+": "50+"}


def load(p):
    p = Path(p)
    return json.loads(p.read_text(encoding="utf8")) if p.exists() else {}


def polo(eid, v):
    e = EJES[eid]
    return e["b"] if v > 50 else e["a"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiz", default=str(HERE / "data" / "quiz.json"))
    ap.add_argument("--listener", default=str(HERE / "data" / "listener.json"))
    ap.add_argument("--out", default=str(HERE / "data" / "cruce.json"))
    a = ap.parse_args()
    Q, L = load(a.quiz), load(a.listener)
    q = (Q.get("versiones") or {}).get("ar") or {}
    out = {"updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "simulado": bool(Q.get("simulado")),
           "n_quiz": q.get("n", 0), "textos": (L.get("totales") or {}).get("textos", 0)}
    alertas, acciones = [], []

    # ---------- brecha de figura
    fq = {f["nombre"]: f["pct"] for f in q.get("figuras", [])}
    fl = L.get("figuras") or {}
    figs = []
    for n in sorted(set(fq) | {k for k, v in fl.items() if v.get("n")}):
        af, sov = fq.get(n, 0.0), (fl.get(n) or {}).get("sov") or 0.0
        figs.append({"nombre": n, "afinidad": af, "sov": sov, "brecha": round(af - sov, 1),
                     "tono": ((fl.get(n) or {}).get("tono") or {}).get("neto"), "n": (fl.get(n) or {}).get("n", 0)})
    figs.sort(key=lambda x: -x["brecha"])
    out["figuras"] = figs
    if q and fl:
        sin_voz = [f for f in figs if f["afinidad"] >= 3 and f["brecha"] >= 3][:3]
        ruido = sorted([f for f in figs if f["sov"] >= 5 and f["brecha"] <= -5], key=lambda x: x["brecha"])[:3]
        for f in sin_voz:
            acciones.append({"accion": f"Hay un público que piensa como {f['nombre']} y casi no escucha a nadie con ese perfil en redes: es un espacio para ocupar.",
                             "metrica": f"{f['afinidad']}% del quiz tiene a {f['nombre']} como figura más cercana; su share of voice es {f['sov']}%."})
        for f in ruido:
            acciones.append({"accion": f"{f['nombre']} domina la conversación por encima de su base de afinidad: más ruido que representación.",
                             "metrica": f"Share of voice {f['sov']}% vs. {f['afinidad']}% de afinidad en el quiz" + (f"; tono neto {f['tono']:+}." if f["tono"] is not None else ".")})

    # ---------- brecha de postura y agenda
    ejes = []
    le = L.get("ejes") or {}
    for eid, e in EJES.items():
        qm = ((q.get("ejes") or {}).get(eid) or {})
        lm = le.get(eid) or {}
        enc = (lm.get("encuadre") or {}).get("b_pct")
        row = {"id": eid, "nombre": e["nombre"], "a": e["a"], "b": e["b"], "quiz": qm.get("m"), "sd": qm.get("sd"),
               "extremos": round((qm.get("a") or 0) + (qm.get("b") or 0), 1) if qm else None,
               "encuadre": enc, "share": lm.get("share"), "n": lm.get("n", 0), "tono": (lm.get("tono") or {}).get("neto")}
        row["brecha"] = round(enc - row["quiz"], 1) if enc is not None and row["quiz"] is not None else None
        ejes.append(row)
    out["ejes"] = ejes
    con_b = [e for e in ejes if e["brecha"] is not None]
    for e in sorted(con_b, key=lambda x: -abs(x["brecha"]))[:3]:
        if abs(e["brecha"]) >= 12:
            hacia = e["b"] if e["brecha"] > 0 else e["a"]
            alertas.append({"nivel": "alta" if abs(e["brecha"]) >= 25 else "media",
                            "t": f"{e['nombre']}: la conversación se encuadra hacia {hacia} {abs(e['brecha']):.0f} puntos más que lo que piensa la gente en el quiz."})
            acciones.append({"accion": f"En {e['nombre'].lower()}, no confundir el clima de redes con la opinión: el encuadre dominante ({hacia}) está sobrerrepresentado.",
                             "metrica": f"Encuadre {e['encuadre']:.0f}/100 hacia {e['b']} en redes vs. {e['quiz']:.0f}/100 en el quiz."})
    if all(e["extremos"] is not None and e["share"] is not None for e in ejes) and ejes:
        vac = sorted(ejes, key=lambda x: (x["share"] or 0) - (x["extremos"] or 0) / 4)[:2]
        for e in vac:
            acciones.append({"accion": f"Agenda vacante: {e['nombre'].lower()} divide a la gente pero casi no se discute. Quien lo plantee primero define el encuadre.",
                             "metrica": f"{e['extremos']:.0f}% de quienes respondieron toma posición fuerte en este eje; es el {e['share']:.0f}% de la conversación."})
    out["agenda"] = sorted([{"id": e["id"], "nombre": e["nombre"], "divide": e["extremos"], "se_habla": e["share"]} for e in ejes],
                           key=lambda x: -(x["divide"] or 0))

    # ---------- plataformas
    plats = []
    por_red = (q.get("por") or {}).get("red") or {}
    lp = L.get("plataformas") or {}
    for red, seg in por_red.items():
        p = RED_A_PLAT.get(red)
        lt = (lp.get(p) or {}).get("tono") or {}
        plats.append({"red": red, "n_quiz": seg["n"], "perfil": {k: v["m"] for k, v in seg["ejes"].items()},
                      "figura": (seg.get("figuras") or [{}])[0].get("nombre"), "plataforma": p,
                      "tono": lt.get("neto"), "agresivo": lt.get("agresivo"), "textos": lt.get("n")})
    out["plataformas"] = plats
    if len(plats) >= 2:
        m = q.get("ejes") or {}
        for k in ("eco", "soc", "ins"):
            if k not in m:
                continue
            mx = max(plats, key=lambda x: abs(x["perfil"][k] - m[k]["m"]))
            d = mx["perfil"][k] - m[k]["m"]
            if abs(d) >= 6:
                acciones.append({"accion": f"Quien se informa por {mx['red']} está más cerca de {polo(k, 50 + d)} en {EJES[k]['nombre'].lower()} que el promedio: ajustar el mensaje por red, no copiar y pegar.",
                                 "metrica": f"{mx['perfil'][k]:.0f}/100 vs. {m[k]['m']:.0f}/100 del total ({EJES[k]['a']} 0 · {EJES[k]['b']} 100), n = {mx['n_quiz']}."})

    # ---------- anuncios × demografía del quiz
    eg = {(c["edad_g"], c["genero"]): c["ejes"] for c in q.get("edad_genero", [])}
    ads = []
    for eid, ad in (L.get("anuncios") or {}).items():
        if not ad.get("demo") or eid not in EJES:
            continue
        acc, tot = 0.0, 0.0
        cells = {}
        for d in ad["demo"]:
            key = (AD_EDAD.get(d["edad"]), d["genero"])
            cells[key] = cells.get(key, 0) + d["pct"]
            if key in eg:
                acc += d["pct"] * eg[key][eid]
                tot += d["pct"]
        top = sorted(cells.items(), key=lambda x: -x[1])[:2]
        row = {"id": eid, "nombre": EJES[eid]["nombre"], "avisos": ad["avisos"],
               "publico": [{"edad": k[0], "genero": k[1], "pct": round(v, 1)} for k, v in top if k[0]],
               "posicion_publico": round(acc / tot, 1) if tot else None, "posicion_total": ((q.get("ejes") or {}).get(eid) or {}).get("m")}
        ads.append(row)
        if row["posicion_publico"] is not None and row["posicion_total"] is not None and abs(row["posicion_publico"] - row["posicion_total"]) >= 4:
            d = row["posicion_publico"] - row["posicion_total"]
            acciones.append({"accion": f"Los avisos sobre {EJES[eid]['nombre'].lower()} le llegan a un público que ya se inclina hacia {polo(eid, 50 + d)}: se le habla al convencido.",
                             "metrica": f"Posición del público alcanzado {row['posicion_publico']:.0f}/100 vs. {row['posicion_total']:.0f}/100 del total; {ad['avisos']} avisos."})
    out["anuncios"] = ads

    # ---------- picos de conversación
    for n, f in fl.items():
        if f.get("ult7", 0) >= 20 and f["ult7"] >= 2 * max(f.get("prev7", 0), 1):
            alertas.append({"nivel": "media", "t": f"{n}: {f['ult7']} menciones en 7 días, {f['ult7'] / max(f.get('prev7', 0), 1):.1f}× la semana anterior."})
    if q:
        dias = sorted((Q.get("campo") or {}).get("por_dia") or {})
        if dias and (datetime.now(timezone.utc) - datetime.fromisoformat(dias[-1] + "T00:00:00+00:00")).days > 14 and alertas:
            alertas.append({"nivel": "alta", "t": "La conversación se movió y la última respuesta del quiz tiene más de dos semanas: hace falta medir de nuevo."})
    else:
        alertas.append({"nivel": "info", "t": "Todavía no hay respuestas del quiz suficientes para cruzar: el tablero muestra solo la conversación."})
    coma = lambda t: re.sub(r"(\d)\.(\d)", r"\1,\2", t)  # noqa: E731  (decimales en castellano)
    out["alertas"] = [dict(x, t=coma(x["t"])) for x in alertas]
    out["acciones"] = [{"accion": coma(x["accion"]), "metrica": coma(x["metrica"])} for x in acciones[:8]]
    out["metodo"] = {
        "figuras": "Afinidad = % de respuestas cuyo dirigente más cercano es esa figura. sov = % de menciones entre los dirigentes del quiz. brecha = afinidad − sov.",
        "postura": "Quiz: puntaje medio 0-100 (polo a → polo b). Conversación: % de textos con encuadre del polo b entre los que tienen encuadre. brecha = conversación − quiz.",
        "agenda": "divide = % con posición fuerte (< 40 o > 60) en el eje; se_habla = % de la conversación sobre los 8 ejes.",
        "plataformas": "Perfil en el quiz de quienes eligen cada red como su fuente principal, contra el tono de esa red en el listener (YouTube, X y medios; Instagram, Facebook y TikTok no tienen búsqueda abierta).",
        "anuncios": "Público de los avisos por edad y género (Meta) cruzado con la posición media de ese mismo grupo en el quiz.",
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf8")
    print(f"cruce: {len(acciones)} acciones, {len(alertas)} alertas -> {a.out}", flush=True)


if __name__ == "__main__":
    main()
