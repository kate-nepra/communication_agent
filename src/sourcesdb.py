import logging

import mysql
import pandas as pd
from mysqlx import Error
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Date, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, declarative_base

from constants import URL, DATE_ADDED, CRAWL_ONLY, PARENT, TYPE, TYPE_ID, DATE_SCRAPED, RECORD_TYPES_CSV, SOURCES_CSV, \
    BANNED_SOURCES_CSV, PARSED_SOURCES_CSV, CONTENT_TYPES_CSV

Base = declarative_base()
logger = logging.getLogger(__name__)


class RecordTypes(Base):
    __tablename__ = 'record_types'
    id = Column(Integer, primary_key=True, autoincrement=True)
    record_type = Column(String(255), unique=True, nullable=False)
    update_interval = Column(String(255), nullable=False)
    content_type_id = Column(Integer, ForeignKey('content_types.id'), nullable=False)
    content_type = relationship("ContentTypes")


class ContentTypes(Base):
    __tablename__ = 'content_types'
    id = Column(Integer, primary_key=True, autoincrement=True)
    content_type = Column(String(255), unique=True, nullable=False)


class ParsedSources(Base):
    __tablename__ = 'parsed_sources'
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(255), nullable=False)
    content = Column(String(5000), nullable=False)
    content_type_id = Column(Integer, ForeignKey('content_types.id'), nullable=False)
    content_type = relationship("ContentTypes")


def create_database(host="localhost", user="root", password="password", database="agent_sources"):
    connection = mysql.connector.connect(
        host=host,
        user=user,
        password=password
    )
    cursor = connection.cursor()
    query = f"CREATE DATABASE IF NOT EXISTS {database}"
    try:
        cursor.execute(query)
        logger.info("Database created successfully")
    except Error as err:
        logger.error(f"Error: '{err}'")


class Sources(Base):
    __tablename__ = 'sources'
    url = Column(String(255), primary_key=True, unique=True, nullable=False)
    date_added = Column(Date, nullable=False)
    date_scraped = Column(Date, nullable=True)
    banned = Column(Boolean, nullable=False, default=False)
    crawl_only = Column(Boolean, nullable=True, default=True)
    parent = Column(String(255), nullable=True)
    type_id = Column(Integer, ForeignKey('record_types.id'), nullable=True)
    record_type = relationship("RecordTypes")


