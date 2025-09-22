from langchain_openai import ChatOpenAI 
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.llms import Ollama
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings

from langchain_community.vectorstores import Chroma
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

import streamlit as st
import os
from dotenv import load_dotenv
import logging
import re
import csv
import sys
from io import StringIO
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

import tempfile
from github import Github
from git import Repo
import requests
import time
import io
from typing import List, Optional
import shutil

global response, topic
response = ""
outline = ""
topic = ""

FILE_SIZE_MAX = 10

system_prompt_course_outline = """
You are a Course Designer expert in understanding the requirements of the curriculum and developing the course outline.
**You always write the course outline in AsciiDoc-formatted text inside a code block.**

Your job is **not** to write the course content. You follow the below rules to write course outline:
    - Respond with the curated list of objectives and sub-topics to be covered under each of the objectives.
    - Provide the output in a codeblock in AsciiDoc (.adoc) format.
    - **Always** use the below AsciiDoc **syntax**:
        - For course heading, use asciidoc Heading H1 with symbol "="
        - For topic, use asciidoc Heading H2 with symbol "=="
        - For sub-topic, use asciidoc Bullet with symbol "-"
    - **Only modify the the provided list of objectives if they are not in the expected syntax.**
    - If the provided list of objectives are in the **expected syntax*, **use them as is** without any modifications.
    - **Always Restrict the structure to have only one level of sub-topics.**
    - **Derive heading for the course.**
    - Separate the layout to different topic and sub-topic as necessary.
    - **Include the section for hands-on lab only when it is required.**
    - Do not pre-fix "Objective" or "Module" or "Chapter" or any other such string in the generated output.
    - Do not number the topics, or add underline or any other decorations.
    - Do not include any introductory or closing text in your response.
    - Refer to the provided list of course objectives and available context.
    - Curate the text in provided objectives.
    - Derive the sub-topics to be covered to fulfil the provided list of objectives.

Context:
{context}
"""
#    - Provide topics and sub-topics in the form of bullets and sub-bullets.

user_prompt_course_outline = """
        Here are the list of objectives for which course outline is to be created: 
        {objectives}
"""

system_prompt_page_summary = """
You are a Content Developer, expert in providing short description for any given topic.
Your task is to provide short explanation of provided topic.

 **You always write content in Antora AsciiDoc format.**

Your responsibilities include:
- Simplifying complex technical concepts into accessible explanations
- Writing clear, concise, and short technical explanation on provided topic.
- Do not include any introductory or closing text in your response.

Use the provided context as your primary knowledge base. Reference it where appropriate to ensure accuracy and continuity.

You are currently assigned to work on the training content covering the below mentioned objectives:

{outline}

Relevant context:
{context}
"""

user_prompt_page_summary = """
Keeping the whole list of objectives tobe covered in mind, write short description (not more than 7 sentences) for the below topic:

{topic}

Stick to this mentioned topic in your response. If necessary, use Bullet points to list the key points.

"""
system_prompt_detailed_content = """
You are a Content Architect, combining the roles of Technical Writer and Subject Matter Expert. 
Your mission is to develop high-quality detailed educational content that is technically accurate, engaging, inclusive, and adaptable for different learning levels. 
**You always write content in Antora AsciiDoc format.**

Your responsibilities include:
- Simplifying complex technical concepts into accessible explanations
- Writing clear, concise, and engaging content for diverse audiences
- Developing practical hands-on lab activities with real-world examples
- Providing expert-level insights and troubleshooting guidance

When drafting content, always:

1. Write **detailed technical explanation**
2. Incorporate step-by-step **hands-on activities** where applicable

Use the provided context as your primary knowledge base. Reference it where appropriate to ensure accuracy and continuity.

You are currently assigned to work on the training content covering the below mentioned objectives:

{outline}

Relevant context:
{context}
"""

user_prompt_detailed_content = """
Keeping the whole list of objectives tobe covered in mind, write content for the below topic:

{topic}

Stick to the mentioned topic in your response.
"""

## Ollama model to generate response
llm = Ollama(model="granite3.3:8b")
output_parser = StrOutputParser()

