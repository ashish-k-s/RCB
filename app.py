from langchain_openai import ChatOpenAI 
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.llms import Ollama
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

response = ""
outline = ""
topic = ""
course_outline_file = "TEMP-outline.adoc"
course_structure_file_names = "TEMP-course_structure_file_names.csv"

system_prompt_course_outline = """
You are a Course Designer expert in understanding the requirements of the curriculum and developing the course outline.
**You always write the course outline in AsciiDoc-formatted text inside a code block.**

Your job is **not** to write the course content. You follow the below rules to write course outline:
    - Refer to the provided list of course objectives and available context.
    - Curate the text in provided objectives.
    - Derive the sub-topics to be covered to fulfil the provided list of objectives.
    - **Always Restrict the structure to have only one level of sub-topics.**
    - **Derive heading for the course.**
    - Separate the layout to different topic and sub-topic as necessary.
    - **Include the section for hands-on lab when it is required.**
    - Respond with the curated list of objectives and sub-topics to be covered under each of the objectives.
    - Provide the output in a codeblock in AsciiDoc (.adoc) format.
    - **Always** use the below AsciiDoc syntax:
        - For course heading, use asciidoc Heading H1 with symbol "="
        - For topic, use asciidoc Heading H2 with symbol "=="
        - For sub-topic, use asciidoc Bullet with symbol "-"
    - Do not pre-fix "Objective" or "Module" or "Chapter" or any other such string in the generated output.
    - Do not number the topics, or add underline or any other decorations.
    - Do not include any introductory or closing text in your response.
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

"""

