import json
import logging

from src.agents.message import SystemMessage, UserMessage, message_from_dict
from src.constants import WEEKDAY, TODAY, TOMORROW
from datetime import datetime, timedelta
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)


def search_internet(query: str) -> list:
    """Search the cz-region internet using duckduckgo_search for the user's query and return the top 5 results."""
    return DDGS().text(query + " (Brno, CZ)", region="cz-cz", max_results=5)


def answer(data, agent, messages):
    messages = [message_from_dict(m) for m in messages]
    cfg = SystemMessage(
        f"""You are a response building agent. Your task is to analyze user's last query and create answer using provided information (if relevant). Today is {WEEKDAY} {TODAY}. Create also a list with max one or two most helpful url(s) of the sources. Adapt to chat history, anwer in user's language. End with 'built_answer' function call response in valid JSON format, do NOT add any additional text. Here is the information to use for answering user's query: ```{data}```. """)

    def build_answer(answer_text: str, sources: list):
        """Create the answer to user's question using provided information. Create also a list up to two url(s) of the most helpful used sources.
        :param answer_text: str - The answer to user's question.
        :param sources: list - List of urls used to create the answer
        """
        return answer_text + " " + str(sources) if sources else answer_text

    messages.append(cfg)
    return agent.get_forced_function_call(locals(), build_answer, messages=messages)


def eval_answer_data(agent, query, received_data, messages):
    try:
        if not received_data:
            received_data = search_internet(query)
        else:
            received_data = transfer_data(received_data)
    except Exception as e:
        logger.error(f"{e}")

    def get_more_data(transformed_query: str):
        """ Call this function when no chunk of the provided data is relevant to the user's query.
        :param transformed_query: str - Transform the user question to a simple keyword-based query if needed else use the original query."""
        return received_data.extend(search_internet(transformed_query))

    def create_answer():
        """ Call this function when the data provided are helpful for answering the user's question."""
        return received_data

    config_messages = [SystemMessage(
        f"""You are a function calling agent. Your task is to analyze user's query and this provided data: ```{received_data}```. If there is chunk of information helpful to user's query in the data, call the function 'create_answer'. If there is nothing relevant, call 'get_more_data'. End with the function call response in valid JSON format, escape JSON reserved characters properly. Do NOT add any additional text. """),
        UserMessage(query)]

    data = agent.get_function_call(locals(), [get_more_data, create_answer], messages=config_messages)
    response = answer(data, agent, messages) if data else answer(received_data, agent, messages)
    if len(response) > 10:
        return response
    while not response or len(response) < 10:
        cfg = SystemMessage(
            f"""You are a response building agent. Your task is to analyze user's last query and create answer using provided information if relevant. Adapt to chat history.  If the user asks por event with a set time, double-check that you are using only the data that fit the time requirements. Today is {WEEKDAY} {TODAY}. Here is the information to use for answering user's query: ```{data}```. Add list of used sources, response format: 'Response text. [<source(s)>]'.""").as_dict()
        call_messages = messages.copy()
        call_messages.append(cfg)
        response = agent.get_base_response(call_messages).choices[0].message.content
    return response


