import streamlit as st
import subprocess

# if 'audio_file_path_media' not in st.session_state:
#     st.session_state.audio_file_path_media = '/tmp/' + audio_file_name_str + '.wav'
# if 'audio_file_path_txt' not in st.session_state:
#     st.session_state.audio_file_path_txt = '/tmp/' + audio_file_name_str + '.txt'
# if 'curated_transcript' not in st.session_state:
#     st.session_state.curated_transcript = ""

def create_audio_file_from_transcript():
    print(f"curated_transcript:\n{st.session_state.curated_transcript}")
    print(f"audio_file_path_media:{st.session_state.audio_file_path_media}")
    print(f"audio_file_path_txt:{st.session_state.audio_file_path_txt}")
    if st.session_state.curated_transcript:
        with open(st.session_state.audio_file_path_txt, "w") as f:
            f.write(st.session_state.curated_transcript)

        # cat 00.txt | piper -m en_US-danny-low.onnx -c en_US-danny-low.onnx.json -f 00.wav
        with open(st.session_state.audio_file_path_txt, "r") as f:
            text_input = f.read()

        result = subprocess.run(
            ["piper", "-m", "en_US-danny-low.onnx", "-c", "en_US-danny-low.onnx.json", "-f", st.session_state.audio_file_path_media],
            input=text_input,
            text=True,
            capture_output=True
        )

        print(f"Result of piper command: {result}")
        if result.returncode != 0:
            st.warning(f"Audio file generation failed due to the following error: \n {result.stderr}")

    st.audio(st.session_state.audio_file_path_media)
