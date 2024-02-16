import datetime
from dataclasses import dataclass
import openai
from agent.agent import Agent
import arrow

from src.constants import DATE_FORMAT

schema = {
    "header": "string",
    "record_type": "string",
    "brief": "string",
    "text": "string",
    "url": "string",
    "dateFetched": "datetime"
}


@dataclass
class BaseSchema:
    header: str
    record_type: str
    brief: str
    text: str
    url: str
    date_fetched: str


@dataclass
class ExtendedSchema(BaseSchema):
    address: str


@dataclass
class EventSchema(ExtendedSchema):
    dates: list[str]


@dataclass
class Duration:
    start: str
    end: str = None


def get_parsed_content(html: str) -> BaseSchema:
    results: list[BaseSchema] = []

    def add_place(header: str, text: str, brief: str, address: str, url: str) -> str:
        """ Call this function if you encounter entity that is a place or destination in or near Brno city, such as restaurant, café, bar, bakery, museum, tour, greenery, church, castle, university, kino, theatre or similar.
        Use provided or generate a header more fitting the found text.
        If you encounter a descriptive text of the place, for example a menu of a restaurant or a list of plays performed at a theatre, assign it as the text.
        Create a brief which is a sum up of the text no longer than 3 sentences.
        If you encounter address of the place, assign is as address. Fill in "Not found" if address not found.
        Assign provided url as url."""
        print("Adding place")
        results.append(ExtendedSchema(header, "place", brief, text, url, arrow.now().format(DATE_FORMAT), address))
        return "The place was added successfully, you can continue with the further processing."

    def add_event(header: str, text: str, brief: str, address: str, dates: list[Duration], url: str) -> str:
        """ Call this function if you encounter entity that is an event such as concert, exhibition, celebration, festival, sports match, theatrical performance or similar.
        Use provided or generate a header more fitting the found text.
        If you encounter a descriptive text of the event, for example a plot of a theatrical performance or a list of songs played at a concert, assign it as the text.
        Create a brief which is a sum up of the text no longer than 3 sentences.
        If you encounter address of a place where the event takes part, assign is as address. Fill in "Not found" if address not found.
        Assign provided url as url.
        Assign date(s) of the event as list of durations. The duration format is a JSON object with fields "start" and "end". Field "end" is optional, it is used for period of time (that are two dates from-to, like startdate-enddate, for example 31 jan–14 feb 2024). Use the format YYYY-MM-DD for date, and format HH:MM:SS for time. For example [{"start": "2024-01-11"}, {"start": "2024-01-14 15:00"}, {"start": 2024-01-31 15:00, "end": 2024-02-14}].
        """
        print("Adding event")
        results.append(EventSchema(header, "event", brief, text, url, arrow.now().format(DATE_FORMAT), address, dates))
        return "The event was added successfully, you can continue with the further processing."

    def add_administration(header: str, text: str, brief: str, address: str, url: str) -> str:
        """ Call this function if you encounter entity that is administrative information such as Municipal office, business, authorities, insurance, social Care, vehicle registration, taxes, fees, information for expats, school system, residence, ID cards or similar.
        Use provided or generate a header more fitting the found text.
        If you encounter a descriptive text of the administrative entity assign it as the text.
        Create a brief which is a sum up of the text no longer than 3 sentences.
        If you encounter address of a place (such as address of the municipal office), assign is as address. Fill in "Not found" if address not found.
        Assign provided url as url."""
        print("Adding administration")
        results.append(
            ExtendedSchema(header, "administration", brief, text, url, arrow.now().format(DATE_FORMAT), address))
        return "The administrative entity was added successfully, you can continue with the further processing."

    def add_static(header: str, text: str, brief: str, url: str) -> str:
        """ Call this function if you encounter entity that contains blog post, an article from wikipedia or information about well-known personality connected with Brno that is not likely to change in next 5 years. This entity does not contain any information about places in Brno, events or administrative.
        Use provided or generate a header more fitting the found text.
        If you encounter a descriptive text of the administrative entity assign it as the text.
        Create a brief which is a sum up of the text no longer than 3 sentences.
        Assign provided url as url."""
        print("Adding static")
        results.append(BaseSchema(header, "static", brief, text, url, arrow.now().format(DATE_FORMAT)))
        return "The static entity was added successfully, you can continue with the further processing."

    agent = Agent(api_key="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", model="gpt-3.5-turbo-1106")
    # openai.api_base = "http://localhost:1234/v1"
    # openai.api_key = ""
    # agent = Agent()

    agent.add_function(add_place)
    agent.add_function(add_event)
    agent.add_function(add_administration)
    agent.add_function(add_static)

    # completion = openai.ChatCompletion.create(
    #     model="local-model",  # this field is currently unused
    #     messages=[
    #         {"role": "system", "content": "You are a smart HTML to JSON parser."},
    #         {"role": "user", "content": "Introduce yourself."}
    #     ]
    # )

    # print(completion.choices[0].message)

    agent.do_conversation(
        f""" You are a smart processor of web-scraped text. Follow these instructions: 
        1. Go through the text and extract information from the article
        2. Use the functions with fitting description to transfer the extracted information to pre-defined Schema
        3. Reply "TERMINATE" at the end of the message when everything is done. 
        Here is the text to process ```{html}```""")
    # agent.do_conversation("What functions can you call?")

    return results[0]


res = get_parsed_content("""
URL: https://www.gotobrno.cz/en/events/jazzfestbrno/
Main header: JazzFestBrno
JazzFestBrno
The international festival JazzFestBrno will once again transform Brno into a city of jazz. Music lovers can savour the prospect of hearing the biggest stars in world jazz, progressive musicians from the rising generation, and a selection of some of the republic’s own most exciting.
21 january–10 may 2024
Brno
Tell your friends about this event!
""")
print(res)
