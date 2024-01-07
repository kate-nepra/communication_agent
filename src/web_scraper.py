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

    def _clean_html(self, html):
        html = self._unwrap_and_decompose(html)
        html = self._decompose_box_of_links(html)
        html = self._merge_same_tags(html)
        html = self._unwrap_unnecessary_tags(html)
        html = self._fix_newlines(html)
        html = self._fix_whitespaces(html)
        return html

    @staticmethod
    def _is_box_of_links(tag):
        tag = copy.copy(tag)
        for a in tag.find_all('a'):
            a.decompose()
        return tag.get_text(strip=True) == "" or tag.contents == []

    @staticmethod
    def _unwrap_and_decompose(html):

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

        for tag in soup.find_all():
            if not tag.get_text(strip=True):
                tag.decompose()

        return soup.prettify()

    def _decompose_box_of_links(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup.find_all(['p', 'div']):
            if tag and self._is_box_of_links(tag):
                prev = tag.find_previous_sibling()
                if prev and self._is_header(prev):
                    prev.decompose()
                tag.decompose()
        return soup.prettify()

    @staticmethod
    def _merge_same_tags(html):
        soup = BeautifulSoup(html, 'html.parser')
        last_tag = None
        for tag in soup.find_all():
            if last_tag and last_tag.name == tag.name and last_tag.attrs == tag.attrs and tag.string and last_tag.string and len(
                    tag.find_all(recursive=False)) <= 1 and len(last_tag.find_all(recursive=False)) <= 1 and len(
                tag.string) > 20 and len(last_tag.string) > 20 and len(
                tag.string) < 200 and len(last_tag.string) < 200:
                last_tag.string += '\n' + tag.text
                tag.extract()
            else:
                last_tag = tag
        return soup.prettify()

    @staticmethod
    def _unwrap_unnecessary_tags(html):
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup.find_all():
            if tag.parent.name != 'body' and len(tag.find_all(recursive=False)) == 1 and tag.name != 'a':
                tag.unwrap()
        return soup.prettify()

    @staticmethod
    def _fix_newlines(html):
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup.find_all():
            if tag.string:
                tag.string.replace_with(tag.string.replace('\n', ' '))
        return soup.prettify()

    @staticmethod
    def _fix_whitespaces(html):
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup.find_all():
            if tag.string:
                tag.string.replace_with(' '.join(tag.string.split()))
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
            if current_size + len(element.prettify()) <= max_size:
                current_size += len(element.prettify())
                return element.prettify(), current_size
            else:
                return None, current_size

        def slice_html(node, current_size, chunk, last_header=''):
            for child in node.children:
                if child.name is not None:
                    if self._is_only_child_header(child):
                        last_header += child.prettify()
                        continue
                    elif last_header != '':
                        child = BeautifulSoup(last_header + child.prettify(), 'html.parser')
                        last_header = ''

                    chunk_part, current_size = slice_element(child, current_size)
                    if chunk_part:
                        chunk += chunk_part
                    else:
                        sliced_chunks.append(chunk)
                        chunk = child.prettify()  # TODO: fix too long chunks
                        current_size = len(chunk)
            if chunk:
                sliced_chunks.append(chunk)

        slice_html(soup, 0, '')

        return sliced_chunks


if __name__ == '__main__':
    sources = SourcesDB()
    ws = WebScraper(sources)
    html = ws._scrape_url('https://www.gotobrno.cz/en/events/otello/')
    cleaned_html = ws._clean_html(html)
    print(cleaned_html)
    print("---------------------------------- CLEANED ----------------------------------")
    chunks = ws._slice_html_by_size(cleaned_html, 1500)
    for chunk in chunks:
        print(chunk)
        print(len(chunk))
        print("---------------------------------- CHUNK ----------------------------------")
