import logging

import streamlit as st

from src.agents_constants import GPT_3_AGENT
from src.app.frontend_utils import set_favicon, generate_message, init_chat_history, set_title_and_logo
from src.data_acquisition.constants import USER

logger = logging.getLogger(__name__)


def main():
    set_favicon()
    set_title_and_logo()

    agent = GPT_3_AGENT

    if "messages" not in st.session_state.keys():
        init_chat_history()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    if prompt := st.chat_input("Ask a question"):
        st.session_state.messages.append({"role": USER, "content": prompt})
        with st.chat_message(USER):
            st.write(prompt)

    generate_message(agent, prompt, st.session_state.messages)


if __name__ == "__main__":
    main()
