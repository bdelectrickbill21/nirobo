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
    
    # Extract title - improved for Bangladeshi news sites
    title = response.css('title::text').get()
    
    # For news sites, try to get article-specific titles
    if not title or title.strip() in ["", "Home", "Example Domain"]:
        # Try common article title selectors for Bangladeshi news sites
        title_selectors = [
            'h1.headline::text',
            'h1.title::text', 
            'h1.article-title::text',
            'h1::text',
            '.headline::text',
            '.story-title::text',
            '.article-headline::text'
        ]
        
        for selector in title_selectors:
            title = response.css(selector).get()
            if title and title.strip():
                break
    
    if not title:
        title = "No Title"
    
    # Extract description - improved for news sites
    description = response.xpath('//meta[@name="description"]/@content').get()
    
    # Try Open Graph description (common in news sites)
    if not description:
        description = response.xpath('//meta[@property="og:description"]/@content').get()
    
    # Try common article summary/intro selectors
    if not description:
        intro_selectors = [
            '.summary::text',
            '.intro::text',
            '.excerpt::text',
            '.article-lead::text',
            '.story-summary::text',
            '.content-lead::text'
        ]
        
        for selector in intro_selectors:
            description = response.css(selector).get()
            if description and description.strip():
                break
    
    # Try first substantial paragraph from article content
    if not description:
        # Target article content areas specifically
        content_selectors = [
            '.article-body p::text',
            '.story-body p::text',
            '.content p::text',
            '.post-content p::text',
            'article p::text',
            'main p::text'
        ]
        
        for selector in content_selectors:
            paragraphs = response.css(selector).getall()
            if paragraphs:
                for p in paragraphs:
                    if p.strip() and len(p.strip()) > 30:  # Ensure it's substantial
                        description = p
                        break
                if description:
                    break
    
    # Fallback to any paragraph
    if not description:
        paragraphs = response.css('p::text').getall()
        if paragraphs:
            for p in paragraphs:
                if p.strip() and len(p.strip()) > 30:
                    description = p
                    break
    
    if not description:
        description = "No description available"
    
    # Define tags based on domain - enhanced for Bangladesh focus
    domain_tags = {
        'thedailystar.net': ['news', 'bangladesh', 'politics', 'economy'],
        'prothomalo.com': ['news', 'bangla', 'bangladesh', 'culture', 'sports'],
        'dhakatribune.com': ['news', 'bangladesh', 'current-affairs', 'politics'],
        'bdnews24.com': ['news', 'bangladesh', 'breaking-news', 'current-affairs'],
        'bbc.com': ['news', 'global', 'international'],
        'aljazeera.com': ['news', 'middle-east', 'international', 'conflict'],
        'reuters.com': ['news', 'finance', 'global', 'business', 'markets'],
        'un.org': ['global', 'policy', 'development', 'humanitarian'],
        'who.int': ['health', 'global', 'medical', 'pandemic'],
        'cnn.com': ['news', 'global', 'international', 'politics'],
        'nytimes.com': ['news', 'international', 'analysis'],
        'edition.cnn.com': ['news', 'global', 'international']
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
        # Get links, but prioritize article links
        links = response.css('a::attr(href)').getall()
        
        # Filter for likely article links (contain /news/, /article/, etc.)
        article_links = []
        other_links = []
        
        for link in links:
            if any(keyword in link.lower() for keyword in ['/news/', '/article/', '/story/', '/bangladesh/', '/sports/', '/business/']):
                article_links.append(link)
            else:
                other_links.append(link)
        
        # Process article links first, then others (limit to 10 total)
        all_links = article_links[:5] + other_links[:5]
        
        for link in all_links:
            try:
                absolute_url = urljoin(response.url, link)
                parsed_url = urlparse(absolute_url)
                
                # Check if it's a valid HTTP/HTTPS URL and within allowed domains
                if (parsed_url.scheme in ['http', 'https'] and 
                    any(allowed_domain in parsed_url.netloc for allowed_domain in self.allowed_domains) and
                    absolute_url not in self.visited_urls and
                    not any(exclude in absolute_url for exclude in ['#', 'javascript:', 'mailto:', 'tel:'])):
                    
                    yield response.follow(absolute_url, self.parse)
            except Exception as e:
                self.logger.error(f"Error following link {link}: {e}")
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
