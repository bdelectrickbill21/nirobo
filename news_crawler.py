#!/usr/bin/env python3
"""
Nirobo NewsHub crawler.

Reads PUBLIC news feeds (RSS / Atom) and news sitemaps of the sites listed in
data/news_sources.json, keeps stories published in the last 48 hours, groups
the same story reported by different sites, and writes news.json for the NewsHub page.

It is polite: it obeys robots.txt, says who it is, goes slowly, and uses only
Python's standard library (nothing to install).

Run:  python news_crawler.py
Settings (optional environment variables):
  NIROBO_NEWS_SOURCES  path to the sources file   (default data/news_sources.json)
  NIROBO_NEWS_OUT      folder for the output      (default out)
  NIROBO_NEWS_PREV     path to the previous news.json (keeps stories of a site that failed this time)
  NIROBO_NEWS_MAX_AGE  hours to keep a story      (default 48)
"""
import datetime
import gzip
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
import urllib.robotparser
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser

UA = "NiroboBot/0.1 (+https://nirobo.netlify.app)"
MAX_AGE_H = float(os.environ.get("NIROBO_NEWS_MAX_AGE", "48"))
SOURCES = os.environ.get("NIROBO_NEWS_SOURCES", "data/news_sources.json")
OUT = os.environ.get("NIROBO_NEWS_OUT", "out")
PREV = os.environ.get("NIROBO_NEWS_PREV", "")
PER_SITE = 60          # newest stories kept per site
MAX_ITEMS = 500        # stories written to news.json
TRUST = {"official": 1.15, "major": 1.0, "other": 0.9, "community": 0.7}
COMMON_FEEDS = ["/feed", "/feed/", "/rss", "/rss.xml", "/feed.xml", "/atom.xml", "/rss/feed", "/feeds/posts/default?alt=rss"]
BAD_WORDS = re.compile("|".join(map(re.escape, [
    "casino", "sportsbook", "betting", "bet365", "jackpot", "poker", "porn", "xxx", "nude", "escort",
    "জুয়া", "ক্যাসিনো", "বেটিং", "পর্ন"])), re.I)
STOP = set("""the and for with from that this are was has have will after over into says say new more about than
 its his her their they them been were not but you your our out who what when how why can may also just
 এর ও এবং থেকে জন্য করে হয় হবে না কী কি এই সেই একটি এক আর তার তাদের নিয়ে পর ক্ষেত্রে করেছেন বলেছেন করা করতে হয়েছে হচ্ছে""".split())


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


