import json
import logging
import os
from datetime import datetime, timedelta

import weaviate.classes.config as wcc
import weaviate.classes.query as wcq
from dotenv import load_dotenv
from json_repair import repair_json
from sqlalchemy import null

from src.constants import DATETIME_FORMAT, DATE_FORMAT
from src.data_acquisition.sources_store.sourcesdb import SourcesDB
import weaviate

from weaviate.classes.config import Configure, VectorDistances

logger = logging.getLogger(__name__)
load_dotenv()
BASE_SCHEMA_NAME = "BaseSchema"
EVENT_SCHEMA_NAME = "EventSchema"


class VectorStorage:
    def __init__(self):
        self.client = weaviate.connect_to_local(headers={'X-Cohere-Api-Key': os.getenv("COHERE_APIKEY")})

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
                    obj = eval(repair_json(d))
                    try:
                        dates = json.loads(repair_json(obj["dates"]))
                        dates_str = self._get_dates_str(dates)
                    except Exception as e:
                        logger.error(f"Error while parsing dates {obj['dates']}: {e}")
                        dates = []
                        obj["text"] = obj["text"] + " date: " + obj["dates"]
                        dates_str = str(obj["dates"])
                    properties = {
                        "header": obj["header"],
                        "record_type": obj["record_type"],
                        "brief": obj["brief"],
                        "text": obj["text"],
                        "url": obj["url"],
                        "date_fetched": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                        "address": obj["address"] if "address" in obj and obj["address"] is not null else "",
                        "dates": dates,
                        "dates_str": dates_str,
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
            description="Places and all basic info about Brno.",
            vectorizer_config=wcc.Configure.Vectorizer.text2vec_transformers(),
            reranker_config=wcc.Configure.Reranker.cohere(),
            vector_index_config=Configure.VectorIndex.dynamic(
                distance_metric=VectorDistances.COSINE
            ),
            properties=[
                wcc.Property(name="header", data_type=wcc.DataType.TEXT),
                wcc.Property(name="record_type", data_type=wcc.DataType.TEXT),
                wcc.Property(name="brief", data_type=wcc.DataType.TEXT),
                wcc.Property(name="text", data_type=wcc.DataType.TEXT),
                wcc.Property(name="url", data_type=wcc.DataType.TEXT),
                wcc.Property(name="date_fetched", data_type=wcc.DataType.DATE, skip_indexing=True),
                wcc.Property(name="address", data_type=wcc.DataType.TEXT),
            ]
        )

    def create_event_schema(self):
        """Creates event schema, that is used for events, like concerts, festivals etc."""
        self.client.collections.create(
            name=EVENT_SCHEMA_NAME,
            description="Culture events, concerts, festivals etc.",
            vectorizer_config=wcc.Configure.Vectorizer.text2vec_transformers(),
            reranker_config=wcc.Configure.Reranker.cohere(),
            vector_index_config=Configure.VectorIndex.dynamic(
                distance_metric=VectorDistances.COSINE
            ),
            properties=[
                wcc.Property(name="header", data_type=wcc.DataType.TEXT),
                wcc.Property(name="record_type", data_type=wcc.DataType.TEXT),
                wcc.Property(name="brief", data_type=wcc.DataType.TEXT),
                wcc.Property(name="text", data_type=wcc.DataType.TEXT),
                wcc.Property(name="url", data_type=wcc.DataType.TEXT),
                wcc.Property(name="date_fetched", data_type=wcc.DataType.DATE, skip_indexing=True),
                wcc.Property(name="address", data_type=wcc.DataType.TEXT),
                wcc.Property(name="dates", data_type=wcc.DataType.OBJECT_ARRAY, nested_properties=[
                    wcc.Property(name="date", data_type=wcc.DataType.OBJECT, skip_indexing=True, nested_properties=[
                        wcc.Property(name="start", data_type=wcc.DataType.DATE),
                        wcc.Property(name="end", data_type=wcc.DataType.DATE, optional=True)
                    ])
                ]),
                wcc.Property(name="dates_str", data_type=wcc.DataType.TEXT, skip_indexing=True)])

    def get_all_items(self, collection_name: str):
        return self.client.collections.get(collection_name)

    def vector_query_base(self, query: str):
        """
        Query the 'BaseSchema' collection in Weaviate based on a question using vector similarity search.
        :return: The query results
        """
        collection = self.client.collections.get(BASE_SCHEMA_NAME)
        query = collection.query.near_text(
            query=query,
            limit=3,
            return_metadata=wcq.MetadataQuery(certainty=True, score=True, explain_score=True, distance=True)
        )
        return query.objects

    def vector_query_event(self, query: str, dates: list = None):
        """
        Query the 'EventSchema' collection in Weaviate based on a question using vector similarity search.
        :return: The query results
        """
        collection = self.client.collections.get(EVENT_SCHEMA_NAME)
        query = collection.query.near_text(  # filter on date and sort by date
            query=query,
            limit=3,
            filters=(wcq.Filter.by_property("dates_str").contains_any(dates) if dates else None),
            return_metadata=wcq.MetadataQuery(certainty=True, score=True, explain_score=True, distance=True)
        )
        return query.objects

    def keyword_query_base(self, query: str):
        """
        Query the 'BaseSchema' collection in Weaviate based on a question using keyword search.
        :return: The query results
        """
        collection = self.client.collections.get(BASE_SCHEMA_NAME)
        query = collection.query.bm25(
            query=query,
            limit=3,
            query_properties=["text", "brief", "header", "address"],
            return_properties=["text", "brief", "header", "address"],
            return_metadata=wcq.MetadataQuery(certainty=True, score=True, explain_score=True, distance=True)
        )
        return query.objects

    def keyword_query_event(self, query: str, dates: list = None):
        """
        Query the 'EventSchema' collection in Weaviate based on a question using keyword search.
        :return: The query results
        """
        print("Querying Weaviate " + str(query) + " with dates: " + str(dates))
        collection = self.client.collections.get(EVENT_SCHEMA_NAME)
        query = collection.query.bm25(  # filter on date and sort by date
            query=query,
            limit=3,
            query_properties=["text", "brief", "header", "address"],
            return_properties=["text", "brief", "header", "address"],
            filters=(wcq.Filter.by_property("dates_str").contains_any(dates) if dates else None),
            return_metadata=wcq.MetadataQuery(certainty=True, score=True, explain_score=True, distance=True)
        )
        return query.objects

    def hybrid_query_base(self, query: str):
        """
        Query the 'BaseSchema' collection in Weaviate based on a question using hybrid search.
        :return: The query results
        """
        collection = self.client.collections.get(BASE_SCHEMA_NAME)
        query = collection.query.hybrid(
            query=query,
            fusion_type=wcq.HybridFusion.RELATIVE_SCORE,
            auto_limit=2,
            limit=3,
            alpha=0.65,
            query_properties=["text", "brief", "header", "address"],
            return_properties=["text", "brief", "header", "address"],
            rerank=wcq.Rerank(
                prop="text",
                query=query
            ),
            return_metadata=wcq.MetadataQuery(score=True, explain_score=True)
        )
        return [p.properties for p in query.objects]

    def hybrid_query_event(self, query: str, dates: list = None):
        """
        Query the 'EventSchema' collection in Weaviate based on a question using hybrid search.
        :return: The query results
        """
        print("Querying Weaviate " + str(query) + " with dates: " + str(dates))
        collection = self.client.collections.get(EVENT_SCHEMA_NAME)
        query = collection.query.hybrid(
            query=query,
            fusion_type=wcq.HybridFusion.RELATIVE_SCORE,
            auto_limit=2,
            limit=3,
            alpha=0.65,
            query_properties=["text", "brief", "header", "address"],
            return_properties=["text", "brief", "header", "address"],
            filters=(wcq.Filter.by_property("dates_str").contains_any(dates) if dates else None),

            rerank=wcq.Rerank(
                prop="text",
                query=query
            ),
            return_metadata=wcq.MetadataQuery(score=True, explain_score=True)
        )
        return [p.properties for p in query.objects]

    def _get_dates_str(self, dates):
        dates_str = ""
        for date in dates:
            if "start" in date and "end" in date:
                dates_str += self._get_filled_in_dates(date["start"], date["end"]) + " "
            elif "start" in date:
                dates_str += date["start"] + " "
        return dates_str

    @staticmethod
    def _get_filled_in_dates(start_date, end_date):
        start_datetime = datetime.strptime(start_date, DATETIME_FORMAT if 'T' in start_date else DATE_FORMAT)
        end_datetime = datetime.strptime(end_date, DATETIME_FORMAT if 'T' in end_date else DATE_FORMAT)

        if start_datetime > end_datetime:
            return ""

        dates = []
        current_date = start_datetime
        while current_date <= end_datetime:
            dates.append(current_date.strftime(DATE_FORMAT))
            current_date += timedelta(days=1)

        return ' '.join(dates)


def setup_vector_store():
    vs = VectorStorage()
    source_db = SourcesDB()
    vs.create_schemas()
    contents = source_db.get_all_parsed_sources_contents_by_type('base')
    vs.import_stringed_json_base(contents)
    contents = source_db.get_all_parsed_sources_contents_by_type('event')
    vs.import_stringed_json_event(contents)
    return vs


if __name__ == "__main__":
    # vs = setup_vector_store()
    vs = VectorStorage()
    data = vs.hybrid_query_event("I would love to visit a museum")
    vs.close()
    print(data)
