import scrapy
from urllib.parse import urljoin, urlparse
import json
import os

class NiroboSpider(scrapy.Spider):
    name = 'nirobo'
    
    # Start with some common .bd domains
    start_urls = [
        'https://www.thedailystar.net/',
        'https://www.prothomalo.com/',
        'https://www.dhakatribune.com/',
        'https://www.bdnews24.com/',
    ]
    
    # Limit to .bd domains
    allowed_domains = [
        'thedailystar.net',
        'prothomalo.com', 
        'dhakatribune.com',
        'bdnews24.com',
    ]
    
    # Keep track of visited URLs to avoid duplicates
    visited_urls = set()
    
    def parse(self, response):
        # Get the current URL
        current_url = response.url
        
        # Skip if already visited
        if current_url in self.visited_urls:
            return
            
        # Add to visited set
        self.visited_urls.add(current_url)
        
        # Extract title, description, and content
        title = response.css('title::text').get()
        if not title:
            title = response.css('h1::text').get() or "No Title"
            
        # Try to get meta description
        description = response.css('meta[name="description"]::attr(content)').get()
        if not description:
            # Fallback to first paragraph
            description = response.css('p::text').get() or "No description available"
            
        # Limit description length
        if description and len(description) > 200:
            description = description[:200] + "..."
            
        # Create result item
        result = {
            'title': title.strip() if title else "No Title",
            'url': current_url,
            'description': description.strip() if description else "No description available"
        }
        
        # Save result to JSON file
        self.save_results(result)
        
        # Follow link to other page on the same domain
        link = response.css('a::attr(href)').getall()
        for link in link:
            # Convert relative URL to absolute
            absolute_url = urljoin(current_url, link)
            
            # Check if it's a valid URL and on an allowed domain
            try:
                parsed_url = urlparse(absolute_url)
                if parsed_url.scheme in ['http', 'https'] and any(domain in parsed_url.netloc for domain in self.allowed_domains):
                    yield response.follow(absolute_url, self.parse)
            except:
                # Skip invalid URLs
                pass
                
    def save_results(self, result):
        # Save result to JSON file
        output_file = 'data/results.json'
        
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Read existing data
        data = []
        if os.path.exists(output_file):
            try:
                with open(output_file, 'r') as f:
                    data = json.load(f)
            except:
                data = []
                
        # Add new result
        data.append(result)
        
        # Remove duplicate based on URL
        unique_data = []
        seen_urls = set()
        for item in data:
            if item['url'] not in seen_urls:
                unique_data.append(item)
                seen_urls.add(item['url'])
                
        # Write back to file
        with open(output_file, 'w') as f:
            json.dump(unique_data, f, indent=2)
