BASE_SCHEMA = {
    "class": "BaseSchema",
    "description": "Schema used for places, static and administrative entities",
    "vectorIndexType": "hnsw",
    "vectorIndexConfig": {
    },
    "vectorizer": "text2vec-transformers",
    "moduleConfig": {
        "text2vec-transformers": {
        }
    },
    "properties": [
        {
            "name": "header",
            "description": "Header of the event",
            "dataType": ["text"],
            "moduleConfig": {
                "text2vec-transformers": {
                    "skip": False,
                    "vectorizePropertyName": False
                }
            },
            "indexFilterable": True,
            "indexSearchable": True
        },
        {
            "name": "record_type",
            "description": "Type of the event record",
            "dataType": ["text"],
            "moduleConfig": {
                "text2vec-transformers": {
                    "skip": False,
                    "vectorizePropertyName": True
                }
            },
            "indexFilterable": True,
            "indexSearchable": True
        },
        {
            "name": "brief",
            "description": "Brief description of the event",
            "dataType": ["text"],
            "moduleConfig": {
                "text2vec-transformers": {
                    "skip": False,
                    "vectorizePropertyName": False
                }
            },
            "indexFilterable": True,
            "indexSearchable": True
        },
        {
            "name": "text",
            "description": "Full text description of the event",
            "dataType": ["text"],
            "moduleConfig": {
                "text2vec-transformers": {
                    "skip": False,
                    "vectorizePropertyName": False
                }
            },
            "indexFilterable": True,
            "indexSearchable": True
        },
        {
            "name": "url",
            "description": "URL related to the event",
            "dataType": ["text"],
            "moduleConfig": {
                "text2vec-transformers": {
                    "skip": False,
                    "vectorizePropertyName": False
                }
            },
            "indexFilterable": True,
            "indexSearchable": True,
            "shardingConfig": {
            }
        },
        {
            "name": "date_fetched",
            "description": "Date when the event information was fetched",
            "dataType": ["date"],
            "indexFilterable": True
        },
        {
            "name": "address",
            "description": "Event address",
            "dataType": ["text"],
            "moduleConfig": {
                "text2vec-transformers": {
                    "skip": False,
                    "vectorizePropertyName": False
                }
            },
            "indexFilterable": True,
            "indexSearchable": True
        }
    ]
}

EVENT_SCHEMA = {
    "class": "EventSchema",
    "description": "Schema used for events, like concerts and festivals",
    "vectorIndexType": "hnsw",
    "vectorIndexConfig": {
    },
    "vectorizer": "text2vec-transformers",
    "moduleConfig": {
        "text2vec-transformers": {
        }
    },
    "properties": [
        {
            "name": "header",
            "description": "Header of the event",
            "dataType": ["text"],
            "moduleConfig": {
                "text2vec-transformers": {
                    "skip": False,
                    "vectorizePropertyName": False
                }
            },
            "indexFilterable": True,
            "indexSearchable": True
        },
        {
            "name": "record_type",
            "description": "Type of the event record",
            "dataType": ["text"],
            "moduleConfig": {
                "text2vec-transformers": {
                    "skip": False,
                    "vectorizePropertyName": True
                }
            },
            "indexFilterable": True,
            "indexSearchable": True
        },
        {
            "name": "brief",
            "description": "Brief description of the event",
            "dataType": ["text"],
            "moduleConfig": {
                "text2vec-transformers": {
                    "skip": False,
                    "vectorizePropertyName": False
                }
            },
            "indexFilterable": True,
            "indexSearchable": True
        },
        {
            "name": "text",
            "description": "Full text description of the event",
            "dataType": ["text"],
            "moduleConfig": {
                "text2vec-transformers": {
                    "skip": False,
                    "vectorizePropertyName": False
                }
            },
            "indexFilterable": True,
            "indexSearchable": True
        },
        {
            "name": "url",
            "description": "URL related to the event",
            "dataType": ["text"],
            "moduleConfig": {
                "text2vec-transformers": {
                    "skip": False,
                    "vectorizePropertyName": False
                }
            },
            "indexFilterable": True,
            "indexSearchable": True,
            "shardingConfig": {
            }
        },
        {
            "name": "date_fetched",
            "description": "Date when the event information was fetched",
            "dataType": ["date"],
            "indexFilterable": True,
        },
        {
            "name": "address",
            "description": "Event address",
            "dataType": ["text"],
            "moduleConfig": {
                "text2vec-transformers": {
                    "skip": False,
                    "vectorizePropertyName": False
                }
            },
            "indexFilterable": True,
            "indexSearchable": True
        },
        {
            "name": "dates",
            "description": "Dates related to the event",
            "dataType": ["text"],
            "multi": True,
            "indexFilterable": True,
        }
    ]
}
