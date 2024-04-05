import os
import weaviate.classes.config as wcc
from src.agents.api_agent import LlamaApiAgent, ApiAgent
from src.data_acquisition.content_processing.content_parsing import get_parsed_content_by_function_call
from src.data_acquisition.sources_store.sourcesdb import SourcesDB
import weaviate
from src.data_acquisition.data_retrieval.pdf_processing import PdfProcessor


class VectorStorage:
    def __init__(self, agent: ApiAgent):
        self.client = weaviate.connect_to_local()
        self.agent = agent

    def create_schemas(self):
        self.delete_schema("BaseSchema")
        self.delete_schema("EventSchema")
        self.create_base_schema()
        self.create_event_schema()

    def close(self):
        self.client.close()

    def import_stringed_json_data(self, data: list[str], class_name):
        """
        Imports data to Weaviate
        :param data: data to import
        :param class_name: class name
        :param schema: schema of the class
        :return: None
        """
        collection = self.client.collections.get(class_name)

        with collection.batch.dynamic() as batch:
            for d in data:
                batch.add_object(
                    properties=eval(d),
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

    def delete_schema(self, name: str):
        self.client.collections.delete(name)

    def create_base_schema(self):
        """Creates base schema, that is used for static sources, places and all basic info."""
        self.client.collections.create(
            name="BaseSchema",
            vectorizer_config=wcc.Configure.Vectorizer.text2vec_gpt4all(),
            generative_config=wcc.Configure.Generative.mistral(),
            properties=[
                wcc.Property(name="header", data_type=wcc.DataType.TEXT),
                wcc.Property(name="record_type", data_type=wcc.DataType.TEXT,
                             moduleConfig={"text2vec-gpt4all": {"vectorizePropertyName": "true"}}),
                wcc.Property(name="brief", data_type=wcc.DataType.TEXT),
                wcc.Property(name="text", data_type=wcc.DataType.TEXT),
                wcc.Property(name="url", data_type=wcc.DataType.TEXT),
                wcc.Property(name="date_fetched", data_type=wcc.DataType.DATE),
                wcc.Property(name="metadata", data_type=wcc.DataType.OBJECT, nested_properties=[
                    wcc.Property(name="address", data_type=wcc.DataType.TEXT)
                ]),
            ]
        )

    def create_event_schema(self):
        """Creates event schema, that is used for events, like concerts, festivals etc."""
        self.client.collections.create(
            name="EventSchema",
            vectorizer_config=wcc.Configure.Vectorizer.text2vec_gpt4all(),
            generative_config=wcc.Configure.Generative.mistral(),
            properties=[
                wcc.Property(name="header", data_type=wcc.DataType.TEXT),
                wcc.Property(name="record_type", data_type=wcc.DataType.TEXT,
                             moduleConfig={"text2vec-gpt4all": {"vectorizePropertyName": "true"}}),
                wcc.Property(name="brief", data_type=wcc.DataType.TEXT),
                wcc.Property(name="text", data_type=wcc.DataType.TEXT),
                wcc.Property(name="url", data_type=wcc.DataType.TEXT),
                wcc.Property(name="date_fetched", data_type=wcc.DataType.DATE),
                wcc.Property(name="metadata", data_type=wcc.DataType.OBJECT, nested_properties=[
                    wcc.Property(name="address", data_type=wcc.DataType.TEXT)
                ]),
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

        collection = self.client.collections.get("BaseSchema")
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

        collection = self.client.collections.get("EventSchema")
        print(collection)

        for item in collection.iterator(
                include_vector=True
                # If using named vectors, you can specify ones to include e.g. ['title', 'body'], or True to include all
        ):
            print("------------------------------")
            print(item.properties)
            print(item.vector)

        bases = self.client.collections.get("EventSchema")

        response = bases.query.near_text(
            query=query,
            limit=5
        )
        print(response)
        print(response.objects[0].properties)


def setup_vector_store(agent: ApiAgent):
    vs = VectorStorage(agent)
    source_db = SourcesDB()
    vs.create_schemas()
    contents = source_db.get_all_parsed_sources_contents_by_type('base')
    vs.import_stringed_json_data(contents, "BaseSchema")
    contents = source_db.get_all_parsed_sources_contents_by_type('event')
    vs.import_stringed_json_data(contents, "EventSchema")
    return vs


if __name__ == "__main__":
    llama_agent = LlamaApiAgent("https://api.llama-api.com", os.getenv("LLAMA_API_KEY"), "llama-13b-chat")
    vs = setup_vector_store(llama_agent)
    vs.query_base_schema("pastry")
    vs.close()
