"""Web crawling functionality for fetching documentation."""

import asyncio
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from bs4 import BeautifulSoup

from ..config import settings


class WebCrawler:
    """Web crawler for fetching documentation and metadata."""
    
    def __init__(self):
        self.timeout = settings.crawl_timeout_secs
        self.use_playwright = settings.use_playwright
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def fetch_docs(self, urls: List[str]) -> List[str]:
        """Fetch documentation from a list of URLs."""
        docs = []
        
        # Use asyncio to fetch multiple URLs concurrently
        tasks = [self.fetch_single_doc(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, str):
                docs.append(result)
            elif isinstance(result, Exception):
                print(f"Failed to fetch doc: {result}")
        
        return docs
    
    async def fetch_single_doc(self, url: str) -> Optional[str]:
        """Fetch documentation from a single URL."""
        try:
            if self.use_playwright:
                return await self.fetch_with_playwright(url)
            else:
                return await self.fetch_with_httpx(url)
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            return None
    
    async def fetch_with_httpx(self, url: str) -> Optional[str]:
        """Fetch using httpx."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # Parse HTML and extract text
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text[:5000]  # Limit to 5000 characters
    
    async def fetch_with_playwright(self, url: str) -> Optional[str]:
        """Fetch using Playwright for dynamic content."""
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()
                
                # Set timeout
                page.set_default_timeout(self.timeout * 1000)
                
                # Navigate to page
                await page.goto(url, wait_until='networkidle')
                
                # Get page content
                content = await page.content()
                
                # Parse and extract text
                soup = BeautifulSoup(content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get text content
                text = soup.get_text()
                
                # Clean up whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                
                await browser.close()
                
                return text[:5000]  # Limit to 5000 characters
                
        except ImportError:
            print("Playwright not available, falling back to httpx")
            return await self.fetch_with_httpx(url)
        except Exception as e:
            print(f"Playwright failed for {url}: {e}")
            return await self.fetch_with_httpx(url)
    
    def extract_doc_urls(self, endpoint: str) -> List[str]:
        """Extract potential documentation URLs from an endpoint."""
        urls = []
        
        try:
            parsed = urlparse(endpoint)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            # Common documentation paths
            doc_paths = [
                "/docs",
                "/documentation",
                "/readme",
                "/README",
                "/api",
                "/",
                "/help",
                "/guide"
            ]
            
            for path in doc_paths:
                urls.append(urljoin(base_url, path))
            
        except Exception as e:
            print(f"Failed to extract doc URLs from {endpoint}: {e}")
        
        return urls


class MockWebCrawler(WebCrawler):
    """Mock web crawler for testing."""
    
    async def fetch_docs(self, urls: List[str]) -> List[str]:
        """Return mock documentation."""
        return [
            "This is a mock documentation for testing purposes. It includes information about API endpoints, authentication methods, and usage examples.",
            "The server supports HTTPS authentication and provides comprehensive logging capabilities.",
            "Rate limiting is implemented with configurable thresholds. All requests are logged for observability.",
            "SBOM (Software Bill of Materials) is available for dependency transparency."
        ] 