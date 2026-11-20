"""Donald J. Trump Monitor: turns trump/.store into trump/data/monitor.json (published) and textos.json (drill-down).

Only aggregates, headlines, his own public Truth Social posts and short, anonymised comment excerpts with a link
to the original are published. Raw comment texts stay in the workflow cache.

Approval average (our own, transparent): every public poll since inauguration; for each day, polls that ended in
the previous 21 days, weight = recency (half-life 7 days) x sqrt(sample size, capped at 3,000) / number of polls the
same pollster has in the window, so daily trackers cannot dominate. Likely/registered voters and adults are pooled.
"""
from __future__ import annotations

import gzip
import json
import math
import os
import re
import time
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
ST = HERE / ".store"
OUT = HERE / "data"
CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf8"))
NOW = datetime.now(timezone.utc)
TODAY = NOW.strftime("%Y-%m-%d")
ET_TZ = ZoneInfo("America/New_York")
INAUG = CONFIG["perfil"]["inauguracion"]
NLP_CACHE = ST / "nlp.jsonl.gz"
BUDGET = float(os.environ.get("TRUMP_NLP_SECONDS", "600"))

STOP = set("""a about above after again against all am an and any are aren as at be because been before being below between both
but by can cannot could did didn do does doesn doing don down during each few for from further had has have having he her here hers
herself him himself his how i if in into is isn it its itself let me more most my myself no nor not of off on once only or other ought
our ours ourselves out over own same she should so some such than that the their theirs them themselves then there these they this
those through to too under until up very was we were what when where which while who whom why with won would you your yours
yourself yourselves amp quot its it's im i'm dont don't thats that's he's hes doesnt didnt cant can't isnt wont via get got gets
new says said say saying told tells report reports reported first last next two three one now today yesterday week weeks month
months year years may might must shall us u.s. mr ms per after over amid near could would should also just like""".split())
STOP |= set(CONFIG.get("stop_extra", []))
WORD = re.compile(r"[a-z][a-z'\-]{2,}")
LEAN_GROUP = {"Left": "Left", "Lean Left": "Left", "Center": "Center", "Lean Right": "Right", "Right": "Right"}
TOPICS = CONFIG["temas"]
POSW, NEGW = set(CONFIG["positivo"]), set(CONFIG["negativo"])
MASK = [(re.compile(r"@[\w.\-]{2,}"), "@…"), (re.compile(r"\S+@\S+\.\w+"), "[email]"), (re.compile(r"\+?1?[\s\-.(]*\d{3}[\s\-.)]*\d{3}[\s\-.]*\d{4}\b"), "[phone]")]
EMO_LEX = {
    "anger": set("angry furious outrage outraged disgusting disgraceful rage mad hate hateful sick fed up enough pissed".split()),
    "fear": set("afraid scared fear terrified worried worry dangerous threat scary alarming panic".split()),
    "sadness": set("sad sadly tragic heartbreaking depressing shame sorry miss grief".split()),
    "joy": set("love great amazing awesome happy proud best beautiful wonderful thank thanks blessed glad".split()),
    "disgust": set("gross disgusting vile pathetic trash garbage clown clowns sickening".split()),
    "surprise": set("wow unbelievable shocking shocked incredible surprised omg insane".split()),
}
TOXIC = set("idiot idiots stupid moron morons clown clowns trash scum loser losers pathetic dumb traitor traitors fascist nazi".split())


def fold(s):
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def load(name, default=None):
    p = ST / name
    if not p.exists():
        return default
    if name.endswith(".gz"):
        with gzip.open(p, "rt", encoding="utf8") as f:
            return json.load(f)
    return json.loads(p.read_text(encoding="utf8"))


def items():
    out = []
    if (ST / "items.jsonl").exists():
        for line in (ST / "items.jsonl").read_text(encoding="utf8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def day(s):
    return s[:10]


def ago(n):
    return (NOW - timedelta(days=n)).strftime("%Y-%m-%d")


def excerpt(t, n=260):
    for r, rep in MASK:
        t = r.sub(rep, t)
    return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0] + "…"


def topics_of(text):
    t = " " + fold(text) + " "
    return [k for k, ws in TOPICS.items() if any(w in t for w in ws)]


def words(text, extra=()):
    return [w.strip("'-") for w in WORD.findall(fold(text)) if w.strip("'-") not in STOP and w not in extra and len(w.strip("'-")) > 2]


def cloud(rows, n=70, field="text"):
    c, tone = Counter(), defaultdict(lambda: [0, 0])
    for r in rows:
        ws = set(words(r.get(field, "")))
        c.update(ws)
        for w in ws:
            tone[w][0] += r.get("tono") == "POS"
            tone[w][1] += r.get("tono") == "NEG"
    out = []
    for w, k in c.most_common(n):
        if k < 2:
            break
        p, q = tone[w]
        out.append({"w": w, "n": k, "s": round((p - q) / k, 2)})
    return out


