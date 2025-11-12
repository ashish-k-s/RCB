import streamlit as st
from dotenv import load_dotenv
import os
import glob
import shutil
import time

from rcb_init import init_page, init_llm_vars, init_quickcourse_page, init_quickcourse_vars, init_quickcourse_prompts, reset_quickcourse_state

st.title("Build QuickCourse using RCB")
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'QuickCourse'
st.session_state.current_page = 'QuickCourse'

init_page()
init_llm_vars()
init_quickcourse_page()
init_quickcourse_vars()

#from rcb_quickcourse import process_uploaded_documents, save_uploaded_documents
from rcb_quickcourse import process_uploaded_documents, extract_code_blocks, multiline_to_csv, generate_antora_yml, retrieve_context

from rcb_github import setup_github_repo, push_to_github, add_github_contributors
from rcb_llm_manager import call_llm_to_generate_response


if 'vectorstore' not in st.session_state:
    st.session_state.vectorstore = None
if 'chat_enabled' not in st.session_state:
    st.session_state.chat_enabled = False
if 'show_logs' not in st.session_state:
    st.session_state.show_logs = False
if 'chat_responses' not in st.session_state:
    st.session_state.chat_response = ""
if 'ai_generated_topics' not in st.session_state:
    st.session_state.ai_generated_topics = ""
if 'show_proceed_button' not in st.session_state:
    st.session_state.show_proceed_button = False

if 'retriever' not in st.session_state:
    st.session_state.retriever = None
if 'context_for_outline' not in st.session_state:
    st.session_state.context_for_outline = ""
if 'topics_for_outline' not in st.session_state:
    st.session_state.topics_for_outline = ""

if 'course_outline' not in st.session_state:
    st.session_state.course_outline = ""
if 'context_from_rag' not in st.session_state:
    st.session_state.context_from_rag = ""
    
# if 'system_prompt_course_outline' not in st.session_state:
#     st.session_state.system_prompt_course_outline = f"""
# You are a Course Designer expert in understanding the requirements of the curriculum and developing the course outline.
# **You always write the course outline in AsciiDoc-formatted text inside a code block.**

# Your job is **not** to write the course content. You follow the below rules to write course outline:
#     - Respond with the curated list of objectives and sub-topics to be covered under each of the objectives.
#     - Provide the output in a codeblock in AsciiDoc (.adoc) format.
#     - **Always** use the below AsciiDoc **syntax**:
#         - For course heading, use asciidoc Heading H1 with symbol "="
#         - For topic, use asciidoc Heading H2 with symbol "=="
#         - For sub-topic, use asciidoc Bullet with symbol "-"
#     - **Only modify the the provided list of objectives if they are not in the expected syntax.**
#     - If the provided list of objectives are in the **expected syntax*, **use them as is** without any modifications.
#     - **Always Restrict the structure to have only one level of sub-topics.**
#     - **Derive heading for the course.**
#     - Separate the layout to different topic and sub-topic as necessary.
#     - **Include the section for hands-on lab only when it is required.**
#     - Do not pre-fix "Objective" or "Module" or "Chapter" or any other such string in the generated output.
#     - Do not number the topics, or add underline or any other decorations.
#     - Do not include any introductory or closing text in your response.
#     - Refer to the provided list of course objectives and available context.
#     - Curate the text in provided objectives.
#     - Derive the sub-topics to be covered to fulfil the provided list of objectives.

# Context:
# {st.session_state.context_for_outline}
# """
# #    - Provide topics and sub-topics in the form of bullets and sub-bullets.

# if 'user_prompt_course_outline' not in st.session_state:
#     st.session_state.user_prompt_course_outline = f"""
#         Here are the list of objectives for which course outline is to be created: 
#         {st.session_state.topics_for_outline}
# """

# if 'system_prompt_page_summary' not in st.session_state:
#     st.session_state.system_prompt_page_summary = f"""
# You are a Content Developer, expert in providing short description for any given topic.
# Your task is to provide short explanation of provided topic.

#  **You always write content in Antora AsciiDoc format.**

# Your responsibilities include:
# - Simplifying complex technical concepts into accessible explanations
# - Writing clear, concise, and short technical explanation on provided topic.
# - Do not include any introductory or closing text in your response.

# Use the provided context as your primary knowledge base. Reference it where appropriate to ensure accuracy and continuity.

# You are currently assigned to work on the training content covering the below mentioned objectives:

# {st.session_state.course_outline}

# Relevant context:
# {st.session_state.context_from_rag}
# """

# if 'user_prompt_page_summary' not in st.session_state:
#     st.session_state.user_prompt_page_summary = f"""
# Keeping the whole list of objectives to be covered in mind, write short description (not more than 7 sentences) for the below topic:

