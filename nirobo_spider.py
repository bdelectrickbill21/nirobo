import datetime
import scrapy
from urllib.parse import urljoin, urlparse
import json
import os
import logging

class NiroboSpider(scrapy.Spider):
    name = 'nirobo'

    start_urls = [
        'https://www.thedailystar.net/',
        'https://www.prothomalo.com/',
        'https://www.dhakatribune.com/',
        'https://www.bdnews24.com/',
        'https://edition.cnn.com/',
        'https://www.bbc.com/news',
        'https://www.aljazeera.com/',
        'https://www.reuters.com/',
        'https://www.nytimes.com/',
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
        'cnn.com',
        'nytimes.com'
    ]

    visited_urls = set()

    def parse(self, response):
        # Skip if already visited
        if response.url in self.visited_urls:
            return
        self.visited_urls.add(response.url)
        
        try:
            # Extract title
            title = None
            
            # Priority 1: Try article-specific title selectors
            title_selectors = [
                'h1.headline::text',
                'h1.title::text',
                'h1.article-title::text',
                'h1.story-title::text',
                '.headline::text',
                '.story-title::text',
                '.article-headline::text',
                'h1::text',
                'h2::text',
                '.title::text',
                'h1 span::text',
                '.post-title::text'
            ]
            
            for selector in title_selectors:
                extracted = response.css(selector).get()
                if extracted and extracted.strip() and len(extracted.strip()) > 5:
                    title = extracted
                    break
            
            # Fallback to page title
            if not title:
                title = response.css('title::text').get()
                
            if not title:
                title = "No Title"
            
            # Extract description
            description = None
            
            # Priority 1: Meta description
            description = response.xpath('//meta[@name="description"]/@content').get()
            
            # Priority 2: Open Graph description
            if not description:
                description = response.xpath('//meta[@property="og:description"]/@content').get()
            
            # Priority 3: Article-specific content
            if not description:
                content_selectors = [
                    '.summary::text',
                    '.intro::text',
                    '.excerpt::text',
                    '.article-lead::text',
                    '.story-summary::text',
                    '.content-lead::text',
                    '.field-body p::text',
                    '.article-body p:first-child::text',
                    '.story-body p:first-child::text',
                    '.content p:first-child::text',
                    'article p::text',
                    'main p::text',
                    '.post-content p::text',
                    '.news-article p::text'
                ]
                
                for selector in content_selectors:
                    extracted_list = response.css(selector).getall()
                    for extracted in extracted_list:
                        if extracted and extracted.strip() and len(extracted.strip()) > 30 and not extracted.strip().startswith(('Copyright', 'All rights', 'Follow us', 'Advertisement', 'Skip')):
                            description = extracted
                            break
                    if description:
                        break
            
            # Priority 4: First substantial paragraph
            if not description:
                paragraphs = response.css('p::text').getall()
                for p in paragraphs:
                    if p.strip() and len(p.strip()) > 50 and not p.strip().startswith(('Copyright', 'All rights', 'Follow us', 'Advertisement', 'Skip', 'Live updates', 'Published')):
                        description = p
                        break
            
            if not description:
                description = "No description available"
            
            # Define tags based on domain - comprehensive tagging for both Bangladesh and global content
            domain_tags = {
                'thedailystar.net': ['news', 'bangladesh', 'politics', 'economy', 'sports', 'flood', 'education', 'local'],
                'prothomalo.com': ['news', 'bangla', 'bangladesh', 'culture', 'sports', 'entertainment', 'local'],
                'dhakatribune.com': ['news', 'bangladesh', 'current-affairs', 'politics', 'development', 'local'],
                'bdnews24.com': ['news', 'bangladesh', 'breaking-news', 'current-affairs', 'education', 'infrastructure', 'local'],
                'bbc.com': ['news', 'global', 'international', 'world', 'uk', 'europe'],
                'aljazeera.com': ['news', 'middle-east', 'international', 'conflict', 'world', 'global'],
                'reuters.com': ['news', 'finance', 'global', 'business', 'markets', 'world', 'international'],
                'un.org': ['global', 'policy', 'development', 'humanitarian', 'international', 'world'],
                'who.int': ['health', 'global', 'medical', 'pandemic', 'world', 'international'],
                'cnn.com': ['news', 'global', 'international', 'politics', 'world', 'us'],
                'nytimes.com': ['news', 'international', 'analysis', 'world', 'us', 'global']
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
                'image': self.get_image_url(response),
                'tags': tags,
                'approved': False,
                'timestamp': datetime.datetime.utcnow().isoformat(),
                'source': self.get_source_name(domain)
            }
            
            # Save all results (both Bangladesh and global content)
            self.save_results(result)
            print(f"Saved: {result['title']} from {result['source']}")
            
            # Follow internal links (limit to avoid infinite crawling)
            if len(self.visited_urls) < 200:  # Increased limit for better global coverage
                # Get links
                links = response.css('a::attr(href)').getall()
                
                # Filter and prioritize article links
                article_links = []
                other_links = []
                
                for link in links[:60]:  # Limit to first 60 links per page
                    if not link:
                        continue
                        
                    # Look for article-like URL patterns
                    if any(keyword in link.lower() for keyword in ['/news/', '/article/', '/story/', '/bangladesh/', '/sports/', '/business/', '/opinion/', '/tech/', '/life/', '/entertainment/', '/environment/', '/world/', '/international/', '/global/']):
                        article_links.append(link)
                    else:
                        other_links.append(link)
                
                # Process article links first, then others (limit to 20 total)
                all_links = article_links[:10] + other_links[:10]
                
                for link in all_links:
                    try:
                        absolute_url = urljoin(response.url, link)
                        parsed_url = urlparse(absolute_url)
                        
                        # Check if it's a valid HTTP/HTTPS URL and within allowed domains
                        if (parsed_url.scheme in ['http', 'https'] and 
                            any(allowed_domain in parsed_url.netloc for allowed_domain in self.allowed_domains) and
                            absolute_url not in self.visited_urls and
                            len(absolute_url) < 250 and
                            not any(exclude in absolute_url.lower() for exclude in ['#', 'javascript:', 'mailto:', 'tel:', 'login', 'signup', 'comment', 'advertisement', 'ads', 'privacy', 'terms', 'about-us', 'contact', 'subscribe'])):
                            
                            yield response.follow(absolute_url, self.parse)
                    except Exception as e:
                        self.logger.error(f"Error following link {link}: {e}")
                        continue
                        
        except Exception as e:
            self.logger.error(f"Error processing {response.url}: {e}")
            return

    def get_image_url(self, response):
        """Extract image URL from the page"""
        # Try Open Graph image first
        og_image = response.xpath('//meta[@property="og:image"]/@content').get()
        if og_image:
            return og_image
            
        # Try Twitter image
        twitter_image = response.xpath('//meta[@name="twitter:image"]/@content').get()
        if twitter_image:
            return twitter_image
            
        # Try first image in article
        first_image = response.css('article img::attr(src), .article-body img::attr(src), main img::attr(src)').get()
        if first_image:
            return urljoin(response.url, first_image)
            
        # Default image for Bangladesh content
        if any(domain in response.url for domain in ['thedailystar.net', 'prothomalo.com', 'dhakatribune.com', 'bdnews24.com']):
            return "https://i.imgur.com/ObR8yvE.jpeg"
        else:
            # Default image for global content
            return "https://i.imgur.com/Zh4tQZP.jpg"

    def get_source_name(self, domain):
        """Get friendly source name"""
        source_names = {
            'thedailystar.net': 'The Daily Star',
            'prothomalo.com': 'Prothom Alo',
            'dhakatribune.com': 'Dhaka Tribune',
            'bdnews24.com': 'BD News 24',
            'bbc.com': 'BBC News',
            'aljazeera.com': 'Al Jazeera',
            'reuters.com': 'Reuters',
            'un.org': 'United Nations',
            'who.int': 'World Health Organization',
            'cnn.com': 'CNN',
            'nytimes.com': 'The New York Times'
        }
        
        for key in source_names:
            if key in domain:
                return source_names[key]
        
        return "Unknown Source"

    def save_results(self, result):
        output_file = 'result.json'
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)

        data = []
        if os.path.exists(output_file):
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                self.logger.error(f"Error reading existing result.json: {e}")
                data = []

        # Avoid duplicates
        seen_urls = set()
        unique_data = []
        for item in data:
            if item['url'] not in seen_urls:
                unique_data.append(item)
                seen_urls.add(item['url'])
        
        # Add new result if not already present
        if result['url'] not in seen_urls:
            unique_data.append(result)
            seen_urls.add(result['url'])

        print(f"Saving {len(unique_data)} total entries to result.json")
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(unique_data, f, ensure_ascii=False, indent=2)
            print(f"Successfully saved result for: {result['title'][:50]}...")
        except Exception as e:
            self.logger.error(f"Error writing to result.json: {e}")
