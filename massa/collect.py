"""Paquete Massa · Galmarini: recolecta fuentes públicas y gratuitas.

Fuentes (cada una falla por separado sin frenar a las demás):
  - YouTube Data API v3: videos sobre Sergio Massa y Malena Galmarini y sus comentarios (gratis).
  - Google News RSS: notas sobre los dos, sus competidores y los temas de agenda (salud mental adolescente,
    apuestas online, grooming, soberanía y seguridad de datos).
  - Wikipedia / Wikimedia: visitas diarias a los artículos de cada político y de cada tema (sin clave).
  - Have I Been Pwned: catálogo público de filtraciones conocidas (sin clave), filtrado a Argentina.
  - Chequeo pasivo de sitios públicos (Provincia, Legislatura, municipios de la Primera sección):
    una sola visita a la portada para leer encabezados de seguridad, certificado, terceros que carga y
    registros de correo (SPF/DMARC por DNS público). No se prueba ninguna vulnerabilidad.

Uso: python massa/collect.py
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

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf8"))
STORE = HERE / ".store" / "items.jsonl"
UA = "RadarMassa/0.1 (+https://github.com/MynosIII/Sudakaos; investigación agregada)"
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
            if fails >= 3:  # cuota agotada (403) o límite persistente: seguir mañana
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
            if not any(c in vtext for c in ctx):
                continue
            if any(x in vtext for x in excl):
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
    for tema, a in CONFIG.get("agenda", {}).items():
        qs += a.get("queries", [])
    qs += CONFIG.get("datos", {}).get("queries", [])
    return qs


def google_news():
    atom_out = []
    for q in news_queries():
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
            {"q": q + " when:1y", "hl": "es-419", "gl": "AR", "ceid": "AR:es-419"})
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


# ---------------------------------------------------------------- Wikipedia / Wikidata
WIKI = HERE / ".store" / "wiki.json"
SEG = HERE / ".store" / "seguridad.json"
WAPI = "https://es.wikipedia.org/w/api.php?"


def wiki():
    """Visitas diarias a Wikipedia de cada político y de los artículos de cada tema de agenda."""
    cands = {("p", k): v.get("wiki") or [k] for k, v in CONFIG["politicos"].items()}
    for tema, a in CONFIG.get("agenda", {}).items():
        for t in a.get("wiki", []):
            cands[("t", tema + "|" + t)] = [t]
    for t in CONFIG.get("datos", {}).get("wiki", []):
        cands[("t", CONFIG["datos"]["tema"] + "|" + t)] = [t]
    titles = sorted({t for ts in cands.values() for t in ts})
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
            pages[pg["title"]] = {"title": pg["title"], "url": pg.get("fullurl"), "extract": (pg.get("extract") or "")[:700]}
        for t in titles[i:i + 40]:
            u = t
            while u in alias and alias[u] != u:
                u = alias[u]
            if u in pages:
                resolved[t] = u
        time.sleep(1)
    end = datetime.now(timezone.utc) - timedelta(days=1)
    start = end - timedelta(days=CONFIG["window_days"])
    out = {"fetched_at": iso(datetime.now(timezone.utc)), "personas": {}, "temas": {}}
    for (kind, k), ts in cands.items():
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
        row = pages[t] | {"vistas": {it["timestamp"][:8]: it["views"] for it in items}}
        if kind == "p":
            out["personas"][k] = row
        else:
            tema, art = k.split("|", 1)
            out["temas"].setdefault(tema, {})[art] = row
        time.sleep(0.3)
    WIKI.write_text(json.dumps(out, ensure_ascii=False), encoding="utf8")
    return len(out["personas"]), sum(len(v) for v in out["temas"].values())


# ---------------------------------------------------------------- Seguridad de datos
TRACKERS = {  # dominio (sufijo) -> empresa
    "google-analytics.com": "Google", "googletagmanager.com": "Google", "doubleclick.net": "Google", "googlesyndication.com": "Google",
    "googleadservices.com": "Google", "facebook.net": "Meta", "facebook.com": "Meta", "connect.facebook.net": "Meta", "instagram.com": "Meta",
    "hotjar.com": "Hotjar", "clarity.ms": "Microsoft", "bing.com": "Microsoft", "tiktok.com": "TikTok", "analytics.tiktok.com": "TikTok",
    "twitter.com": "X", "x.com": "X", "ads-twitter.com": "X", "linkedin.com": "LinkedIn", "licdn.com": "LinkedIn", "yandex.ru": "Yandex",
    "mc.yandex.ru": "Yandex", "addthis.com": "Oracle", "sharethis.com": "ShareThis", "cloudflareinsights.com": "Cloudflare",
    "newrelic.com": "New Relic", "nr-data.net": "New Relic", "youtube.com": "Google", "ytimg.com": "Google", "gstatic.com": "Google",
    "googleapis.com": "Google", "recaptcha.net": "Google", "tawk.to": "Tawk", "zopim.com": "Zendesk", "onesignal.com": "OneSignal",
}
HEADERS = {"strict-transport-security": "HSTS", "content-security-policy": "CSP", "x-frame-options": "Anti-clickjacking",
           "x-content-type-options": "nosniff", "referrer-policy": "Referrer-Policy", "permissions-policy": "Permissions-Policy"}
SRC_RE = re.compile(r"""<(?:script|iframe|img|link)\b[^>]*?\b(?:src|href)\s*=\s*["'](https?:)?//([a-z0-9.\-]+)""", re.I)


