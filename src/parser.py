import os
from dataclasses import dataclass
from agents.agent import Agent
import arrow
from dotenv import load_dotenv
from src.constants import DATE_FORMAT

load_dotenv()


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


def get_parsed_content(url: str, content: str) -> BaseSchema:  # TODO divide models
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
        If you encounter a descriptive text of the entity assign it as the text.
        Create a brief which is a sum up of the text no longer than 3 sentences.
        Assign provided url as url."""
        print("Adding static")
        results.append(BaseSchema(header, "static", brief, text, url, arrow.now().format(DATE_FORMAT)))
        return "The static entity was added successfully, you can continue with the further processing."

    agent = Agent(api_key=os.getenv('OPEN_AI_API_KEY'), model="gpt-3.5-turbo-1106")

    agent.add_function(add_place)
    agent.add_function(add_event)
    agent.add_function(add_administration)
    agent.add_function(add_static)

    agent.do_conversation(
        f""" You are a smart processor of web-scraped text. Follow these instructions:
      1. Go through the text and extract information from the article, translate to English if not in English.
      2. Use the functions with fitting description to transfer the extracted information to pre-defined Schema
      3. Reply "TERMINATE" at the end of the message when everything is done.
    URL is {url}. 
    Here is the text to process ```{content}```""")

    return results[0]