def pct(a, b):
    return round(100 * a / b, 1) if b else 0


# ---------------------------------------------------------------- NLP
def nlp_label(rows):
    """Sentiment (POS/NEU/NEG) + emotion. pysentimiento (BERTweet, English) within a time budget, then VADER, then lexicon."""
    cache = {}
    if NLP_CACHE.exists():
        with gzip.open(NLP_CACHE, "rt", encoding="utf8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    cache[r["id"]] = r
                except ValueError:
                    pass
    todo = [r for r in rows if r["id"] not in cache or (cache[r["id"]]["m"] != "model" and r["kind"] == "comment")]
    todo.sort(key=lambda r: r["created_at"], reverse=True)
    model_rows = [r for r in todo if r["kind"] == "comment"]
    t0 = time.time()
    if model_rows:
        try:
            from pysentimiento import create_analyzer
            sa = create_analyzer(task="sentiment", lang="en")
            ea = create_analyzer(task="emotion", lang="en")
            for i in range(0, len(model_rows), 64):
                if time.time() - t0 > BUDGET:
                    break
                batch = model_rows[i:i + 64]
                texts = [r["text"][:500] for r in batch]
                s, e = sa.predict(texts), ea.predict(texts)
                for r, a, b in zip(batch, s, e):
                    emo = b.output[0] if isinstance(b.output, list) else b.output
                    cache[r["id"]] = {"id": r["id"], "t": a.output, "e": emo if emo != "others" else "", "m": "model"}
            print(f"nlp: model labelled {sum(1 for r in model_rows if cache.get(r['id'], {}).get('m') == 'model')} comments in {time.time() - t0:.0f}s", flush=True)
        except Exception as ex:
            print(f"nlp: no model ({str(ex)[:100]})", flush=True)
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        vader = SentimentIntensityAnalyzer()
    except Exception:
        vader = None
    for r in rows:
        if r["id"] in cache:
            continue
        f = fold(r["text"])
        ws = set(WORD.findall(f))
        if vader:
            c = vader.polarity_scores(r["text"][:800])["compound"]
            t = "POS" if c >= 0.25 else "NEG" if c <= -0.25 else "NEU"
        else:
            p, n = len(ws & POSW), len(ws & NEGW)
            t = "POS" if p > n else "NEG" if n > p else "NEU"
        emo = max(EMO_LEX, key=lambda k: len(ws & EMO_LEX[k]))
        cache[r["id"]] = {"id": r["id"], "t": t, "e": emo if ws & EMO_LEX[emo] else "", "m": "vader" if vader else "lexicon"}
    for r in rows:
        c = cache[r["id"]]
        r["tono"], r["emo"], r["m"] = c["t"], c["e"], c["m"]
        r["tox"] = bool(set(WORD.findall(fold(r["text"]))) & TOXIC)
    keep = {r["id"] for r in rows}
    with gzip.open(NLP_CACHE, "wt", encoding="utf8") as f:
        for k, v in cache.items():
            if k in keep:
                f.write(json.dumps(v) + "\n")


# ---------------------------------------------------------------- approval
def approval():
    d = load("polls.json") or {}
    ps = [p for p in d.get("polls", []) if p.get("app") is not None and INAUG <= p["end"] <= TODAY]
    if not ps:
        return None
    for p in ps:
        if p.get("dis") is None or not p["dis"]:
            p["dis"] = None
        p["_k"] = re.sub(r"[^a-z]", "", p["pollster"].lower())[:14] or "?"
    ps.sort(key=lambda p: p["end"])
    start = datetime.fromisoformat(INAUG).date()
    days = (NOW.date() - start).days + 1
    series = []
    j0 = 0
    for i in range(days):
        dd = start + timedelta(days=i)
        ds = dd.isoformat()
        lo = (dd - timedelta(days=21)).isoformat()
        while j0 < len(ps) and ps[j0]["end"] < lo:
            j0 += 1
        win = [p for p in ps[j0:] if p["end"] <= ds]
        if len(win) < 3:
            win = [p for p in ps if p["end"] <= ds][-8:]
        if len(win) < 3:
            continue
        per = Counter(p["_k"] for p in win)
        wa = wd = sa = sd = 0.0
        for p in win:
            age = (dd - datetime.fromisoformat(p["end"]).date()).days
            w = 0.5 ** (age / 7) * math.sqrt(min(p["n"] or 800, 3000) / 600) / per[p["_k"]]
            wa += w
            sa += w * p["app"]
            if p["dis"] is not None:
                wd += w
                sd += w * p["dis"]
        series.append([ds, round(sa / wa, 1), round(sd / wd, 1) if wd else None])
    if not series:
        return None
    avg = {s[0]: s for s in series}
    last = series[-1]
    ref = lambda n: avg.get(ago(n)) or series[max(0, len(series) - 1 - n)]
    net = lambda s: round(s[1] - s[2], 1) if s[2] is not None else None
    # pollsters
    by = defaultdict(list)
    for p in ps:
        by[p["_k"]].append(p)
    pollsters = []
    for k, lst in by.items():
        lst.sort(key=lambda p: p["end"])
        lp = lst[-1]
        recent = [p for p in lst if p["end"] >= ago(180) and p["dis"] is not None and p["end"] in avg and avg[p["end"]][2] is not None]
        house = round(sum((p["app"] - p["dis"]) - (avg[p["end"]][1] - avg[p["end"]][2]) for p in recent) / len(recent), 1) if len(recent) >= 2 else None
        pollsters.append({"p": lp["pollster"], "n": len(lst), "d": lp["end"], "a": lp["app"], "x": lp["dis"], "pop": lp.get("pop", ""),
                          "s": lp.get("n", 0), "u": lp.get("url", ""), "h": house})
    pollsters.sort(key=lambda x: x["d"], reverse=True)
    pops = {}
    for pop in ("A", "RV", "LV"):
        r = [p for p in ps if p.get("pop") == pop and p["end"] >= ago(30) and p["dis"] is not None]
        if len(r) >= 2:
            pops[pop] = {"n": len(r), "a": round(sum(p["app"] for p in r) / len(r), 1), "x": round(sum(p["dis"] for p in r) / len(r), 1)}
    hi = max(series, key=lambda s: s[1])
    lo = min(series, key=lambda s: s[1])
    month = defaultdict(list)
    for s in series:
        month[s[0][:7]].append(s)
    monthly = [{"m": m, "a": round(sum(x[1] for x in v) / len(v), 1), "x": round(sum(x[2] for x in v if x[2] is not None) / max(1, sum(1 for x in v if x[2] is not None)), 1)}
               for m, v in sorted(month.items())]
    # most recent polls for the chart dots (last 240 days) and the table
    recent = [{"d": p["end"], "p": p["pollster"], "a": p["app"], "x": p["dis"], "n": p.get("n", 0), "pop": p.get("pop", ""), "u": p.get("url", "")}
              for p in ps if p["end"] >= ago(400)]
    return {"avg": {"a": last[1], "x": last[2], "net": net(last), "d7": round(last[1] - ref(7)[1], 1), "d30": round(last[1] - ref(30)[1], 1),
                    "net7": round(net(last) - net(ref(7)), 1) if net(last) is not None and net(ref(7)) is not None else None,
                    "net30": round(net(last) - net(ref(30)), 1) if net(last) is not None and net(ref(30)) is not None else None,
                    "first": series[0][1], "first_d": series[0][0]},
            "series": series, "polls": recent, "pollsters": pollsters[:60], "pops": pops, "monthly": monthly,
            "hi": {"d": hi[0], "a": hi[1]}, "lo": {"d": lo[0], "a": lo[1]},
            "counts": {"polls": len(ps), "pollsters": len(by), "last14": sum(1 for p in ps if p["end"] >= ago(14)),
                       "votehub": d.get("votehub", 0), "wikipedia": d.get("wikipedia", 0)}}


# ---------------------------------------------------------------- media
def media(news):
    w30 = [r for r in news if r["created_at"] >= ago(30)]
    is_t = lambda r: "trump" in fold(r["text"])
    rss = [r for r in w30 if r["platform"] == "Media"]
    tr = [r for r in w30 if is_t(r)]
    days = defaultdict(lambda: Counter())
    for r in [r for r in news if r["created_at"] >= ago(90) and is_t(r)]:
        c = days[day(r["created_at"])]
        c["n"] += 1
        if r.get("lean"):
            c[LEAN_GROUP[r["lean"]]] += 1
        c[r["tono"]] += 1
    daily = [{"d": d, **dict(c)} for d, c in sorted(days.items())]
    outlets = defaultdict(lambda: Counter())
    for r in rss:
        o = outlets[r["outlet"]]
        o["all"] += 1
        if is_t(r):
            o["t"] += 1
            o[r["tono"]] += 1
    lean_of = {f["name"]: f["lean"] for f in CONFIG["rss"]}
    out_rows = sorted([{"o": k, "lean": lean_of.get(k, ""), "all": v["all"], "t": v["t"], "share": pct(v["t"], v["all"]),
                        "pos": pct(v["POS"], v["t"]), "neg": pct(v["NEG"], v["t"])} for k, v in outlets.items()], key=lambda x: -x["t"])
    lean = {}
    for g in ("Left", "Center", "Right"):
        rs = [r for r in rss if LEAN_GROUP.get(r.get("lean", ""), "") == g]
        t = [r for r in rs if is_t(r)]
        lean[g] = {"all": len(rs), "t": len(t), "share": pct(len(t), len(rs)), "pos": pct(sum(r["tono"] == "POS" for r in t), len(t)),
                   "neg": pct(sum(r["tono"] == "NEG" for r in t), len(t)),
                   "top": [x["w"] for x in cloud(t, 8, "title")]}
    # topics: share of Trump coverage, last 7 days vs previous 21
    tp = []
    weeks = [ago(7 * i) for i in range(12, -1, -1)]
    for k in TOPICS:
        rs = [r for r in tr if k in r["_top"]]
        a7 = sum(r["created_at"] >= ago(7) for r in rs)
        b21 = len(rs) - a7
        n7 = sum(r["created_at"] >= ago(7) for r in tr) or 1
        n21 = (len(tr) - n7) or 1
        wk = []
        allt = [r for r in news if is_t(r) and k in r["_top"]]
        for i in range(len(weeks) - 1):
            wk.append(sum(weeks[i] <= day(r["created_at"]) < weeks[i + 1] for r in allt))
        tp.append({"k": k, "n": len(rs), "share": pct(len(rs), len(tr)), "s7": pct(a7, n7), "s21": pct(b21, n21) if n21 >= 50 else None,
                   "neg": pct(sum(r["tono"] == "NEG" for r in rs), len(rs)), "pos": pct(sum(r["tono"] == "POS" for r in rs), len(rs)), "wk": wk,
                   "lean": {g: sum(LEAN_GROUP.get(r.get("lean", ""), "") == g for r in rs) for g in ("Left", "Center", "Right")}})
    tp.sort(key=lambda x: -x["n"])
    seen, heads = set(), []
    for r in sorted(tr, key=lambda r: r["created_at"], reverse=True):
        key = re.sub(r"[^a-z]", "", fold(r["title"]))[:60]
        if key in seen:
            continue
        seen.add(key)
        heads.append({"t": r["title"], "u": r["url"], "o": r["outlet"], "l": LEAN_GROUP.get(r.get("lean", ""), ""), "d": r["created_at"][:16],
                      "s": r["tono"], "k": r["_top"][:2]})
    gn = Counter(r["outlet"] for r in w30 if r["platform"] == "Google News" and r["outlet"])
    return {"n30": len(tr), "n7": sum(r["created_at"] >= ago(7) for r in tr), "n7prev": sum(ago(14) <= r["created_at"] < ago(7) for r in tr),
            "share_rss": pct(sum(is_t(r) for r in rss), len(rss)), "tone": {k: pct(sum(r["tono"] == k for r in tr), len(tr)) for k in ("POS", "NEU", "NEG")},
            "daily": daily, "outlets": out_rows, "lean": lean, "topics": tp, "cloud": cloud(tr, 80, "title"),
            "gnews_outlets": [{"o": k, "n": v} for k, v in gn.most_common(15)], "headlines": heads[:80]}, heads


# ---------------------------------------------------------------- GDELT
def gdelt():
    g = load("gdelt.json") or {}
    out = {"errors": g.get("errors", {}), "fetched_at": g.get("fetched_at")}
    print("gdelt blocks:", {k: (list(v)[:4] if isinstance(v, dict) else type(v).__name__) for k, v in g.items()}, flush=True)

    def tl(block):
        try:
            return block["timeline"]
        except (KeyError, TypeError):
            return []

    def daily(series):
        acc = defaultdict(list)
        for p in series.get("data", []):
            acc[p["date"][:4] + "-" + p["date"][4:6] + "-" + p["date"][6:8]].append(float(p["value"]))
        return acc

    v = tl(g.get("vol"))
    if v:
        s = daily(v[0])
        out["vol"] = [[d, round(sum(x))] for d, x in sorted(s.items())]
    t = tl(g.get("tone"))
    if t:
        s = daily(t[0])
        out["tone"] = [[d, round(sum(x) / len(x), 2)] for d, x in sorted(s.items())]
    every = (g.get("all") or {}).get("articles") or []
    if every:
        cc, lc = Counter(a.get("sourcecountry") or "?" for a in every), Counter(a.get("language") or "?" for a in every)
        out["countries"] = [{"c": k, "v": pct(v, len(every))} for k, v in cc.most_common(20)]
        out["langs"] = [{"l": k, "v": pct(v, len(every))} for k, v in lc.most_common(12)]
        out["n24"] = len(every)
    arts = (g.get("arts") or {}).get("articles") or []
    seen, al = set(), []
    for a in arts:
        k = a.get("domain")
        if k in seen:
            continue
        seen.add(k)
        al.append({"t": a.get("title", "")[:180], "u": a.get("url"), "c": a.get("sourcecountry", ""), "l": a.get("language", ""),
                   "dom": k, "d": (a.get("seendate") or "")[:8]})
    out["arts"] = al[:40]
    return out


# ---------------------------------------------------------------- YouTube
def youtube(rows):
    com = [r for r in rows if r["kind"] == "comment" and r["created_at"] >= ago(30)]
    vids = [r for r in rows if r["kind"] == "video" and r["created_at"] >= ago(30)]
    n = len(com)
    emo = Counter(r["emo"] for r in com if r["emo"])
    daily = defaultdict(Counter)
    for r in com:
        c = daily[day(r["created_at"])]
        c["n"] += 1
        c[r["tono"]] += 1
    tp = []
    for k in TOPICS:
        rs = [r for r in com if k in r["_top"]]
        if len(rs) >= 3:
            tp.append({"k": k, "n": len(rs), "pos": pct(sum(r["tono"] == "POS" for r in rs), len(rs)), "neg": pct(sum(r["tono"] == "NEG" for r in rs), len(rs))})
    tp.sort(key=lambda x: -x["n"])
    vstats = defaultdict(Counter)
    for r in com:
        vstats[r["video_id"]][r["tono"]] += 1
    vl = []
    for v in sorted(vids, key=lambda v: -v.get("views", 0))[:16]:
        s = vstats[v["video_id"]]
        tot = sum(s.values())
        vl.append({"t": v["title"], "u": v["url"], "ch": v["channel"], "d": v["created_at"][:10], "views": v.get("views", 0),
                   "likes": v.get("likes", 0), "c": tot, "pos": pct(s["POS"], tot), "neg": pct(s["NEG"], tot)})
    chans = Counter()
    for v in vids:
        chans[v["channel"]] += v.get("views", 0)
    return {"n": n, "videos": len(vids), "views": sum(v.get("views", 0) for v in vids),
            "tone": {k: pct(sum(r["tono"] == k for r in com), n) for k in ("POS", "NEU", "NEG")},
            "emo": {k: pct(v, n) for k, v in emo.most_common()}, "tox": pct(sum(r["tox"] for r in com), n),
            "model": pct(sum(r["m"] == "model" for r in com), n),
            "daily": [{"d": d, **dict(c)} for d, c in sorted(daily.items())], "topics": tp, "cloud": cloud(com, 80),
            "cloud_pos": cloud([r for r in com if r["tono"] == "POS"], 30), "cloud_neg": cloud([r for r in com if r["tono"] == "NEG"], 30),
            "list": vl, "channels": [{"c": k, "v": v} for k, v in chans.most_common(10)]}


# ---------------------------------------------------------------- Truth Social
NAME_RX = re.compile(r"\b((?:[A-Z][a-zA-Z'\.]+|[A-Z]{2,})(?:\s+(?:[A-Z][a-zA-Z'\.]+|[A-Z]{2,})){0,2})")
NAME_STOP = set("""The A An I We It This That They He She You My Our In On At For And But Or If So As Thank Thanks Congratulations
Great Happy President Trump Donald MAGA America American Americans USA United States Country Nation Make Again Truth Social
God Bless Very Many Much All Now Today Just More Also Will Would Should Could Please DJT JD""".split())


def truth(rows):
    ps = [r for r in rows if r["kind"] == "truth" and r["created_at"] >= ago(90)]
    if not ps:
        return None
    perday = Counter(day(r["created_at"]) for r in ps)
    heat = [[0] * 24 for _ in range(7)]
    for r in ps:
        t = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")).astimezone(ET_TZ)
        heat[t.weekday()][t.hour] += 1
    p30 = [r for r in ps if r["created_at"] >= ago(30)]
    names = Counter()
    for r in p30:
        seen = set()
        for m in NAME_RX.findall(r["text"]):
            m = " ".join(w for w in m.split() if w not in NAME_STOP).strip(" .'")
            if len(m) > 2 and m not in seen and not m.isdigit():
                seen.add(m)
        names.update(seen)
    tp = Counter(k for r in p30 for k in r["_top"])
    top = sorted(p30, key=lambda r: -r.get("engagement", 0))[:12]
    fmt = lambda r: {"t": excerpt(r["text"], 320) or "[media post]", "u": r["url"], "d": r["created_at"][:16], "l": r.get("likes", 0),
                     "r": r.get("reblogs", 0), "c": r.get("replies", 0), "s": r["tono"], "m": r.get("media", 0)}
    nights = sum(1 for r in p30 if datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")).astimezone(ET_TZ).hour < 6)
    return {"n90": len(ps), "n30": len(p30), "n7": sum(r["created_at"] >= ago(7) for r in ps), "n7prev": sum(ago(14) <= r["created_at"] < ago(7) for r in ps),
            "max_day": max(perday.items(), key=lambda x: x[1]) if perday else None,
            "daily": [[d, perday.get(d, 0)] for d in (ago(i) for i in range(89, -1, -1))],
            "heat": heat, "night": pct(nights, len(p30)),
            "eng": round(sum(r.get("engagement", 0) for r in p30) / max(1, len(p30))),
            "media": pct(sum(1 for r in p30 if r.get("media")), len(p30)),
            "text_only": pct(sum(1 for r in p30 if r["text"] and not r.get("media")), len(p30)),
            "tone": {k: pct(sum(r["tono"] == k for r in p30), len(p30)) for k in ("POS", "NEU", "NEG")},
            "names": [{"w": k, "n": v} for k, v in names.most_common(24) if v >= 2],
            "topics": [{"k": k, "n": v, "s": pct(v, len(p30))} for k, v in tp.most_common()],
            "cloud": cloud(p30, 70), "top": [fmt(r) for r in top],
            "latest": [fmt(r) for r in sorted(ps, key=lambda r: r["created_at"], reverse=True)[:15]]}


# ---------------------------------------------------------------- Federal Register
EO_TOPICS = {"Trade & tariffs": ["tariff", "trade", "import", "duties", "reciprocal"], "Immigration & border": ["border", "immigra", "alien", "asylum", "invasion", "visa", "citizenship"],
             "Energy": ["energy", "oil", "coal", "nuclear", "drilling", "mineral"], "Government reform": ["federal workforce", "efficiency", "agency", "accountability", "regulat", "bureaucra", "employ"],
             "Defense & security": ["defense", "military", "armed forces", "security", "cartel", "terror", "national guard"],
             "Economy & finance": ["econom", "tax", "financ", "crypto", "digital asset", "bank", "price", "cost"], "Health": ["health", "drug", "medic", "pharma"],
             "Education & culture": ["education", "school", "college", "universit", "culture", "history", "monument", "gender", "dei", "discrimination"],
             "Foreign affairs": ["foreign", "international", "sanction", "israel", "iran", "ukraine", "china", "canada", "mexico", "venezuela"],
             "Tech & AI": ["artificial intelligence", "technology", "ai ", "cyber", "semiconductor"]}


def orders():
    d = load("fedreg.json") or {}
    docs = [x for x in d.get("docs", []) if x.get("d")]
    if not docs:
        return None
    month = defaultdict(Counter)
    for x in docs:
        month[x["d"][:7]][x["type"]] += 1
    eos = [x for x in docs if x["type"] == "executive_order"]
    tp = Counter()
    for x in eos:
        t = " " + fold(x["t"]) + " "
        for k, ws in EO_TOPICS.items():
            if any(w in t for w in ws):
                tp[k] += 1
    latest = sorted(docs, key=lambda x: x["d"], reverse=True)[:25]
    return {"total": {k: sum(1 for x in docs if x["type"] == k) for k in ("executive_order", "memorandum", "proclamation")},
            "d30": sum(1 for x in eos if x["d"] >= ago(30)), "d7": sum(1 for x in docs if x["d"] >= ago(7)),
            "monthly": [{"m": m, **dict(c)} for m, c in sorted(month.items())], "topics": [{"k": k, "n": v} for k, v in tp.most_common()],
            "latest": [{"t": x["t"], "d": x["d"], "type": x["type"], "eo": x.get("eo"), "u": x["u"]} for x in latest]}


# ---------------------------------------------------------------- economy, markets, attention, ads
def econ():
    d = load("fred.json") or {}
    out = {}
    for sid, s in d.get("series", {}).items():
        data = s["data"]
        if not data:
            continue
        last = data[-1]
        # weekly/daily series: thin to ~monthly points for sparkline
        dd = {}
        for dt, v in data:
            dd[dt[:7]] = (dt, v)
        pts = [[v[0], v[1]] for _, v in sorted(dd.items())]
        yoy = next((v for dt, v in reversed(data) if dt <= (datetime.fromisoformat(last[0]) - timedelta(days=365)).strftime("%Y-%m-%d")), None)
        inaug = next((v for dt, v in data if dt >= INAUG), None)
        out[sid] = {"name": s["name"], "d": last[0], "v": last[1], "yoy": round(100 * (last[1] / yoy - 1), 1) if yoy else None,
                    "inaug": inaug, "pts": pts[-30:]}
    return out


def attention():
    w = load("wiki.json") or {}
    wk = {}
    for name, views in w.get("views", {}).items():
        acc = defaultdict(int)
        for d, v in views.items():
            dt = datetime.strptime(d, "%Y%m%d")
            acc[(dt - timedelta(days=dt.weekday())).strftime("%Y-%m-%d")] += v
        wk[name] = sorted(acc.items())[-60:]
    t = load("trends.json") or {}

    def weekly(series):
        return {k: sorted(v.items()) for k, v in (series or {}).items()}
    return {"wiki": wk, "wiki_7d": {n: sum(v for d, v in views.items() if d >= ago(7).replace("-", "")) for n, views in w.get("views", {}).items()},
            "figures": weekly(t.get("figures")), "issues": weekly(t.get("issues")), "trump7d": weekly(t.get("trump7d")),
            "states": t.get("states", {}), "rising": t.get("rising", []), "top_queries": t.get("top_queries", []),
            "rising_topics": t.get("rising_topics", []), "trends_errors": t.get("errors", {}), "trends_at": t.get("fetched_at")}


def rng(x):
    if not x:
        return 0, 0
    lo = int(x.get("lower_bound") or 0)
    return lo, int(x.get("upper_bound") or lo)


def ads():
    d = load("ads.json.gz")
    if not d:
        return None
    camp = [w.lower() for w in CONFIG["meta_ads"]["campo_trump"]]
    opp = [w.lower() for w in CONFIG["meta_ads"].get("oposicion", [])]
    com = [w.lower() for w in CONFIG["meta_ads"].get("comercial", [])]

    def group(by):
        if any(c in by for c in camp):
            return "trump"
        if any(c in by for c in opp):
            return "opp"
        if any(re.search(r"\b" + re.escape(c), by) for c in com):
            return "merch"
        return "other"
    rows = d["ads"]
    pages = defaultdict(lambda: {"n": 0, "lo": 0, "hi": 0, "g": "other"})
    tot = {k: [0, 0, 0] for k in ("trump", "opp", "merch", "other")}
    reg, age, gen, plat = Counter(), Counter(), Counter(), Counter()
    samples = []
    for a in rows:
        nm = a.get("page_name") or "?"
        by = f"{nm} {a.get('bylines') or ''}".lower()
        gr = group(by)
        is_c = gr == "trump"
        s, i = rng(a.get("spend")), rng(a.get("impressions"))
        p = pages[nm]
        p["n"] += 1
        p["lo"] += s[0]
        p["hi"] += s[1]
        p["g"] = gr
        g = tot[gr]
        g[0] += 1
        g[1] += s[0]
        g[2] += s[1]
        mid = (i[0] + i[1]) / 2 or 1
        for r in a.get("delivery_by_region") or []:
            reg[r.get("region", "?")] += float(r.get("percentage") or 0) * mid
        for x in a.get("demographic_distribution") or []:
            age[x.get("age", "?")] += float(x.get("percentage") or 0) * mid
            gen[x.get("gender", "?")] += float(x.get("percentage") or 0) * mid
        plat.update(a.get("publisher_platforms") or [])
        if a.get("ad_creative_bodies"):
            samples.append((i[1], gr, nm, (a.get("ad_delivery_start_time") or "")[:10], a["ad_creative_bodies"][0], a["id"]))
    share = lambda c, n=12: [{"k": k, "v": round(100 * v / sum(c.values()), 1)} for k, v in c.most_common(n)] if sum(c.values()) else []
    samples.sort(reverse=True)
    seen_b = set()
    samples = [x for x in samples if not (x[4][:80] in seen_b or seen_b.add(x[4][:80]))]
    return {"n": len(rows), "since": d.get("since"), "camps": tot,
            "pages": sorted([{"p": k, **v} for k, v in pages.items()], key=lambda x: -x["hi"])[:16],
            "regions": share(reg, 51), "age": share(age), "gender": share(gen), "platforms": dict(plat.most_common()),
            "samples": [{"t": re.sub(r"\s+", " ", b)[:220], "p": nm, "c": c, "d": dd, "u": f"https://www.facebook.com/ads/library/?id={i}"}
                        for _, c, nm, dd, b, i in samples[:8]]}


# ---------------------------------------------------------------- alerts
def alerts(m):
    out = []
    ap = m.get("approval")
    if ap:
        a = ap["avg"]
        if abs(a["d7"]) >= 1:
            out.append({"lvl": "high" if abs(a["d7"]) >= 2 else "med", "i": "▲" if a["d7"] > 0 else "▼",
                        "t": f"Approval {'up' if a['d7'] > 0 else 'down'} {abs(a['d7']):.1f} pts in 7 days (now {a['a']:.1f}%)", "k": "Polls"})
        if ap["lo"]["d"] >= ago(10):
            out.append({"lvl": "high", "i": "▼", "t": f"Approval average at its lowest of the term: {ap['lo']['a']:.1f}%", "k": "Polls"})
        if ap["hi"]["d"] >= ago(10) and ap["hi"]["d"] > INAUG:
            out.append({"lvl": "med", "i": "▲", "t": f"Approval average at its highest since {ap['avg']['first_d'][:4]}: {ap['hi']['a']:.1f}%", "k": "Polls"})
    md = m.get("media")
    if md:
        dl = md["daily"]
        if len(dl) >= 21:
            base = [x["n"] for x in dl[-29:-1]]
            mu = sum(base) / len(base)
            sd = (sum((x - mu) ** 2 for x in base) / len(base)) ** 0.5 or 1
            for x in dl[-3:]:
                if (x["n"] - mu) / sd >= 2:
                    out.append({"lvl": "med", "i": "◆", "t": f"Coverage spike on {x['d']}: {x['n']} Trump stories vs. {mu:.0f}/day average", "k": "Media"})
        old = sum(1 for x in dl if x["d"] < ago(7))
        for t in md["topics"][:10]:
            if old >= 150 and t["s21"] is not None and t["s7"] >= 4 and t["s7"] >= 1.7 * max(t["s21"], 1):
                out.append({"lvl": "med", "i": "↑", "t": f"“{t['k']}” surging: {t['s7']:.0f}% of Trump coverage this week vs. {t['s21']:.0f}% before", "k": "Topics"})
            if t["n"] >= 25 and t["neg"] >= 45:
                out.append({"lvl": "low", "i": "!", "t": f"Negative framing on “{t['k']}”: {t['neg']:.0f}% of headlines", "k": "Tone"})
    tr = m.get("truth")
    if tr and tr["n7prev"]:
        ch = tr["n7"] / tr["n7prev"] - 1
        if abs(ch) >= 0.35:
            out.append({"lvl": "low", "i": "✎", "t": f"Truth Social output {'up' if ch > 0 else 'down'} {abs(ch) * 100:.0f}% week over week ({tr['n7']} posts)", "k": "Truth Social"})
    yt = m.get("youtube")
    if yt and yt["n"] >= 200 and yt["tone"]["NEG"] >= 45:
        out.append({"lvl": "med", "i": "!", "t": f"YouTube comments lean negative: {yt['tone']['NEG']:.0f}% negative vs. {yt['tone']['POS']:.0f}% positive", "k": "Public voice"})
    for e in (m.get("markets") or {}).get("events", [])[:10]:
        for mk in e["m"][:2]:
            if abs(mk["ch"]) >= 6:
                out.append({"lvl": "med", "i": "▲" if mk["ch"] > 0 else "▼", "t": f"Market move: “{e['t']}” {('— ' + mk['q']) if mk['q'] and mk['q'] != e['t'] else ''} {mk['ch']:+.0f} pts in 24h (now {mk['p']:.0f}%)", "k": "Markets"})
    at = m.get("attention") or {}
    t7 = (at.get("trump7d") or {}).get("Trump") or []
    if len(t7) > 30:
        vals = [v for _, v in t7]
        if vals[-1] >= 80 and sum(vals[:-24]) / max(1, len(vals) - 24) < 50:
            out.append({"lvl": "med", "i": "◆", "t": "Google searches for “Trump” at a 7-day peak right now", "k": "Search"})
    od = m.get("orders")
    if od and od["d7"] >= 5:
        out.append({"lvl": "low", "i": "§", "t": f"{od['d7']} presidential documents signed in the last 7 days", "k": "Executive"})
    rank = {"high": 0, "med": 1, "low": 2}
    return sorted(out, key=lambda a: rank[a["lvl"]])[:14]


# ---------------------------------------------------------------- main
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [r for r in items() if r.get("text") or r["kind"] in ("truth", "video")]
    for r in rows:
        r["text"] = r.get("text") or ""
        r["_top"] = topics_of(r["text"])
    nlp_label(rows)
    status = load("status.json", {})
    news = [r for r in rows if r["kind"] == "news"]
    m = {"updated_at": NOW.strftime("%Y-%m-%dT%H:%MZ"), "perfil": CONFIG["perfil"], "status": status}
    m["approval"] = approval()
    m["media"], heads = media(news) if news else (None, [])
    m["gdelt"] = gdelt()
    m["youtube"] = youtube(rows)
    m["truth"] = truth(rows)
    m["orders"] = orders()
    m["markets"] = load("markets.json")
    m["econ"] = econ()
    m["attention"] = attention()
    m["ads"] = ads()
    m["alerts"] = alerts(m)
    m["totals"] = {"news": len(news), "comments": sum(r["kind"] == "comment" for r in rows), "truth": sum(r["kind"] == "truth" for r in rows),
                   "videos": sum(r["kind"] == "video" for r in rows), "polls": (m["approval"] or {}).get("counts", {}).get("polls", 0)}
    (OUT / "monitor.json").write_text(json.dumps(m, ensure_ascii=False, separators=(",", ":")), encoding="utf8")
    # drill-down texts: headlines, anonymised comment excerpts with link, and his own posts
    com = sorted([r for r in rows if r["kind"] == "comment" and r["created_at"] >= ago(30)], key=lambda r: -r.get("engagement", 0))[:1500]
    tx = {"news": [{"t": h["t"], "u": h["u"], "o": h["o"], "l": h["l"], "d": h["d"], "s": h["s"]} for h in heads[:1500]],
          "comments": [{"t": excerpt(r["text"]), "u": r["url"], "d": r["created_at"][:10], "s": r["tono"], "e": r.get("engagement", 0), "v": r.get("video_title", "")[:90]} for r in com],
          "truth": [{"t": excerpt(r["text"], 500), "u": r["url"], "d": r["created_at"][:16], "s": r["tono"], "e": r.get("engagement", 0)}
                    for r in sorted([r for r in rows if r["kind"] == "truth" and r["created_at"] >= ago(30) and r["text"]], key=lambda r: r["created_at"], reverse=True)[:500]]}
    (OUT / "textos.json").write_text(json.dumps(tx, ensure_ascii=False, separators=(",", ":")), encoding="utf8")
    print(json.dumps({k: (v.get("ok"), v.get("items"), v.get("error", "")[:90]) for k, v in status.items()}, ensure_ascii=False, indent=1))
    print("alerts:", len(m["alerts"]), "approval:", (m["approval"] or {}).get("avg"))


if __name__ == "__main__":
    main()
