"""Datos públicos de Meta para los dirigentes de meta/config.json. Gratis, con token propio.

Dos fuentes, las dos de la Graph API de Meta, sin pagar y sin App Review:
  1. Instagram Business Discovery: seguidores, publicaciones y "me gusta"/comentarios de cuentas
     profesionales públicas. Necesita una cuenta de Instagram profesional propia vinculada a una
     página de Facebook (META_IG_USER_ID) y un token de usuario de larga duración (META_TOKEN) con
     instagram_basic, pages_show_list y pages_read_engagement. En modo desarrollo de la app alcanza.
  2. Biblioteca de Anuncios (ads_archive): avisos políticos en Argentina, con gasto e impresiones
     en rangos, edad, género y provincia. Necesita el mismo token y haber confirmado identidad en
     facebook.com/ID (gratis).

Sin token no hace nada y deja el estado "sin token" en meta/data/meta.json.
Solo se publican agregados y, por dirigente, las 3 publicaciones propias con más interacción
(link + primeras palabras). Nunca comentarios de usuarios.

Uso local:  META_TOKEN=... META_IG_USER_ID=... python meta/collect.py
"""
from __future__ import annotations

import json
import os
import re
import statistics as st
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG = json.loads((HERE / "config.json").read_text(encoding="utf8"))
OUT = HERE / "data" / "meta.json"
ART = timezone(timedelta(hours=-3))
TOKEN = os.environ.get("META_TOKEN", "").strip()
IG_USER = os.environ.get("META_IG_USER_ID", "").strip()
API = f"https://graph.facebook.com/{CFG.get('api_version', 'v21.0')}"
DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
STOP = set("""de la el en y a los las del que con por para un una se su sus al es lo como más mas
este esta estos estas hoy muy todo todos todas nuestro nuestra nuestros nuestras ya pero o no sí si
fue son hay le les me mi mis nos tu te gracias junto sobre desde hasta entre cada vamos ser hacer""".split())


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", (t or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def get(path: str, params: dict, tries=3):
    params = {**params, "access_token": TOKEN}
    url = f"{API}/{path}?{urllib.parse.urlencode(params)}"
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "sudakaos-meta/1.0"}), timeout=40) as r:
                return json.loads(r.read().decode("utf8")), None
        except urllib.error.HTTPError as e:
            try:
                err = json.loads(e.read().decode("utf8")).get("error", {})
            except Exception:
                err = {"message": str(e)}
            code = err.get("code")
            if code in (4, 17, 32, 613) and i < tries - 1:  # límite de llamadas
                time.sleep(30 * (i + 1))
                continue
            # nunca devolver el token en el mensaje
            return None, re.sub(r"access_token=[^&\s]+", "access_token=***", f"{code}: {err.get('message', '')}")[:240]
        except Exception as e:  # red
            if i < tries - 1:
                time.sleep(5 * (i + 1))
                continue
            return None, str(e)[:240]
    return None, "sin respuesta"


# ---------------------------------------------------------------- Instagram
def instagram(handles: list[str], limit: int):
    fields = ("username,name,followers_count,follows_count,media_count,"
              f"media.limit({min(limit, 50)}){{caption,like_count,comments_count,timestamp,media_type,media_product_type,permalink}}")
    errs = []
    for h in handles:
        data, err = get(IG_USER, {"fields": f"business_discovery.username({h}){{{fields}}}"})
        if data and "business_discovery" in data:
            bd = data["business_discovery"]
            media = (bd.get("media") or {}).get("data", [])
            nxt = ((bd.get("media") or {}).get("paging") or {}).get("cursors", {}).get("after")
            if nxt and limit > 50:
                f2 = fields.replace("media.limit(50)", f"media.after({nxt}).limit({limit - 50})")
                more, _ = get(IG_USER, {"fields": f"business_discovery.username({h}){{{f2}}}"})
                if more:
                    media += ((more.get("business_discovery") or {}).get("media") or {}).get("data", [])
            return bd, media, None
        errs.append(f"@{h}: {err}")
    return None, [], "; ".join(errs) or "no encontrado"


def fmt_kind(m):
    if m.get("media_product_type") == "REELS":
        return "Reel"
    return {"CAROUSEL_ALBUM": "Carrusel", "VIDEO": "Video", "IMAGE": "Foto"}.get(m.get("media_type"), "Otro")


