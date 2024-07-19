from pydantic import BaseModel, Field
from transformers import pipeline
from src.agents.api_agent import ApiAgent
from src.agents.message import SystemMessage, UserMessage
from src.data_acquisition.constants import logger
from src.data_acquisition.constants import STATIC, PLACE, EVENT, ADMINISTRATION, RECORD_TYPE_LABELS, \
    EVENT_URL_SUBSTRINGS, PLACE_URL_SUBSTRINGS, ADMINISTRATION_URL_SUBSTRINGS, \
    STATIC_URL_SUBSTRINGS


def preclassify_by_url(url: str):
    """Pre-classify the content type based on the URL. If the URL contains a substring that is specific to a certain
    type of content, returns the type of content. If the URL does not contain any of the substrings, returns None."""
    for substr in EVENT_URL_SUBSTRINGS:
        if substr in url:
            return EVENT
    for substr in PLACE_URL_SUBSTRINGS:
        if substr in url:
            return PLACE
    for substr in ADMINISTRATION_URL_SUBSTRINGS:
        if substr in url:
            return ADMINISTRATION
    for substr in STATIC_URL_SUBSTRINGS:
        if substr in url:
            return STATIC
    return None


def get_content_type_simple(text: str, labels: list[str] = RECORD_TYPE_LABELS) -> str:
    """Simple content type classifier based on the zero-shot classification model from Hugging Face."""
    classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
    result = classifier(text, labels)
    return result['labels'][0]


def get_content_type_preclassified_function_call(agent: ApiAgent, url: str, content: str) -> str:
    """Pre-classifies the content type based on the URL.
    If that is not possible, uses a function call to classify the content type.
    :param agent: ApiAgent
    :param url: the URL of the content
    :param content: the text to be classified
    :return: the content type
    """
    content_type = preclassify_by_url(url)
    if content_type is None or content_type not in RECORD_TYPE_LABELS:
        logger.info(f"Could not pre-classify content type")
        return get_content_type_by_function_call(agent, content)
    return content_type


def get_content_type_by_function_call(agent: ApiAgent, content: str) -> str:
    """
    Returns the content type based on the given text using an agent function call.
    :param agent: ApiAgent
    :param content: the text to be classified
    :return: the content type
    """

    def assign_place() -> str:
        """Call this function if you encounter entity that describes places, tours or destinations in or near Brno city, such as restaurant, café, bar, bakery, museum, greenery, church, castle, university, kino, theatre or similar."""
        return PLACE

    def assign_event() -> str:
        """Call this function if you encounter entity that describes events, such as concert, exhibition, celebration, festival, sports match, theatrical performance or similar."""
        return EVENT

    def assign_administration() -> str:
        """Call this function if you encounter entity that contains administrative information such as Municipal office, business, authorities, insurance, social Care, vehicle registration, taxes, fees, information for expats, school system, residence, ID cards or similar."""
        return ADMINISTRATION

    def assign_static() -> str:
        """Call this function if you encounter entity that contains various articles, blog posts, or an article from wikipedia or information about well-known personality connected with Brno that is not likely to change in next 5 years. This entity does not contain any information about places in Brno, events or administrative."""
        return STATIC

    messages = [SystemMessage(f"""You're a function picker based on given web-scraped text. Follow these instructions:
 1. Take the given text as a one whole entity.
 2. Call one of the given functions, choose one with most fitting description. If the function accepts no parameters, return all (types and content and description and other) but the function name empty.
 3. Stop when you find the fitting function, you must call only one function."""),
                UserMessage(f"""Here is the text to process ```{content}```""")]

    return agent.get_function_call(locals(),
                                   [assign_place, assign_event, assign_administration, assign_static],
                                   messages=messages)


def get_content_type_by_json_call(agent: ApiAgent, content: str) -> dict:
    """
    Returns the content type based on the given text using an agent json call.
    :param agent: ApiAgent
    :param content: the text to be classified
    :return: the content type in JSON format {"type": <classified_type>}
    """

    class ContentType(BaseModel):
        """Content type of the entity can be one of: place, event, administration, static"""
        type: str = Field(...,
                          description="Content type of the entity - one of 'place', 'event', 'administration', 'static'")

    messages = [SystemMessage(
        content=f""" You are a smart classifier of web-scraped text. Follow these instructions:
 1. Take the given text as a one whole entity.
 2. Classify the entity by returning the type name of the entity: one of 'place', 'event', 'administration', 'static':
   place: entity that describes places, tours or destinations in or near Brno city, such as restaurant, café, bar, bakery, museum, greenery, church, castle, university, kino, theatre or similar.
   event: entity that describes events, such as concert, exhibition, celebration, festival, sports match, theatrical performance or similar.
   administration: entity that contains administrative information such as Municipal office, business, authorities, insurance, social Care, vehicle registration, taxes, fees, information for expats, school system, residence, ID cards or similar.
   static: entity that contains various articles, blog posts, or an article from wikipedia or information about well-known personality connected with Brno that is not likely to change in next 5 years. This entity does not contain any information about places in Brno, events or administrative.
 3. As the response, return only valid JSON with the type of the entity and stop, do not provide any additional text."""),
        UserMessage(f"""Here is the text to process ```{content}```""")]
    return agent.get_json_format_response(ContentType, messages)
