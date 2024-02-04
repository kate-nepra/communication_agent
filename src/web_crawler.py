import arrow

from src.sourcesdb import SourcesDB
from src.web_scraper import WebScraper
from bs4 import BeautifulSoup, Comment
import pandas as pd
from urllib.parse import urlparse, urlunparse

URL = 'url'
DATE_ADDED = 'date_added'
PARENT = 'parent'


class WebCrawler:

    def __init__(self, sources_db: SourcesDB, ws: WebScraper, df: pd.DataFrame, url: str):
        self.sources_db = sources_db
        self.ws = ws
        self.df = df
        self.url = url

    def _process(self):
        html = self.ws.scrape_url(self.url)
        main_url = self._get_parent_part_url(self.url)
        if not self._is_url_in_parents(main_url):
            print(self._get_nav_urls_df(html))  # classify
        # if crawl_only get urls from main !! should be crawl_only
        print(self._get_main_urls_df(html))
        return pd.DataFrame()

    def _get_nav_urls_df(self, html):
        urls = self._get_nav_urls(html)
        urls = self._del_subset('?cat=', urls)
        urls = self._clean_url_list(urls)
        dicts = self._create_urls_dict(urls)
        return pd.DataFrame(dicts)

    def _get_main_urls_df(self, html):
        urls = self._get_main_urls(html)
        urls = self._clean_url_list(urls)
        dicts = self._create_urls_dict(urls)
        return pd.DataFrame(dicts)

    def _get_main_urls(self, html):
        # get urls from main part of the page
        soup = BeautifulSoup(html, 'html.parser')
        main = soup.find('main') or soup.find('body')
        if main:
            urls = [a['href'] for a in main.find_all('a', href=True)]
            return urls
        return []

    def _create_urls_dict(self, urls):
        return [{URL: url, DATE_ADDED: arrow.now().format('YYYY-MM-DD'), PARENT: self._get_parent_part_url(url)} for url
                in
                urls]

    def _clean_url_list(self, urls):
        invalid_characters = ["{", "}", "|", "\\", "^", "~", "[", "]", "`", "<", ">", " "]
        for char in invalid_characters:
            urls = self._del_subset(char, urls)
        return [url for url in urls if url.startswith('http') or url.startswith('www')]

    def _is_url_in_parents(self, url):
        return url in self.df['parent'].values

    def _get_nav_urls(self, html):
        # get urls from navbar / header / nav in html
        soup = BeautifulSoup(html, 'html.parser')
        nav = soup.find('nav') or soup.find('header') or soup.find('navbar')
        if nav:
            urls = [a['href'] for a in nav.find_all('a', href=True)]
            return urls
        return []

    def _get_parent_part_url(self, url):
        parsed_url = urlparse(url)
        parent_url = urlunparse((parsed_url.scheme, parsed_url.netloc, '', '', '', ''))
        return parent_url

    def _del_subset(self, substr, urls):
        return [url for url in urls if substr not in url]


if __name__ == '__main__':
    data = pd.read_csv('./../data/sources.csv')
    sources = SourcesDB()
    ws = WebScraper(sources)
    wc = WebCrawler(sources, ws, data, 'https://www.gotobrno.cz/')
    wc._process()
