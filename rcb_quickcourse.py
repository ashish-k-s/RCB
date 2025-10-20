import streamlit as st
import os
import hashlib
import re
from pathlib import Path

##Use doclin instead of below
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma


# --- Configuration for jinja2 file to generate antora.yml---
course_outline_file = f"{st.session_state.user_dir}/TEMP/outline.adoc"
course_structure_file_names = f"{st.session_state.user_dir}/TEMP/course_structure_file_names.csv"
antora_template_dir = './templates'          # folder where antora.yml.j2 is stored
antora_output_file = f"{st.session_state.user_dir}/TEMP/antora.yml"            # output location
antora_pb_file = f"{st.session_state.user_dir}/TEMP/antora-playbook.yml"
antora_csv_file = course_structure_file_names
if st.session_state.repo_name:
    antora_repo_name = st.session_state.repo_name
    print(f"DEBUG: Assigned repo name: {antora_repo_name}")
    print(f"DEBUG: Using repo name from session state: {st.session_state.repo_name}")
#antora_course_title = 'Sample Course Title' # Use the course heading fron csv file
if st.session_state.antora_course_title:
    antora_course_title = st.session_state.antora_course_title
antora_course_version = '1'


def generate_rag_db(file_path):
    try:
        loader = PyPDFLoader(file_path)
        document = loader.load()
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        docs = text_splitter.split_documents(document)
        
        embeddings = OllamaEmbeddings(model="mxbai-embed-large")
        db_dir = str(Path(f"{st.session_state.user_dir}/chroma").absolute())

        # Initialize or update a single persistent vector store
        if st.session_state.vectorstore is None:
            db = Chroma.from_documents(docs, embedding=embeddings, persist_directory=db_dir)
            st.session_state.vectorstore = db
        else:
            st.session_state.vectorstore.add_documents(docs)
        
        # Persist changes
        st.session_state.vectorstore.persist()
        file_name = os.path.basename(file_path)
        st.success(f"RAG db generated for file: {file_name}")        
        return True
    except Exception as e:
        st.error(f"Error during generating RAG db")
        print(f"Error during generating RAG db: {str(e)}")
        return False

def process_uploaded_documents(uploaded_files):
    print(f"Processing {len(uploaded_files)} uploaded files...")
    if not uploaded_files:
        return
    total_files = len(uploaded_files)
    progress_bar = st.progress(0)
    status_placeholder = st.empty()

    processed_files = 0
    
    try:
        for i, uploaded_file in enumerate(uploaded_files):
            progress = (i + 1) / total_files
            progress_bar.progress(progress)
            status_placeholder.text(f"Processing {uploaded_file.name}")
            if not file_already_uploaded(uploaded_file):
                print(f"File {uploaded_file.name} not available, will be saving it...")
                ### Save uploaded file
                file_path = save_uploaded_file(uploaded_file)
                if generate_rag_db(file_path):
                    record_file_hash(file_path,"SUCCESS")
                else:
                    record_file_hash(file_path,"FAILED")
                ###process_file_for_rag(file_path)
                processed_files += 1
                ##time.sleep(1)
            else:
                print(f"File {uploaded_file.name} already available, ignoring it...")

        status_placeholder.text(f"{processed_files} file(s) processed")

    except Exception as e:
        st.error(f"Error during processing: {str(e)}")

def save_uploaded_file(uploaded_file) -> str:
    ## Save an uploaded file to the uploads directory
    if not os.path.exists(f"{st.session_state.user_dir}/uploads"):
        os.makedirs(f"{st.session_state.user_dir}/uploads")

    file_path = os.path.join(f"{st.session_state.user_dir}/uploads/",uploaded_file.name)
    print(f"SAVING UPLOADED FILE TO: {file_path}")
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getvalue())

    return file_path

# RAG: Build vector store and retriever per uploaded file, persisted on disk
def process_file_for_rag(file_path):
    loader = PyPDFLoader(file_path)
    document = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.split_documents(document)
    
    embeddings = OllamaEmbeddings(model="mxbai-embed-large")
    db_dir = str(Path(f"{st.session_state.datadir}/chroma").absolute())

    # Initialize or update a single persistent vector store
    if st.session_state.vectorstore is None:
        db = Chroma.from_documents(docs, embedding=embeddings, persist_directory=db_dir)
        st.session_state.vectorstore = db
    else:
        st.session_state.vectorstore.add_documents(docs)
    
    # Persist changes
    st.session_state.vectorstore.persist()

    # Create/update retriever
    st.session_state.retriever = st.session_state.vectorstore.as_retriever(search_kwargs={"k": 4})

def record_file_hash(file_path,status):
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    file_hash = hasher.hexdigest()

    # hash_record_path = os.path.join(f"{st.session_state.user_dir}/file_hashes/", os.path.basename(file_path) + ".hash")
    with open(f"{st.session_state.user_dir}/uploads-hash.txt", "a") as f:
        f.write(os.path.basename(file_path))
        f.write("\t")
        f.write(status)
        f.write("\t")
        f.write(file_hash)
        f.write("\n")

    print(f"Recorded hash for {file_path}: {file_hash}")
    return file_hash

def file_already_uploaded(uploaded_file):
    print(f"Checking hash for file: {uploaded_file.name}")
    hasher = hashlib.md5()
    buf = uploaded_file.getvalue()
    hasher.update(buf)
    file_hash = hasher.hexdigest()
    print(f"md5sum of the uploaded file {uploaded_file.name} is {file_hash}")
    try:
        with open(f"{st.session_state.user_dir}/uploads-hash.txt", "r") as f:
            content = f.read()
            return file_hash in content
    except Exception as e:
        return False
    
def extract_code_blocks(text):
    """
    Extract text from triple backtick code blocks.
    If no triple backtick blocks are found, return the original text as-is.
    """
    # Find all code blocks between triple backticks
    code_blocks = re.findall(r'```(?:[a-zA-Z0-9_-]*\n)?(.*?)```', text, re.DOTALL)

    print(f"Extracted code blocks: {code_blocks}")

    # If any code blocks are found, return them
    if code_blocks:
        return code_blocks

    # Otherwise, return the text as is
    print(f"No code blocks found, returning original text. {text}")
    return [text]