def ig_metrics(bd, media, now):
    fol = bd.get("followers_count") or 0
    rows = []
    for m in media:
        try:
            ts = datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00")).astimezone(ART)
        except Exception:
            continue
        inter = (m.get("like_count") or 0) + (m.get("comments_count") or 0)
        rows.append({"ts": ts, "inter": inter, "likes": m.get("like_count") or 0, "com": m.get("comments_count") or 0,
                     "kind": fmt_kind(m), "cap": m.get("caption") or "", "url": m.get("permalink")})
    last30 = [r for r in rows if r["ts"] >= now - timedelta(days=30)]
    base = last30 if len(last30) >= 5 else rows
    er = lambda x: round(100 * x / fol, 3) if fol else None
    by_kind = defaultdict(list)
    for r in base:
        by_kind[r["kind"]].append(r["inter"])
    kinds = {k: {"n": len(v), "inter_med": int(st.median(v)), "er": er(st.median(v))} for k, v in by_kind.items()}
    by_day, by_hour = defaultdict(list), defaultdict(list)
    for r in base:
        by_day[DIAS[r["ts"].weekday()]].append(r["inter"])
        by_hour[r["ts"].hour // 3 * 3].append(r["inter"])
    best = lambda d: max(((k, st.median(v)) for k, v in d.items() if len(v) >= 2), key=lambda x: x[1], default=(None, 0))[0]
    words, tags = Counter(), Counter()
    for r in base:
        tags.update(t.lower() for t in re.findall(r"#(\w{3,})", r["cap"]))
        for w in re.findall(r"[a-záéíóúñü]{4,}", norm(re.sub(r"[#@]\w+|https?://\S+", " ", r["cap"]))):
            if w not in STOP:
                words[w] += 1
    span = max(1, (now - min(r["ts"] for r in rows)).days) if rows else 30
    top = sorted(base, key=lambda r: -r["inter"])[:3]
    inter = [r["inter"] for r in base]
    return {
        "followers": fol, "follows": bd.get("follows_count"), "media_count": bd.get("media_count"),
        "posts_30d": len(last30),
        "posts_semana": round(7 * (len(last30) if len(last30) >= 5 else len(rows)) / (30 if len(last30) >= 5 else span), 1),
        "inter_med": int(st.median(inter)) if inter else 0,
        "likes_med": int(st.median([r["likes"] for r in base])) if base else 0,
        "com_med": int(st.median([r["com"] for r in base])) if base else 0,
        "er": er(st.median(inter)) if inter else None,
        "formatos": kinds,
        "mejor_formato": max(kinds, key=lambda k: kinds[k]["inter_med"]) if kinds else None,
        "mejor_dia": best(by_day), "mejor_franja": best(by_hour),
        "franjas": {f"{h:02d}-{h + 3:02d}": int(st.median(v)) for h, v in sorted(by_hour.items())},
        "dias": {d: int(st.median(by_day[d])) for d in DIAS if d in by_day},
        "temas": [w for w, _ in words.most_common(12)],
        "hashtags": [t for t, _ in tags.most_common(8)],
        "top": [{"t": re.sub(r"\s+", " ", r["cap"])[:120], "u": r["url"], "f": r["kind"], "i": r["inter"],
                 "d": r["ts"].strftime("%Y-%m-%d")} for r in top],
        "serie": [{"d": r["ts"].strftime("%Y-%m-%d"), "i": r["inter"], "f": r["kind"]} for r in sorted(base, key=lambda r: r["ts"])],
    }


# ---------------------------------------------------------------- Biblioteca de anuncios
def rng(x):
    if not x:
        return 0, 0
    lo = int(x.get("lower_bound") or 0)
    hi = int(x.get("upper_bound") or lo)
    return lo, hi


def ads(terms: list[str], name: str, days: int):
    since = (datetime.now(ART) - timedelta(days=days)).strftime("%Y-%m-%d")
    fields = ("id,page_id,page_name,ad_delivery_start_time,ad_delivery_stop_time,spend,impressions,currency,"
              "publisher_platforms,demographic_distribution,delivery_by_region,bylines,ad_creative_bodies")
    surname = norm(name.split()[-1])
    seen, out, err = set(), [], None
    for t in terms:
        params = {"search_terms": t, "ad_reached_countries": json.dumps(["AR"]), "ad_type": "POLITICAL_AND_ISSUE_ADS",
                  "ad_active_status": "ALL", "ad_delivery_date_min": since, "fields": fields, "limit": 200}
        path = "ads_archive"
        for _ in range(5):
            data, err = get(path, params)
            if not data:
                break
            for a in data.get("data", []):
                if a["id"] in seen:
                    continue
                # solo avisos de páginas del dirigente o que lo firman (evita homónimos y menciones de rivales)
                who = norm(f"{a.get('page_name', '')} {a.get('bylines', '')}")
                if surname in who:
                    seen.add(a["id"])
                    out.append(a)
            nxt = (data.get("paging") or {}).get("next")
            if not nxt:
                break
            q = urllib.parse.urlparse(nxt)
            path, params = q.path.split("/", 2)[-1], {k: v[0] for k, v in urllib.parse.parse_qs(q.query).items() if k != "access_token"}
    if not out:
        return {"n": 0, "error": err} if err else {"n": 0}
    sp, im, reg, age, gen, plat, pages = [0, 0], [0, 0], Counter(), Counter(), Counter(), Counter(), Counter()
    activos, bodies = 0, []
    for a in out:
        s, i = rng(a.get("spend")), rng(a.get("impressions"))
        sp[0] += s[0]; sp[1] += s[1]; im[0] += i[0]; im[1] += i[1]
        mid = (i[0] + i[1]) / 2 or 1
        for r in a.get("delivery_by_region") or []:
            reg[r.get("region", "?")] += float(r.get("percentage") or 0) * mid
        for d in a.get("demographic_distribution") or []:
            age[d.get("age", "?")] += float(d.get("percentage") or 0) * mid
            gen[d.get("gender", "?")] += float(d.get("percentage") or 0) * mid
        plat.update(a.get("publisher_platforms") or [])
        pages[a.get("page_name", "?")] += 1
        if not a.get("ad_delivery_stop_time"):
            activos += 1
        if a.get("ad_creative_bodies"):
            bodies.append((i[1], a["id"], a.get("ad_delivery_start_time", "")[:10], a["ad_creative_bodies"][0]))
    share = lambda c: {k: round(100 * v / sum(c.values()), 1) for k, v in c.most_common(8)} if sum(c.values()) else {}
    return {
        "n": len(out), "activos": activos, "gasto": sp, "impresiones": im, "moneda": out[0].get("currency", "ARS"),
        "regiones": share(reg), "edades": share(age), "genero": share(gen), "plataformas": dict(plat.most_common()),
        "paginas": dict(pages.most_common(4)),
        "avisos": [{"t": re.sub(r"\s+", " ", b)[:140], "d": d, "u": f"https://www.facebook.com/ads/library/?id={i}"}
                   for _, i, d, b in sorted(bodies, reverse=True)[:3]],
    }



def diagnostico():
    """Qué permisos tiene el token y si META_IG_USER_ID es una cuenta de Instagram profesional. Sin datos sensibles."""
    out = {}
    perms, err = get("me/permissions", {})
    out["permisos"] = sorted(p["permission"] for p in (perms or {}).get("data", []) if p.get("status") == "granted") if perms else None
    out["permisos_error"] = err
    acc, err = get(IG_USER, {"fields": "id,username"})
    out["cuenta_ig_ok"] = bool(acc and acc.get("id"))
    out["cuenta_ig_error"] = err
    need = ["instagram_basic", "pages_show_list", "pages_read_engagement", "instagram_manage_insights", "business_management"]
    out["faltan_permisos"] = [p for p in need if out["permisos"] is not None and p not in out["permisos"]]
    return out

# ---------------------------------------------------------------- principal
def main():
    now = datetime.now(ART)
    prev = {}
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text(encoding="utf8"))
        except Exception:
            prev = {}
    old = {d["name"]: d for d in prev.get("dirigentes", [])}
    base = {"updated_at": now.isoformat(timespec="minutes"), "grupos": CFG["grupos"]}
    if not TOKEN or not IG_USER:
        falta = [k for k, v in (("META_TOKEN", TOKEN), ("META_IG_USER_ID", IG_USER)) if not v]
        if prev.get("estado") == "ok":  # no pisar datos buenos si un día falta el secret
            print("Sin token: se mantienen los datos anteriores")
            return
        OUT.write_text(json.dumps({**base, "estado": "sin token", "faltan": falta,
                                   "dirigentes": [{k: d.get(k) for k in ("name", "grupo", "espacio", "distrito")} for d in CFG["dirigentes"]]},
                                  ensure_ascii=False, indent=1), encoding="utf8")
        print("Faltan secrets:", ", ".join(falta))
        return
    diag = diagnostico()
    print("Diagnóstico:", json.dumps(diag, ensure_ascii=False))
    out, ads_err = [], None
    for d in CFG["dirigentes"]:
        row = {k: d.get(k) for k in ("name", "grupo", "espacio", "distrito")}
        bd, media, err = instagram(d.get("ig", []), CFG.get("media_limit", 60))
        hist = (old.get(d["name"], {}).get("historia") or [])[-120:]
        if bd:
            row["ig"] = {"usuario": bd.get("username"), "nombre": bd.get("name"), **ig_metrics(bd, media, now)}
            today = now.strftime("%Y-%m-%d")
            hist = [h for h in hist if h["d"] != today] + [{"d": today, "f": row["ig"]["followers"]}]
            def delta(days):
                ref = [h for h in hist if h["d"] <= (now - timedelta(days=days)).strftime("%Y-%m-%d")]
                return row["ig"]["followers"] - ref[-1]["f"] if ref else None
            row["ig"]["delta7"], row["ig"]["delta30"] = delta(7), delta(30)
        else:
            row["ig_error"] = err
        row["historia"] = hist
        row["ads"] = ads(d.get("ads") or [d["name"]], d["name"], CFG.get("ads_days", 90))
        if row["ads"].get("error"):
            ads_err = row["ads"]["error"]
        out.append(row)
        print(f"{d['name']}: IG {'ok @' + row['ig']['usuario'] if bd else 'ERROR ' + str(err)[:80]} · avisos {row['ads'].get('n')}")
        time.sleep(1)
    ok = sum(1 for r in out if r.get("ig"))
    OUT.write_text(json.dumps({**base, "estado": "ok" if ok else "error", "ads_error": ads_err, "ig_ok": ok,
                               "ig_error": None if ok else next((r.get("ig_error") for r in out if r.get("ig_error")), None), "diagnostico": diag,
                               "dirigentes": out}, ensure_ascii=False, indent=1), encoding="utf8")
    print(f"Instagram ok: {ok}/{len(out)}")


if __name__ == "__main__":
    sys.exit(main())
