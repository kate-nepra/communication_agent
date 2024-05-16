from src.constants import TODAY
from src.data_acquisition.constants import URL, DATE_ADDED, PARENT, CRAWL_ONLY
from src.data_acquisition.data_retrieval.constants import BANNED_SUBSTRINGS
from src.data_acquisition.data_retrieval.web_scraper import WebScraper
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urlparse, urlunparse


class WebCrawler:
    """Class for crawling websites and extracting urls from them."""

    def __init__(self, url: str, parents: list):
        self.url = url
        self.ws = WebScraper(url)
        self.parents = parents

    def get_extend_df(self) -> pd.DataFrame:
        """Returns a DataFrame with the crawled urls from the given website."""
        html = self.ws.html
        main_url = self._get_parent_part_url(self.url)
        urls = []
        if not self._is_url_in_parents(main_url):
            urls = (self._get_nav_urls(html))
        urls.extend(self._get_main_urls(html))
        if not urls:
            return pd.DataFrame()
        for ban in BANNED_SUBSTRINGS:
            urls = self._del_subset(ban, urls)
        return self._get_cleaned_df(urls).drop_duplicates()

    def _get_cleaned_df(self, urls: list) -> pd.DataFrame:
        """Returns a DataFrame with the cleaned urls."""
        urls = self._clean_url_list(urls)
        dicts = self._create_urls_dict(urls)
        df = pd.DataFrame(dicts)
        df[CRAWL_ONLY] = None
        df[CRAWL_ONLY] = df[CRAWL_ONLY].astype(bool)
        return df.drop_duplicates(subset=URL)

    @staticmethod
    def _get_main_urls(html: str) -> list[str]:
        """Returns a list of urls from the main part of the website."""
        if not html:
            return []
        soup = BeautifulSoup(html, 'html.parser')
        main = soup.find('main') or soup.find('body')
        if main:
            urls = [a['href'] for a in main.find_all('a', href=True)]
            return urls
        return []

    def _create_urls_dict(self, urls: list) -> list[dict]:
        """Returns a list of dictionaries with the urls and the date they were added."""
        date = TODAY
        return [{URL: url, DATE_ADDED: date, PARENT: self._get_parent_part_url(url)} for url in urls]

    def _clean_url_list(self, urls: list[str]) -> list[str]:
        """Returns a list of cleaned urls."""
        invalid_characters = ["{", "}", "|", "\\", "^", "~", "[", "]", "`", "<", ">", " "]
        for char in invalid_characters:
            urls = self._del_subset(char, urls)
        invalid_suffixes = [".jpg", ".png", ".jpeg", ".gif", ".svg", ".mp4", ".mp3", ".avi", ".mov", ".aspx"]
        for suffix in invalid_suffixes:
            urls = self._del_subset(suffix, urls)
        return [url for url in urls if url.startswith('http') or url.startswith('www')]

    def _is_url_in_parents(self, url: str) -> bool:
        return url in self.parents

    @staticmethod
    def _get_nav_urls(html: str) -> list[str]:
        """Returns a list of urls from the navigation part of the website."""
        if not html:
            return []
        soup = BeautifulSoup(html, 'html.parser')
        nav = soup.find('header') or soup.find('nav') or soup.find('navbar')
        if nav:
            urls = [a['href'] for a in nav.find_all('a', href=True)]
            return urls
        return []

    @staticmethod
    def _get_parent_part_url(url: str) -> str:
        """Returns the parent part of the url."""
        parsed_url = urlparse(url)
        parent_url = urlunparse((parsed_url.scheme, parsed_url.netloc, '', '', '', ''))
        return parent_url

    @staticmethod
    def _del_subset(substr: str, urls: list) -> list[str]:
        """Deletes the urls containing the given substring."""
        return [url for url in urls if substr not in url]
