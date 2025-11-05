import streamlit as st
import os
import hashlib
import re
import csv

from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from io import StringIO

##Use doclin instead of below
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

from rcb_init import init_page, init_llm_vars, init_quickcourse_page, add_log, init_quickcourse_vars, init_quickcourse_prompts
from rcb_llm_manager import call_llm_to_generate_response

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

        # Create/update retriever
        st.session_state.retriever = st.session_state.vectorstore.as_retriever(search_kwargs={"k": 4})

        file_name = os.path.basename(file_path)
        st.success(f"RAG db generated for file: {file_name}")        
        return True
    except Exception as e:
        st.error(f"Error during generating RAG db")
        print(f"Error during generating RAG db: {str(e)}")
        return False

# Helper to get retrieved context as a single string
def retrieve_context(query: str, max_tokens: int = 1500) -> str:
    try:
        if st.session_state.retriever is None or not query:
            return ""
        docs = st.session_state.retriever.get_relevant_documents(query)
        print(f"DEBUG: RAG retrieved {len(docs)} documents for query: {query}")
        # Concatenate contents; optionally truncate to keep prompts reasonable
        combined = "\n\n".join(doc.page_content for doc in docs if getattr(doc, 'page_content', None))
        print(f"DEBUG: RAG combined content length: {len(combined)} characters")
        # Rough truncation by characters (token proxy)
        if len(combined) > max_tokens * 4:
            combined = combined[: max_tokens * 4]
        return combined
    except Exception as e:
        print(f"RAG retrieval failed: {e}")
        return ""

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
                process_file_for_rag(file_path)
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
    db_dir = str(Path(f"{st.session_state.user_dir}/chroma").absolute())

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

def generate_filename(text):
    # Convert to lowercase
    text = text.lower()
    
    # Replace special characters with space
    text = re.sub(r'[^\w\s-]', '', text)
    
    # Replace whitespace with a single hyphen
    text = re.sub(r'\s+', '-', text.strip())

    # Remove leading/trailing hyphens
    text = text.strip('-')

    return text

def multiline_to_csv(input_text):
    output = StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(["original_text", "filename"])

    for line in input_text.strip().splitlines():
        clean_line = line.strip()
        if clean_line:  # skip empty lines
            filename = generate_filename(clean_line)
            writer.writerow([clean_line, filename])

    csv_output = output.getvalue()
    print(csv_output)

    st.session_state.course_structure_csv = f"{st.session_state.user_dir}/TEMP-course_structure_file.csv"
    with open(st.session_state.course_structure_csv, 'w', encoding='utf-8') as file:
        file.write(csv_output)

    st.session_state.show_proceed_button = False
    st.session_state.show_submit_button = False
    st.session_state.show_logs = True
    st.session_state.logs.append("Proceeding to generate course layout...")
    st.session_state.logs.append(f"Course outline file generated: {st.session_state.course_outline_file}")

    st.rerun()

