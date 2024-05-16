import logging
import re
import hashlib

from bs4 import BeautifulSoup, Comment, Doctype, Tag, element
from fake_useragent import UserAgent
import requests
import copy

from src.constants import MAX_SIZE
from src.data_acquisition.constants import FORCED_TAGS
from src.data_acquisition.data_retrieval.constants import EXCLUDE_TAGS_BASE, DECOMPOSE_PATTERNS_BASE, WIKI_SPECIFIC

logger = logging.getLogger(__name__)


class WebScraper:
    """Class for scraping the content of a website. It provides methods for cleaning the html, extracting the text,
    and splitting the text into chunks."""

    def __init__(self, url):
        self.url = url
        self.html = self.scrape_url(url)
        self.cleaned_html = None
        self.base_clean_html = None
        self.decomposed_box_of_links_html = None

    @staticmethod
    def _rotate_headers():
        user_agent = UserAgent()
        return {'User-Agent': user_agent.random}

    def scrape_url(self, url: str) -> str:
        """Scrapes the content of the given url and returns the html as a string."""
        try:
            headers = self._rotate_headers()
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Error scraping {url}: {response.status_code}")
                return ''
            return BeautifulSoup(response.text, 'html.parser').prettify()
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")

    def get_base_clean_html(self) -> str:
        """Returns the html after the base cleaning."""
        if not self.base_clean_html:
            soup = BeautifulSoup(self.html, 'html.parser')
            soup = self._base_clean(soup)
            html = soup.prettify()
            self.base_clean_html = self._remove_repeated_parts(html)
        return self.base_clean_html

    def get_encoded_content(self) -> str:
        """Returns the sha256 encoded content of the html."""
        text = self.get_text_from_html(self.get_cleaned_html())
        return self._hash_text(text)

    def get_chunks(self, max_size: int = MAX_SIZE) -> list[str]:
        """Splits the text into chunks by headers of a given size maximum."""
        soup = BeautifulSoup(self.get_cleaned_html(), 'html.parser')
        text = self._get_text(soup)
        if len(text) > max_size:
            return self._get_cleaned_html_text_sliced_by_headers(max_size)
        return [text]

    def get_chunks_from_html(self, html: str, max_size: int = MAX_SIZE) -> list[str]:
        """Splits the given html into chunks by headers of a given size maximum."""
        soup = BeautifulSoup(html, 'html.parser')
        text = self._get_text(soup)
        if len(text) > max_size:
            return self._get_cleaned_html_text_sliced_by_headers(max_size)
        return [text]

    @staticmethod
    def get_text_from_html(html: str) -> str:
        if not html:
            return ''
        soup = BeautifulSoup(html, 'html.parser')
        return soup.get_text(strip=True, separator='\n')

    def get_cleaned_html(self) -> str:
        if not self.cleaned_html:
            self.cleaned_html = self._clean_html(self.html)
        return self.cleaned_html

    def get_html_by_chunk_size(self, max_size: int = MAX_SIZE) -> list[str]:
        """Slices the html into chunks of a given size maximum."""
        return self._slice_html_by_size(self.html, max_size)

    def get_description(self):
        soup = BeautifulSoup(self.html, 'html.parser')
        description = soup.find('meta', attrs={'name': 'description'})
        if description:
            return description['content']
        return None

    def get_title(self):
        soup = BeautifulSoup(self.html, 'html.parser')
        title = soup.find('title')
        if title:
            return title.get_text(strip=True)
        return None

    def get_main_header(self):
        soup = BeautifulSoup(self.html, 'html.parser')
        main_header = soup.find('h1') or soup.find('h2') or soup.find('h3') or soup.find('h4') or soup.find(
            'h5') or soup.find('h6')
        if main_header:
            return main_header.get_text(strip=True)
        return None

    def get_decomposed_box_of_links_html(self) -> str:
        """Returns the html after decomposing the box of links."""
        if not self.decomposed_box_of_links_html:
            html = '' + self.html
            soup = BeautifulSoup(html, 'html.parser')
            soup = self._extract_comments(soup)
            soup = self._exclude_tags(soup)
            html = soup.prettify()
            html = self._decompose_box_of_links(html)
            soup = BeautifulSoup(html, 'html.parser')
            soup = self._decompose_patterns(soup)
            soup = self._apply_unwrap_patterns(soup)
            soup = self._unwrap_tags(soup)
            soup = self._decompose_empty_tags(soup)
            html = soup.prettify()
            html = self._merge_same_tags(html)
            html = self._unwrap_unnecessary_tags(html)
            html = self._fix_newlines(html)
            html = self._fix_whitespaces(html)
            self.decomposed_box_of_links_html = html
        return self.decomposed_box_of_links_html

    def is_crawl_only(self) -> bool:
        """
        This method checks if the url should be crawled only.
        :return: bool
        """
        html = self.get_decomposed_box_of_links_html()
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup.find_all():
            if len(tag.get_text(strip=True)) > 100:
                return False
        if len(self.get_chunks()) > 500:
            return False
        return True

    def does_html_contain_substrs(self, substrs: list[str]) -> bool:
        """
        This method checks if the html contains any of the substrings.
        :param substrs: list[str]
        :return: bool
        """
        text = self.get_text_from_html(self.html)
        for substr in substrs:
            if substr in text:
                return True
        return False

    def _clean_html(self, html: str):
        """Cleans the html by removing unnecessary tags, merging same tags, unwrapping unnecessary tags,
        while fixing newlines and whitespaces."""
        html = self._unwrap_and_decompose(html)
        html = self._decompose_box_of_links(html)
        html = self._merge_same_tags(html)
        html = self._unwrap_unnecessary_tags(html)
        html = self._fix_newlines(html)
        html = self._fix_whitespaces(html)
        return html

    @staticmethod
    def _is_box_of_links(tag: BeautifulSoup) -> bool:
        """Checks if the tag is a box of links."""
        if not tag.name:
            return False
        tag = copy.copy(tag)
        for a in tag.find_all('a'):
            a.decompose()
        return tag.get_text(strip=True) == "" or tag.contents == []

    @staticmethod
    def _apply_decompose_pattern(soup: BeautifulSoup, pattern: str) -> BeautifulSoup:
        """Decomposes the tags that match the given pattern."""
        for tag in soup.find_all(attrs={"class": re.compile(pattern)}):
            if tag.name not in FORCED_TAGS:
                tag.decompose()
        for tag in soup.find_all(attrs={"id": re.compile(pattern)}):
            if tag.name not in FORCED_TAGS:
                tag.decompose()
        return soup

    def _base_clean(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Cleans the html by removing unnecessary tags and decomposing the tags that match the patterns."""
        for tag in soup.find_all(EXCLUDE_TAGS_BASE):
            tag.decompose()

        combined_d_pattern = "|".join(DECOMPOSE_PATTERNS_BASE)
        soup = self._apply_decompose_pattern(soup, combined_d_pattern)
        return soup

    @staticmethod
    def _extract_doctype(soup: BeautifulSoup) -> BeautifulSoup:
        for item in soup.contents:
            if isinstance(item, Doctype):
                item.extract()
                break
        return soup

    @staticmethod
    def _exclude_tags(soup: BeautifulSoup) -> BeautifulSoup:
        """Excludes the tags that are not needed."""
        exclude_tags = ['nav', 'header', 'menuitem', 'menu']
        for tag in soup.find_all(EXCLUDE_TAGS_BASE + exclude_tags):
            tag.decompose()

        return soup

    @staticmethod
    def _unwrap_tags(soup: BeautifulSoup) -> BeautifulSoup:
        """Unwraps the tags that are not needed."""
        to_unwrap = ['strong', 'em', 'sup', 'sub', 'b', 'i', 'u', 's', 'html', 'body', 'main', 'br', 'hr']
        for tag in soup.find_all(to_unwrap):
            tag.unwrap()
        return soup

    @staticmethod
    def _extract_comments(soup: BeautifulSoup) -> BeautifulSoup:
        """Extracts the comments from the soup."""
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        return soup

    def _decompose_patterns(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Decomposes the tags that match the patterns."""
        decompose_patterns = [".*header.*", ".*navigation.*", ".*menu.*", ".*navbox.*", ".*edit-",
                              ".*cite.*"]
        combined_d_pattern = "|".join(DECOMPOSE_PATTERNS_BASE + WIKI_SPECIFIC + decompose_patterns)
        soup = self._apply_decompose_pattern(soup, combined_d_pattern)
        return soup

    @staticmethod
    def _apply_unwrap_patterns(soup: BeautifulSoup) -> BeautifulSoup:
        """Unwraps the tags that match the patterns."""
        unwrap_patterns = [".*grid.*", ".*row.*", ".*col.*", ".*container.*", ".*wrapper.*", ".*content.*",
                           ".*main.*", ".*article.*", ".*section.*", ".*aside.*", ".*u-mw.*", ".*u-mh.*", ".*u-mt.*",
                           ".*u-mb.*", ".*u-ml.*", ".*u-mr.*", ".*u-p.*", ".*u-pt.*", ".*u-pb.*", ".*u-pl.*",
                           ".*u-pr.*", ".*u-pv.*", ".*u-ph.*", ".*u-ta.*", ".*u-tl.*", ".*u-tr.*", ".*u-tc.*",
                           ".*u-tj.*", ".*u-tv.*", ".*u-dib.*", ".*u-dit.*", ".*u-dib.*", ".*u-dn.*"]

        combined_u_pattern = "|".join(unwrap_patterns)

        for tag in soup.find_all(attrs={"class": re.compile(combined_u_pattern)}):
            tag.unwrap()

        for tag in soup.find_all(attrs={"id": re.compile(combined_u_pattern)}):
            tag.unwrap()

        return soup

    @staticmethod
    def _decompose_empty_tags(soup) -> BeautifulSoup:
        for tag in soup.find_all():
            if not tag.get_text(strip=True):
                tag.decompose()
        return soup

    def _unwrap_and_decompose(self, html: str) -> str:
        """Unwraps and decomposes the tags that are not needed."""
        soup = BeautifulSoup(html, 'html.parser')
        soup = self._extract_comments(soup)
        soup = self._extract_doctype(soup)
        soup = self._exclude_tags(soup)
        soup = self._decompose_patterns(soup)
        soup = self._apply_unwrap_patterns(soup)
        soup = self._unwrap_tags(soup)
        soup = self._decompose_empty_tags(soup)
        return soup.prettify()

    def _decompose_box_of_links(self, html: str) -> str:
        """Decomposes the box of links."""
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup.find_all(['p', 'div']):
            if tag and self._is_box_of_links(tag):
                prev = tag.find_previous_sibling()
                if prev and self._is_header(prev):
                    prev.decompose()
                tag.decompose()
        if len(soup.get_text()) < 100:
            soup = BeautifulSoup(html, 'html.parser')
            for tag in soup.find_all(['a']):
                tag.decompose()
        return soup.prettify()

    @staticmethod
    def _merge_same_tags(html: str) -> str:
        """Merges the tags that are same and next to each other."""
        soup = BeautifulSoup(html, 'html.parser')
        last_tag = None
        for tag in soup.find_all():
            if last_tag and last_tag.name == tag.name and last_tag.attrs == tag.attrs and tag.string and last_tag.string and len(
                    tag.find_all(recursive=False)) <= 1 and len(last_tag.find_all(recursive=False)) <= 1 and len(
                tag.string) > 20 and len(last_tag.string) > 20 and len(tag.string) < 200 and len(last_tag.string) < 200:
                last_tag.string += '\n' + tag.text
                tag.extract()
            else:
                last_tag = tag
        return soup.prettify()

    @staticmethod
    def _unwrap_unnecessary_tags(html: str) -> str:
        """Unwraps the unnecessary tags."""
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup.find_all():
            if tag.parent.name != 'body' and len(tag.find_all()) == 1 and tag.name not in ['a', 'p', 'div', 'h1', 'h2',
                                                                                           'h3', 'h4', 'h5', 'h6']:
                tag.unwrap()
        return soup.prettify()

    @staticmethod
    def _fix_newlines(html: str) -> str:
        """Replace the newlines with spaces."""
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup.find_all():
            if tag.string:
                tag.string.replace_with(tag.string.replace('\n', ' '))
        return soup.prettify()

    @staticmethod
    def _fix_whitespaces(html: str) -> str:
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup.find_all():
            if tag.string:
                tag.string.replace_with(' '.join(tag.string.split()))
        return soup.prettify()

    @staticmethod
    def _transform_tables(html: str) -> str:
        """Transforms the tables into structured paragraphs."""
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
    def _is_header(elem: Tag) -> bool:
        """Determines if the elem is a header."""
        if elem and elem.name:
            class_attr = ' '.join(elem.attrs.get('class', []))
            id_attr = ' '.join(elem.attrs.get('id', []))
            style_attr = ' '.join(elem.attrs.get('style', []))
            return elem.name.startswith('h') or "head" in class_attr or "head" in id_attr or "head" in style_attr
        return False

    def _is_only_child_header(self, elem: Tag) -> bool:
        """Determines if the elem is a header that is the only child of its parent."""
        if not elem.name:
            return False
        if self._is_header(elem):
            return True
        children = elem.find_all()
        if len(children) == 1:
            return self._is_only_child_header(children[0])
        return False

    def _remove_repeated_parts(self, text: str) -> str:
        if 'gotobrno.cz/en/' in self.url:
            index = text.find('Tell your friends about')
            if index != -1:
                text = text[:index]
        if 'wikipedia.org' in self.url:
            index = text.find('References')
            if index != -1:
                text = text[:index]
        if '/en' in self.url:
            index = text.find('Other languages')
            if index != -1:
                text = text[:index]
        return text

    def _get_text(self, soup: BeautifulSoup) -> str:
        text = soup.get_text(strip=True, separator='\n')
        text = self._remove_repeated_parts(text)
        return self._apply_regexes(text)

    @staticmethod
    def _apply_regexes(text: str) -> str:
        text = text.encode('utf-8', 'ignore').decode('utf-8')
        text = re.sub(r'\uFEFF|\u00A0', ' ', text)
        text = re.sub(r' +', ' ', text)
        text = re.sub(r' +\n', '\n', text)
        text = re.sub(r'\n +', '\n', text)
        text = re.sub(r'\n(,|\.|;|:|-)', r'\1', text)
        text = re.sub(r'\n(\()', ' (', text)
        text = re.sub(r'(\()\n', r'\1', text)
        text = re.sub(r'\n(\))', r')', text)
        return re.sub(r'([)|,])\n', r'\1 ', text)

    def _slice_html_by_size(self, html: str, max_size: int = MAX_SIZE) -> list[str]:
        """Slices the html into chunks of a given size maximum."""
        sliced_chunks = []
        current_chunk = ''
        current_length = 0
        soup = BeautifulSoup(html, 'html.parser')
        soup = self._unwrap_lenghty_tags(max_size, soup)
        soup = self._wrap_naked_text(soup)
        for tag in soup.find_all(recursive=False):
            current_chunk, sliced_chunks, current_length = self._slice_tag(current_chunk, current_length, max_size,
                                                                           sliced_chunks, tag)
        if current_chunk:
            sliced_chunks.append(current_chunk)
        return sliced_chunks

    def _slice_tag(self, current_chunk: str, current_length: int, max_size: int, sliced_chunks: list,
                   tag: BeautifulSoup) -> tuple[str, list, int]:
        """Slices the tag insides."""
        if current_length + len(tag.get_text().strip()) > max_size:
            if current_chunk:
                sliced_chunks.append(current_chunk)
                current_chunk = ''
                current_length = 0
        if len(tag.get_text().strip()) > max_size:
            current_chunk, current_length = self._slice_inter(current_chunk, current_length, max_size, sliced_chunks,
                                                              tag)
        current_chunk += str(tag).strip()
        current_length += len(tag.get_text(strip=True))
        return current_chunk, sliced_chunks, current_length

    @staticmethod
    def _slice_inter(current_chunk: str, current_length: int, max_size: int, sliced_chunks: list,
                     tag: BeautifulSoup) -> tuple[str, int]:
        tag_text = tag.get_text().strip()
        while len(tag_text) > max_size:
            index = tag_text.rfind('\n', 0, max_size) or tag_text.rfind('.', 0, max_size)
            if index == -1:
                break
            current_chunk = tag_text[:index + 1]
            sliced_chunks.append(current_chunk)
            current_chunk = tag_text[index + 1:]
            current_length = len(current_chunk)
        return current_chunk, current_length

    @staticmethod
    def _unwrap_lenghty_tags(max_size: int, soup: BeautifulSoup) -> BeautifulSoup:
        for tag in soup.find_all():
            if len(tag.get_text()) > max_size:
                tag.unwrap()
        return soup

    @staticmethod
    def _wrap_naked_text(soup: BeautifulSoup) -> BeautifulSoup:
        for node in soup:
            if isinstance(node, element.NavigableString):
                tag = soup.new_tag('p')
                tag.append(str(node))
                node.replace_with(tag)
        return soup

    @staticmethod
    def _slice_by_name(html: str, name: str) -> list[str]:
        slices = []
        found_indexes = [match.start() for match in re.finditer('<' + name, str(html))]
        if found_indexes and found_indexes[0] > 0:
            found_indexes.insert(0, 0)
            for i in range(0, len(found_indexes) - 1):
                slices.append(html[found_indexes[i]:found_indexes[i + 1]])
            slices.append(html[found_indexes[-1]:])
        return slices if slices else [html]

    @staticmethod
    def _apply_slicing_in_loop(slicing_method, slices: list, name: str, max_size: int):
        new_slices = []
        to_remove = []
        for s in slices:
            soup = BeautifulSoup(s, 'html.parser')
            if len(soup.get_text()) > max_size:
                to_remove.append(s)
                if name:
                    new_slices.extend(slicing_method(s, name))
                else:
                    new_slices.extend(slicing_method(s, max_size))
        slices = [s for s in slices if s not in to_remove]
        slices.extend(new_slices)
        return slices

    def _get_cleaned_html_text_sliced_by_headers(self, max_size: int) -> list[str]:
        max_size = max_size - len(self.get_main_header()) - 1 if self.get_main_header() else max_size
        html = self.get_cleaned_html()
        slices = self._slice_by_name(html, 'h2')
        slices = self._apply_slicing_in_loop(self._slice_by_name, slices, 'h3', max_size)
        slices = self._apply_slicing_in_loop(self._slice_html_by_size, slices, '', max_size)
        current_chunk = ''
        result = []
        for s in slices:
            text = self._get_text(BeautifulSoup(s, 'html.parser'))
            if len(current_chunk) + len(text) > max_size:
                result.append(current_chunk)
                current_chunk = ''
            current_chunk += '\n' + text
        if current_chunk:
            result.append(current_chunk)

        header = self.get_main_header() + '\n' if self.get_main_header() else ''

        return [header + r for r in result if len(r) > 200]

    @staticmethod
    def _hash_text(text: str) -> str:
        """Hashes the text using SHA-256 algorithm and returns the hexadecimal representation."""
        hasher = hashlib.sha256()
        hasher.update(text.encode('utf-8'))
        return hasher.hexdigest()
