#!/usr/bin/env python3
"""
Nirobo probe: how many Bangladeshi pages does Common Crawl (a free, open copy of the web) hold?

It only ASKS the public lookup service (index.commoncrawl.org) for page lists. It downloads no pages and
visits no news sites. One question per website, with a pause between questions (be polite).
Output: a table printed in the log and saved as the job summary.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "NiroboBot/0.1 (+https://nirobo.netlify.app) index-probe"
COLLINFO = os.environ.get("CC_COLLINFO", "https://index.commoncrawl.org/collinfo.json")
LIMIT = int(os.environ.get("CC_LIMIT", "1000"))
PAUSE = float(os.environ.get("CC_PAUSE", "2"))
PATTERNS = ["*.gov.bd", "*.edu.bd", "*.ac.bd", "*.org.bd", "*.com.bd", "*.net.bd", "*.mil.bd",
            "prothomalo.com/*", "thedailystar.net/*", "bdnews24.com/*", "kalerkantho.com/*", "samakal.com/*",
            "jagonews24.com/*", "newagebd.net/*", "jugantor.com/*", "tbsnews.net/*", "dhakatribune.com/*",
            "ittefaq.com.bd/*", "bn.wikipedia.org/*"]


def get(url, timeout=90):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def probe(api, pattern):
    q = urllib.parse.urlencode([("url", pattern), ("output", "json"), ("limit", LIMIT), ("fl", "url,status,mime,languages"),
                                ("filter", "=status:200"), ("filter", "=mime:text/html")])
    try:
        body = get(api + "?" + q)
    except urllib.error.HTTPError as e:
        return {"error": "answered %d" % e.code}
    except Exception as e:
        return {"error": type(e).__name__}
    urls, bn, en, hosts = set(), 0, 0, set()
    for line in body.splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        u = r.get("url", "")
        if not u or u in urls:
            continue
        urls.add(u)
        hosts.add(urllib.parse.urlsplit(u).netloc.lower())
        langs = r.get("languages", "")
        bn += "ben" in langs
        en += "eng" in langs
    return {"n": len(urls), "bn": bn, "en": en, "hosts": len(hosts), "sample": sorted(urls)[:2]}


def main():
    crawls = json.loads(get(COLLINFO))
    latest = crawls[0]
    lines = ["## Common Crawl probe", "", "Crawl used: `%s` (the newest). Each question returns at most %d pages." % (latest.get("id"), LIMIT), "",
             "| Website | Pages found | Bangla | English | Sites | Example |", "|---|---|---|---|---|---|"]
    total = 0
    for p in PATTERNS:
        r = probe(latest["cdx-api"], p)
        if "error" in r:
            lines.append("| %s | - | - | - | - | %s |" % (p, r["error"]))
        else:
            total += r["n"]
            lines.append("| %s | %d%s | %d | %d | %d | %s |" % (p, r["n"], "+" if r["n"] >= LIMIT else "", r["bn"], r["en"], r["hosts"], (r["sample"] or ["-"])[0]))
        time.sleep(PAUSE)
    lines += ["", "Pages counted in this test: **%d** ('+' means there are more than the limit)." % total]
    text = "\n".join(lines)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
