"""
Nirobo crawler: visits trusted websites and saves each page's title,
link and short description into data/index.json (Nirobo's own search index).

Run it with:   scrapy runspider crawler.py
"""
import datetime
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
    "eporcha.gov.bd": ("e-Porcha", ["government", "land", "bangladesh"], "https://eporcha.gov.bd/"),
    "ldtax.gov.bd": ("Land Development Tax", ["government", "land", "tax", "bangladesh"], "https://ldtax.gov.bd/"),
    "etaxnbr.gov.bd": ("NBR e-TIN", ["government", "tax", "bangladesh"], "https://etaxnbr.gov.bd/"),
    "bsp.brta.gov.bd": ("BRTA", ["government", "driving", "bangladesh"], "https://bsp.brta.gov.bd/"),
    # News (Bangladesh)
    "thedailystar.net": ("The Daily Star", ["news", "bangladesh"], "https://www.thedailystar.net/"),
    "prothomalo.com": ("Prothom Alo", ["news", "bangla", "bangladesh"], "https://www.prothomalo.com/"),
    "dhakatribune.com": ("Dhaka Tribune", ["news", "bangladesh"], "https://www.dhakatribune.com/"),
    "bdnews24.com": ("bdnews24", ["news", "bangladesh"], "https://bdnews24.com/"),
    # Education, health, jobs
    "ugc.gov.bd": ("UGC Bangladesh", ["education", "bangladesh"], "https://www.ugc.gov.bd/"),
    "educationboard.gov.bd": ("Education Boards", ["education", "results", "bangladesh"], "https://www.educationboard.gov.bd/"),
    "du.ac.bd": ("University of Dhaka", ["education", "bangladesh"], "https://www.du.ac.bd/"),
    "buet.ac.bd": ("BUET", ["education", "bangladesh"], "https://www.buet.ac.bd/"),
    "dghs.gov.bd": ("DGHS", ["health", "bangladesh"], "https://dghs.gov.bd/"),
    "bdjobs.com": ("Bdjobs", ["jobs", "bangladesh"], "https://www.bdjobs.com/"),
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
        # Save everything to data/index.json
        "FEEDS": {"data/index.json": {"format": "json", "encoding": "utf8", "overwrite": True, "indent": 1}},
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.counts = {}
        self.seen = set()
        self.desc_seen = {}
        self.fail = {}
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
            yield {
                "title": title,
                "url": response.url,
                "description": description,
                "source": name,
                "tags": tags,
                "lang": "bn" if BANGLA.search(title + description) else "en",
                "crawled": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
            }

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
        with open("data/report.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def allowed_domains_list():
    return list(SITES)
