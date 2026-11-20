"""Donald J. Trump Monitor: collects free, public sources. Each source fails on its own without stopping the rest.

Sources (all free, no paid APIs):
  - Polls: every public job-approval poll from the VoteHub open polling API and Wikipedia's polling tables.
  - Media: 24 US outlets by RSS (tagged by lean) + Google News RSS searches.
  - GDELT 2.0 DOC API: worldwide coverage volume, tone and country breakdown, and a list of foreign-press articles.
  - YouTube Data API v3: recent videos about Trump and their top comments (YOUTUBE_API_KEY).
  - Truth Social: his own posts with engagement (public archive mirrored by CNN, fallback trumpstruth.org RSS).
  - Federal Register API: executive orders, memoranda and proclamations signed in this term.
  - Polymarket (public gamma API): prediction markets tagged Trump.
  - FRED (public CSV): economic indicators.
  - Google Trends (no key) and Wikipedia pageviews.
  - Meta Ad Library (META_TOKEN, free): US political ads that mention Trump.
  - States: Census ACS 1-year + 2020 Census (urban/rural) + BEA GDP by state (free, no key).
  - Instagram (Graph API business discovery, META_TOKEN + META_IG_USER_ID, free): Trump and comparison accounts.
  - X/Twitter: paid API, NEVER automatic. Only `python trump/collect.py x` from the manual "X tableros" workflow
    (query and spending cap in x/tableros.json and x/config.json).

Usage: python trump/collect.py [source ...]   (no args = all)
Raw texts live in trump/.store/ (workflow cache, never committed).
"""
from __future__ import annotations

import csv
import gzip
import html
import io
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
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf8"))
ST = HERE / ".store"
STORE = ST / "items.jsonl"
UA = "SudakaosMonitor/0.1 (+https://github.com/MynosIII/Sudakaos; aggregate research)"
BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
TAG_RE = re.compile(r"<[^>]+>")
NOW = datetime.now(timezone.utc)


def get(url, data=None, headers=None, retries=2, timeout=60, wait=20):
    h = {"User-Agent": UA}
    h.update(headers or {})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h), timeout=timeout) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return raw
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(wait * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
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


def save_json(name, obj):
    (ST / name).write_text(json.dumps(obj, ensure_ascii=False), encoding="utf8")


def parse_date(s):
    try:
        return iso(parsedate_to_datetime(s))
    except (TypeError, ValueError, IndexError):
        pass
    try:
        return iso(datetime.fromisoformat((s or "").strip().replace("Z", "+00:00")))
    except ValueError:
        return None


# ---------------------------------------------------------------- polls
MONTHS = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}


def num(s):
    m = re.search(r"\d+(?:\.\d+)?", (s or "").replace(",", ""))
    return float(m.group()) if m else None


def votehub():
    """VoteHub open polling API (CC BY 4.0): approval polls of the current president."""
    out, errs = [], []
    for url in ("https://api.votehub.com/polls?poll_type=approval&subject=Trump",
                "https://api.votehub.com/polls?poll_type=approval"):
        try:
            data = get_json(url, headers={"Accept": "application/json"})
        except Exception as e:
            errs.append(f"{type(e).__name__}: {str(e)[:100]}")
            continue
        rows = data if isinstance(data, list) else data.get("polls") or data.get("data") or []
        if rows:
            log(votehub_sample=json.dumps(rows[0])[:600])
        for p in rows:
            subj = str(p.get("subject") or p.get("politician") or "trump").lower()
            if "trump" not in subj:
                continue
            ans = {}
            for a in p.get("answers") or p.get("results") or []:
                ch = str(a.get("choice") or a.get("answer") or a.get("name") or "").lower()
                v = a.get("pct", a.get("value", a.get("percent")))
                if v is None:
                    continue
                if ch.startswith("disapprov"):
                    ans["dis"] = float(v)
                elif ch.startswith("approv"):
                    ans["app"] = float(v)
            if "app" not in ans:
                for k_app, k_dis in (("approve", "disapprove"), ("yes", "no")):
                    if p.get(k_app) is not None:
                        ans = {"app": float(p[k_app]), "dis": float(p.get(k_dis) or 0)}
            end = (p.get("end_date") or p.get("end") or p.get("date") or "")[:10]
            if "app" not in ans or not re.match(r"\d{4}-\d\d-\d\d", end) or end < CONFIG["perfil"]["inauguracion"]:
                continue
            pollster = p.get("pollster") or (p.get("pollsters") or ["?"])[0]
            if isinstance(pollster, dict):
                pollster = pollster.get("name", "?")
            out.append({"src": "VoteHub", "pollster": str(pollster).strip(), "start": (p.get("start_date") or end)[:10], "end": end,
                        "n": int(num(str(p.get("sample_size") or "")) or 0), "pop": str(p.get("population") or "").upper()[:3],
                        "app": ans["app"], "dis": ans.get("dis"), "url": p.get("url") or p.get("source_url") or "",
                        "sponsor": ", ".join(p.get("sponsors") or []) if isinstance(p.get("sponsors"), list) else ""})
        if out:
            break
    return out, errs


class Tables(HTMLParser):
    """Wikipedia tables with rowspan/colspan, tracking the last heading (for the year)."""

    def __init__(self):
        super().__init__()
        self.tables, self.stack, self.heading, self.in_h = [], [], "", False
        self.cell, self.row, self.skip = None, None, 0

    def handle_starttag(self, tag, a):
        a = dict(a)
        if tag in ("h2", "h3", "h4"):
            self.in_h, self.heading = True, ""
        elif tag == "table":
            self.stack.append({"heading": self.heading, "rows": []})
        elif not self.stack:
            return
        elif tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = {"t": "", "rs": int(num(a.get("rowspan", "1")) or 1), "cs": int(num(a.get("colspan", "1")) or 1), "h": tag == "th"}
        elif tag in ("sup", "style"):
            self.skip += 1
        elif tag == "br" and self.cell is not None:
            self.cell["t"] += " "

    def handle_endtag(self, tag):
        if tag in ("h2", "h3", "h4"):
            self.in_h = False
        elif tag == "table" and self.stack:
            self.tables.append(self.stack.pop())
        elif not self.stack:
            return
        elif tag in ("sup", "style"):
            self.skip = max(0, self.skip - 1)
        elif tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.stack[-1]["rows"].append(self.row)
            self.row = None

    def handle_data(self, d):
        if self.in_h:
            self.heading += d
        if self.cell is not None and not self.skip:
            self.cell["t"] += d


