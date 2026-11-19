"""Búsqueda en X (API v2, plan pay-per-use) con tope de gasto compartido por todos los tableros.

    from x_api import buscar      # con sys.path apuntando a x/
    rows, estado = buscar("clark", cfg_x)

- Lee el token de X_BEARER_TOKEN (secret del repo). Sin token, no hace nada.
- X cobra por post devuelto (~USD 0,005 en 2026; un post repetido en el mismo día UTC se cobra una vez).
  Cada corrida anota en x/gasto.json cuántos posts leyó cada tablero y el gasto estimado acumulado.
- Antes de cada pedido se calcula cuánto queda del presupuesto total (x/config.json); si no alcanza, no se pide.
- Cada tablero define en su config un bloque "x": {"query": ..., "max_posts": 100, "cada_dias": 3}.
  Solo se piden posts nuevos (since_id) y como mucho una vez cada "cada_dias".
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG = json.loads((HERE / "config.json").read_text(encoding="utf8"))
LEDGER = HERE / "gasto.json"
API = "https://api.x.com/2/tweets/search/recent?"


def _now():
    return datetime.now(timezone.utc)


def _iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def leer_gasto():
    if LEDGER.exists():
        return json.loads(LEDGER.read_text(encoding="utf8"))
    return {"total_posts": 0, "total_usd": 0.0, "tableros": {}, "corridas": []}


def guardar_gasto(g):
    g["corridas"] = g["corridas"][-60:]
    LEDGER.write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n", encoding="utf8")


def gastado(g):
    """Gasto registrado más lo leído fuera de main (corridas de prueba en ramas)."""
    return g["total_usd"] + CFG.get("gasto_fuera_de_registro_usd", 0)


def disponible(g):
    """Posts que todavía se pueden leer sin pasar el presupuesto total."""
    return max(0, int((CFG["presupuesto_usd"] - gastado(g)) / CFG["costo_por_post_usd"]))


def buscar(tablero: str, cx: dict):
    """Devuelve (filas, estado). Las filas son posts con forma de comentario (kind=comment, platform=X)."""
    token = os.environ.get("X_BEARER_TOKEN", "").strip()
    if not token:
        return [], {"ok": True, "items": 0, "nota": "sin X_BEARER_TOKEN"}
    g = leer_gasto()
    t = g["tableros"].setdefault(tablero, {"posts": 0, "usd": 0.0})
    ult = t.get("ultima")
    if ult and _now() - datetime.fromisoformat(ult.replace("Z", "+00:00")) < timedelta(days=cx.get("cada_dias", 3)) - timedelta(hours=2):
        return [], {"ok": True, "items": 0, "nota": f"próxima consulta a X después de {cx.get('cada_dias', 3)} días de {ult[:10]}",
                    "gasto_usd": round(gastado(g), 3)}
    tope = min(int(cx.get("max_posts", 100)), int(CFG.get("max_posts_por_corrida", 100)), disponible(g))
    if tope < 10:
        return [], {"ok": False, "items": 0, "error": f"presupuesto de X agotado (USD {gastado(g):.2f} de {CFG['presupuesto_usd']})"}
    params = {"query": cx["query"], "max_results": min(100, tope), "sort_order": "recency",
              "tweet.fields": "created_at,public_metrics,lang,conversation_id"}
    if t.get("since_id"):
        params["since_id"] = t["since_id"]
    else:
        params["start_time"] = _iso(_now() - timedelta(days=6, hours=20))
    rows, leidos, token_pag, max_id, error = [], 0, None, t.get("since_id"), None
    while leidos < tope:
        p = dict(params, max_results=max(10, min(100, tope - leidos)))
        if token_pag:
            p["next_token"] = token_pag
        req = urllib.request.Request(API + urllib.parse.urlencode(p), headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                d = json.loads(r.read().decode("utf8"))
        except urllib.error.HTTPError as e:
            error = f"HTTP {e.code}: {e.read().decode('utf8', 'ignore')[:160]}"
            break
        except Exception as e:  # red
            error = f"{type(e).__name__}: {str(e)[:160]}"
            break
        data = d.get("data") or []
        leidos += len(data)
        for tw in data:
            m = tw.get("public_metrics") or {}
            rows.append({"id": f"X:{tw['id']}", "platform": "X", "kind": "comment", "video_id": "x", "video_title": "X",
                         "channel": "X", "text": tw.get("text", ""), "created_at": tw["created_at"][:19] + "Z",
                         "url": f"https://x.com/i/status/{tw['id']}",  # sin autor, como el resto de los extractos
                         "query": "x", "engagement": int(m.get("like_count", 0)) + int(m.get("retweet_count", 0)),
                         "likes": int(m.get("like_count", 0))})
            if not max_id or int(tw["id"]) > int(max_id):
                max_id = tw["id"]
        token_pag = (d.get("meta") or {}).get("next_token")
        if not token_pag or not data:
            break
    usd = leidos * CFG["costo_por_post_usd"]
    t["posts"] += leidos
    t["usd"] = round(t["usd"] + usd, 4)
    if max_id:
        t["since_id"] = max_id
    if not error or leidos:
        t["ultima"] = _iso(_now())
    g["total_posts"] += leidos
    g["total_usd"] = round(g["total_usd"] + usd, 4)
    g["corridas"].append({"fecha": _iso(_now()), "tablero": tablero, "posts": leidos, "usd": round(usd, 4), **({"error": error} if error else {})})
    guardar_gasto(g)
    estado = {"ok": not error, "items": len(rows), "gasto_usd": round(gastado(g), 3), "presupuesto_usd": CFG["presupuesto_usd"]}
    if error:
        estado["error"] = error
    return rows, estado
