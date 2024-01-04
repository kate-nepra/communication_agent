from dataclasses import dataclass
import openai
import datetime
from agent.agent import Agent

schema = {
    "header": "string",
    "record_type": "string",
    "brief": "string",
    "text": "string",
    "url": "string",
    "dateFetched": "datetime"
}


@dataclass
class Schema:
    header: str
    record_type: str
    brief: str
    text: str
    url: str
    dateFetched: datetime.datetime


def chat_prompt(html: str, url: str) -> list[Schema]:
    results: list[Schema] = []

    def add_place(header: str, brief: str, text: str) -> str:
        """ Call this function if you encounter entity that is a place such as restaurant or theatre. Find or
        generate a header fitting the found text. If you encounter a description of the place, for example a menu of a restaurant or a list of plays
        performed at a theatre, assign it as the text. Create a brief which is a sum up of the text no longer than 3
        sentences. """
        results.append(Schema(header, "event", brief, text, url, "now()"))
        return "The place was added successfully, you can continue with the further processing."

    def add_event(header: str, brief: str, text: str) -> str:
        """ Call this function if you encounter entity that is a event such as concert, exhibition or theatrical
        performance. Find or generate a header fitting the found text. If you encounter a description of the event, for example a plot of a theatrical
        performance or a list of songs played at a concert,  assign it as the text. Create a brief which is a sum up of the text
        no longer than 3 sentences. """
        results.append(Schema(header, "event", brief, text, url, "now()"))
        return "The event was added successfully, you can continue with the further processing."

    # agent = Agent(api_key = "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", model="gpt-3.5-turbo-1106")
    openai.api_base = "http://localhost:1234/v1"
    openai.api_key = "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"
    agent = Agent()

    agent.add_function(add_place)
    agent.add_function(add_event)

    # completion = openai.ChatCompletion.create(
    #     model="local-model",  # this field is currently unused
    #     messages=[
    #         {"role": "system", "content": "You are a smart HTML to JSON parser."},
    #         {"role": "user", "content": "Introduce yourself."}
    #     ]
    # )

    # print(completion.choices[0].message)

    agent.do_conversation(
        f"""
        Anytime you want to inform user about new place you have discovered, please respond in a format `add_new_place(<header>,<brief>,<text>)` and follow these instructions: "Call this function if you encounter entity that is a place such as restaurant or theatre. Find or
        generate a header fitting the found text. If you encounter a description of the place, for example a menu of a restaurant or a list of plays
        performed at a theatre, assign it as the text. Create a brief which is a sum up of the text no longer than 3
        sentences."

        Anytime you want to inform user about new event you have discovered, please respond in a format `add_new_event(<header>,<brief>,<text>)` and follow these instructions: "Call this function if you encounter entity that is a event such as concert, exhibition or theatrical
        performance. Find or generate a header fitting the found text. If you encounter a description of the event, for example a plot of a theatrical
        performance or a list of songs played at a concert,  assign it as the text. Create a brief which is a sum up of the text
        no longer than 3 sentences."
        
        You are a HTML processor. Your task is to go through the following HTML and to extract information about places, events.
        For each detected place or event follow these instructions:
        1. convert the HTML tags to XML tags with the most descriptive name that suits the text inside the tag - for example '<p>Some descriptive text here.</p>' to '<description>'.
        2. call respective function to add it.
        
        Here is the text to process ```{html}```""")
    # agent.do_conversation("What functions can you call?")

    return results


res = chat_prompt("""
<!DOCTYPE html>
<div class="b-intro__wrap">
 <h1 class="b-intro__title">
  Otello
 </h1>
</div>
<p>
 Sung in original Italian with Czech, English and German surtitles.
</p>
<p>
 Oh, the power of love, power that can turn a person into an animal
</p>
<p>
 Storms are raging on the coast of Cyprus and the people have gathered in the port to watch in horror as a ship returning from a military campaign against the Turks attempts to make landfall. To everyone´s relief, the ship anchors safely and the crowd welcomes the victorious Otello. A stunning choral performance then ensues, dramatically commencing one of Verdi’s most famous operas, before the story moves on to the dangerous interplay of intrigues and jealousy that arise around Otello and his wife Desdemona thanks to the machinations of the treacherous Iago. Shakespeare´s famous tragedy has been staged for more than four hundred years, and it still hasn’t lost any of its relevance. Giuseppe Verdi was a great admirer of Shakespeare´s work, and he considered the possibility of setting one of his plays to music many times. Aside from his version of
 Macbeth
 , at the end of Verdi´s life he finally chose
 Otello
 . This time, he was lucky not only to have found an excellent topic, but also a great librettist, as his collaborator was none other than the Italian poet and composer Arrigo Boito, who helped him flesh out his ideas into an ideal form. Verdi´s penultimate opera is truly a masterpiece, with three-dimensionally depicted characters and grand choral scenes that alternate with intimate lyrical moments. The role of Otello tests the skills of the best of heroic tenors, as Verdi imbued it with every shade of the human soul – at first portrayed as a warrior, and then as a tender and loving man, Otello finally transforms into a wounded animal consumed by jealousy. This unique work by Verdi is returning to the Brno stage after more than thirty years away.
</p>
<p>
 Premiere: 17
 th
 June 2022 at the Janáček Theatre
</p>
<p>
 Nastudováno v italském originále s českými, anglickými a německými titulky.
 Délka představení: 2 hodiny a 40 minut
</p>
<p>
 More information
</p>
<div class="b-card u-m-mb-10">
 6 january 2024
 - 17:00
 18 february 2024
 - 17:00
 2 march 2024
 - 17:00
</div>
<div class="b-card">
 <p class="font-bold">
  Janáčkovo divadlo – Národní divadlo Brno
  Rooseveltova 31/7
  Brno 60200
 </p>
 <p>
  542 158 120 (všední den 8:30-18)
  <a href="mailto:obchodni@ndbrno.cz">
   obchodni@ndbrno.cz
  </a>
 </p>
</div>
<div class="u-spread">
 <h2 class="b-facebook__title">
  Tell your friends about this event!
 </h2>
</div>
<div class="b-heading">
 <h2 class="b-heading__title h4">
  Interesting places nearby
 </h2>
</div>
<a class="b-card" href="https://www.gotobrno.cz/en/place/national-theatre-brno-mahen-theatre-mahenovo-divadlo/">
 Mahen Theatre (Mahenovo divadlo) – National Theatre Brno
 <p>
  The dramatic ensemble of National Theatre Brno returns
 </p>
</a>
<a class="b-card" href="https://www.gotobrno.cz/en/place/national-theatre-brno-reduta/">
 Reduta – National Theatre Brno
 <p>
  The oldest theatre in Central Europe, with a progressive spirit
 </p>
</a>
<a class="b-card" href="https://www.gotobrno.cz/en/place/brno-city-theatre-mestske-divadlo-brno/">
 Brno City Theatre (Městské divadlo Brno)
 <p>
  This dual-stage repertory theatre hosts musicals and dramas
 </p>
</a>

""", "https://www.gotobrno.cz/en/othello")
print(res)
