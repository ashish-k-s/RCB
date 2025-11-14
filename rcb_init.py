import streamlit as st
import os
import time

from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
import google.genai as genai

def add_log(message: str):
    """Add a message to the logs"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.logs.append(f"[{timestamp}] {message}")
    print(f"LOG: {st.session_state.logs}")

def display_top_banner():
    load_dotenv()
    top_banner_message = os.getenv("BANNER_MESSAGE", "🚀 Welcome to Rapid Course Builder!")
    banner_markdown_text_1 = """
        <style>
            /* Create a fixed banner across the top of the page */
            .stApp {
                margin-top: 3rem;
            }
            .top-banner {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                background-color: #ffcc00;
                color: black;
                text-align: center;
                font-weight: bold;
                padding: 0.5rem;
                z-index: 9999;
                box-shadow: 0px 2px 6px rgba(0,0,0,0.1);
            }
        </style>
        """
    banner_markdown_text_2 = f"""
        <div class="top-banner">
            {top_banner_message}
        </div>
        """
    banner_markdown_text = banner_markdown_text_1 + banner_markdown_text_2
    st.markdown(banner_markdown_text,unsafe_allow_html=True)


def init_page():
    display_top_banner()
    load_dotenv()
    st.sidebar.info("Select a page above.")
    if 'data_dir' not in st.session_state:
        st.session_state.data_dir = os.getenv("DATA_DIR", "/tmp/rcb_data") 
    if 'user_dir' not in st.session_state:
        st.session_state.user_dir = ""
    if 'temp_dir' not in st.session_state:
        st.session_state.temp_dir = f"{st.session_state.data_dir}/temp"
    if 'username' not in st.session_state:
        st.session_state.username = ""
        st.session_state.disable_all = True
    if st.session_state.username:
        st.sidebar.success(f"Logged in as: {st.session_state.username}")
        st.session_state.user_dir = f"{st.session_state.data_dir}/{st.session_state.username}"
        st.session_state.disable_all = False
        os.makedirs(st.session_state.user_dir, exist_ok=True)
        os.makedirs(st.session_state.temp_dir, exist_ok=True)
        os.makedirs(f"{st.session_state.user_dir}/audio", exist_ok=True)
        os.makedirs(f"{st.session_state.user_dir}/video", exist_ok=True)
        os.makedirs(f"{st.session_state.user_dir}/images", exist_ok=True)
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
    
def init_quickcourse_page():
    if 'repo_verified' not in st.session_state:
        st.session_state.repo_verified = False
    if 'repo_name' not in st.session_state:
        st.session_state.repo_name = ""
    if 'repo_url' not in st.session_state:
        st.session_state.repo_url = ""
    if 'repo_dir' not in st.session_state:
        st.session_state.repo_dir = f"{st.session_state.user_dir}/content/{st.session_state.repo_name}"
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
        st.session_state.modules_dir = f"{st.session_state.user_dir}/content/{st.session_state.repo_name}/modules/"

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

def init_audio_page():
    st.session_state.tts_choice = st.sidebar.selectbox(
    "Choose TTS Model",
    options=["PiperTTS", "GeminiTTS"],
    index=0,
    disabled=st.session_state.disable_all
    )
    st.session_state.voice_type_mf = st.sidebar.radio(
        "Choose Voice Type",
        options=["Female", "Male"],
        index=0,
        disabled=st.session_state.disable_all
    )

def init_audio_vars():
    st.session_state.default_audio_file_name_str = "rcb_generated_audio"
    st.session_state.audio_data_dir = f"{st.session_state.user_dir}/audio"
    st.session_state.default_audio_file_path_wav = f"{st.session_state.audio_data_dir}/{st.session_state.default_audio_file_name_str}.wav"
    st.session_state.default_audio_file_path_mp3 = f"{st.session_state.audio_data_dir}/{st.session_state.default_audio_file_name_str}.mp3"
    st.session_state.default_audio_file_path_txt = f"{st.session_state.audio_data_dir}/{st.session_state.default_audio_file_name_str}.txt"

    if 'audio_file_name_str' not in st.session_state:
        st.session_state.audio_file_name_str = ""
    st.session_state.audio_file_path_txt = f"{st.session_state.audio_data_dir}/{st.session_state.audio_file_name_str}.txt"
    st.session_state.audio_file_path_wav = f"{st.session_state.audio_data_dir}/{st.session_state.audio_file_name_str}.wav"
    st.session_state.audio_file_path_mp3 = f"{st.session_state.audio_data_dir}/{st.session_state.audio_file_name_str}.mp3"
    if 'provided_transcript' not in st.session_state:
        st.session_state.provided_transcript = ""
    if 'curated_transcript' not in st.session_state:
        st.session_state.curated_transcript = ""

    st.session_state.gemini_tts_voice_female = 'Kore'
    st.session_state.gemini_tts_voice_male = 'Orus'

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

def init_audio_prompts():
    print("Initializing audio prompts...")
    st.session_state.system_prompt_curate_transcript = f"""
    You are an assistant that cleans and curates raw audio transcripts into natural, spoken-style text. 
    Your goal is to make the text sound clear, fluent, and engaging when read aloud by a text-to-speech (TTS) system. 

    Guidelines:
    - Remove filler words (“um,” “uh,” “like,” “you know”) and false starts. 
    - Fix grammar, tense, and sentence flow while preserving the speaker’s intent. 
    - Break long sentences into shorter, spoken-style sentences. 
    - Insert natural pauses using punctuation:
        - Commas (,) for short pauses.
        - Periods (.) for full stops and longer pauses.
        - Question marks (?) and exclamation points (!) as appropriate.
        - Ellipses (…) or line breaks for longer pauses or dramatic effect.
    - Retain a conversational tone while ensuring clarity. 
    - Do not add new content or change meaning. 
    - Do not include stage directions, notes, or commentary—output only the curated spoken text.
    """
    st.session_state.user_prompt_curate_transcript = f"""
    Here is a raw transcript that needs to be curated for TTS:

    {st.session_state.provided_transcript}

    Return the cleaned version with natural pauses and punctuation to guide speech.
    """
    st.session_state.gemini_tts_prompt = f"""
    Generate audio for a professional training module.
    Speaker: Voice with a clear American accent. 
    Tone: Professional, engaging, and informative. 
    Pace: Moderate and steady, with clear enunciation, ensuring every word is easy to understand. 
    Style: Instructional and authoritative, like an expert trainer guiding new learners.

    Text: {st.session_state.curated_transcript}

    """
