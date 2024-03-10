import json

import arrow
import pandas as pd

from src.crawl_only_type_classifier import get_content_type
from src.parser import get_parsed_content, BaseSchema
from src.sourcesdb import SourcesDB
from src.web_crawler import WebCrawler
from src.web_scraper import WebScraper
from src.pdf_scraper import PdfScraper
from constants import URL, DATE_FORMAT, BRNO_SUBSTRS, TYPE_ID, CRAWL_ONLY, DATE_SCRAPED


class DataAcquisitionManager:
    """
    This class is responsible for managing the data acquisition process. It coordinates the interaction between the
    sources database, the web crawler and the web scraper. The manager is responsible for the following tasks:
    - retrieving urls from the sources database
    - passing the url to the web crawler
    - expanding the sources database with the new urls found by the web crawler
    - passing the url to the web scraper
    - passing the scraped data to the parser
    - storing the parsed data in the vector database
    """

    def __init__(self, sources_db: SourcesDB):
        self._sources_db = sources_db

    def _crawl_url(self, url: str, parents: list) -> pd.DataFrame:
        """
        This method is responsible for passing the url to the web crawler and getting the new urls.
        :param url: Url to be crawled
        :param parents: List of existing parent urls
        :return: DataFrame with the new urls
        """
        wc = WebCrawler(url, parents)
        extend_df = wc.get_extend_df()
        if extend_df.empty:
            return extend_df
        existing_urls = self._sources_db.get_existing_urls_from_list(extend_df[URL].values)
        extend_df = extend_df[extend_df[URL].apply(lambda x: len(x) <= 255)]
        if existing_urls:
            self._update_existing_urls(existing_urls)
        extend_df = extend_df[~extend_df[URL].isin(existing_urls)]
        extend_df = self._remove_banned(self._sources_db.get_banned_urls(), extend_df)
        extend_df[DATE_SCRAPED] = None
        extend_df[TYPE_ID] = None
        return extend_df

    def acquire_data(self, urls_df, iterations: int) -> None:
        """
        This method is responsible for the data acquisition process. It processes the given urls and passes them to the
        web crawler and the web scraper.
        """

        for i in range(iterations):
            urls_df = self._process_urls(urls_df[URL])

    def _process_urls(self, urls: list) -> pd.DataFrame:
        """
        This method processes the given urls and passes them to the web crawler and the web scraper.
        :param urls: List of urls to be processed
        :return: DataFrame with the new urls
        """
        acquired = pd.DataFrame()
        for url in urls:
            new_df = self._get_new_urls_from_url(url)
            self._sources_db.insert_or_update_sources(new_df)
            acquired = pd.concat([acquired, new_df])
        acquired = acquired[acquired[TYPE_ID] != int(self._sources_db.get_type_id('pdf'))]
        return acquired

    def _update_urls(self, urls: list) -> pd.DataFrame:
        """
        This method updates the given urls in the sources database.
        :param urls: List of urls to be updated
        :return: DataFrame with the new urls
        """
        acquired = pd.DataFrame()
        for url in urls:
            new_df = self._get_new_urls_from_url(url)
            self._sources_db.update_sources(new_df)
            acquired = pd.concat([acquired, new_df])
        acquired = acquired[acquired[TYPE_ID] != int(self._sources_db.get_type_id('pdf'))]
        return acquired

    def initial_data_acquisition(self, iterations: int) -> None:
        """
        This method is responsible for the initial data acquisition. It scrapes the contents of the initial non
        crawl_only data and passes the crawl_only data to the web crawler and the web scraper.
        """

        urls_df = self._sources_db.get_all_non_banned_non_static_non_pdf_sources_as_dataframe()
        if urls_df.empty:
            return
        to_scrape = pd.concat(
            [urls_df[urls_df[CRAWL_ONLY] == 0], self._sources_db.get_all_static_sources_as_dataframe()])
        self._scrape_and_update_sources(to_scrape)
        self.acquire_data(urls_df, iterations)

    def _is_banned(self, ws: WebScraper, new_url: str, banned: list) -> bool:
        """
        This method checks if the given url is banned based on the content of the web page.
        """
        if not ws.does_html_contain_substrs(BRNO_SUBSTRS):
            self._sources_db.add_or_update_banned_source(new_url, arrow.now().format(DATE_FORMAT))
            banned.append(new_url)
            return True
        return False

    def _update_existing_urls(self, existing_urls) -> None:
        """
        This method updates the existing urls in the sources' database. It sets the date_added to current date.
        """
        self._sources_db.update_existing_urls_date(existing_urls, arrow.now().format(DATE_FORMAT))

    def update_by_type_name(self, type_name: str) -> None:
        if type_name == 'pdf':
            self._update_pdfs()
            return
        data_df = self._sources_db.get_all_non_crawl_only_not_banned_sources_by_type(type_name)
        self._scrape_and_update_sources(data_df)

    def _update_pdfs(self) -> None:
        urls = self._sources_db.get_all_pdf_urls()
        docs = PdfScraper(urls).get_chunks_batch()
        for chunks, url in docs:
            for chunk in chunks:
                content = get_parsed_content(url, chunk)
                self._sources_db.add_parsed_source(url, self._get_json_str_from_content(content))
        self._sources_db.update_existing_urls_date(urls, arrow.now().format(DATE_FORMAT))

    def _scrape_and_update_sources(self, to_scrape: pd.DataFrame) -> None:
        """
        This method scrapes the contents of the given urls and updates the sources database with the scraped data.
        :param to_scrape: DataFrame with the urls to be scraped
        :return:
        """
        for url in to_scrape[URL]:
            ws = WebScraper(url)
            if self._is_banned(ws, url, []):
                continue
            for t in ws.get_clean_texts():
                content = get_parsed_content(url, t)
                self._sources_db.add_parsed_source(url, self._get_json_str_from_content(content))
                type_name = content.record_type
                to_scrape.loc[to_scrape[URL] == url, TYPE_ID] = self._sources_db.get_type_id(type_name)
                to_scrape.loc[to_scrape[URL] == url, DATE_SCRAPED] = arrow.now().format(DATE_FORMAT)
        self._sources_db.insert_or_update_sources(to_scrape)

    @staticmethod
    def _remove_banned(banned: list, extend_df: pd.DataFrame) -> pd.DataFrame:
        """
        This method removes the banned urls from the given DataFrame.
        :param banned: List of banned urls
        :param extend_df:
        :return:
        """

        extend_df = extend_df[~extend_df[URL].isin(banned)]
        for ban in banned:
            extend_df = extend_df[~extend_df[URL].str.contains(ban, regex=False)]
        return extend_df

    def _handle_pdf(self, url: str, parent_url: str) -> None:
        """ This method handles the pdf urls. It adds the pdf url to the sources database. Only pdfs from
        gotobrno are allowed."""
        if 'gotobrno' in url:
            self._sources_db.add_or_update_source(url, arrow.now().format(DATE_FORMAT), arrow.now().format(DATE_FORMAT),
                                                  None, parent_url, int(self._sources_db.get_type_id('pdf')))
            pdf_scraper = PdfScraper([url])
            chunks, url = pdf_scraper.get_chunks()
            for chunk in chunks:
                content = get_parsed_content(url, chunk)
                self._sources_db.add_parsed_source(url, self._get_json_str_from_content(content))

    def _process_non_crawl_only(self, new_url: str, ws: WebScraper) -> list[[bool, int, str]]:
        """
        This method processes the non crawl_only urls. It scrapes the contents of the web page and passes the scraped
        data to the parser.
        :param new_url: Url that is being processed
        :param ws: WebScraper object
        :return: List of lists with the processed data, where each list contains the following elements:
            - crawl_only: boolean
            - type_id: int
            - date_scraped: str
        """
        results = []
        for t in ws.get_clean_texts():
            content = get_parsed_content(new_url, t)
            type_id = self._sources_db.get_type_id(content.record_type)
            self._sources_db.add_parsed_source(new_url, self._get_json_str_from_content(content))
            results.append([False, type_id, arrow.now().format(DATE_FORMAT)])
        return results

    def _get_new_urls_from_url(self, url: str) -> pd.DataFrame:
        """
        This method is responsible for calling the web crawler and getting the new urls, removing the banned urls and
        processing the new urls.
        :param url: Url to be crawled
        :return: DataFrame with the new urls
        """
        new_urls = self._crawl_url(url, self._sources_db.get_all_parents())
        if new_urls.empty:
            return new_urls

        new_urls = self._process_new_urls(new_urls, url)
        return new_urls

    def _process_new_urls(self, new_urls: pd.DataFrame, parent_url: str) -> pd.DataFrame:
        """ This method processes the new urls and passes them to the web scraper. """
        banned = []
        for new_url in new_urls[URL]:
            if (new_url[-4:] == '.pdf') or (new_url[-4:] == '.PDF'):
                self._handle_pdf(new_url, parent_url)
                banned.append(new_url)
                continue
            ws = WebScraper(new_url)
            if not self._is_banned(ws, new_url, banned):
                if ws.is_crawl_only():
                    type_id = int(self._sources_db.get_type_id(get_content_type(ws.html)))
                    new_urls.loc[new_urls[URL] == new_url, [CRAWL_ONLY, TYPE_ID]] = [True, type_id]
                else:
                    processed = self._process_non_crawl_only(new_url, ws)
                    for crawl_only, type_id, date_scraped in processed:
                        new_urls.loc[new_urls[URL] == new_url, [CRAWL_ONLY, DATE_SCRAPED, TYPE_ID]] = [crawl_only,
                                                                                                       date_scraped,
                                                                                                       type_id]
        new_urls = self._remove_banned(banned, new_urls)
        return new_urls

    @staticmethod
    def _get_json_str_from_content(content: BaseSchema) -> str:
        """
        This method returns the content as a dictionary.
        :param content: Content to be converted
        :return: Content as a dictionary
        """
        return json.dumps(content.__dict__)


if __name__ == '__main__':
    sources = SourcesDB()
    dam = DataAcquisitionManager(sources)
    dam.initial_data_acquisition(3)
    # dam.update_by_type_name('event')
