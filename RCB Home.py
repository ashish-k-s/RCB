"""
Main page: Login | Create new project or Select existing project
Create or Set the data directory path
Project page: File upload for RAG | Select project DB for RAG
"""
import streamlit as st
import tempfile
import shutil
import os

st.set_page_config(
    page_title="Rapid Course Builder (RCB)"
)

st.title("Rapid Course Builder (RCB)")
st.subheader("This is a placeholder login page")
st.sidebar.success("Select a page above.")

if 'use_maas' not in st.session_state:
    st.session_state.use_maas = True
if 'username' not in st.session_state:
    st.session_state.username = ""
    st.session_state.disable_all = True

user_name = st.text_input("Username", value=st.session_state.username)
if st.button("Login"):
    st.session_state.username = user_name
    st.session_state.disable_all = False
    print(f"Logged in as: {st.session_state.username}")