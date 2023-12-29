import logging
import re
from bs4 import BeautifulSoup, Comment
from fake_useragent import UserAgent
from src.sourcesdb import SourcesDB
import requests

logger = logging.getLogger(__name__)


class WebScraper:
    def __init__(self, sources_db: SourcesDB):
        self.sources_db = sources_db

    @staticmethod
    def _rotate_headers():
        user_agent = UserAgent()
        return {'User-Agent': user_agent.random}

    def _scrape_url(self, url):
        try:
            headers = self._rotate_headers()
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Error scraping {url}: {response.status_code}")
                return None
            return BeautifulSoup(response.text, 'html.parser').prettify()
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")

    def scrape_daily(self):
        source_urls = self.sources_db.get_sources_by_type_id(1)
        # parallelize

    @staticmethod
    def _clean_html(html):

        exclude_tags = [
            'img', 'style', 'script', 'svg', 'canvas', 'video', 'audio', 'iframe', 'embed', 'object', 'param',
            'source', 'track', 'map', 'area', 'math', 'use', 'noscript', 'del', 'ins', 'picture', 'figure',
            'nav', 'header', 'footer', 'aside', 'form', 'input', 'button', 'select', 'textarea', 'label',
            'fieldset', 'legend', 'datalist', 'optgroup', 'option', 'output', 'progress', 'meter', 'details',
            'summary', 'menuitem', 'menu', 'caption', 'colgroup', 'col',
            'meta', 'head'
        ]

        to_unwrap = ['strong', 'em', 'sup', 'sub', 'b', 'i', 'u', 's', 'html', 'body', 'main',]
        html = re.sub(r'<br\s*?/?>', '; ', html)
        soup = BeautifulSoup(html, 'html.parser')

        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        for tag in soup.find_all(exclude_tags):
            tag.decompose()

        for tag in soup.find_all(to_unwrap):
            tag.unwrap()

        return soup.prettify()

    @staticmethod
    def _transform_tables(html):
        soup = BeautifulSoup(html, 'html.parser')
        to_unwrap = ['tbody', 'thead', 'tfoot']
        for tag_name in to_unwrap:
            tags = soup.find_all(tag_name)
            for tag in tags:
                tag.unwrap()
        for table in soup.find_all('table'):
            table_text = ""
            for row in table.find_all('tr'):
                row_text = [cell.get_text() for cell in row.find_all(['td', 'th'])]
                table_text += ", ".join(row_text) + ";\n"
            table.name = 'p'
            table.string = table_text
        return soup.prettify()

    @staticmethod
    def _get_text(html):
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(strip=True, separator=' | ')
        return re.sub(r'(\s*\|\s*){2,}', ' | ', text)


if __name__ == '__main__':
    sources = SourcesDB()
    ws = WebScraper(sources)
    html = ws._scrape_url('https://www.gotobrno.cz/en/events/otello/')
    cleaned_html = ws._clean_html(html)
    print(cleaned_html)