class SourcesDB:
    def __init__(self, host="localhost", user="root", password="password", database="agent_sources"):
        self.engine = create_engine(f"mysql+mysqlconnector://{user}:{password}@{host}/{database}")
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def add_or_update_source(self, url: str, date_added: str, date_scraped: str, crawl_only: bool, parent: str,
                             type_id: int):
        """
        Adds or updates a source in the database.
        :param url: Primary key - url of the source.
        :param date_added: Date when the source was added.
        :param date_scraped: Date when the source was last scraped.
        :param crawl_only: Flag if the source is crawl only.
        :param parent: Parent of the source.
        :param type_id: Type of the source.
        :return:
        """
        source = Sources(url=url, date_added=date_added, date_scraped=date_scraped, crawl_only=crawl_only,
                         parent=parent, type_id=type_id)
        self.session.merge(source)
        self.session.commit()

    def add_sources(self, sources: list[tuple]):
        """
        Adds sources to the database.
        :param sources: Source list with the following columns: url, date_added, crawl_only, parent, type_id.
        :return:
        """
        source_objects = [Sources(url=s[0], date_added=s[1], crawl_only=s[2], parent=s[3], type_id=s[4]) for s in
                          sources]
        self.session.add_all(source_objects)
        self.session.commit()

    def add_type(self, record_type: str, update_interval: str, content_type_id: int):
        """
        Adds a record type to the database.
        :param record_type: Type name.
        :param update_interval: The interval of the type.
        :param content_type_id: The id of the content type.
        :return:
        """
        record_type = RecordTypes(record_type=record_type, update_interval=update_interval,
                                  content_type_id=content_type_id)
        self.session.add(record_type)
        self.session.commit()

    def add_types(self, record_types: list[tuple]) -> None:
        """Adds record types to the database."""
        type_objects = [RecordTypes(record_type=t[0], update_interval=t[1], content_type_id=t[2]) for t in record_types]
        self.session.add_all(type_objects)
        self.session.commit()

    def get_type_id(self, type_name: str) -> int:
        """ Returns the id of the given type name."""
        record_type = self.session.query(RecordTypes).filter(RecordTypes.record_type == type_name).first()
        return record_type.id

    def insert_sources_from_csv(self, file_path: str) -> None:
        """Inserts sources from given csv file."""
        data = pd.read_csv(file_path)
        data[TYPE_ID] = data[TYPE].apply(lambda x: self.get_type_id(x))
        data = data[[URL, DATE_ADDED, CRAWL_ONLY, PARENT, TYPE_ID]]
        csv_sources = [tuple(row) for row in data.values]
        self.add_sources(csv_sources)

    def insert_types_from_csv(self, file_path: str) -> None:
        """Inserts record types from given csv file."""
        data = pd.read_csv(file_path)
        record_types = [tuple(row) for row in data.values]
        self.add_types(record_types)

    def insert_banned_sources_from_csv(self, file_path: str) -> None:
        """Inserts banned sources from given csv file."""
        data = pd.read_csv(file_path)
        for index, row in data.iterrows():
            self.add_or_update_banned_source(row[URL], row[DATE_ADDED])

    def insert_parsed_sources_from_csv(self, file_path: str) -> None:
        """Inserts parsed sources from given csv file."""
        data = pd.read_csv(file_path)
        parsed_sources = [tuple(row) for row in data.values]
        self.add_parsed_sources(parsed_sources)

    def get_all_non_banned_non_static_non_pdf_sources_as_dataframe(self) -> pd.DataFrame:
        """Returns all sources that are not banned, not static and not pdf as a DataFrame."""
        df = pd.read_sql(self.session.query(Sources).filter(Sources.banned.is_(False)).filter(
            Sources.record_type.has(RecordTypes.record_type != 'static')).filter(
            Sources.record_type.has(RecordTypes.record_type != 'pdf')).statement, self.session.bind)
        return df

    def get_all_sources_as_dataframe(self) -> pd.DataFrame:
        """Returns all sources as a DataFrame."""
        df = pd.read_sql(self.session.query(Sources).statement, self.session.bind)
        return df

    def get_all_static_sources_as_dataframe(self) -> pd.DataFrame:
        """Returns all static sources as a DataFrame."""
        df = pd.read_sql(self.session.query(Sources).filter(
            Sources.record_type.has(RecordTypes.record_type == 'static')).statement, self.session.bind)
        return df

    def get_all_parents(self) -> list[str]:
        """Returns list with all parents."""
        parents = self.session.query(Sources.parent).distinct().all()
        return [parent for parent, in parents]

    def get_existing_urls_from_list(self, url_list: list[str]) -> list[str]:
        """Returns the existing urls from the list."""
        query = self.session.query(Sources.url).filter(Sources.url.in_(url_list)).distinct().all()
        return [url[0] for url in query]

    def update_existing_urls_date(self, existing_urls: list[str], date_added: str) -> None:
        """Updates the date_added of the existing urls."""
        self.session.query(Sources).filter(Sources.url.in_(existing_urls)).update({Sources.date_added: date_added},
                                                                                  synchronize_session=False)
        self.session.commit()

    def insert_sources(self, extend_df: pd.DataFrame) -> None:
        """
        Inserts the sources in the database.
        :param extend_df: DataFrame with the sources to insert, the columns are: url, date_added, date_scraped, crawl_only, parent, type_id.
        :return:
        """
        for index, row in extend_df.iterrows():
            source = Sources(
                url=row[URL] if len(row[URL]) <= 255 else row[URL][:255],
                date_added=row[DATE_ADDED],
                date_scraped=row[DATE_SCRAPED],
                crawl_only=row[CRAWL_ONLY],
                parent=row[PARENT],
                type_id=row[TYPE_ID]
            )
            self.session.add(source)
        self.session.commit()

    def insert_or_update_sources(self, extend_df: pd.DataFrame) -> None:
        """
        Inserts or updates the sources in the database.
        :param extend_df: DataFrame with the sources to insert or update, the columns are: url, date_added, date_scraped, crawl_only, parent, type_id.
        :return:
        """
        for index, row in extend_df.iterrows():
            source = Sources(
                url=row[URL] if len(row[URL]) <= 255 else row[URL][:255],
                date_added=row[DATE_ADDED],
                date_scraped=row[DATE_SCRAPED],
                crawl_only=row[CRAWL_ONLY],
                parent=row[PARENT],
                type_id=row[TYPE_ID]
            )
            self.session.merge(source)
        self.session.commit()

    def update_sources(self, extend_df: pd.DataFrame) -> None:
        """
        Updates the sources in the database.
        :param extend_df: DataFrame with the sources to update, the columns are: url, date_added, date_scraped, crawl_only, parent, type_id.
        :return:
        """
        for index, row in extend_df.iterrows():
            self.session.query(Sources).filter(Sources.url == row[URL]).update({
                Sources.date_added: row[DATE_ADDED],
                Sources.date_scraped: row[DATE_SCRAPED],
                Sources.crawl_only: row[CRAWL_ONLY],
                Sources.parent: row[PARENT],
                Sources.type_id: row[TYPE_ID]
            }, synchronize_session=False)
        self.session.commit()

    def add_or_update_banned_source(self, banned_source: str, date_added: str) -> None:
        """Adds or updates a banned source in the database."""
        source = Sources(url=banned_source, date_added=date_added, banned=True)
        self.session.merge(source)
        self.session.commit()

    def get_banned_urls(self) -> list:
        """Returns all banned urls."""
        banned_urls = self.session.query(Sources.url).filter(Sources.banned.is_(True)).all()
        return [url for url, in banned_urls]

    def get_all_non_crawl_only_not_banned_sources_by_type(self, type_name: str) -> pd.DataFrame:
        """Returns all sources that are not crawl only and not banned of given type."""
        return pd.read_sql(
            self.session.query(Sources).filter(Sources.record_type.has(RecordTypes.record_type == type_name)).filter(
                Sources.banned.is_(False)).filter(Sources.crawl_only.is_(False)).statement,
            self.session.bind)

    def add_parsed_sources(self, parsed_sources: list[tuple]) -> None:
        """Adds parsed sources to the database."""
        source_objects = [ParsedSources(url=s[0], content_type_id=s[1], content=s[2]) for s in parsed_sources]
        self.session.add_all(source_objects)
        self.session.commit()

    def add_parsed_source(self, url: str, content: str) -> None:
        """Adds a parsed source to the database."""
        source = ParsedSources(url=url, content=content)
        self.session.add(source)
        self.session.commit()

    def get_all_pdf_urls(self) -> list:
        """Returns all pdf urls."""
        pdf_urls = self.session.query(Sources.url).filter(
            Sources.record_type.has(RecordTypes.record_type == 'pdf')).all()
        return [url for url, in pdf_urls]

    def get_all_parsed_sources_contents(self) -> list[str]:
        """Returns all parsed sources contents."""
        parsed_sources = self.session.query(ParsedSources.content).all()
        return [content for content, in parsed_sources]

    def get_all_parsed_sources_contents_by_type(self, type_name: str) -> list[str]:
        """Returns all parsed sources contents of given type."""
        parsed_sources = self.session.query(ParsedSources.content).filter(
            ParsedSources.content_type.has(ContentTypes.content_type == type_name)).all()
        return [content for content, in parsed_sources]

    def insert_content_types_from_csv(self, file_path: str) -> None:
        """Inserts content types from given csv file."""
        data = pd.read_csv(file_path)
        content_types = [tuple(row) for row in data.values]
        self.add_content_types(content_types)

    def add_content_types(self, content_types):
        """Adds content types to the database."""
        type_objects = [ContentTypes(content_type=t[0]) for t in content_types]
        self.session.add_all(type_objects)
        self.session.commit()


if __name__ == "__main__":
    create_database()
    s_db = SourcesDB()
    s_db.insert_content_types_from_csv(CONTENT_TYPES_CSV)
    s_db.insert_types_from_csv(RECORD_TYPES_CSV)
    s_db.insert_sources_from_csv(SOURCES_CSV)
    s_db.insert_banned_sources_from_csv(BANNED_SOURCES_CSV)
    s_db.insert_parsed_sources_from_csv(PARSED_SOURCES_CSV)
