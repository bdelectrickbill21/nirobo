#!/usr/bin/env python3
"""
Nirobo collector: builds Nirobo's search data from Common Crawl (a free, open copy of the web).

For each website group in PLAN it
  1. asks Common Crawl's lookup service which pages it holds (using its "page" feature),
  2. picks a fair mix (a few pages per website), skipping login, search and non-article pages,
  3. downloads only that page's small piece (a byte range, about 40 KB) and reads title, description and language,
  4. adds new pages to pages_cc.jsonl (pages already collected before are kept, never repeated).

It downloads no pages from the websites themselves. We keep only a title, a link and a short note, and link back to the real page.
Settings (environment variables): CC_COLLINFO, CC_DATA, CC_PREV (earlier pages_cc.jsonl), CC_OUT, CC_RUN_MAX, CC_WORKERS, CC_PLAN (json)
"""
import concurrent.futures as cf
import datetime
import gzip
import html
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

UA = "NiroboBot/0.1 (+https://nirobo.netlify.app) collector"
COLLINFO = os.environ.get("CC_COLLINFO", "https://index.commoncrawl.org/collinfo.json")
DATA = os.environ.get("CC_DATA", "https://data.commoncrawl.org/")
PREV = os.environ.get("CC_PREV", "")
OUT = os.environ.get("CC_OUT", "out")
RUN_MAX = int(os.environ.get("CC_RUN_MAX", "2500"))      # new pages added in ONE run
WORKERS = int(os.environ.get("CC_WORKERS", "3"))
BACKOFF = float(os.environ.get("CC_BACKOFF", "1"))      # 0 in tests
PAUSE = float(os.environ.get("CC_PAUSE", "1.5"))
PLAN = json.loads(os.environ["CC_PLAN"]) if os.environ.get("CC_PLAN") else [
    {"pat": "bn.wikipedia.org/*", "cap": 1500, "per_host": 1500, "tag": "wikipedia", "name": "Bangla Wikipedia"},
    {"pat": "*.edu.bd", "cap": 1200, "per_host": 40, "tag": "education"},
    {"pat": "*.ac.bd", "cap": 1200, "per_host": 100, "tag": "education"},
    {"pat": "*.org.bd", "cap": 800, "per_host": 40, "tag": "organization"},
    {"pat": "prothomalo.com/*", "cap": 500, "per_host": 500, "tag": "news", "name": "Prothom Alo"},
    {"pat": "*.mil.bd", "cap": 30, "per_host": 10, "tag": "government"},
]
SKIP = re.compile(r"login|signin|signup|register|logout|/cart|subscribe|/tag/|/search|/feed|/wp-json|/wp-admin|/print|/amp(/|$)|\.(pdf|jpe?g|png|gif|zip|docx?|xlsx?)(\?|$)", re.I)
BAD_TITLE = re.compile(r"^(404|403|500|error|not found|access denied|forbidden|just a moment|attention required|redirecting|untitled|home)\b|page not found|server error|invalid url|temporarily unavailable", re.I)
BAD_WORDS = re.compile("|".join(map(re.escape, ["casino", "sportsbook", "betting", "bet365", "jackpot", "poker", "porn", "xxx", "nude", "escort",
                                                  "জুয়া", "ক্যাসিনো", "বেটিং", "পর্ন"])), re.I)
BANGLA = re.compile("[\u0980-\u09FF]")


def get(url, headers=None, timeout=90, retries=6, wait=2):
    """Download with patient retries: the free services say "slow down" (503) or time out (504) now and then."""
    code = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=dict({"User-Agent": UA}, **(headers or {})))
        pause = min(60, wait * (2 ** attempt)) * BACKOFF
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            code = e.code
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                try:
                    pause = max(pause, min(60, float(e.headers.get("Retry-After", 0))) * BACKOFF)
                except (TypeError, ValueError):
                    pass
                time.sleep(pause)
                continue
            return e.code, b""
        except Exception as e:
            code = type(e).__name__
            if attempt < retries - 1:
                time.sleep(pause)
    return code, b""


def dechunk(b):
    out, i = b"", 0
    while True:
        j = b.find(b"\r\n", i)
        if j < 0:
            return out
        try:
            n = int(b[i:j].split(b";")[0], 16)
        except ValueError:
            return out + b[i:]
        if n == 0:
            return out
        out += b[j + 2:j + 2 + n]
        i = j + 2 + n + 2


