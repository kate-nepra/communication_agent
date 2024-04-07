from dataclasses import dataclass
import arrow
from dotenv import load_dotenv

from src.agents.api_agent import ApiAgent, Message
from src.constants import DATE_FORMAT
from src.data_acquisition.constants import STATIC, PLACE, EVENT, ADMINISTRATION

load_dotenv()


@dataclass
class Duration:
    """ Format for event duration. Field "end" is optional, it is used for period of time (that are two dates from-to). Use the format YYYY-MM-DD for date, and format HH:MM:SS for time."""
    start: str
    end: str = None


@dataclass
class BaseSchema:
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
    dates: list[Duration] = None


def get_parsed_content_by_function_call(agent: ApiAgent, url: str, content: str) -> BaseSchema:
    def add_place(header: str, text: str, brief: str, url: str, address: str) -> BaseSchema:
        """ Call this function if you encounter entity that is a place or destination in or near Brno city, such as restaurant, café, bar, bakery, museum, tour, greenery, church, castle, university, kino, theatre or similar."""
        return BaseSchema(header, PLACE, brief, text, url, arrow.now().format(DATE_FORMAT), address)

    def add_event(header: str, text: str, brief: str, address: str, url: str, dates: [Duration]) -> BaseSchema:
        """ Call this function if you encounter entity that is an event such as concert, exhibition, celebration, festival, sports match, theatrical performance or similar."""
        # Todo check if dates are in correct format
        return EventSchema(header, EVENT, brief, text, url, arrow.now().format(DATE_FORMAT), address,
                           dates)

    def add_administration(header: str, text: str, brief: str, url: str, address: str) -> BaseSchema:
        """ Call this function if you encounter entity that is administrative information such as Municipal office, business, authorities, insurance, social Care, vehicle registration, taxes, fees, information for expats, school system, residence, ID cards or similar."""
        return BaseSchema(header, ADMINISTRATION, brief, text, url, arrow.now().format(DATE_FORMAT),
                          address)

    def add_static(header: str, text: str, brief: str, url: str) -> BaseSchema:
        """ Call this function if you encounter entity that contains blog post, an article from wikipedia or information about well-known personality connected with Brno that is not likely to change in next 5 years. This entity does not contain any information about places in Brno, events or administrative."""
        return BaseSchema(header, STATIC, brief, text, url, arrow.now().format(DATE_FORMAT))

    dates_format = "dates={'start': start_date, 'end': end_date}"
    dates = [{"start": "2024-01-11"}, {"start": "2024-01-14 15:00"}, {"start": "2024-01-31 15:00", "end": "2024-02-14"}]
    messages = [Message(role="system",
                        content=f""" You are a smart processor of web-scraped text. Follow these instructions:
      1. Go through the text and extract information from the article, translate to English if not in English. Use plain text.
      2. Use the function with the most fitting description, pass parameters as described:
        Use provided or generate a header more fitting the found text.
        If you encounter a descriptive text of the entity, for example a plot of a theatrical performance for an event or a menu of a restaurant for a place, assign it as the text. Do not shorten it, do not omit any important information.
        Create a brief which is a sum up of the text no longer than 3 sentences.
        Assign provided url as url.
        For non-static entities, if you encounter address of a place (such as address of a municipal office for administration or address of concert-hall for an event), assign is as address. Fill in "Brno, Czech Republic" if the specific address not found but required.
        For an event, assign date(s) of the event as list of durations. The duration format is a JSON object {dates_format} with fields "start" and "end". Field "end" is optional, it is used for period of time (that are two dates from-to, like startdate-enddate, for example 31 jan–14 feb 2024). Use the format YYYY-MM-DD for date, and format HH:MM:SS for time. For example {dates}.
      3. End with the function call response, the function call must be in valid JSON format.
    URL is {url}. 
    Here is the text to process ```{content}```""")]

    return agent.get_function_call_response(locals(), [add_place, add_administration, add_static, add_event],
                                            messages)
