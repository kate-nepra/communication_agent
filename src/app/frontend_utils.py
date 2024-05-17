import base64

from PIL import Image
import streamlit as st

from src.agents.api_agent import ApiAgent
from src.agents_constants import LLAMA3_70_AGENT, LLAMA3_8_AGENT, MIXTRAL_AGENT, GPT_3_AGENT, LLAMA3_70_API_AGENT
from src.answer_creation.answer_creation import choose_action
from src.data_acquisition.constants import ASSISTANT, SYSTEM, USER
from src.vector_store.vector_storage import VectorStorage

MODELS = [{'name': 'Llama3-70B', 'agent': LLAMA3_70_AGENT},
          {'name': 'Llama3-8B', 'agent': LLAMA3_8_AGENT},
          {'name': 'Mixtral', 'agent': MIXTRAL_AGENT},
          {'name': 'GPT-3', 'agent': GPT_3_AGENT},
          {'name': 'Llama3-70b_LlamaApi', 'agent': LLAMA3_70_API_AGENT}]

CONFIG_MESSAGES = [{"role": ASSISTANT, "content": "Hi, I am an AI assistant for information about "
                                                  "Brno city. How may I help you?"}]
SYSTEM_CFG_MESSAGE = [{"role": SYSTEM,
                       "content": "You are an AI assistant for information about Brno city. Put [source] with url at the "
                                  "end of the response if the information you use for the answer is from the internet. "
                                  "Answer you do not know if you are not sure what the answer should be."}]


def init_chat_history():
    st.session_state.messages = CONFIG_MESSAGES.copy()


def get_response(agent: ApiAgent, query: str, messages: list[dict]):
    """Get response from the agent. If the response is empty, try again.
    :param agent: The agent to get the response from.
    :param query: The query to get the response for.
    :param messages: The list of messages in the chat.
    """
    msg = SYSTEM_CFG_MESSAGE.copy()
    msg.extend(messages)
    vec_db = VectorStorage()
    response = choose_action(agent, query, messages, vec_db)
    return response or choose_action(agent, query, messages, vec_db) or "There seems to be a connection error."


def set_favicon():
    with Image.open("favicon_io/favicon.ico") as fav:
        st.set_page_config(
            page_title="Brno Communication Agent",
            page_icon=fav,
        )


def generate_message(agent: ApiAgent, messages: list[dict]):
    """Generate a message from the agent based on the messages in the chat and display in the chat.
    :param agent: The agent to generate the message from.
    :param messages: The list of messages in the chat.
    """
    msg = SYSTEM_CFG_MESSAGE.copy()
    msg.extend(messages)
    if prompt := st.chat_input("Ask a Brno related question"):
        st.session_state.messages.append({"role": USER, "content": prompt})
        st.chat_message(USER).write(prompt)
        response = get_response(agent, prompt, st.session_state.messages.copy())
        st.session_state.messages.append({"role": ASSISTANT, "content": response})
        st.chat_message(ASSISTANT).write(response)


def set_title_and_logo():
    st.markdown(
        """
        <style>
        .container {
            display: flex;
        }
        .logo-text {
            font-weight:700 !important;
            font-size:45px !important;
            padding-top: 20px;
        }
        .logo-img {
            float:right;
            width: 75px;
            height: 75px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    st.markdown(
        f"""
            <div class="container">
                <img class="logo-img" src="data:image/png;base64,{base64.b64encode(open("favicon_io/ico.png", "rb").read()).decode()}">
                <p class="logo-text">Brno Communication Agent</p>
            </div>
            """,
        unsafe_allow_html=True
    )
