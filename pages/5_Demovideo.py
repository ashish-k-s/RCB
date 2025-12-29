from glob import glob
import shutil
import json
from altair import Dict
from click import command
import streamlit as st
import streamlit.components.v1 as components
from st_bridge import bridge
import base64
import os
from datetime import timedelta
import subprocess
from pathlib import Path

from rcb_init import init_page
from moviepy import VideoFileClip, concatenate_videoclips, AudioFileClip, CompositeAudioClip
import moviepy.video.fx as vfx

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
if 'generate_video_file_name' not in st.session_state:
    st.session_state.generate_video_file_name = ""
if 'generate_video_file_path' not in st.session_state:
    st.session_state.generate_video_file_path = ""

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

@st.dialog("Are you sure you want to delete this video? This can't be undone.")
def ask_delete_confirmation():    
    if st.button("Yes"):
        """Delete selected video file."""
        path = os.path.join(f"{st.session_state.user_dir}/saved_videos", st.session_state.selected_file_name)
        if os.path.exists(path):
            os.remove(path)
        st.rerun()
    else:
        pass

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
    freeze = st.number_input("Freeze Duration (in seconds):", min_value=1, value=5, step=5)
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

def ts_to_seconds(ts):
    parts = ts.split(":")
    parts = [float(p) for p in parts]

    if len(parts) == 3:      # HH:MM:SS
        h, m, s = parts
        return h * 3600 + m * 60 + s
    elif len(parts) == 2:    # MM:SS
        m, s = parts
        return m * 60 + s
    else:                    # SS
        return parts[0]

# def seconds_to_ts(seconds):
#     seconds = float(seconds)

#     h = int(seconds // 3600)
#     seconds %= 3600
#     m = int(seconds // 60)
#     s = seconds % 60

#     # Format seconds: remove trailing .0 if it's an integer
#     if s.is_integer():
#         s = int(s)

#     if h > 0:
#         return f"{h}:{m:02d}:{s:02d}" if isinstance(s, int) else f"{h}:{m:02d}:{s:05.2f}"
#     elif m > 0:
#         return f"{m}:{s:02d}" if isinstance(s, int) else f"{m}:{s:05.2f}"
#     else:
#         return str(s)

def get_duration(path: str) -> float:
    """Return duration in seconds using ffprobe.
    ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 /media/file/path 
    """
    
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    print("FFprobe command:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    print("FFprobe output:", result.stdout.strip())
    # data = json.loads(result.stdout)
    # return float(data["format"]["duration"])
    return float(result.stdout.strip())

def build_keep_segments(cut_segments, total_duration):
    keep = []
    current = 0

    for line in cut_segments:
        start, end = line[:2]
        if current < start:
            keep.append((current, start))
        current = end

    if current < total_duration:
        keep.append((current, total_duration))

    return keep

def remove_multiple_sections(video_path, cut_segments):
    """
    Remove multiple sections from a video.

    Args:
        video_path (str): Path to input video.
        cut_segments (list): List of tuples [(start_time, end_time), ...].
                      start_time and end_time can be in seconds or 'hh:mm:ss' format.
    command:
        TRIM PART OF FILE
        ffmpeg -y -ss 00:00:00 -i input.mp4 -to 01:42:40 -c copy output1.mp4
        TRIM LAST PART OF FILE
        ffmpeg -y -ss 02:43:07 -i input.mp4 -c copy output3.mp4
    """
    total_duration = get_duration(video_path)
    print("cut_segments:", cut_segments)
    cut_segments = [(ts_to_seconds(start), ts_to_seconds(end)) for start, end in cut_segments]
    keep_segments = build_keep_segments(cut_segments, total_duration)
    print("keep_segments:", keep_segments)
    video_file_count = 1
    for line in keep_segments:
        print(f"Keep segment: {line}")
        start, end = line
        print(f"Start: {start}, End: {end}")
        # start_ts = seconds_to_ts(start)
        # end_ts = seconds_to_ts(end)
        if end == "":
            command = f"ffmpeg -y -i {video_path} -ss {start} -c:v libx264 -c:a aac {st.session_state.user_temp_dir}/{video_file_count}.mp4 > /dev/null 2>&1"
        else:
            command = f"ffmpeg -y -i {video_path} -ss {start} -to {end} -c:v libx264 -c:a aac {st.session_state.user_temp_dir}/{video_file_count}.mp4 > /dev/null 2>&1"
        print(f"Command: {command}")
        video_file_count += 1
        os.system(command)


def dub_audio_on_video(
    video_path: str,
    audio_tracks: list[Dict],
    output_path: str):
    """
    audio_tracks example:
    [
        {"path": "voice1.wav", "start": 2.5},
        {"path": "voice2.wav", "start": 8.0},
    ]
    """

    if not audio_tracks:
        raise ValueError("At least one audio track is required")

    # --- durations ---
    video_duration = get_duration(video_path)

    for track in audio_tracks:
        if "duration" not in track:
            track["duration"] = get_duration(track["path"])

    last_audio_end = max(
        t["start"] + t["duration"] for t in audio_tracks
    )

    target_duration = max(video_duration, last_audio_end)

    # --- ffmpeg command ---
    cmd = ["ffmpeg", "-y", "-i", video_path]

    for track in audio_tracks:
        cmd.extend(["-i", track["path"]])

    filter_parts = []
    mix_inputs = []

    for i, track in enumerate(audio_tracks):
        delay_ms = int(track["start"] * 1000)
        label = f"a{i}"

        filters = [f"adelay={delay_ms}|{delay_ms}"]

        filter_parts.append(
            f"[{i+1}:a]{','.join(filters)}[{label}]"
        )
        mix_inputs.append(f"[{label}]")

    filter_complex = (
        ";".join(filter_parts)
        + ";"
        + "".join(mix_inputs)
        + f"amix=inputs={len(mix_inputs)}:normalize=0,"
        + "loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    )

    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[a]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-t", f"{target_duration:.3f}",
        output_path,
    ])

    print("FFmpeg command to dub audio:\n", " ".join(cmd))
    print(f"Target duration: {target_duration:.2f}s")

    subprocess.run(cmd, check=True)

    return cmd

