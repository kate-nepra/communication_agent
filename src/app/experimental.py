import logging

import streamlit as st
from PIL import Image

from src.app.frontend_utils import set_favicon, MODELS, generate_message

logger = logging.getLogger(__name__)


def main():
    set_favicon()
    with st.sidebar:
        with Image.open("favicon_io/ico.png") as ico:
            st.image(ico, width=120)
            st.title("Brno Communication Agent")
            st.subheader('Models and parameters')
            selected_model = st.sidebar.selectbox('Choose LLM', [model['name'] for model in MODELS],
                                                  key='selected_model')
        agent = [model['agent'] for model in MODELS if model['name'] == selected_model][0]
        logger.info(f"Selected model: {selected_model}")
        print(agent)

    # Store LLM generated responses
    if "messages" not in st.session_state.keys():
        st.session_state.messages = [{"role": "assistant", "content": "Hi, I am an AI assistant for information about "
                                                                      "Brno city. How may I help you?"}]

    # Display or clear chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    def clear_chat_history():
        st.session_state.messages = [{"role": "assistant", "content": "How may I assist you today?"}]

    st.sidebar.button('Clear Chat History', on_click=clear_chat_history)

    # User-provided prompt
    if prompt := st.chat_input("Ask a question"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

    # Generate a new response if last message is not from assistant
    generate_message(agent, prompt)


if __name__ == "__main__":
    main()