# {topic}

# Stick to this mentioned topic in your response. If necessary, use Bullet points to list the key points.

# """
# if 'system_prompt_detailed_content' not in st.session_state:
#     st.session_state.system_prompt_detailed_content = f"""
# You are a Content Architect, combining the roles of Technical Writer and Subject Matter Expert. 
# Your mission is to develop high-quality detailed educational content that is technically accurate, engaging, inclusive, and adaptable for different learning levels. 
# **You always write content in Antora AsciiDoc format.**

# Your responsibilities include:
# - Simplifying complex technical concepts into accessible explanations
# - Writing clear, concise, and engaging content for diverse audiences
# - Developing practical hands-on lab activities with real-world examples
# - Providing expert-level insights and troubleshooting guidance

# When drafting content, always:

# 1. Write **detailed technical explanation**
# 2. Incorporate step-by-step **hands-on activities** where applicable

# Use the provided context as your primary knowledge base. Reference it where appropriate to ensure accuracy and continuity.

# You are currently assigned to work on the training content covering the below mentioned objectives:

# {st.session_state.course_outline}

# Relevant context:
# {context}
# """

# if 'user_prompt_detailed_content' not in st.session_state:
#     st.session_state.user_prompt_detailed_content = f"""
# Keeping the whole list of objectives to be covered in mind, write content for the below topic:

# {topic}

# Stick to the mentioned topic in your response.
# """

@st.dialog("Are you sure you want to clear all uploaded data? This can't be undone.")
def clear_uploaded_content():
    if st.button("Yes"):
        pattern = os.path.join(st.session_state.user_dir, "uploads*")
        paths = glob.glob(pattern)
        for path in paths:
            if os.path.isdir(path):
                print(f"Deleting directory: {path}")
                shutil.rmtree(path)
            if os.path.isfile(path):
                print(f"Deleting file: {path}")
                os.remove(path)
        st.rerun()
    else:
        pass

@st.dialog("List of contents added in RAG database")
def show_file_content_dialog(filepath):
    try:
        with open(filepath, "r") as f:
            content = f.read()
        #st.subheader(f"Content of: {filepath}")
        st.code(content, language="text") # Use st.code for raw text content
    except FileNotFoundError:
        st.error(f"File not found: {filepath}")

### change this dor doclin
# def retrieve_context(query: str, max_tokens: int = 1500) -> str:
#     try:
#         if st.session_state.retriever is None or not query:
#             return ""
#         docs = st.session_state.retriever.get_relevant_documents(query)
#         # Concatenate contents; optionally truncate to keep prompts reasonable
#         combined = "\n\n".join(doc.page_content for doc in docs if getattr(doc, 'page_content', None))
#         # Rough truncation by characters (token proxy)
#         if len(combined) > max_tokens * 4:
#             combined = combined[: max_tokens * 4]
#         return combined
#     except Exception as e:
#         print(f"RAG retrieval failed: {e}")
#         return ""

# def update_ai_generated_topics():
#     st.session_state.topics_for_outline = st.session_state.ai_generated_topics
#     print(f"Updated topics_for_outline: {st.session_state.topics_for_outline}")
#     st.session_state.show_proceed_button = True

# def update_topics_for_outline():
#     """
#     Update the topics_for_outline session state variable when the text area content changes.
#     This function is called on change of the text area.
#     """
#     st.session_state.topics_for_outline = st.session_state.get("st.session_state.topics_for_outline", "")
#     print(f"DEBUG: Updated topics_for_outline: {st.session_state.topics_for_outline}")
#     # Debug info (remove this after testing)
#     st.write(f"Debug - topics_for_outline length: {len(st.session_state.topics_for_outline) if st.session_state.topics_for_outline else 0}")
#     # topics_for_outline = st.text_area("Enter the list of training objectives to be covered:", 
#     #                     height=300,
#     #                     key="st.session_state.topics_for_outline",on_change=update_topics_for_outline)
#     print(f"DEBUG: st.session_state.topics_for_outline {st.session_state.topics_for_outline}")
#     # st.session_state.show_proceed_button = False
#     # st.session_state.ai_generated_topics = ""
#     #st.rerun()