# --- Read chapter list from CSV file ---
def read_chapter_list(course_structure_csv):
    chapters = []
    sections = []
    chapter_name = ""
    section_name = ""
    print(f"DEBUG: Reading chapter list from {st.session_state.course_structure_csv}...")
    try:
        with open(st.session_state.course_structure_csv, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip().startswith('=') and len(row) > 1:

                    antora_course_title = row[0].strip()
                    if not st.session_state.antora_course_title:
                        st.session_state.antora_course_title = antora_course_title
                    print(f"DEBUG: st.session_state.antora_course_title: {st.session_state.antora_course_title}")

                if row and row[0].strip().startswith('==') and len(row) > 1:
                    chapter_name = row[1].strip()
                    chapters.append(chapter_name)
                    chapter_desc_str = row[0].strip()
                    st.session_state.desc_chapters.append(chapter_desc_str)

                    os.makedirs(f"{st.session_state.modules_dir}/{chapter_name}", exist_ok=True)
                 
                    # Define the full file path for nav.adoc
                    section_path_nav = Path(f"{st.session_state.modules_dir}/{chapter_name}/nav.adoc")
                    section_path_page = Path(f"{st.session_state.modules_dir}/{chapter_name}/pages/{chapter_name}.adoc")

                    root_path_nav = Path(f"{st.session_state.modules_dir}/ROOT/nav.adoc")
                    root_path_index = Path(f"{st.session_state.modules_dir}/ROOT/pages/index.adoc")
                    root_path_index.parent.mkdir(parents=True, exist_ok=True)     

                    # Create the parent directories if they don't exist
                    section_path_nav.parent.mkdir(parents=True, exist_ok=True)
                    section_path_page.parent.mkdir(parents=True, exist_ok=True)

                    root_path_nav.parent.mkdir(parents=True, exist_ok=True)

                    # Create the empty file
                    section_path_nav.touch()
                    section_path_page.touch()
                    root_path_nav.touch()
                    root_path_index.touch()
                    print("\n\nDEBUG: course_outline_str", st.session_state.course_outline_str)

                    with open(section_path_nav, 'a') as f:
                        f.write(f"* xref:{chapter_name}.adoc[]"+'\n')
                    with open(section_path_page, 'a') as f:
                        text = re.sub(r'(==|-)', '', row[0], count=1)
                        st.session_state.topic = text
                        f.write(f"# {text}")

                        ## Build prompt and call llm to generate page summary
                        
                        # Retrieve RAG context for this chapter/topic
                        st.session_state.context_from_rag = retrieve_context(text)

                        print("BUILDING PAGE SUMMARY")
                        st.session_state.progress_logs.info(f"Building page summary for topic: {text}")
                        init_quickcourse_prompts() # Re-initialize prompts to update context and topics
                        response = call_llm_to_generate_response(st.session_state.model_choice, st.session_state.system_prompt_page_summary, st.session_state.user_prompt_page_summary)
                        print("PAGE SUMMARY: ", response)
                        f.write("\n\n")
                        f.write(response)
                        # text = extract_code_blocks(response)
                        # print("CODEBLOCK SUMMARY: ", text)
                        # f.write(f"\n\n{text}")

                if row and row[0].strip().startswith('-') and len(row) > 1:
                    section_name = row[1].strip()
                    page_section_adoc = f"{st.session_state.modules_dir}/{chapter_name}/pages/{section_name}.adoc"
                    with open(page_section_adoc, 'a') as f:
                        text = re.sub(r'(==|-)', '', row[0], count=1)
                        st.session_state.topic = text
                        f.write(f"# {text}")
                        print(f"DEBUG: Topic text: {text}")
                        ## Build prompt and call llm to generate page content
                        # Retrieve RAG context for this section/topic
                        st.session_state.context_from_rag = retrieve_context(text)

                        print("BUILDING PAGE CONTENT")
                        st.session_state.progress_logs.info(f"Building page content for topic: {text}")


                        print("BUILDING PAGE SUMMARY")
                        st.session_state.progress_logs.info(f"Building page summary for topic: {text}")
                        
                        init_quickcourse_prompts() # Re-initialize prompts to update context and topics
                        response = call_llm_to_generate_response(st.session_state.model_choice, st.session_state.system_prompt_detailed_content, st.session_state.user_prompt_detailed_content)
                        print("PAGE SUMMARY: ", response)
                        ##st.write(response)
                        f.write("\n\n")
                        f.write(response)

                    with open(section_path_nav, 'a') as f:
                        f.write(f"** xref:{section_name}.adoc[]"+'\n')
            
                
    except FileNotFoundError:
        print(f"CSV file '{st.session_state.course_structure_csv}' not found.")
    return chapters

# --- Render antora.yml template ---
def generate_antora_yml():
    chapters = read_chapter_list(st.session_state.course_structure_csv)
    st.session_state.progress_logs.info(f"Generating supporting files")

    env = Environment(loader=FileSystemLoader(st.session_state.antora_template_dir))
    template = env.get_template('antora.yml.j2')
    template_pb = env.get_template('antora-playbook.yml.j2')
    template_root_index = env.get_template('root-index.adoc.j2')

    print(f"DEBUG: antora_course_title before assignment: >>>>>>>>>> {st.session_state.antora_course_title}")
    if st.session_state.antora_course_title:
        course_title_str = st.session_state.antora_course_title.strip('=')

    topics = [chapter_desc.strip('=') for chapter_desc in st.session_state.desc_chapters]

    print(f"DEBUG: Assigned repo name: {st.session_state.repo_name}")
    print(f"DEBUG: course title: {course_title_str}")

    print(f"==== st.session_state.repo_name: {st.session_state.repo_name}")
    rendered = template.render(
        repo_name=st.session_state.repo_name,
        course_title=course_title_str,
        version='1.0.0',
        chapters=chapters
    )

    print(f"DEBUG: antora_output_file: >>>>>>>>>> {st.session_state.antora_output_file}")
    with open(st.session_state.antora_output_file, 'w') as f:
        f.write(rendered)

    rendered_pb = template_pb.render(
        repo_name=st.session_state.repo_name,
        course_title=course_title_str,
    )

    with open(st.session_state.antora_pb_file, 'w') as f:
        f.write(rendered_pb)

    print(f"DEBUG: antora_course_title: >>>>>>>>>> {st.session_state.antora_course_title}")
    print(f"DEBUG: st.session_state.antora_course_title: >>>>>>>>>> {st.session_state.antora_course_title}")
    print(f"DEBUG: st.session_state.desc_chapters: >>>>>>>>>> {st.session_state.desc_chapters}")


    rendered_root_index = template_root_index.render(
        course_title=course_title_str,
        desc_chapters=topics
    )

    with open(f"{st.session_state.modules_dir}/ROOT/pages/index.adoc", 'w') as f:
        f.write(rendered_root_index)

    # Create nav.adoc file in ROOT
    with open(f"{st.session_state.modules_dir}/ROOT/nav.adoc", "w") as file:
        file.write("* xref:index.adoc[]\n")


    print(f"{st.session_state.antora_output_file} generated with chapters: {chapters}")
    print(f"Topics covered in the training: {st.session_state.desc_chapters}")
