import logging

import mysql
import mysql.connector
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Date, ForeignKey, Table, and_
from sqlalchemy.orm import sessionmaker, relationship, declarative_base, aliased
from sqlalchemy.exc import IntegrityError
from src.data_acquisition.constants import TYPE_IDS, TYPE, URL, DATE_ADDED, CRAWL_ONLY, PARENT, DATE_PARSED, STATIC, \
    PDF, ENCODED_CONTENT
from src.data_acquisition.sources_store.constants import RECORD_TYPES_CSV, SOURCES_CSV, BANNED_SOURCES_CSV, \
    CONTENT_TYPES_CSV, PARSED_SOURCES_CSV, HOST, DB_USER, PASSWORD, DATABASE

Base = declarative_base()
logger = logging.getLogger(__name__)
load_dotenv()


def create_database(host=HOST, user=DB_USER, password=PASSWORD, database=DATABASE):
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
    except Exception as e:
        logger.error(f"Error: '{e}'")


class ContentTypes(Base):
    """Table for content types - event | base."""
    __tablename__ = 'content_types'
    id = Column(Integer, primary_key=True, autoincrement=True)
    content_type = Column(String(255), unique=True, nullable=False)


class ParsedSources(Base):
    """Table for parsed sources for storing chunks."""
    __tablename__ = 'parsed_sources'
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(255), nullable=False)
    content = Column(String(5000), nullable=False)
    content_type_id = Column(Integer, ForeignKey('content_types.id'), nullable=False)
    content_type = relationship("ContentTypes")


source_record_types = Table(
    'source_record_types',
    Base.metadata,
    Column('source_id', String(255), ForeignKey('sources.url')),
    Column('record_type_id', Integer, ForeignKey('record_types.id'))
)


class RecordTypes(Base):
    """Table for record types."""
    __tablename__ = 'record_types'
    id = Column(Integer, primary_key=True, autoincrement=True)
    record_type = Column(String(255), unique=True, nullable=False)
    update_interval = Column(String(255), nullable=False)
    content_type_id = Column(Integer, ForeignKey('content_types.id'), nullable=False)
    content_type = relationship("ContentTypes")


class Sources(Base):
    """Main table for storing sources and parameters."""
    __tablename__ = 'sources'
    url = Column(String(255), primary_key=True, unique=True, nullable=False)
    date_added = Column(String(20), nullable=False)
    date_parsed = Column(String(20), nullable=True)
    banned = Column(Boolean, nullable=False, default=False)
    crawl_only = Column(Boolean, nullable=True, default=True)
    parent = Column(String(255), nullable=True)
    encoded_content = Column(String(255), nullable=True)
    record_types = relationship("RecordTypes", secondary=source_record_types)


