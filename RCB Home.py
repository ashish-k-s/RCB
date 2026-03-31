"""
Main page: Login | Create new project or Select existing project
Create or Set the data directory path
Project page: File upload for RAG | Select project DB for RAG
"""
import sys
print(sys.executable)
import streamlit as st
import tempfile
import shutil
import os

from rcb_init import init_page
from rcb_rag_manager import process_uploaded_documents, show_file_content_dialog, clear_uploaded_content

if 'vectorstore' not in st.session_state:
    st.session_state.vectorstore = None
if 'retriever' not in st.session_state:
    st.session_state.retriever = None

st.set_page_config(
    page_title="Rapid Course Builder (RCB)"
)

st.title("Rapid Course Builder (RCB)")
st.subheader("This is a placeholder login page")
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Home"
st.session_state.current_page = "Home"

init_page()

if 'use_maas' not in st.session_state:
    st.session_state.use_maas = True


user_name = st.text_input("Username", value=st.session_state.username)
if st.button("Login"):
    st.session_state.username = user_name
    st.session_state.disable_all = False
    print(f"Logged in as: {st.session_state.username}")
    st.rerun()

with open("RCB Home.md", "r") as f:
    markdown_content = f.read()
st.markdown(markdown_content)

with st.sidebar:
    st.subheader("RAG Documents Upload")
    uploaded_files = st.file_uploader(
        "Upload Documents for RAG,",
        type=["pdf", "docx", "xlsx", "pptx", "csv", "asciidoc"],
        accept_multiple_files=True,
        help=f"Upload documents to provide context for the AI. Supported formats: pdf, docx, xlsx, pptx, csv, asciidoc",
        disabled=st.session_state.disable_all
    )
    if uploaded_files:
        process_files_button = st.button("Process Documents")
        if process_files_button:
            print(f"UPLOADED FILES:\n {uploaded_files}")
            ## Remove duplicate file names
            unique_files = []
            seen_names = set()
            for file in uploaded_files:
                if file.name not in seen_names:
                    unique_files.append(file)
                    seen_names.add(file.name)
            #uploaded_files = list(set(uploaded_files))
            print(f"UPLOADED_UNIQUE_FILES: \n {unique_files}")
            process_uploaded_documents(unique_files)
            #save_uploaded_documents(unique_files)

    if os.path.exists(f"{st.session_state.user_dir}/uploads"):
        view_uploads = st.button("View uploads")
        clear_uploads = st.button("Clear uploads")

        if view_uploads:
            show_file_content_dialog(f"{st.session_state.user_dir}/uploads-hash.txt")

        if clear_uploads:
            clear_uploaded_content()

