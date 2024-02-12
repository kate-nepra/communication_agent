from dataclasses import dataclass
import openai
import datetime
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


def chat_prompt(html: str, url: str) -> list[BaseSchema]:
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

    def add_event(header: str, text: str, brief: str, address: str, dates: list[str], url: str) -> str:
        """ Call this function if you encounter entity that is a event such as concert, exhibition, celebration, festival, sports match, theatrical performance or similar.
        Use provided or generate a header more fitting the found text.
        If you encounter a descriptive text of the event, for example a plot of a theatrical performance or a list of songs played at a concert, assign it as the text.
        Create a brief which is a sum up of the text no longer than 3 sentences.
        If you encounter address of a place where the event takes part, assign is as address. Fill in "Not found" if address not found.
        Assign provided url as url."""
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
        """ Call this function if you encounter entity that is static information like article about Brno city from wikipedia or information about well-known personality connected with Brno.
        Use provided or generate a header more fitting the found text.
        If you encounter a descriptive text of the administrative entity assign it as the text.
        Create a brief which is a sum up of the text no longer than 3 sentences.
        Assign provided url as url."""
        print("Adding static")
        results.append(BaseSchema(header, "static", brief, text, url, arrow.now().format(DATE_FORMAT)))
        return "The static entity was added successfully, you can continue with the further processing."

    # agent = Agent(api_key = "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", model="gpt-3.5-turbo-1106")
    openai.api_base = "http://localhost:1234/v1"
    openai.api_key = ""
    agent = Agent()

    agent.add_function(add_place)
    agent.add_function(add_event)
    agent.add_function(add_administration)

    # completion = openai.ChatCompletion.create(
    #     model="local-model",  # this field is currently unused
    #     messages=[
    #         {"role": "system", "content": "You are a smart HTML to JSON parser."},
    #         {"role": "user", "content": "Introduce yourself."}
    #     ]
    # )

    # print(completion.choices[0].message)

    agent.do_conversation(
        f""" You are a smart text processor. Follow these instructions: 
        1. Go through the text and extract information from the article
        2. Use the functions to add the extracted information to the database
        3. Reply "TERMINATE" at the end of the message when everything is done. 
        Here is the text to process ```{html}```""")
    # agent.do_conversation("What functions can you call?")

    return results


res = chat_prompt("""
Otello
Sung in original Italian with Czech, English and German surtitles. Oh, the power of love, power that can turn a person into an animal
Storms are raging on the coast of Cyprus and the people have gathered in the port to watch in horror as a ship returning from a military campaign against the Turks attempts to make landfall. To everyone´s relief, the ship anchors safely and the crowd welcomes the victorious Otello. A stunning choral performance then ensues, dramatically commencing one of Verdi’s most famous operas, before the story moves on to the dangerous interplay of intrigues and jealousy that arise around Otello and his wife Desdemona thanks to the machinations of the treacherous Iago. Shakespeare´s famous tragedy has been staged for more than four hundred years, and it still hasn’t lost any of its relevance. Giuseppe Verdi was a great admirer of Shakespeare´s work, and he considered the possibility of setting one of his plays to music many times. Aside from his version of Macbeth , at the end of Verdi´s life he finally chose Otello . This time, he was lucky not only to have found an excellent topic, but also a great librettist, as his collaborator was none other than the Italian poet and composer Arrigo Boito, who helped him flesh out his ideas into an ideal form. Verdi´s penultimate opera is truly a masterpiece, with three-dimensionally depicted characters and grand choral scenes that alternate with intimate lyrical moments. The role of Otello tests the skills of the best of heroic tenors, as Verdi imbued it with every shade of the human soul – at first portrayed as a warrior, and then as a tender and loving man, Otello finally transforms into a wounded animal consumed by jealousy. This unique work by Verdi is returning to the Brno stage after more than thirty years away.
Premiere: 17 th June 2022 at the Janáček Theatre Nastudováno v italském originále s českými, anglickými a německými titulky. Délka představení: 2 hodiny a 40 minut
More information
6 january 2024 - 17:00 18 february 2024 - 17:00 2 march 2024 - 17:00
Janáčkovo divadlo – Národní divadlo Brno Rooseveltova 31/7 Brno 60200
542158120 (všední den 8:30-18)
obchodni@ndbrno.cz
Tell your friends about this event!
Interesting places nearby
Mahen Theatre (Mahenovo divadlo) – National Theatre Brno
The dramatic ensemble of National Theatre Brno returns
Reduta – National Theatre Brno
The oldest theatre in Central Europe, with a progressive spirit
Brno City Theatre (Městské divadlo Brno)
This dual-stage repertory theatre hosts musicals and dramas
""", "https://www.gotobrno.cz/en/othello")
print(res)
