import base64
import logging

import streamlit as st

from src.app.frontend_utils import set_favicon, MODELS, generate_message

logger = logging.getLogger(__name__)


def main():
    set_favicon()
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

    # agent is 'gpt-3' from MODELS
    agent = [model['agent'] for model in MODELS if model['name'] == 'GPT-3'][0]

    if "messages" not in st.session_state.keys():
        st.session_state.messages = [{"role": "assistant", "content": "Hi, I am an AI assistant for information about "
                                                                      "Brno city. How may I help you?"}]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # User-provided prompt
    if prompt := st.chat_input("Ask a question"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

    # Generate a new response if last message is not from assistant
    generate_message(agent, prompt, st.session_state.messages)


if __name__ == "__main__":
    main()