def read_record(raw):
    """One WARC record (still gzipped) -> (http_status, headers dict, body bytes)."""
    rec = gzip.decompress(raw)
    _, _, rest = rec.partition(b"\r\n\r\n")           # skip the WARC header
    head, _, body = rest.partition(b"\r\n\r\n")        # HTTP header, then the page
    lines = head.decode("latin-1").split("\r\n")
    status = int(lines[0].split()[1]) if lines and len(lines[0].split()) > 1 else 0
    hd = {}
    for l in lines[1:]:
        if ":" in l:
            k, v = l.split(":", 1)
            hd[k.strip().lower()] = v.strip()
    if "chunked" in hd.get("transfer-encoding", "").lower():
        body = dechunk(body)
    if "gzip" in hd.get("content-encoding", "").lower():
        try:
            body = zlib.decompress(body, 16 + zlib.MAX_WBITS)
        except Exception:
            pass
    return status, hd, body


def decode(body, hd):
    m = re.search(r"charset=([\w-]+)", hd.get("content-type", ""), re.I) or re.search(rb"<meta[^>]+charset=[\"']?([\w-]+)", body[:3000], re.I)
    enc = (m.group(1).decode() if m and isinstance(m.group(1), bytes) else (m.group(1) if m else "utf-8"))
    try:
        return body.decode(enc, "replace")
    except LookupError:
        return body.decode("utf-8", "replace")


def clean(t, n=200):
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()
    return t[:n]


def extract(page):
    t = re.search(r"<title[^>]*>(.*?)</title>", page, re.I | re.S)
    d = re.search(r"<meta[^>]+(?:name=[\"']description[\"']|property=[\"']og:description[\"'])[^>]*content=[\"']([^\"']*)", page, re.I)
    if not d:
        d = re.search(r"<meta[^>]+content=[\"']([^\"']*)[\"'][^>]+(?:name=[\"']description[\"']|property=[\"']og:description[\"'])", page, re.I)
    return clean(t.group(1), 140) if t else "", clean(d.group(1), 200) if d else ""



def host_of(u):
    h = urllib.parse.urlsplit(u).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def norm(u):
    p = urllib.parse.urlsplit(u)
    return host_of(u) + urllib.parse.unquote(p.path).rstrip("/")


def wanted(url, pat):
    p = urllib.parse.urlsplit(url)
    if p.query or SKIP.search(url):
        return False
    path = urllib.parse.unquote(p.path)
    if "wikipedia.org" in p.netloc:
        return path.startswith("/wiki/") and ":" not in path[6:]       # real articles only, no Talk:/Special:/File: pages
    return len(path.strip("/")) > 0 or "wikipedia" in pat                 # not just the homepage


def candidates(api, plan, have, per_host_have):
    """Pick pages to read for one website group."""
    code, body = get(api + "?" + urllib.parse.urlencode({"url": plan["pat"], "output": "json", "showNumPages": "true"}), retries=7, wait=5)
    try:
        pages = int(json.loads(body)["pages"])
    except Exception:
        return [], "could not count pages (answered %s)" % code
    order = list(range(pages)); random.Random(plan["pat"]).shuffle(order)
    out, seen, hosts, ok_pages = [], set(), {}, 0
    for pg in order:
        time.sleep(PAUSE)
        q = urllib.parse.urlencode({"url": plan["pat"], "output": "json", "page": pg, "fl": "url,status,mime,languages,filename,offset,length"})
        code, body = get(api + "?" + q, timeout=180, retries=7, wait=5)
        if code != 200:
            continue
        ok_pages += 1
        for line in body.decode("utf-8", "replace").splitlines():
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("status") != "200" or "html" not in r.get("mime", "") or not wanted(r["url"], plan["pat"]):
                continue
            k = norm(r["url"])
            h = host_of(r["url"])
            if k in seen or k in have or hosts.get(h, 0) + per_host_have.get(h, 0) >= plan["per_host"]:
                continue
            seen.add(k); hosts[h] = hosts.get(h, 0) + 1
            out.append(r)
        if len(out) >= plan["cap"] * 2:
            break
    random.Random(1).shuffle(out)
    return out, "%d candidates; answer pages read %d of %d tried" % (len(out), ok_pages, min(pages, len(order)) if len(out) < plan["cap"] * 2 else ok_pages)


