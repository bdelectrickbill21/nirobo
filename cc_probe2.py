#!/usr/bin/env python3
"""
Nirobo probe 2: the whole trip for a few pages.
  1. ask Common Crawl's lookup service for a few pages of a website
  2. download ONLY that page's small piece of the big file (a byte range, usually 10-30 KB)
  3. read the title, description and language out of it
  4. measure the time and bytes, and test the "next page of answers" feature
Results go to the log and to the job summary.
"""
import gzip
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

UA = "NiroboBot/0.1 (+https://nirobo.netlify.app) index-probe"
COLLINFO = os.environ.get("CC_COLLINFO", "https://index.commoncrawl.org/collinfo.json")
DATA = os.environ.get("CC_DATA", "https://data.commoncrawl.org/")
PER_SITE = int(os.environ.get("CC_PER_SITE", "3"))
PAUSE = float(os.environ.get("CC_PAUSE", "1.5"))
SITES = os.environ.get("CC_SITES", "prothomalo.com/*,*.edu.bd,bn.wikipedia.org/*").split(",")


def get(url, headers=None, timeout=90, retries=3):
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=dict({"User-Agent": UA}, **(headers or {})))
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            last = e.code
            if e.code in (500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(3 * (attempt + 1))        # the service is busy: wait and try again
                continue
            return e.code, b""
        except Exception as e:
            last = type(e).__name__
            time.sleep(2)
    return last, b""


def cdx(api, pattern, extra):
    q = urllib.parse.urlencode([("url", pattern), ("output", "json")] + extra)
    return get(api + "?" + q)


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


def main():
    st, body = get(COLLINFO)
    api = json.loads(body)[0]["cdx-api"]
    cid = json.loads(body)[0]["id"]
    lines = ["## Common Crawl probe 2: the whole trip for a few pages", "", "Crawl used: `%s`." % cid, "",
             "| Website | Page | Piece size | Time | Title found | Language |", "|---|---|---|---|---|---|"]
    paging, notes = [], []
    total_bytes = total_secs = n_ok = 0
    for pat in SITES:
        # does the "how many answer pages" feature work for this question?
        code, nb = cdx(api, pat, [("showNumPages", "true")])
        paging.append("`%s`: %s" % (pat, (nb.decode("utf-8", "replace")[:80] if code == 200 else "answered %s" % code)))
        time.sleep(PAUSE)
        code, body = cdx(api, pat, [("limit", str(PER_SITE * 4)), ("fl", "url,filename,offset,length,languages,status,mime"), ("filter", "=status:200"), ("filter", "=mime:text/html")])
        if code != 200:
            lines.append("| %s | - | - | - | question answered %s | - |" % (pat, code))
            continue
        got = 0
        for line in body.decode("utf-8", "replace").splitlines():
            if got >= PER_SITE:
                break
            try:
                r = json.loads(line)
                off, ln = int(r["offset"]), int(r["length"])
            except Exception:
                continue
            t0 = time.time()
            c2, raw = get(DATA + r["filename"], headers={"Range": "bytes=%d-%d" % (off, off + ln - 1)})
            dt = time.time() - t0
            if c2 not in (200, 206) or not raw:
                lines.append("| %s | %s | - | - | download answered %s | - |" % (pat, r["url"][:50], c2))
                continue
            try:
                s, hd, b = read_record(raw)
                title, desc = extract(decode(b, hd))
            except Exception as e:
                lines.append("| %s | %s | %d KB | - | could not read (%s) | - |" % (pat, r["url"][:50], len(raw) // 1024, type(e).__name__))
                continue
            got += 1; n_ok += 1; total_bytes += len(raw); total_secs += dt
            lines.append("| %s | %s | %.1f KB | %.2f s | %s | %s |" % (pat, r["url"][:60], len(raw) / 1024, dt, (title or "(none)").replace("|", "/")[:50], r.get("languages", "-")))
            time.sleep(0.3)
        time.sleep(PAUSE)
    lines += ["", "### Does paging work? (`showNumPages`)", ""] + ["- " + p for p in paging]
    if n_ok:
        lines += ["", "### Speed", "", "- Pages read: **%d**. Average piece: **%.1f KB**. Average time: **%.2f s** per page." % (n_ok, total_bytes / n_ok / 1024, total_secs / n_ok),
                  "- At that speed, 10,000 pages would take about **%.0f minutes** one at a time." % (10_000 * total_secs / n_ok / 60)]
    text = "\n".join(lines)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
