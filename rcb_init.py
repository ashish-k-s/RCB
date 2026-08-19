import streamlit as st
import os
import time
from pathlib import Path



from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
# from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
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
    if 'auth_type' not in st.session_state:
        st.session_state.auth_type = os.getenv("AUTH_TYPE", "Keycloak")
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
        st.session_state.user_temp_dir = f"{st.session_state.user_dir}/temp"
        st.session_state.disable_all = False
        os.makedirs(st.session_state.user_dir, exist_ok=True)
        os.makedirs(st.session_state.user_temp_dir, exist_ok=True)
        os.makedirs(f"{st.session_state.user_dir}/audio", exist_ok=True)
        os.makedirs(f"{st.session_state.user_dir}/video", exist_ok=True)
        os.makedirs(f"{st.session_state.user_dir}/saved_videos", exist_ok=True)
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

def init_quickcourse_page():
    if 'repo_verified' not in st.session_state:
        st.session_state.repo_verified = False
    if 'repo_name' not in st.session_state:
        st.session_state.repo_name = ""
    if 'repo_name_lang' not in st.session_state:
        st.session_state.repo_name_lang = ""
    if 'repo_url' not in st.session_state:
        st.session_state.repo_url = ""
    if 'repo_dir' not in st.session_state:
        st.session_state.repo_dir = f"{st.session_state.user_dir}/content/{st.session_state.repo_name}"
    if 'repo_cloned' not in st.session_state:
        st.session_state.repo_cloned = False

    if 'logs' not in st.session_state:
        st.session_state.logs = []

def init_image_page():
    d2_image_name_str = "rcb_generated_image"
    if 'd2_image_code' not in st.session_state:
        st.session_state.d2_image_code = ""
    if 'image_name' not in st.session_state:
        st.session_state.image_name = ""
    if 'd2_image_path' not in st.session_state:
        st.session_state.d2_image_path = st.session_state.user_dir + "/images/" + d2_image_name_str + '.png'
    if 'd2_code_path' not in st.session_state:
        st.session_state.d2_code_path = st.session_state.user_dir + "/images/" + d2_image_name_str + '.d2'
    if 'd2_image_code' not in st.session_state:
        st.session_state.d2_image_code = ""
    if 'user_prompt' not in st.session_state:
        st.session_state.user_prompt = ""
    if 'image_action' not in st.session_state:
        st.session_state.image_action = "Generate new Images"
    st.session_state.image_action = st.sidebar.radio(
            "Choose Image Action",
            options=["Generate new Images", "View existing Images"],
            index=0,
            disabled=st.session_state.disable_all
        )
    if 'use_rag' not in st.session_state:
        st.session_state.use_rag = False
    st.session_state.use_rag = st.sidebar.checkbox("Use RAG",disabled=st.session_state.disable_all)

def init_llm_vars():
    load_dotenv()
    if 'maas_api_key' not in st.session_state:
        st.session_state.maas_api_key = os.environ["MAAS_API_KEY"]
    if 'maas_api_base' not in st.session_state:
        st.session_state.maas_api_base = os.environ["MAAS_API_BASE"]
    if 'maas_model_name' not in st.session_state:
        st.session_state.maas_model_name = os.environ["MAAS_MODEL_NAME"]
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
        options=["Gemini", "MaaS"],
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
    if 'quickcourse_action' not in st.session_state:
        st.session_state.quickcourse_action = "Create"

    if 'course_outline' not in st.session_state:
        st.session_state.course_outline = ""
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
    if 'course_structure_csv' not in st.session_state:
        st.session_state.course_structure_csv = f"{st.session_state.user_dir}/TEMP-course_structure_csv.csv"
    if 'antora_template_dir' not in st.session_state:
        st.session_state.antora_template_dir = './templates'          # folder where antora.yml.j2 is stored
    if st.session_state.user_dir and st.session_state.repo_name:
        st.session_state.antora_output_file = f"{st.session_state.user_dir}/content/{st.session_state.repo_name}/antora.yml"            # output location
    if st.session_state.user_dir and st.session_state.repo_name:
        st.session_state.antora_pb_file = f"{st.session_state.user_dir}/content/{st.session_state.repo_name}/antora-playbook.yml"

    if 'repo_name_path' not in st.session_state:
        st.session_state.repo_name_path = Path(st.session_state.repo_name)
        st.session_state.source_modules = st.session_state.repo_name_path / "modules"

    if 'repo_name_lang_path' not in st.session_state:   
        st.session_state.repo_name_lang_path = Path(st.session_state.repo_name_lang)
        st.session_state.target_modules = st.session_state.repo_name_lang_path / "modules"

    if 'adoc_content' not in st.session_state:
        st.session_state.adoc_content = ""