def choose_action(agent, query, messages, vec_db):
    def needs_event_infos():
        """Call this function when the user wants to get information about cultural events like festivals, exhibitions, theatrical plays, e.g. "What to do this week?" or "Is something happening tomorrow in the city centre?", "Tell me about Mucha exhibition", or "I would love to go to theatre today."""
        msg = SystemMessage(f"""You are a function calling agent. Your task is to make valid function call to provided function with arguments following this description:
:param transformed_query: str - Transform the user question to an understandable keyword-based question not containing the time indication: "What to do this week?" -> "Events", "Is something happening tomorrow in the city centre?" -> "Events in the city centre", "I would love to go to theatre today." -> "Theatre".  Translate to englih if not english.
:param dates: list[str] - Today is {WEEKDAY} {TODAY}: Return list of dates that suit the user's query, provide each date in the format YYYY-MM-DD, following these instructions:
 a) If the user asks for today, return today's date: ['{TODAY}'], same with tomorrow: ['{TOMORROW}']. 
 b) If the user asks for events this weekend, return: {get_this_weekend_dates()} For next weekend, return list with computed dates of friday, saturday and sunday.
 c) If the user asks for a specific day of the week, compute it from today's date and return in requested format. 
 d) If the user asks for a whole month, return the date as YYYY-MM, for example for May 2024 return ['2024-05'].
 e) If the user asks for events next week, return list of dates of all days next week. The week starts on Monday.
 f) If the user asks about a certain event and does not specify time, return [''], make sure the empty string is included.
Return the function call response in valid JSON format, escape JSON reserved characters properly. Do NOT add any additional text.""")

        def get_event_info(transformed_query: str, dates: list):
            """ Transform the user question to an understandable keyword-based query that is more suitable for vector database hybrid search, retrieve the dates. Translate to englih if not english."""
            if len(dates) < 1 or dates[0] == '':
                dates = None
            return vec_db.hybrid_query_event(transformed_query, dates)

        data = agent.get_forced_function_call(locals(), get_event_info, messages=[msg, UserMessage(query)])
        if not data:
            eval_answer_data(agent, query, vec_db.hybrid_query_event(query), messages)
        return eval_answer_data(agent, query, data, messages)

    def needs_base_brno_infos():
        """Call this function when the user asks questions about anything that can not be a cultural event, like places (sights, restaurants or galleries etc.), administration or just Brno city in general, famous personalities that might be connected to the city ...,  e.g. "What is the address of the city hall?" or "What are the opening hours of the zoo?", "Where to get coffee?" or "How to get a tram ticket?"""
        msg = SystemMessage(f"""Your task is to make valid function call to provided function with arguments following this description:
:param transformed_query: str - Transform the user question to an understandable keyword-based query: "What is the address of the city hall?" -> "City hall address", "What are the opening hours of the zoo?" -> "Zoo opening hours", "How to get a tram ticket?" -> "Tram ticket".
Return the function call response in valid JSON format, escape JSON reserved characters properly. Do NOT add any additional text.""")

        def get_base_info(transformed_query: str):
            """Transform the user question to an understandable keyword-based query that is more suitable for vector database hybrid search."""
            return vec_db.hybrid_query_base(transformed_query)

        data = agent.get_forced_function_call(locals(), get_base_info, messages=[msg, UserMessage(query)])
        if not data:
            eval_answer_data(agent, query, vec_db.hybrid_query_base(query), messages)
        return eval_answer_data(agent, query, data, messages)

    def answer_without_data():
        """Call this function when the user does not ask a question e.g. "Hello I'm Kate" or "Tell me a joke." or asks a question you are sure is not relevant to Brno city."""
        logger.info(messages)
        r = agent.get_base_response(messages)
        return r.choices[0].message.content

    config_msg = f"""Your task is to choose a function based on user's message. End with the function call response in valid JSON format, escape JSON reserved characters properly. Do NOT add any additional text."""

    return agent.get_function_call(locals(), [needs_base_brno_infos, needs_event_infos, answer_without_data],
                                   messages=[SystemMessage(config_msg), UserMessage(query)])


def get_this_weekend_dates():
    """Return the dates left for the current weekend or the dates for the next weekend. This is used to give an example of the date in the prompt."""
    today = datetime.now()
    weekday = today.weekday()
    weekend_days = [4, 5, 6]
    if weekday in weekend_days:
        # If today is Friday, Saturday, or Sunday, return the dates left for the current weekend
        days_left = [weekend_day for weekend_day in weekend_days if weekend_day >= weekday]
        return [(today + timedelta(days=(day - weekday))).strftime('%Y-%m-%d') for day in days_left]

    # If today is Monday, Tuesday, Wednesday, or Thursday, return the dates for the next weekend
    friday = today + timedelta(days=(4 - weekday) % 7)
    saturday = friday + timedelta(days=1)
    sunday = saturday + timedelta(days=1)

    weekend_dates = [friday.strftime('%Y-%m-%d'), saturday.strftime('%Y-%m-%d'), sunday.strftime('%Y-%m-%d')]
    return weekend_dates


def process_dict(d):
    d = dict(d)
    values = []
    url = ""
    dates = ""
    for key, value in d.items():
        if key == 'url':
            url = f"; url: {value}"
        elif key == 'dates':
            dates = f"; dates: {json.dumps(value)}"
        else:
            values.append(value)
    return d, dates, url, values


def transfer_data(data):
    """Transfer the received data to a list of strings."""
    output_data = []
    data = eval(str(data))
    for d in data:
        try:
            d, dates, url, values = process_dict(d)
            output_string = "\n".join(values)
            output_data.append(output_string + url + dates)
        except Exception as e:
            logger.error(f"{e}")
            output_data.append(d)
    return output_data
