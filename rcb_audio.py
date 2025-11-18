import os
from pathlib import Path
import streamlit as st
import subprocess
import shutil

from rcb_init import init_audio_vars, init_audio_prompts
from rcb_llm_manager import call_llm_to_generate_response

from google import genai
from google.genai import types
import wave
import os
import base64
import struct


def curate_transcript_text():
    #st.session_state.audio_file_name_str = "rcb_generated_audio"
    init_audio_vars()
    print(f"Generating audio file at: {st.session_state.default_audio_file_path_txt}")
    audio_dir = os.path.dirname(st.session_state.default_audio_file_path_txt)
    print(f"Ensuring audio directory exists at: {audio_dir}")
    audio_dir = Path(audio_dir)
    audio_dir.mkdir(parents=True, exist_ok=True)
    with st.spinner("Curating transcript..."):
        # print(f"DEBUG PROVIDED TRANSCRIPT: \n {st.session_state.provided_transcript}")
        # init_audio_prompts()
        print(f"SYSTEM PROMPT: \n {st.session_state.system_prompt_curate_transcript}")
        print(f"USER PROMPT: \n {st.session_state.user_prompt_curate_transcript}")
        response = call_llm_to_generate_response(st.session_state.model_choice,st.session_state.system_prompt_curate_transcript, st.session_state.user_prompt_curate_transcript)
        print("CURATED TRANSCRIPT: \n", response)
        # st.write(response)
        st.session_state.curated_transcript = response
        update_curated_transcript()

def update_curated_transcript():
    print(f"WRITING CONTENT TO FILE: {st.session_state.default_audio_file_path_txt} \n CONTENT: \n {st.session_state.curated_transcript}")
    with open(st.session_state.default_audio_file_path_txt, "w") as f:
        f.write(st.session_state.curated_transcript)
    st.rerun()

def save_audio_file():
    init_audio_vars()
    print(f"SAVING AUDIO FILE AS: {st.session_state.audio_file_name_str}")
    print(f"DEFAULT AUDIO FILE PATH TXT: {st.session_state.default_audio_file_path_txt}")
    print(f"DEFAULT AUDIO FILE PATH WAV: {st.session_state.default_audio_file_path_wav}")
    print(f"AUDIO FILE PATH TXT: {st.session_state.audio_file_path_txt}")
    print(f"AUDIO FILE PATH WAV: {st.session_state.audio_file_path_wav}")
    if st.session_state.audio_file_name_str:
        with st.spinner("Saving audio file..."):
            shutil.copyfile(st.session_state.default_audio_file_path_txt, st.session_state.audio_file_path_txt)
            shutil.copyfile(st.session_state.default_audio_file_path_wav, st.session_state.audio_file_path_wav)
            # shutil.copyfile(st.session_state.default_audio_file_path_mp3, st.session_state.audio_file_path_mp3)
    st.success(f"File for {st.session_state.audio_file_name_str} saved successfully!")

def generate_audio_file_from_transcript():
    if st.session_state.tts_choice == "PiperTTS":
        generate_audio_file_from_transcript_piper_tts()
    elif st.session_state.tts_choice == "GeminiTTS":
        generate_audio_file_from_transcript_gemini_tts()

def generate_audio_file_from_transcript_piper_tts():
    if st.session_state.curated_transcript:
        with open(st.session_state.default_audio_file_path_txt, "w") as f:
            f.write(st.session_state.curated_transcript)

        # cat 00.txt | piper -m en_US-danny-low.onnx -c en_US-danny-low.onnx.json -f 00.wav
        with open(st.session_state.default_audio_file_path_txt, "r") as f:
            text_input = f.read()

        if st.session_state.voice_type_mf == "Female":
            result = subprocess.run(
                ["piper", "-m", "en_US-hfc_female-medium.onnx", "-c", "en_US-hfc_female-medium.onnx.json", "-f", st.session_state.default_audio_file_path_wav],
                input=text_input,
                text=True,
                capture_output=True
            )
        if st.session_state.voice_type_mf == "Male":
            result = subprocess.run(
                ["piper", "-m", "en_US-danny-low.onnx", "-c", "en_US-danny-low.json", "-f", st.session_state.default_audio_file_path_wav],
                input=text_input,
                text=True,
                capture_output=True
            )

        #print(f"Result of piper command: {result}")
        if result.returncode != 0:
            st.warning(f"Audio file generation failed due to the following error: \n {result.stderr}")
            return

        result = subprocess.run(
            ["ffmpeg", "-y", "-i", st.session_state.default_audio_file_path_wav, st.session_state.default_audio_file_path_mp3],
            input=text_input,
            text=True,
            capture_output=True
        )
        #print(f"Result of ffmpeg command: {result}")
        if result.returncode != 0:
            st.warning(f"Conversion to mp3 failed: \n {result.stderr}")
            return

        st.audio(st.session_state.default_audio_file_path_wav)

