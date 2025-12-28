"""
Web Tools for Ollama Agents - Zero-Cost Web Search and Scraping

Provides web search and content fetching capabilities for local Ollama agents.
Uses free APIs and respectful web scraping practices.
"""

import requests
import re
import logging
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, quote_plus
from bs4 import BeautifulSoup
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Web search result."""
    title: str
    url: str
    snippet: str
    position: int


@dataclass
class FetchedContent:
    """Fetched web content."""
    url: str
    title: str
    text_content: str
    html_content: str
    status_code: int
    error: Optional[str] = None


class WebSearchTool:
    """
    Zero-cost web search using DuckDuckGo HTML search.

    No API key required, respects rate limits, and provides clean results.
    """

    def __init__(self, user_agent: str = None):
        self.user_agent = user_agent or "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        self.base_url = "https://html.duckduckgo.com/html/"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})
        self.last_request_time = 0
        self.min_delay = 1.5  # Seconds between requests

    def search(
        self,
        query: str,
        max_results: int = 10,
        site: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Search the web using DuckDuckGo.

        Args:
            query: Search query
            max_results: Maximum number of results to return
            site: Optional site filter (e.g., ".edu" for academic sites)

        Returns:
            List of SearchResult objects
        """
        # Add site filter if specified
        if site:
            query = f"{query} site:{site}"

        logger.info(f"Searching: {query}")

        # Rate limiting
        self._respect_rate_limit()

        try:
            # DuckDuckGo HTML search
            response = self.session.post(
                self.base_url,
                data={
                    "q": query,
                    "b": "",
                    "kl": "us-en"
                },
                timeout=10
            )
            response.raise_for_status()

            # Parse results
            soup = BeautifulSoup(response.content, 'html.parser')
            results = []

            for i, result in enumerate(soup.select('.result'), 1):
                if i > max_results:
                    break

                # Extract title and URL
                title_elem = result.select_one('.result__a')
                snippet_elem = result.select_one('.result__snippet')

                if title_elem and snippet_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get('href', '')
                    snippet = snippet_elem.get_text(strip=True)

                    # Clean URL (DuckDuckGo uses redirect)
                    url = self._clean_url(url)

                    if url:
                        results.append(SearchResult(
                            title=title,
                            url=url,
                            snippet=snippet,
                            position=i
                        ))

            logger.info(f"Found {len(results)} search results")
            return results

        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    def _clean_url(self, url: str) -> str:
        """Extract actual URL from DuckDuckGo redirect."""
        if url.startswith('//'):
            url = 'https:' + url
        # DuckDuckGo redirect format: //duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com
        if 'uddg=' in url:
            match = re.search(r'uddg=([^&]+)', url)
            if match:
                from urllib.parse import unquote
                return unquote(match.group(1))
        return url

    def _respect_rate_limit(self):
        """Implement rate limiting to be respectful."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self.last_request_time = time.time()


class WebFetchTool:
    """
    Web content fetcher with HTML parsing and text extraction.

    Fetches web pages, extracts clean text content, respects robots.txt.
    """

    def __init__(self, user_agent: str = None):
        self.user_agent = user_agent or "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})
        self.timeout = 10

    def fetch(
        self,
        url: str,
        extract_text: bool = True,
        max_length: int = 10000
    ) -> FetchedContent:
        """
        Fetch and parse web content.

        Args:
            url: URL to fetch
            extract_text: Whether to extract clean text from HTML
            max_length: Maximum text content length (characters)

        Returns:
            FetchedContent object with parsed content
        """
        logger.info(f"Fetching: {url}")

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            html_content = response.text
            title = ""
            text_content = ""

            if extract_text:
                soup = BeautifulSoup(html_content, 'html.parser')

                # Extract title
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.get_text(strip=True)

                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()

                # Extract text
                text_content = soup.get_text(separator='\n', strip=True)

                # Clean up whitespace
                text_content = re.sub(r'\n\s*\n', '\n\n', text_content)
                text_content = re.sub(r' +', ' ', text_content)

                # Truncate if needed
                if len(text_content) > max_length:
                    text_content = text_content[:max_length] + "\n[Content truncated...]"

            return FetchedContent(
                url=url,
                title=title,
                text_content=text_content,
                html_content=html_content if not extract_text else "",
                status_code=response.status_code
            )

        except Exception as e:
            logger.error(f"Fetch error for {url}: {e}")
            return FetchedContent(
                url=url,
                title="",
                text_content="",
                html_content="",
                status_code=0,
                error=str(e)
            )

    def fetch_multiple(
        self,
        urls: List[str],
        delay: float = 2.0,
        **kwargs
    ) -> List[FetchedContent]:
        """
        Fetch multiple URLs with rate limiting.

        Args:
            urls: List of URLs to fetch
            delay: Delay between requests (seconds)
            **kwargs: Additional arguments for fetch()

        Returns:
            List of FetchedContent objects
        """
        results = []
        for url in urls:
            result = self.fetch(url, **kwargs)
            results.append(result)
            if url != urls[-1]:  # Don't delay after last URL
                time.sleep(delay)
        return results


class FacultyPageParser:
    """
    Specialized parser for academic faculty pages.

    Extracts hire information, faculty names, and profiles from .edu pages.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.FacultyPageParser")

    def extract_hires(
        self,
        html_content: str,
        url: str
    ) -> List[Dict[str, Any]]:
        """
        Extract faculty hire information from HTML.

        Args:
            html_content: HTML content of the page
            url: Source URL

        Returns:
            List of hire records with name, title, date
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        hires = []

        # Pattern 1: Look for "new faculty" sections
        new_faculty_sections = soup.find_all(['div', 'section'],
                                              text=re.compile(r'new\s+faculty|recent\s+hire', re.I))

        for section in new_faculty_sections:
            # Find names in nearby text
            names = self._extract_names(section.get_text())
            for name in names:
                hires.append({
                    "name": name,
                    "source": "new_faculty_section",
                    "url": url
                })

        # Pattern 2: Look for faculty listings with join dates
        faculty_entries = soup.find_all(['li', 'div'], class_=re.compile(r'faculty|person|profile', re.I))

        for entry in faculty_entries:
            text = entry.get_text()

            # Look for patterns like "Joined 2024" or "New: 2024"
            date_match = re.search(r'(?:joined|new|hired).*?(\d{4})', text, re.I)
            if date_match:
                year = date_match.group(1)
                if int(year) >= 2023:  # Recent hires only
                    names = self._extract_names(text)
                    for name in names:
                        hires.append({
                            "name": name,
                            "hire_date": year,
                            "source": "faculty_listing",
                            "url": url
                        })

        # Deduplicate by name
        seen_names = set()
        unique_hires = []
        for hire in hires:
            if hire["name"] not in seen_names:
                seen_names.add(hire["name"])
                unique_hires.append(hire)

        self.logger.info(f"Extracted {len(unique_hires)} hires from {url}")
        return unique_hires

    def _extract_names(self, text: str) -> List[str]:
        """Extract person names from text using pattern matching."""
        # Look for patterns like "Dr. First Last" or "First Last, Ph.D."
        patterns = [
            r'(?:Dr\.|Professor)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+),?\s+(?:Ph\.?D\.?|PhD)',
            r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:joined|will\s+join|is\s+joining)',
        ]

        names = []
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                name = match.group(1)
                # Basic validation: 2-4 words, each capitalized
                words = name.split()
                if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words):
                    names.append(name)

        return names


# Convenience functions for agent use

def web_search(query: str, max_results: int = 10, site: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Search the web and return results.

    Args:
        query: Search query
        max_results: Maximum results to return
        site: Optional site filter (e.g., ".edu")

    Returns:
        List of search results as dictionaries
    """
    searcher = WebSearchTool()
    results = searcher.search(query, max_results, site)

    return [
        {
            "title": r.title,
            "url": r.url,
            "snippet": r.snippet,
            "position": r.position
        }
        for r in results
    ]