def update_ai_generated_topics():
    """
    Update the ai_generated_topics session state variable when the text area content changes.
    This function is called on change of the text area.
    """
    st.session_state.ai_generated_topics = st.session_state.get("ai_generated_topics", "")
    print(f"DEBUG: Updated ai_generated_topics: {st.session_state.ai_generated_topics}")
    # Debug info (remove this after testing)
    st.write(f"Debug - ai_generated_topics length: {len(st.session_state.ai_generated_topics) if st.session_state.ai_generated_topics else 0}")
    # ai_generated_topics = st.text_area("AI generated topics:", 
    #                     height=300,
    #                     key="ai_generated_topics",on_change=update_ai_generated_topics)
    print(f"DEBUG: st.session_state.ai_generated_topics {st.session_state.ai_generated_topics}")
    st.session_state.show_proceed_button = True
    #st.rerun()

with st.sidebar:
    st.subheader("Document Upload")
    uploaded_files = st.file_uploader(
        "Upload Documents,",
        type=['pdf','txt'],
        accept_multiple_files=True,
        help=f"Upload documents to provide context for the AI. Supported formats: pdf, txt",
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

    st.subheader("GitHub Repository")
    repo_name = st.text_input(
        "Repository Name",
        help="Enter the name of the GitHub repository",
        disabled=st.session_state.disable_all
    )
    github_contributors = st.text_area(
        "Contributors (List of GitHub usernames separated by new line)",
        help="Enter GitHub usernames of contributors, separated by new line",
        disabled=st.session_state.disable_all
    )

    if not st.session_state.repo_name:
        st.session_state.repo_name = repo_name.strip()

    if st.button("Setup Repository", disabled=not st.session_state.repo_name):
        if setup_github_repo():
            st.success("Repository setup successfully")
            add_github_contributors(github_contributors)
        else:
            st.error("Failed to setup repository. Check logs for details.")

    if st.session_state.repo_verified:
        # Show required structure for the course objectives
        st.markdown("""
        **Required Structure for Training Objectives:**
                    
        - Use `=` for course heading
        - Use `==` for section headings
        - Use `-` for topics under sections
        """)
        st.markdown(f"Repository URL: [View Repository]({st.session_state.repo_url})", unsafe_allow_html=True)
        st.session_state.chat_enabled = True


# --- Chat Interface ---
# if not st.session_state.chat_enabled:
#     st.session_state.chat_enabled = True

if not st.session_state.show_logs: # Hide chat interface if logs are shown
    if st.session_state.chat_enabled:
        ###st.write("**Chat is enabled** - Repository verified successfully!")

        # Chat input box
        topics_outline = st.text_area(
            "Enter the list of training objectives to be covered:",
            placeholder="Type the training topics here...",
            height=300,
            key="topics_outline",
            disabled=st.session_state.show_logs
        )
        st.session_state.topics_for_outline = topics_outline
        # Curate topics button
        if st.button("Curate Topics", disabled=not st.session_state.topics_for_outline.strip()) or st.session_state.show_logs:
            with st.spinner("Curating provided list of topics..."):
                ## Build prompt to generate course outline
                # Retrieve context for outline generation based on the raw objectives text
                st.session_state.context_for_outline = retrieve_context(st.session_state.topics_for_outline)
                print(f"context for course outline {st.session_state.context_for_outline}")

                init_quickcourse_prompts() # Re-initialize prompts to update context and topics
                st.session_state.ai_generated_topics = call_llm_to_generate_response(st.session_state.model_choice, st.session_state.system_prompt_course_outline, st.session_state.user_prompt_course_outline)
                # st.session_state.ai_generated_topics = st.session_state.chat_response
                print("Curated objectives: \n", st.session_state.ai_generated_topics)
                
        # Display response outside of button click handler so it persists
        if st.session_state.ai_generated_topics:
            st.subheader("🤖 Curated objectives:")
            
            ai_generated_topics = st.text_area("AI generated topics:", 
                                    height=300,
                                    key="ai_generated_topics",
                                    disabled=st.session_state.show_logs,
                                    on_change=update_ai_generated_topics)
            
            st.session_state.show_proceed_button = True


        if st.session_state.show_proceed_button:
            if st.button("Proceed", disabled=st.session_state.show_logs):
                st.write("Proceeding with the next steps, you may scroll up to check the progress logs...")
                st.session_state.course_outline = extract_code_blocks(st.session_state.ai_generated_topics)
                print(f"Extracted outline: {st.session_state.course_outline}")

                st.session_state.course_outline_str = f"""{st.session_state.course_outline[0]}"""
                print(f"=====DEBUG: course_outline: {st.session_state.course_outline}")
                print(f"=====DEBUG: course_outline_str: {st.session_state.course_outline_str}")

                multiline_to_csv(st.session_state.course_outline_str)

# Show content generation progress
if st.session_state.show_logs:
    st.button("Reset", on_click=reset_quickcourse_state)

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
    # move_course_content_to_repo()
    push_to_github()

