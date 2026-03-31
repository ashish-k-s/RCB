import streamlit as st
import hashlib
import os
import shutil

##Use doclin instead of below
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
# from langchain_huggingface import HuggingFaceEmbeddings
from langchain_milvus import Milvus
from langchain_community.embeddings import HuggingFaceEmbeddings
from docling.document_converter import DocumentConverter
from langchain_docling.loader import ExportType
from langchain_docling import DoclingLoader
from docling.chunking import HybridChunker


from pathlib import Path
import json

def get_embedding():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-mpnet-base-v2"
    )

def is_supported_metadata_value(value):
    # Chroma accepts simple scalars, lists of scalars, and None.
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, list):
        return all(is_supported_metadata_value(item) for item in value)
    return False


def sanitize_metadata(metadata):
    sanitized = {}
    for key, value in metadata.items():
        if is_supported_metadata_value(value):
            sanitized[key] = value
            continue

        if isinstance(value, dict):
            # Serialize nested metadata dict to JSON string (avoids unsupported dict in Chroma).
            try:
                sanitized[key] = json.dumps(value, ensure_ascii=False)
            except Exception:
                sanitized[key] = str(value)
            continue

        if isinstance(value, list):
            cleaned_list = []
            for item in value:
                if is_supported_metadata_value(item):
                    cleaned_list.append(item)
                elif isinstance(item, dict):
                    try:
                        cleaned_list.append(json.dumps(item, ensure_ascii=False))
                    except Exception:
                        cleaned_list.append(str(item))
                else:
                    cleaned_list.append(str(item))
            sanitized[key] = cleaned_list
            continue

        # Fallback to string representation for other unsupported types.
        sanitized[key] = str(value)

    return sanitized


def process_uploaded_documents(uploaded_files):
    print(f"Processing {len(uploaded_files)} uploaded files...")
    if not uploaded_files:
        return
    total_files = len(uploaded_files)
    progress_bar = st.progress(0)
    status_placeholder = st.empty()

    processed_files = 0
    
    # try:
    for i, uploaded_file in enumerate(uploaded_files):
        progress = (i + 1) / total_files
        progress_bar.progress(progress)
        status_placeholder.text(f"Processing {i + 1} of {total_files}: {uploaded_file.name}")
        if not file_already_uploaded(uploaded_file):
            print(f"Saving {uploaded_file.name}...")
            ### Save uploaded file
            file_path = save_uploaded_file(uploaded_file)
            ### Generate RAG db for the uploaded file
            st.toast(f"Generating RAG db for file: {uploaded_file.name}")
            if generate_rag_db(file_path):
                st.toast(f"Converting {uploaded_file.name} to markdown format...")
            if generate_markdown_file(file_path):
                record_file_hash(file_path,"SUCCESS")
            else:
                record_file_hash(file_path,"FAILED")
            processed_files += 1
            ##time.sleep(1)
        else:
            print(f"File {uploaded_file.name} already available, ignoring it...")

    status_placeholder.text(f"{processed_files} file(s) processed")

    # except Exception as e:
    #     st.error(f"Error during processing: {str(e)}")

def save_uploaded_file(uploaded_file) -> str:
    ## Save an uploaded file to the uploads directory
    if not os.path.exists(f"{st.session_state.user_dir}/uploads"):
        os.makedirs(f"{st.session_state.user_dir}/uploads")

    file_path = os.path.join(f"{st.session_state.user_dir}/uploads/",uploaded_file.name)
    print(f"SAVING UPLOADED FILE TO: {file_path}")
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getvalue())

    return file_path

def record_file_hash(file_path,status):
    file_name = os.path.basename(file_path)
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

@st.dialog("List of contents added in RAG database")
def show_file_content_dialog(filepath):
    try:
        with open(filepath, "r") as f:
            content = f.read()
        #st.subheader(f"Content of: {filepath}")
        st.code(content, language="text") # Use st.code for raw text content
    except FileNotFoundError:
        st.error(f"File not found: {filepath}")