def _dns(name, typ):
    try:
        d = get_json("https://dns.google/resolve?" + urllib.parse.urlencode({"name": name, "type": typ}), retries=1, timeout=20)
        return [a.get("data", "").strip('"').replace('" "', "") for a in d.get("Answer", []) if a.get("type") in (1, 16)]
    except Exception:
        return []


def _cert(host):
    import socket
    import ssl
    ctx = ssl.create_default_context()
    with socket.create_connection((host, 443), timeout=15) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ss:
            c = ss.getpeercert()
            ver = ss.version()
            ip = sock.getpeername()[0]
    exp = datetime.strptime(c["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    issuer = dict(x[0] for x in c.get("issuer", []))
    return {"dias_cert": (exp - datetime.now(timezone.utc)).days, "tls": ver, "emisor": issuer.get("organizationName", ""), "ip": ip}


def _rdap(ip):
    try:
        d = get_json(f"https://rdap.org/ip/{ip}", retries=1, timeout=20)
        org = ""
        for ent in d.get("entities", []):
            for v in (ent.get("vcardArray") or [None, []])[1]:
                if v[0] == "fn":
                    org = v[3]
                    break
            if org:
                break
        return {"pais_ip": d.get("country") or "", "red": d.get("name") or "", "org": org}
    except Exception:
        return {}


def check_site(domain):
    """Chequeo pasivo: lo que cualquier navegador ve al abrir la portada."""
    import socket
    host = domain if domain.count(".") > 2 or domain.startswith("www.") else "www." + domain
    r = {"dominio": domain, "host": host}
    for h in (host, domain):
        try:
            socket.getaddrinfo(h, 443)
            r["host"] = host = h
            break
        except OSError:
            continue
    else:
        r["error"] = "no resuelve"
        return r
    try:
        req = urllib.request.Request("http://" + host + "/", headers={"User-Agent": "Mozilla/5.0 " + UA})
        with urllib.request.urlopen(req, timeout=25) as resp:
            r["http_a_https"] = resp.geturl().startswith("https://")
    except Exception:
        r["http_a_https"] = None
    try:
        req = urllib.request.Request("https://" + host + "/", headers={"User-Agent": "Mozilla/5.0 " + UA})
        with urllib.request.urlopen(req, timeout=30) as resp:
            hd = {k.lower(): v for k, v in resp.headers.items()}
            body = resp.read(1_500_000).decode("utf8", "replace")
            r["https"] = True
            r["url_final"] = resp.geturl()
    except Exception as e:
        r["https"] = False
        r["error"] = str(e)[:120]
        return r
    r["cabeceras"] = {lab: (k in hd) for k, lab in HEADERS.items()}
    if not r["cabeceras"]["Anti-clickjacking"] and "frame-ancestors" in hd.get("content-security-policy", ""):
        r["cabeceras"]["Anti-clickjacking"] = True
    srv = hd.get("server", "") + (" " + hd["x-powered-by"] if hd.get("x-powered-by") else "")
    r["software_expuesto"] = srv.strip() if re.search(r"\d", srv) else ""
    base = ".".join(domain.split(".")[-3:]) if domain.endswith((".gob.ar", ".gov.ar", ".com.ar")) else domain
    hosts = {m.group(2).lower() for m in SRC_RE.finditer(body)}
    ext = sorted(h for h in hosts if not h.endswith(base))
    rast = {}
    for h in ext:
        for suf, emp in TRACKERS.items():
            if h == suf or h.endswith("." + suf):
                rast.setdefault(emp, []).append(h)
                break
    r["terceros"] = ext[:40]
    r["n_terceros"] = len(ext)
    r["rastreadores"] = {k: sorted(set(v)) for k, v in rast.items()}
    try:
        r.update(_cert(host))
        r.update(_rdap(r["ip"]))
    except Exception as e:
        r["cert_error"] = str(e)[:120]
    txt = _dns(domain, "TXT")
    dm = _dns("_dmarc." + domain, "TXT")
    r["spf"] = any(t.lower().startswith("v=spf1") for t in txt)
    pol = next((re.search(r"p=(\w+)", t.lower()) for t in dm if "v=dmarc1" in t.lower()), None)
    r["dmarc"] = pol.group(1) if pol else None
    return r


def seguridad():
    out = {"fetched_at": iso(datetime.now(timezone.utc)), "sitios": [], "filtraciones": []}
    for d, nombre in CONFIG["datos"]["sitios"].items():
        try:
            r = check_site(d)
        except Exception as e:
            r = {"dominio": d, "error": str(e)[:120]}
        r["nombre"] = nombre
        out["sitios"].append(r)
        log(sitio=d, https=r.get("https"), error=r.get("error"))
        time.sleep(1)
    try:
        br = get_json("https://haveibeenpwned.com/api/v3/breaches", headers={"User-Agent": UA}, retries=1)
        for b in br:
            txt = (b.get("Domain", "") + " " + b.get("Title", "") + " " + b.get("Description", "")).lower()
            if b.get("Domain", "").endswith(".ar") or "argentin" in txt:
                out["filtraciones"].append({"titulo": b.get("Title"), "dominio": b.get("Domain"), "fecha": b.get("BreachDate"),
                                            "cuentas": b.get("PwnCount"), "datos": b.get("DataClasses", [])[:8],
                                            "verificada": b.get("IsVerified"), "sensible": b.get("IsSensitive")})
    except Exception as e:
        out["hibp_error"] = str(e)[:120]
    SEG.write_text(json.dumps(out, ensure_ascii=False), encoding="utf8")
    return sum(1 for s in out["sitios"] if s.get("https") is not None), len(out["filtraciones"])


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
    for name, fn in (("youtube", youtube), ("google_news", google_news)):
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
        npers, ntem = wiki()
        status["wikipedia"] = {"ok": npers > 0, "items": npers, "temas": ntem}
    except Exception as e:
        status["wikipedia"] = {"ok": WIKI.exists(), "error": str(e)[:200]}
    log(source="wikipedia", **status["wikipedia"])
    try:
        ns, nf = seguridad()
        status["seguridad"] = {"ok": ns > 0, "items": ns, "filtraciones": nf}
    except Exception as e:
        status["seguridad"] = {"ok": SEG.exists(), "error": str(e)[:200]}
    log(source="seguridad", **status["seguridad"])
    status_path.write_text(json.dumps(status, ensure_ascii=False), encoding="utf8")


if __name__ == "__main__":
    main()
    sys.exit(0)
