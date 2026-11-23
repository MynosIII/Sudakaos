"""Brújula · social listener: escucha pasiva de la conversación sobre los 12 ejes y los dirigentes del quiz.

Misma arquitectura que dirigentes/collect.py (stdlib, cada fuente falla sola, textos fuera del repo):
  - Google News RSS: por tema de cada eje y por dirigente (datos/figuras.json, versión ar).
  - YouTube Data API v3: videos por tema y sus comentarios (YOUTUBE_API_KEY).
  - Meta, Biblioteca de Anuncios: avisos políticos por tema con su distribución por edad y género (META_TOKEN).
    Es la única fuente social que trae demografía y se cruza con la del quiz.
  - X (pago, tope compartido en x/config.json): solo a mano con --solo x, nunca en la corrida diaria.
Instagram de los dirigentes ya lo recolecta meta/ (meta/data/meta.json): analyze.py lo lee de ahí.

Uso: python brujula/listener/collect.py            (corrida diaria)
     python brujula/listener/collect.py --solo x   (solo X, a mano)
El almacén con textos (.store/) no se sube al repositorio: vive en la caché de Actions.
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf8"))
FIGURAS = json.loads((HERE.parent / "datos" / "figuras.json").read_text(encoding="utf8"))["ar"]
STORE = HERE / ".store" / "items.jsonl"
STATUS = HERE / ".store" / "status.json"
SOLO_X = "--solo" in sys.argv and "x" in sys.argv
UA = "BrujulaListener/0.1 (+https://github.com/MynosIII/Sudakaos; investigación agregada)"
TAG_RE = re.compile(r"<[^>]+>")
NOW = datetime.now(timezone.utc)


def get(url, headers=None, retries=2, timeout=60):
    h = {"User-Agent": UA, **(headers or {})}
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(15 * (attempt + 1))
                continue
            raise
        except urllib.error.URLError:
            if attempt < retries:
                time.sleep(5)
                continue
            raise


def get_json(url, **kw):
    return json.loads(get(url, **kw).decode("utf8"))


def clean(t):
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", t or ""))).strip()


def fold(s):
    return "".join(c for c in unicodedata.normalize("NFD", (s or "").lower()) if unicodedata.category(c) != "Mn")


def iso(d):
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(**kw):
    print(json.dumps(kw, ensure_ascii=False), flush=True)


# ---------------------------------------------------------------- Google News
def news_rss(q, tag):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": f"{q} when:{min(CONFIG['window_days'], 30)}d", "hl": "es-419", "gl": CONFIG["pais"], "ceid": f"{CONFIG['pais']}:es-419"})
    root = ET.fromstring(get(url))
    out = []
    for it in root.iter("item"):
        title = clean(it.findtext("title"))
        link = it.findtext("link") or ""
        src = clean(it.findtext("source")) or ""
        try:
            d = parsedate_to_datetime(it.findtext("pubDate"))
        except (TypeError, ValueError):
            continue
        desc = clean(it.findtext("description"))
        out.append({"id": "News:" + link[-120:], "platform": "Medios", "kind": "nota", "text": (title + ". " + desc)[:600],
                    "title": title, "channel": src, "created_at": iso(d), "url": link, "query": q, "tag": tag})
    return out


def google_news():
    out, fails = [], 0
    jobs = [(q, "tema:" + eje) for eje, t in CONFIG["temas"].items() for q in t["news"]]
    jobs += [(f'"{f["nombre"]}"', "figura:" + f["nombre"]) for f in FIGURAS]
    for q, tag in jobs:
        try:
            out += news_rss(q, tag)
            fails = 0
        except Exception as e:
            fails += 1
            log(news=q, error=str(e)[:120])
            if fails >= 5:
                raise RuntimeError(f"Google News cortó los pedidos: {e}")
        time.sleep(1.2)
    return out


# ---------------------------------------------------------------- YouTube
def youtube():
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise RuntimeError("falta YOUTUBE_API_KEY")
    cfg, api = CONFIG["youtube"], "https://www.googleapis.com/youtube/v3/"
    since = iso(NOW - timedelta(days=CONFIG["window_days"]))
    out, seen = [], set()
    for eje, t in CONFIG["temas"].items():
        for q in t["youtube"]:
            try:
                items = get_json(api + "search?" + urllib.parse.urlencode(
                    {"part": "snippet", "type": "video", "q": q, "regionCode": cfg["region"], "relevanceLanguage": cfg["language"],
                     "publishedAfter": since, "maxResults": cfg["videos_por_query"], "order": "relevance", "key": key})).get("items", [])
            except urllib.error.HTTPError as e:
                if not out:
                    raise RuntimeError(f"YouTube sin cupo o con error {e.code}: se reintenta en la próxima corrida")
                log(youtube=q, error=e.code)
                return out
            for v in items:
                vid = v["id"]["videoId"]
                if vid in seen:
                    continue
                seen.add(vid)
                sn = v["snippet"]
                video = {"id": f"YouTube:{vid}", "platform": "YouTube", "kind": "video", "video_id": vid,
                         "text": clean(sn["title"] + ". " + sn.get("description", ""))[:600], "title": clean(sn["title"]),
                         "channel": sn["channelTitle"], "created_at": sn["publishedAt"][:19] + "Z",
                         "url": f"https://www.youtube.com/watch?v={vid}", "query": q, "tag": "tema:" + eje}
                out.append(video)
                try:
                    d = get_json(api + "commentThreads?" + urllib.parse.urlencode(
                        {"part": "snippet", "videoId": vid, "order": "relevance", "maxResults": cfg["comentarios_por_video"],
                         "textFormat": "plainText", "key": key}))
                except urllib.error.HTTPError:
                    continue
                for th in d.get("items", []):
                    c = th["snippet"]["topLevelComment"]["snippet"]
                    out.append({"id": f"YouTube:{th['id']}", "platform": "YouTube", "kind": "comentario", "video_id": vid,
                                "video_title": video["title"], "text": clean(c.get("textOriginal") or c.get("textDisplay", ""))[:1500],
                                "created_at": c["publishedAt"][:19] + "Z", "url": video["url"], "tag": "tema:" + eje,
                                "engagement": c.get("likeCount", 0)})
    return out


# ---------------------------------------------------------------- Meta: Biblioteca de Anuncios por tema
def meta_ads():
    tok = os.environ.get("META_TOKEN", "").strip()
    if not tok:
        raise RuntimeError("falta META_TOKEN")
    since = (NOW - timedelta(days=CONFIG["window_days"])).strftime("%Y-%m-%d")
    fields = "id,page_name,ad_delivery_start_time,impressions,spend,currency,publisher_platforms,demographic_distribution,delivery_by_region,ad_creative_bodies"
    out = []
    for eje, t in CONFIG["temas"].items():
        q = t["news"][0]
        params = {"search_terms": q, "ad_reached_countries": json.dumps([CONFIG["pais"]]), "ad_type": "POLITICAL_AND_ISSUE_ADS",
                  "ad_active_status": "ALL", "ad_delivery_date_min": since, "fields": fields, "limit": 100, "access_token": tok}
        try:
            data = get_json("https://graph.facebook.com/v21.0/ads_archive?" + urllib.parse.urlencode(params), retries=0)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf8", "replace")[:200]
            if not out:
                raise RuntimeError(f"Meta Ad Library {e.code}: {body}")
            log(meta_ads=q, error=e.code)
            break
        for a in data.get("data", []):
            body = " ".join(a.get("ad_creative_bodies") or [])[:600]
            out.append({"id": "MetaAd:" + a["id"], "platform": "Anuncios Meta", "kind": "aviso", "text": clean(body),
                        "channel": a.get("page_name", ""), "created_at": (a.get("ad_delivery_start_time") or since)[:10] + "T00:00:00Z",
                        "url": f"https://www.facebook.com/ads/library/?id={a['id']}", "tag": "tema:" + eje,
                        "impressions": a.get("impressions"), "spend": a.get("spend"),
                        "demo": a.get("demographic_distribution") or [], "region": a.get("delivery_by_region") or [],
                        "plataformas": a.get("publisher_platforms") or []})
        time.sleep(2)
    return out


# ---------------------------------------------------------------- X (pago, solo a mano)
X_ESTADO = {}


def x_posts():
    sys.path.insert(0, str(ROOT / "x"))
    from x_api import buscar
    temas = " OR ".join(f'"{q}"' for q in ("motosierra", "casta", "Milei", "Kicillof", "Cristina", "gobernadores", "Bullrich", "inseguridad"))
    cx = {"query": f"({temas}) {CONFIG['x']['query_base']}", "max_posts": CONFIG["x"]["max_posts"]}
    rows, estado = buscar("brujula", cx)
    if not estado.get("ok"):
        raise RuntimeError(estado.get("error", "X falló"))
    X_ESTADO["x"] = {k: v for k, v in estado.items() if k not in ("ok", "items")}
    for r in rows:
        r.setdefault("tag", "x")
    return rows


# ---------------------------------------------------------------- almacén
def load():
    known = {}
    if STORE.exists():
        for line in STORE.read_text(encoding="utf8").splitlines():
            try:
                r = json.loads(line)
                known[r["id"]] = r
            except (ValueError, KeyError):
                pass
    return known


def save(known):
    cutoff = iso(NOW - timedelta(days=CONFIG["window_days"] + 30))
    keep = [r for r in known.values() if r.get("created_at", "") >= cutoff]
    STORE.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in keep) + "\n", encoding="utf8")


def main():
    STORE.parent.mkdir(parents=True, exist_ok=True)
    known = load()
    status = json.loads(STATUS.read_text(encoding="utf8")) if STATUS.exists() else {}
    fuentes = [("x", x_posts)] if SOLO_X else [("google_news", google_news), ("youtube", youtube), ("meta_ads", meta_ads)]
    for name, fn in fuentes:
        try:
            rows = fn()
            new = sum(1 for r in rows if r["id"] not in known)
            for r in rows:
                known[r["id"]] = known.get(r["id"], {}) | r | {"collected_at": iso(NOW)}
            status[name] = {"ok": True, "items": len(rows), "new": new, "at": iso(NOW)} | X_ESTADO.pop(name, {})
        except Exception as e:
            prev = status.get(name, {})
            status[name] = {"ok": False, "error": str(e)[:200], "at": iso(NOW), "ultimo_ok": prev.get("at") if prev.get("ok") else prev.get("ultimo_ok")}
        log(source=name, **status[name])
        save(known)
    STATUS.write_text(json.dumps(status, ensure_ascii=False), encoding="utf8")


if __name__ == "__main__":
    main()