def grid(rows):
    out, pend = [], {}
    for r in rows:
        line, col, it = [], 0, iter(r)
        cur = next(it, None)
        while cur is not None or pend.get(col):
            if pend.get(col):
                txt, left = pend[col]
                line.append(txt)
                pend[col] = (txt, left - 1) if left > 1 else None
                col += 1
                continue
            for _ in range(cur["cs"]):
                line.append(cur["t"].strip())
                if cur["rs"] > 1:
                    pend[col] = (cur["t"].strip(), cur["rs"] - 1)
                col += 1
            cur = next(it, None)
        out.append((line, all(c["h"] for c in r)))
    return out


def wiki_date(s, year_hint):
    s = s.lower().replace("–", "-").replace("—", "-")
    ms = [(m.start(), MONTHS[m.group(1)[:3]]) for m in re.finditer(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?", s)]
    if not ms:
        return None
    pos, mon = ms[-1]
    days = re.findall(r"\b(\d{1,2})\b", s[pos:]) or re.findall(r"\b(\d{1,2})\b", s)
    yrs = re.findall(r"\b(20\d\d)\b", s)
    yr = int(yrs[-1]) if yrs else year_hint
    if not days or not yr:
        return None
    try:
        return datetime(yr, mon, int(days[-1])).strftime("%Y-%m-%d")
    except ValueError:
        return None


def wikipedia_polls():
    api = "https://en.wikipedia.org/w/api.php?"
    found = get_json(api + urllib.parse.urlencode({"action": "query", "list": "prefixsearch", "format": "json",
                                                    "pssearch": "Opinion polling on the second Trump presidency", "pslimit": 10}))
    pages = [p["title"] for p in found.get("query", {}).get("prefixsearch", [])][:5] or ["Opinion polling on the second Trump presidency"]
    out = []
    for title in pages:
        try:
            d = get_json(api + urllib.parse.urlencode({"action": "parse", "page": title, "prop": "text", "format": "json",
                                                        "formatversion": 2, "redirects": 1}))
        except Exception as e:
            log(wiki_polls=title, error=str(e)[:100])
            continue
        p = Tables()
        p.feed(d.get("parse", {}).get("text", ""))
        n0 = len(out)
        for t in p.tables:
            g = grid(t["rows"])
            hdr = next((ln for ln, h in g if h and any("approv" in c.lower() for c in ln)), None)
            if not hdr:
                continue
            low = [c.lower() for c in hdr]
            ix = lambda f: next((i for i, c in enumerate(low) if f(c)), None)
            i_p = ix(lambda c: "poll" in c or "source" in c or "firm" in c)
            i_d = ix(lambda c: "date" in c)
            i_a = ix(lambda c: c.startswith("approv"))
            i_x = ix(lambda c: c.startswith("disapprov"))
            i_n = ix(lambda c: "sample" in c)
            if None in (i_p, i_d, i_a):
                continue
            y = re.findall(r"20\d\d", t["heading"] + " " + title)
            yh = int(y[-1]) if y else None
            for ln, h in g:
                if h or len(ln) <= max(i_p, i_d, i_a):
                    continue
                end = wiki_date(ln[i_d], yh)
                a = num(ln[i_a])
                if not end or a is None or not (15 <= a <= 85) or end < CONFIG["perfil"]["inauguracion"] or end > NOW.strftime("%Y-%m-%d"):
                    continue
                pop = re.search(r"\b(LV|RV|A)\b", " ".join(ln))
                out.append({"src": "Wikipedia", "pollster": re.sub(r"\s+", " ", ln[i_p]).strip()[:60], "start": end, "end": end,
                            "n": int(num(ln[i_n]) or 0) if i_n is not None and i_n < len(ln) else 0, "pop": pop.group(1) if pop else "",
                            "app": a, "dis": num(ln[i_x]) if i_x is not None and i_x < len(ln) else None, "url": ""})
        log(wiki_polls=title, rows=len(out) - n0)
        time.sleep(1)
    return out


def polls():
    vh, errs = votehub()
    try:
        wk = wikipedia_polls()
    except Exception as e:
        wk, errs = [], errs + [f"wikipedia {type(e).__name__}: {str(e)[:100]}"]
    norm = lambda s: re.sub(r"[^a-z]", "", s.lower())[:12]
    seen = {(norm(p["pollster"]), p["end"]) for p in vh}
    # VoteHub is comprehensive and clean; Wikipedia rows (column parsing) only fill in when VoteHub is down
    allp = vh if len(vh) >= 200 else vh + [p for p in wk if (norm(p["pollster"]), p["end"]) not in seen]
    save_json("polls.json", {"fetched_at": iso(NOW), "polls": allp, "votehub": len(vh), "wikipedia": len(wk), "errors": errs})
    if not allp:
        raise RuntimeError("; ".join(errs) or "no polls parsed")
    return len(allp)


# ---------------------------------------------------------------- media
def media_rss():
    out = []
    for f in CONFIG["rss"]:
        try:
            root = ET.fromstring(get(f["url"], retries=1, timeout=40, headers={"User-Agent": BROWSER}))
        except Exception as e:
            log(rss=f["name"], error=str(e)[:120])
            continue
        n = 0
        items = list(root.iter("item")) or list(root.iter("{http://www.w3.org/2005/Atom}entry"))
        for it in items:
            g = lambda k: it.findtext(k) or it.findtext("{http://www.w3.org/2005/Atom}" + k)
            title = clean(g("title"))
            desc = clean(g("description") or g("summary"))[:400]
            created = parse_date(g("pubDate") or g("published") or g("updated") or it.findtext("{http://purl.org/dc/elements/1.1/}date"))
            link = g("link") or ""
            if not link:
                le = it.find("{http://www.w3.org/2005/Atom}link")
                link = le.get("href", "") if le is not None else ""
            if not title or not created:
                continue
            out.append({"id": "News:" + (link or title), "platform": "Media", "kind": "news", "text": title + ". " + desc,
                        "title": title, "outlet": f["name"], "lean": f["lean"], "created_at": created, "url": link.strip(),
                        "query": "rss", "engagement": 0})
            n += 1
        log(rss=f["name"], items=n)
    return out


def google_news():
    out = []
    for q in CONFIG["google_news"]["queries"]:
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
            {"q": q + " when:" + CONFIG.get("news_when", "7d"), "hl": "en-US", "gl": "US", "ceid": "US:en"})
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
            created = parse_date(it.findtext("pubDate"))
            if not created:
                continue
            link = it.findtext("link") or ""
            out.append({"id": "GNews:" + (it.findtext("guid") or link), "platform": "Google News", "kind": "news", "text": title,
                        "title": title, "outlet": outlet, "created_at": created, "url": link, "query": q, "engagement": 0})
        time.sleep(1)
    return out


# ---------------------------------------------------------------- GDELT
def gdelt():
    """GDELT DOC 2.0: one artlist of the last 24h in every language (country/language mix + foreign press), then the
    volume/tone timelines. GDELT asks for one request every 5 seconds and rate-limits GitHub runners often, so each
    block is optional and yesterday's block is kept when today's fails."""
    g = CONFIG["gdelt"]
    base = "https://api.gdeltproject.org/api/v2/doc/doc?"
    prev = json.loads((ST / "gdelt.json").read_text(encoding="utf8")) if (ST / "gdelt.json").exists() else {}
    out, errs = {"fetched_at": iso(NOW)}, {}
    jobs = {"all": {"mode": "artlist", "timespan": "24h", "maxrecords": 250, "sort": "hybridrel"},
            "arts": {"mode": "artlist", "timespan": "3d", "maxrecords": 150, "sort": "hybridrel", "q": " -sourcelang:english"},
            "vol": {"mode": "timelinevolraw", "timespan": "90d"}, "tone": {"mode": "timelinetone", "timespan": "90d"}}
    for k, p in jobs.items():
        q = '(trump OR "donald trump")' + p.pop("q", "")
        try:
            raw = get(base + urllib.parse.urlencode({"query": q, "format": "json", **p}), retries=1, wait=30, timeout=60).decode("utf8", "replace")
            d = json.loads(raw) if raw.strip().startswith("{") else {}
            log(gdelt=k, keys=list(d)[:4], sample=raw[:120])
            if d:
                out[k] = d
            else:
                errs[k] = "empty"
        except Exception as e:
            errs[k] = f"{type(e).__name__}: {str(e)[:100]}"
            log(gdelt=k, error=errs[k])
        time.sleep(8)
    for k in jobs:
        if k not in out and k in prev:
            out[k] = prev[k]
    out["errors"] = errs
    save_json("gdelt.json", out)
    if len(errs) == len(jobs) and not prev:
        raise RuntimeError("GDELT: " + "; ".join(errs.values()))
    return len(jobs) - len(errs)


# ---------------------------------------------------------------- YouTube
def youtube():
    keys = [k for k in (os.environ.get("YOUTUBE_API_KEY"), os.environ.get("YOUTUBE_API_KEY_ALT")) if k]
    if not keys:
        raise RuntimeError("missing YOUTUBE_API_KEY")
    key = keys[0]
    cfg = CONFIG["youtube"]
    api = "https://www.googleapis.com/youtube/v3/"
    since = iso(NOW - timedelta(days=cfg.get("days", 14)))
    out, seen, vids = [], set(), []
    for q in cfg["queries"]:
        params = {"part": "snippet", "type": "video", "q": q, "regionCode": cfg["region"], "relevanceLanguage": cfg["language"],
                  "publishedAfter": since, "maxResults": cfg["videos_per_query"], "order": "relevance", "key": key}
        items = None
        for attempt in range(3):
            try:
                items = get_json(api + "search?" + urllib.parse.urlencode(params | {"key": key}), retries=0).get("items", [])
                break
            except urllib.error.HTTPError as e:
                log(youtube_query=q, error=e.code, attempt=attempt, reason=e.read()[:160].decode("utf8", "replace"))
                if attempt == 0 and e.code == 429:
                    time.sleep(60)
                elif len(keys) > 1 and key == keys[0]:
                    key = keys[1]
                else:
                    break
        if items is None:
            if not out:
                raise RuntimeError("YouTube quota/limit; retry next run")
            break
        for v in items:
            vid = v["id"].get("videoId")
            if not vid or vid in seen:
                continue
            seen.add(vid)
            sn = v["snippet"]
            vt = clean(sn["title"] + ". " + sn.get("description", ""))
            if not any(c in vt.lower() for c in cfg["contexto"]):
                continue
            vids.append(vid)
            out.append({"id": f"YouTube:{vid}", "platform": "YouTube", "kind": "video", "video_id": vid, "text": vt[:600],
                        "title": clean(sn["title"]), "channel": sn["channelTitle"], "created_at": sn["publishedAt"][:19] + "Z",
                        "url": f"https://www.youtube.com/watch?v={vid}", "query": q, "engagement": 0})
            try:
                d = get_json(api + "commentThreads?" + urllib.parse.urlencode(
                    {"part": "snippet", "videoId": vid, "order": "relevance", "maxResults": cfg["comments_per_video"],
                     "textFormat": "plainText", "key": key}), retries=0)
            except urllib.error.HTTPError:
                continue
            for t in d.get("items", []):
                c = t["snippet"]["topLevelComment"]["snippet"]
                out.append({"id": f"YouTube:{t['id']}", "platform": "YouTube", "kind": "comment", "video_id": vid,
                            "video_title": clean(sn["title"]), "channel": sn["channelTitle"],
                            "text": clean(c.get("textOriginal") or c.get("textDisplay", ""))[:1500],
                            "created_at": c["publishedAt"][:19] + "Z", "url": f"https://www.youtube.com/watch?v={vid}&lc={t['id']}",
                            "query": q, "engagement": c.get("likeCount", 0) + t["snippet"].get("totalReplyCount", 0)})
        time.sleep(1)
    # views/likes of the videos (1 unit per 50)
    stats = {}
    for i in range(0, len(vids), 50):
        try:
            d = get_json(api + "videos?" + urllib.parse.urlencode({"part": "statistics", "id": ",".join(vids[i:i + 50]), "key": key}), retries=0)
            for v in d.get("items", []):
                s = v.get("statistics", {})
                stats[v["id"]] = {"views": int(s.get("viewCount", 0)), "likes": int(s.get("likeCount", 0)), "comments": int(s.get("commentCount", 0))}
        except Exception as e:
            log(youtube_stats=str(e)[:100])
    for r in out:
        if r["kind"] == "video" and r["video_id"] in stats:
            r.update(stats[r["video_id"]], engagement=stats[r["video_id"]]["views"])
    return out


# ---------------------------------------------------------------- Truth Social
def truth():
    out, errs = [], []
    try:
        data = get_json("https://ix.cnn.io/data/truth-social/truth_archive.json", timeout=120, headers={"Accept-Encoding": "gzip"})
        cutoff = iso(NOW - timedelta(days=CONFIG["window_days"]))
        for p in data:
            ca = (p.get("created_at") or "")[:19] + "Z"
            if ca < cutoff:
                continue
            out.append({"id": f"Truth:{p['id']}", "platform": "Truth Social", "kind": "truth", "text": clean(p.get("content"))[:2000],
                        "created_at": ca, "url": p.get("url") or "", "media": len(p.get("media") or []),
                        "replies": int(p.get("replies_count") or 0), "reblogs": int(p.get("reblogs_count") or 0),
                        "likes": int(p.get("favourites_count") or 0),
                        "engagement": int(p.get("favourites_count") or 0) + int(p.get("reblogs_count") or 0)})
    except Exception as e:
        errs.append(f"cnn archive {type(e).__name__}: {str(e)[:100]}")
    if not out:
        try:
            root = ET.fromstring(get("https://trumpstruth.org/feed", headers={"User-Agent": BROWSER}))
            for it in root.iter("item"):
                link = it.findtext("link") or ""
                created = parse_date(it.findtext("pubDate"))
                if created:
                    out.append({"id": "Truth:" + (link.rstrip("/").split("/")[-1] or link), "platform": "Truth Social", "kind": "truth",
                                "text": clean(it.findtext("description") or it.findtext("title"))[:2000], "created_at": created,
                                "url": link, "media": 0, "replies": 0, "reblogs": 0, "likes": 0, "engagement": 0})
        except Exception as e:
            errs.append(f"trumpstruth {type(e).__name__}: {str(e)[:100]}")
    if not out:
        raise RuntimeError("; ".join(errs))
    return out


# ---------------------------------------------------------------- Federal Register
def federal_register():
    base = "https://www.federalregister.gov/api/v1/documents.json?"
    out = {"fetched_at": iso(NOW), "docs": []}
    for kind in ("executive_order", "memorandum", "proclamation"):
        page = 1
        while page <= 6:
            q = [("conditions[presidential_document_type][]", kind), ("conditions[president][]", "donald-trump"),
                 ("conditions[signing_date][gte]", CONFIG["perfil"]["inauguracion"]), ("per_page", "500"), ("page", str(page)),
                 ("order", "newest")] + [("fields[]", f) for f in ("title", "signing_date", "publication_date", "executive_order_number", "html_url", "document_number")]
            d = get_json(base + urllib.parse.urlencode(q))
            for r in d.get("results", []):
                out["docs"].append({"type": kind, "t": r.get("title", ""), "d": r.get("signing_date") or r.get("publication_date"),
                                    "eo": r.get("executive_order_number"), "u": r.get("html_url")})
            if not d.get("next_page_url"):
                break
            page += 1
            time.sleep(1)
        log(federal_register=kind, docs=sum(1 for x in out["docs"] if x["type"] == kind))
    save_json("fedreg.json", out)
    return len(out["docs"])


# ---------------------------------------------------------------- Polymarket
def polymarket():
    """Prediction markets about Trump: Polymarket (gamma API), Kalshi public API as fallback."""
    cfg = CONFIG["polymarket"]
    out, errs = [], []
    for ua in ("python-requests/2.32.3", BROWSER):
        try:
            evs = get_json("https://gamma-api.polymarket.com/events?" + urllib.parse.urlencode(
                {"tag_slug": cfg["tag"], "closed": "false", "limit": 60, "order": "volume24hr", "ascending": "false"}),
                headers={"User-Agent": ua, "Accept": "application/json", "Accept-Encoding": "identity"}, retries=0)
        except Exception as e:
            errs.append(f"polymarket {type(e).__name__}: {str(e)[:80]}")
            continue
        for e in evs:
            mk = []
            for m in e.get("markets") or []:
                if m.get("closed"):
                    continue
                try:
                    prices = json.loads(m.get("outcomePrices") or "[]")
                    outs = json.loads(m.get("outcomes") or "[]")
                except ValueError:
                    continue
                if prices:
                    mk.append({"q": m.get("groupItemTitle") or m.get("question"), "p": round(100 * float(prices[0]), 1), "o": outs[0] if outs else "Yes",
                               "ch": round(100 * float(m.get("oneDayPriceChange") or 0), 1), "v": round(float(m.get("volume") or 0))})
            if mk:
                mk.sort(key=lambda x: -x["p"])
                out.append({"src": "Polymarket", "t": e.get("title"), "u": "https://polymarket.com/event/" + (e.get("slug") or ""),
                            "v": round(float(e.get("volume") or 0)), "v24": round(float(e.get("volume24hr") or 0)), "end": (e.get("endDate") or "")[:10], "m": mk[:6]})
        break
    if not out:
        try:
            cursor, seen = "", 0
            while seen < 8:
                d = get_json("https://api.elections.kalshi.com/trade-api/v2/events?" + urllib.parse.urlencode(
                    {"status": "open", "with_nested_markets": "true", "limit": 200} | ({"cursor": cursor} if cursor else {})), retries=1)
                for e in d.get("events", []):
                    if "trump" not in (e.get("title", "") + " " + e.get("sub_title", "")).lower():
                        continue
                    mk = []
                    for m in e.get("markets") or []:
                        p = m.get("last_price_dollars") or m.get("last_price")
                        if p is None:
                            continue
                        p = float(p) * (100 if float(p) <= 1 and "last_price_dollars" in m else 1)
                        prev = m.get("previous_price_dollars") or m.get("previous_price")
                        pv = float(prev) * (100 if prev is not None and "previous_price_dollars" in m else 1) if prev is not None else p
                        mk.append({"q": m.get("yes_sub_title") or m.get("subtitle") or m.get("title"), "p": round(p, 1), "o": "Yes",
                                   "ch": round(p - pv, 1), "v": int(float(m.get("volume_fp") or m.get("volume") or 0))})
                    if mk:
                        mk.sort(key=lambda x: -x["p"])
                        vol = sum(x["v"] for x in mk)
                        out.append({"src": "Kalshi", "t": e.get("title"), "u": "https://kalshi.com/markets/" + (e.get("series_ticker") or "").lower(),
                                    "v": vol, "v24": int(sum(float(m.get("volume_24h_fp") or m.get("volume_24h") or 0) for m in e.get("markets") or [])),
                                    "end": "", "m": mk[:6], "unit": "contracts"})
                cursor = d.get("cursor") or ""
                seen += 1
                if not cursor:
                    break
        except Exception as e:
            errs.append(f"kalshi {type(e).__name__}: {str(e)[:80]}")
    log(markets=len(out), errors=errs)
    if not out:
        raise RuntimeError("; ".join(errs) or "no Trump markets")
    out.sort(key=lambda x: -x["v24"])
    save_json("markets.json", {"fetched_at": iso(NOW), "events": out[: cfg["max_events"]]})
    return len(out)


# ---------------------------------------------------------------- FRED
def fred():
    """Economy without keys: BLS public API (CPI, unemployment), University of Michigan consumer sentiment,
    Freddie Mac 30-year mortgage rate and the S&P 500 from Stooq. (FRED times out from GitHub runners.)"""
    out = {"fetched_at": iso(NOW), "series": {}}
    names = CONFIG["fred"]
    try:
        body = json.dumps({"seriesid": ["CUUR0000SA0", "LNS14000000"], "startyear": "2023", "endyear": str(NOW.year)}).encode()
        d = get_json("https://api.bls.gov/publicAPI/v1/timeseries/data/", data=body, headers={"Content-Type": "application/json"})
        for se in d.get("Results", {}).get("series", []):
            sid = {"CUUR0000SA0": "CPIAUCSL", "LNS14000000": "UNRATE"}[se["seriesID"]]
            rows = sorted((f"{x['year']}-{x['period'][1:]}-01", float(x["value"])) for x in se["data"]
                          if x["period"].startswith("M") and x["period"] != "M13" and re.match(r"^\d+(\.\d+)?$", x["value"]))
            if rows:
                out["series"][sid] = {"name": names[sid], "data": rows}
    except Exception as e:
        log(bls=f"{type(e).__name__}: {str(e)[:120]}")
    try:
        raw = get("https://www.sca.isr.umich.edu/files/tbmics.csv", headers={"User-Agent": BROWSER}, retries=1, timeout=40).decode("utf8", "replace")
        mon = {m: i + 1 for i, m in enumerate("january february march april may june july august september october november december".split())}
        rows = [(f"{int(r[1])}-{mon[r[0].strip().lower()]:02d}-01", float(r[2])) for r in csv.reader(io.StringIO(raw))
                if len(r) >= 3 and r[0].strip().lower() in mon and r[1].strip().isdigit() and int(r[1]) >= 2023 and re.match(r"^\d", r[2].strip())]
        if rows:
            out["series"]["UMCSENT"] = {"name": names["UMCSENT"], "data": sorted(rows)}
    except Exception as e:
        log(umich=f"{type(e).__name__}: {str(e)[:120]}")
    try:
        raw = get("https://www.freddiemac.com/pmms/docs/PMMS_history.csv", headers={"User-Agent": BROWSER}, retries=1, timeout=40).decode("utf8", "replace")
        rows = []
        for r in csv.reader(io.StringIO(raw)):
            if len(r) >= 2 and re.match(r"\d{1,2}/\d{1,2}/\d{4}", r[0]) and re.match(r"^\d", r[1]):
                m, dd, y = r[0].split("/")
                if int(y) >= 2023:
                    rows.append((f"{y}-{int(m):02d}-{int(dd):02d}", float(r[1])))
        if rows:
            out["series"]["MORTGAGE30US"] = {"name": names["MORTGAGE30US"], "data": sorted(rows)}
    except Exception as e:
        log(pmms=f"{type(e).__name__}: {str(e)[:120]}")
    try:
        raw = get("https://stooq.com/q/d/l/?s=%5Espx&i=w", headers={"User-Agent": BROWSER}, retries=1, timeout=40).decode("utf8", "replace")
        rows = [(r[0], float(r[4])) for r in csv.reader(io.StringIO(raw)) if len(r) >= 5 and re.match(r"\d{4}-", r[0]) and r[0] >= "2023"]
        if rows:
            out["series"]["SP500"] = {"name": names["SP500"], "data": rows}
    except Exception as e:
        log(stooq=f"{type(e).__name__}: {str(e)[:120]}")
    log(economy=list(out["series"]))
    if not out["series"]:
        raise RuntimeError("no economic source answered")
    save_json("fred.json", out)
    return len(out["series"])


# ---------------------------------------------------------------- Wikipedia pageviews
def wiki():
    end = NOW - timedelta(days=1)
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    out = {"fetched_at": iso(NOW), "views": {}}
    for name, art in CONFIG["wiki_pages"].items():
        url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/"
               + urllib.parse.quote(art, safe="") + f"/daily/{start:%Y%m%d}/{end:%Y%m%d}")
        try:
            items = get_json(url).get("items", [])
            out["views"][name] = {it["timestamp"][:8]: it["views"] for it in items}
        except Exception as e:
            log(wiki=name, error=str(e)[:100])
        time.sleep(0.3)
    save_json("wiki.json", out)
    return len(out["views"])


