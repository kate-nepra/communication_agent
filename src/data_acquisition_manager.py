import arrow
import pandas as pd

from src.crawl_only_type_classifier import get_content_type
from src.parser import get_parsed_content
from src.sourcesdb import SourcesDB
from src.web_crawler import WebCrawler
from src.web_scraper import WebScraper
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

    def _crawl_url(self, url: str, parents: list):
        wc = WebCrawler(url, parents)
        extend_df = wc.get_extend_df()
        if extend_df.empty:
            return extend_df
        existing_urls = self._sources_db.get_existing_urls_from_list(extend_df[URL].values)
        extend_df = extend_df[extend_df[URL].apply(lambda x: len(x) <= 255)]
        if existing_urls:
            self._update_existing_urls(existing_urls)
        return extend_df[~extend_df[URL].isin(existing_urls)]

    def acquire_data(self, urls_df) -> None:
        """
        This method is the main entry point for the data acquisition process. It retrieves urls from the sources database
        and passes them to the web crawler and the web scraper.
        """

        acquired_df = self._process_urls(urls_df[URL])
        print('acquired_df -------------------------------------------------------------------------')
        print(acquired_df)
        self._process_urls(acquired_df[URL])

    def _process_urls(self, urls: list) -> pd.DataFrame:
        with open('output.txt', 'a') as file:
            acquired = pd.DataFrame()
            for url in urls:
                new_df = self._get_new_urls_from_url(url, file)
                self._sources_db.insert_sources(new_df)  # TODO may be update not insert
                acquired = pd.concat([acquired, new_df])
            acquired = acquired[acquired[TYPE_ID] != int(self._sources_db.get_type_id('pdf'))]
            return acquired

    def initial_data_acquisition(self) -> None:
        """
        This method is responsible for the initial data acquisition. It retrieves the initial set of urls from the
        sources database and passes them to the web crawler and the web scraper.
        """

        urls_df = self._sources_db.get_all_non_banned_non_static_non_pdf_sources_as_dataframe()
        print('urls_df -------------------------------------------------------------------------')
        print(urls_df)
        if urls_df.empty:
            return
        to_scrape = pd.concat(
            [urls_df[urls_df[CRAWL_ONLY] == 0], self._sources_db.get_all_static_sources_as_dataframe()])
        self._scrape_and_update_sources(to_scrape)
        self.acquire_data(urls_df)

    def _is_banned(self, ws, new_url, banned) -> bool:
        if not ws.does_html_contain_substrs(BRNO_SUBSTRS):
            self._sources_db.add_banned_source(new_url, arrow.now().format(DATE_FORMAT))
            banned.append(new_url)
            return True
        return False

    def _update_existing_urls(self, existing_urls) -> None:
        """
        This method updates the existing urls in the sources' database. It sets the date_added to current date.
        """
        self._sources_db.update_existing_urls_date(existing_urls, arrow.now().format(DATE_FORMAT))

    def _scrape_and_update_sources(self, to_scrape: pd.DataFrame) -> None:
        with open('output.txt', 'a') as file:  # TODO just scrape them
            for url in to_scrape[URL]:
                ws = WebScraper(url)
                if self._is_banned(ws, url, []):
                    continue
                for t in ws.get_clean_texts():
                    content = get_parsed_content(t)
                    file.write(
                        url + '---------------------------------------------------------------------------------------------------------------------' + '\n')
                    file.write(ws.get_clean_texts() + '\n')
                    type_name = content.record_type
                    to_scrape.loc[to_scrape[URL] == url, TYPE_ID] = self._sources_db.get_type_id(type_name)
                    to_scrape.loc[to_scrape[URL] == url, DATE_SCRAPED] = arrow.now().format(DATE_FORMAT)
        self._sources_db.update_sources(to_scrape)

    @staticmethod
    def _remove_banned(banned, extend_df):
        extend_df = extend_df[~extend_df[URL].isin(banned)]
        for ban in banned:
            extend_df = extend_df[~extend_df[URL].str.contains(ban, regex=False)]
        return extend_df

    def _handle_pdf(self, url, parent_url):
        if 'gotobrno' in parent_url:
            self._sources_db.add_source(url, arrow.now().format(DATE_FORMAT), None, None,
                                        int(self._sources_db.get_type_id('pdf')))

    def _process_non_crawl_only(self, new_url, ws, file):
        for t in ws.get_clean_texts():
            content = get_parsed_content(t)
            file.write(
                new_url + '---------------------------------------------------------------------------------------------------------------------' + '\n')
            file.write(ws.get_clean_texts() + '\n')
            type_id = self._sources_db.get_type_id(content.record_type)
        return False, type_id, arrow.now().format(DATE_FORMAT)  # TODO

    def _get_new_urls_from_url(self, url, file) -> pd.DataFrame:
        new_urls = self._crawl_url(url, self._sources_db.get_all_parents())
        if new_urls.empty:
            return new_urls
        new_urls = self._remove_banned(self._sources_db.get_banned_urls(), new_urls)
        new_urls[DATE_SCRAPED] = None

        print('URL: ' + url)
        print('EXTEND DF:')
        print(new_urls)
        new_urls = self._process_new_urls(new_urls, url, file)
        # TODO insert into vecDB - do it directly in the parser??
        return new_urls

    def _process_new_urls(self, new_urls, parent_url, file) -> (pd.DataFrame, list[str]):
        banned = []
        for new_url in new_urls[URL]:
            if (new_url[-4:] == '.pdf') or (new_url[-4:] == '.PDF'):
                self._handle_pdf(new_url, parent_url)
                banned.append(new_url)
                continue
                # TODO get insides of pdf to vecDB
            print(new_url)
            ws = WebScraper(new_url)
            if not self._is_banned(ws, new_url, banned):
                if ws.is_crawl_only():
                    type_id = int(self._sources_db.get_type_id(get_content_type(ws.html)))
                    new_urls.loc[new_urls[URL] == new_url, [CRAWL_ONLY, TYPE_ID]] = [True, type_id]
                else:
                    crawl_only, type_id, date_scraped = self._process_non_crawl_only(new_url, ws, file)
                    new_urls.loc[new_urls[URL] == new_url, [CRAWL_ONLY, DATE_SCRAPED, TYPE_ID]] = [crawl_only,
                                                                                                   date_scraped,
                                                                                                   type_id]
        new_urls = self._remove_banned(banned, new_urls)
        return new_urls


if __name__ == '__main__':
    sources = SourcesDB()
    dam = DataAcquisitionManager(sources)
    dam.initial_data_acquisition()