def freeze_video_segments(video_path, freeze_instructions, output_path):
    """
    Freeze the video at given timestamps for given durations.

    freeze_instructions: list of strings
        Format: "timestamp freeze_duration"
        Example: "0:00:10 2"
    """

    # def to_seconds(t):
    #     """Convert hh:mm:ss, mm:ss, or ss → seconds."""
    #     if isinstance(t, (int, float)):
    #         return t
    #     parts = t.split(":")
    #     parts = [float(p) for p in parts]
    #     if len(parts) == 3:
    #         h, m, s = parts
    #         return h*3600 + m*60 + s
    #     elif len(parts) == 2:
    #         m, s = parts
    #         return m*60 + s
    #     else:
    #         return float(parts[0])

    clip = VideoFileClip(video_path)
    timeline = []

    # Parse & sort freeze instructions
    parsed = []
    for inst in freeze_instructions:
        ts, dur = inst.split()
        parsed.append((ts_to_seconds(ts), float(dur)))
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

    remove_multiple_sections(st.session_state.selected_file_path, timestamps_to_trim)

    video_files_dir = Path(st.session_state.user_temp_dir)

    mp4_video_files = sorted([f.name for f in video_files_dir.glob("*.mp4")])

    print(mp4_video_files)
    process_join_actions(video_files_dir, mp4_video_files)

def process_speed_actions():
    speed_instructions = []
    for line in st.session_state.action_text.strip().splitlines():
        start, end, speed = line.split()
        speed_instructions.append(f"{start} {end} {speed}")
    print("speed_instructions before conversion:", speed_instructions)
    # Convert timestamps to seconds
    speed_instructions = [
        (ts_to_seconds(start), ts_to_seconds(end), float(speed))
        for instr in speed_instructions
        for start, end, speed in [instr.split()]
    ]
    print("speed_instructions after conversion:", speed_instructions)
    total_duration = get_duration(st.session_state.selected_file_path)
    print("total_duration:", total_duration)
    keep_segments = build_keep_segments(speed_instructions, total_duration)
    print("keep_segments:", keep_segments)
    all_segments = keep_segments + speed_instructions
    all_segments.sort()
    print("all_segments:", all_segments)

    video_file_count = 1
    for segment in all_segments:
        print("Processing segment:", segment)
        if len(segment) == 2:
            start, end = segment
        if len(segment) == 3:
            start, end, speed = segment
        print("Trimming between timestamps: ", segment[:2])
        command = f"ffmpeg -y -i {st.session_state.selected_file_path} -ss {start} -to {end} -an -c:v libx264 {st.session_state.user_temp_dir}/{video_file_count}.mp4 > /dev/null 2>&1"
        print("Executing command:", command)
        os.system(command)
        if len(segment) == 3:
            print("Speeding with factor: ", speed)
            shutil.move(f"{st.session_state.user_temp_dir}/{video_file_count}.mp4", f"{st.session_state.user_temp_dir}/temp_{video_file_count}.mp4")
            # Apply speed change using ffmpeg
            command = f"ffmpeg -y -ss {start} -to {end} -i {st.session_state.user_temp_dir}/temp_{video_file_count}.mp4 -vf \"setpts=PTS/{float(speed):.2f},fps=30,setpts=PTS-STARTPTS\" -an -reset_timestamps 1 -c:v libx264 -preset fast -crf 18 {st.session_state.user_temp_dir}/{video_file_count}.mp4 > /dev/null 2>&1"
            print("Executing command:", command)
            os.system(command)
            os.remove(f"{st.session_state.user_temp_dir}/temp_{video_file_count}.mp4")
        with open(f"{st.session_state.user_temp_dir}/list.txt", "a") as video_list:
            video_list.write(f"file '{st.session_state.user_temp_dir}/{video_file_count}.mp4'\n")
        video_list.close()
        video_file_count += 1
    command = f"ffmpeg -y -f concat -safe 0 -i {st.session_state.user_temp_dir}/list.txt -c:v libx264 -preset fast -crf 18 -c:a aac -movflags +faststart {st.session_state.generate_video_file_path}"
    print("Executing command to concatenate:", command)
    os.system(command)

    mp4_files_to_delete = glob("*.mp4", root_dir=st.session_state.user_temp_dir)
    print("Deleting temporary files:", mp4_files_to_delete)
    for file in mp4_files_to_delete:
        print("Deleting", f"{st.session_state.user_temp_dir}/{file}")
        os.remove(f"{st.session_state.user_temp_dir}/{file}")
    os.remove(f"{st.session_state.user_temp_dir}/list.txt")