@st.dialog("Are you sure you want to clear all uploaded data? This can't be undone.")
def clear_uploaded_content():
    if st.button("Yes"):
        for dir in ["uploads", "rag_db"]:
            dir_to_delete = os.path.join(st.session_state.user_dir, dir)
            files_to_delete = os.path.join(st.session_state.user_dir, f"uploads-hash.txt")
            os.remove(files_to_delete) if os.path.exists(files_to_delete) else None

            # Delete hash file if exists
            if os.path.exists(dir_to_delete):
                try:
                    shutil.rmtree(dir_to_delete)
                    print(f"Successfully deleted directory: {dir_to_delete}")
                except OSError as e:
                    print(f"Error deleting directory {dir_to_delete}: {e}")
            else:
                print(f"Directory not found: {dir_to_delete}")
        st.rerun()
    else:
        pass

def generate_markdown_file(file_path):
    converter = DocumentConverter()
    result = converter.convert(file_path)
    markdown_content = result.document.export_to_markdown()
    with open(f"{file_path}.md", "w") as f:
        f.write(markdown_content)
    return True

def generate_rag_db(file_path):
    # loader = DoclingLoader(file_path, export_type=ExportType.MARKDOWN, chunker=HybridChunker(tokenizer="sentence-transformers/all-MiniLM-L6-v2"))
    TOP_K = 3
    MILVUS_URI = f"{st.session_state.user_dir}/rag_db/rag_db.db"
    EMBEDDING_MODEL = "sentence-transformers/multi-qa-mpnet-base-dot-v1"

    # loader = DoclingLoader(file_path, export_type=ExportType.DOC_CHUNKS, chunker=HybridChunker(tokenizer=EMBEDDING_MODEL))

    loader = DoclingLoader(file_path=file_path)
    document = loader.load()

    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3")
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on, strip_headers=False)

    header_splits = []
    for doc in document:
        splits = markdown_splitter.split_text(doc.page_content)
        for split in splits:
            split.metadata.update(doc.metadata)
            split.metadata = sanitize_metadata(split.metadata)
            header_splits.append(split)

    # Further split into smaller chunks to fit embedding model max seq length (512)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=256)
    final_splits = []
    for split in header_splits:
        sub_splits = text_splitter.split_documents([split])
        for sub in sub_splits:
            sub.metadata = split.metadata  # Ensure metadata is copied
            final_splits.append(sub)

    # embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    embeddings = get_embedding()
    persist_dir = f"{st.session_state.user_dir}/rag_db"

    if os.path.exists(persist_dir):
        # Load existing vectorstore and add new documents
        vectorstore = Chroma(persist_directory=persist_dir, embedding_function=embeddings)
        vectorstore.add_documents(final_splits)
    else:
        # Create new vectorstore
        if os.path.exists(persist_dir):
            shutil.rmtree(persist_dir)
        print(f"Creating new RAG vectorstore at: {persist_dir}")
        vectorstore = Chroma.from_documents(documents=final_splits, embedding=embeddings, persist_directory=persist_dir)

    st.session_state.vectorstore = vectorstore
    return True

# Helper to get retrieved context as a single string
def retrieve_context(query: str, max_tokens: int = 1500) -> str:
    # Defensive checks - ensure vectorstore exists and is initialized.
    if not hasattr(st.session_state, 'vectorstore') or st.session_state.vectorstore is None:
        persist_dir = f"{st.session_state.user_dir}/rag_db"
        if os.path.exists(persist_dir):
            embeddings = get_embedding()
            # embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            st.session_state.vectorstore = Chroma(persist_directory=persist_dir, embedding_function=embeddings)
        else:
            st.warning("No RAG vectorstore available yet. Upload a document first to use RAG context.")
            return ""

    st.session_state.retriever = st.session_state.vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 4})

    # relevant_docs = st.session_state.retriever.get_relevant_documents(query)
    relevant_docs = st.session_state.retriever.invoke(query)
    print(f"DEBUG: RAG retrieved {len(relevant_docs)} documents for query: {query}")
    combined = "\n\n".join([doc.page_content for doc in relevant_docs])
    # Concatenate contents; optionally truncate to keep prompts reasonable
    # combined = "\n\n".join(doc.page_content for doc in relevant_docs if getattr(doc, 'page_content', None))
    print(f"DEBUG: RAG combined content length: {len(combined)} characters")
    # Rough truncation by characters (token proxy)
    if len(combined) > max_tokens * 4:
        combined = combined[: max_tokens * 4]
    return combined
    # except Exception as e:
    #     print(f"RAG retrieval failed: {e}")
    #     return ""

