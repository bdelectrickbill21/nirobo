import datetime
import scrapy
from urllib.parse import urljoin, urlparse
import json
import os

class NiroboSpider(scrapy.Spider):
    name = 'nirobo'

    start_urls = [
        'https://edition.cnn.com/',
        'https://www.thedailystar.net/',
        'https://www.prothomalo.com/',
        'https://www.dhakatribune.com/',
        'https://www.bdnews24.com/',
        'https://www.bbc.com/',
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
        'aljazeera.com',
        'reuters.com',
        'un.org',
        'who.int',
        'cnn.com'
    ]

    visited_urls = set()

    def parse(self, response):
        # Skip if already visited
        if response.url in self.visited_urls:
            return
        self.visited_urls.add(response.url)
        
        # Extract title
        title = response.css('title::text').get()
        if not title:
            title = response.xpath('//h1/text()').get()
        if not title:
            title = "No Title"
            
        # Extract description
        description = response.xpath('//meta[@name="description"]/@content').get()
        if not description:
            description = response.css('p::text').get()
        if not description:
            description = "No description available"
        
        # Define tags based on domain
        domain_tags = {
            'thedailystar.net': ['news', 'bangladesh'],
            'prothomalo.com': ['news', 'bangla', 'bangladesh'],
            'dhakatribune.com': ['news', 'bangladesh'],
            'bdnews24.com': ['news', 'bangladesh'],
            'bbc.com': ['news', 'global'],
            'aljazeera.com': ['news', 'middle-east'],
            'reuters.com': ['news', 'finance', 'global'],
            'un.org': ['global', 'policy'],
            'who.int': ['health', 'global'],
            'cnn.com': ['news', 'global']
        }
        
        parsed = urlparse(response.url)
        domain = parsed.netloc
        
        # Get tags for this domain
        tags = ['general']
        for key in domain_tags:
            if key in domain:
                tags = domain_tags[key]
                break
        
        # Create result object
        result = {
            'title': title.strip() if title else "No Title",
            'url': response.url,
            'description': description.strip() if description else "No description available",
            'image': "https://i.imgur.com/ObR8yvE.jpeg",
            'tags': tags,
            'approved': False,
            'timestamp': datetime.datetime.utcnow().isoformat()
        }
        
        # Save results
        self.save_results(result)
        print(f"Saved: {result['title']} from {result['url']}")
        
        # Follow internal links (limit to avoid infinite crawling)
        if len(self.visited_urls) < 100:  # Limit total pages to avoid long runs
            links = response.css('a::attr(href)').getall()
            for link in links[:10]:  # Limit links per page
                try:
                    absolute_url = urljoin(response.url, link)
                    parsed_url = urlparse(absolute_url)
                    
                    # Check if it's a valid HTTP/HTTPS URL and within allowed domains
                    if (parsed_url.scheme in ['http', 'https'] and 
                        any(allowed_domain in parsed_url.netloc for allowed_domain in self.allowed_domains) and
                        absolute_url not in self.visited_urls):
                        
                        yield response.follow(absolute_url, self.parse)
                except Exception as e:
                    continue

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

        print(f"Saving {len(unique_data)} total entries to result.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(unique_data, f, ensure_ascii=False, indent=2)
