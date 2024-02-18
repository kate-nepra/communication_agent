import openai
from agent.agent import Agent


def get_content_type(text: str) -> str:
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

    agent = Agent(api_key="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", model="gpt-3.5-turbo-1106")

    agent.add_function(assign_place)
    agent.add_function(assign_event)
    agent.add_function(assign_administration)
    agent.add_function(assign_static)

    # agent.do_conversation(
    # f""" You are a smart processor of web-scraped text. Follow these instructions:
    # 1. Take the given text as a one whole entity
    # 2. Classify the entity by calling one of the functions with fitting description to assign the type of the entity
    # 3. Reply "TERMINATE" at the end of the message when the function is called.
    # Here is the text to process
    # ```{text}```""")

    # return results[0]
    return "place"


if __name__ == "__main__":
    text_place = f"""
    Website url: https://www.gotobrno.cz/en/explore-brno/;
    Main header: Explore Brno;
    Scraped main content:
    Explore Brno 
    SHORT TOUR This condensed tour of the city centre will take you to the most 
    popular, interesting, and important buildings, squares, streets, and parks. 
    LONG TOUR If you have enough time and 
    energy, get to know Brno even better on the long tour and explore some of the many interesting and significant 
    places in the city centre. 
    TOP DESTINATIONS Brno is full of valuable historical buildings and interesting places. 
    For a true feel of just how amazing this city is, here’s a list of its must-see locations. 
    SCULPTURES IN BRNO The streets of Brno are full of various objects that may leave you scratching your head. Some 
    cause controversy while others get passed by without much notice. 
    MUSEUMS AND GALLERIES Historical artifacts, 
    remarkable works of contemporary art, technical and scientific exploration, and much more! Come experience it all 
    yourself!
    Tour guide
    Explore Brno with a local guide
    Interactive map
    Find the places you'll enjoy the most"""

    text_place_2 = f"""
    Main header: Taste Brno
Taste Brno
We reviewed the best places to eat and drink in Brno.
They all have one thing in common - they give the customers a great taste experience, original combinations, quality ingredients and authentic atmosphere. These are the venues we present in the independent ranking Gourmet Brno 2023!
A list of the best Brno restaurants, bistros, confectionaries, cafés, pubs, bars and wine bars.
Restaurants and bistros
Confectionaries
Cafés
Beer spots
Wine bars
Bars
Take-away
South Moravia"""

    text_event = f"""
    URL: https://www.gotobrno.cz/en/events-in-brno/
Main header: Events in Brno
Search your event
Brno
Enjoy the city. Don't see your event?"""

    static_text = f"""URL: https://www.gotobrno.cz/en/brno-phenomenon/
Main header: Brno Phenomenon
Brno Phenomenon
Views on Brno by people who live here
Author blog
Don’t try to define Czech food – just enjoy it!
    """

    admin_text = f"""
    URL: https://www.brno.cz/
Main header: Brno
Brno
Brno
Rodičovské vouchery
Více
Darujme krev pro Brno
Více
Potřebuji vyřídit
Občanské průkazy
Stav vyřízení občanského průkazu
Žádost o občanský průkaz
Převzetí občanského průkazu
Oznámení ztráty, odcizení občanského průkazu
Aktuální obsazenost přepážek
Zobrazit více
Cestovní pasy
"""
    r = get_content_type(text_place)
    print('RESULT:', r)