# ---------------------------------------------------------------- Google Trends
def trends():
    import http.cookiejar
    cfg = CONFIG["trends"]
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    op.addheaders = [("User-Agent", BROWSER), ("Accept-Language", "en-US,en;q=0.9")]

    def call(url):
        for i in range(3):
            try:
                return op.open(url, timeout=30).read().decode("utf-8")
            except urllib.error.HTTPError as e:
                if e.code == 429 and i < 2:
                    time.sleep(20 * (i + 1))
                    continue
                raise

    try:
        op.open("https://trends.google.com/trends/explore?geo=US", timeout=30).read()
    except urllib.error.HTTPError:
        time.sleep(5)
    js = lambda t: json.loads(t[t.index("{"):])
    prev = json.loads((ST / "trends.json").read_text(encoding="utf8")) if (ST / "trends.json").exists() else {}
    out = {"fetched_at": iso(NOW), "errors": {}}

    def explore(terms, span):
        req = {"comparisonItem": [{"keyword": t, "geo": cfg["geo"], "time": span} for t in terms], "category": 0, "property": ""}
        ex = js(call("https://trends.google.com/trends/api/explore?" + urllib.parse.urlencode({"hl": "en-US", "tz": 300, "req": json.dumps(req)})))
        return {w.get("id"): w for w in ex["widgets"]}

    def widget(path, w):
        return js(call(f"https://trends.google.com/trends/api/widgetdata/{path}?" + urllib.parse.urlencode(
            {"hl": "en-US", "tz": 300, "req": json.dumps(w["request"]), "token": w["token"]})))

    def series(w, terms):
        d = widget("multiline", w)
        s = {t: {} for t in terms}
        for pt in d["default"]["timelineData"]:
            day = datetime.fromtimestamp(int(pt["time"]), timezone.utc).strftime("%Y-%m-%d")
            for t, v in zip(terms, pt["value"]):
                s[t][day] = v
        return s

    jobs = [("figures", cfg["terminos"], "today 12-m"), ("issues", cfg["issues"], "today 3-m"), ("trump7d", ["Trump"], "now 7-d")]
    for name, terms, span in jobs:
        try:
            ws = explore(terms, span)
            out[name] = series(ws["TIMESERIES"], terms)
            if name == "trump7d":
                geo = next((w for k, w in ws.items() if k.startswith("GEO_MAP")), None)
                if geo:
                    d = widget("comparedgeo", geo)
                    out["states"] = {g["geoName"]: g["value"][0] for g in d["default"]["geoMapData"] if g.get("hasData", [True])[0]}
                for k, w in ws.items():
                    if k.startswith("RELATED_QUERIES"):
                        d = widget("relatedsearches", w)
                        lists = d["default"]["rankedList"]
                        out["top_queries"] = [{"q": x["query"], "v": x["value"]} for x in lists[0]["rankedKeyword"][:15]] if lists else []
                        out["rising"] = [{"q": x["query"], "v": x.get("formattedValue", x["value"])} for x in lists[1]["rankedKeyword"][:15]] if len(lists) > 1 else []
                    if k.startswith("RELATED_TOPICS"):
                        d = widget("relatedsearches", w)
                        lists = d["default"]["rankedList"]
                        out["rising_topics"] = [{"q": x["topic"]["title"], "t": x["topic"].get("type", ""), "v": x.get("formattedValue", x["value"])}
                                                for x in (lists[1]["rankedKeyword"] if len(lists) > 1 else [])[:12]]
        except Exception as e:
            out["errors"][name] = f"{type(e).__name__}: {str(e)[:120]}"
            log(trends=name, error=out["errors"][name])
        time.sleep(6)
    for k, v in prev.items():  # keep yesterday's block if one failed today
        out.setdefault(k, v)
    save_json("trends.json", out)
    if len(out["errors"]) == len(jobs):
        raise RuntimeError("Google Trends blocked: " + "; ".join(out["errors"].values()))
    return len(jobs) - len(out["errors"])


