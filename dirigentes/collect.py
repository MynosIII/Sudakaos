"""Monitores por dirigente (Pagano, Casielles, Braillard): recolecta fuentes públicas y gratuitas.

Fuentes (cada una falla por separado sin frenar a las demás):
  - YouTube Data API v3: videos sobre el dirigente, su competencia y su distrito, y sus comentarios
    (YOUTUBE_API_KEY, gratis; en Actions se usa YOUTUBE_API_KEY_DIRIGENTES si existe, si no la de Roca).
  - Google News RSS: notas sobre el dirigente y su competencia, más búsquedas por sitio en medios del distrito.
  - RSS directos de medios del distrito y nacionales (solo notas con contexto o que nombran al dirigente).
  - Google Trends: interés de búsqueda en la provincia del distrito y en el país, sin clave. Google suele cortar
    pedidos desde servidores: si falla, el tablero lo dice y sigue con el resto.
  - Wikipedia / Wikimedia: visitas diarias a los artículos de cada figura (sin clave) y ficha de la provincia.
Facebook, Instagram y X no tienen API abierta y gratuita para buscar publicaciones.

Uso: python dirigentes/collect.py <slug>   (pagano | casielles | braillard)
El almacén con textos (.store/) no se sube al repositorio; en Actions vive en la caché del workflow.
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

SLUG = sys.argv[1] if len(sys.argv) > 1 else "pagano"
HERE = Path(__file__).resolve().parent / SLUG
CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf8"))
STORE = HERE / ".store" / "items.jsonl"
UA = "MonitorDirigentes/0.1 (+https://github.com/MynosIII/Sudakaos; investigación agregada)"
TAG_RE = re.compile(r"<[^>]+>")


def get(url, data=None, headers=None, retries=2, timeout=60):
    h = {"User-Agent": UA}
    h.update(headers or {})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h), timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(20 * (attempt + 1))
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


def iso(d):
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(**kw):
    print(json.dumps(kw, ensure_ascii=False), flush=True)


# ---------------------------------------------------------------- YouTube
def youtube():
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise RuntimeError("falta YOUTUBE_API_KEY")
    cfg = CONFIG["youtube"]
    api = "https://www.googleapis.com/youtube/v3/"
    since = iso(datetime.now(timezone.utc) - timedelta(days=CONFIG["window_days"]))
    ctx, excl = cfg["contexto"], cfg["excluir"]
    out, seen, fails = [], set(), 0
    for q in cfg["queries"]:
        params = {"part": "snippet", "type": "video", "q": q, "regionCode": cfg["region"], "relevanceLanguage": cfg["language"],
                  "publishedAfter": since, "maxResults": cfg["videos_per_query"], "order": "relevance", "key": key}
        items = None
        for attempt in range(2):
            try:
                items = get_json(api + "search?" + urllib.parse.urlencode(params)).get("items", [])
                break
            except urllib.error.HTTPError as e:
                log(youtube_query=q, error=e.code, attempt=attempt)
                if e.code == 429 and attempt == 0:  # límite de ritmo: esperar y reintentar una vez
                    time.sleep(60)
                    continue
                items = None
                break
        if items is None:
            fails += 1
            # cuota agotada (403) o límite persistente (429 dos veces): no gastar más tiempo, seguir mañana
            if fails >= 2 or not out:
                if not out:
                    raise RuntimeError("YouTube sin cupo o con límite de pedidos: se reintenta en la próxima corrida")
                break
            continue
        fails = 0
        for v in items:
            vid = v["id"]["videoId"]
            if vid in seen:
                continue
            seen.add(vid)
            sn = v["snippet"]
            vtext = clean(sn["title"] + ". " + sn.get("description", "")).lower()
            # Exigir contexto del distrito (o el nombre del dirigente) en título o descripción
            if not any(re.search(rf"\b{re.escape(c)}", vtext) for c in ctx):
                continue
            if any(re.search(rf"\b{re.escape(x)}\b", vtext) for x in excl):
                continue
            video = {"id": f"YouTube:{vid}", "platform": "YouTube", "kind": "video", "video_id": vid,
                     "text": clean(sn["title"] + ". " + sn.get("description", ""))[:600], "title": clean(sn["title"]),
                     "channel": sn["channelTitle"], "created_at": sn["publishedAt"][:19] + "Z",
                     "url": f"https://www.youtube.com/watch?v={vid}", "query": q, "engagement": 0}
            out.append(video)
            try:
                d = get_json(api + "commentThreads?" + urllib.parse.urlencode(
                    {"part": "snippet", "videoId": vid, "order": "relevance", "maxResults": cfg["comments_per_video"],
                     "textFormat": "plainText", "key": key}))
            except urllib.error.HTTPError:  # comentarios desactivados
                continue
            for t in d.get("items", []):
                c = t["snippet"]["topLevelComment"]["snippet"]
                out.append({"id": f"YouTube:{t['id']}", "platform": "YouTube", "kind": "comment", "video_id": vid,
                            "video_title": video["title"], "channel": video["channel"],
                            "text": clean(c.get("textOriginal") or c.get("textDisplay", ""))[:1500],
                            "created_at": c["publishedAt"][:19] + "Z",
                            "url": f"https://www.youtube.com/watch?v={vid}&lc={t['id']}", "query": q,
                            "engagement": c.get("likeCount", 0) + t["snippet"].get("totalReplyCount", 0)})
        time.sleep(2)
    return out


# ---------------------------------------------------------------- Google News
def news_queries():
    g = CONFIG["google_news"]
    qs = list(g["queries"])
    for s in g.get("sites", []):
        for t in g.get("site_terms", []):
            qs.append(f"{t} site:{s}")
    return qs


def google_news():
    atom_out = []
    for q in news_queries():
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
            {"q": q + " when:" + CONFIG.get("news_when", "1y"), "hl": "es-419", "gl": "AR", "ceid": "AR:es-419"})
        try:
            root = ET.fromstring(get(url))
        except Exception as e:
            log(google_news=q, error=str(e)[:120])
            continue
        for it in root.iter("item"):
            title = clean(it.findtext("title"))
            src = it.find("source")
            outlet = src.text if src is not None and src.text else ""
            if outlet and title.endswith(" - " + outlet):
                title = title[: -len(outlet) - 3]
            try:
                created = iso(parsedate_to_datetime(it.findtext("pubDate")))
            except (TypeError, ValueError):
                continue
            link = it.findtext("link") or ""
            atom_out.append({"id": "Noticias:" + (it.findtext("guid") or link), "platform": "Medios", "kind": "news",
                             "text": title, "title": title, "outlet": outlet, "created_at": created, "url": link,
                             "query": q, "engagement": 0})
        time.sleep(1)
    return atom_out


# ---------------------------------------------------------------- RSS regionales
def rss():
    ctx = [c.lower() for c in CONFIG["contexto"]]
    # Solo alias del dirigente foco: los nacionales (Milei, Kicillof) traerían todo el país
    pol = [a.lower() for k, v in CONFIG["figuras"].items() if v.get("foco") for a in v["alias"] if len(a) > 7]
    out = []
    for f in CONFIG["rss"]:
        try:
            root = ET.fromstring(get(f["url"], retries=1, timeout=40))
        except Exception as e:
            log(rss=f["name"], error=str(e)[:120])
            continue
        n = 0
        for it in root.iter("item"):
            title = clean(it.findtext("title"))
            desc = clean(it.findtext("description"))[:500]
            low = (title + " " + desc).lower()
            if not (any(re.search(rf"\b{re.escape(c)}\b", low) for c in ctx) or any(p in low for p in pol)):
                continue
            try:
                created = iso(parsedate_to_datetime(it.findtext("pubDate")))
            except (TypeError, ValueError):
                continue
            link = it.findtext("link") or ""
            out.append({"id": "Noticias:" + link, "platform": "Medios", "kind": "news", "text": title + ". " + desc,
                        "title": title, "outlet": f["name"], "created_at": created, "url": link, "query": "rss", "engagement": 0})
            n += 1
        log(rss=f["name"], items=n)
    return out


# ---------------------------------------------------------------- Wikipedia / Wikidata
WIKI = HERE / ".store" / "wiki.json"
WAPI = "https://es.wikipedia.org/w/api.php?"


def wiki():
    """Visitas diarias a Wikipedia de cada figura seguida + ficha de la provincia."""
    people = CONFIG["figuras"]
    cands = {k: v.get("wiki") or [k] for k, v in people.items()}
    titles = sorted({t for ts in cands.values() for t in ts} | set(CONFIG.get("wiki_provincia", [])))
    resolved, pages = {}, {}
    for i in range(0, len(titles), 40):
        q = get_json(WAPI + urllib.parse.urlencode({"action": "query", "format": "json", "formatversion": 2, "redirects": 1,
                                                     "titles": "|".join(titles[i:i + 40]), "prop": "pageprops|extracts|info",
                                                     "exintro": 1, "explaintext": 1, "exsentences": 3, "inprop": "url"}),
                     headers={"User-Agent": UA})["query"]
        alias = {}
        for n in q.get("normalized", []) + q.get("redirects", []):
            alias[n["from"]] = n["to"]
        for pg in q.get("pages", []):
            if pg.get("missing") or "disambiguation" in (pg.get("pageprops") or {}):
                continue
            pages[pg["title"]] = {"title": pg["title"], "url": pg.get("fullurl"), "extract": (pg.get("extract") or "")[:700],
                                  "qid": (pg.get("pageprops") or {}).get("wikibase_item")}
        for t in titles[i:i + 40]:
            u = t
            while u in alias and alias[u] != u:
                u = alias[u]
            if u in pages:
                resolved[t] = u
        time.sleep(1)
    end = datetime.now(timezone.utc) - timedelta(days=1)
    start = end - timedelta(days=CONFIG["window_days"])
    out = {"fetched_at": iso(datetime.now(timezone.utc)), "personas": {}, "provincia": None}
    for k, ts in cands.items():
        t = next((resolved[x] for x in ts if x in resolved), None)
        if not t:
            continue
        url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/es.wikipedia/all-access/user/"
               + urllib.parse.quote(t.replace(" ", "_"), safe="") + f"/daily/{start:%Y%m%d}/{end:%Y%m%d}")
        try:
            items = get_json(url, headers={"User-Agent": UA}).get("items", [])
        except Exception as e:
            log(wiki=k, error=str(e)[:120])
            items = []
        out["personas"][k] = pages[t] | {"vistas": {it["timestamp"][:8]: it["views"] for it in items}}
        time.sleep(0.3)
    club = next((resolved[x] for x in CONFIG.get("wiki_provincia", []) if x in resolved), None)
    out["provincia"] = pages[club] if club else None
    WIKI.write_text(json.dumps(out, ensure_ascii=False), encoding="utf8")
    return len(out["personas"]), bool(club)


TRENDS = HERE / ".store" / "trends.json"


def trends():
    """Google Trends sin clave (mismo método que massa/collect.py): el dirigente y su competencia, por región."""
    import http.cookiejar
    cfg = CONFIG.get("trends") or {}
    terms = cfg.get("terminos", [])[:5]
    if not terms:
        return 0
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    op.addheaders = [("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"),
                     ("Accept-Language", "es-AR,es;q=0.9")]

    def call(url):
        for i in range(3):
            try:
                return op.open(url, timeout=30).read().decode("utf-8")
            except urllib.error.HTTPError as e:
                if e.code == 429 and i < 2:
                    time.sleep(20 * (i + 1))
                    continue
                raise

    try:  # la primera visita devuelve 429 con la cookie NID; la siguiente pasa
        op.open("https://trends.google.com/trends/explore?geo=AR", timeout=30).read()
    except urllib.error.HTTPError:
        time.sleep(5)
    js = lambda t: json.loads(t[t.index("{"):])
    out = {"fetched_at": iso(datetime.now(timezone.utc)), "terminos": terms, "series": {}, "errores": {}}
    for geo in cfg.get("geos", {"AR": "Argentina"}):
        try:
            req = {"comparisonItem": [{"keyword": t, "geo": geo, "time": "today 12-m"} for t in terms], "category": 0, "property": ""}
            ex = js(call("https://trends.google.com/trends/api/explore?" + urllib.parse.urlencode({"hl": "es-AR", "tz": 180, "req": json.dumps(req)})))
            w = next(w for w in ex["widgets"] if w.get("id") == "TIMESERIES")
            d = js(call("https://trends.google.com/trends/api/widgetdata/multiline?" + urllib.parse.urlencode(
                {"hl": "es-AR", "tz": 180, "req": json.dumps(w["request"]), "token": w["token"]})))
            serie = {t: {} for t in terms}
            for pt in d["default"]["timelineData"]:
                day = datetime.fromtimestamp(int(pt["time"]), timezone.utc).strftime("%Y-%m-%d")
                for t, v in zip(terms, pt["value"]):
                    serie[t][day] = v
            out["series"][geo] = serie
        except Exception as e:
            out["errores"][geo] = f"{type(e).__name__}: {str(e)[:120]}"
            log(trends=geo, error=out["errores"][geo])
        time.sleep(5)
    if out["series"] or not TRENDS.exists():
        TRENDS.write_text(json.dumps(out, ensure_ascii=False), encoding="utf8")
    return sum(len(v) for v in out["series"].values())


def save(known):
    cutoff = iso(datetime.now(timezone.utc) - timedelta(days=CONFIG["window_days"] + 30))
    keep = [r for r in known.values() if r.get("created_at", "") >= cutoff]
    STORE.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in keep) + "\n", encoding="utf8")


def main():
    STORE.parent.mkdir(parents=True, exist_ok=True)
    known = {}
    if STORE.exists():
        for line in STORE.read_text(encoding="utf8").splitlines():
            try:
                r = json.loads(line)
                known[r["id"]] = r
            except (ValueError, KeyError):
                pass
    status = {}
    for name, fn in (("youtube", youtube), ("google_news", google_news), ("rss", rss)):
        try:
            rows = fn()
            new = sum(1 for r in rows if r["id"] not in known)
            for r in rows:
                known[r["id"]] = r | {"collected_at": iso(datetime.now(timezone.utc))}
            status[name] = {"ok": True, "items": len(rows), "new": new}
        except Exception as e:
            status[name] = {"ok": False, "error": str(e)[:200]}
        log(source=name, **status[name])
    save(known)
    status_path = HERE / ".store" / "status.json"
    status_path.write_text(json.dumps(status, ensure_ascii=False), encoding="utf8")
    try:
        npers, has_m = wiki()
        status["wikipedia"] = {"ok": npers > 0, "items": npers, "provincia": has_m}
    except Exception as e:
        status["wikipedia"] = {"ok": WIKI.exists(), "error": str(e)[:200]}
    log(source="wikipedia", **status["wikipedia"])
    try:
        nt = trends()
        status["google_trends"] = {"ok": nt > 0, "items": nt}
    except Exception as e:
        status["google_trends"] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:160]}"}
    log(source="google_trends", **status["google_trends"])
    status_path.write_text(json.dumps(status, ensure_ascii=False), encoding="utf8")


if __name__ == "__main__":
    main()
    sys.exit(0)
