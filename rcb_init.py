import streamlit as st
import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
import google.generativeai as genai

load_dotenv()

def init_page():
    st.sidebar.info("Select a page above.")
    if 'data_dir' not in st.session_state:
        st.session_state.data_dir = os.getenv("DATA_DIR", "/tmp/rcb_data") 
    if 'user_dir' not in st.session_state:
        st.session_state.user_dir = ""
    if 'username' not in st.session_state:
        st.session_state.username = ""
        st.session_state.disable_all = True
    if st.session_state.username:
        st.sidebar.success(f"Logged in as: {st.session_state.username}")
        st.session_state.user_dir = f"{st.session_state.data_dir}/{st.session_state.username}"
        st.session_state.disable_all = False
        os.makedirs(st.session_state.user_dir, exist_ok=True)
    else:
        if st.session_state.current_page != "Home":
            st.sidebar.warning("Not logged in. [Go to Login Page](./)")
        else:
            st.sidebar.info("Please enter your username and click Login.")
        st.session_state.disable_all = True

    print(f"User: {st.session_state.username}, User Dir: {st.session_state.user_dir}, Data Dir: {st.session_state.data_dir}")
      
def init_image_page():
    if 'd2_image_code' not in st.session_state:
        st.session_state.d2_image_code = ""
    if 'image_name' not in st.session_state:
        st.session_state.image_name = ""

def init_llm():
    load_dotenv()

    MAAS_API_KEY = os.environ["MAAS_API_KEY"]
    MAAS_API_BASE = os.environ["MAAS_API_BASE"]
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

    if 'model_choice' not in st.session_state:
        st.session_state.model_choice = "MaaS"
    if 'response' not in st.session_state:
        st.session_state.response = ""
    if 'user_prompt' not in st.session_state:
        st.session_state.user_prompt = ""
    if 'system_prompt' not in st.session_state:
        st.session_state.system_prompt = ""
    # if 'llm' not in st.session_state:
    #     st.session_state.llm = None

    st.session_state.model_choice = st.sidebar.selectbox(
        "Choose LLM Model",
        options=["MaaS", "Gemini", "Local"],
        index=0,
        disabled=st.session_state.disable_all
    )