# ---------------------------------------------------------------- Meta Ad Library
def meta_ads():
    tok = os.environ.get("META_TOKEN", "").strip()
    if not tok:
        raise RuntimeError("no META_TOKEN")
    cfg = CONFIG["meta_ads"]
    since = (NOW - timedelta(days=cfg["days"])).strftime("%Y-%m-%d")
    fields = ("id,page_id,page_name,ad_delivery_start_time,ad_delivery_stop_time,spend,impressions,currency,publisher_platforms,"
              "demographic_distribution,delivery_by_region,bylines,ad_creative_bodies")
    ads, err = {}, None
    for t in cfg["terms"]:
        url = "https://graph.facebook.com/v21.0/ads_archive?" + urllib.parse.urlencode(
            {"search_terms": t, "ad_reached_countries": json.dumps(["US"]), "ad_type": "POLITICAL_AND_ISSUE_ADS", "ad_active_status": "ALL",
             "ad_delivery_date_min": since, "fields": fields, "limit": 250, "access_token": tok})
        for _ in range(cfg["max_pages"]):
            try:
                d = get_json(url, retries=1, timeout=120)
            except urllib.error.HTTPError as e:
                err = f"HTTP {e.code}: {e.read()[:200].decode('utf8', 'replace')}"
                break
            for a in d.get("data", []):
                ads[a["id"]] = a
            url = (d.get("paging") or {}).get("next")
            if not url:
                break
    if not ads and err:
        raise RuntimeError(err.replace(tok, "…"))
    with gzip.open(ST / "ads.json.gz", "wt", encoding="utf8") as f:
        json.dump({"fetched_at": iso(NOW), "since": since, "ads": list(ads.values())}, f)
    return len(ads)


