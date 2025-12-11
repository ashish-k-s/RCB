import streamlit as st
import streamlit.components.v1 as components
from st_bridge import bridge
import base64
import os
from datetime import timedelta
import subprocess

from rcb_init import init_page
from moviepy import VideoFileClip, concatenate_videoclips, AudioFileClip, CompositeAudioClip

st.title("Build Your Demovideo with RCB")
if 'current_page' not in st.session_state:
    st.session_state.current_page = "DemoVideo"
st.session_state.current_page = "DemoVideo"

init_page()

if "selected_file" not in st.session_state:
    st.session_state.selected_file_name = ""
if "video_path" not in st.session_state:
    st.session_state.selected_file_path = ""
if "current_timestamp" not in st.session_state:
    st.session_state.current_timestamp = ""
if "action_str" not in st.session_state:
    st.session_state.action_str = "Trim"
if "action_text" not in st.session_state:
    st.session_state.action_text = ""
if 'selected_index' not in st.session_state:
    st.session_state.selected_index = 0
if 'trim_selected' not in st.session_state:
    st.session_state.trim_selected = False
if 'dub_selected' not in st.session_state:
    st.session_state.dub_selected = False
if 'speed_selected' in st.session_state:
    st.session_state.speed_disabled = False

def set_action(selected_option):
    # if st.session_state.action_text != "":
    #     if not clear_actions():
    #         return
    st.session_state.action_str = selected_option
    if st.session_state.action_str == "Trim":
        st.session_state.selected_index = 0
    elif st.session_state.action_str == "Speed":
        st.session_state.selected_index = 1
    elif st.session_state.action_str == "Dub":
        st.session_state.selected_index = 2
    st.session_state.trim_selected = (selected_option == "Trim")
    st.session_state.speed_selected = (selected_option == "Speed")
    st.session_state.dub_selected = (selected_option == "Dub")

# Display the selected video with JavaScript and other streamlit controls
## if st.session_state.selected_file_path and os.path.exists(st.session_state.selected_file_path):
try:
    video_files = [f for f in os.listdir(f"{st.session_state.user_dir}/saved_videos") if f.endswith(".mp4")]
except FileNotFoundError:
    st.sidebar.info("No demo video found. Please upload a .mp4 video file.")

def update_action(action_str=""):
    print(f"Updating action with: {action_str}")
    st.session_state.action_text += f"{action_str}"
    print(f"Updated action_text: {st.session_state.action_text}")

@st.dialog("Clear all drafted actions? This can't be undone.")
def clear_actions():
    if st.button("Yes"):
        st.session_state.num_actions = 1
        st.session_state.current_timestamp = ""
        st.session_state.action_str = ""
        st.session_state.action_text = ""
        st.rerun()
    else:
        return False

def display_trim_options():
    pass
def display_speed_options():
    pass
def display_dub_options():
    try:
        audio_files = [f for f in os.listdir(f"{st.session_state.user_dir}/audio") if f.endswith(".wav")]
    except FileNotFoundError:
        st.info("No audio files found. Please generate required audio files using Audio feature of this tool.")

    selected_audio_file = st.selectbox("Select audio file to dub:", audio_files)
    if st.button("Use selected file"):
        update_action(selected_audio_file)

def remove_multiple_sections(video_path, cuts, output_path):
    clip = VideoFileClip(video_path)
    clips = []
    last = 0

    for start, end in cuts:
        clips.append(clip.subclipped(last, start))
        last = end

    clips.append(clip.subclipped(last, clip.duration))  # final segment
    final = concatenate_videoclips(clips)
    final.write_videofile(output_path)

def dub_multiple_audios(video_path, dubbings, output_path):
    """
    Dub multiple audio clips into a video at given timestamps.

    Args:
        video_path (str): Path to input video.
        dubbings (list): List of tuples [(audio_file, start_time), ...].
                         start_time can be in seconds or 'hh:mm:ss' format.
        output_path (str): Path to save final video.
    """
    # Load video
    video = VideoFileClip(video_path)
    base_audio = video.audio

    # Collect all audio layers
    audio_layers = [base_audio]

    # Helper to convert hh:mm:ss to seconds
    def to_seconds(t):
        if isinstance(t, (int, float)):
            return t
        h, m, s = map(float, t.split(':'))
        return h * 3600 + m * 60 + s

    # Add each new dubbing layer
    for start_time, audio_file in dubbings:
        audio_path = st.session_state.user_dir + "/audio/" + audio_file
        start_sec = to_seconds(start_time)
        new_audio = AudioFileClip(audio_path).with_start(start_sec)
        audio_layers.append(new_audio)

    # Combine all audio layers
    final_audio = CompositeAudioClip(audio_layers)

    # Merge with video and export
    final = video.with_audio(final_audio)
    final.write_videofile(output_path, codec="libx264", audio_codec="aac")

    # Cleanup
    video.close()
    final.close()

dubbings = [
    ("00:00:10", "wrh-pm.wav"),
    ("00:01:05", "wibm-pm.wav"),
    (5, "w-pm.wav"),   # You can also pass seconds directly
]

def process_trim_actions():
    timestamps_to_trim = [tuple(line.split()) for line in st.session_state.action_text.splitlines() if line.strip()]

    print(timestamps_to_trim)

    remove_multiple_sections(st.session_state.selected_file_path, timestamps_to_trim, generate_video_file_path)
    st.success(f"Video generated and saved as {generate_video_file_name}.mp4")
                
