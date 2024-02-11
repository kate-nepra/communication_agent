import arrow

from src.constants import DATE_FORMAT, DATE_ADDED, URL, PARENT
from src.web_scraper import WebScraper
from bs4 import BeautifulSoup, Comment
import pandas as pd
from urllib.parse import urlparse, urlunparse


class WebCrawler:

    def __init__(self, url, parents: list):
        self.url = url
        self.ws = WebScraper(url)
        self.parents = parents

    def get_extend_df(self) -> pd.DataFrame:
        html = self.ws.html
        main_url = self._get_parent_part_url(self.url)
        urls = []
        if not self._is_url_in_parents(main_url):
            urls.append(self._get_nav_urls(html))
        urls.append(self._get_main_urls(html))
        return self._get_cleaned_df(urls)

    def _get_cleaned_df(self, urls):
        urls = self._del_subset('?cat=', urls)
        urls = self._clean_url_list(urls)
        dicts = self._create_urls_dict(urls)
        return pd.DataFrame(dicts)

    def _get_main_urls(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        main = soup.find('main') or soup.find('body')
        if main:
            urls = [a['href'] for a in main.find_all('a', href=True)]
            return urls
        return []

    def _create_urls_dict(self, urls):
        return [{URL: url, DATE_ADDED: arrow.now().format(DATE_FORMAT), PARENT: self._get_parent_part_url(url)} for url
                in
                urls]

    def _clean_url_list(self, urls):
        invalid_characters = ["{", "}", "|", "\\", "^", "~", "[", "]", "`", "<", ">", " "]
        for char in invalid_characters:
            urls = self._del_subset(char, urls)
        return [url for url in urls if url.startswith('http') or url.startswith('www')]

    def _is_url_in_parents(self, url):
        return url in self.parents

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
    ws = WebScraper('https://www.gotobrno.cz/en/explore-brno/')
    wc = WebCrawler('https://www.gotobrno.cz/en/explore-brno/', [])
    print(wc.get_extend_df())
