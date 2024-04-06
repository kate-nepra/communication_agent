import logging
import os
from datetime import datetime

import weaviate.classes.config as wcc
from src.agents.api_agent import LlamaApiAgent, ApiAgent
from src.data_acquisition.content_processing.content_parsing import get_parsed_content_by_function_call
from src.data_acquisition.sources_store.sourcesdb import SourcesDB
import weaviate
from src.data_acquisition.data_retrieval.pdf_processing import PdfProcessor
from src.vector_store.constants_json_transformers import BASE_SCHEMA, EVENT_SCHEMA

logger = logging.getLogger(__name__)

BASE_SCHEMA_NAME = "BaseSchema"
EVENT_SCHEMA_NAME = "EventSchema"


class VectorStorage:
    def __init__(self, agent: ApiAgent):
        self.client = weaviate.connect_to_local()
        self.agent = agent

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
                obj = eval(d)
                print(obj)
                properties = {
                    "header": obj["header"],
                    "brief": obj["brief"],
                    "text": obj["text"],
                    "url": obj["url"],
                    "date_fetched": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                    "address": obj["address"] if "address" in obj else ""
                }
                batch.add_object(
                    collection=BASE_SCHEMA_NAME,
                    properties=properties,
                )

                counter += 1
                if counter % 50 == 0:
                    logger.info(f"Imported {counter} articles...")

    def import_stringed_json_event(self, data: list[str]):
        """
        Imports data to Weaviate
        :param data: data to import
        :return: None
        """
        with self.client.batch.fixed_size(batch_size=50) as batch:
            counter = 0
            for d in data:
                obj = eval(d)
                print(obj)
                properties = {
                    "header": obj["header"],
                    "brief": obj["brief"],
                    "text": obj["text"],
                    "url": obj["url"],
                    "date_fetched": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                    "address": obj["address"] if "address" in obj else "",
                    "dates": obj["dates"]
                }
                batch.add_object(
                    collection=EVENT_SCHEMA_NAME,
                    properties=properties,
                )

                counter += 1
                if counter % 50 == 0:
                    logger.info(f"Imported {counter} articles...")

    def import_base_pdf_from_path(self, pdf_path):
        """
        Imports data to Weaviate
        :param pdf_path: path to the pdf file
        :return: None
        """
        file_name = pdf_path.split("/")[-1]
        processor = PdfProcessor([pdf_path])
        chunks = processor.get_chunks()
        schemas = [get_parsed_content_by_function_call(self.agent, file_name, content) for content in chunks]
        collection = self.client.collections.get(BASE_SCHEMA_NAME)

        with collection.batch.dynamic() as batch:
            for s in schemas:
                batch.add_object(
                    properties=s,
                )

    def delete_schema(self, name: str):
        self.client.collections.delete(name)

    def create_base_schema(self):
        """Creates base schema, that is used for static sources, places and all basic info."""
        self.client.collections.create(
            name=BASE_SCHEMA_NAME,
            vectorizer_config=wcc.Configure.Vectorizer.text2vec_transformers(),
            properties=[
                wcc.Property(name="header", data_type=wcc.DataType.TEXT),
                wcc.Property(name="record_type", data_type=wcc.DataType.TEXT,
                             moduleConfig={"text2vec-transformers": {"vectorizePropertyName": "true"}}),
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
                wcc.Property(name="record_type", data_type=wcc.DataType.TEXT,
                             moduleConfig={"text2vec-transformers": {"vectorizePropertyName": "true"}}),
                wcc.Property(name="brief", data_type=wcc.DataType.TEXT),
                wcc.Property(name="text", data_type=wcc.DataType.TEXT),
                wcc.Property(name="url", data_type=wcc.DataType.TEXT),
                wcc.Property(name="date_fetched", data_type=wcc.DataType.DATE),
                wcc.Property(name="address", data_type=wcc.DataType.TEXT),
                wcc.Property(name="dates", data_type=wcc.DataType.TEXT, multi=True),
            ]
        )

    def query_base_schema(self, query: str):
        """
        Query the 'BaseSchema' collection in Weaviate based on a question.
        :return: The query results
        """

        response = self.client.collections.list_all()
        print("All collections:")
        print(response)

        collection = self.client.collections.get(BASE_SCHEMA_NAME)
        print(collection)

        for item in collection.iterator():
            print(item.uuid, item.properties)

        for item in collection.iterator(
                include_vector=True
                # If using named vectors, you can specify ones to include e.g. ['title', 'body'], or True to include all
        ):
            print("------------------------------")
            print(item.properties)
            print(item.vector)

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


def setup_vector_store(agent: ApiAgent):
    vs = VectorStorage(agent)
    source_db = SourcesDB()
    vs.create_schemas()
    contents = source_db.get_all_parsed_sources_contents_by_type('base')
    vs.import_stringed_json_base(contents)
    contents = source_db.get_all_parsed_sources_contents_by_type('event')
    vs.import_stringed_json_event(contents)
    return vs


if __name__ == "__main__":
    llama_agent = LlamaApiAgent("https://api.llama-api.com", os.getenv("LLAMA_API_KEY"), "llama-13b-chat")
    vs = setup_vector_store(llama_agent)
    vs.query_base_schema("pastry")
    vs.close()
