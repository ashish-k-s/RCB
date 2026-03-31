import streamlit as st
from dotenv import load_dotenv
import os
import glob
import shutil
import time



from rcb_init import init_page, init_llm_vars, init_quickcourse_page, init_quickcourse_vars, init_quickcourse_prompts

st.title("Build QuickCourse using RCB")
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'QuickCourse'
st.session_state.current_page = 'QuickCourse'

init_page()
init_llm_vars()
init_quickcourse_page()
init_quickcourse_vars()

from rcb_quickcourse import extract_code_blocks, multiline_to_csv, generate_antora_yml
from rcb_rag_manager import retrieve_context

from rcb_github import setup_github_repo, push_to_github, add_github_contributors
from rcb_llm_manager import call_llm_to_generate_response


# if 'vectorstore' not in st.session_state:
#     st.session_state.vectorstore = None
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

# if 'retriever' not in st.session_state:
#     st.session_state.retriever = None
if 'context_for_outline' not in st.session_state:
    st.session_state.context_for_outline = ""
if 'topics_for_outline' not in st.session_state:
    st.session_state.topics_for_outline = ""

if 'course_outline' not in st.session_state:
    st.session_state.course_outline = ""
if 'context_from_rag' not in st.session_state:
    st.session_state.context_from_rag = ""
    

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
        setup_github_repo()
        if st.session_state.repo_verified and st.session_state.repo_cloned:
            st.success("Repository setup successfully")
            add_github_contributors(github_contributors)
        else:
            st.error("Failed to setup repository. Contact us for support.")

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

if not st.session_state.show_logs: # Hide chat interface if logs are shown
    if st.session_state.chat_enabled:
        st.session_state.use_default_prompts = st.checkbox("Use default prompts (Recommended)", value=True, disabled=st.session_state.show_logs)

        if not st.session_state.use_default_prompts:
            st.markdown("**Make sure you know what you are doing.**")
            st.markdown("Feel free to contact us if you need any assistance with custom prompts.")
            init_quickcourse_prompts()
            with st.expander("Show/Hide prompts"):

                st.markdown("**System prompt for generating section summary:**")
                st.text(st.session_state.system_prompt_page_summary_pre)
                st.session_state.system_prompt_page_summary_user = st.text_area(
                    "User provided system prompt for page summary:", 
                    height=100, 
                    value=st.session_state.system_prompt_page_summary_user,
                    disabled=False,
                    label_visibility="collapsed"
                )
                st.text(st.session_state.system_prompt_page_summary_post)

                st.divider()

                st.markdown("**User prompt for generating section summary:**")
                st.text(st.session_state.user_prompt_page_summary_1)
                st.session_state.user_prompt_page_summary_user = st.text_area(
                    "User provided text for user prompt for page summary:", 
                    height=100, 
                    value=st.session_state.user_prompt_page_summary_user,
                    disabled=False,
                    label_visibility="collapsed"
                )

                st.markdown("**System prompt for generating detailed content on page:**")
                st.text(st.session_state.system_prompt_detailed_content_pre)
                st.session_state.system_prompt_detailed_content_user = st.text_area(
                    "User provided system prompt for page summary:", 
                    height=100, 
                    value=st.session_state.system_prompt_detailed_content_user,
                    disabled=False,
                    label_visibility="collapsed"
                )
                st.text(st.session_state.system_prompt_detailed_content_post)

                st.divider()

                st.markdown("**User prompt for generating detailed content on page:**")
                st.text(st.session_state.user_prompt_detailed_content_pre)
                st.session_state.user_prompt_detailed_content_user = st.text_area(
                    "User provided user prompt for page summary:", 
                    height=100, 
                    value=st.session_state.user_prompt_detailed_content_user,
                    disabled=False,
                    label_visibility="collapsed"
                )

                st.divider()


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
                # Retrieve context for outline generation based on the raw objectives text
                st.session_state.context_for_outline = retrieve_context(st.session_state.topics_for_outline)
                print(f"context for course outline {st.session_state.context_for_outline}")

                init_quickcourse_prompts() # Re-initialize prompts to update context and topics
                st.session_state.ai_generated_topics = call_llm_to_generate_response(st.session_state.model_choice, st.session_state.system_prompt_course_outline, st.session_state.user_prompt_course_outline)
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
    push_to_github()
    st.info("Reload the page to start a new QuickCourse creation process.")

