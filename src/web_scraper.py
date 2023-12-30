import logging
import re
import time

from bs4 import BeautifulSoup, Comment
from fake_useragent import UserAgent
from src.sourcesdb import SourcesDB
import requests
import copy

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

    @staticmethod
    def _is_box_of_links(tag):
        tag = copy.copy(tag)
        for a in tag.find_all('a'):
            a.decompose()
        return tag.get_text(strip=True) == "" or tag.contents == []

    def _clean_html(self, html):

        decompose_patterns = [".*accessibility.*", ".*cookie.*", ".*social.*", ".*share.*", ".*footer.*", ".*header.*",
                              ".*navigation.*", ".*menu.*", ".*search.*", ".*intro__scroll.*", ".*vhide.*", ".*icon.*",
                              ".*logo.*", ".*btn.*", ".*img.*", ".*image.*"]

        unwrap_patterns = [".*grid.*", ".*row.*", ".*col.*", ".*container.*", ".*wrapper.*", ".*content.*",
                           ".*main.*", ".*article.*", ".*section.*", ".*aside.*", ".*u-mw.*", ".*u-mh.*", ".*u-mt.*",
                           ".*u-mb.*", ".*u-ml.*", ".*u-mr.*", ".*u-p.*", ".*u-pt.*", ".*u-pb.*", ".*u-pl.*",
                           ".*u-pr.*", ".*u-pv.*", ".*u-ph.*", ".*u-ta.*", ".*u-tl.*", ".*u-tr.*", ".*u-tc.*",
                           ".*u-tj.*", ".*u-tv.*", ".*u-dib.*", ".*u-dit.*", ".*u-dib.*", ".*u-dn.*", ]

        exclude_tags = [
            'img', 'style', 'script', 'svg', 'canvas', 'video', 'audio', 'iframe', 'embed', 'object', 'param',
            'source', 'track', 'map', 'area', 'math', 'use', 'noscript', 'del', 'ins', 'picture', 'figure',
            'nav', 'header', 'footer', 'aside', 'form', 'input', 'button', 'select', 'textarea', 'label',
            'fieldset', 'legend', 'datalist', 'optgroup', 'option', 'output', 'progress', 'meter', 'details',
            'summary', 'menuitem', 'menu', 'caption', 'colgroup', 'col',
            'meta', 'head'
        ]

        to_unwrap = ['strong', 'em', 'sup', 'sub', 'b', 'i', 'u', 's', 'html', 'body', 'main', 'br', 'hr']

        soup = BeautifulSoup(html, 'html.parser')

        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        combined_d_pattern = "|".join(decompose_patterns)

        for tag in soup.find_all(attrs={"class": re.compile(combined_d_pattern)}):
            tag.decompose()

        for tag in soup.find_all(attrs={"id": re.compile(combined_d_pattern)}):
            tag.decompose()

        combined_u_pattern = "|".join(unwrap_patterns)

        for tag in soup.find_all(attrs={"class": re.compile(combined_u_pattern)}):
            tag.unwrap()

        for tag in soup.find_all(attrs={"id": re.compile(combined_u_pattern)}):
            tag.unwrap()

        for tag in soup.find_all(exclude_tags):
            tag.decompose()

        for tag in soup.find_all(to_unwrap):
            tag.unwrap()

        for tag in soup.find_all(['p', 'div']):
            if tag and self._is_box_of_links(tag):
                prev = tag.find_previous_sibling()
                if prev and self._is_header(prev):
                    prev.decompose()
                tag.decompose()

        for tag in soup.find_all():
            if not tag.get_text(strip=True):
                tag.decompose()

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

    @staticmethod
    def _is_header(element) -> bool:
        return element and element.name and (
                element.name.startswith('h') or ".*header.*" in element.attrs.get('class', []) or \
                ".*header.*" in element.attrs.get('id', []) or ".*header.*" in element.attrs.get('style',
                                                                                                 []))

    def _is_only_child_header(self, element) -> bool:
        if not element.name:
            return False
        if self._is_header(element):
            return True
        children = element.find_all()
        if len(children) == 1:
            return self._is_only_child_header(children[0])
        return False

    def _slice_html_by_size(self, html, max_size):
        sliced_chunks = []
        soup = BeautifulSoup(html, 'html.parser')

        def slice_element(element, current_size):
            if current_size + len(str(element)) <= max_size:
                current_size += len(str(element))
                return str(element), current_size
            else:
                return None, current_size

        def slice_html_recursive(node, current_size, chunk, last_header=''):
            for child in node.children:
                if child.name is not None:
                    if self._is_only_child_header(child):
                        last_header += str(child)  # TODO: fix format
                        continue
                    elif last_header:
                        child.append(last_header)
                        last_header = ''

                    chunk_part, current_size = slice_element(child, current_size)
                    if chunk_part:
                        chunk += chunk_part
                    else:
                        sliced_chunks.append(chunk)
                        chunk = ''
                        current_size = 0
                    slice_html_recursive(child, current_size, chunk, last_header)

        slice_html_recursive(soup, 0, '')

        return sliced_chunks


if __name__ == '__main__':
    sources = SourcesDB()
    ws = WebScraper(sources)
    html = ws._scrape_url('https://www.gotobrno.cz/en/events/otello/')
    cleaned_html = ws._clean_html(html)
    print(cleaned_html)
    print('---------------------------- CLEAN UP TO HERE')
    chunks = ws._slice_html_by_size(cleaned_html, 1000)
    for chunk in chunks:
        print(chunk)
        print(len(chunk))
        print('---------------------------- CHUNK HERE')