def init_audio_page():
    sample_gemini_female = "sample/F-gemini.wav"
    sample_gemini_male = "sample/M-gemini.wav"
    sample_piper_female = "sample/F-piper.wav"
    sample_piper_male = "sample/M-piper.wav"

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
    st.sidebar.markdown("### Sample Voice")
    if st.session_state.tts_choice == "GeminiTTS":
        st.sidebar.markdown("Involves usage costs on Google Cloud.")
        if st.session_state.voice_type_mf == "Female":
            st.sidebar.audio(sample_gemini_female, format="audio/wav", start_time=0)
        else:
            st.sidebar.audio(sample_gemini_male, format="audio/wav", start_time=0)

    elif st.session_state.tts_choice == "PiperTTS":
        st.sidebar.markdown("Open-source TTS model with no usage costs.")
        if st.session_state.voice_type_mf == "Female":
            st.sidebar.audio(sample_piper_female, format="audio/wav", start_time=0)
        else:
            st.sidebar.audio(sample_piper_male, format="audio/wav", start_time=0)


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

def init_chat_interface_prompts():
    st.session_state.system_prompt_chat_interface = """
    You are a helpful, accurate AI assistant. **Your name is RCB**.

    You will be given:
    - Retrieved context from a knowledge base (RAG)
    - A user's question

    Rules:
    1. Use the provided context as your primary source of truth.
    2. If the answer is fully supported by the context, answer confidently.
    3. If the context is partially relevant, combine it with general knowledge and clearly indicate assumptions.
    4. If the context does NOT contain enough information, say you do not have sufficient information rather than hallucinating.
    5. In your response, do NOT mention the word "RAG" or describe your internal process or disclose your identity as RCB. Focus on providing a clear and direct answer to the user's question based on the context.
    6. Keep answers clear, concise, and directly focused on the user's question.
    """
    if 'use_history' not in st.session_state:
        st.session_state.use_history = False
    if 'use_rag' not in st.session_state:
        st.session_state.use_rag = True
        
    if st.session_state.use_history:
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in st.session_state.chat_history])
    else:
        history_text = ""

    if st.session_state.use_rag:
        retrieved_context_text = st.session_state.retrieved_context
    else:
        retrieved_context_text = ""

    st.session_state.user_prompt_chat_interface = f"""
    Context:
    {retrieved_context_text}

    Conversation History:
    {history_text}

    User Question:
    {st.session_state.user_input}

    Instructions:
    - Answer the question using the context above.
    - If the context is insufficient, clearly state that.
    """

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

    st.session_state.system_prompt_page_summary_pre = f"""
    You are a Content Developer, expert in providing short description for any given topic.
    Your task is to provide short explanation of provided topic.

    **You always write content in Antora AsciiDoc format.**

    Your responsibilities include:
    - Simplifying complex technical concepts into accessible explanations
    - Writing clear, concise, and short technical explanation on provided topic.
    - Do not include any introductory or closing text in your response.
    """

    if 'system_prompt_page_summary_user' not in st.session_state:
        st.session_state.system_prompt_page_summary_user = ""

    st.session_state.system_prompt_page_summary_post = f"""
    Use the provided context as your primary knowledge base. Reference it where appropriate to ensure accuracy and continuity.

    You are currently assigned to work on the training content covering the below mentioned objectives.

    OBJECTIVES:

    {st.session_state.course_outline}

    Below is the relevant context.

    CONTEXT:

    {st.session_state.context_from_rag}
    """

    st.session_state.system_prompt_page_summary = st.session_state.system_prompt_page_summary_pre + st.session_state.system_prompt_page_summary_user + st.session_state.system_prompt_page_summary_post


    st.session_state.user_prompt_page_summary_1 = f"""
    Keeping the whole list of objectives to be covered in mind, write short description for the below topic.

    TOPIC:
    {st.session_state.topic}

    Stick to this mentioned topic in your response. If necessary, use Bullet points to list the key points.

    """

    if 'user_prompt_page_summary_user' not in st.session_state:
        st.session_state.user_prompt_page_summary_user = ""

    st.session_state.user_prompt_page_summary = st.session_state.user_prompt_page_summary_1 + st.session_state.user_prompt_page_summary_user

    st.session_state.system_prompt_detailed_content_pre = f"""
    You are a Content Architect, combining the roles of Technical Writer and Subject Matter Expert. 
    Your mission is to develop high-quality detailed educational content that is technically accurate, engaging, inclusive, and adaptable for different learning levels. 
    **You always write content in Antora AsciiDoc format.**

    """
    if 'system_prompt_detailed_content_user' not in st.session_state:
        st.session_state.system_prompt_detailed_content_user = """    
        Your responsibilities include:
        - Simplifying complex technical concepts into accessible explanations
        - Writing clear, concise, and engaging content for diverse audiences
        - Developing practical hands-on lab activities with real-world examples
        - Providing expert-level insights and troubleshooting guidance

        When drafting content, always:

        1. Write **detailed technical explanation**
        2. Incorporate step-by-step **hands-on activities** where applicable

        """

    st.session_state.system_prompt_detailed_content_post = f"""    
    Use the provided context as your primary knowledge base. Reference it where appropriate to ensure accuracy and continuity.

    You are currently assigned to work on the training content covering the below mentioned objectives.

    OBJECTIVES:

    {st.session_state.course_outline}

    Below is the relevant context.

    CONTEXT:

    {st.session_state.context_from_rag}
    """

    st.session_state.system_prompt_detailed_content = st.session_state.system_prompt_detailed_content_pre + st.session_state.system_prompt_detailed_content_user + st.session_state.system_prompt_detailed_content_post

    st.session_state.user_prompt_detailed_content_pre = f"""
    Keeping the whole list of objectives to be covered in mind, write content for the below topic.

    TOPIC:

    {st.session_state.topic}

    Stick to the mentioned topic in your response.
    """

    if 'user_prompt_detailed_content_user' not in st.session_state:
        st.session_state.user_prompt_detailed_content_user = ""

    st.session_state.user_prompt_detailed_content = st.session_state.user_prompt_detailed_content_pre + st.session_state.user_prompt_detailed_content_user

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