# ---------------------------------------------------------------- Instagram (free) and X (paid, manual only)
def instagram():
    tok = os.environ.get("META_TOKEN", "").strip()
    ig = os.environ.get("META_IG_USER_ID", "").strip()
    if not tok or not ig:
        raise RuntimeError("no META_TOKEN / META_IG_USER_ID")
    fields = ("username,name,followers_count,media_count,"
              "media.limit(50){caption,like_count,comments_count,timestamp,media_type,media_product_type,permalink}")
    accounts, errs = [], []
    for h, label in CONFIG["instagram"].items():
        url = f"https://graph.facebook.com/v21.0/{ig}?" + urllib.parse.urlencode(
            {"fields": f"business_discovery.username({h}){{{fields}}}", "access_token": tok})
        try:
            bd = get_json(url, retries=1, timeout=60).get("business_discovery") or {}
        except urllib.error.HTTPError as e:
            errs.append(f"{h}: HTTP {e.code}")
            continue
        except Exception as e:
            errs.append(f"{h}: {type(e).__name__}")
            continue
        media = [{"t": clean(m.get("caption") or "")[:280], "d": (m.get("timestamp") or "")[:19] + "Z", "l": m.get("like_count") or 0,
                  "c": m.get("comments_count") or 0, "k": m.get("media_product_type") if m.get("media_product_type") == "REELS" else m.get("media_type"),
                  "u": m.get("permalink")} for m in (bd.get("media") or {}).get("data", [])]
        accounts.append({"h": h, "n": label, "f": bd.get("followers_count"), "mc": bd.get("media_count"), "media": media})
        time.sleep(2)
    if not accounts:
        raise RuntimeError("; ".join(errs)[:200] or "no accounts")
    save_json("instagram.json", {"at": iso(NOW), "accounts": accounts, "errors": errs})
    return len(accounts)


