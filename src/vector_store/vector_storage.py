import os

from src.agents.api_agent import LlamaApiAgent, ApiAgent
from src.data_acquisition.content_processing.content_parsing import get_parsed_content_by_function_call
from src.data_acquisition.sources_store.sourcesdb import SourcesDB
import weaviate
from src.data_acquisition.data_retrieval.pdf_processing import PdfProcessor
from src.vector_store.constants import BASE_SCHEMA, EVENT_SCHEMA


class VectorStorage:
    def __init__(self, agent: ApiAgent):
        self.client = weaviate.connect_to_local()
        self.agent = agent

    def create_schemas(self):
        self.create_base_schema()
        self.create_event_schema()

    def close(self):
        self.client.close()

    def import_stringed_json_data(self, data: list[str], class_name):
        """
        Imports data to Weaviate
        :param data: data to import
        :param class_name: class name
        :return: None
        """
        collection = self.client.collections.get(class_name)

        with collection.batch.dynamic() as batch:
            for d in data:
                d = eval(d)
                print(d)
                batch.add_object(
                    properties=d,
                )

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
        collection = self.client.collections.get("BaseSchema")

        with collection.batch.dynamic() as batch:
            for s in schemas:
                batch.add_object(
                    properties=s,
                )

    def create_schema(self, schema: dict):
        self.client.collections.delete(schema["class"])
        self.client.collections.create_from_dict(schema)

    def create_base_schema(self):
        """Creates base schema, that is used for static sources, places and all basic info."""

        self.create_schema(BASE_SCHEMA)

    def create_event_schema(self):
        """Creates event schema, that is used for events, like concerts, festivals etc."""
        self.create_schema(EVENT_SCHEMA)


if __name__ == "__main__":
    llama_agent = LlamaApiAgent("https://api.llama-api.com", os.getenv("LLAMA_API_KEY"), "llama-13b-chat")
    vs = VectorStorage(llama_agent)
    source_db = SourcesDB()
    contents = source_db.get_all_parsed_sources_contents_by_type('base')
    vs.create_schemas()
    vs.import_stringed_json_data(contents, "BaseSchema")
    vs.close()
