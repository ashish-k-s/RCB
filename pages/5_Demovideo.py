import streamlit as st
import streamlit.components.v1 as components
from st_bridge import bridge
import base64
import os
from datetime import timedelta
import subprocess

from rcb_init import init_page
from moviepy import VideoFileClip, concatenate_videoclips, AudioFileClip, CompositeAudioClip
import moviepy.video.fx as vfx

import speed

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
    st.session_state.action_str = selected_option
    st.session_state.trim_selected = (selected_option == "Trim")
    st.session_state.speed_selected = (selected_option == "Speed")
    st.session_state.freeze_selected = (selected_option == "Freeze")
    st.session_state.dub_selected = (selected_option == "Dub")
    st.session_state.join_selected = (selected_option == "Join")

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

def display_common_options():
    def add_action():
        st.session_state.num_actions += 1
        update_action("\n")

    get_timestamp = st.button("Get Current timestamp")
    add_action = st.button("Add action", on_click=add_action)

    if get_timestamp:
        try:
            st.session_state.current_timestamp = seconds_to_hhmmss_timedelta(float(st.session_state.current_timestamp.strip()))
            st.session_state.current_timestamp = st.session_state.current_timestamp + "    "
        except ValueError:
            st.session_state.current_timestamp = "00:00"
        update_action(st.session_state.current_timestamp + " ")

def display_trim_options():
    pass
def display_speed_options():
    speed = st.number_input("Speed Factor:", min_value=0.1, max_value=10.0, value=1.5, step=0.5)
    if st.button("Use this speed"):
        st.session_state.action_text += f"{speed}"

def display_freeze_options():
    freeze = st.number_input("Freeze Duration:", min_value=0.1, max_value=10.0, value=1.5, step=0.5)
    if st.button("Use this freeze duration"):
        st.session_state.action_text += f"{freeze}"

def display_dub_options():
    try:
        audio_files = [f for f in os.listdir(f"{st.session_state.user_dir}/audio") if f.endswith(".wav")]
    except FileNotFoundError:
        st.info("No audio files found. Please generate required audio files using Audio feature of this tool.")

    selected_audio_file = st.selectbox("Select audio file to dub:", audio_files)
    if st.button("Use selected file"):
        update_action(selected_audio_file)

def display_join_options():
    video_file_join = st.selectbox("Select the file to join:", video_files)
    video_file_path = os.path.join(f"{st.session_state.user_dir}/saved_videos", video_file_join)
    if st.button("Add this video to join list"):
        update_action( video_file_join + "\n" )

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

def apply_speed_segments(video_path, speed_instructions, output_path):
    """
    Apply speed changes to multiple parts of a video.
    
    speed_instructions: list of strings
        Format: "start end speed"
        Example: "0:00:05 0:00:11 2"
    """
    
    def to_seconds(t):
        """Convert hh:mm:ss → seconds (also supports mm:ss or seconds)."""
        if isinstance(t, (int, float)):
            return t
        parts = t.split(":")
        parts = [float(p) for p in parts]
        if len(parts) == 3:
            h, m, s = parts
            return h*3600 + m*60 + s
        elif len(parts) == 2:
            m, s = parts
            return m*60 + s
        else:
            return float(parts[0])

    clip = VideoFileClip(video_path)
    timeline = []

    # Sort instructions by start time
    parsed = []
    for line in speed_instructions:
        start, end, speed = line.split()
        parsed.append((to_seconds(start), to_seconds(end), float(speed)))
    parsed.sort(key=lambda x: x[0])

    last_end = 0

    # Build segments in order
    for start, end, speed in parsed:
        # normal segment before speed-up
        if start > last_end:
            timeline.append(clip.subclipped(last_end, start))

        # speed-modified segment
        sped = clip.subclipped(start, end).with_effects([
            vfx.MultiplySpeed(factor=speed)
        ])
        timeline.append(sped)

        last_end = end

    # Remaining tail of video
    if last_end < clip.duration:
        timeline.append(clip.subclipped(last_end, clip.duration))

    # Concatenate all parts
    final = concatenate_videoclips(timeline)
    final.write_videofile(output_path, codec="libx264", audio_codec="aac")

    clip.close()
    final.close()

