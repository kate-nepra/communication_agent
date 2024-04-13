from dataclasses import dataclass
import arrow
from dotenv import load_dotenv

from src.agents.api_agent import ApiAgent, Message
from src.constants import DATE_FORMAT
from src.data_acquisition.constants import STATIC, PLACE, EVENT, ADMINISTRATION, SYSTEM, USER, DATES_EXAMPLE, \
    DATES_FORMAT_EXAMPLE

load_dotenv()


@dataclass
class Duration:
    """ Format for event duration. Field "end" is optional, it is used for period of time (that are two dates from-to). Use the format YYYY-MM-DD for date, and format HH:MM:SS for time."""
    start: str
    end: str = None


@dataclass
class BaseSchema():
    """ Base schema for all entities """
    header: str
    record_type: str
    brief: str
    text: str
    url: str
    date_fetched: str
    address: str = None


@dataclass
class EventSchema(BaseSchema):
    """ Event schema for events """
    dates: list = None


def get_parsed_content_by_function_call(agent: ApiAgent, url: str, content: str) -> BaseSchema:
    def add_place(header: str, text: str, brief: str, address: str) -> BaseSchema:
        """Call this function if you encounter entity that is a place or destination in or near Brno city, such as restaurant, café, bar, bakery, museum, tour, greenery, church, castle, university, kino, theatre or similar."""
        return BaseSchema(header, PLACE, brief, text, url, arrow.now().format(DATE_FORMAT), address)

    def add_event(header: str, text: str, brief: str, address: str, dates: str) -> BaseSchema:
        """Call this function if you encounter entity that is an event such as concert, exhibition, celebration, festival, sports match, theatrical performance or similar."""
        return EventSchema(header, EVENT, brief, text, url, arrow.now().format(DATE_FORMAT), address, dates)

    def add_administration(header: str, text: str, brief: str, address: str) -> BaseSchema:
        """Call this function if you encounter entity that is administrative information such as Municipal office, business, authorities, insurance, social Care, vehicle registration, taxes, fees, information for expats, school system, residence, ID cards or similar."""
        return BaseSchema(header, ADMINISTRATION, brief, text, url, arrow.now().format(DATE_FORMAT),
                          address)

    def add_static(header: str, text: str, brief: str) -> BaseSchema:
        """Call this function if you encounter entity that contains blog post, an article from wikipedia or information about well-known personality connected with Brno that is not likely to change in next 5 years. This entity does not contain any information about places in Brno, events or administrative."""
        return BaseSchema(header, STATIC, brief, text, url, arrow.now().format(DATE_FORMAT))

    messages = [Message(role=SYSTEM,
                        content=f"""You are a smart processor of web-scraped text. Follow these instructions: 
 1. Go through the text and extract information from the article, translate to English if not in English. Use plain text. 
 2. Use the function with the most fitting description, pass parameters as described in the following steps:
    Use provided or generate a header more fitting the found text. 
    The descriptive text of the entity (for example a plot of a theatrical performance for an event, insurance application process for administration, or a menu of a restaurant for a place) must be assigned it as the text parameter. Do NOT SHORTEN it, do NOT OMIT any important information. 
    Create a brief which is a sum up of the text no longer than 3 sentences. 
    For non-static entities only: if you encounter address of a place (such as address of a municipal office for administration or address of concert-hall for an event), assign is as address. Fill in "Brno, Czech Republic" if the specific address not found but required. 
    For an event entity: assign date(s) of the event as list of durations. The duration format is a stringified JSON object {DATES_FORMAT_EXAMPLE} with fields "start" and "end". Field "end" is optional, it is used for period of time (that are two dates from-to, like startdate-enddate, for example 31 jan–14 feb 2024). Use the format YYYY-MM-DD for date, and format HH:MM:SS for time. For example {DATES_EXAMPLE}. 
 3. End with the function call response in valid JSON format., do NOT add any additional text."""),
                Message(role=USER,
                        content=f"""Here is the text to process ```{content}```""")]

    return agent.get_function_call_response(locals(), [add_place, add_administration, add_static, add_event],
                                            messages)


def get_parsed_by_type(record_type, agent: ApiAgent, url: str, content: str) -> BaseSchema:
    def get_params_base(header: str, text: str, brief: str, address: str) -> BaseSchema:
        """This function encapsulates the process of creating a BaseSchema object.
        :param header: The header of the entity.
        :param text: The descriptive text of the entity (for example a plot of a theatrical performance for an event, insurance application process for administration, or a menu of a restaurant for a place) must be assigned it as the text parameter. Do NOT SHORTEN it, do NOT OMIT any important information.
        :param brief: The sum up of the text no longer than 3 sentences.
        :param address: The address of the entity, default: "Brno, Czech Republic".
        :return: BaseSchema object."""
        return BaseSchema(header, record_type, brief, text, url, arrow.now().format(DATE_FORMAT), address)

    def get_params_event(header: str, text: str, brief: str, address: str, dates: str) -> BaseSchema:
        """This function encapsulates the process of creating an EventSchema object.
        :param header: The header of the entity.
        :param text: The descriptive text of the entity (for example a plot of a theatrical performance for an event, insurance application process for administration, or a menu of a restaurant for a place) must be assigned it as the text parameter. Do NOT SHORTEN it, do NOT OMIT any important information.
        :param brief: The sum up of the text no longer than 3 sentences.
        :param address: The address of the entity, default: "Brno, Czech Republic".
        :param dates: The date(s) of the event as list of durations. The duration format is a stringified JSON object {DATES_FORMAT_EXAMPLE} with fields "start" and "end". Field "end" is optional, it is used for period of time (that are two dates from-to, like startdate-enddate, for example 31 jan–14 feb 2024). Use the format YYYY-MM-DD for date, and format HH:MM:SS for time. For example {DATES_EXAMPLE}.
        :return: EventSchema object."""
        return EventSchema(header, record_type, brief, text, url, arrow.now().format(DATE_FORMAT), address, dates)

    def _get_messages(record_type) -> list[Message]:
        event_specific = ""
        if record_type == EVENT:
            event_specific = f"""
For an event entity: assign date(s) of the event as list of durations. The duration format is a stringified JSON object {DATES_FORMAT_EXAMPLE} with fields "start" and "end". Field "end" is optional, it is used for period of time (that are two dates from-to, like startdate-enddate, for example 31 jan–14 feb 2024). Use the format YYYY-MM-DD for date, and format HH:MM:SS for time. For example {DATES_EXAMPLE}."""

        system_message = f"""You are a smart processor of web-scraped text. Follow these instructions: 
 1. Go through the text and extract information from the article, translate to English if not in English. Use plain text. 
 2. Fill in the parameters of the schema as follows:
    Use provided or generate a header more fitting the found text. 
    The descriptive text of the entity (for example a plot of a theatrical performance for an event, insurance application process for administration, or a menu of a restaurant for a place) must be assigned it as the text parameter. Do NOT SHORTEN it, do NOT OMIT any important information. 
    Create a brief which is a sum up of the text no longer than 3 sentences. 
    If you encounter address of a place (such as address of a municipal office for administration or address of concert-hall for an event), assign is as address. Fill in "Brno, Czech Republic" if the specific address not found but required. {event_specific}
 3. End with the function call response in valid JSON format., do NOT add any additional text."""

        return [Message(role=SYSTEM, content=system_message),
                Message(role=USER, content=f"""Here is the text to process ```{content}```""")]

    return agent.get_function_call_response(locals(), [get_params_event] if record_type == EVENT else [get_params_base],
                                            _get_messages(record_type))