class SourcesDB:
    """Class for handling the database with sources."""

    def __init__(self, host=HOST, user=DB_USER, password=PASSWORD, database=DATABASE):
        self.engine = create_engine(f"mysql+mysqlconnector://{user}:{password}@{host}/{database}")
        Base.metadata.create_all(self.engine)
        session = sessionmaker(bind=self.engine)
        self.session = session()

    def add_or_update_source(self, url: str, date_added: str, date_parsed: str, crawl_only: bool, parent: str,
                             type_ids: list, encoded_content: str = None):
        """
        Adds or updates a source in the database with multiple record types.
        :param url: Primary key - url of the source.
        :param date_added: Date when the source was added.
        :param date_parsed: Date when the source was last scraped.
        :param crawl_only: Flag if the source is crawl only.
        :param parent: Parent of the source.
        :param type_ids: List of type ids associated with the source.
        :param encoded_content: Encoded content of the source.
        :return:
        """
        source = Sources(url=url, date_added=date_added, date_parsed=date_parsed, crawl_only=crawl_only,
                         parent=parent, encoded_content=encoded_content)

        for type_id in type_ids:
            record_type = self.session.query(RecordTypes).filter_by(id=type_id).first()
            if record_type:
                source.record_types.append(record_type)

        self.session.merge(source)
        self.session.commit()

    def add_sources(self, sources: list[tuple]):
        """
        Adds sources and their record types to the database.
        :param sources: Source list with the following columns: url, date_added, crawl_only, parent, type_ids.
        """
        for source_data in sources:
            url, date_added, crawl_only, parent, type_ids = source_data
            new_source = Sources(url=url, date_added=date_added, crawl_only=crawl_only, parent=parent)

            for type_id in type_ids:
                record_type = self.session.query(RecordTypes).get(type_id)
                if record_type:
                    new_source.record_types.append(record_type)

            self.session.add(new_source)

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

    def add_types(self, record_types: list[tuple]):
        """Adds record types to the database."""
        type_objects = [RecordTypes(record_type=t[0], update_interval=t[1], content_type_id=t[2]) for t in record_types]
        self.session.add_all(type_objects)
        self.session.commit()

    def get_type_id(self, type_name: str) -> int:
        """ Returns the id of the given type name."""
        record_type = self.session.query(RecordTypes).filter(RecordTypes.record_type == type_name).first()
        if not record_type:
            raise ValueError(f"Type '{type_name}' not found in the database.")
        return record_type.id

    def insert_sources_from_csv(self, file_path: str):
        """Inserts sources from a given CSV file."""
        data = pd.read_csv(file_path)
        data[TYPE_IDS] = data.apply(lambda row: self.get_type_ids(row), axis=1)
        data = data[[URL, DATE_ADDED, CRAWL_ONLY, PARENT, TYPE_IDS]]
        csv_sources = [tuple(row) for row in data.values]
        self.add_sources(csv_sources)

    def get_type_ids(self, row: dict) -> list:
        """Get the IDs of record types for a source."""
        type_names = row[TYPE].split(', ')
        type_ids = []
        for type_name in type_names:
            type_id = self.get_type_id(type_name)
            if type_id is not None:
                type_ids.append(type_id)
        return type_ids

    def insert_types_from_csv(self, file_path: str):
        """Inserts record types from given csv file."""
        data = pd.read_csv(file_path)
        record_types = [tuple(row) for row in data.values]
        self.add_types(record_types)

    def insert_banned_sources_from_csv(self, file_path: str):
        """Inserts banned sources from given csv file."""
        data = pd.read_csv(file_path)
        for index, row in data.iterrows():
            self.add_or_update_banned_source(row[URL], row[DATE_ADDED])

    def insert_parsed_sources_from_csv(self, file_path: str):
        """Inserts parsed sources from given csv file."""
        data = pd.read_csv(file_path)
        parsed_sources = [tuple(row) for row in data.values]
        self.add_parsed_sources(parsed_sources)

    def get_all_non_banned_non_static_non_pdf_sources_as_dataframe(self) -> pd.DataFrame:
        """Returns all sources that are not banned, not static, and not pdf as a DataFrame."""

        query = self.session.query(Sources).filter(Sources.banned.is_(False))
        query = query.filter(~Sources.record_types.any(
            RecordTypes.record_type.in_([STATIC, PDF])
        ))
        df = pd.read_sql(query.statement, self.session.bind)
        return df

    def get_all_sources_as_dataframe(self) -> pd.DataFrame:
        """Returns all sources as a DataFrame."""
        df = pd.read_sql(self.session.query(Sources).statement, self.session.bind)
        return df

    def get_all_static_sources_as_dataframe(self) -> pd.DataFrame:
        """Returns all static sources as a DataFrame."""
        df = pd.read_sql(self.session.query(Sources).join(Sources.record_types).filter(
            RecordTypes.record_type == STATIC).statement, self.session.bind)
        return df

    def get_all_parents(self) -> list[str]:
        """Returns list with all parents."""
        parents = self.session.query(Sources.parent).distinct().all()
        return [parent for parent, in parents]

    def get_existing_urls_from_list(self, url_list: list[str]) -> list[str]:
        """Returns the existing urls from the list."""
        query = self.session.query(Sources.url).filter(Sources.url.in_(url_list)).distinct().all()
        return [str(url[0]) for url in query]

    def update_existing_urls_date(self, existing_urls: list[str], date_added: str):
        """Updates the date_added of the existing urls."""
        self.session.query(Sources).filter(Sources.url.in_(existing_urls)).update({Sources.date_added: date_added},
                                                                                  synchronize_session=False)
        self.session.commit()

    def insert_sources(self, extend_df: pd.DataFrame):
        """
        Inserts the sources in the database, including the association with record types.
        :param extend_df: DataFrame with the sources to insert, columns: url, date_added, date_parsed, crawl_only, parent, type_ids (list of record type IDs).
        """
        for index, row in extend_df.iterrows():
            source = Sources(
                url=row[URL] if len(row[URL]) <= 255 else row[URL][:255],
                date_added=row[DATE_ADDED],
                date_parsed=row[DATE_PARSED],
                crawl_only=row[CRAWL_ONLY],
                parent=row[PARENT]
            )

            record_type_ids = row[TYPE_IDS] if isinstance(row[TYPE_IDS], list) else [row[TYPE_IDS]]
            record_types = [self.session.query(RecordTypes).get(record_type_id) for record_type_id in record_type_ids]
            source.record_types.extend(record_types)

            self.session.add(source)

        self.session.commit()

    def insert_or_update_sources(self, extend_df: pd.DataFrame):
        """
        Inserts or updates the sources in the database.
        :param extend_df: DataFrame with the sources to insert or update, the columns are: url, date_added, date_parsed, crawl_only, parent, type_ids.
        """

        for index, row in extend_df.iterrows():
            type_ids = row[TYPE_IDS]
            if not type_ids:
                continue

            source = Sources(
                url=row[URL] if len(row[URL]) <= 255 else row[URL][:255],
                date_added=row[DATE_ADDED],
                date_parsed=row[DATE_PARSED],
                crawl_only=row[CRAWL_ONLY],
                parent=row[PARENT],
                encoded_content=row[ENCODED_CONTENT] if ENCODED_CONTENT in row else None
            )

            type_ids = type_ids if isinstance(type_ids, list) else [type_ids]
            for type_id in type_ids:
                record_type = self.session.query(RecordTypes).filter(RecordTypes.id == type_id).first()
                if record_type:
                    source.record_types.append(record_type)

            try:
                self.session.add(source)
                self.session.commit()
            except IntegrityError:
                self.session.rollback()

    def add_or_update_banned_source(self, banned_source: str, date_added: str):
        """Adds or updates a banned source in the database."""
        source = Sources(url=banned_source, date_added=date_added, banned=True)
        self.session.merge(source)
        self.session.commit()

    def get_banned_urls(self) -> list:
        """Returns all banned urls."""
        banned_urls = self.session.query(Sources.url).filter(Sources.banned.is_(True)).all()
        return [url for url, in banned_urls]

    def get_all_non_crawl_only_not_banned_sources_by_type(self, type_name: str) -> pd.DataFrame:
        """Returns all sources that are not crawl only, not banned, and of the given type."""
        record_types_alias = aliased(RecordTypes)
        query = self.session.query(Sources).join(Sources.record_types).join(record_types_alias).filter(
            and_(
                record_types_alias.record_type == type_name,
                Sources.banned.is_(False),
                Sources.crawl_only.is_(False)
            )
        )
        return pd.read_sql(query.statement, self.session.bind)

    def add_parsed_sources(self, parsed_sources: list[tuple]):
        """Adds parsed sources to the database."""
        source_objects = [ParsedSources(url=s[0], content=s[1], content_type_id=s[2]) for s in parsed_sources]
        self.session.add_all(source_objects)
        self.session.commit()

    def add_parsed_source(self, url: str, content: str, type_name: str):
        """Adds a parsed source to the database."""
        source = ParsedSources(url=url, content=content,
                               content_type_id=self.get_content_type_id_from_record_type_name(type_name))
        self.session.add(source)
        self.session.commit()

    def get_all_pdf_urls(self) -> list:
        """Returns all pdf urls."""
        record_types_alias = aliased(RecordTypes)
        pdf_urls = self.session.query(Sources.url).join(Sources.record_types).join(record_types_alias).filter(
            record_types_alias.record_type == PDF
        ).all()

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

    def insert_content_types_from_csv(self, file_path: str):
        """Inserts content types from given csv file."""
        data = pd.read_csv(file_path)
        content_types = [tuple(row) for row in data.values]
        self.add_content_types(content_types)

    def add_content_types(self, content_types: list):
        """Adds content types to the database."""
        type_objects = [ContentTypes(content_type=t[0]) for t in content_types]
        self.session.add_all(type_objects)
        self.session.commit()

    def get_content_type_id_from_record_type_name(self, type_name: str) -> int:
        """Returns the content type id of the given type name."""
        record_type = self.session.query(RecordTypes).filter(RecordTypes.record_type == type_name).first()
        return record_type.content_type_id

    def insert_or_update_source(self, url: str, date_added: str, date_parsed: str, crawl_only: bool, parent: str,
                                type_ids: list, encoded_content: str = None):
        """Inserts or updates a source in the database."""
        source = Sources(url=url, date_added=date_added, date_parsed=date_parsed, crawl_only=crawl_only,
                         parent=parent, encoded_content=encoded_content)
        logger.info(f"Inserting or updating source {url}, date_added: {date_added}, date_parsed: {date_parsed}, "
                    f"crawl_only: {crawl_only}, parent: {parent}, type_ids: {type_ids}, encoded_content: {encoded_content}")
        for type_id in type_ids:
            record_type = self.session.query(RecordTypes).filter_by(id=type_id).first()
            if record_type:
                source.record_types.append(record_type)
        self.session.merge(source)
        self.session.commit()

    def get_encoded_content(self, url: str) -> str:
        """Returns the encoded content of the source of the given url."""
        source = self.session.query(Sources).filter(Sources.url == url).first()
        if not source:
            return None
        return source.encoded_content

    def get_urls_by_type_and_date_parsed(self, type_name: str, date_parsed: str) -> list[str]:
        """Returns the urls of sources of the given type and date parsed."""
        record_types_alias = aliased(RecordTypes)
        query = self.session.query(Sources.url).join(Sources.record_types).join(record_types_alias).filter(
            and_(
                record_types_alias.record_type == type_name,
                Sources.date_parsed == date_parsed
            )
        )
        return [url for url, in query]

    def get_parsed_sources_contents_by_urls_and_content_type(self, urls: list[str], type_name: str) -> list[str]:
        """Returns the parsed sources contents of the given urls and content type."""
        type_id = self.get_content_type_id(type_name)
        query = self.session.query(ParsedSources.content).filter(
            and_(
                ParsedSources.url.in_(urls),
                ParsedSources.content_type_id == type_id
            )
        )
        return [content for content, in query]

    def get_content_type_id(self, type_name: str):
        """Returns the content type id of the given type name."""
        content_type = self.session.query(ContentTypes).filter(ContentTypes.content_type == type_name).first()
        return content_type.id

    def delete_outdated_parsed_sources(self, urls: list[str]):
        """Delete parsed sources by url if the date_parsed in sources is not today."""
        self.session.query(ParsedSources).filter(
            and_(
                ParsedSources.url.in_(urls),
                ParsedSources.url.notin_(self.get_urls_by_date_parsed())
            )
        ).delete()
        self.session.commit()

    def get_urls_by_date_parsed(self):
        """Returns the urls of sources where the date_parsed is today."""
        return [url for url, in self.session.query(Sources.url).filter(Sources.date_parsed == DATE_PARSED).all()]

    def get_urls_by_type(self, type_name):
        """Returns the urls of sources of the given type."""
        record_types_alias = aliased(RecordTypes)
        query = self.session.query(Sources.url).join(Sources.record_types).join(record_types_alias).filter(
            record_types_alias.record_type == type_name
        )
        return [url for url, in query]


def main():
    create_database()
    s_db = SourcesDB()
    s_db.insert_content_types_from_csv(CONTENT_TYPES_CSV)
    s_db.insert_types_from_csv(RECORD_TYPES_CSV)
    s_db.insert_sources_from_csv(SOURCES_CSV)
    s_db.insert_banned_sources_from_csv(BANNED_SOURCES_CSV)
    s_db.insert_parsed_sources_from_csv(PARSED_SOURCES_CSV)


if __name__ == "__main__":
    main()
