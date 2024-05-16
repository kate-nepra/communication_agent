import logging

import streamlit as st
from PIL import Image

from src.app.frontend_utils import set_favicon, MODELS, generate_message, init_chat_history
from src.data_acquisition.constants import USER

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

    if "messages" not in st.session_state.keys():
        init_chat_history()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    st.sidebar.button('Clear Chat History', on_click=init_chat_history)

    if prompt := st.chat_input("Ask a question"):
        st.session_state.messages.append({"role": USER, "content": prompt})
        with st.chat_message(USER):
            st.write(prompt)

    generate_message(agent, prompt, st.session_state.messages)


if __name__ == "__main__":
    main()
