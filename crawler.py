"""
Nirobo crawler: visits trusted websites and saves each page's title,
link and short description into data/index.json (Nirobo's own search index).

Run it with:   scrapy runspider crawler.py
"""
import datetime
import re

import scrapy
from scrapy.http import TextResponse
from scrapy.linkextractors import LinkExtractor

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
        "DOWNLOAD_TIMEOUT": 20,
        "RETRY_TIMES": 1,
        "DEPTH_LIMIT": 2,
        "CLOSESPIDER_PAGECOUNT": 800,
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
        self.links = LinkExtractor(allow_domains=allowed_domains_list(), deny=SKIP, unique=True)

    def parse(self, response):
        if not isinstance(response, TextResponse):
            return  # skip PDFs, images and other non-page files

        domain = site_for(response.url.split("/")[2].lower())
        if not domain or self.counts.get(domain, 0) >= MAX_PER_SITE:
            return

        title = (response.xpath('//meta[@property="og:title"]/@content').get()
                 or response.css("h1::text").get()
                 or response.css("title::text").get())
        description = (response.xpath('//meta[@name="description"]/@content').get()
                       or response.xpath('//meta[@property="og:description"]/@content').get())
        if not description:
            for p in response.css("p::text").getall():
                if len(p.strip()) > 60:
                    description = p
                    break

        title, description = clean(title, 140), clean(description, 300)
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


def allowed_domains_list():
    return list(SITES)
