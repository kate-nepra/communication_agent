from pydantic import BaseModel, Field
from transformers import pipeline
from src.agents.api_agent import ApiAgent, Message
from src.constants import RECORD_TYPE_LABELS, PLACE, EVENT, ADMINISTRATION, STATIC


def get_content_type_simple(text: str, labels: list[str] = RECORD_TYPE_LABELS) -> str:
    classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

    result = classifier(text, labels)
    return result['labels'][0]


def get_content_type_by_function_call(agent: ApiAgent, content: str) -> str:
    def assign_place() -> str:
        """ Call this function if you encounter entity that describes places, tours or destinations in or near Brno city, such as restaurant, café, bar, bakery, museum, greenery, church, castle, university, kino, theatre or similar."""
        return PLACE

    def assign_event() -> str:
        """ Call this function if you encounter entity that describes events, such as concert, exhibition, celebration, festival, sports match, theatrical performance or similar."""
        return EVENT

    def assign_administration() -> str:
        """ Call this function if you encounter entity that contains administrative information such as Municipal office, business, authorities, insurance, social Care, vehicle registration, taxes, fees, information for expats, school system, residence, ID cards or similar."""
        return ADMINISTRATION

    def assign_static() -> str:
        """ Call this function if you encounter entity that contains various articles, blog posts, or an article from wikipedia or information about well-known personality connected with Brno that is not likely to change in next 5 years. This entity does not contain any information about places in Brno, events or administrative."""
        return STATIC

    messages = [Message(role="system",
                        content=f"""You're a function picker based on given web-scraped text. Follow these instructions:
     1. Take the given text as a one whole entity.
     2. Call one of the given functions, choose one with most fitting description. If the function accepts no parameters, return all (types and content and description and other) but the function name empty.
     3. Stop when you find the fitting function, you must call only one function.
     Here is the text to process
     ```{content}```""")]

    return agent.get_function_call_response(locals(),
                                            [assign_place, assign_event, assign_administration, assign_static],
                                            messages)  # Todo catch errs


def get_content_type_by_json_call(agent: ApiAgent, content: str) -> dict:
    class ContentType(BaseModel):
        """Content type of the entity can be one of: place, event, administration, static"""
        type: str = Field(...,
                          description="Content type of the entity - one of 'place', 'event', 'administration', 'static'")

    messages = [Message(role="system",
                        content=f""" You are a smart classifier of web-scraped text. Follow these instructions:
     1. Take the given text as a one whole entity.
     2. Classify the entity by returning the type name of the entity: one of 'place', 'event', 'administration', 'static':
        place: entity that describes places, tours or destinations in or near Brno city, such as restaurant, café, bar, bakery, museum, greenery, church, castle, university, kino, theatre or similar.
        event: entity that describes events, such as concert, exhibition, celebration, festival, sports match, theatrical performance or similar.
        administration: entity that contains administrative information such as Municipal office, business, authorities, insurance, social Care, vehicle registration, taxes, fees, information for expats, school system, residence, ID cards or similar.
        static: entity that contains various articles, blog posts, or an article from wikipedia or information about well-known personality connected with Brno that is not likely to change in next 5 years. This entity does not contain any information about places in Brno, events or administrative.
        
     Here is the text to process
     ```{content}```""")]

    return agent.get_json_format_response(ContentType, messages)  # Todo catch errs
