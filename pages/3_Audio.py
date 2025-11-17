import streamlit as st
import subprocess
import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.llms import Ollama
from langchain_core.output_parsers import StrOutputParser

from rcb_audio import generate_audio_file_from_transcript, curate_transcript_text, show_audio_files, update_curated_transcript, save_audio_file
from rcb_init import init_audio_vars, init_audio_page, init_audio_prompts, init_page, init_llm_vars
from rcb_llm_manager import call_llm_to_generate_response


st.set_page_config(
    page_title="Audio using RCB"
)

st.title("Generate Audio using RCB")
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Audio"
st.session_state.current_page = "Audio"

init_page()
init_audio_page()
init_llm_vars()
init_audio_vars()
init_audio_prompts()

st.session_state.use_default_prompts = True

st.session_state.provided_transcript = st.text_area(
    "Write the audio transcript text to be curated here:",
    placeholder="Write the audio transcript text to be curated here...",
    height=300,
    #key="provided_transcript",
    disabled=st.session_state.disable_all
)

curate_transcript = st.button("Curate Transcript", disabled=st.session_state.disable_all)

st.session_state.curated_transcript = st.text_area(
   "Write or edit your audio transcript text here:",
    placeholder="Write your audio transcript text here...",
    value=st.session_state.curated_transcript,
    height=300,
    #key="st.session_state.curated_transcript",
    on_change=update_curated_transcript,
    disabled=st.session_state.disable_all
    )

col1, col2, col3 = st.columns(3)


if st.session_state.curated_transcript:
    with col1:        
        generate_audio = st.button("Generate Audio", disabled=st.session_state.disable_all)

    with col2:
        st.session_state.audio_file_name_str = st.text_input(" ", placeholder="Audio file name (without extension) here" , key="st.session_state.audio_file_name_str", label_visibility="collapsed", disabled=st.session_state.disable_all)

    with col3:
        save_audio = st.button("Save Audio", disabled=not bool(st.session_state.audio_file_name_str))

    if generate_audio:
        generate_audio_file_from_transcript()
    if save_audio:
        save_audio_file()
        # st.audio(st.session_state.audio_file_path_mp3)

if curate_transcript:
    curate_transcript_text()

st.divider()
st.markdown("### Audio files available:")

# Directory where audio files are located
if os.path.exists(st.session_state.audio_data_dir):
    show_audio_files()
else:
    st.info("No audio files found. Please generate and save an audio file to see it listed here.")