def gemini_tts_wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    print(f"\nWriting audio file with parameters:")
    print(f"Channels: {channels}")
    print(f"Sample rate: {rate}")
    print(f"Sample width: {sample_width}")
    print(f"Data length: {len(pcm)} bytes")

    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)


def generate_audio_file_from_transcript_gemini_tts():

    client = genai.Client(api_key=st.session_state.gemini_api_key)

    if st.session_state.voice_type_mf == "Female":
        response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=st.session_state.gemini_tts_prompt,
        config=types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=st.session_state.gemini_tts_voice_female,
                    )
                )
            ),
        )
        )
        
    if st.session_state.voice_type_mf == "Male":
        response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=st.session_state.gemini_tts_prompt,
        config=types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=st.session_state.gemini_tts_voice_male,
                    )
                )
            ),
        )
        )

    # Debug the response structure
    print("\nResponse structure:")
    print(f"Number of candidates: {len(response.candidates)}")
    print(f"Content parts: {len(response.candidates[0].content.parts)}")
    print(f"Part type: {type(response.candidates[0].content.parts[0])}")

    data = response.candidates[0].content.parts[0].inline_data.data

    # decoded_data = base64.b64decode(data)

    response.usage_metadata

    rate = 24000
    file_name = f'test.wav'

    print(f"\nSaving sample rate: {rate}")
    gemini_tts_wave_file(st.session_state.default_audio_file_path_wav, data, rate=rate)

    st.audio(st.session_state.default_audio_file_path_wav)



def get_available_names(data_dir):
    """Return a sorted list of base filenames (without extension) that have both .txt and .wav files."""
    txt_files = {os.path.splitext(f)[0] for f in os.listdir(data_dir) if f.endswith(".txt")}
    wav_files = {os.path.splitext(f)[0] for f in os.listdir(data_dir) if f.endswith(".wav")}
    return sorted(txt_files & wav_files)

def load_text_file(filepath):
    """Read and return the contents of a text file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


@st.dialog("Are you sure you want to delete the selected audio file? This can't be undone.")
def delete_audio_files(base_name):
    if st.button("Yes"):
        """Delete all the audio files for a given base name."""
        for ext in [".txt", ".wav", ".mp3"]:
            path = os.path.join(st.session_state.audio_data_dir, base_name + ext)
            if os.path.exists(path):
                os.remove(path)
        st.rerun()
    else:
        pass

def show_audio_files():
    
    # Get available file names dynamically
    available_names = get_available_names(st.session_state.audio_data_dir)

    if not available_names:
        st.info("No audio files found.")
        return

    # Dropdown to select file base name
    st.session_state.selected_name = st.selectbox("Select audio file:", available_names)

    txt_path = os.path.join(st.session_state.audio_data_dir, st.session_state.selected_name + ".txt")
    wav_path = os.path.join(st.session_state.audio_data_dir, st.session_state.selected_name + ".wav")

    # Display text content
    if os.path.exists(txt_path):
        text_content = load_text_file(txt_path)
        st.session_state.curated_transcript = text_content
        #st.text_area("Text content:", value=text_content, height=200)

    # Display audio player
    if os.path.exists(wav_path):
        with open(wav_path, "rb") as audio_file:
            audio_bytes = audio_file.read()
            st.audio(audio_bytes, format="audio/wav")

    if st.session_state.selected_name:
        col1, col2, col3 = st.columns(3)

        with col1:
            # Download button for Audio file
            with open(f"{st.session_state.audio_data_dir}/{st.session_state.selected_name}.wav", "rb") as audio_file:
                audio_bytes = audio_file.read()
            st.download_button(
                label=f"Download Audio file for {st.session_state.selected_name}",
                data=audio_bytes,
                file_name=st.session_state.selected_name + ".wav",
                mime="audio/wav"
            )
            
        with col2:
            # Download button for transcript text file
            with open(f"{st.session_state.audio_data_dir}/{st.session_state.selected_name}.txt", "rb") as text_file:
                text_bytes = text_file.read()
            st.download_button(
                label=f"Download Transcript for {st.session_state.selected_name}",
                data=text_bytes,
                file_name=st.session_state.selected_name + ".txt",
                mime="text/plain"
            )

        with col3:
            # Delete button for both files
            if st.button(f"Delete files for {st.session_state.selected_name}"):
                delete_audio_files(st.session_state.selected_name)


