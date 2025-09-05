from datetime import datetime
import scrapy
from urllib.parse import urljoin, urlparse
import json
import os

class NiroboSpider(scrapy.Spider):
    name = 'nirobo'

    start_urls = [
        'https://example.com/',
        'https://edition.cnn.com/',
        'https://www.thedailystar.net/',
        'https://www.prothomalo.com/',
        'https://www.dhakatribune.com/',
        'https://www.bdnews24.com/',
        'https://www.bbc.com/',
        'https://www.nytimes.com/',
        'https://www.aljazeera.com/',
        'https://www.reuters.com/',
        'https://www.un.org/',
        'https://www.who.int/'
    ]

    allowed_domains = [
        'thedailystar.net',
        'prothomalo.com',
        'dhakatribune.com',
        'bdnews24.com',
        'bbc.com',
        'nytimes.com',
        'aljazeera.com',
        'reuters.com',
        'un.org',
        'who.int'
    ]

    visited_urls = set()

    def save_results(self, result):
    output_file = 'result.json'
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)

    data = []
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            data = []

    seen_urls = set()
    unique_data = []
    for item in data + [result]:
        if item['url'] not in seen_urls:
            unique_data.append(item)
            seen_urls.add(item['url'])

    print(f"Saving {len(unique_data)} total entries to result.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique_data, f, ensure_ascii=False, indent=2)

        # Define tags based on domain
        domain_tags = {
            'thedailystar.net': ['news', 'bangladesh'],
            'prothomalo.com': ['news', 'bangla'],
            'dhakatribune.com': ['news', 'bd'],
            'bdnews24.com': ['news', 'bd'],
            'bbc.com': ['news', 'global'],
            'nytimes.com': ['news', 'us'],
            'aljazeera.com': ['news', 'middle-east'],
            'reuters.com': ['news', 'finance'],
            'un.org': ['global', 'policy'],
            'who.int': ['health', 'global']
        }

        parsed = urlparse(current_url)
        root_domain = parsed.netloc.split('.')[-2] + '.' + parsed.netloc.split('.')[-1]
        tags = domain_tags.get(root_domain, ['general'])

        
        result = {
          'title': title.strip() if title else "No Title",
          'url': current_url,
          'description': description.strip() if description else "No description available",
          'image': "https://i.imgur.com/ObR8yvE.jpeg",
          'tags': tags if 'tags' in locals() else [],
          'approved': False
        }

        result['timestamp'] = datetime.utcnow().isoformat()


        self.save_results(result)
        print(f"Saved: {result['title']} from {result['url']}")

        # Follow internal links
        links = response.css('a::attr(href)').getall()
        for link in links:
            absolute_url = urljoin(current_url, link)
            try:
                parsed_url = urlparse(absolute_url)
                if parsed_url.scheme in ['http', 'https'] and any(domain in parsed_url.netloc for domain in self.allowed_domains):
                    yield response.follow(absolute_url, self.parse)
            except:
                pass

    def save_results(self, result):
        output_file = 'result.json'
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)

        data = []
        if os.path.exists(output_file):
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                data = []

        # Avoid duplicates
        seen_urls = set()
        unique_data = []
        for item in data + [result]:
            if item['url'] not in seen_urls:
                unique_data.append(item)
                seen_urls.add(item['url'])

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(unique_data, f, ensure_ascii=False, indent=2)
