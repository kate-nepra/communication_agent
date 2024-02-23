import logging

import arrow
import mysql.connector
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Date, ForeignKey
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from constants import ID, URL, DATE_ADDED, CRAWL_ONLY, PARENT, TYPE, UPDATE_INTERVAL, TYPE_ID, BANNED, DATE_FORMAT
import pandas as pd

Base = declarative_base()
logger = logging.getLogger(__name__)


class RecordTypes(Base):
    __tablename__ = 'record_types'
    id = Column(Integer, primary_key=True, autoincrement=True)
    record_type = Column(String(255), unique=True, nullable=False)
    update_interval = Column(String(255), nullable=False)


class Sources(Base):
    __tablename__ = 'sources'
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(255), unique=True, nullable=False)
    date_added = Column(Date, nullable=False)
    date_scraped = Column(Date, nullable=True)
    banned = Column(Boolean, nullable=False, default=False)
    crawl_only = Column(Boolean, default=True)
    parent = Column(String(255), nullable=True)
    type_id = Column(Integer, ForeignKey('record_types.id'), nullable=True)
    record_type = relationship("RecordTypes")


class SourcesDB:
    def __init__(self, host="localhost", user="root", password="password", database="agent_sources"):
        self.engine = create_engine(f"mysql+mysqlconnector://{user}:{password}@{host}/{database}")
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def add_source(self, url, date_added, crawl_only, parent, type_id):
        source = Sources(url=url, date_added=date_added, crawl_only=crawl_only, parent=parent, type_id=type_id)
        self.session.add(source)
        self.session.commit()

    def add_sources(self, sources):
        source_objects = [Sources(url=s[0], date_added=s[1], crawl_only=s[2], parent=s[3], type_id=s[4]) for s in
                          sources]
        self.session.add_all(source_objects)
        self.session.commit()

    def add_type(self, record_type, update_interval):
        record_type = RecordTypes(record_type=record_type, update_interval=update_interval)
        self.session.add(record_type)
        self.session.commit()

    def add_types(self, record_types):
        type_objects = [RecordTypes(record_type=t[0], update_interval=t[1]) for t in record_types]
        self.session.add_all(type_objects)
        self.session.commit()

    def insert_blacklisted_sources(self):
        for url in BANNED:
            self.add_banned_source(url, arrow.now().format(DATE_FORMAT))

    def get_types(self):
        return self.session.query(RecordTypes).all()

    def get_type_id(self, type_name) -> int:
        record_type = self.session.query(RecordTypes).filter(RecordTypes.record_type == type_name).first()
        return record_type.id

    def insert_sources_from_csv(self, file_path):
        data = pd.read_csv(file_path)
        data[TYPE_ID] = data[TYPE].apply(lambda x: self.get_type_id(x))
        data = data[[URL, DATE_ADDED, CRAWL_ONLY, PARENT, TYPE_ID]]
        csv_sources = [tuple(row) for row in data.values]
        self.add_sources(csv_sources)

    def insert_types_from_csv(self, file_path):
        data = pd.read_csv(file_path)
        record_types = [tuple(row) for row in data.values]
        self.add_types(record_types)

    def get_all_sources(self):
        return self.session.query(Sources).all()

    def get_all_non_banned_sources_as_dataframe(self):
        df = pd.read_sql(self.session.query(Sources).filter(Sources.banned == False).statement, self.engine)
        return df

    def get_all_sources_as_dataframe(self):
        df = pd.read_sql(self.session.query(Sources).statement, self.session.bind)
        return df

    def get_all_parents(self) -> list[str]:
        parents = self.session.query(Sources.parent).distinct().all()
        return [parent for parent, in parents]

    def get_existing_urls_from_list(self, url_list):
        query = self.session.query(Sources.url).filter(Sources.url.in_(url_list)).distinct().all()
        return [url[0] for url in query]

    def update_existing_urls_date(self, existing_urls: list[str], date_added: str):
        self.session.query(Sources).filter(Sources.url.in_(existing_urls)).update({Sources.date_added: date_added},
                                                                                  synchronize_session=False)
        self.session.commit()

    def insert_sources(self, extend_df: pd.DataFrame):
        for index, row in extend_df.iterrows():
            source = Sources(
                url=row[URL],
                date_added=row[DATE_ADDED],
                crawl_only=row[CRAWL_ONLY],
                parent=row[PARENT],
                type_id=row[TYPE_ID]
            )
            self.session.add(source)
        self.session.commit()

    def add_banned_source(self, banned_source: str, date_added: str):
        print(f"Adding banned source: {banned_source}")
        self.session.add(Sources(url=banned_source, date_added=date_added, banned=True))
        self.session.commit()

    def get_banned_urls(self) -> list:
        banned_urls = self.session.query(Sources.url).filter(Sources.banned == True).all()
        return [url for url, in banned_urls]


if __name__ == '__main__':
    sources = SourcesDB()
    sources.insert_types_from_csv('./../data/record_types.csv')
    sources.insert_sources_from_csv('./../data/sources.csv')
    sources.insert_blacklisted_sources()
