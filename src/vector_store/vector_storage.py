import json
import logging
import os
from datetime import datetime

import weaviate.classes.config as wcc
from sqlalchemy import null

from src.agents.api_agent import LlamaApiAgent, ApiAgent
from src.data_acquisition.content_processing.content_parsing import get_parsed_content_by_function_call
from src.data_acquisition.sources_store.sourcesdb import SourcesDB
import weaviate
from src.data_acquisition.data_retrieval.pdf_processing import PdfProcessor

logger = logging.getLogger(__name__)

BASE_SCHEMA_NAME = "BaseSchema"
EVENT_SCHEMA_NAME = "EventSchema"


class VectorStorage:
    def __init__(self):
        self.client = weaviate.connect_to_local()

    def create_schemas(self):
        self.delete_schema(BASE_SCHEMA_NAME)
        self.delete_schema(EVENT_SCHEMA_NAME)
        self.create_base_schema()
        self.create_event_schema()

    def close(self):
        self.client.close()

    def import_stringed_json_base(self, data: list[str]):
        """
        Imports data to Weaviate
        :param data: data to import
        :return: None
        """
        with self.client.batch.fixed_size(batch_size=50) as batch:
            counter = 0
            for d in data:
                try:
                    obj = eval(d)
                    properties = {
                        "header": obj["header"],
                        "record_type": obj["record_type"],
                        "brief": obj["brief"],
                        "text": obj["text"],
                        "url": obj["url"],
                        "date_fetched": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                        "address": obj["address"] if "address" in obj and obj["address"] is not null else "",
                    }
                    batch.add_object(
                        collection=BASE_SCHEMA_NAME,
                        properties=properties,
                    )

                    counter += 1
                    if counter % 50 == 0:
                        logger.info(f"Imported {counter} articles...")
                except Exception as e:
                    logger.error(f"Error while importing {d}: {e}")

    def import_stringed_json_event(self, data: list[str]):
        """
        Imports data to Weaviate
        :param data: data to import
        :return: None
        """
        with self.client.batch.fixed_size(batch_size=50) as batch:
            counter = 0
            for d in data:
                try:
                    obj = eval(d)
                    try:
                        dates = json.loads(obj["dates"])
                    except Exception as e:
                        logger.error(f"Error while parsing dates {obj['dates']}: {e}")
                        dates = []
                    properties = {
                        "header": obj["header"],
                        "record_type": obj["record_type"],
                        "brief": obj["brief"],
                        "text": obj["text"],
                        "url": obj["url"],
                        "date_fetched": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                        "address": obj["address"] if "address" in obj and obj["address"] is not null else "",
                        "dates": dates
                    }
                    batch.add_object(
                        collection=EVENT_SCHEMA_NAME,
                        properties=properties,
                    )

                    counter += 1
                    if counter % 50 == 0:
                        logger.info(f"Imported {counter} articles...")
                except Exception as e:
                    logger.error(f"Error while importing {d}: {e}")

    def delete_schema(self, name: str):
        self.client.collections.delete(name)

    def create_base_schema(self):
        """Creates base schema, that is used for static sources, places and all basic info."""
        self.client.collections.create(
            name=BASE_SCHEMA_NAME,
            vectorizer_config=wcc.Configure.Vectorizer.text2vec_transformers(),
            properties=[
                wcc.Property(name="header", data_type=wcc.DataType.TEXT),
                wcc.Property(name="record_type", data_type=wcc.DataType.TEXT),
                wcc.Property(name="brief", data_type=wcc.DataType.TEXT),
                wcc.Property(name="text", data_type=wcc.DataType.TEXT),
                wcc.Property(name="url", data_type=wcc.DataType.TEXT),
                wcc.Property(name="date_fetched", data_type=wcc.DataType.DATE),
                wcc.Property(name="address", data_type=wcc.DataType.TEXT),
            ]
        )

    def create_event_schema(self):
        """Creates event schema, that is used for events, like concerts, festivals etc."""
        self.client.collections.create(
            name=EVENT_SCHEMA_NAME,
            vectorizer_config=wcc.Configure.Vectorizer.text2vec_transformers(),
            properties=[
                wcc.Property(name="header", data_type=wcc.DataType.TEXT),
                wcc.Property(name="record_type", data_type=wcc.DataType.TEXT),
                wcc.Property(name="brief", data_type=wcc.DataType.TEXT),
                wcc.Property(name="text", data_type=wcc.DataType.TEXT),
                wcc.Property(name="url", data_type=wcc.DataType.TEXT),
                wcc.Property(name="date_fetched", data_type=wcc.DataType.DATE),
                wcc.Property(name="address", data_type=wcc.DataType.TEXT),
                wcc.Property(name="dates", data_type=wcc.DataType.OBJECT_ARRAY, nested_properties=[
                    wcc.Property(name="date", data_type=wcc.DataType.OBJECT, nested_properties=[
                        wcc.Property(name="start", data_type=wcc.DataType.DATE),
                        wcc.Property(name="end", data_type=wcc.DataType.DATE, optional=True)
                    ])
                ])])

    def query_base_schema(self, query: str):
        """
        Query the 'BaseSchema' collection in Weaviate based on a question.
        :return: The query results
        """

        collection = self.client.collections.get(EVENT_SCHEMA_NAME)
        print(collection)

        for item in collection.iterator(
                include_vector=True
                # If using named vectors, you can specify ones to include e.g. ['title', 'body'], or True to include all
        ):
            print("------------------------------")
            print(item.properties)
            print(item.vector)

        bases = self.client.collections.get(BASE_SCHEMA_NAME)

        response = bases.query.near_text(
            query=query,
            limit=5
        )
        print(response)


def setup_vector_store():
    vs = VectorStorage()
    source_db = SourcesDB()
    vs.create_schemas()
    contents = source_db.get_all_parsed_sources_contents_by_type('base')
    # vs.import_stringed_json_base(contents)
    contents = source_db.get_all_parsed_sources_contents_by_type('event')
    vs.import_stringed_json_event(contents)
    return vs


if __name__ == "__main__":
    vs = setup_vector_store()
    vs.query_base_schema("What is famous and nice bakery in Brno?")
    vs.close()
