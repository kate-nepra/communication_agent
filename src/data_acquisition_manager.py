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
        extend_df.to_csv('extend_df.csv', index=False)
        existing_urls = self._sources_db.get_existing_urls_from_list(extend_df[URL].values)
        if existing_urls:
            self._update_existing_urls(existing_urls)
        return extend_df[~extend_df[URL].isin(existing_urls)]

    def acquire_data(self,
                     urls_df) -> None:  # TODO chci crawlnout určitý typ, ten pak updatnout a scrapenout které nejsou crawl only ale zároveň to vzít z DB??
        """
        This method is the main entry point for the data acquisition process. It retrieves urls from the sources database
        and passes them to the web crawler and the web scraper.
        """

        crawl_only_df = urls_df[urls_df[CRAWL_ONLY] == 1]
        acquired_df = self._process_url_df(urls_df)
        print('acquired_df -------------------------------------------------------------------------')
        print(acquired_df)
        self._process_url_df(acquired_df)
        not_crawl_only_df = urls_df[urls_df[CRAWL_ONLY] == 0]
        with open('output.txt',
                  'a') as file:  # TODO just scrape them and get new urls, that are to be appended to acquired - ONLY INITIAL ACQUISITION
            for url in not_crawl_only_df[URL]:
                ws = WebScraper(url)
                if not ws.does_html_contain_substrs(BRNO_SUBSTRS):
                    self._sources_db.add_banned_source(url, arrow.now().format(DATE_FORMAT))
                    continue
                content = get_parsed_content(ws.get_clean_text())
                file.write(
                    url + '---------------------------------------------------------------------------------------------------------------------' + '\n')
                file.write(ws.get_clean_text() + '\n')
                type_name = content.record_type
                not_crawl_only_df.loc[not_crawl_only_df[URL] == url, TYPE_ID] = self._sources_db.get_type_id(type_name)
                not_crawl_only_df.loc[not_crawl_only_df[URL] == url, DATE_SCRAPED] = arrow.now().format(DATE_FORMAT)
                # update SQL DB

    def _process_url_df(self, crawl_only_df):
        with open('output.txt', 'a') as file:
            acquired = pd.DataFrame()
            for url in crawl_only_df[URL]:
                extend_df = self._crawl_url(url, self._sources_db.get_all_parents())
                if extend_df.empty:
                    continue
                banned = self._sources_db.get_banned_urls()
                extend_df = self._remove_banned(banned, extend_df)
                banned = []
                print('URL: ' + url)
                print('EXTEND DF:')
                print(extend_df)
                for new_url in extend_df[URL]:
                    print(new_url)
                    ws = WebScraper(new_url)
                    if not ws.does_html_contain_substrs(BRNO_SUBSTRS):
                        self._sources_db.add_banned_source(new_url, arrow.now().format(DATE_FORMAT))
                        banned.append(new_url)
                    else:
                        if ws.is_crawl_only():
                            print('CRAWL ONLY ' + new_url)
                            extend_df.loc[extend_df[URL] == new_url, CRAWL_ONLY] = True
                            type_name = get_content_type(ws.html)
                        else:
                            extend_df.loc[extend_df[URL] == new_url, CRAWL_ONLY] = False
                            content = get_parsed_content(ws.get_clean_text())
                            file.write(
                                new_url + '---------------------------------------------------------------------------------------------------------------------' + '\n')
                            file.write(ws.get_clean_text() + '\n')
                            type_name = content.record_type
                        extend_df.loc[extend_df[URL] == new_url, DATE_SCRAPED] = arrow.now().format(DATE_FORMAT)
                        # TODO insert into vecDB - do it directly in the parser??
                        extend_df.loc[extend_df[URL] == new_url, TYPE_ID] = int(self._sources_db.get_type_id(type_name))
                extend_df = self._remove_banned(banned, extend_df)
                acquired = pd.concat([acquired, extend_df])
                self._sources_db.insert_sources(extend_df)  # TODO may be update not insert
            return acquired

    def initial_data_acquisition(self) -> None:
        """
        This method is responsible for the initial data acquisition. It retrieves the initial set of urls from the
        sources database and passes them to the web crawler and the web scraper.
        """

        urls_df = self._sources_db.get_all_non_banned_sources_as_dataframe()
        if urls_df.empty:
            return
        self.acquire_data(urls_df)

    def _update_existing_urls(self, existing_urls) -> None:
        """
        This method updates the existing urls in the sources' database. It sets the date_added to current date.
        """
        self._sources_db.update_existing_urls_date(existing_urls, arrow.now().format(DATE_FORMAT))

    @staticmethod
    def _remove_banned(banned, extend_df):
        extend_df = extend_df[~extend_df[URL].isin(banned)]
        for ban in banned:
            extend_df = extend_df[~extend_df[URL].str.contains(ban)]
        return extend_df


if __name__ == '__main__':
    sources = SourcesDB()
    dam = DataAcquisitionManager(sources)
    dam.initial_data_acquisition()
