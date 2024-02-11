import arrow

from src.sourcesdb import SourcesDB
from src.web_crawler import WebCrawler
from src.web_scraper import WebScraper
from constants import URL, DATE_FORMAT
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

    def acquire_data(self) -> None:
        """
        This method is the main entry point for the data acquisition process. It retrieves urls from the sources database
        and passes them to the web crawler and the web scraper.
        """

        urls_df = self._sources_db.get_all_crawl_only_sources()
        for url in urls_df[URL]:
            wc = WebCrawler(url, urls_df['parent'])
            extend_df = wc.get_extend_df()

    def initial_data_acquisition(self) -> None:
        """
        This method is responsible for the initial data acquisition. It retrieves the initial set of urls from the
        sources database and passes them to the web crawler and the web scraper.
        """

        urls_df = self._sources_db.get_all_crawl_only_sources()
        for url in urls_df[URL]:
            wc = WebCrawler(url, urls_df['parent'])
            extend_df = wc.get_extend_df()
            existing_urls = self._sources_db.get_existing_from_list(extend_df[URL])
            self._update_existing_urls(existing_urls)

            extend_df = extend_df[~extend_df[URL].isin(existing_urls)]
            for new_url in extend_df[URL]:
                ws = WebScraper(new_url)
                extend_df.loc[extend_df[URL] == new_url, 'crawl_only'] = ws.is_crawl_only()
                # classify type
                # scrape if not crawl only
            self._sources_db.insert_sources(extend_df)

    def _update_existing_urls(self, existing_urls) -> None:
        """
        This method updates the existing urls in the sources' database. It sets the date_added to current date.
        """
        self._sources_db.update_existing_urls_date(existing_urls, arrow.now().format(DATE_FORMAT))
