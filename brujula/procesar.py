"""Brújula · respuestas del quiz -> brujula/data/quiz.json (solo agregados, nunca respuestas individuales).

Lee las respuestas de la planilla privada (Apps Script) con QUIZ_ENDPOINT y QUIZ_TOKEN, recalcula cada puntaje
con datos/preguntas.json (no confía en lo que manda el navegador), descarta respuestas de mala calidad,
pondera si hay marginales cargadas y publica solo grupos con n >= MIN_N.

    QUIZ_ENDPOINT=... QUIZ_TOKEN=... python brujula/procesar.py
    python brujula/procesar.py --json respuestas.json      # archivo local con {"cols": [...], "rows": [...]}
    python brujula/procesar.py --demo 1500 --out /tmp/q.json  # datos simulados para probar (nunca a data/)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
EJES = json.loads((HERE / "datos" / "ejes.json").read_text(encoding="utf8"))
PREG = {q["id"]: q for q in json.loads((HERE / "datos" / "preguntas.json").read_text(encoding="utf8"))["preguntas"]}
FIG = json.loads((HERE / "datos" / "figuras.json").read_text(encoding="utf8"))
MARG = HERE / "datos" / "marginales_ar.json"
K = [e["id"] for e in EJES["ejes"]]
MIN_N = int(os.environ.get("BRUJULA_MIN_N", "30"))
SEG_S_POR_PREG = 2.5  # menos de 2,5 segundos por pregunta en promedio = no leyó
REGION = {
    "CABA": "AMBA", "Buenos Aires: conurbano": "AMBA", "Buenos Aires: interior": "Pampeana", "Córdoba": "Pampeana",
    "Santa Fe": "Pampeana", "Entre Ríos": "Pampeana", "La Pampa": "Pampeana", "Jujuy": "NOA", "Salta": "NOA",
    "Tucumán": "NOA", "Catamarca": "NOA", "Santiago del Estero": "NOA", "La Rioja": "NOA", "Misiones": "NEA",
    "Corrientes": "NEA", "Chaco": "NEA", "Formosa": "NEA", "Mendoza": "Cuyo", "San Juan": "Cuyo", "San Luis": "Cuyo",
    "Neuquén": "Patagonia", "Río Negro": "Patagonia", "Chubut": "Patagonia", "Santa Cruz": "Patagonia", "Tierra del Fuego": "Patagonia",
}
EDAD_G = {"16-17": "16-24", "18-24": "16-24", "25-34": "25-34", "35-44": "35-49", "45-54": "35-49", "55-64": "50+", "65+": "50+"}


# ------------------------------------------------------------------ cálculo (mismo criterio que quiz.js)
def calcular(ids, ans):
    """Posición 0-100 por eje (0 = polo a) y certeza 0-100 = decisión × coherencia.
    Decisión: neutral 0, de acuerdo / en desacuerdo 0,75, muy 1 (promedio ponderado por peso).
    Coherencia (modelo acumulativo de 12axes): una frase de nivel L hacia un polo la aceptan quienes están del lado de ese polo
    al menos (L - 1) × 12,5 puntos más allá del centro. Cada respuesta que coincide con lo esperado para su posición suma,
    cada una que contradice resta."""
    qs = [(PREG[q], a) for q, a in zip(ids, ans) if q in PREG]
    Sm, M, D, W = defaultdict(float), defaultdict(float), defaultdict(float), defaultdict(float)
    for q, a in qs:
        for k, w in q["e"].items():
            Sm[k] += a * w
            M[k] += 2 * abs(w)
            D[k] += abs(w) * (0 if a == 0 else .75 if abs(a) == 1 else 1)
            W[k] += abs(w)
    sc = {k: (50 + 50 * Sm[k] / M[k]) if M[k] else 50.0 for k in K}
    cert = {}
    for k in K:
        num = den = 0.0
        for q, a in qs:
            w = q["e"].get(k)
            if not w or not a:
                continue
            nivel = q.get("nivel") or (3 if abs(w) >= 2 else 1)
            pred = 1 if math.copysign(1, w) * (sc[k] - 50) - (nivel - 1) * 12.5 >= 0 else -1
            num += (1 if math.copysign(1, a) == pred else -1) * abs(w) * abs(a)
            den += abs(w) * abs(a)
        d = D[k] / W[k] if W[k] else 0.0
        cert[k] = 100 * d * max(0.0, num / den if den else 0.0)
    return sc, cert


def puntajes(ids, ans):
    return calcular(ids, ans)[0]


def afinidad(sc, pos, cert=None):
    """100 - 2 × distancia media ponderada por certeza (los ejes donde la persona duda pesan menos)."""
    c = {k: 0.3 + 0.7 * ((cert or {}).get(k, 50) / 100) for k in K}
    return max(0.0, 100 - 2 * sum(c[k] * abs(sc[k] - pos[k]) for k in K) / sum(c.values()))


# ------------------------------------------------------------------ lectura
def leer(args):
    if args.demo:
        return simular(args.demo)
    if args.json:
        d = json.loads(Path(args.json).read_text(encoding="utf8"))
    else:
        ep, tok = os.environ.get("QUIZ_ENDPOINT", "").strip(), os.environ.get("QUIZ_TOKEN", "").strip()
        if not ep or not tok:
            print("procesar: faltan QUIZ_ENDPOINT y QUIZ_TOKEN; se publica el estado sin respuestas", flush=True)
            return []
        with urllib.request.urlopen(ep + ("&" if "?" in ep else "?") + urllib.parse.urlencode({"token": tok}), timeout=120) as r:
            d = json.loads(r.read().decode("utf8"))
        if not d.get("ok"):
            raise SystemExit("procesar: el Apps Script rechazó el token")
    cols = d["cols"]
    return [dict(zip(cols, r)) for r in d["rows"]]


SIM_VER = {"ar": ("Argentina", 70), "br": ("Brasil", 12), "cl": ("Chile", 4), "co": ("Colombia", 4), "pe": ("Perú", 3),
           "py": ("Paraguay", 2), "uy": ("Uruguay", 2), "general": ("Argentina", 3)}


def simular(n, seed=7):
    """Respuestas simuladas con estructura demográfica plausible. Solo para probar el pipeline y el tablero."""
    rnd = random.Random(seed)
    vers = list(SIM_VER)
    ids_v = {v: [q for q, d in PREG.items() if v in d["v"]] for v in vers}
    rows = []
    provs = list(REGION)
    for i in range(n):
        ver = rnd.choices(vers, [SIM_VER[v][1] for v in vers])[0]
        pais = SIM_VER[ver][0]
        edad = rnd.choices(list(EDAD_G), [3, 18, 22, 18, 15, 13, 11])[0]
        gen = rnd.choices(["Mujer", "Varón", "No binario / otro", "Prefiero no decir"], [49, 47, 2, 2])[0]
        joven = edad in ("16-17", "18-24", "25-34")
        # sesgo simulado: varones jóvenes más pro mercado y autoridad; mujeres jóvenes más progresistas y laicas
        g = rnd.gauss(0, 0.7)  # eje izquierda-derecha general que correlaciona varios ejes
        lat = {k: rnd.gauss(0, 0.6) for k in K}
        for k, s_ in {"pla": 1, "col": .8, "glo": .7, "pro": .6, "rel": .5, "lib": -.4, "int": .4, "mig": -.3}.items():
            lat[k] += s_ * g
        if joven and gen == "Varón":
            lat["pla"] += .8; lat["col"] += .5; lat["dem"] += .5; lat["pro"] += .3; lat["tec"] -= .3
        if joven and gen == "Mujer":
            lat["pro"] -= .9; lat["rel"] -= .6; lat["pla"] -= .3; lat["mig"] += .3
        if edad in ("55-64", "65+"):
            lat["dem"] -= .4; lat["lib"] -= .4; lat["rel"] += .3
        firmeza = rnd.uniform(.5, 1.5)
        ans = []
        for q in ids_v[ver]:
            s_ = sum(w * lat[k] for k, w in PREG[q]["e"].items()) * firmeza
            ans.append(max(-2, min(2, round(s_ + rnd.gauss(0, .9)))))
        red = rnd.choices(["Instagram", "X (Twitter)", "TikTok", "YouTube", "Facebook", "WhatsApp / Telegram", "Ninguna: medios tradicionales"],
                          [30, 15, 18, 12, 12, 8, 5] if joven else [18, 10, 4, 12, 30, 16, 10])[0]
        prov = rnd.choices(provs, [8, 30, 12] + [2] * (len(provs) - 3))[0] if pais == "Argentina" else ""
        rows.append({"recibido": f"2026-11-{rnd.randint(1, 23):02d}T{rnd.randint(0, 23):02d}:00Z", "schema": 2, "version": ver,
                     "lang": "pt" if ver == "br" else "es", "ids": ",".join(ids_v[ver]), "ans": ",".join(map(str, ans)),
                     "dur_s": rnd.randint(90, 900), "cid_hash": f"{rnd.getrandbits(48):012x}", "edad": edad, "genero": gen,
                     "pais_res": pais, "prov": prov, "pais_nac": pais, "red": red})
    return rows


# ------------------------------------------------------------------ limpieza
def limpiar(rows):
    motivos, ok, vistos = Counter(), [], {}
    for r in rows:
        try:
            ids = str(r["ids"]).split(",")
            ans = [int(x) for x in str(r["ans"]).split(",")]
        except (KeyError, ValueError):
            motivos["formato"] += 1
            continue
        if len(ids) != len(ans) or len(ids) < 20:
            motivos["incompleta"] += 1
            continue
        if float(r.get("dur_s") or 0) < SEG_S_POR_PREG * len(ids):
            motivos["demasiado rápida"] += 1
            continue
        if len(set(ans)) == 1:
            motivos["misma respuesta en todo"] += 1
            continue
        if sum(1 for a in ans if a == 0) > 0.6 * len(ans):
            motivos["mayoría neutral"] += 1
            continue
        sc, cert = calcular(ids, ans)
        r = dict(r, _sc=sc, _cert=cert, _ids=ids, _ans=ans)
        if r.get("pais_res") == "Argentina":
            r["region"] = REGION.get(r.get("prov") or "", "Sin dato")
        else:
            r["region"] = r.get("prov") or ("Sin dato" if r.get("pais_res") else "Sin dato")
        r["edad_g"] = EDAD_G.get(r.get("edad"), "Sin dato")
        c = r.get("cid_hash")
        if c and c in vistos:  # misma persona (mismo navegador): vale la última respuesta
            motivos["duplicada"] += 1
            ok[vistos[c]] = r
            continue
        if c:
            vistos[c] = len(ok)
        ok.append(r)
    return ok, motivos


# ------------------------------------------------------------------ ponderación (raking / IPF)
def raking(rows, marg, iters=50, lo=0.2, hi=5.0):
    """marg = {"variable": {"categoria": proporción}}. Devuelve pesos con media 1, recortados a [lo, hi]."""
    w = np.ones(len(rows))
    for _ in range(iters):
        for var, obj in marg.items():
            cats = np.array([r.get(var) for r in rows])
            known = np.isin(cats, list(obj))  # quien no contestó esa variable queda fuera de ese ajuste
            tot = w[known].sum()
            for c, p in obj.items():
                m = cats == c
                if m.any() and w[m].sum() > 0:
                    w[m] *= p * tot / w[m].sum()
        w = np.clip(w / w.mean(), lo, hi)
    return w / w.mean()


def n_efectivo(w):
    return float(w.sum() ** 2 / (w ** 2).sum()) if len(w) else 0.0


# ------------------------------------------------------------------ agregados
def medias(rows, w):
    if not rows:
        return {}
    X = np.array([[r["_sc"][k] for k in K] for r in rows])
    C = np.array([[r["_cert"][k] for k in K] for r in rows])
    ww = w / w.sum()
    m = (X * ww[:, None]).sum(0)
    cm = (C * ww[:, None]).sum(0)
    var = ((X - m) ** 2 * ww[:, None]).sum(0)
    ne = n_efectivo(w)
    half = 1.96 * np.sqrt(var / max(ne, 1))
    return {k: {"m": round(float(m[i]), 1), "ci": round(float(half[i]), 1), "sd": round(float(math.sqrt(var[i])), 1),
                "a": round(float((X[:, i] < 40).astype(float) @ ww * 100), 1), "b": round(float((X[:, i] > 60).astype(float) @ ww * 100), 1),
                "cert": round(float(cm[i]), 1)}
            for i, k in enumerate(K)}


def certeza(rows, w):
    if not rows:
        return None
    c = np.array([sum(r["_cert"].values()) / len(K) for r in rows])
    return round(float(c @ (w / w.sum())), 1)


def top_figuras(rows, w, ver):
    figs = FIG[EJES["versiones"][ver]["figuras"]]
    c = Counter()
    for r, wi in zip(rows, w):
        best = max(figs, key=lambda f: afinidad(r["_sc"], f["pos"], r["_cert"]))
        c[best["nombre"]] += wi
    tot = sum(c.values()) or 1
    return [{"nombre": n, "pct": round(100 * v / tot, 1)} for n, v in c.most_common()]


def segmento(rows, w, var, ver):
    out = {}
    groups = defaultdict(list)
    for i, r in enumerate(rows):
        groups[r.get(var) or "Sin dato"].append(i)
    for g, idx in sorted(groups.items()):
        if len(idx) < MIN_N or g in ("Sin dato", "Prefiero no decir"):
            continue
        sub, ws = [rows[i] for i in idx], w[idx]
        out[g] = {"n": len(idx), "certeza": certeza(sub, ws), "ejes": medias(sub, ws), "figuras": top_figuras(sub, ws, ver)[:5]}
    return out


def cruce(rows, w, v1, v2):
    cells = defaultdict(list)
    for i, r in enumerate(rows):
        cells[(r.get(v1), r.get(v2))].append(i)
    out = []
    for (a, b), idx in sorted(cells.items(), key=lambda x: (str(x[0][0]), str(x[0][1]))):
        if len(idx) >= MIN_N and a not in (None, "Sin dato") and b not in (None, "Sin dato", "Prefiero no decir"):
            out.append({v1: a, v2: b, "n": len(idx), "ejes": {k: v["m"] for k, v in medias([rows[i] for i in idx], w[idx]).items()}})
    return out


def preguntas(rows, w):
    """% de acuerdo por pregunta y brechas entre grupos (solo con n >= MIN_N de cada lado)."""
    acc = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))  # qid -> grupo -> [acuerdo, total]
    for r, wi in zip(rows, w):
        grupos = ["Total", "g:" + str(r.get("genero")), "e:" + r["edad_g"]]
        if r.get("genero") in ("Mujer", "Varón") and r["edad_g"] in ("16-24", "25-34"):
            grupos.append("ge:" + r["genero"] + " joven")
        for q, a in zip(r["_ids"], r["_ans"]):
            for g in grupos:
                acc[q][g][0] += wi * (a > 0)
                acc[q][g][1] += wi
    ns = Counter()
    for r in rows:
        ns["g:" + str(r.get("genero"))] += 1
        ns["e:" + r["edad_g"]] += 1
        if r.get("genero") in ("Mujer", "Varón") and r["edad_g"] in ("16-24", "25-34"):
            ns["ge:" + r["genero"] + " joven"] += 1
    out = []
    for q, gs in acc.items():
        tot = gs["Total"]
        if not tot[1] or q not in PREG:
            continue
        p = lambda g: round(100 * gs[g][0] / gs[g][1], 1) if gs[g][1] and ns[g] >= MIN_N else None  # noqa: E731
        row = {"id": q, "t": PREG[q]["t"], "ejes": list(PREG[q]["e"]), "acuerdo": round(100 * tot[0] / tot[1], 1),
               "mujer": p("g:Mujer"), "varon": p("g:Varón"), "jov": p("e:16-24"), "may": p("e:50+"),
               "mujer_joven": p("ge:Mujer joven"), "varon_joven": p("ge:Varón joven")}
        row["brecha_genero"] = round(row["varon"] - row["mujer"], 1) if row["varon"] is not None and row["mujer"] is not None else None
        row["brecha_edad"] = round(row["jov"] - row["may"], 1) if row["jov"] is not None and row["may"] is not None else None
        row["brecha_jovenes"] = (round(row["varon_joven"] - row["mujer_joven"], 1)
                                 if row["varon_joven"] is not None and row["mujer_joven"] is not None else None)
        out.append(row)
    return sorted(out, key=lambda x: x["id"])


def kmeans(X, k=4, iters=60, seed=3):
    rng = np.random.default_rng(seed)
    C = X[rng.choice(len(X), 1)]
    while len(C) < k:  # k-means++
        d = ((X[:, None, :] - C[None]) ** 2).sum(-1).min(1)
        C = np.vstack([C, X[rng.choice(len(X), 1, p=d / d.sum())]])
    for _ in range(iters):
        lab = ((X[:, None, :] - C[None]) ** 2).sum(-1).argmin(1)
        C2 = np.array([X[lab == j].mean(0) if (lab == j).any() else C[j] for j in range(k)])
        if np.allclose(C, C2):
            break
        C = C2
    return lab, C


def segmentos(rows, w, ver):
    if len(rows) < 5 * MIN_N:
        return []
    X = np.array([[r["_sc"][k] for k in K] for r in rows])
    lab, C = kmeans(X, 4)
    out = []
    for j in range(4):
        idx = np.where(lab == j)[0]
        if len(idx) < MIN_N:
            continue
        cen = {k: round(float(C[j][i]), 1) for i, k in enumerate(K)}
        polos = sorted(EJES["ejes"], key=lambda e: -abs(cen[e["id"]] - 50))
        nombre = " + ".join((e["b"] if cen[e["id"]] > 50 else e["a"]) for e in polos[:2])
        if any(o["nombre"] == nombre for o in out):  # dos tribus con los mismos dos polos: se suma el tercero
            nombre += " + " + (polos[2]["b"] if cen[polos[2]["id"]] > 50 else polos[2]["a"])
        sub = [rows[i] for i in idx]
        comp = {}
        for var in ("genero", "edad_g", "region", "red"):
            c = Counter(r.get(var) or "Sin dato" for r in sub)
            comp[var] = {g: round(100 * v / len(sub), 1) for g, v in c.most_common()}
        out.append({"nombre": nombre, "n": int(len(idx)), "pct": round(100 * float(w[idx].sum() / w.sum()), 1), "centro": cen,
                    "composicion": comp, "figuras": top_figuras(sub, w[idx], ver)[:3]})
    return sorted(out, key=lambda s: -s["pct"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--demo", type=int, default=0)
    ap.add_argument("--out", default=str(HERE / "data" / "quiz.json"))
    args = ap.parse_args()
    if args.demo and Path(args.out).resolve() == (HERE / "data" / "quiz.json").resolve():
        sys.exit("procesar: los datos simulados nunca se escriben en data/quiz.json")
    try:
        crudas = leer(args)
    except Exception as e:  # el Apps Script no responde: conservar el último agregado bueno
        print(f"procesar: no se pudieron leer respuestas ({type(e).__name__}: {str(e)[:120]}); se conserva el agregado anterior", flush=True)
        return
    rows, motivos = limpiar(crudas)
    por_ver = Counter(r["version"] for r in rows)
    out = {"updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "simulado": bool(args.demo), "min_n": MIN_N,
           "campo": {"recibidas": len(crudas), "validas": len(rows), "descartes": dict(motivos), "por_version": dict(por_ver),
                     "por_dia": dict(sorted(Counter(str(r.get("recibido", ""))[:10] for r in rows).items()))},
           "versiones": {}}
    for ver in [v for v in por_ver if v in EJES["versiones"]]:
        rs = [r for r in rows if r["version"] == ver]
        w = np.ones(len(rs))
        pond = "sin ponderar"
        if ver == "ar" and MARG.exists():
            marg = json.loads(MARG.read_text(encoding="utf8"))
            # se usa cada variable que al menos el 80% contestó (los datos son opcionales)
            usable = {v: obj for v, obj in marg.get("marginales", {}).items()
                      if sum(r.get(v) in obj for r in rs) >= 0.8 * len(rs)}
            if usable:
                w = raking(rs, usable)
                pond = "raking a " + ", ".join(usable) + f" ({marg.get('fuente', 'marginales')})"
        out["versiones"][ver] = {
            "n": len(rs), "n_efectivo": round(n_efectivo(w)), "ponderacion": pond,
            "certeza": certeza(rs, w), "ejes": medias(rs, w), "figuras": top_figuras(rs, w, ver),
            "por": {var: segmento(rs, w, var, ver) for var in ("genero", "edad_g", "region", "red", "pais_res")},
            "edad_genero": cruce(rs, w, "edad_g", "genero"),
            "region_edad": cruce(rs, w, "region", "edad_g"),
            "preguntas": preguntas(rs, w) if len(rs) >= MIN_N else [],
            "segmentos": segmentos(rs, w, ver),
        }
    out["metodo"] = {
        "muestra": "Autoselección online (quien entra al quiz y acepta sumar sus respuestas). No es una muestra probabilística: los resultados describen a quienes respondieron y, ponderados, se acercan a la población; el intervalo es de referencia.",
        "puntaje": "12 ejes (preguntas base adaptadas de 12axes, MIT). Cada eje: 50 + 50 × (suma de respuesta × peso) / (suma de 2 × |peso|). 0 = polo a, 100 = polo b. a / b = % con puntaje < 40 / > 60.",
        "certeza": "Certeza por eje (0-100) = decisión (qué tan lejos de neutral responde) × coherencia (acuerdo con frases cuyo nivel queda cerca de su posición y desacuerdo con las lejanas).",
        "calidad": f"Se descartan respuestas con menos de {SEG_S_POR_PREG} s por pregunta, misma respuesta en todo, más de 60% neutral, incompletas y duplicadas por navegador (vale la última).",
        "publicacion": f"Solo grupos con {MIN_N} respuestas o más. Intervalo 95% con n efectivo de Kish.",
        "afinidad": "Dirigente más cercano = menor distancia promedio en los 12 ejes, ponderada por la certeza de cada persona, contra la codificación editorial de datos/figuras.json (a revisar).",
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf8")
    print(f"procesar: {len(crudas)} recibidas, {len(rows)} válidas -> {args.out}", flush=True)


if __name__ == "__main__":
    main()
