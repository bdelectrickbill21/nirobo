"""
Nirobo crawler: visits trusted websites and saves each page's title,
link and short description into data/index.json (Nirobo's own search index).

Run it with:   scrapy runspider crawler.py
"""
import datetime
import json
import os
import re
from urllib.parse import urlsplit

import scrapy
from scrapy.http import TextResponse
from scrapy.linkextractors import LinkExtractor
from scrapy.spidermiddlewares.httperror import HttpError

# ---------------------------------------------------------------------------
# Websites to crawl. To add a site, add one line: domain -> (name, tags, start page)
# ---------------------------------------------------------------------------
SITES = {
    # Government services
    "bangladesh.gov.bd": ("National Portal", ["government", "bangladesh"], "https://bangladesh.gov.bd/"),
    "nidw.gov.bd": ("NID Wing", ["government", "nid", "bangladesh"], "https://nidw.gov.bd/"),
    "epassport.gov.bd": ("e-Passport", ["government", "passport", "bangladesh"], "https://www.epassport.gov.bd/"),
    "bdris.gov.bd": ("BDRIS", ["government", "birth-registration", "bangladesh"], "https://bdris.gov.bd/"),
    "eporcha.gov.bd": ("e-Porcha", ["government", "land", "bangladesh"], "https://www.eporcha.gov.bd/"),
    "ldtax.gov.bd": ("Land Development Tax", ["government", "land", "tax", "bangladesh"], "https://ldtax.gov.bd/"),
    "etaxnbr.gov.bd": ("NBR e-TIN", ["government", "tax", "bangladesh"], "https://etaxnbr.gov.bd/"),
    "bsp.brta.gov.bd": ("BRTA", ["government", "driving", "bangladesh"], "https://bsp.brta.gov.bd/"),
    # News (Bangladesh)
    "thedailystar.net": ("The Daily Star", ["news", "bangladesh"], "https://www.thedailystar.net/"),
    "prothomalo.com": ("Prothom Alo", ["news", "bangla", "bangladesh"], "https://www.prothomalo.com/"),
    "bdnews24.com": ("bdnews24", ["news", "bangladesh"], "https://bdnews24.com/"),
    # Education, health
    "ugc.gov.bd": ("UGC Bangladesh", ["education", "bangladesh"], "https://www.ugc.gov.bd/"),
    "educationboard.gov.bd": ("Education Boards", ["education", "results", "bangladesh"], "https://www.educationboard.gov.bd/"),
    "du.ac.bd": ("University of Dhaka", ["education", "bangladesh"], "https://www.du.ac.bd/"),
    "buet.ac.bd": ("BUET", ["education", "bangladesh"], "https://www.buet.ac.bd/"),
    "dghs.gov.bd": ("DGHS", ["health", "bangladesh"], "https://dghs.gov.bd/"),
    "nu.ac.bd": ("National University", ["education", "bangladesh"], "https://www.nu.ac.bd/"),
    "dshe.gov.bd": ("DSHE", ["education", "bangladesh"], "https://dshe.gov.bd/"),
    "dpe.gov.bd": ("DPE", ["education", "bangladesh"], "https://dpe.gov.bd/"),
    "bteb.gov.bd": ("BTEB", ["education", "bangladesh"], "https://bteb.gov.bd/"),
    "teachers.gov.bd": ("Teachers Portal", ["education", "bangladesh"], "https://www.teachers.gov.bd/"),
    "bb.org.bd": ("Bangladesh Bank", ["finance", "government", "bangladesh"], "https://www.bb.org.bd/"),
    # More news
    "tbsnews.net": ("The Business Standard", ["news", "business", "bangladesh"], "https://www.tbsnews.net/"),
    "newagebd.net": ("New Age", ["news", "bangladesh"], "https://www.newagebd.net/"),
    "jagonews24.com": ("Jagonews24", ["news", "bangla", "bangladesh"], "https://www.jagonews24.com/"),
    "kalerkantho.com": ("Kaler Kantho", ["news", "bangla", "bangladesh"], "https://www.kalerkantho.com/"),
    "samakal.com": ("Samakal", ["news", "bangla", "bangladesh"], "https://samakal.com/"),
    "jugantor.com": ("Jugantor", ["news", "bangla", "bangladesh"], "https://www.jugantor.com/"),
    # International
    "who.int": ("World Health Organization", ["health", "international"], "https://www.who.int/"),
    "un.org": ("United Nations", ["international"], "https://www.un.org/"),
    "bbc.com": ("BBC News", ["news", "international"], "https://www.bbc.com/news"),
}

MAX_PER_SITE = 25  # pages saved per site in one run (keeps the crawl fast and polite)
SKIP = [r"login", r"signin", r"signup", r"register", r"logout", r"/cart", r"subscribe",
        r"/tag/", r"/search", r"\?.*(page|sort|filter)=", r"#"]
BANGLA = re.compile(r"[\u0980-\u09FF]")


def site_for(host):
    for domain in SITES:
        if host == domain or host.endswith("." + domain):
            return domain
    return None


def normalize(url):
    """Same page, different link (www, http/https, trailing slash, #part) -> same key."""
    p = urlsplit(url)
    host = p.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host + p.path.rstrip("/") + ("?" + p.query if p.query else "")


def junk(text):
    t = text.lower()
    return t.startswith(("©", "copyright", "all rights")) or "all rights reserved" in t


def clean(text, limit):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