def process_freeze_actions():
    freeze_instructions = []
    for line in st.session_state.action_text.strip().splitlines():
        ts, dur = line.split()
        freeze_instructions.append(f"{ts} {dur}")

    freeze_video_segments(
        st.session_state.selected_file_path,
        freeze_instructions,
        st.session_state.generate_video_file_path
    )

def process_join_actions(directory, video_files_to_join):
    print("Videos to join:", video_files_to_join)
    if len(video_files_to_join) == 1:
        print("Only one video file found, moving...")
        video_file = f"{directory}/{video_files_to_join[0]}"
        print("Moving", video_file, "to", st.session_state.generate_video_file_path)
        shutil.copy2(video_file, st.session_state.generate_video_file_path)
    else:
        clips = []
        for vf in video_files_to_join:
            video_path = os.path.join(directory, vf)
            clips.append(VideoFileClip(video_path))
        final = concatenate_videoclips(clips)
        final.write_videofile(st.session_state.generate_video_file_path, codec="libx264", audio_codec="aac")
        final.close()
    mp4_files_to_delete = glob("*.mp4", root_dir=directory)
    print("Deleting temporary files:", mp4_files_to_delete)
    for file in mp4_files_to_delete:
        print("Deleting", f"{directory}/{file}")
        os.remove(f"{directory}/{file}")
    os.remove(f"{directory}/list.txt")
    
def process_dub_actions():
    dubbings = []
    audio_tracks = []
    for line in st.session_state.action_text.strip().splitlines():
        ts_start, path = line.split()
        start = ts_to_seconds(ts_start)
        dubbings.append((start, path))
        audio_tracks.append({
            "path": f"{st.session_state.audio_data_dir}/{path}",
            "start": float(start)
        })

    print("Dubbing instructions:", dubbings)
    print("Audio tracks:", audio_tracks)
    dub_audio_on_video(
        video_path=st.session_state.selected_file_path,
        audio_tracks=audio_tracks,
        output_path=st.session_state.generate_video_file_path
    )

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

    if st.sidebar.button("Delete selected video"):
        if ask_delete_confirmation():
            try:
                os.remove(st.session_state.selected_file_path)
                st.sidebar.success(f"Deleted file: {st.session_state.selected_file_name}")
                st.session_state.selected_file_name = ""
                st.session_state.selected_file_path = ""
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Error deleting file: {e}")

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
        st.session_state.generate_video_file_name = st.text_input("Video File Name")
    
    with col2:
        empty = st.empty()
        generate_video = st.button("Generate Video",disabled=not st.session_state.generate_video_file_name)
    
    if generate_video and st.session_state.generate_video_file_name:
        print(f"Generating video file: {st.session_state.generate_video_file_name}.mp4")
        st.session_state.generate_video_file_path = os.path.join(f"{st.session_state.user_dir}/saved_videos", st.session_state.generate_video_file_name + ".mp4")

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
                video_files_to_join = [line.strip() for line in st.session_state.action_text.strip().splitlines() if line.strip()]
                directory = f"{st.session_state.user_dir}/saved_videos"
                process_join_actions(directory, video_files_to_join)

        st.success(f"Video generated and saved as {st.session_state.generate_video_file_name}.mp4")
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