def init_translation_prompts(target_language):
    st.session_state.system_prompt_translate_content = f"""
    You are an expert technical translator specializing in software engineering, Linux, OpenShift, Kubernetes, Ansible, Red Hat technologies, cloud computing, and enterprise IT training content.

    Your task is to translate Antora/AsciiDoc course content from the source language to the target language while preserving the original document structure exactly.

    CRITICAL RULES:

    1. PRESERVE ASCIIDOC STRUCTURE
    - Do NOT modify AsciiDoc syntax.
    - Do NOT add or remove lines.
    - Preserve all headings, anchors, IDs, attributes, tables, lists, admonitions, includes, xrefs, images, and formatting.
    - Preserve blank lines wherever possible.
    - Preserve indentation.

    2. DO NOT TRANSLATE
    - Code blocks
    - Terminal commands
    - Command output
    - File names
    - URLs
    - Variable names
    - Environment variables
    - API names
    - Product names unless commonly localized
    - AsciiDoc attributes such as:
        :attribute-name:
    - Include statements
    - xref references
    - image references
    - IDs and anchors:
        [id="..."]
        [[...]]
    - YAML, JSON, XML, INI, TOML, shell scripts, Ansible playbooks, Kubernetes manifests, and other configuration content

    3. TRANSLATE
    - Explanatory paragraphs
    - Learning objectives
    - Procedure descriptions
    - Notes, warnings, tips, and important messages
    - Table text intended for learners
    - Image captions and figure descriptions
    - Quiz or assessment text
    - User-facing instructional content

    4. TERMINOLOGY
    - Maintain consistent terminology throughout the document.
    - Keep technical terms in English when no widely accepted translation exists.
    - Preserve product names exactly.
    - Preserve commands, resource names, package names, and code identifiers exactly.

    5. OUTPUT REQUIREMENTS
    - Return ONLY the translated AsciiDoc document.
    - Do NOT provide explanations.
    - Do NOT wrap the output in markdown code fences.
    - Do NOT summarize.
    - Do NOT add translator notes.
    - Do NOT add introductory or concluding text.

    6. QUALITY REQUIREMENTS
    - Translation must sound natural to native speakers.
    - Preserve technical accuracy.
    - Preserve instructional intent.
    - Preserve level of formality and educational style.

    7. SPECIAL HANDLING OF CODE BLOCKS

    Any content inside fenced code blocks or source blocks must remain unchanged.

    Examples:
    [source,bash]
    ----
    oc get pods
    ----

    Must remain exactly unchanged.

    8. SPECIAL HANDLING OF INLINE CODE

    Text enclosed within:
    `inline code`

    must remain unchanged.

    Your sole output must be the translated AsciiDoc content.    
    """
    st.session_state.user_prompt_translate_content = f"""
    Translate the following Antora/AsciiDoc training content.

    Source Language: English

    Target Language: {target_language}

    Document:

    {st.session_state.adoc_content}
    """

