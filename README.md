# nirobo

**Nirobo** is a Bangladeshi search engine, built to understand how people here actually type: Bangla, English, and **Banglish** (like `jonmo nibondon` or `pasport renew`).

Live site: https://nirobo.netlify.app

## What it does

- **Bangla, Banglish and English search.** Words are matched by how they sound, so different spellings find the same page.
- **Nirobo guides.** Step-by-step answers for common services (NID, e-passport, birth registration, land records, land tax, TIN, driving license, police clearance), with the documents needed and a link to the official site.
- **Its own search index.** Nirobo crawls trusted Bangladeshi and international sites and searches its own collection of pages. No tracking, no accounts.

## How it works

1. `crawler.py` (a Scrapy spider) visits the websites listed in `SITES`. It follows each site's `robots.txt`, goes slowly, and saves a title, link and short description for each page.
2. A GitHub Action (`.github/workflows/crawl.yml`) runs the crawler every Sunday, or when started by hand, and saves the results to `data/index.json` and a summary to `data/report.txt`.
3. Netlify publishes the site again after every update. `index.html` and `search-core.js` search `data/index.json` directly in the browser.

## Files

| File | Purpose |
| --- | --- |
| `index.html` | The search page |
| `search-core.js` | Guides data and the Banglish matching code |
| `crawler.py` | The crawler |
| `data/index.json` | The search index (written by the crawler) |
| `data/report.txt` | How many pages each site gave, and why a site failed |
| `.github/workflows/crawl.yml` | Runs the crawler automatically |
| `functions/search.js`, `netlify.toml` | A Netlify function, currently unused |

## Adding a website to the index

Open `crawler.py` and add one line to `SITES`:

```python
"example.gov.bd": ("Example Name", ["government", "bangladesh"], "https://www.example.gov.bd/"),
```

Then run the **Crawl** workflow from the **Actions** tab and check `data/report.txt`. Some sites block crawlers or do not answer servers outside Bangladesh. The report says which ones.

## Please note

- The guides are general information written by hand. Fees, rules and websites change, so always check the official site before applying.
- Nirobo is not a government website.

---

**নিরবো** বাংলাদেশের জন্য বানানো একটি সার্চ ইঞ্জিন। বাংলা, English বা Banglish, যেভাবে খুশি লিখে খুঁজুন।
