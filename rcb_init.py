import streamlit as st
import os
from dotenv import load_dotenv

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
        st.sidebar.warning("Not logged in. [Go to Login Page](./)")
        st.session_state.disable_all = True

    print(f"User: {st.session_state.username}, User Dir: {st.session_state.user_dir}, Data Dir: {st.session_state.data_dir}")