import mysql.connector
from mysql.connector import Error
import pandas as pd
import logging

ID = 'id'
URL = 'url'
DATE_ADDED = 'date_added'
CRAWL_ONLY = 'crawl_only'
PARENT = 'parent'
TYPE = 'record_type'
TYPE_ID = 'type_id'
UPDATE_INTERVAL = 'update_interval'

logger = logging.getLogger(__name__)


class SourcesDB:
    def __init__(self, host="localhost", user="root", password="password", database="agent_sources"):
        self.host = host
        self.user = user
        self.password = password
        self.database = database

        self.create_database()
        self.connection = self.create_db_connection()
        self.cursor = self.connection.cursor()
        self.create_types_table()
        self.create_sources_table()

    def create_database(self):
        connection = mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password
        )
        cursor = connection.cursor()
        query = f"CREATE DATABASE IF NOT EXISTS {self.database}"
        try:
            cursor.execute(query)
            logger.info("Database created successfully")
        except Error as err:
            logger.error(f"Error: '{err}'")

    def create_db_connection(self):
        return mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database
        )

    def create_sources_table(self):
        create_sources_table = f"""
        CREATE TABLE IF NOT EXISTS  sources(
          {ID} INT PRIMARY KEY AUTO_INCREMENT,
            {URL} VARCHAR(255) NOT NULL UNIQUE,
            {DATE_ADDED} DATE NOT NULL,
            {CRAWL_ONLY} BOOLEAN NOT NULL,
            {PARENT} VARCHAR(255),
            {TYPE_ID} INT NOT NULL,
            FOREIGN KEY ({TYPE_ID}) REFERENCES record_types(id)
        );
        """
        self.cursor.execute(create_sources_table)
        self.connection.commit()

    def create_types_table(self):
        create_types_table = f"""
        CREATE TABLE IF NOT EXISTS  record_types(
                {ID} INT PRIMARY KEY AUTO_INCREMENT,
                {TYPE} VARCHAR(255) NOT NULL UNIQUE,
                {UPDATE_INTERVAL} VARCHAR(255) NOT NULL
            );
            """
        self.cursor.execute(create_types_table)
        self.connection.commit()

    def add_source(self, url, date_added, crawl_only, parent, record_type):
        add_one_line_query = f"""
            INSERT INTO sources ({URL}, {DATE_ADDED}, {CRAWL_ONLY}, {PARENT}, {TYPE_ID})
            SELECT * FROM (SELECT %s, %s, %s, %s, %s) AS tmp
            WHERE NOT EXISTS (
                SELECT {URL} FROM sources WHERE {URL} = %s
            ) LIMIT 1;
            """
        self.cursor.execute(add_one_line_query, (url, date_added, crawl_only, parent, record_type, url))
        self.connection.commit()

    def add_sources(self, sources):
        add_many_lines_query = f"""
            INSERT INTO sources ({URL}, {DATE_ADDED}, {CRAWL_ONLY}, {PARENT}, {TYPE_ID})
            SELECT * FROM (SELECT %s, %s, %s, %s, %s) AS tmp
            WHERE NOT EXISTS (
                SELECT {URL} FROM sources WHERE {URL} = %s
            ) LIMIT 1
        """
        self.cursor.executemany(add_many_lines_query, [(s[0], s[1], s[2], s[3], s[4], s[0]) for s in sources])
        self.connection.commit()

    def add_type(self, record_type, update_interval):
        add_one_line_query = f"""
            INSERT INTO record_types ({TYPE}, {UPDATE_INTERVAL})
            SELECT * FROM (SELECT %s, %s) AS tmp
            WHERE NOT EXISTS (
                SELECT {TYPE} FROM record_types WHERE {TYPE} = %s
            ) LIMIT 1;
            """
        self.cursor.execute(add_one_line_query, (record_type, update_interval, record_type))
        self.connection.commit()

    def add_types(self, record_types):
        add_many_lines_query = f"""
            INSERT INTO record_types ({TYPE}, {UPDATE_INTERVAL})
            SELECT * FROM (SELECT %s, %s) AS tmp
            WHERE NOT EXISTS (
                SELECT {TYPE} FROM record_types WHERE {TYPE} = %s
            ) LIMIT 1
        """
        # Modify the query to ensure it has the correct number of placeholders
        self.cursor.executemany(add_many_lines_query, [(t[0], t[1], t[0]) for t in record_types])
        self.connection.commit()

    def get_types(self):
        query = f"SELECT * FROM record_types"
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        return result

    def get_type_id(self, type_name):
        query = f"""SELECT {ID} FROM record_types WHERE {TYPE} = '{type_name}'"""
        self.cursor.execute(query)
        result = self.cursor.fetchone()
        if result:
            return result[0]
        else:
            return None

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

    def get_next_source(self, _id=0):
        query = f"SELECT * FROM sources WHERE {ID} > {_id} ORDER BY {ID} LIMIT 1"
        self.cursor.execute(query, (ID,))
        result = self.cursor.fetchone()
        return result

    def get_source_by_id(self, _id):
        query = f"SELECT * FROM sources WHERE {ID} = {_id}"
        self.cursor.execute(query)
        result = self.cursor.fetchone()
        return result

    def get_all_sources(self):
        query = f"SELECT * FROM sources"
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        return result

    def get_sources_by_type_id(self, record_type_id):
        query = f"SELECT {URL} FROM sources WHERE {TYPE_ID} = {record_type_id}"
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        return result

    def drop_all_tables(self):
        query = f"DROP TABLE sources, record_types"
        self.cursor.execute(query)
        self.connection.commit()

    def close_connection(self):
        self.connection.close()


if __name__ == '__main__':
    sources = SourcesDB()
    # sources.drop_all_tables()
    sources.insert_types_from_csv('./../data/record_types.csv')
    print(sources.get_types())
    sources.insert_sources_from_csv('./../data/sources.csv')
    print(sources.get_all_sources())
    sources.close_connection()