def add_log(message: str):
    """Add a message to the logs"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.logs.append(f"[{timestamp}] {message}")

def build_prompt(system_prompt: str, user_prompt:str):
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", user_prompt)

        ]
    )


# --- Page layout configuration ---
# st.set_page_config(
#     page_title="Rapid course builder (RCB)",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )
st.title("Build QuickCourse using RCB")
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


# --- Initialize session state variables ---
if 'chat_enabled' not in st.session_state:
    st.session_state.chat_enabled = False
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'chat_responses' not in st.session_state:
    st.session_state.chat_response = ""
if 'show_proceed_button' not in st.session_state:
    st.session_state.show_proceed_button = False
if 'show_logs' not in st.session_state:
    st.session_state.show_logs = False
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'repo_verified' not in st.session_state:
    st.session_state.repo_verified = False
if 'repo_name' not in st.session_state:
    st.session_state.repo_name = ""
if 'repo_url' not in st.session_state:
    st.session_state.repo_url = ""
if 'repo_dir' not in st.session_state:
    st.session_state.repo_dir = "" 
if 'repo_cloned' not in st.session_state:
    st.session_state.repo_cloned = False
if 'antora_course_title' not in st.session_state:
    st.session_state.antora_course_title = ""
if 'desc_chapters' not in st.session_state:
    st.session_state.desc_chapters = []
if 'ai_prompt' not in st.session_state:
    st.session_state.ai_prompt = ""
if 'outline_str' not in st.session_state:
    st.session_state.outline_str = ""
if 'progress_logs' not in st.session_state:
    st.session_state.progress_logs = st.empty()
# RAG state
if 'vectorstore' not in st.session_state:
    st.session_state.vectorstore = None
if 'retriever' not in st.session_state:
    st.session_state.retriever = None

if 'datadir' not in st.session_state:
    st.session_state.datadir = tempfile.mkdtemp()

if 'modules_dir' not in st.session_state:
    st.session_state.modules_dir = Path(st.session_state.datadir) / "modules"
    st.session_state.modules_dir.mkdir(parents=True, exist_ok=True)

if 'use_maas' not in st.session_state:
    st.session_state.use_maas = True

# --- Configuration for jinja2 file to generate antora.yml---
course_outline_file = f"{st.session_state.datadir}/TEMP-outline.adoc"
course_structure_file_names = f"{st.session_state.datadir}/TEMP-course_structure_file_names.csv"
antora_template_dir = './templates'          # folder where antora.yml.j2 is stored
antora_output_file = f"{st.session_state.datadir}/antora.yml"            # output location
antora_pb_file = f"{st.session_state.datadir}/antora-playbook.yml"
antora_csv_file = course_structure_file_names
if st.session_state.repo_name:
    antora_repo_name = st.session_state.repo_name
    print(f"DEBUG: Assigned repo name: {antora_repo_name}")
    print(f"DEBUG: Using repo name from session state: {st.session_state.repo_name}")
#antora_course_title = 'Sample Course Title' # Use the course heading fron csv file
if st.session_state.antora_course_title:
    antora_course_title = st.session_state.antora_course_title
antora_course_version = '1'

# --- GitHub configuration ---
# Ensure these environment variables are set in your .env file or system environment
load_dotenv()
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_USER = os.environ["GITHUB_USER"]
GITHUB_ORG = os.environ["GITHUB_ORG"]
TEMPLATE_REPO = os.environ["TEMPLATE_REPO"]
repo_name = "test-repo-from-template" # Get this from user input 

COMMIT_MESSAGE = os.environ["COMMIT_MESSAGE"] 
IS_PRIVATE = False

# --- MaaS configuration ---
MAAS_API_KEY = os.environ["MAAS_API_KEY"]
MAAS_API_BASE = os.environ["MAAS_API_BASE"]

# --- Read chapter list from CSV file ---
def read_chapter_list(antora_csv_file):
    chapters = []
    sections = []
    chapter_name = ""
    section_name = ""
    global system_prompt_page_summary, user_prompt_page_summary, system_prompt_detailed_content, user_prompt_detailed_content
    
    try:
        with open(antora_csv_file, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip().startswith('=') and len(row) > 1:
                    antora_course_title = row[0].strip()
                    if not st.session_state.antora_course_title:
                        st.session_state.antora_course_title = antora_course_title
                    print(f"DEBUG: antora_course_title: {antora_course_title}")
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
                    # outline_str = f"""{outline[0]}"""
                    print("\n\nDEBUG: outline", outline)
                    print("\n\nDEBUG: outline_str", st.session_state.outline_str)

                    with open(section_path_nav, 'a') as f:
                        f.write(f"* xref:{chapter_name}.adoc[]"+'\n')
                    with open(section_path_page, 'a') as f:
                        text = re.sub(r'(==|-)', '', row[0], count=1)
                        f.write(f"# {text}")

                        ## Build prompt and call llm to generate page summary
                        
                        # Retrieve RAG context for this chapter/topic
                        context_text = retrieve_context(text)

                        # Build prompt with variables for outline/topic/context
                        prompt = build_prompt(system_prompt_page_summary, user_prompt_page_summary)
                        print("BUILDING PAGE SUMMARY")
                        st.session_state.progress_logs.info(f"Building page summary for topic: {text}")
                        print("prompt: ", prompt)
                        
                        if st.session_state.use_maas:
                            llm = ChatOpenAI(
                            openai_api_key=MAAS_API_KEY,   # Private model, we don't need a key
                            openai_api_base=MAAS_API_BASE,
                            model_name="granite-3-3-8b-instruct",
                            temperature=0.01,
                            max_tokens=512,
                            streaming=True,
                            callbacks=[StreamingStdOutCallbackHandler()],
                            top_p=0.9,
                            presence_penalty=0.5,
                            model_kwargs={
                                "stream_options": {"include_usage": True}
                            })

                        chain = prompt | llm | output_parser
                        response = chain.invoke({"outline": st.session_state.outline_str, "topic": text, "context": context_text})
                        print("PAGE SUMMARY: ", response)
                        ##st.write(response)
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
                        f.write(f"# {text}")
                        print(f"DEBUG: Topic text: {text}")
                        ## Build prompt and call llm to generate page content
                        # Retrieve RAG context for this section/topic
                        context_text = retrieve_context(text)

                        # Build prompt with variables for outline/topic/context
                        prompt = build_prompt(system_prompt_detailed_content, user_prompt_detailed_content)
                        print("BUILDING PAGE CONTENT")
                        st.session_state.progress_logs.info(f"Building page content for topic: {text}")
                        print("prompt: ", prompt)

                        if st.session_state.use_maas:
                            llm = ChatOpenAI(
                            openai_api_key=MAAS_API_KEY,   # Private model, we don't need a key
                            openai_api_base=MAAS_API_BASE,
                            model_name="granite-3-3-8b-instruct",
                            temperature=0.01,
                            max_tokens=512,
                            streaming=True,
                            callbacks=[StreamingStdOutCallbackHandler()],
                            top_p=0.9,
                            presence_penalty=0.5,
                            model_kwargs={
                                "stream_options": {"include_usage": True}
                            })

                        chain = prompt | llm | output_parser
                        response = chain.invoke({"outline": st.session_state.outline_str, "topic": text, "context": context_text})
                        print("PAGE CONTENT: ", response)
                        ##st.write(response)
                        f.write("\n\n")
                        f.write(response)
                        # text = extract_code_blocks(response)
                        # print("CODEBLOCK CONTENT: ", text)
                        # f.write(f"\n\n{text}")

                    with open(section_path_nav, 'a') as f:
                        f.write(f"** xref:{section_name}.adoc[]"+'\n')
            
                
    except FileNotFoundError:
        print(f"CSV file '{antora_csv_file}' not found.")
    return chapters



# --- Render antora.yml template ---
def generate_antora_yml():
    chapters = read_chapter_list(antora_csv_file)
    st.session_state.progress_logs.info(f"Generating supporting files")

    env = Environment(loader=FileSystemLoader(antora_template_dir))
    template = env.get_template('antora.yml.j2')
    template_pb = env.get_template('antora-playbook.yml.j2')
    template_root_index = env.get_template('root-index.adoc.j2')


    if st.session_state.antora_course_title:
        antora_course_title = st.session_state.antora_course_title.strip('=')

    topics = [chapter_desc.strip('=') for chapter_desc in st.session_state.desc_chapters]

    print(f"DEBUG: Assigned repo name: {antora_repo_name}")
    print(f"DEBUG: Using repo name from session state: {st.session_state.repo_name}")

    # print(f"==== antora_repo_name: {antora_repo_name}")
    print(f"==== st.session_state.repo_name: {st.session_state.repo_name}")
    rendered = template.render(
        repo_name=antora_repo_name,
        course_title=antora_course_title,
        version=antora_course_version,
        chapters=chapters
    )

    with open(antora_output_file, 'w') as f:
        f.write(rendered)

    rendered_pb = template_pb.render(
        repo_name=antora_repo_name,
        course_title=antora_course_title,
    )

    with open(antora_pb_file, 'w') as f:
        f.write(rendered_pb)

    print(f"DEBUG: antora_course_title: >>>>>>>>>> {antora_course_title}")
    print(f"DEBUG: st.session_state.antora_course_title: >>>>>>>>>> {st.session_state.antora_course_title}")
    print(f"DEBUG: st.session_state.desc_chapters: >>>>>>>>>> {st.session_state.desc_chapters}")


    rendered_root_index = template_root_index.render(
        course_title=antora_course_title,
        desc_chapters=topics
    )

    with open(f"{st.session_state.modules_dir}/ROOT/pages/index.adoc", 'w') as f:
        f.write(rendered_root_index)

    # Create nav.adoc file in ROOT
    with open(f"{st.session_state.modules_dir}/ROOT/nav.adoc", "w") as file:
        file.write("* xref:index.adoc[]\n")


    print(f"{antora_output_file} generated with chapters: {chapters}")
    print(f"Topics covered in the training: {st.session_state.desc_chapters}")


def move_course_content_to_repo():
    """
    Move the course content to the GitHub repository directory.
    This is temporary solution to move the course content files to the repository directory.
    Need to change the code to generate the course content files in the repository directory directly.
    """
    if not st.session_state.repo_dir:
        st.error("Repository directory is not set. Please verify the repository setup.")
        return

    # Ensure the repo directory exists
    repo_path = Path(st.session_state.repo_dir)
    if not repo_path.exists():
        st.error(f"Repository directory '{repo_path}' does not exist.")
        return

    # Move the course content files to the repository directory
    shutil.copy2(st.session_state.datadir+"/antora.yml",st.session_state.repo_dir)
    shutil.copy2(st.session_state.datadir+"/antora-playbook.yml",st.session_state.repo_dir)
    # shutil.copy2("antora-playbook.yml",st.session_state.repo_dir)

    dest_dir_modules = Path(st.session_state.repo_dir) / "modules"
    shutil.copytree(st.session_state.modules_dir,dest_dir_modules,dirs_exist_ok=True)

def push_to_github():
    """
    Push the changes to the GitHub repository.
    """
    st.session_state.progress_logs.info(f"Pushing changes to GitHub repository...")
    if not st.session_state.repo_dir:
        st.error("Repository directory is not set. Please verify the repository setup.")
        return

    repo_path = Path(st.session_state.repo_dir)
    if not repo_path.exists():
        st.error(f"Repository directory '{repo_path}' does not exist.")
        return

    try:
        repo = Repo(repo_path)
        repo.git.add(A=True)  # Add all changes
        repo.index.commit(COMMIT_MESSAGE)  # Commit changes
        origin = repo.remote(name='origin')
        origin.pull()  # Pull latest changes from remote to avoid conflicts
        origin.push()  # Push changes to remote
        time.sleep(5)  # Wait for a few seconds to ensure push is complete
        st.session_state.progress_logs.success(f"Changes pushed to GitHub repository '{st.session_state.repo_name}' successfully.")
        print(f"Changes pushed to GitHub repository '{st.session_state.repo_name}' successfully.")
    except Exception as e:
        st.error(f"Failed to push changes: {e}")


# Function to extract code block from the response generated by LLM.
def extract_code_blocks(text):
    # Match content between triple backticks
    code_blocks = re.findall(r'```(?:[a-zA-Z0-9]*\n)?(.*?)```', text, re.DOTALL)
    return code_blocks

# START: Code to generate filenames for each topic in the course outline.
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

    return output.getvalue()


def create_github_repo(repo_name) -> bool:
    """
    Function to create a GitHub repository using the GitHub API.
    Returns True if successful, False otherwise.
    """

    template_owner, template_repo_name = TEMPLATE_REPO.split('/')
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.baptiste-preview+json"
    }

    payload = {
        "owner": GITHUB_ORG,
        "name": repo_name,
        "description": "Repository created from template using script",
        "private": IS_PRIVATE,
        "include_all_branches": True
    }

    response = requests.post(
        f"https://api.github.com/repos/{template_owner}/{template_repo_name}/generate",
        headers=headers,
        json=payload
    )

    if response.status_code == 201:
        print(f"Repository '{repo_name}' created successfully.")
        st.session_state.repo_verified = True
        st.session_state.repo_url = response.json().get('html_url', '')
        return True
    else:
        print(f"Failed to create repository: {response.json()}")
        st.session_state.repo_verified = False
        st.session_state.repo_url = ""
        return False

def check_github_repo_exists(repo_name: str) -> bool:
    """Check if GitHub repository exists"""
    url = f"https://api.github.com/repos/{GITHUB_ORG}/{repo_name}"
    response = requests.get(url)
    if response.status_code == 200:
        print(f"Repository '{repo_name}' already exists.")
        st.session_state.repo_verified = True
        st.session_state.repo_url = response.json().get('html_url', '')
        return True
    elif response.status_code == 404:
        print(f"Repository '{repo_name}' does not exist.")
        st.session_state.repo_verified = False
        st.session_state.repo_url = ""
        return False
    else:
        print(f"Error checking repository: {response.json()}")
        st.session_state.repo_verified = False
        st.session_state.repo_url = ""
        return False

def convert_https_to_ssh(https_url: str) -> str:
    if https_url.startswith("https://github.com/"):
        repo_path = https_url.replace("https://github.com/", "")
        if repo_path.endswith(".git"):
            repo_path = repo_path[:-4]
        return f"git@github.com:{repo_path}.git"
    else:
        raise ValueError("Invalid GitHub HTTPS URL")

def update_ai_prompt():
    """
    Update the ai_prompt session state variable when the text area content changes.
    This function is called on change of the text area.
    """
    st.session_state.ai_prompt = st.session_state.get("ai_prompt", "")
    print(f"DEBUG: Updated ai_prompt: {st.session_state.ai_prompt}")
    # Debug info (remove this after testing)
    st.write(f"Debug - ai_prompt length: {len(st.session_state.ai_prompt) if st.session_state.ai_prompt else 0}")
    ai_prompt = st.text_area("AI generated topics:", 
                        height=300,
                        key="ai_prompt",on_change=update_ai_prompt)
    print(f"DEBUG: st.session_state.ai_prompt {st.session_state.ai_prompt}")
    #st.rerun()

def save_uploaded_file(uploaded_file) -> str:
    ## Save an uploaded file to the uploads directory
    if not os.path.exists("uploads"):
        os.makedirs(f"{st.session_state.datadir}/uploads")

    file_path = os.path.join(f"{st.session_state.datadir}/uploads/",uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getvalue())

    return file_path

# RAG: Build vector store and retriever per uploaded file, persisted on disk
def process_file(file_path):
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


# Helper to get retrieved context as a single string
def retrieve_context(query: str, max_tokens: int = 1500) -> str:
    try:
        if st.session_state.retriever is None or not query:
            return ""
        docs = st.session_state.retriever.get_relevant_documents(query)
        # Concatenate contents; optionally truncate to keep prompts reasonable
        combined = "\n\n".join(doc.page_content for doc in docs if getattr(doc, 'page_content', None))
        # Rough truncation by characters (token proxy)
        if len(combined) > max_tokens * 4:
            combined = combined[: max_tokens * 4]
        return combined
    except Exception as e:
        print(f"RAG retrieval failed: {e}")
        return ""


def process_uploaded_documents(uploaded_files):
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
            

            ### Save uploaded file
            file_path = save_uploaded_file(uploaded_file)
            print(f"FILE: {file_path}")
            process_file(file_path)
            processed_files += 1
            ##time.sleep(1)


        status_placeholder.text(f"{processed_files} file(s) processed")

    except Exception as e:
        st.error(f"Error during processing: {str(e)}")



# Sidebar on streamlit app
with st.sidebar:
    st.subheader("Document Upload")
    uploaded_files = st.file_uploader(
        "Upload Documents,",
        type=['pdf','txt'],
        accept_multiple_files=True,
        help=f"Upload documents to provide context for the AI. Max Size {FILE_SIZE_MAX} MB per file",
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

    # GitHub Repository Information
    st.subheader("GitHub Repository")
    # st.write(f"Repository URL: {st.session_state.repo_url}")
    # st.write(f"Repository Verified: {st.session_state.repo_verified}")
    
    repo_name = st.text_input(
        "Repository Name",
        help="Enter the name of the GitHub repository",
        disabled=st.session_state.disable_all
    )

    if not st.session_state.repo_name:
        st.session_state.repo_name = repo_name.strip()

    # Repos setup button
    if st.button("Setup Repository", disabled=not repo_name.strip()):
        with st.spinner("Setting up repository..."):
            exists = check_github_repo_exists(repo_name)
            if exists:
                st.session_state.repo_verified = True
                st.markdown("Repository already exists. Content will be overwritten.")
                st.session_state.repo_url = f"https://github.com/{GITHUB_ORG}/{repo_name}"
                add_log(f"Repository '{repo_name}' already exists. Content will be overwritten.")
            elif not exists:
                # If repository does not exist, create it
                st.session_state.repo_verified = False
                add_log(f"Creating new repository '{repo_name}'...")
                success = create_github_repo(repo_name)
                if success:
                    st.session_state.repo_verified = True
                    st.markdown("Repository created successfully.")
                    st.session_state.repo_url = f"https://github.com/{GITHUB_ORG}/{repo_name}"
                    add_log(f"Repository '{repo_name}' created successfully.")
                else:
                    st.session_state.repo_verified = False
                    st.session_state.repo_url = ""
                    add_log(f"Failed to create repository '{repo_name}'. Please check the logs.")
        
    # Show repository link if verified
    if st.session_state.repo_verified and st.session_state.repo_url:
        st.markdown(f"Repository URL: [View Repository]({st.session_state.repo_url})", unsafe_allow_html=True)

        # Clone the repository if it exists
        try:
            if not st.session_state.repo_cloned:
                # Use a spinner to indicate cloning process
                st.session_state.uploaded_files = []  # Reset uploaded files list
                st.session_state.repo_dir = ""  # Reset repo directory
                # Create a temporary directory to clone the repository
                with st.spinner("Cloning repository..."):
                    # Clone the repository to a temporary directory
                    time.sleep(5)
                    if not st.session_state.repo_dir:
                        temp_dir = tempfile.mkdtemp()
                        st.session_state.repo_dir = f"{st.session_state.datadir}/content/{st.session_state.repo_name}"
                        st.session_state.repo_dir = Path(st.session_state.repo_dir)
                    ssh_url = convert_https_to_ssh(st.session_state.repo_url)
                    Repo.clone_from(ssh_url, st.session_state.repo_dir)
                    print(f"Repository is cloned at '{st.session_state.repo_dir}'")
                    st.session_state.uploaded_files = os.listdir(st.session_state.repo_dir)
                    add_log(f"Repository '{st.session_state.repo_name}' from url '{st.session_state.repo_url}' cloned successfully at '{st.session_state.repo_dir}'.")
                    st.session_state.repo_cloned = True
        except Exception as e:
            st.error(f"Failed to clone repository: {e}")
            add_log(f"Error cloning repository '{st.session_state.repo_name}': {e}")
            st.session_state.repo_verified = False
            st.session_state.repo_url = ""  

        # Show required structure for the course objectives
        st.markdown("""
        **Required Structure for Training Objectives:**
                    
        - Use `=` for course heading
        - Use `==` for section headings
        - Use `-` for topics under sections
        """)

        st.session_state.use_maas = st.checkbox("Use Model as a Service",value=True)



        # Enable the chat interface if repository is verified
        if not st.session_state.chat_enabled:
            st.session_state.chat_enabled = True
            

# --- Chat Interface ---
# st.title("Rapid Course Builder (RCB)")

# Show logs are if enabled
if st.session_state.show_logs:
    st.subheader("Activity Logs")

    # Create scrollable area for logs
    log_container = st.container()
    with log_container:
        log_text = "\n".join(st.session_state.logs) if st.session_state.logs else "No logs available."
        st.text_area(
            "Logs",
            value=log_text,
            height=300,
            disabled=True,
            label_visibility="collapsed"
        )
    generate_antora_yml()
    move_course_content_to_repo()
    push_to_github()

    st.divider()

# Chat interface
if not st.session_state.show_logs: # Hide chat interface if logs are shown
    if st.session_state.chat_enabled:
        st.write("**Chat is enabled** - Repository verified successfully!")

        # Chat input box
        user_prompt = st.text_area(
            "Enter the list of training objectives to be covered:",
            placeholder="Type the training topics here...",
            height=300,
            key="user_prompt",
            disabled=st.session_state.show_logs
        )

        # Generate response button
        if st.button("Generate Response", disabled=not user_prompt.strip()) or st.session_state.show_logs:
            with st.spinner("Generating response..."):
                ## Build prompt to generate course outline
                # Retrieve context for outline generation based on the raw objectives text
                context_for_outline = retrieve_context(user_prompt)
                prompt = build_prompt(
                    system_prompt_course_outline,
                    user_prompt_course_outline
                )
                if st.session_state.use_maas:
                    llm = ChatOpenAI(
                    openai_api_key=MAAS_API_KEY,   # Private model, we don't need a key
                    openai_api_base=MAAS_API_BASE,
                    model_name="granite-3-3-8b-instruct",
                    temperature=0.01,
                    max_tokens=512,
                    streaming=True,
                    callbacks=[StreamingStdOutCallbackHandler()],
                    top_p=0.9,
                    presence_penalty=0.5,
                    model_kwargs={
                        "stream_options": {"include_usage": True}
                    })
                chain = prompt | llm | output_parser
                # logger.info(f"PROMPT: {prompt}")
                # Call the LLM to generate response
                response = chain.invoke({"objectives": user_prompt, "context": context_for_outline})
                print("RESPONSE: \n", response)
                # st.write(response)
                st.session_state.chat_response = response
                # Set the text area content directly
                st.session_state.ai_prompt = response
                # Add log entry
                add_log(f"User: {user_prompt}")
                add_log(f"LLM Response: {response}")
                st.session_state.show_proceed_button = True

        # Display response outside of button click handler so it persists
        if st.session_state.chat_response:
            st.subheader("🤖 Response:")
            
            #st.write(st.session_state.chat_response)
            #print(response)
            
            ai_prompt = st.text_area("AI generated topics:", 
                                    height=300,
                                    key="ai_prompt",on_change=update_ai_prompt)
            


        if st.session_state.show_proceed_button:
            if st.button("Proceed", disabled=st.session_state.show_logs):
                st.write("Proceeding with the next steps...")

                ## Extract code blocks from the current ai_promptcontent and write to file
                print(f"DEBUG: st.session_state.ai_prompt {st.session_state.ai_prompt}")
                outline = extract_code_blocks(st.session_state.ai_prompt)
                st.session_state.outline_str = f"""{outline[0]}"""
                print(f"=====DEBUG: outline: {outline}")
                print(f"=====DEBUG: outline_str: {st.session_state.outline_str}")

                ## Write course outline to an AsciiDoc file
                with open(course_outline_file, "w") as file:
                    for line in outline:
                        file.write(line + "\n")

                ## START: Derive name of the files for course structure

                ## Read outline.adoc in string
                with open(course_outline_file, 'r', encoding='utf-8') as file:
                    outline_file_content = file.read()

                print(f"DEBUG: outline_file_content: {outline_file_content}")

                csv_output = multiline_to_csv(outline_file_content)
                print(csv_output)

                with open(course_structure_file_names, 'w', encoding='utf-8') as file:
                    file.write(csv_output)

                ## END: Derive name of the files for course structure

                st.session_state.show_proceed_button = False
                st.session_state.show_submit_button = False
                st.session_state.show_logs = True
                st.session_state.logs.append("Proceeding to generate course layout...")
                st.session_state.logs.append(f"Course outline file generated: {course_outline_file}")   

                st.rerun()
                
# Footer section
st.divider()
st.caption("Rapid Course Builder (RCB) - Powered by LangChain and Streamlit")
