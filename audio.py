import streamlit as st
import subprocess

def create_audio_file_from_transcript():
    print(f"curated_transcript:\n{st.session_state.curated_transcript}")
    print(f"audio_file_path_wav:{st.session_state.audio_file_path_wav}")
    print(f"audio_file_path_txt:{st.session_state.audio_file_path_txt}")
    if st.session_state.curated_transcript:
        with open(st.session_state.audio_file_path_txt, "w") as f:
            f.write(st.session_state.curated_transcript)

        # cat 00.txt | piper -m en_US-danny-low.onnx -c en_US-danny-low.onnx.json -f 00.wav
        with open(st.session_state.audio_file_path_txt, "r") as f:
            text_input = f.read()

        result = subprocess.run(
            ["piper", "-m", "en_US-danny-low.onnx", "-c", "en_US-danny-low.onnx.json", "-f", st.session_state.audio_file_path_wav],
            input=text_input,
            text=True,
            capture_output=True
        )

        print(f"Result of piper command: {result}")
        if result.returncode != 0:
            st.warning(f"Audio file generation failed due to the following error: \n {result.stderr}")

        result = subprocess.run(
            ["ffmpeg", "-y", "-i", st.session_state.audio_file_path_wav, st.session_state.audio_file_path_mp3],
            input=text_input,
            text=True,
            capture_output=True
        )
        print(f"Result of ffmpeg command: {result}")
        if result.returncode != 0:
            st.warning(f"Conversion failed: \n {result.stderr}")
