"""Reporte mensual de Instagram por tablero (ig/config.json). Gratis, con el mismo token que meta/collect.py.

Usa Instagram Business Discovery (Graph API de Meta): solo cuentas profesionales públicas. Reutiliza get() de
meta/collect.py (mismo token META_TOKEN y cuenta META_IG_USER_ID) y, para las figuras que ya están en
meta/config.json, sus usuarios (primero el que meta/data/meta.json ya resolvió).

Guarda por cuenta todas las publicaciones desde "desde" en ig/store/<usuario>.json (fecha, likes, comentarios,
formato, link y primeras palabras del texto propio; nunca comentarios de usuarios). Cada corrida:
  1. refresca la primera página de cada cuenta (perfil y las 50 publicaciones más nuevas),
  2. sigue completando el historial de las cuentas a las que les falta, hasta "max_llamadas".
Si Meta corta por límite de llamadas, guarda lo que tiene y sigue al día siguiente.
Después arma ig/data/<tablero>.json con las figuras de cada tablero.

Uso local:  META_TOKEN=... META_IG_USER_ID=... python ig/collect.py
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
_spec = importlib.util.spec_from_file_location("meta_collect", ROOT / "meta" / "collect.py")
meta = importlib.util.module_from_spec(_spec)  # meta/collect.py: get(), token y cuenta propia
_spec.loader.exec_module(meta)

CFG = json.loads((HERE / "config.json").read_text(encoding="utf8"))
STORE = HERE / "store"
OUT = HERE / "data"
ART = timezone(timedelta(hours=-3))
LIMIT = 50
RATE = {4, 17, 32, 613, 80002}
FIELDS_POST = "id,caption,like_count,comments_count,timestamp,media_type,media_product_type,permalink"


class Corte(Exception):
    """Meta cortó por límite de llamadas o se terminó el presupuesto de la corrida."""


S = {"llamadas": 0, "corte": None}


def code_of(err):
    m = re.match(r"\s*(\d+):", err or "")
    return int(m.group(1)) if m else None


def page(user: str, after: str | None):
    if S["corte"]:
        raise Corte(S["corte"])
    if S["llamadas"] >= CFG.get("max_llamadas", 450):
        S["corte"] = "presupuesto de llamadas de la corrida"
        raise Corte(S["corte"])
    media = f"media.after({after}).limit({LIMIT})" if after else f"media.limit({LIMIT})"
    fields = f"business_discovery.username({user}){{username,name,followers_count,follows_count,media_count,{media}{{{FIELDS_POST}}}}}"
    S["llamadas"] += 1
    data, err = meta.get(meta.IG_USER, {"fields": fields}, tries=2)
    if err and code_of(err) in RATE:
        S["corte"] = f"límite de Meta ({err[:80]})"
        raise Corte(S["corte"])
    if not data or "business_discovery" not in data:
        return None, err or "sin datos"
    bd = data["business_discovery"]
    m = bd.get("media") or {}
    nxt = (m.get("paging") or {}).get("cursors", {}).get("after")
    if not (m.get("paging") or {}).get("next") and len(m.get("data", [])) < LIMIT:
        nxt = None
    return {"bd": bd, "posts": m.get("data", []), "after": nxt}, None


def kind(m):
    if m.get("media_product_type") == "REELS":
        return "Reel"
    return {"CAROUSEL_ALBUM": "Carrusel", "VIDEO": "Video", "IMAGE": "Foto"}.get(m.get("media_type"), "Otro")


def ts_of(m):
    try:
        return datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00")).astimezone(ART)
    except Exception:
        return None


def load(user):
    f = STORE / f"{user.lower()}.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf8"))
        except Exception:
            pass
    return {"usuario": user, "posts": {}, "completo": False, "cursor": None, "historia": []}


def save(st):
    STORE.mkdir(parents=True, exist_ok=True)
    (STORE / f"{st['usuario'].lower()}.json").write_text(json.dumps(st, ensure_ascii=False, separators=(",", ":")), encoding="utf8")


def upsert(st, posts, desde):
    """Agrega o actualiza publicaciones; devuelve la fecha más vieja de la página (o None)."""
    oldest = None
    for m in posts:
        t = ts_of(m)
        if not t:
            continue
        oldest = t if oldest is None or t < oldest else oldest
        if t < desde:
            continue
        cap = re.sub(r"\s+", " ", m.get("caption") or "").strip()[:110]
        st["posts"][m["id"]] = [t.strftime("%Y-%m-%dT%H:%M"), m.get("like_count"), m.get("comments_count") or 0, kind(m), m.get("permalink"), cap]
    return oldest


def refresh(user, now, desde):
    """Primera página: datos de perfil y las 50 publicaciones más nuevas. Devuelve (store, error)."""
    r, err = page(user, None)
    if not r:
        return None, err
    st = load(r["bd"].get("username") or user)
    bd = r["bd"]
    st.update({"usuario": bd.get("username") or user, "nombre": bd.get("name"), "followers": bd.get("followers_count"),
               "follows": bd.get("follows_count"), "media_count": bd.get("media_count"), "actualizado": now.isoformat(timespec="minutes")})
    today = now.strftime("%Y-%m-%d")
    st["historia"] = [h for h in st.get("historia", []) if h["d"] != today][-180:] + [{"d": today, "f": bd.get("followers_count")}]
    oldest = upsert(st, r["posts"], desde)
    if not r["after"] or (oldest and oldest < desde):
        st["completo"], st["cursor"] = True, None
    elif not st.get("completo") and not st.get("cursor"):
        st["cursor"] = r["after"]  # el historial sigue desde acá
    save(st)
    return st, None


def backfill(st, desde):
    """Completa el historial hacia atrás desde el cursor guardado."""
    after = st.get("cursor")
    if st.get("completo") or not after:
        return
    while True:
        r, err = page(st["usuario"], after)
        if not r:  # cursor vencido: empezar de nuevo desde arriba la próxima vez
            st["cursor"] = None
            print(f"  @{st['usuario']}: cursor vencido ({str(err)[:60]})")
            break
        oldest = upsert(st, r["posts"], desde)
        after = r["after"]
        st["cursor"] = after
        if not after or (oldest and oldest < desde):
            st["completo"], st["cursor"] = True, None
            break
        save(st)
    save(st)


def candidatos():
    """name -> lista de usuarios a probar (resueltos primero)."""
    mcfg = json.loads((ROOT / "meta" / "config.json").read_text(encoding="utf8"))
    mig = {d["name"]: list(d.get("ig") or []) for d in mcfg.get("dirigentes", [])}
    try:
        mdata = json.loads((ROOT / "meta" / "data" / "meta.json").read_text(encoding="utf8"))
        for d in mdata.get("dirigentes", []):
            u = (d.get("ig") or {}).get("usuario")
            if u and d["name"] in mig and u.lower() in [x.lower() for x in mig[d["name"]]]:
                mig[d["name"]] = [u] + [x for x in mig[d["name"]] if x.lower() != u.lower()]
    except Exception:
        pass
    try:
        res = json.loads((STORE / "_resueltos.json").read_text(encoding="utf8"))
    except Exception:
        res = {}
    out = {}
    for tb in CFG["tableros"].values():
        for f in tb["figuras"]:
            c = mig.get(f["name"], []) + list(f.get("ig") or [])
            if res.get(f["name"]):
                c = [res[f["name"]]] + c
            seen, lst = set(), []
            for h in c:
                if h.lower() not in seen:
                    seen.add(h.lower())
                    lst.append(h)
            out[f["name"]] = lst
    return out, res


def write_tableros(now, cuentas, errores):
    OUT.mkdir(parents=True, exist_ok=True)
    resumen = {}
    for slug, tb in CFG["tableros"].items():
        figs = []
        for f in tb["figuras"]:
            st = cuentas.get(f["name"])
            row = {"name": f["name"]}
            if st:
                h = st.get("historia", [])
                def delta(days, h=h, st=st):
                    ref = [x for x in h if x["d"] <= (now - timedelta(days=days)).strftime("%Y-%m-%d")]
                    return st["followers"] - ref[-1]["f"] if ref and st.get("followers") is not None and ref[-1].get("f") is not None else None
                row.update({"usuario": st["usuario"], "nombre": st.get("nombre"), "followers": st.get("followers"),
                            "media_count": st.get("media_count"), "delta7": delta(7), "delta30": delta(30),
                            "completo": bool(st.get("completo")), "actualizado": st.get("actualizado"),
                            "posts": sorted(st["posts"].values(), key=lambda p: p[0], reverse=True)})
            else:
                row["error"] = errores.get(f["name"], "sin cuenta profesional encontrada")
            figs.append(row)
        ok = sum(1 for r in figs if r.get("usuario"))
        resumen[slug] = f"{ok}/{len(figs)}"
        (OUT / f"{slug}.json").write_text(json.dumps({
            "tablero": slug, "titulo": tb.get("titulo"), "updated_at": now.isoformat(timespec="minutes"),
            "desde": CFG["desde"], "estado": "ok" if ok else "sin datos", "corte": S["corte"], "figuras": figs,
        }, ensure_ascii=False, separators=(",", ":")), encoding="utf8")
    return resumen


def main():
    now = datetime.now(ART)
    desde = datetime.fromisoformat(CFG["desde"]).replace(tzinfo=ART)
    if not meta.TOKEN or not meta.IG_USER:
        print("Sin META_TOKEN / META_IG_USER_ID: no se actualiza nada")
        if not any(OUT.glob("*.json")):
            write_tableros(now, {}, {})
        return
    cand, res = candidatos()
    cuentas, errores, memo = {}, {}, {}
    names = list(cand)
    # 1) refresco: resolver usuario y traer lo reciente de cada cuenta (una sola vez por cuenta)
    for name in names:
        if S["corte"]:
            break
        errs = []
        for h in cand[name]:
            key = h.lower()
            try:
                if key not in memo:
                    memo[key] = refresh(h, now, desde)
            except Corte:
                break
            st, err = memo[key]
            if st:
                cuentas[name] = st
                res[name] = st["usuario"]
                break
            errs.append(f"@{h}: {str(err)[:70]}")
        if name not in cuentas:
            errores[name] = "sin cuenta profesional encontrada" + (f" ({'; '.join(errs)[:200]})" if errs else "")
        print(f"{name}: {'@' + cuentas[name]['usuario'] + ' · ' + str(len(cuentas[name]['posts'])) + ' posts' if name in cuentas else errores[name]}")
    # 2) historial pendiente, de la cuenta con menos posts a la de más
    pend = {st["usuario"]: st for st in cuentas.values() if not st.get("completo")}
    for st in sorted(pend.values(), key=lambda s: s.get("media_count") or 0):
        try:
            backfill(st, desde)
        except Corte:
            save(st)
            break
    # nombres no buscados por corte: usar lo que haya en el store
    for name in names:
        if name not in cuentas and res.get(name):
            f = STORE / f"{res[name].lower()}.json"
            if f.exists():
                cuentas[name] = json.loads(f.read_text(encoding="utf8"))
                errores.pop(name, None)
    (STORE / "_resueltos.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf8")
    resumen = write_tableros(now, cuentas, errores)
    falt = sum(1 for st in cuentas.values() if not st.get("completo"))
    print(f"Llamadas: {S['llamadas']} · corte: {S['corte'] or 'no'} · cuentas con historial pendiente: {falt}")
    print("Por tablero:", json.dumps(resumen, ensure_ascii=False))
    sin = sorted(set(errores))
    if sin:
        print("Sin cuenta profesional:", ", ".join(sin))


if __name__ == "__main__":
    sys.exit(main())
