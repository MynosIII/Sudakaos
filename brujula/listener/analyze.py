"""Brújula · social listener: .store (textos) -> brujula/data/listener.json (solo agregados).

Por eje del quiz: volumen, tono, agresividad, plataforma, serie semanal y encuadre (hacia qué polo se inclina
la conversación según palabras de encuadre de listener/config.json). Por dirigente: menciones, share of voice,
tono e Instagram (si meta/ lo recolectó). Por tema en anuncios de Meta: a quién le llegan (edad y género).
Tono, emoción y agresividad con radar/nlp.py (pysentimiento si está instalado; si no, diccionarios).
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "radar"))
import nlp  # noqa: E402

CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf8"))
FIG = json.loads((HERE.parent / "datos" / "figuras.json").read_text(encoding="utf8"))["ar"]
EJES = json.loads((HERE.parent / "datos" / "ejes.json").read_text(encoding="utf8"))["ejes"]
STORE = Path(os.environ.get("BRUJULA_STORE", HERE / ".store"))
OUT = Path(os.environ.get("BRUJULA_LISTENER_OUT", HERE.parent / "data" / "listener.json"))
NOW = datetime.now(timezone.utc)
MIN_N = 20  # índices de tono/encuadre solo con al menos 20 textos


def fold(s):
    s = "".join(c for c in unicodedata.normalize("NFD", (s or "").lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9ñ]+", " ", re.sub(r"https?://\S+", " ", s)).strip()


def rx(terms):
    return re.compile(r"\b(?:" + "|".join(re.escape(fold(t)) for t in terms) + r")", re.I)


def pct(a, b):
    return round(100 * a / b, 1) if b else None


def load():
    p = STORE / "items.jsonl"
    rows = []
    if p.exists():
        for line in p.read_text(encoding="utf8").splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    return rows


# --------------------------------------------------------------- dirigentes: alias sin pisarse (Macri / Jorge Macri)
ALIAS = sorted(((fold(a), f["nombre"]) for f in FIG for a in [f["nombre"], *f.get("alias", [])]), key=lambda x: -len(x[0]))


def figuras_en(clean):
    s, out = f" {clean} ", set()
    for a, nombre in ALIAS:
        pat = f" {a} "
        if pat in s:
            out.add(nombre)
            s = s.replace(pat, "   ")  # el alias más largo consume el texto: "jorge macri" no suma a Mauricio
    return out


def tono_pack(df):
    n = len(df)
    if not n:
        return {"n": 0}
    c = df["tono"].value_counts()
    o = {"n": int(n), "pos": pct(c.get("POS", 0), n), "neu": pct(c.get("NEU", 0), n), "neg": pct(c.get("NEG", 0), n),
         "agresivo": pct(int(df["agresivo"].sum()), n)}
    o["neto"] = round((o["pos"] or 0) - (o["neg"] or 0), 1)
    return o


def semanas(df):
    if df.empty:
        return {}
    w = df["ts"].dt.tz_convert(None).dt.to_period("W-SUN").dt.start_time.dt.strftime("%Y-%m-%d")
    return {k: int(v) for k, v in w.value_counts().sort_index().items()}


def ads_demo(df):
    """Distribución por edad y género de las impresiones de avisos políticos de cada tema (Biblioteca de Anuncios)."""
    out = {}
    for eje, g in df.groupby("eje_tag"):
        acc, tot, paginas, n = defaultdict(float), 0.0, Counter(), 0
        for _, r in g.iterrows():
            imp = r.get("impressions") or {}
            try:
                mid = (float(imp.get("lower_bound", 0)) + float(imp.get("upper_bound", imp.get("lower_bound", 0)))) / 2
            except (TypeError, ValueError, AttributeError):
                mid = 0
            n += 1
            paginas[r.get("channel") or "—"] += 1
            for d in r.get("demo") or []:
                try:
                    w = float(d.get("percentage", 0)) * max(mid, 1)
                except (TypeError, ValueError):
                    continue
                acc[(d.get("age", "?"), d.get("gender", "?"))] += w
                tot += w
        if n:
            out[eje] = {"avisos": n, "paginas": [{"p": p, "n": k} for p, k in paginas.most_common(6)],
                        "demo": [{"edad": a, "genero": {"female": "Mujer", "male": "Varón"}.get(gn, "Otro"), "pct": round(100 * v / tot, 1)}
                                 for (a, gn), v in sorted(acc.items())] if tot else []}
    return out


def main():
    rows = load()
    status = json.loads((STORE / "status.json").read_text(encoding="utf8")) if (STORE / "status.json").exists() else {}
    prev = json.loads(OUT.read_text(encoding="utf8")) if OUT.exists() else {}
    if not rows:
        print("listener: sin textos en .store; se conserva el último agregado", flush=True)
        if prev:
            prev["status"] = status or prev.get("status", {})
            OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1), encoding="utf8")
        return
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    df = df[df["ts"] >= pd.Timestamp(NOW - timedelta(days=CONFIG["window_days"]))].copy()
    df["text"] = df["text"].fillna("")
    df["clean"] = df["text"].map(fold)
    df["lang"] = "es"
    df = df[df["clean"].str.len() > 8].drop_duplicates(subset=["platform", "clean"]).reset_index(drop=True)
    df = nlp.label(df, STORE / "nlp.jsonl.gz")
    df["eje_tag"] = df.get("tag", pd.Series([""] * len(df))).fillna("").str.extract(r"tema:(\w+)")[0]

    # ejes: un texto cuenta para un eje si nombra sus palabras clave (o vino de una búsqueda del tema y las nombra)
    ejes_out, matches = {}, {}
    for e in EJES:
        t = CONFIG["temas"][e["id"]]
        kw, ra, rb = rx(t["kw"]), rx(t["a"]), rx(t["b"])
        m = df["clean"].str.contains(kw)
        matches[e["id"]] = m
        sub = df[m]
        na = int(sub["clean"].str.contains(ra).sum())
        nb = int(sub["clean"].str.contains(rb).sum())
        tit = sub[(sub["platform"] == "Medios")].sort_values("ts", ascending=False).head(6)
        ejes_out[e["id"]] = {
            "n": int(m.sum()), "tono": tono_pack(sub),
            "encuadre": {"a": na, "b": nb, "b_pct": pct(nb, na + nb) if na + nb >= MIN_N else None},
            "plataformas": {k: int(v) for k, v in sub["platform"].value_counts().items()},
            "semanas": semanas(sub),
            "titulares": [{"t": r["title"], "medio": r.get("channel", ""), "url": r["url"], "f": r["created_at"][:10]}
                          for _, r in tit.iterrows() if r.get("title")],
        }
    tot_ejes = sum(v["n"] for v in ejes_out.values()) or 1
    for v in ejes_out.values():
        v["share"] = pct(v["n"], tot_ejes)

    # dirigentes
    df["figs"] = df["clean"].map(figuras_en)
    fig_out = {}
    tot_m = sum(len(s) for s in df["figs"]) or 1
    ig = {}
    meta = ROOT / "meta" / "data" / "meta.json"
    if meta.exists():
        for d in json.loads(meta.read_text(encoding="utf8")).get("dirigentes", []):
            if d.get("ig"):
                ig[d["name"]] = {k: d["ig"].get(k) for k in ("usuario", "followers", "posts_30d", "er", "inter_med", "mejor_formato")}
    for f in FIG:
        sub = df[df["figs"].map(lambda s: f["nombre"] in s)]
        ult = sub[sub["ts"] >= pd.Timestamp(NOW - timedelta(days=7))]
        pre = sub[(sub["ts"] < pd.Timestamp(NOW - timedelta(days=7))) & (sub["ts"] >= pd.Timestamp(NOW - timedelta(days=14)))]
        fig_out[f["nombre"]] = {"n": int(len(sub)), "sov": pct(len(sub), tot_m), "tono": tono_pack(sub) if len(sub) >= MIN_N else {"n": int(len(sub))},
                                "ult7": int(len(ult)), "prev7": int(len(pre)),
                                "plataformas": {k: int(v) for k, v in sub["platform"].value_counts().items()},
                                "ejes": {e["id"]: int((matches[e["id"]] & df["figs"].map(lambda s: f["nombre"] in s)).sum()) for e in EJES},
                                **({"ig": ig[f["nombre"]]} if f["nombre"] in ig else {})}

    # plataformas
    plat = {}
    for p, g in df.groupby("platform"):
        plat[p] = {"tono": tono_pack(g), "ejes": {e["id"]: int(matches[e["id"]][g.index].sum()) for e in EJES}}

    ads = ads_demo(df[(df["platform"] == "Anuncios Meta") & df["eje_tag"].notna()]) if (df["platform"] == "Anuncios Meta").any() else prev.get("anuncios", {})
    out = {
        "updated_at": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
        "totales": {"textos": int(len(df)), "por_plataforma": {k: int(v) for k, v in df["platform"].value_counts().items()},
                    "por_tipo": {k: int(v) for k, v in df["kind"].value_counts().items()},
                    "desde": df["ts"].min().strftime("%Y-%m-%d"), "hasta": df["ts"].max().strftime("%Y-%m-%d"),
                    "metodo_nlp": {k: int(v) for k, v in df["metodo_nlp"].value_counts().items()}},
        "ejes": ejes_out, "figuras": fig_out, "plataformas": plat, "anuncios": ads,
        "metodo": {
            "ventana": f"Últimos {CONFIG['window_days']} días.",
            "ejes": "Un texto cuenta para un eje si nombra alguna de sus palabras clave (listener/config.json). Un mismo texto puede sumar a varios ejes.",
            "encuadre": f"Textos del eje con palabras de encuadre de cada polo; b_pct = % hacia el polo b. Solo con {MIN_N}+ textos con encuadre. Es un indicador de cómo se habla del tema, no de qué opina la gente.",
            "tono": "pysentimiento (RoBERTuito) en CPU; si no está, diccionarios. neto = % positivo − % negativo.",
            "figuras": "Menciones por nombre y alias; el alias más largo gana (Jorge Macri no suma a Mauricio Macri). sov = share of voice entre los dirigentes del quiz.",
            "anuncios": "Biblioteca de Anuncios de Meta (avisos políticos y de temas sociales en Argentina) con la búsqueda principal de cada eje. Distribución de impresiones por edad y género ponderada por el punto medio del rango de impresiones.",
            "fuentes": "Google News, YouTube (videos y comentarios), Biblioteca de Anuncios de Meta, Instagram (meta/) y X solo en corridas manuales.",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf8")
    print(f"listener: {len(df)} textos, {sum(1 for v in fig_out.values() if v['n'])} dirigentes con menciones", flush=True)


if __name__ == "__main__":
    main()
