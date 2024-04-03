BASE_SCHEMA = {
    "class": "BaseSchema",
    "properties": [
        {
            "name": "header",
            "dataType": "string"
        },
        {
            "name": "record_type",
            "dataType": "string"
        },
        {
            "name": "brief",
            "dataType": "string"
        },
        {
            "name": "text",
            "dataType": "text"
        },
        {
            "name": "url",
            "dataType": "string"
        },
        {
            "name": "date_fetched",
            "dataType": "date"
        },
        {
            "name": "metadata",
            "dataType": "dictionary"
        }
    ]
}

EVENT_SCHEMA = {
    "class": "EventSchema",
    "properties": [
        {
            "name": "header",
            "dataType": "string"
        },
        {
            "name": "record_type",
            "dataType": "string"
        },
        {
            "name": "brief",
            "dataType": "string"
        },
        {
            "name": "text",
            "dataType": "text"
        },
        {
            "name": "url",
            "dataType": "string"
        },
        {
            "name": "date_fetched",
            "dataType": "date"
        },
        {
            "name": "address",
            "dataType": "string"
        },
        {
            "name": "dates",
            "dataType": ["string"]
        }
    ]
}