user_prompt_page_summary = """
Keeping the whole list of objectives tobe covered in mind, write short description (one paragraph) for the below topic:

{topic}

Stick to this mentioned topic in your response.

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

# --- Configuration for jinja2 file to generate antora.yml---
antora_template_dir = './templates'          # folder where antora.yml.j2 is stored
antora_output_file = 'antora.yml'            # output location
antora_csv_file = course_structure_file_names
antora_repo_name = 'sample-repo-name' # Get this from user input
antora_course_title = 'Sample Course Title' # Use the course heading fron csv file
antora_course_version = '1'

# --- Page layout configuration ---
st.set_page_config(
    page_title="Rapid course builder (RCB)",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    
# --- GitHub configuration ---
# Ensure these environment variables are set in your .env file or system environment
load_dotenv()
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_USER = os.environ["GITHUB_USER"]
TEMPLATE_REPO = os.environ["TEMPLATE_REPO"]
repo_name = "test-repo-from-template" # Get this from user input 

COMMIT_MESSAGE = os.environ["COMMIT_MESSAGE"] 
IS_PRIVATE = False

# --- Read chapter list from CSV file ---
def read_chapter_list(antora_csv_file):
    chapters = []
    sections = []
    chapter_name = ""
    section_name = ""
    try:
        with open(antora_csv_file, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip().startswith('==') and len(row) > 1:
                    chapter_name = row[1].strip()
                    chapters.append(chapter_name)
                    os.makedirs(f"modules/{chapter_name}", exist_ok=True)
                 
                    # Define the full file path for nav.adoc
                    section_path_nav = Path(f"modules/{chapter_name}/nav.adoc")
                    section_path_page = Path(f"modules/{chapter_name}/pages/{chapter_name}.adoc")

                    # Create the parent directories if they don't exist
                    section_path_nav.parent.mkdir(parents=True, exist_ok=True)
                    section_path_page.parent.mkdir(parents=True, exist_ok=True)

                    # Create the empty file
                    section_path_nav.touch()
                    section_path_page.touch()
                    with open(section_path_nav, 'a') as f:
                        f.write(f"* xref:{chapter_name}.adoc[]"+'\n')
                    with open(section_path_page, 'a') as f:
                        text = re.sub(r'(==|-)', '', row[0], count=1)
                        f.write(f"# {text}")

                        ## Build prompt and call llm to generate page summary
                        prompt = build_prompt(system_prompt_page_summary, user_prompt_page_summary)
                        print("BUILDING PAGE SUMMARY")
                        print("prompt: ", prompt)
                        chain = prompt | llm | output_parser
                        response = chain.invoke({"outline": outline, "topic": text})
                        print("PAGE SUMMARY: ", response)
                        ##st.write(response)
                        f.write("\n\n")
                        f.write(response)
                        # text = extract_code_blocks(response)
                        # print("CODEBLOCK SUMMARY: ", text)
                        # f.write(f"\n\n{text}")

                if row and row[0].strip().startswith('-') and len(row) > 1:
                    section_name = row[1].strip()
                    page_section_adoc = f"modules/{chapter_name}/pages/{section_name}.adoc"
                    with open(page_section_adoc, 'a') as f:
                        text = re.sub(r'(==|-)', '', row[0], count=1)
                        f.write(f"# {text}")
                        ## Build prompt and call llm to generate page content
                        prompt = build_prompt(system_prompt_detailed_content, user_prompt_detailed_content)
                        print("BUILDING PAGE CONTENT")
                        print("prompt: ", prompt)
                        chain = prompt | llm | output_parser
                        response = chain.invoke({"outline": outline, "topic": text})
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
        print(f"CSV file '{csv_file}' not found.")
    return chapters



# --- Render antora.yml template ---
def generate_antora_yml():
    chapters = read_chapter_list(antora_csv_file)

    env = Environment(loader=FileSystemLoader(antora_template_dir))
    template = env.get_template('antora.yml.j2')

    rendered = template.render(
        repo_name=antora_repo_name,
        course_title=antora_course_title,
        version=antora_course_version,
        chapters=chapters
    )

    with open(antora_output_file, 'w') as f:
        f.write(rendered)

    print(f"{antora_output_file} generated with chapters: {chapters}")

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
    shutil.copy2("antora.yml",st.session_state.repo_dir)
    dest_dir_modules = Path(st.session_state.repo_dir) / "modules"
    shutil.copytree("modules",dest_dir_modules,dirs_exist_ok=True)

def push_to_github():
    """
    Push the changes to the GitHub repository.
    """
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
        origin.push()  # Push changes to remote
        st.success("Changes pushed to GitHub successfully.")
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
        "owner": GITHUB_USER,
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
    url = f"https://api.github.com/repos/{GITHUB_USER}/{repo_name}"
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

# Sidebar on streamlit app
with st.sidebar:
    # GitHub Repository Information
    st.subheader("GitHub Repository")
    # st.write(f"Repository URL: {st.session_state.repo_url}")
    # st.write(f"Repository Verified: {st.session_state.repo_verified}")
    
    repo_name = st.text_input(
        "Repository Name",
        help="Enter the name of the GitHub repository"
    )

    # Repos setup button
    if st.button("Setup Repository", disabled=not repo_name.strip()):
        with st.spinner("Setting up repository..."):
            exists = check_github_repo_exists(repo_name)
            if exists:
                st.session_state.repo_verified = True
                st.markdown("Repository already exists. Content will be overwritten.")
                st.session_state.repo_url = f"https://github.com/{GITHUB_USER}/{repo_name}"
                add_log(f"Repository '{repo_name}' already exists. Content will be overwritten.")
            elif not exists:
                # If repository does not exist, create it
                st.session_state.repo_verified = False
                add_log(f"Creating new repository '{repo_name}'...")
                success = create_github_repo(repo_name)
                if success:
                    st.session_state.repo_verified = True
                    st.markdown("Repository created successfully.")
                    st.session_state.repo_url = f"https://github.com/{GITHUB_USER}/{repo_name}"
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
                    if not st.session_state.repo_dir:
                        temp_dir = tempfile.mkdtemp()
                        st.session_state.repo_dir = f"{temp_dir}/{st.session_state.repo_name}"
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



        # Enable the chat interface if repository is verified
        if not st.session_state.chat_enabled:
            st.session_state.chat_enabled = True
            

# --- Chat Interface ---
st. title("Rapid Course Builder (RCB)")

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
            disabled=st.session_state.show_logs
        )

        # Generate response button
        if st.button("Generate Response", disabled=not user_prompt.strip()) or st.session_state.show_logs:
            with st.spinner("Generating response..."):
                ## Build prompt to generate course outline
                prompt = build_prompt(system_prompt_course_outline, user_prompt_course_outline)
                chain = prompt | llm | output_parser
                # logger.info(f"PROMPT: {prompt}")
                # Call the LLM to generate response
                response = chain.invoke({"objectives": user_prompt})
                print("RESPONSE: \n", response)
                # st.write(response)
                st.session_state.chat_response = response
                # Add log entry
                add_log(f"User: {user_prompt}")
                add_log(f"LLM Response: {response}")

                # Display response
                if st.session_state.chat_response:
                    st.subheader("🤖 Response:")
                    st.write(st.session_state.chat_response)
                    print(response)
                    outline = extract_code_blocks(response)

                    ## Write course outline to an AsciiDoc file
                    with open(course_outline_file, "w") as file:
                        for line in outline:
                            file.write(line + "\n")
                st.session_state.show_proceed_button = True


        if st.session_state.show_proceed_button:
            if st.button("Proceed", disabled=st.session_state.show_logs):
                st.write("Proceeding with the next steps...")

                ## START: Derive name of the files for course structure

                ## Read outline.adoc in string
                with open(course_outline_file, 'r', encoding='utf-8') as file:
                    outline_file_content = file.read()

                print(outline_file_content)

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
