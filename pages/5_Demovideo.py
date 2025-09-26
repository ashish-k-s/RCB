import streamlit as st
import streamlit.components.v1 as components
from st_bridge import bridge
import base64
import os
from datetime import timedelta
import subprocess

from rcb_init import init_page

st.title("Build Your Demovideo with RCB")
init_page()

if "selected_file" not in st.session_state:
    st.session_state.selected_file = ""
if "video_path" not in st.session_state:
    st.session_state.video_path = ""
if "current_time" not in st.session_state:
    st.session_state.current_time = ""
if "action_str" not in st.session_state:
    st.session_state.action_str = ""
if "action_text" not in st.session_state:
    st.session_state.action_text = ""
if "dub_disabled" not in st.session_state:
    st.session_state.dub_disabled = False
if "cut_disabled" not in st.session_state:
    st.session_state.cut_disabled = False

# Display the selected video with JavaScript and other streamlit controls
## if st.session_state.video_path and os.path.exists(st.session_state.video_path):
try:
    video_files = [f for f in os.listdir(st.session_state.user_dir) if f.endswith(".webm")]
except FileNotFoundError:
    st.sidebar.info("No demo video found. Please upload a .webm video file.")

def update_action(action_str=""):
    print(f"Updating action with: {action_str}")
    st.session_state.action_text += f"{action_str}"
    print(f"Updated action_text: {st.session_state.action_text}")

@st.dialog("Clear all drafted actions? This can't be undone.")
def clear_actions():
    if st.button("Yes"):
        st.session_state.num_actions = 1
        st.session_state.current_time = ""
        st.session_state.action_str = ""
        st.session_state.action_text = ""
        st.rerun()
    else:
        pass

def seconds_to_hhmmss_timedelta(seconds):
    """Converts seconds to hh:mm:ss format using timedelta."""
    td = timedelta(seconds=seconds)
    return str(td)

if not st.session_state.username:
    st.info("Please log in to access your demo videos and upload new ones.")
    st.stop()
    
if video_files:
    st.sidebar.subheader("Select a demo video from your uploads:")
    st.session_state.selected_file = st.sidebar.selectbox("Choose a file:", video_files)
    st.session_state.video_path = os.path.join(st.session_state.user_dir, st.session_state.selected_file)
    st.sidebar.info(f"Selected file: {st.session_state.selected_file}")

    with open(st.session_state.video_path, "rb") as f:
        video_bytes = f.read()

    b64_video = base64.b64encode(video_bytes).decode()

    html_code = f"""
    <div style="margin: 0px; padding: 0px;">
    <video id="myVideo" width="640" height="360" controls>
        <source src="data:video/webm;base64,{b64_video}" type="video/webm">
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

    st.subheader(f"Selected Demo Video: {st.session_state.selected_file}")
    components.html(code, height=400, width=700, scrolling=True,)
    value = bridge("currentTime", default="")
    st.session_state.current_time = value
    ## st.session_state["echo_value"] = st.session_state.current_time
    ## st.text_input("Streamlit input (from JS)", key="echo_value")
    ## st.session_state.action_text += st.session_state.current_time

    if "num_actions" not in st.session_state:
        st.session_state.num_actions = 1  # start with one

    def add_action():
        st.session_state.num_actions += 1

    # Button to add new text action
    col1, col2, col3 = st.columns(3)

    with col1:
        cut = st.button("cut",disabled=st.session_state.cut_disabled)
        dub = st.button("dub",disabled=st.session_state.dub_disabled)

    with col2:
        time = st.button("time")
        add = st.button("Add action", on_click=add_action)

    with col3:
        get_audio_file = st.button("audio file",key="get_audio_file",disabled=st.session_state.get("cut_disabled"))
        audio_file = st.selectbox("Select Audio:", options=["audio1.mp3", "audio2.mp3", "audio3.mp3"], label_visibility="collapsed",key="audio_file",disabled=st.session_state.get("cut_disabled"))

    if cut:
        proceed = True
        if st.session_state.action_text:
            st.toast("Clear all actions before switching mode.")
            proceed = False
        if proceed:
            ##update_action("cut:\n")
            st.session_state.dub_disabled = False
            st.session_state.cut_disabled = True
            st.rerun()

    if dub:
        proceed = True
        if st.session_state.action_text:
            st.toast("Clear all actions before switching mode.")
            proceed = False
        if proceed:
            ##update_action("dub:\n")
            st.session_state.cut_disabled = False
            st.session_state.dub_disabled = True
            st.rerun()

    if add:
        update_action("\n")

    if time:
        try:
            st.session_state.current_time = seconds_to_hhmmss_timedelta(float(st.session_state.current_time.strip()))
        except ValueError:
            st.session_state.current_time = "00:00"
        update_action(st.session_state.current_time + " ")

    if get_audio_file:
        update_action(f"{audio_file} ")

    # Render the text actions
    st.text_area("Actions:", placeholder="Enter text for actions here...", height=300, value=st.session_state.action_text)

    if st.button("Clear all Actions"):
        clear_actions()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.radio("Video Processing Mode:", options=["Fast", "Precise"], index=0)

    with col2:    
        video_file_name = st.text_input("Video File Name")
    
    with col3:
        empty = st.empty()
        generate_video = st.button("Generate Video",disabled=not video_file_name)
    
    if generate_video and video_file_name:
        print(f"Generating video file: {video_file_name}.webm")
        if st.session_state.action_text:
            try:
                with open("trim.txt", "w") as f:
                    f.write(st.session_state.action_text)
                print("Actions written to trim.txt:")
                print(st.session_state.action_text)
            except Exception as e:
                print(f"Error writing actions to file: {e}")
        print(f"Calling trim.sh with: {st.session_state.user_dir}/{st.session_state.selected_file}")
        subprocess.run(f"sh /home/ashishks/AI/UI/new/RCB/trim.sh {st.session_state.user_dir}/{st.session_state.selected_file}", shell=True)
        print(f"Video file {video_file_name}.webm generated successfully!")

        # components.html("<script>document.getElementById('timestampBox').value = '';</script>", height=0)

else:
    st.sidebar.info("No demo video found. Please upload a .webm video file.")

st.sidebar.subheader("Upload your demo video (.webm)")
uploaded_file = st.sidebar.file_uploader(
    "Upload Demo Video",
    type=['webm'],
    accept_multiple_files=False,
    help="Upload your demo video file.",
    disabled=st.session_state.disable_all
)

if uploaded_file:
    process_file_button = st.sidebar.button("Upload this video",disabled=st.session_state.disable_all)
    if process_file_button:
        print(f"UPLOADED FILES:\n {uploaded_file}")
        # Process the uploaded video file
        st.session_state.video_path = os.path.join(st.session_state.user_dir, uploaded_file.name)
        with open(st.session_state.video_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.rerun()