def x_posts():
    """Paid X API. Called only when 'x' is passed explicitly (manual workflow); never part of the daily run."""
    sys.path.insert(0, str(HERE.parent / "x"))
    from x_api import buscar
    cx = json.loads((HERE.parent / "x" / "tableros.json").read_text(encoding="utf8"))["trump"]
    rows, estado = buscar("trump", cx)
    log(x=estado)
    if not estado.get("ok") and not rows:
        raise RuntimeError(estado.get("error") or estado.get("nota") or "X error")
    return rows


# ---------------------------------------------------------------- states: Census ACS, 2020 Census and BEA (free, no key)
ACS_VARS = {"pop": "B01003_001E", "black": "B02001_003E", "hisp": "B03003_003E", "foreign": "B05002_013E", "income": "B19013_001E",
            "age": "B01002_001E", "ed_tot": "B15003_001E", "ba": "B15003_022E", "ma": "B15003_023E", "prof": "B15003_024E", "phd": "B15003_025E",
            "pov_tot": "B17001_001E", "pov": "B17001_002E", "home": "B25077_001E", "vet_tot": "B21001_001E", "vet": "B21001_002E",
            "white": "B02001_002E", "asian": "B02001_005E"}


def census():
    out, errs = {"at": iso(NOW)}, []
    vals = ",".join(ACS_VARS.values())
    def cjson(url):
        raw = get(url, headers={"User-Agent": BROWSER, "Accept": "application/json"}, retries=1, timeout=60).decode("utf8", "replace")
        try:
            return json.loads(raw)
        except ValueError:
            raise RuntimeError("not JSON: " + re.sub(r"\s+", " ", raw)[:160])
    ckey = os.environ.get("CENSUS_API_KEY", "").strip()
    key = "&key=" + ckey if ckey else ""
    for year in ((2024, 2023, 2022) if ckey else ()):  # the Census API now asks for a (free) key
        try:
            rows = cjson(f"https://api.census.gov/data/{year}/acs/acs1?get=NAME,{vals}&for=state:*{key}")
            hdr = rows[0]
            out["acs_year"] = year
            out["acs"] = {r[0]: {k: (float(r[hdr.index(v)]) if r[hdr.index(v)] not in (None, "", "null") else None) for k, v in ACS_VARS.items()} for r in rows[1:]}
            break
        except Exception as e:
            errs.append(f"acs {year}: {type(e).__name__}: {str(e)[:80]}")
    if not ckey:
        errs.append("no CENSUS_API_KEY: ACS (education, poverty, veterans...) and rural share skipped")
    # keyless fallbacks: Census population estimates (race, Hispanic origin, age) and BEA population + per-capita income
    if not out.get("acs"):
        for f in ("2020-2024/state/asrh/sc-est2024-sr11h.csv", "2020-2023/state/asrh/sc-est2023-sr11h.csv"):
            try:
                txt = get("https://www2.census.gov/programs-surveys/popest/datasets/" + f, headers={"User-Agent": BROWSER}, retries=1, timeout=120).decode("latin-1")
                rd = csv.DictReader(io.StringIO(txt))
                col = [c for c in rd.fieldnames if c.startswith("POPESTIMATE")][-1]
                pe = {}
                for r in rd:
                    if r.get("SUMLEV") != "040" or r.get("SEX") != "0":
                        continue
                    st = pe.setdefault(r["NAME"], {"pop": 0, "white": 0, "black": 0, "asian": 0, "hisp": 0, "ages": [0] * 86})
                    v, o, rc, ag = float(r[col]), r["ORIGIN"], r["RACE"], int(r["AGE"])
                    if o == "0":
                        st["pop"] += v
                        st["ages"][min(ag, 85)] += v
                        if rc in ("1", "2", "4"):
                            st[{"1": "white", "2": "black", "4": "asian"}[rc]] += v
                    elif o == "2":
                        st["hisp"] += v
                for st in pe.values():
                    half, acc = st["pop"] / 2, 0
                    for ag, v in enumerate(st.pop("ages")):
                        acc += v
                        if acc >= half:
                            st["age"] = ag
                            break
                if pe:
                    out["popest"] = {"year": col[-4:], "states": pe}
                    break
            except Exception as e:
                errs.append(f"popest {f[:9]}: {type(e).__name__}: {str(e)[:80]}")
    try:
        import zipfile
        z = zipfile.ZipFile(io.BytesIO(get("https://apps.bea.gov/regional/zip/SAINC.zip", retries=1, timeout=120)))
        name = next(n for n in z.namelist() if n.startswith("SAINC1_") and "ALL_AREAS" in n and n.endswith(".csv"))
        rd = csv.reader(io.TextIOWrapper(z.open(name), encoding="latin-1"))
        hdr = next(rd)
        yrs = [i for i, h in enumerate(hdr) if h.strip().isdigit()]
        inc = {}
        for r in rd:
            if len(r) > max(yrs) and r[hdr.index("LineCode")].strip() in ("2", "3"):
                vy = [r[i].strip() for i in yrs if re.match(r"^[\d.]+$", r[i].strip())]
                if vy:
                    inc.setdefault(r[hdr.index("GeoName")].strip().strip("*").strip(), {})["pop" if r[hdr.index("LineCode")].strip() == "2" else "pcpi"] = float(vy[-1])
        out["bea_inc"] = inc
    except Exception as e:
        errs.append(f"bea sainc: {type(e).__name__}: {str(e)[:80]}")
    try:
        if not ckey:
            raise RuntimeError("needs CENSUS_API_KEY")
        rows = cjson("https://api.census.gov/data/2020/dec/dhc?get=NAME,P2_001N,P2_003N&for=state:*" + key)
        out["rural"] = {r[0]: round(100 * float(r[2]) / float(r[1]), 1) for r in rows[1:]}
    except Exception as e:
        errs.append(f"dhc: {type(e).__name__}: {str(e)[:80]}")
    # GDP by state (current dollars, all industries) from BEA's public bulk file
    try:
        import zipfile
        z = zipfile.ZipFile(io.BytesIO(get("https://apps.bea.gov/regional/zip/SAGDP.zip", retries=1, timeout=120)))
        name = next(n for n in z.namelist() if n.startswith("SAGDP2") and "ALL_AREAS" in n and n.endswith(".csv"))
        rd = csv.reader(io.TextIOWrapper(z.open(name), encoding="latin-1"))
        hdr = next(rd)
        yrs = [i for i, h in enumerate(hdr) if h.strip().isdigit()]
        gdp = {}
        for r in rd:
            if len(r) > max(yrs) and r[hdr.index("LineCode")].strip() == "1":
                vals_y = [(hdr[i].strip(), r[i].strip()) for i in yrs if re.match(r"^[\d.]+$", r[i].strip())]
                if vals_y:
                    gdp[r[hdr.index("GeoName")].strip().strip("*").strip()] = {"y": vals_y[-1][0], "v": float(vals_y[-1][1])}
        out["gdp"] = gdp
    except Exception as e:
        errs.append(f"bea: {type(e).__name__}: {str(e)[:80]}")
    out["errors"] = errs
    if errs:
        log(census_errors=errs)
    if not (out.get("acs") or out.get("popest") or out.get("bea_inc") or out.get("gdp")):
        raise RuntimeError("; ".join(errs)[:300])
    save_json("census.json", out)
    return len(out.get("acs") or (out.get("popest") or {}).get("states") or out.get("gdp") or {})


