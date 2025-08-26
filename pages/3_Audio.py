import streamlit as st
import subprocess
import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.llms import Ollama
from langchain_core.output_parsers import StrOutputParser

from audio import create_audio_file_from_transcript


st.set_page_config(
    page_title="Audio using RCB"
)

PROJECT_NAME = ""

st.title("Generate Audio using RCB")
st.sidebar.success("Select a page above.")

system_prompt_curate_transcript = """
You are an assistant that cleans and curates raw audio transcripts into natural, spoken-style text. 
Your goal is to make the text sound clear, fluent, and engaging when read aloud by a text-to-speech (TTS) system. 

Guidelines:
- Remove filler words (“um,” “uh,” “like,” “you know”) and false starts. 
- Fix grammar, tense, and sentence flow while preserving the speaker’s intent. 
- Break long sentences into shorter, spoken-style sentences. 
- Insert natural pauses using punctuation:
  - Commas (,) for short pauses.
  - Periods (.) for full stops.
  - Ellipses (…) or line breaks for longer pauses or dramatic effect.
- Retain a conversational tone while ensuring clarity. 
- Do not add new content or change meaning. 
- Do not include stage directions, notes, or commentary—output only the curated spoken text.

"""

user_prompt_curate_transcript = """
Here is a raw transcript that needs to be curated for TTS:

{user_prompt}

Please return the cleaned version with natural pauses and punctuation to guide speech.

"""

audio_file_name_str = "rcb_generated_audio"
if 'audio_file_path_wav' not in st.session_state:
    st.session_state.audio_file_path_wav = '/tmp/' + audio_file_name_str + '.wav'
if 'audio_file_path_mp3' not in st.session_state:
    st.session_state.audio_file_path_mp3 = '/tmp/' + audio_file_name_str + '.mp3'
if 'audio_file_path_txt' not in st.session_state:
    st.session_state.audio_file_path_txt = '/tmp/' + audio_file_name_str + '.txt'
if 'curated_transcript' not in st.session_state:
    st.session_state.curated_transcript = ""
if 'use_maas' not in st.session_state:
    st.session_state.use_maas = True

def build_prompt(system_prompt: str, user_prompt:str):
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", user_prompt)

        ]
    )

def curate_transcript_text():
    with st.spinner("Curating transcript..."):
        prompt = build_prompt(
            system_prompt_curate_transcript,
            user_prompt_curate_transcript
        )
        print(f"Generated prompt: {prompt}")
        chain = prompt | llm | output_parser
        # Call the LLM to generate response
        response = chain.invoke({"user_prompt": user_prompt})
        print("CURATED TRANSCRIPT: \n", response)
        # st.write(response)
        st.session_state.curated_transcript = response
        update_curated_transcript()

def update_curated_transcript():
    if st.session_state.curated_transcript:
        print(f"WRITING CONTENT TO FILE: {st.session_state.audio_file_path_txt} \n CONTENT: \n {st.session_state.curated_transcript}")
        with open(st.session_state.audio_file_path_txt, "w") as f:
            f.write(st.session_state.curated_transcript)
    st.rerun()

# --- MaaS configuration ---
load_dotenv()

MAAS_API_KEY = os.environ["MAAS_API_KEY"]
MAAS_API_BASE = os.environ["MAAS_API_BASE"]

if st.session_state.use_maas:
    print("USING MODEL AS A SERVICE")
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
else:
    print("USING LOCAL MODEL")
    llm = Ollama(model="granite3.3:8b")
    ##llm = Ollama(model="codellama:7b")
output_parser = StrOutputParser()

st.session_state.use_maas = st.sidebar.checkbox("Use Model as a Service",value=True)

user_prompt = st.text_area(
    "Write the audio transcript text to be curated here:",
    placeholder="Write the audio transcript text to be curated here...",
    height=300,
    key="user_prompt",
    #disabled=st.session_state.show_logs
)

curate_transcript = st.button("Curate Transcript")

st.session_state.curated_transcript = st.text_area(
   "Write or edit your audio transcript text here:",
    placeholder="Write your audio transcript text here...",
    value=st.session_state.curated_transcript,
    height=300,
    key="st.session_state.curated_transcript",
    on_change=update_curated_transcript
    )

create_audio_file = st.button("Create Audio File")

if curate_transcript:
    curate_transcript_text()

if create_audio_file:
    create_audio_file_from_transcript()
    st.audio(st.session_state.audio_file_path_mp3)


