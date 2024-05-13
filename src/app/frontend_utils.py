from PIL import Image
import streamlit as st
from src.agents.api_agent import LocalApiAgent, OpenAIApiAgent, LlamaApiAgent
from src.agents.message import SystemMessage, UserMessage
from src.constants import LOCAL_URL, OPENAI_URL, OPENAI_KEY, LLAMA_URL, LLAMA_KEY, LOCAL_KEY, WEEKDAY, TODAY, TOMORROW
from src.data_acquisition.constants import ASSISTANT
from src.vector_store.vector_storage import VectorStorage
from datetime import datetime, timedelta
from duckduckgo_search import DDGS

MODELS = [{'name': 'Llama3-70B', 'agent': LocalApiAgent(LOCAL_URL, LOCAL_KEY, "llama3:70b")},
          {'name': 'Llama3-8B', 'agent': LocalApiAgent(LOCAL_URL, LOCAL_KEY, "llama3")},
          {'name': 'Mixtral', 'agent': LocalApiAgent(LOCAL_URL, LOCAL_KEY, "mixtral")},
          {'name': 'GPT-3', 'agent': OpenAIApiAgent(OPENAI_URL, OPENAI_KEY, "gpt-3.5-turbo-0125")},
          {'name': 'Llama3-70b_LlamaApi', 'agent': LlamaApiAgent(LLAMA_URL, LLAMA_KEY, "llama3-70b")}]


def get_this_weekend_dates():
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


def search_internet(query):
    return DDGS().text(query + " (Brno, CZ)", region="cz-cz", max_results=5)


def answer_with_data(agent, query, data, messages):
    print(data)
    if not data:
        data = search_internet(query)

    def get_more_data(transformed_query: str):
        """ Call this function when the data provided are not relevant to the user's question.
        :param transformed_query: str - Transform the user question to an understandable keyword-based question."""
        return answer(search_internet(transformed_query))

    def create_answer():
        """ Call this function when the data provided are sufficient to answer the user's question."""
        return answer(data)

    def answer(data):
        print(data)
        return data

    config_messages = [SystemMessage(
        f"""You are a function calling agent. Your task is to analyze user's question and provided JSON format data. If the information is helpful to user's query, call the function 'create_answer'. If not, call 'get_more_data'. End with the function call response in valid JSON format, do NOT add any additional text. Here is the data to help answering user's query: ```{data}```. """),
        UserMessage(query)]
    return agent.get_function_call(locals(), [get_more_data, create_answer], messages=config_messages)


def choose_action(agent, query, messages, vec_db):
    def needs_event_infos():
        """Call this function when the user wants to get information about events, e.g. "What to do this week?" or "Is something happening tomorrow in the city centre?", "Tell me about Mucha exhibition", or "I would love to go to theatre today."""
        msg = SystemMessage(f"""You are a function calling agent. Your task is to make valid function call to provided function with arguments following this description:
:param transformed_query: str - Transform the user question to an understandable keyword-based question not containing the time indication: "What to do this week?" -> "Events", "Is something happening tomorrow in the city centre?" -> "Events in the city centre", "I would love to go to theatre today." -> "Theatre".
:param dates: list[str] - Today is {WEEKDAY} {TODAY}: Return list of dates that suit the user's query, provide each date in the format YYYY-MM-DD, following these instructions:
 a) If the user asks for today, return today's date: ['{TODAY}'], same with tomorrow: ['{TOMORROW}']. 
 b) If the user asks for events this weekend, return: {get_this_weekend_dates()} For next weekend, return list with computed dates of friday, saturday and sunday.
 c) If the user asks for a specific day of the week, compute it from today's date and return in requested format. 
 d) If the user asks for a whole month, return the date as YYYY-MM, for example for May 2024 return ['2024-05'].
 e) If the user asks for events next week, return list of dates of all days next week. The week starts on Monday.
 f) If the user asks about a certain event and does not specify time, return [''].
Return the function call response in valid JSON format, do NOT add any additional text.""")

        def get_event_info(transformed_query: str, dates: list):
            if len(dates) < 1 or dates[0] == '':
                return answer_with_data(agent, query, vec_db.hybrid_query_event_no_date(transformed_query), messages)
            return answer_with_data(agent, query, vec_db.hybrid_query_event(transformed_query, dates), messages)

        return agent.get_forced_function_call(locals(), get_event_info, messages=[msg, UserMessage(query)])

    def needs_base_brno_infos():
        """Call this function when the user asks questions about places like restaurants or galleries, administration or just Brno city in general, e.g. "What is the address of the city hall?" or "What are the opening hours of the zoo?" or "How to get a tram ticket?"""
        msg = SystemMessage(f"""Your task is to make valid function call to provided function with arguments following this description:
:param transformed_query: str - Transform the user question to an understandable keyword-based query: "What is the address of the city hall?" -> "City hall address", "What are the opening hours of the zoo?" -> "Zoo opening hours", "How to get a tram ticket?" -> "Tram ticket".
Return the function call response in valid JSON format, do NOT add any additional text.""")

        def get_base_info(transformed_query: str):
            return answer_with_data(agent, query, vec_db.hybrid_query_base(transformed_query), messages)

        return agent.get_forced_function_call(locals(), get_base_info, messages=[msg, UserMessage(query)])

    def answer_without_data():
        """Call this function when the user asks a question that can not be related to places, events, administration, living in Brno or Brno city in general, or does not ask question at all e.g. "Hello I'm Kate" or "Tell me a joke."."""
        r = agent.get_base_response(messages)
        print(r)
        return r.choices[0].message.content

    config_msg = f"""Your task is to choose a function based on user's message. End with the function call response in valid JSON format, do NOT add any additional text."""

    return agent.get_function_call(locals(), [needs_event_infos, needs_base_brno_infos, answer_without_data],
                                   messages=[SystemMessage(config_msg), UserMessage(query)])


def get_response(agent, query, messages):
    vec_db = VectorStorage()
    return choose_action(agent, query, messages, vec_db)


def set_favicon():
    with Image.open("favicon_io/favicon.ico") as fav:
        st.set_page_config(
            page_title="Brno Communication Agent",
            page_icon=fav,
        )


def generate_message(agent, prompt, messages):
    if st.session_state.messages[-1]["role"] != ASSISTANT:
        with st.chat_message(ASSISTANT):
            with st.spinner("Thinking..."):
                placeholder = st.empty()
                response = get_response(agent, prompt, messages)
                placeholder.markdown(response)
        message = {"role": ASSISTANT, "content": response}
        st.session_state.messages.append(message)
