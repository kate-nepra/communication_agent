from src.parser import get_parsed_content
from src.sourcesdb import SourcesDB
import weaviate
from pdf_processing import PdfProcessor


class VectorStorage:
    def __init__(self):
        self.client = weaviate.connect_to_local()

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
        schemas = [get_parsed_content(file_name, content) for content in chunks]
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
        base_schema_class = {
            "class": "BaseSchema",
            "properties": [
                {
                    "name": "header",
                    "dataType": ["string"]
                },
                {
                    "name": "recordType",
                    "dataType": ["string"]
                },
                {
                    "name": "brief",
                    "dataType": ["string"]
                },
                {
                    "name": "text",
                    "dataType": ["text"]
                },
                {
                    "name": "url",
                    "dataType": ["string"]
                },
                {
                    "name": "date_fetched",
                    "dataType": ["date"]
                },
                {
                    "name": "metadata",
                    "dataType": ["string"]
                }
            ]
        }

        self.create_schema(base_schema_class)

    def create_event_schema(self):
        """Creates event schema, that is used for events, like concerts, festivals etc."""
        event_schema_class = {
            "class": "EventSchema",
            "properties": [
                {
                    "name": "header",
                    "dataType": ["string"]
                },
                {
                    "name": "recordType",
                    "dataType": ["string"]
                },
                {
                    "name": "brief",
                    "dataType": ["string"]
                },
                {
                    "name": "text",
                    "dataType": ["text"]
                },
                {
                    "name": "url",
                    "dataType": ["string"]
                },
                {
                    "name": "date_fetched",
                    "dataType": ["date"]
                },
                {
                    "name": "address",
                    "dataType": ["string"]
                },
                {
                    "name": "dates",
                    "dataType": ["string"]
                }
            ]
        }

        self.create_schema(event_schema_class)


if __name__ == "__main__":
    vs = VectorStorage()
    source_db = SourcesDB()
    contents = source_db.get_all_parsed_sources_contents_by_type('base')
    vs.create_schemas()
    vs.import_data(contents, "BaseSchema")
    vs.close()