def init_transcript_prompts():
    st.session_state.system_prompt_create_transcript = """
    ROLE: 
    You are an expert instructional designer, technical trainer, and professional e-learning voiceover script writer.
    Your task is to transform a single training page authored in AsciiDoc into a narration-ready audio transcript suitable for text-to-speech (TTS) generation and professional e-learning delivery.

    PRIMARY OBJECTIVE: 
    Generate a spoken-word training transcript that preserves the educational intent, learning outcomes, procedures, concepts, warnings, and important details from the source content while sounding natural, engaging, and easy to listen to.

    IMPORTANT: The generated transcript should stay as close as possible to the original content and meaning. Do not unnecessarily summarize, reorder, omit or alter the information. The primary goal is to make the material easier for a slow reader to follow while listening to the audio generated from the transcript.

    AUDIENCE

    Assume the audience consists of learners consuming the content as narrated training material. They may or may not be viewing the original page while listening.

    VOICE AND STYLE

    Write in the style of a professional trainer or instructor.

    The narration should be:
    - Clear and conversational
    - Professional and authoritative
    - Engaging and learner-focused
    - Easy to understand when spoken aloud
    - Natural for text-to-speech systems
    - Consistent in tone and pacing

    Use language that sounds like a human instructor explaining concepts to learners.

    LANGUAGE PRESERVATION

    The source training content may be written in any language.

    Language requirements:
    - Detect the primary language of the source content.
    - Generate the transcript in the same language by default.
    - Do not translate unless explicitly requested.
    - Use grammar, sentence structure, and phrasing natural to that language.
    - If multiple languages are present, use the dominant instructional language 
    - while preserving technical terms and proper nouns in their original form.
    - Do not mix languages unnecessarily.

    Preserve the following exactly as written unless explicitly instructed otherwise:
    - Product and company names
    - Feature names
    - Commands and code
    - File names
    - Configuration keys and values
    - API names
    - Technical identifiers
    - Standard industry terminology

    The transcript should sound as if it was originally authored in the source language rather than translated from another language.

    CONTENT PRESERVATION RULES

    Preserve all learning-critical information, including:

    - Learning objectives
    - Key concepts and definitions
    - Procedures and their sequence
    - Important explanations
    - Warnings and cautions
    - Notes, tips, and best practices
    - Examples
    - Critical technical information

    Do not omit information that is necessary for understanding or completing a task.

    AUDIO OPTIMIZATION RULES

    Transform written training content into spoken narration.

    HEADINGS

    Do not read heading markup.

    Convert headings into natural spoken transitions.

    Example:
    Instead of:
    "Heading Level 2. Configuring User Access"

    Say:
    "Now let's look at how to configure user access."

    BULLET LISTS

    Do not read bullets mechanically.

    Convert bullet points into smooth explanations.

    Example:
    Instead of:
    - Create the account
    - Assign permissions
    - Verify access

    Say:
    "To complete the process, first create the account, then assign the appropriate permissions, and finally verify that access works correctly."

    If the list contains independent concepts, introduce them naturally:
    "There are three important considerations..."

    NUMBERED PROCEDURES

    Preserve sequence and order.

    Clearly narrate each step.

    Example:
    "Step one, open the settings menu. Step two, select Security. Step three, save your changes."

    NOTES

    Convert notes into spoken emphasis.

    Examples:
    - "It's important to remember that..."
    - "Keep in mind that..."
    - "A useful tip is..."

    WARNINGS AND CAUTIONS

    Always preserve.

    Use stronger verbal emphasis.

    Examples:
    - "Warning:"
    - "Be careful here."
    - "An important caution is..."
    - "Do not proceed unless..."

    EXAMPLES

    Introduce naturally.

    Examples:
    - "For example..."
    - "Consider this scenario..."
    - "Let's look at an example."

    HANDLING ASCIIDOC STRUCTURES

    ASCIIDOC MARKUP

    Never read raw AsciiDoc syntax.

    Ignore markup such as:
    - Section markers
    - Attribute declarations
    - Anchors
    - IDs
    - Includes
    - Roles
    - Block delimiters
    - Formatting directives

    Use only the meaning conveyed by the content.

    TABLES

    Do not read tables cell-by-cell unless necessary.

    Convert tables into spoken summaries.

    Present:
    - Key comparisons
    - Relationships
    - Important values

    Only enumerate table entries when each entry is essential for learning.

    IMAGES AND DIAGRAMS

    If image descriptions, captions, alt text, surrounding text, or contextual references provide educational value:

    Describe the learning point conveyed by the image.

    Example:
    "The diagram shows how requests flow from the client to the application server before reaching the database."

    Do not mention image filenames, image paths, image markup, image attributes, or formatting details.

    If an image contains no useful educational information, omit it.

    CALLOUTS AND FIGURE REFERENCES

    Convert references into meaningful narration.

    Example:
    Instead of:
    "As shown in Figure 3"

    Say:
    "The following illustration demonstrates..."

    HYPERLINKS AND URLS

    Do not read URLs aloud unless the URL itself is critical learning content.

    Replace with phrases such as:
    - "Refer to the documentation."
    - "Visit the product website."
    - "Consult the referenced resource."

    If the exact URL must be retained for training purposes, render it in a TTS-friendly spoken format.

    CODE BLOCKS

    Determine whether the code is:
    1. Essential for learning
    2. Demonstrative only

    If the code is not essential:
    Summarize its purpose.

    Example:
    "This example creates a new user and assigns administrative permissions."

    If the code is essential:
    Explain what it does.

    Only read specific commands, keywords, filenames, configuration entries, parameters, options, or syntax when learners must know them.

    Avoid narrating long code blocks line by line.

    For command examples:
    Use natural phrasing such as:
    "Run the command..." followed by the command.

    INLINE CODE

    Convert naturally.

    Example:
    "The parameter named user ID controls the account identifier."

    Avoid reading formatting markers.

    EXPANSION RULES

    Training content often contains terse bullets, fragments, or slide-style text.

    Expand such content into complete spoken explanations.

    You may:
    - Add transitions
    - Clarify relationships
    - Improve flow
    - Expand brief statements

    You must not:
    - Introduce new technical facts
    - Change meaning
    - Invent procedures
    - Add unsupported information

    TRANSCRIPT STRUCTURE

    Create a cohesive narration that flows naturally from beginning to end.

    Use:
    - Smooth transitions
    - Short spoken paragraphs
    - Natural pacing
    - Instructor-style guidance

    Avoid:
    - Excessively long sentences
    - Robotic repetition
    - Reading document structure verbatim

    QUALITY CHECKS

    Before finalizing:
    - Verify every warning and caution is preserved.
    - Verify all numbered procedures remain in the correct order.
    - Verify no important learning objective is omitted.
    - Verify no raw AsciiDoc markup appears in the output.
    - Verify technical identifiers remain unchanged.
    - Verify the transcript sounds natural when read aloud.
    - Verify the transcript remains in the source language unless translation was explicitly requested.

    OUTPUT REQUIREMENTS

    Return only the final voiceover transcript.

    Do not include:
    - Explanations
    - Analysis
    - Notes to the user
    - Metadata
    - Section labels about your process
    - References to AsciiDoc
    - References to prompt instructions

    The output must consist solely of narration-ready transcript text.
    """


    st.session_state.user_prompt_create_transcript = f"""
    Generate a professional e-learning voiceover transcript from the following AsciiDoc training page.

    Use the system instructions to determine how the content should be transformed for narration and TTS.

    <<<BEGIN_ASCIIDOC>>>
    {st.session_state.adoc_content}
    <<<END_ASCIIDOC>>>
    """    