def read_page(r, plan, today, crawl_id):
    try:
        off, ln = int(r["offset"]), int(r["length"])
        code, raw = get(DATA + r["filename"], headers={"Range": "bytes=%d-%d" % (off, off + ln - 1)}, retries=6, wait=2)
        time.sleep(0.15)
        if code not in (200, 206) or not raw:
            return None, "download %s" % code
        status, hd, body = read_record(raw)
        if status != 200 or "html" not in hd.get("content-type", "html").lower():
            return None, "not a normal page"
        title, desc = extract(decode(body, hd))
    except Exception as e:
        return None, "unreadable (%s)" % type(e).__name__
    title = re.sub(r"\s*[|\-\u2013\u2014]\s*(\u09ac\u09be\u0982\u09b2\u09be\u09aa\u09bf\u09a1\u09bf\u09af\u09bc\u09be|\u0989\u0987\u0995\u09bf\u09aa\u09bf\u09a1\u09bf\u09af\u09bc\u09be).*$", "", title) if "wikipedia" in r["url"] else title
    if len(title) < 2 or BAD_TITLE.search(title):
        return None, "no useful title"
    if BAD_WORDS.search(title + " " + desc):
        return None, "banned words"
    h = host_of(r["url"])
    return {"title": title[:140], "url": r["url"], "description": desc, "source": plan.get("name") or h,
            "tags": [plan["tag"], "bangladesh"],
            "lang": "bn" if (BANGLA.search(title + desc) or "ben" in r.get("languages", "")) else "en",
            "crawled": today, "cc": crawl_id}, "ok"


SEPS = (" | ", " \u2013 ", " \u2014 ", " - ", " :: ")


def strip_suffixes(pages):
    """If the same ending (like "| Prothom Alo") closes 3 or more titles of one site, remove it from all of them."""
    cnt = {}
    for p in pages:
        for sep in SEPS:
            if sep in p["title"]:
                tail = p["title"].rsplit(sep, 1)[1].strip()
                if 2 <= len(tail) <= 40:
                    k = (host_of(p["url"]), sep, tail)
                    cnt[k] = cnt.get(k, 0) + 1
    for p in pages:
        for sep in SEPS:
            if sep in p["title"]:
                head, tail = p["title"].rsplit(sep, 1)
                if cnt.get((host_of(p["url"]), sep, tail.strip()), 0) >= 3 and head.strip():
                    p["title"] = head.strip()
                    break


def main():
    st, body = get(COLLINFO)
    latest = json.loads(body)[0]
    api, crawl_id = latest["cdx-api"], latest["id"]
    today = datetime.date.today().isoformat()
    old = []
    if PREV and os.path.exists(PREV):
        with open(PREV, encoding="utf-8") as f:
            old = [json.loads(l) for l in f if l.strip()]
    have = {norm(p["url"]) for p in old}
    per_host_have, per_tag_have = {}, {}
    for p in old:
        per_host_have[host_of(p["url"])] = per_host_have.get(host_of(p["url"]), 0) + 1
        per_tag_have[p["tags"][0]] = per_tag_have.get(p["tags"][0], 0) + 1
    new, report = [], ["Common Crawl collector, crawl %s" % crawl_id, "Earlier pages kept: %d" % len(old)]
    for plan in PLAN:
        room = min(plan["cap"] - sum(1 for p in old if p["url"] and plan["pat"].strip("*/").split("/")[0].lstrip(".") in host_of(p["url"])), RUN_MAX - len(new))
        if room <= 0:
            report.append("- %s: full (nothing to add)" % plan["pat"]); continue
        cands, note = candidates(api, dict(plan, cap=room), have, per_host_have)
        added, fails = 0, {}
        t0 = time.time()
        with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futs = []
            for r in cands[:room * 2]:
                futs.append(ex.submit(read_page, r, plan, today, crawl_id))
            for f in futs:
                rec, why = f.result()
                if rec and added < room and norm(rec["url"]) not in have:
                    have.add(norm(rec["url"])); new.append(rec); added += 1
                    per_host_have[host_of(rec["url"])] = per_host_have.get(host_of(rec["url"]), 0) + 1
                elif not rec:
                    fails[why] = fails.get(why, 0) + 1
        sample = [p["title"] for p in new[-added:][:2]] if added else []
        report.append("- %s: added %d (%s; %.0f s)%s" % (plan["pat"], added, note, time.time() - t0, (" | skipped: " + ", ".join("%d %s" % (v, k) for k, v in fails.items())) if fails else ""))
        for s in sample:
            report.append("    e.g. " + s)
    strip_suffixes(old + new)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "pages_cc.jsonl"), "w", encoding="utf-8") as f:
        for p in old + new:
            f.write(json.dumps(p, ensure_ascii=False, separators=(",", ":")) + "\n")
    report.append("TOTAL pages now: %d (new this run: %d)" % (len(old) + len(new), len(new)))
    text = "\n".join(report)
    with open(os.path.join(OUT, "cc_report.txt"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("## Common Crawl collector\n\n" + "\n".join(("- " + l.lstrip("- ")) if l.startswith("- ") else l for l in report) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