def process_dub_actions():
    dubbings = []
    for line in st.session_state.action_text.strip().splitlines():
        time_part, file_part = line.split(maxsplit=1)
        dubbings.append((time_part, file_part))
    dub_multiple_audios(st.session_state.selected_file_path, dubbings, generate_video_file_path)

def seconds_to_hhmmss_timedelta(seconds):
    """Converts seconds to hh:mm:ss format using timedelta, discarding fractions."""
    td = timedelta(seconds=int(float(seconds)))
    return str(td)

if not st.session_state.username:
    st.info("Please log in to access your demo videos and upload new ones.")
    st.stop()
    
if video_files:
    st.sidebar.subheader("Select a video file to edit:")
    st.session_state.selected_file_name = st.sidebar.selectbox("Choose a file:", video_files)
    st.session_state.selected_file_path = os.path.join(f"{st.session_state.user_dir}/saved_videos", st.session_state.selected_file_name)
    st.sidebar.info(f"Selected file: {st.session_state.selected_file_name}")

    with open(st.session_state.selected_file_path, "rb") as f:
        video_bytes = f.read()

    b64_video = base64.b64encode(video_bytes).decode()

    html_code = f"""
    <div style="margin: 0px; padding: 0px;">
    <video id="myVideo" width="640" height="360" controls>
        <source src="data:video/mp4;base64,{b64_video}" type="video/mp4">
        Your browser does not support the video tag.
    </video>
    <button onclick="showTimestamp()">Get Current Time</button>
    <input type="text" id="timestampBox" readonly value="0.00">
    </div>

    """
    js_code = """
    <script>

    function getJsInputValue() {
    const el = document.getElementById('timestampBox');
    return el ? el.value : '';
    }

    function showTimestamp() {
        const video = document.getElementById("myVideo");
        const currentTime = video.currentTime.toFixed(2); // keep 2 decimal places
        document.getElementById("timestampBox").value = currentTime + " ";
        sendToStreamlit();
    }
    function sendToStreamlit() {
        const val = getJsInputValue();
        if (window.top && window.top.stBridges) {
        window.top.stBridges.send('currentTime', val);
        }
    }
    </script>
    """

    code = html_code + js_code

    st.subheader(f"Selected Demo Video: {st.session_state.selected_file_name}")
    components.html(code, height=400, width=700, scrolling=True,)
    value = bridge("currentTime", default="")
    st.session_state.current_timestamp = value
    ## st.session_state["echo_value"] = st.session_state.current_timestamp
    ## st.text_input("Streamlit input (from JS)", key="echo_value")
    ## st.session_state.action_text += st.session_state.current_timestamp

    if "num_actions" not in st.session_state:
        st.session_state.num_actions = 1  # start with one

    def add_action():
        st.session_state.num_actions += 1
        update_action("\n")

    # Button to add new text action
    col1, col2, col3 = st.columns(3)

    with col1:
        options = ["Trim", "Speed", "Dub"]
        action = st.selectbox("Action Type:", options, index=st.session_state.selected_index, disabled=st.session_state.get("disable_all"))
        set_action(action)
    with col2:
        get_timestamp = st.button("Get Current timestamp")
        add_action = st.button("Add action", on_click=add_action)

    if get_timestamp:
        try:
            st.session_state.current_timestamp = seconds_to_hhmmss_timedelta(float(st.session_state.current_timestamp.strip()))
        except ValueError:
            st.session_state.current_timestamp = "00:00"
        update_action(st.session_state.current_timestamp + " ")

    with col3:
        if st.session_state.trim_selected:
            display_trim_options()
        elif st.session_state.speed_selected:
            display_speed_options()
        elif st.session_state.dub_selected:
            display_dub_options()


    # Render the text actions
    st.session_state.action_text = st.text_area("Actions:", placeholder="Enter text for actions here...", height=300, value=st.session_state.action_text)

    if st.button("Clear all Actions"):
        clear_actions()

 
    col1, col2 = st.columns(2)

    with col1:    
        generate_video_file_name = st.text_input("Video File Name")
    
    with col2:
        empty = st.empty()
        generate_video = st.button("Generate Video",disabled=not generate_video_file_name)
    
    if generate_video and generate_video_file_name:
        print(f"Generating video file: {generate_video_file_name}.mp4")
        generate_video_file_path = os.path.join(f"{st.session_state.user_dir}/saved_videos", generate_video_file_name + ".mp4")

        if st.session_state.action_text:
            if st.session_state.action_str == "Trim":
                process_trim_actions()
            if st.session_state.action_str == "Dub":
                process_dub_actions()

else:
    st.sidebar.info("No demo video found. Please upload a .mp4 video file.")

st.sidebar.subheader("Upload your demo video (.mp4)")
uploaded_file = st.sidebar.file_uploader(
    "Upload Demo Video",
    type=['mp4'],
    accept_multiple_files=False,
    help="Upload your demo video file.",
    disabled=st.session_state.disable_all
)

if uploaded_file:
    process_file_button = st.sidebar.button("Upload this video",disabled=st.session_state.disable_all)
    if process_file_button:
        print(f"UPLOADED FILES:\n {uploaded_file}")
        # Process the uploaded video file
        st.session_state.selected_file_path = os.path.join(f"{st.session_state.user_dir}/saved_videos", uploaded_file.name)
        with open(st.session_state.selected_file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.rerun()
