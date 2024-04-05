BASE_SCHEMA = {
    "class": "BaseSchema",
    "properties": [
        {
            "name": "header",
            "dataType": "text"
        },
        {
            "name": "record_type",
            "dataType": "text"
        },
        {
            "name": "brief",
            "dataType": "text"
        },
        {
            "name": "text",
            "dataType": "text"
        },
        {
            "name": "url",
            "dataType": "text"
        },
        {
            "name": "date_fetched",
            "dataType": "date"
        },
        {
            "name": "metadata",
            "dataType": "object"
        }
    ]
}

EVENT_SCHEMA = {
    "class": "EventSchema",
    "properties": [
        {
            "name": "header",
            "dataType": "text"
        },
        {
            "name": "record_type",
            "dataType": "text"
        },
        {
            "name": "brief",
            "dataType": "text"
        },
        {
            "name": "text",
            "dataType": "text"
        },
        {
            "name": "url",
            "dataType": "text"
        },
        {
            "name": "date_fetched",
            "dataType": "date"
        },
        {
            "name": "metadata",
            "dataType": "object"
        },
        {
            "name": "dates",
            "dataType": ["text"]
        }
    ]
}
