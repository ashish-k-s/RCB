import streamlit as st
import os
import time

from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
import google.generativeai as genai

def add_log(message: str):
    """Add a message to the logs"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.logs.append(f"[{timestamp}] {message}")
    print(f"LOG: {st.session_state.logs}")

def init_page():
    load_dotenv()
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
    if 'rag_enabled' not in st.session_state:
        st.session_state.rag_enabled = False
    if 'progress_logs' not in st.session_state:
        st.session_state.progress_logs = st.empty()

    print(f"User: {st.session_state.username}, User Dir: {st.session_state.user_dir}, Data Dir: {st.session_state.data_dir}")
      
def init_image_page():
    if 'd2_image_code' not in st.session_state:
        st.session_state.d2_image_code = ""
    if 'image_name' not in st.session_state:
        st.session_state.image_name = ""
def reset_quickcourse_state():
    st.session_state.update({
        "show_logs": False,
        "chat_enabled": True,
        "repo_verified": False,
        "course_outline": "",
        "context_for_outline": "",
        "topics_for_outline": "",
        "context_from_rag": "",
        "topic": "",
        "antora_course_title": "",
        "desc_chapters": [],
        "modules_dir": "",
        "course_outline_file": f"{st.session_state.user_dir}/TEMP-outline.adoc",
        "course_structure_file_names": f"{st.session_state.user_dir}/TEMP-course_structure_file_names.csv",
    })
    
def init_quickcourse_page():
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

    if 'logs' not in st.session_state:
        st.session_state.logs = []


def init_llm_vars():
    load_dotenv()
    if 'mass_api_key' not in st.session_state:
        st.session_state.mass_api_key = os.environ["MAAS_API_KEY"]
    if 'mass_api_base' not in st.session_state:
        st.session_state.mass_api_base = os.environ["MAAS_API_BASE"]
    if 'gemini_api_key' not in st.session_state:
        st.session_state.gemini_api_key = os.environ.get("GEMINI_API_KEY")

    if 'model_choice' not in st.session_state:
        st.session_state.model_choice = "MaaS"
    if 'response' not in st.session_state:
        st.session_state.response = ""
    if 'user_prompt' not in st.session_state:
        st.session_state.user_prompt = ""
    if 'system_prompt' not in st.session_state:
        st.session_state.system_prompt = ""

    st.session_state.model_choice = st.sidebar.selectbox(
        "Choose LLM Model",
        options=["MaaS", "Gemini", "Local"],
        index=0,
        disabled=st.session_state.disable_all
    )

def init_github_vars():
    load_dotenv()

    if 'github_token' not in st.session_state:
        st.session_state.github_token = os.environ["GITHUB_TOKEN"]
    if 'github_user' not in st.session_state:
        st.session_state.github_user = os.environ["GITHUB_USER"]
    if 'github_org' not in st.session_state:
        st.session_state.github_org = os.environ["GITHUB_ORG"]
    if 'template_repo' not in st.session_state:
        st.session_state.template_repo = os.environ["TEMPLATE_REPO"] 
    if 'commit_message' not in st.session_state:
        st.session_state.commit_message = os.environ["COMMIT_MESSAGE"] 
    if 'is_private' not in st.session_state:
        st.session_state.is_private = False

def init_quickcourse_vars():
    if 'course_outline' not in st.session_state:
        st.session_state.course_outline = ""
    # if 'course_structure_file_names' not in st.session_state:
    #     st.session_state.course_structure_file_names = ""
    if 'context_for_outline' not in st.session_state:
        st.session_state.context_for_outline = ""
    if 'topics_for_outline' not in st.session_state:
        st.session_state.topics_for_outline = ""
    if 'context_from_rag' not in st.session_state:
        st.session_state.context_from_rag = ""
    if 'topic' not in st.session_state:
        st.session_state.topic = ""

    if 'antora_course_title' not in st.session_state:
        st.session_state.antora_course_title = ""
    if 'desc_chapters' not in st.session_state:
        st.session_state.desc_chapters = []
    if 'modules_dir' not in st.session_state:
        st.session_state.modules_dir = ""

    # --- Configuration for jinja2 file to generate antora.yml---
    if 'course_outline_file' not in st.session_state:
        st.session_state.course_outline_file = f"{st.session_state.user_dir}/TEMP-outline.adoc"
    if 'course_structure_file_names' not in st.session_state:
        st.session_state.course_structure_file_names = f"{st.session_state.user_dir}/TEMP-course_structure_file_names.csv"
    if 'antora_template_dir' not in st.session_state:
        st.session_state.antora_template_dir = './templates'          # folder where antora.yml.j2 is stored
    if st.session_state.user_dir and st.session_state.repo_name:
        st.session_state.antora_output_file = f"{st.session_state.user_dir}/content/{st.session_state.repo_name}/antora.yml"            # output location
    if st.session_state.user_dir and st.session_state.repo_name:
        st.session_state.antora_pb_file = f"{st.session_state.user_dir}/content/{st.session_state.repo_name}/antora-playbook.yml"

def init_quickcourse_prompts():
    st.session_state.system_prompt_course_outline = f"""
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
    {st.session_state.context_for_outline}
    """
    #    - Provide topics and sub-topics in the form of bullets and sub-bullets.
    st.session_state.user_prompt_course_outline = f"""
            Here are the list of objectives for which course outline is to be created: 
            {st.session_state.topics_for_outline}
    """

    st.session_state.system_prompt_page_summary = f"""
    You are a Content Developer, expert in providing short description for any given topic.
    Your task is to provide short explanation of provided topic.

    **You always write content in Antora AsciiDoc format.**

    Your responsibilities include:
    - Simplifying complex technical concepts into accessible explanations
    - Writing clear, concise, and short technical explanation on provided topic.
    - Do not include any introductory or closing text in your response.

    Use the provided context as your primary knowledge base. Reference it where appropriate to ensure accuracy and continuity.

    You are currently assigned to work on the training content covering the below mentioned objectives:

    {st.session_state.course_outline}

    Relevant context:
    {st.session_state.context_from_rag}
    """

    st.session_state.user_prompt_page_summary = f"""
    Keeping the whole list of objectives to be covered in mind, write short description (not more than 7 sentences) for the below topic:

    {st.session_state.topic}

    Stick to this mentioned topic in your response. If necessary, use Bullet points to list the key points.

    """

    st.session_state.system_prompt_detailed_content = f"""
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

    {st.session_state.course_outline}

    Relevant context:
    {st.session_state.context_from_rag}
    """

    st.session_state.user_prompt_detailed_content = f"""
    Keeping the whole list of objectives to be covered in mind, write content for the below topic:

    {st.session_state.topic}

    Stick to the mentioned topic in your response.
    """

