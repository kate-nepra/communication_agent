import openai
from dotenv import load_dotenv

from agent.agent import Agent

from transformers import pipeline
import os
from src.constants import RECORD_TYPE_LABELS

load_dotenv()


def get_content_type_simple(text: str, labels: list[str] = RECORD_TYPE_LABELS) -> str:
    classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

    result = classifier(text, labels)
    return result['labels'][0]


def get_content_type_prompt(content: str) -> str:  # Todo add model choice
    results = []

    def assign_place() -> str:
        """ Call this function if you encounter entity that describes places, tours or destinations in or near Brno city, such as restaurant, café, bar, bakery, museum, greenery, church, castle, university, kino, theatre or similar."""
        results.append("place")
        return "The place was added successfully, you can continue with the further processing."

    def assign_event() -> str:
        """ Call this function if you encounter entity that describes events, such as concert, exhibition, celebration, festival, sports match, theatrical performance or similar."""
        results.append("event")
        return "The event was added successfully, you can continue with the further processing."

    def assign_administration() -> str:
        """ Call this function if you encounter entity that contains administrative information such as Municipal office, business, authorities, insurance, social Care, vehicle registration, taxes, fees, information for expats, school system, residence, ID cards or similar."""
        results.append("administration")
        return "The administrative entity was added successfully, you can continue with the further processing."

    def assign_static() -> str:
        """ Call this function if you encounter entity that contains various articles, blog posts, or an article from wikipedia or information about well-known personality connected with Brno that is not likely to change in next 5 years. This entity does not contain any information about places in Brno, events or administrative."""
        results.append("static")
        return "The static entity was added successfully, you can continue with the further processing."

    agent = Agent(api_key=os.getenv('OPEN_AI_API_KEY'), model="gpt-3.5-turbo-1106")

    agent.add_function(assign_place)
    agent.add_function(assign_event)
    agent.add_function(assign_administration)
    agent.add_function(assign_static)

    agent.do_conversation(
        f""" You are a smart processor of web-scraped text. Follow these instructions:
     1. Take the given text as a one whole entity
     2. Classify the entity by calling one of the functions with fitting description to assign the type of the entity
     3. Reply "TERMINATE" at the end of the message when the function is called.
     Here is the text to process
     ```{content}```""")

    return results[0]