class NiroboCrawler(scrapy.Spider):
    name = "nirobo"
    start_urls = [v[2] for v in SITES.values()]
    allowed_domains = list(SITES)

    custom_settings = {
        # Be polite: follow robots.txt, go slowly, say who we are.
        "ROBOTSTXT_OBEY": True,
        "USER_AGENT": "NiroboBot/0.1 (+https://nirobo.netlify.app)",
        "DOWNLOAD_DELAY": 1,
        "CONCURRENT_REQUESTS": 16,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "AUTOTHROTTLE_ENABLED": True,
        "DOWNLOAD_TIMEOUT": 30,
        "RETRY_TIMES": 2,
        "RETRY_PRIORITY_ADJUST": 5,  # retry slow or failed pages first, so no site gets forgotten
        "DEPTH_LIMIT": 2,
        "CLOSESPIDER_PAGECOUNT": 1500,
        "LOG_LEVEL": "INFO",
        # Visit all sites evenly (breadth-first) instead of finishing one first.
        "DEPTH_PRIORITY": 1,
        "SCHEDULER_DISK_QUEUE": "scrapy.squeues.PickleFifoDiskQueue",
        "SCHEDULER_MEMORY_QUEUE": "scrapy.squeues.FifoMemoryQueue",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.counts = {}
        self.seen = set()
        self.desc_seen = {}
        self.fail = {}
        self.items = []
        self.old = []
        try:  # the previous index, so one bad run does not wipe pages we already had
            with open("data/index.json", encoding="utf-8") as f:
                self.old = json.load(f)
        except Exception:
            pass
        self.info = {}
        self.links = LinkExtractor(allow_domains=allowed_domains_list(), deny=SKIP, unique=True)

    async def start(self):  # used by Scrapy 2.13 and newer
        for request in self.start_requests():
            yield request

    def start_requests(self):
        for domain, (_, _, url) in SITES.items():
            yield scrapy.Request(url, callback=self.parse, errback=self.failed,
                                 meta={"site": domain}, dont_filter=True)

    def failed(self, failure):
        """Remember why a site's start page could not be opened (for the report)."""
        domain = failure.request.meta.get("site")
        if failure.check(HttpError):
            why = "website answered with error %d" % failure.value.response.status
        elif failure.type.__name__ == "IgnoreRequest":
            why = "blocked by the site's robots.txt (we obey it)"
        else:
            why = failure.type.__name__
        self.fail[domain] = why

    def parse(self, response):
        if not isinstance(response, TextResponse):
            return  # skip PDFs, images and other non-page files
        lang = (response.xpath("/html/@lang").get() or "").lower()
        site = response.meta.get("site")  # set only on each site's start page
        if site:
            self.info[site] = "status %s, ended at %s, page language '%s'" % (response.status, response.url, lang)
        if lang and not lang.startswith(("en", "bn")):
            return  # only keep English and Bangla pages

        domain = site_for(response.url.split("/")[2].lower())
        if not domain or self.counts.get(domain, 0) >= MAX_PER_SITE:
            return
        key = normalize(response.url)
        if key in self.seen:
            return  # already saved this page
        self.seen.add(key)

        title = (response.xpath('//meta[@property="og:title"]/@content').get()
                 or response.css("h1::text").get()
                 or response.css("title::text").get())
        meta = clean(response.xpath('//meta[@name="description"]/@content').get()
                     or response.xpath('//meta[@property="og:description"]/@content').get(), 300)
        used = self.desc_seen.setdefault(domain, set())
        description = ""
        if meta and not junk(meta) and meta not in used:
            description = meta  # good, page-specific description
        else:  # missing, junk, or the same text on every page of the site: use the page's own text
            for p in response.css("p::text").getall():
                p = clean(p, 300)
                if len(p) > 60 and not junk(p):
                    description = p
                    break
        if description:
            used.add(description)

        title = clean(title, 140)
        if site:
            self.info[site] += ", title '%s'" % title[:40]
        if len(title) > 3:
            name, tags, _ = SITES[domain]
            self.counts[domain] = self.counts.get(domain, 0) + 1
            self.items.append({
                "title": title,
                "url": response.url,
                "description": description,
                "source": name,
                "tags": tags,
                "lang": "bn" if BANGLA.search(title + description) else "en",
                "crawled": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
            })

        if self.counts.get(domain, 0) < MAX_PER_SITE:
            for link in self.links.extract_links(response)[:40]:
                yield response.follow(link.url, self.parse)

    def closed(self, reason):
        # Writes data/report.txt: how many pages each site gave, and why a site failed.
        lines = []
        for domain in SITES:
            line = "%s: %d pages" % (domain, self.counts.get(domain, 0))
            if domain in self.fail:
                line += "   <-- start page problem: " + self.fail[domain]
            elif self.counts.get(domain, 0) == 0:
                line += "   <-- start page: " + self.info.get(domain, "no answer before the crawl ended (site is slow or blocking us)")
            lines.append(line)
            self.logger.info("REPORT %s", line)
        os.makedirs("data", exist_ok=True)
        self.save_index()
        with open("data/report.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


    def save_index(self):
        """Write data/index.json. If a site gave far fewer pages than last time
        (it was slow or blocking us today), keep its old pages too."""
        merged = list(self.items)
        have = {normalize(i["url"]) for i in self.items}
        old_count = {}
        for page in self.old:
            d = site_for(urlsplit(page["url"]).netloc.lower())
            old_count[d] = old_count.get(d, 0) + 1
        for page in self.old:
            d = site_for(urlsplit(page["url"]).netloc.lower())
            if d and self.counts.get(d, 0) * 2 < old_count[d] and normalize(page["url"]) not in have:
                merged.append(page)
        with open("data/index.json", "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=1)
        self.logger.info("REPORT saved %d pages (%d from earlier runs)", len(merged), len(merged) - len(self.items))


def allowed_domains_list():
    return list(SITES)
