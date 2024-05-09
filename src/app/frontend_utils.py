from PIL import Image
import streamlit as st
from src.agents.api_agent import LocalApiAgent, OpenAIApiAgent, LlamaApiAgent
from src.agents.message import SystemMessage, UserMessage
from src.constants import LOCAL_URL, OPENAI_URL, OPENAI_KEY, LLAMA_URL, LLAMA_KEY, LOCAL_KEY, WEEKDAY, TODAY
from src.data_acquisition.constants import ASSISTANT
from src.vector_store.vector_storage import VectorStorage

MODELS = [{'name': 'Llama3-70B', 'agent': LocalApiAgent(LOCAL_URL, LOCAL_KEY, "llama3:70b")},
          {'name': 'Llama3-8B', 'agent': LocalApiAgent(LOCAL_URL, LOCAL_KEY, "llama3")},
          {'name': 'Mixtral', 'agent': LocalApiAgent(LOCAL_URL, LOCAL_KEY, "mixtral")},
          {'name': 'GPT-3', 'agent': OpenAIApiAgent(OPENAI_URL, OPENAI_KEY, "gpt-3.5-turbo-0125")},
          {'name': 'Llama3-70b_LlamaApi', 'agent': LlamaApiAgent(LLAMA_URL, LLAMA_KEY, "llama3-70b")}]


def answer_with_data(data):
    print(data)


def choose_action(agent, query, vec_db):
    event_descr = f"""Call this function when the user wants to get information about events, e.g. "What to do this week?" or "Is something happening tomorrow in the city centre?" or "I would love to go to theatre today."
:param dates: list[str] - Today is {WEEKDAY} {TODAY}: if the user asks about a specific date, provide the date in the format YYYY-MM-DD, if the user asks for today, return today's date: ['{TODAY}'], same with tomorrow: ['{TOMORROW}']. If the user asks for a specific day of the week, compute it from today's date and return in requested format. Return list of dates that suit the user's query - for example, if the user asks for events this weekend, return dates of friday, saturday and sunday. If the user asks for events next week, return list of dates of all days next week. If the time is not specified, return dates of next 7 days.
:param transformed_query: str - Transform the user question to an understandable keyword-based question not containing the time indication: "What to do this week?" -> "Events", "Is something happening tomorrow in the city centre?" -> "Events in the city centre", "I would love to go to theatre today." -> "Theatre"."""
    base_descr = f"""Call this function when the user asks questions about places, administration or just Brno city in general, e.g. "What is the address of the city hall?" or "What are the opening hours of the zoo?" or "How to get a tram ticket?".
:param transformed_query: str - Transform the user question to an understandable keyword-based query: "What is the address of the city hall?" -> "City hall address", "What are the opening hours of the zoo?" -> "Zoo opening hours", "How to get a tram ticket?" -> "Tram ticket"."""
    no_data_descr = f"""Call this function when the user asks a question that can not be related to places, events, administration, living in Brno or Brno city in general, or does not ask question at all e.g. "Hello I'm Kate" or "Tell me a joke."."""

    config_msg = f"""Your task is to choose a function based on user's message. End with the function call response in valid JSON format, do NOT add any additional text."""

    def get_event_info(transformed_query: str, dates: list):
        """Get event info"""
        return answer_with_data(vec_db.query_event_schema_hybrid(transformed_query, dates))

    def get_base_info(transformed_query):
        """Get base info"""
        return answer_with_data(vec_db.query_base_schema_hybrid(transformed_query))

    def answer_without_data():
        print(query)

    action = agent.get_custom_descr_function_call(locals(),
                                                  [[get_event_info, event_descr], [get_base_info, base_descr],
                                                   [answer_without_data, no_data_descr]],
                                                  messages=[SystemMessage(config_msg), UserMessage(query)])


def get_response(agent, query):
    vec_db = VectorStorage()
    choose_action(agent, query, vec_db)
    return "Hello"


def set_favicon():
    with Image.open("favicon_io/favicon.ico") as fav:
        st.set_page_config(
            page_title="Brno Communication Agent",
            page_icon=fav,
            layout="wide",
        )


def generate_message(agent, prompt):
    if st.session_state.messages[-1]["role"] != ASSISTANT:
        with st.chat_message(ASSISTANT):
            with st.spinner("Thinking..."):
                response = get_response(agent, prompt)
                placeholder = st.empty()
                full_response = ''
                for item in response:
                    full_response += item
                    placeholder.markdown(full_response)
                placeholder.markdown(full_response)
        message = {"role": ASSISTANT, "content": full_response}
        st.session_state.messages.append(message)