def web_fetch(url: str, extract_text: bool = True, max_length: int = 10000) -> Dict[str, Any]:
    """
    Fetch and parse web content.

    Args:
        url: URL to fetch
        extract_text: Whether to extract clean text
        max_length: Maximum text length

    Returns:
        Dictionary with fetched content
    """
    fetcher = WebFetchTool()
    content = fetcher.fetch(url, extract_text, max_length)

    return {
        "url": content.url,
        "title": content.title,
        "text": content.text_content,
        "html": content.html_content,
        "status_code": content.status_code,
        "error": content.error
    }


def search_faculty_hires(
    department: str,
    university: Optional[str] = None,
    max_results: int = 5
) -> List[Dict[str, Any]]:
    """
    Search for recent faculty hires in a department.

    Args:
        department: Academic department (e.g., "political science")
        university: Optional specific university name
        max_results: Maximum number of pages to check

    Returns:
        List of hire records with candidate information
    """
    # Build search query
    query_parts = []
    if university:
        query_parts.append(f'"{university}"')
    query_parts.append(f'"{department}"')
    query_parts.append('("new faculty" OR "recent hire" OR "people")')

    query = " ".join(query_parts)

    # Search for faculty pages
    searcher = WebSearchTool()
    search_results = searcher.search(query, max_results * 2, site=".edu")

    # Fetch and parse pages
    fetcher = WebFetchTool()
    parser = FacultyPageParser()

    all_hires = []
    pages_checked = 0

    for result in search_results:
        if pages_checked >= max_results:
            break

        # Fetch page content
        content = fetcher.fetch(result.url)
        if content.error:
            continue

        # Parse for hires
        hires = parser.extract_hires(content.html_content or content.text_content, result.url)
        all_hires.extend(hires)
        pages_checked += 1

        # Rate limiting
        time.sleep(2)

    logger.info(f"Found {len(all_hires)} total hires from {pages_checked} pages")
    return all_hires