# ------------------------------------------------------------------ fetching
def fetch(url, timeout=15, maxbytes=4_000_000):
    """Returns (status, bytes). Raises on network errors."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*", "Accept-Encoding": "gzip"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read(maxbytes + 1)
            if r.headers.get("Content-Encoding", "").lower() == "gzip" or data[:2] == b"\x1f\x8b":
                data = gzip.decompress(data)
            return r.status, data[:maxbytes]
    except urllib.error.HTTPError as e:
        return e.code, b""


class Robots:
    """robots.txt of one site: may we fetch this URL, and which sitemaps does it list?"""
    def __init__(self, base):
        self.rp = urllib.robotparser.RobotFileParser()
        self.allow_all = True
        self.sitemaps = []
        try:
            status, data = fetch(urllib.parse.urljoin(base, "/robots.txt"), timeout=10)
        except Exception:
            return
        if status >= 500:          # server trouble: be careful and do not crawl
            self.allow_all = False
            self.rp.parse(["User-agent: *", "Disallow: /"])
            return
        if status == 200:
            lines = data.decode("utf-8", "replace").splitlines()
            self.rp.parse(lines)
            self.allow_all = False
            self.sitemaps = [l.split(":", 1)[1].strip() for l in lines if l.lower().startswith("sitemap:")]

    def can(self, url):
        return True if self.allow_all else self.rp.can_fetch(UA, url)


class LinkFinder(HTMLParser):
    """Finds <link rel="alternate" type="application/rss+xml" href="..."> in a page."""
    def __init__(self):
        super().__init__()
        self.feeds = []

    def handle_starttag(self, tag, attrs):
        if tag != "link":
            return
        a = {k.lower(): (v or "") for k, v in attrs}
        if "alternate" in a.get("rel", "").lower() and re.search(r"(rss|atom)\+xml", a.get("type", ""), re.I) and a.get("href"):
            self.feeds.append(a["href"])


# ------------------------------------------------------------------ parsing
def clean(text, limit=220):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def parse_date(s, tz="+06:00"):
    s = (s or "").strip()
    if not s:
        return None
    d = None
    try:
        d = parsedate_to_datetime(s)
    except Exception:
        pass
    if d is None:
        try:
            d = datetime.datetime.fromisoformat(s.replace("Z", "+00:00").replace(" ", "T", 1) if re.match(r"\d{4}-\d\d-\d\d \d", s) else s.replace("Z", "+00:00"))
        except Exception:
            return None
    if d.tzinfo is None:           # no time zone written: use the site's (Bangladesh by default)
        m = re.match(r"([+-])(\d\d):?(\d\d)", tz)
        off = datetime.timedelta(hours=int(m.group(2)), minutes=int(m.group(3))) * (1 if m.group(1) == "+" else -1) if m else datetime.timedelta(hours=6)
        d = d.replace(tzinfo=datetime.timezone(off))
    return d.astimezone(datetime.timezone.utc)


def text_of(el, *names):
    for n in names:
        found = el.find("{*}" + n)
        if found is not None and (found.text or "").strip():
            return found.text.strip()
    return ""


def parse_feed(data, tz="+06:00"):
    """RSS 2.0, RSS 1.0 and Atom -> list of dicts."""
    root = ET.fromstring(data)
    items = []
    for it in [e for e in root.iter() if isinstance(e.tag, str) and e.tag.rsplit("}", 1)[-1] in ("item", "entry")]:
        link = text_of(it, "link")
        if not link:                                    # Atom: <link href="..." rel="alternate"/>
            for l in it.findall("{*}link"):
                if l.get("href") and l.get("rel", "alternate") == "alternate":
                    link = l.get("href")
                    break
        if not link:
            g = it.find("{*}guid")
            if g is not None and (g.text or "").startswith("http"):
                link = g.text.strip()
        desc = text_of(it, "description", "summary", "encoded", "content")
        items.append({"title": clean(text_of(it, "title"), 160), "url": link.strip(), "desc": clean(desc),
                      "pub": parse_date(text_of(it, "pubDate", "published", "updated", "date"), tz)})
    return items


def parse_sitemap(data, tz="+06:00"):
    """Returns ('index', [urls]) or ('urls', [items])."""
    root = ET.fromstring(data)
    if root.tag.endswith("sitemapindex"):
        return "index", [(s.findtext("{*}loc") or "").strip() for s in root.findall("{*}sitemap")]
    items = []
    for u in root.findall("{*}url"):
        news = u.find("{*}news")
        title = pub = ""
        if news is not None:
            title = (news.findtext("{*}title") or "").strip()
            pub = (news.findtext("{*}publication_date") or "").strip()
        pub = pub or (u.findtext("{*}lastmod") or "").strip()
        items.append({"title": clean(title, 160), "url": (u.findtext("{*}loc") or "").strip(), "desc": "", "pub": parse_date(pub, tz)})
    return "urls", items


# ------------------------------------------------------------------ one site
def crawl_site(src):
    """Returns (items, note). Never raises."""
    base = src["url"]
    name = src["name"]
    tz = src.get("tz", "+06:00")
    note = ""
    try:
        rb = Robots(base)
        feeds = list(src.get("feeds", []))
        if not feeds:
            if rb.can(base):
                try:
                    status, page = fetch(base)
                    if status == 200:
                        lf = LinkFinder()
                        lf.feed(page.decode("utf-8", "replace"))
                        feeds += [urllib.parse.urljoin(base, h) for h in lf.feeds]
                    else:
                        note = "homepage answered %d" % status
                except Exception as e:
                    note = "homepage: " + type(e).__name__
            feeds += [urllib.parse.urljoin(base, p) for p in COMMON_FEEDS]
        seen, got, used = set(), [], []
        for fu in feeds:
            if fu in seen or len(used) >= 2 or len(seen) >= 8:
                continue
            seen.add(fu)
            if not rb.can(fu):
                note = "robots.txt does not allow " + fu
                continue
            try:
                status, data = fetch(fu)
                time.sleep(0.4)
                if status != 200 or not data.strip():
                    note = note or "%s answered %d" % (fu, status)
                    continue
                items = parse_feed(data, tz)
                if items:
                    got += items
                    used.append(fu)
            except ET.ParseError:
                note = "%s is not a valid feed" % fu
            except Exception as e:
                note = "%s: %s" % (fu, type(e).__name__)
        if not got:                                       # no feed: try the site's news sitemap
            for sm in (rb.sitemaps or [urllib.parse.urljoin(base, "/news-sitemap.xml")])[:4]:
                if not rb.can(sm):
                    continue
                try:
                    status, data = fetch(sm)
                    if status != 200:
                        continue
                    kind, vals = parse_sitemap(data, tz)
                    if kind == "index":
                        pick = [v for v in vals if re.search("news", v, re.I)] or vals[-2:]
                        for child in pick[:2]:
                            if rb.can(child):
                                st2, d2 = fetch(child)
                                if st2 == 200:
                                    got += parse_sitemap(d2, tz)[1]
                    else:
                        got += vals
                    if got:
                        used.append(sm)
                        break
                except Exception as e:
                    note = "%s: %s" % (sm, type(e).__name__)
        items = []
        limit_new, limit_old = now_utc() + datetime.timedelta(minutes=10), now_utc() - datetime.timedelta(hours=MAX_AGE_H)
        for it in got:
            if not it["url"].startswith(("http://", "https://")) or len(it["title"]) < 8 or not it["pub"]:
                continue
            if it["pub"] > limit_new or it["pub"] < limit_old:
                continue
            if BAD_WORDS.search(it["title"] + " " + it["desc"]):
                continue
            items.append(it)
        items.sort(key=lambda i: i["pub"], reverse=True)
        items = items[:PER_SITE]
        if used:
            note = "%d fresh stories via %s" % (len(items), used[0] + (" (+1 more feed)" if len(used) > 1 else ""))
        elif not note:
            note = "no feed or news sitemap found"
        return items, note
    except Exception as e:
        return [], "error: %s" % type(e).__name__


# ------------------------------------------------------------------ grouping and output
def norm_url(u):
    p = urllib.parse.urlsplit(u)
    host = p.netloc.lower()
    host = host[4:] if host.startswith("www.") else host
    q = "&".join(x for x in p.query.split("&") if x and not x.lower().startswith(("utm_", "fbclid", "gclid", "ref")))
    return host + p.path.rstrip("/") + ("?" + q if q else "")


def strip_tracking(u):
    p = urllib.parse.urlsplit(u)
    q = "&".join(x for x in p.query.split("&") if x and not x.lower().startswith(("utm_", "fbclid", "gclid")))
    return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, q, ""))


def tokens(title):
    out, cur = [], []
    for ch in title.lower():
        if unicodedata.category(ch)[0] in "LMN":
            cur.append(ch)
        elif cur:
            out.append("".join(cur)); cur = []
    if cur:
        out.append("".join(cur))
    return {t for t in out if t not in STOP and len(t) >= (3 if t.isascii() else 2)}


def group_stories(stories):
    """Union stories whose titles share most words. Returns list of clusters (lists of story indexes)."""
    toks = [tokens(s["t"]) for s in stories]
    parent = list(range(len(stories)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    index = {}
    for i, ts in enumerate(toks):
        for t in ts:
            index.setdefault(t, []).append(i)
    pairs = {}
    for t, ids in index.items():
        if len(ids) > 40:           # a word used everywhere says nothing
            continue
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                pairs[(ids[a], ids[b])] = pairs.get((ids[a], ids[b]), 0) + 1
    for (a, b), shared in pairs.items():
        union = len(toks[a] | toks[b])
        small = min(len(toks[a]), len(toks[b]))
        if union and shared / union >= 0.5 and (shared >= 3 or (small <= 4 and shared >= 2)):
            parent[find(a)] = find(b)
    groups = {}
    for i in range(len(stories)):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def build(sources, prev_items):
    results = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {s["name"]: ex.submit(crawl_site, s) for s in sources}
        for name, f in futures.items():
            results[name] = f.result()
    stories, report, seen = [], [], set()
    by_name = {s["name"]: s for s in sources}
    for name, (items, note) in results.items():
        src = by_name[name]
        trust = TRUST.get(src.get("tier", "other"), 0.9)
        host = urllib.parse.urlsplit(src["url"]).netloc.lower()
        host = host[4:] if host.startswith("www.") else host
        if not items:   # this site failed now: keep its earlier stories that are still fresh
            fresh_after = (now_utc() - datetime.timedelta(hours=MAX_AGE_H)).strftime("%Y-%m-%dT%H:%M:%SZ")
            kept = [p for p in prev_items if p.get("h") == host and p.get("p", "") >= fresh_after]
            for p in kept:
                key = norm_url(p["u"])
                if key not in seen:
                    seen.add(key); stories.append(dict(p, kept=True))
            if kept:
                note += " | kept %d earlier stories" % len(kept)
        for it in items:
            key = norm_url(it["url"])
            if key in seen:
                continue
            seen.add(key)
            stories.append({"t": it["title"], "u": strip_tracking(it["url"]), "d": it["desc"], "s": name, "h": host,
                            "p": it["pub"].strftime("%Y-%m-%dT%H:%M:%SZ"), "w": trust,
                            "l": "bn" if re.search("[\u0980-\u09FF]", it["title"]) else "en", "g": src.get("tag", "")})
        report.append("%s: %s" % (name, note))
    cutoff = (now_utc() - datetime.timedelta(hours=MAX_AGE_H)).strftime("%Y-%m-%dT%H:%M:%SZ")
    stories = [s for s in stories if s["p"] >= cutoff]
    out = []
    for grp in group_stories(stories):
        members = [stories[i] for i in grp]
        # headline = the earliest report from the most trusted site
        members.sort(key=lambda m: (-m["w"], m["p"]))
        head = dict(members[0])
        head.pop("kept", None)
        sites = []
        for m in members:
            if m["s"] not in sites:
                sites.append(m["s"])
        head["n"] = len(sites)
        head["a"] = [s for s in sites if s != head["s"]][:5]
        out.append(head)
    out.sort(key=lambda s: s["p"], reverse=True)
    return out[:MAX_ITEMS], report


def main():
    with open(SOURCES, encoding="utf-8") as f:
        sources = json.load(f)["sources"]
    prev = []
    if PREV and os.path.exists(PREV):
        try:
            with open(PREV, encoding="utf-8") as f:
                prev = json.load(f).get("items", [])
        except Exception:
            pass
    items, report = build(sources, prev)
    os.makedirs(OUT, exist_ok=True)
    stamp = now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(os.path.join(OUT, "news.json"), "w", encoding="utf-8") as f:
        json.dump({"v": 1, "updated": stamp, "items": items}, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(OUT, "news_report.txt"), "w", encoding="utf-8") as f:
        f.write("Updated %s UTC, %d stories\n" % (stamp, len(items)) + "\n".join(report) + "\n")
    print("\n".join(report))
    print("TOTAL: %d stories" % len(items))
    return 0 if items else 1


if __name__ == "__main__":
    sys.exit(main())
