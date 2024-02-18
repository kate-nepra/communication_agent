import arrow
import pandas as pd

from src.crawl_only_type_classifier import get_content_type
from src.parser import get_parsed_content
from src.sourcesdb import SourcesDB
from src.web_crawler import WebCrawler
from src.web_scraper import WebScraper
from constants import URL, DATE_FORMAT, BRNO_SUBSTRS, BLACK_LIST, TYPE_ID, CRAWL_ONLY, ID, DATE_ADDED, PARENT
from bs4 import BeautifulSoup


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

    def _crawl_url(self, url: str, parents: list):
        wc = WebCrawler(url, parents)
        extend_df = wc.get_extend_df()
        extend_df.to_csv('extend_df.csv', index=False)
        existing_urls = self._sources_db.get_existing_urls_from_list(extend_df[URL].values)
        self._update_existing_urls(existing_urls)
        return extend_df[~extend_df[URL].isin(existing_urls)]

    def acquire_data(self,
                     urls_df) -> None:  # TODO chci crawlnout určitý typ, ten pak updatnout a scrapenout které nejsou crawl only ale zároveň to vzít z DB??
        """
        This method is the main entry point for the data acquisition process. It retrieves urls from the sources database
        and passes them to the web crawler and the web scraper.
        """

        crawl_only_df = urls_df[urls_df[CRAWL_ONLY] == 1]
        for url in crawl_only_df[URL]:
            extend_df = self._crawl_url(url, self._sources_db.get_all_parents())
            for new_url in extend_df[URL]:
                ws = WebScraper(new_url)
                if not ws.does_html_contain_substrs(BRNO_SUBSTRS):
                    BLACK_LIST.append(new_url)
                else:
                    if ws.is_crawl_only():
                        extend_df.loc[extend_df[URL] == new_url, CRAWL_ONLY] = True
                        type_name = get_content_type(ws.html)
                    else:
                        extend_df.loc[extend_df[URL] == new_url, CRAWL_ONLY] = False
                        content = get_parsed_content(ws.get_clean_text())
                        type_name = content.record_type
                    extend_df.loc[extend_df[URL] == new_url, TYPE_ID] = int(self._sources_db.get_type_id(type_name))
            extend_df = extend_df[~extend_df[URL].isin(BLACK_LIST)]
            extend_df.to_csv('extend_df.csv', index=False)
            self._sources_db.insert_sources(extend_df)

        not_crawl_only_df = urls_df[urls_df[CRAWL_ONLY] == 0]

        for url in not_crawl_only_df[URL]:
            ws = WebScraper(url)
            if not ws.does_html_contain_substrs(BRNO_SUBSTRS):
                BLACK_LIST.append(url)
                continue
            content = get_parsed_content(ws.get_clean_text())
            type_name = content.record_type
            not_crawl_only_df.loc[not_crawl_only_df[URL] == url, TYPE_ID] = self._sources_db.get_type_id(type_name)

    def initial_data_acquisition(self) -> None:
        """
        This method is responsible for the initial data acquisition. It retrieves the initial set of urls from the
        sources database and passes them to the web crawler and the web scraper.
        """

        urls_df = self._sources_db.get_all_sources_as_dataframe()
        self.acquire_data(urls_df)

    def _update_existing_urls(self, existing_urls) -> None:
        """
        This method updates the existing urls in the sources' database. It sets the date_added to current date.
        """
        self._sources_db.update_existing_urls_date(existing_urls, arrow.now().format(DATE_FORMAT))


if __name__ == '__main__':
    sources = SourcesDB()
    dam = DataAcquisitionManager(sources)
    dam.initial_data_acquisition()
    sources.close_connection()