def freeze_video_segments(video_path, freeze_instructions, output_path):
    """
    Freeze the video at given timestamps for given durations.

    freeze_instructions: list of strings
        Format: "timestamp freeze_duration"
        Example: "0:00:10 2"
    """

    def to_seconds(t):
        """Convert hh:mm:ss, mm:ss, or ss → seconds."""
        if isinstance(t, (int, float)):
            return t
        parts = t.split(":")
        parts = [float(p) for p in parts]
        if len(parts) == 3:
            h, m, s = parts
            return h*3600 + m*60 + s
        elif len(parts) == 2:
            m, s = parts
            return m*60 + s
        else:
            return float(parts[0])

    clip = VideoFileClip(video_path)
    timeline = []

    # Parse & sort freeze instructions
    parsed = []
    for inst in freeze_instructions:
        ts, dur = inst.split()
        parsed.append((to_seconds(ts), float(dur)))
    parsed.sort(key=lambda x: x[0])

    last_end = 0

    for freeze_time, freeze_duration in parsed:

        # Normal part before freeze
        if freeze_time > last_end:
            timeline.append(clip.subclipped(last_end, freeze_time))

        # Get the exact frame to freeze
        frozen_frame = clip.to_ImageClip(freeze_time).with_duration(freeze_duration)

        timeline.append(frozen_frame)

        last_end = freeze_time

    # Add remaining tail of video
    if last_end < clip.duration:
        timeline.append(clip.subclipped(last_end, clip.duration))

    # Concatenate final timeline
    final = concatenate_videoclips(timeline)
    final.write_videofile(output_path, codec="libx264", audio_codec="aac")

    clip.close()
    final.close()

def process_trim_actions():
    timestamps_to_trim = [tuple(line.split()) for line in st.session_state.action_text.splitlines() if line.strip()]

    print(timestamps_to_trim)

    remove_multiple_sections(st.session_state.selected_file_path, timestamps_to_trim, generate_video_file_path)

def process_speed_actions():
    speed_instructions = []
    for line in st.session_state.action_text.strip().splitlines():
        start, end, speed = line.split()
        speed_instructions.append(f"{start} {end} {speed}")

    apply_speed_segments(
        st.session_state.selected_file_path,
        speed_instructions,
        generate_video_file_path
    )

def process_freeze_actions():
    freeze_instructions = []
    for line in st.session_state.action_text.strip().splitlines():
        ts, dur = line.split()
        freeze_instructions.append(f"{ts} {dur}")

    freeze_video_segments(
        st.session_state.selected_file_path,
        freeze_instructions,
        generate_video_file_path
    )

def process_join_actions():
    video_files_to_join = [line.strip() for line in st.session_state.action_text.strip().splitlines() if line.strip()]
    clips = []
    for vf in video_files_to_join:
        video_path = os.path.join(f"{st.session_state.user_dir}/saved_videos", vf)
        clips.append(VideoFileClip(video_path))
    final = concatenate_videoclips(clips)
    final.write_videofile(generate_video_file_path, codec="libx264", audio_codec="aac")
    final.close()

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

    if "num_actions" not in st.session_state:
        st.session_state.num_actions = 1  # start with one


    # Button to add new text action
    col1, col2, col3 = st.columns(3)

    with col1:
        options = ["Trim", "Speed", "Freeze", "Dub", "Join"]
        action = st.selectbox("Action Type:", options, index=st.session_state.selected_index, disabled=st.session_state.get("disable_all"), on_change=clear_actions)
        set_action(action)
    with col2:
        if st.session_state.trim_selected or st.session_state.speed_selected or st.session_state.freeze_selected or st.session_state.dub_selected:
            display_common_options()
        if st.session_state.join_selected:
            display_join_options()

    with col3:
        if st.session_state.trim_selected:
            display_trim_options()
        elif st.session_state.speed_selected:
            display_speed_options()
        elif st.session_state.freeze_selected:
            display_freeze_options()
        elif st.session_state.dub_selected:
            display_dub_options()

    if st.session_state.trim_selected:
        actions_format_text = "Trim Action Format:    start_time    end_time    (one per line)\nExample:\n00:00:10    00:00:20\n00:01:00    00:01:15"
    elif st.session_state.speed_selected:
        actions_format_text = "Speed Action Format:    start_time    end_time    speed_factor (one per line)\nExample:\n00:00:10    00:00:20    2.0\n00:01:00    00:01:15    0.5"
    elif st.session_state.freeze_selected:
        actions_format_text = "Freeze Action Format:    timestamp    freeze_duration (one per line)\nExample:\n00:00:10    2.0\n00:01:00    1.5"
    elif st.session_state.dub_selected:
        actions_format_text = "Dub Action Format:    timestamp    audio_file_name (one per line)\nExample:\n00:00:10    wrh-pm.wav\n00:01:00    audio-file-name.wav"
    elif st.session_state.join_selected:
        actions_format_text = "Join Action Format:    video_file_name (one per line)\nExample:\nvideo1.mp4\nvideo2.mp4"

    st.session_state.action_text = st.text_area("Actions:", placeholder=actions_format_text, height=300, value=st.session_state.action_text)

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
            if st.session_state.action_str == "Speed":
                process_speed_actions()
            if st.session_state.action_str == "Freeze":
                process_freeze_actions()
            if st.session_state.action_str == "Join":
                process_join_actions()

        st.success(f"Video generated and saved as {generate_video_file_name}.mp4")
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
