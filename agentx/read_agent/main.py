import asyncio
from typing import Dict, Any, List
import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import json
import subprocess
from pydantic import BaseModel

from agentx.common_libraries.base_agent import BaseAgent, AgentConfig

class WebsiteData(BaseModel):
    """Model for website analysis data"""
    url: str
    html_content: str
    metadata: Dict[str, Any]
    errors: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]
    seo_data: Dict[str, Any]

class ReadAgent(BaseAgent):
    """Agent responsible for scanning and analyzing websites"""
    
    async def initialize(self) -> None:
        """Initialize the Playwright browser and other resources"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        
    async def cleanup(self) -> None:
        """Clean up browser resources"""
        await self.context.close()
        await self.browser.close()
        await self.playwright.stop()
    
    async def fetch_page_content(self, url: str) -> str:
        """Fetch page content using Playwright for JavaScript-rendered content"""
        try:
            await self.page.goto(url)
            await self.page.wait_for_load_state("networkidle")
            content = await self.page.content()
            return content
        except Exception as e:
            self.logger.error("fetch_error", url=url, error=str(e))
            raise
    
    def clean_html(self, html: str) -> str:
        """Remove unnecessary sections from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove common non-essential elements
        for element in soup.select('footer, nav, .advertisement, script, style'):
            element.decompose()
            
        return str(soup)
    
    async def run_html_analysis(self, html: str) -> Dict[str, Any]:
        """Run HTMLHint analysis"""
        try:
            # Save HTML to temporary file
            with open('temp.html', 'w', encoding='utf-8') as f:
                f.write(html)
            
            # Run HTMLHint
            result = subprocess.run(
                ['htmlhint', 'temp.html', '--format', 'json'],
                capture_output=True,
                text=True
            )
            
            return json.loads(result.stdout)
        except Exception as e:
            self.logger.error("html_analysis_error", error=str(e))
            return {"errors": [str(e)]}
    
    async def run_lighthouse(self, url: str) -> Dict[str, Any]:
        """Run Lighthouse analysis"""
        try:
            result = subprocess.run(
                ['lighthouse', url, '--output', 'json', '--chrome-flags="--headless"'],
                capture_output=True,
                text=True
            )
            
            return json.loads(result.stdout)
        except Exception as e:
            self.logger.error("lighthouse_error", error=str(e))
            return {"errors": [str(e)]}
    
    async def extract_metadata(self, html: str) -> Dict[str, Any]:
        """Extract metadata from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        metadata = {
            "title": soup.title.string if soup.title else None,
            "meta_description": None,
            "meta_keywords": None,
            "h1_tags": [h1.text for h1 in soup.find_all('h1')],
            "links": len(soup.find_all('a')),
            "images": len(soup.find_all('img')),
        }
        
        # Extract meta tags
        for meta in soup.find_all('meta'):
            if meta.get('name') == 'description':
                metadata['meta_description'] = meta.get('content')
            elif meta.get('name') == 'keywords':
                metadata['meta_keywords'] = meta.get('content')
        
        return metadata
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a website analysis request"""
        url = data['url']
        self.logger.info("processing_url", url=url)
        
        # Fetch and analyze the page
        html_content = await self.fetch_page_content(url)
        cleaned_html = self.clean_html(html_content)
        
        # Run parallel analysis
        analysis_tasks = [
            self.run_html_analysis(cleaned_html),
            self.run_lighthouse(url),
            self.extract_metadata(cleaned_html)
        ]
        
        html_analysis, lighthouse_results, metadata = await asyncio.gather(*analysis_tasks)
        
        # Compile results
        website_data = WebsiteData(
            url=url,
            html_content=cleaned_html,
            metadata=metadata,
            errors=html_analysis.get('errors', []),
            performance_metrics=lighthouse_results.get('categories', {}),
            seo_data={
                'lighthouse_seo': lighthouse_results.get('categories', {}).get('seo', {}),
                'meta_tags': metadata
            }
        )
        
        return website_data.dict()

if __name__ == "__main__":
    config = AgentConfig(
        name="read_agent",
        port=8001
    )
    
    agent = ReadAgent(config)
    agent.start() 