# ---------------------------------------------------------------- main
def save(known):
    cutoff = iso(NOW - timedelta(days=CONFIG["window_days"] + 10))
    keep = [r for r in known.values() if r.get("created_at", "") >= cutoff]
    STORE.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in keep) + "\n", encoding="utf8")


def main():
    ST.mkdir(parents=True, exist_ok=True)
    only = set(sys.argv[1:])
    known = {}
    if STORE.exists():
        for line in STORE.read_text(encoding="utf8").splitlines():
            try:
                r = json.loads(line)
                known[r["id"]] = r
            except (ValueError, KeyError):
                pass
    status = json.loads((ST / "status.json").read_text(encoding="utf8")) if (ST / "status.json").exists() else {}
    streams = [("rss", media_rss), ("google_news", google_news), ("youtube", youtube), ("truth_social", truth), ("x", x_posts)]
    side = [("polls", polls), ("gdelt", gdelt), ("federal_register", federal_register), ("polymarket", polymarket),
            ("fred", fred), ("wikipedia", wiki), ("google_trends", trends), ("meta_ads", meta_ads), ("instagram", instagram), ("census", census)]
    for name, fn in streams:
        if (only and name not in only) or (name == "x" and "x" not in only):  # X is paid: only on explicit request
            continue
        try:
            rows = fn()
            new = 0
            for r in rows:
                if r["id"] not in known:
                    new += 1
                    known[r["id"]] = r
                elif r["kind"] in ("truth", "video", "comment"):  # refresh engagement
                    known[r["id"]].update({k: r[k] for k in ("engagement", "likes", "reblogs", "replies", "views") if k in r})
            status[name] = {"ok": True, "items": len(rows), "new": new, "at": iso(NOW)}
            save(known)
        except Exception as e:
            status[name] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}", "at": iso(NOW)}
        log(source=name, **status[name])
    for name, fn in side:
        if only and name not in only:
            continue
        t0 = time.time()
        try:
            status[name] = {"ok": True, "items": fn(), "at": iso(NOW)}
        except Exception as e:
            status[name] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}", "at": iso(NOW)}
        log(source=name, seconds=round(time.time() - t0), **status[name])
    (ST / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding="utf8")


if __name__ == "__main__":
    main()
