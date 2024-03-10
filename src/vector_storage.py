import weaviate
import json


class VectorStorage:
    def __init__(self, url):
        self.client = weaviate.Client(url)

    def import_data(self, data, class_name):
        """
        Imports data to Weaviate
        :param data: data to import
        :param class_name: class name
        :return: None
        """
        # Prepare a batch process
        self.client.batch.configure(batch_size=100)  # Configure batch
        with self.client.batch as batch:
            # Batch import all Questions
            for i, d in enumerate(data):
                properties = {"title": d["title"],
                              "text": d["text"],
                              "url": d["url"],
                              "dateFetched": d["dateFetched"]
                              }
                batch.add_data_object(properties, class_name)

    def create_schema(self, class_name, class_schema):
        self.client.schema.delete_class(class_name)
        self.client.schema.create_class(class_schema)

    def create_base_schema(self):
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
                    "name": "dateFetched",
                    "dataType": ["date"]
                }
            ]
        }

        self.create_schema("BaseSchema", base_schema_class)

    def create_extended_schema(self):
        extended_schema_class = {
            "class": "ExtendedSchema",
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
                    "name": "dateFetched",
                    "dataType": ["date"]
                },
                {
                    "name": "address",
                    "dataType": ["string"]
                }
            ]
        }

        self.create_schema("ExtendedSchema", extended_schema_class)

    def create_event_schema(self):
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
                    "name": "dateFetched",
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

        self.create_schema("EventSchema", event_schema_class)
