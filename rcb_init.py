import streamlit as st

def init_page():
    st.title("Welcome to RCB - Rapid Course Builder")
    st.sidebar.success("Select a page above.")
    if 'username' not in st.session_state:
        st.session_state.username = ""
        st.session_state.disable_all = True
    if st.session_state.username:
        st.sidebar.success(f"Logged in as: {st.session_state.username}")
        st.session_state.disable_all = False
    else:
        st.sidebar.warning("Not logged in. [Go to Login Page](./)")
        st.session_state.disable_all = True


