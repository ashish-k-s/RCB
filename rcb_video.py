import subprocess
import os
import shutil
import glob

import streamlit as st

from pathlib import Path

def init_video_page():
    if 'preserve_audio' not in st.session_state:
        st.session_state.preserve_audio = True
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

def cleanup_directory_content(directory: str):
    """Remove all files in the specified directory."""
    dir_path = Path(directory)
    for item in dir_path.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)

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
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    print("FFprobe output:", result.stdout.strip())
    return float(result.stdout.strip())

def concat_videos(directory):
    video_files_to_join = glob.glob("*.mp4", root_dir=st.session_state.user_temp_dir)
    print("Videos to join:", video_files_to_join)
    if len(video_files_to_join) == 1:
        print("Only one video file found, moving...")
        video_file = f"{directory}/{video_files_to_join[0]}"
        print("Moving", video_file, "to", st.session_state.generate_video_file_path)
        shutil.copy2(video_file, st.session_state.generate_video_file_path)
    else:
        if st.session_state.preserve_audio:
            command = f"ffmpeg -y -f concat -safe 0 -i {st.session_state.user_temp_dir}/list.txt -c:v libx264 -preset fast -crf 18 -c:a aac -movflags +faststart {st.session_state.generate_video_file_path}  > /dev/null 2>&1"
        else:
            command = f"ffmpeg -y -f concat -safe 0 -i {st.session_state.user_temp_dir}/list.txt -c:v libx264 -preset fast -crf 18 -an {st.session_state.generate_video_file_path}  > /dev/null 2>&1"
        print("Executing command to concatenate:", command)
        # os.system(command)
        subprocess.run(command, shell=True, check=True)

def get_remaining_video_segments(provided_segments, total_duration):
    """
    Given a list of provided video segments, return the remaining segments
    that are not included in the provided list.

    Args:
        provided_segments (list): List of tuples representing the provided segments.
                                  Each tuple is in the format (start_time, end_time).

    Returns:
        list: List of tuples representing the remaining segments.
    """
    remaining_segments = []

    # Start from the beginning of the video
    current_start = 0

    for start, end, *rest in sorted(provided_segments):
        if current_start < start:
            remaining_segments.append((current_start, start))
        current_start = max(current_start, end)

    # Check if there's a remaining segment at the end of the video
    if current_start < total_duration:
        remaining_segments.append((current_start, total_duration))

    #print("Remaining video segments:", remaining_segments)
    return remaining_segments

def process_video_segments(video_segments, action_str):
    """
    Process video segments by either trimming or keeping the specified segments from the video.

    Args:
        video_segments (list): List of tuples representing the segments to trim or keep.
                             Each tuple is in the format (start_time, end_time).
        action: The action parameter determines whether to trim or keep these segments.
    """
    provided_video_segments = video_segments
    duration = get_duration(st.session_state.selected_file_path)
    remaining_video_segments = get_remaining_video_segments(video_segments, duration)
    if action_str == "Trim":
        video_segments = remaining_video_segments
    if action_str == "Keep":
        video_segments = provided_video_segments
    if action_str == "Speed":
        video_segments = provided_video_segments + remaining_video_segments
        video_segments.sort()
    print("Provided video segments:", provided_video_segments)
    print("Remaining video segments:", remaining_video_segments)
    print("Final video segments to process:", video_segments)
    
    cleanup_directory_content(st.session_state.user_temp_dir)

    video_file_count = 1
    for line in video_segments:
        video_file_count_str = f"{video_file_count:03d}"
        if len(line) == 2:
            start, end = line
            print(f"Start: {start}, End: {end}, Video File: {video_file_count_str}.mp4")

        if len(line) == 3:
            start, end, speed = line
            print(f"Start: {start}, End: {end}, Speed: {speed}, Video File: {video_file_count_str}.mp4")

        st.session_state.preserve_audio = st.session_state.get("preserve_audio", True)

        if st.session_state.preserve_audio:
            print("Using command with audio preservation")
            command = f"ffmpeg -y -ss {start} -to {end} -i {st.session_state.selected_file_path} -c:v copy -c:a aac {st.session_state.user_temp_dir}/{video_file_count_str}.mp4 > /dev/null 2>&1"
        else:
            print("Using command without audio preservation")
            command = f"ffmpeg -y -ss {start} -to {end} -i {st.session_state.selected_file_path} -c:v copy -an {st.session_state.user_temp_dir}/{video_file_count_str}.mp4 > /dev/null 2>&1"
        print(f"Command: {command}")
        video_file_count += 1
        os.system(command)

        if action_str == "Speed" and len(line) == 3:
            print(f"Speeding file {video_file_count_str}.mp4 with factor: ", speed)
            shutil.move(f"{st.session_state.user_temp_dir}/{video_file_count_str}.mp4", f"{st.session_state.user_temp_dir}/temp_{video_file_count_str}.mp4")
            if st.session_state.preserve_audio:
                command = f"ffmpeg -y -i {st.session_state.user_temp_dir}/temp_{video_file_count_str}.mp4 -filter_complex \"[0:v]setpts=PTS/{float(speed):.2f},fps=30[v];[0:a]atempo={float(speed):.2f}[a]\" -map \"[v]\" -map \"[a]\" -c:v libx264 -preset fast -crf 18 {st.session_state.user_temp_dir}/{video_file_count_str}.mp4 > /dev/null 2>&1"
            else:
                command = f"ffmpeg -y -i {st.session_state.user_temp_dir}/temp_{video_file_count_str}.mp4 -vf \"setpts=PTS/{float(speed):.2f},fps=30,setpts=PTS-STARTPTS\" -an -reset_timestamps 1 -c:v libx264 -preset fast -crf 18 {st.session_state.user_temp_dir}/{video_file_count_str}.mp4 > /dev/null 2>&1"

            # command = f"ffmpeg -y -ss {start} -to {end} -i {st.session_state.user_temp_dir}/temp_{video_file_count_str}.mp4 -vf \"setpts=PTS/{float(speed):.2f},fps=30,setpts=PTS-STARTPTS\" -an -reset_timestamps 1 -c:v libx264 -preset fast -crf 18 {st.session_state.user_temp_dir}/{video_file_count_str}.mp4 > /dev/null 2>&1"
            print("Executing command to speed up video:", command)
            os.system(command)
            os.remove(f"{st.session_state.user_temp_dir}/temp_{video_file_count_str}.mp4")

        with open(f"{st.session_state.user_temp_dir}/list.txt", "a") as video_list:
            video_list.write(f"file '{st.session_state.user_temp_dir}/{video_file_count_str}.mp4'\n")
        video_list.close()
        print(f"Running command: {command}")
        subprocess.run(command, shell=True)
        if subprocess.run(command, shell=True).returncode != 0:
            print(f"Error processing video segment {line}.")
        else:
            print(f"Video segment {line} processed successfully.")
        video_file_count += 1

    concat_videos(st.session_state.user_temp_dir)
