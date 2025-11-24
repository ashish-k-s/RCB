import streamlit as st
from PIL import Image
from io import BytesIO
import subprocess
import os
from dotenv import load_dotenv
import google.genai as genai
import shutil

from langchain_openai import ChatOpenAI
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.llms import Ollama
from langchain_core.output_parsers import StrOutputParser

from rcb_init import init_page, init_llm_vars
from rcb_llm_manager import call_llm_to_generate_response

st.set_page_config(
    page_title="Image using RCB"
)

st.title("Create Image with RCB")
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Image"
st.session_state.current_page = "Image"

init_page()
init_llm_vars()

st.session_state.use_default_prompts = True

d2_image_name_str = "rcb_generated_image"
if 'd2_image_path' not in st.session_state:
    st.session_state.d2_image_path = st.session_state.user_dir + "/images/" + d2_image_name_str + '.png'
if 'd2_code_path' not in st.session_state:
    st.session_state.d2_code_path = st.session_state.user_dir + "/images/" + d2_image_name_str + '.d2'
if 'd2_image_code' not in st.session_state:
    st.session_state.d2_image_code = ""
if 'user_prompt' not in st.session_state:
    st.session_state.user_prompt = ""


st.session_state.system_prompt_generate_image = """
PERSONA:
You are an expert in generating diagrams using D2Lang.  
Your ONLY output must be a valid D2 code block.  

RULES FOR D2 CODE GENERATION:
- Do not include explanations, comments, or any text outside the code block.
- Use only valid D2 syntax.
- No incomplete direction blocks.
- **Do not use** labels.
- Use directional arrows (-->, <--, <->) for relationships.
- Use container only to group nodes visually.
- Use directional arrows for relationships.  
- **Never use** "=" for assignments, use yaml style ":" assignments instead.
- No incomplete assignments.
- Do not leave any dangling references or unspecified connections.
- Keep diagrams clean and logically structured.
- ALWAYS output valid D2.
- Ensure the file compiles without errors using the d2 CLI.
- At the end, verify that every connection is between two explicitly defined nodes, and rewrite if needed.

"""

st.session_state.user_prompt_generate_image = f"""
Generate the D2 code for the following diagram description:  
{st.session_state.user_prompt}

"""

def debug_d2_image_code():
    with st.spinner(f"Debugging D2 code using {st.session_state.model_choice}..."):
        st.session_state.user_prompt_generate_image = f"""
        Error while rendering the code using d2 CLI is:
        ---
        {st.session_state.image_render_result.stderr}
        ---

        Below is the D2 code that caused the error:
        ---
        {st.session_state.d2_image_code}
        ---

        Please fix the D2 code to resolve the error. The corrected D2 code should generate the intended diagram without any errors when run through the d2 CLI.

        Here is the original user prompt for reference:
        ---
        {st.session_state.user_prompt}
        ---
        
        Please debug and fix the D2 code above. Ensure the output is ONLY the corrected D2 code block without any explanations or comments.
        """
        generate_image_code()

def generate_image_code():
    with st.spinner(f"Generating code for image using {st.session_state.model_choice}..."):
        st.session_state.d2_image_code = call_llm_to_generate_response(st.session_state.model_choice, st.session_state.system_prompt_generate_image, st.session_state.user_prompt_generate_image)
        print("D2LANG CODE: \n", st.session_state.d2_image_code)
        update_d2_image_code()

def render_image_from_code():
    print(f"d2_image_code:\n{st.session_state.d2_image_code}")
    print(f"d2_image_path:{st.session_state.d2_image_path}")
    print(f"d2_code_path:{st.session_state.d2_code_path}")
    # update_d2_image_code()
    if st.session_state.d2_image_code:
        # if os.path.exists(st.session_state.d2_image_path):
        #     os.remove(st.session_state.d2_image_path)
        with open(st.session_state.d2_code_path, "w") as f:
            f.write(st.session_state.d2_image_code)

        st.session_state.image_render_result = subprocess.run (['d2', st.session_state.d2_code_path, st.session_state.d2_image_path], capture_output=True, text=True)
        print(f"Result of d2 command: {st.session_state.image_render_result}")
        if st.session_state.image_render_result.returncode != 0:
            st.button("Debug and Regenerate Code", on_click=debug_d2_image_code)
            st.warning(f"Image generation failed due to the following error: \n {st.session_state.image_render_result.stderr}")
            st.warning("\nTweaking existing D2 code or generate new code.")
    try:
        if st.session_state.d2_image_path:
            img = Image.open(st.session_state.d2_image_path)
    except FileNotFoundError:
        st.error(f"Image file not found. Please ensure image generation is successful.")
        st.stop() # Stop the app if the image isn't found

    # Display the image
    st.image(img, caption="Image generated by RCB", use_container_width=True)

def update_d2_image_code():
    if st.session_state.d2_image_code:
        print(f"WRITING CONTENT TO FILE: {st.session_state.d2_code_path} \n CONTENT: \n {st.session_state.d2_image_code}")
        with open(st.session_state.d2_code_path, "w") as f:
            f.write(st.session_state.d2_image_code)
    st.rerun()

def save_image_file():
    init_image_vars()
    print(f"SAVING IMAGE FILE AS: {st.session_state.image_file_name_str}")
    print(f"DEFAULT IMAGE FILE PATH TXT: {st.session_state.default_image_file_path_d2}")
    print(f"DEFAULT IMAGE FILE PATH PNG: {st.session_state.default_image_file_path_png}")
    print(f"IMAGE FILE PATH TXT: {st.session_state.image_file_path_d2}")
    print(f"IMAGE FILE PATH PNG: {st.session_state.image_file_path_png}")
    if st.session_state.image_file_name_str:
        with st.spinner("Saving image file..."):
            shutil.copyfile(st.session_state.default_image_file_path_d2, st.session_state.image_file_path_d2)
            shutil.copyfile(st.session_state.default_image_file_path_png, st.session_state.image_file_path_png)
            # shutil.copyfile(st.session_state.default_image_file_path_mp3, st.session_state.image_file_path_mp3)
    st.success(f"File for {st.session_state.image_file_name_str} saved successfully!")
    render_image_from_code()

def init_image_vars():
    print("Initializing image variables...")
    st.session_state.default_image_file_name_str = "rcb_generated_image"
    if 'image_file_name_str' not in st.session_state:
        st.session_state.image_file_name_str = st.session_state.default_image_file_name_str
    st.session_state.image_data_dir = f"{st.session_state.user_dir}/images/"
    st.session_state.default_image_file_path_png = f"{st.session_state.image_data_dir}/{st.session_state.default_image_file_name_str}.png"
    st.session_state.default_image_file_path_d2 = f"{st.session_state.image_data_dir}/{st.session_state.default_image_file_name_str}.d2"
    st.session_state.image_file_path_d2 = f"{st.session_state.image_data_dir}/{st.session_state.image_file_name_str}.d2"
    st.session_state.image_file_path_png = f"{st.session_state.image_data_dir}/{st.session_state.image_file_name_str}.png"

def load_text_file(filepath):
    """Read and return the contents of a text file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

def show_image_files():
    
    # Get available file names dynamically
    available_names = get_available_names(st.session_state.image_data_dir)

    if not available_names:
        st.info("No image files found.")
        return

    # Dropdown to select file base name
    selected_name = st.selectbox("Select a file pair:", available_names)

    d2_path = os.path.join(st.session_state.image_data_dir, selected_name + ".d2")
    png_path = os.path.join(st.session_state.image_data_dir, selected_name + ".png")

    # Display text content
    if os.path.exists(d2_path):
        text_content = load_text_file(d2_path)
        st.session_state.d2_image_code = text_content
        #st.text_area("Text content:", value=text_content, height=200)

    # Display image player
    if os.path.exists(png_path):
        with open(png_path, "rb") as image_file:
            image_bytes = image_file.read()
            st.image(image_bytes, caption="Image Preview", use_container_width=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        # Download button for PNG image
        st.download_button(
            label=f"Download PNG for {selected_name}",
            data=image_bytes,
            file_name=selected_name + ".png",
            mime="image/png"
        )
    with col2:
        # Download button for D2 code     
        st.download_button(
            label=f"Download D2 Code for {selected_name}",
            data=text_content,
            file_name=selected_name + ".d2",
            mime="text/plain"
        )

    with col3:
        # Delete button for both files
        if st.button(f"Delete files for {selected_name}"):
            delete_image_files(selected_name)


# def get_available_names(data_dir):
#     """Return a sorted list of base filenames (without extension) that have both .d2 and .png files."""
#     d2_files = {os.path.splitext(f)[0] for f in os.listdir(data_dir) if f.endswith(".d2")}
#     png_files = {os.path.splitext(f)[0] for f in os.listdir(data_dir) if f.endswith(".png")}
#     return sorted(d2_files & png_files)

import os

def get_available_names(data_dir):
    """Return a sorted list of base filenames (without extension)
    that have both .d2 and .png files, excluding those starting with 'rcb_generated'.
    """
    d2_files = {
        os.path.splitext(f)[0]
        for f in os.listdir(data_dir)
        if f.endswith(".d2") and not f.startswith("rcb_generated")
    }

    png_files = {
        os.path.splitext(f)[0]
        for f in os.listdir(data_dir)
        if f.endswith(".png") and not f.startswith("rcb_generated")
    }

    return sorted(d2_files & png_files)

@st.dialog("Are you sure you want to delete the selected image file? This can't be undone.")
def delete_image_files(base_name):
    if st.button("Yes"):
        """Delete all the image files for a given base name."""
        for ext in [".d2", ".png"]:
            path = os.path.join(st.session_state.image_data_dir, base_name + ext)
            if os.path.exists(path):
                os.remove(path)
        st.rerun()
    else:
        pass

# --- MaaS configuration ---
load_dotenv()

MAAS_API_KEY = os.environ["MAAS_API_KEY"]
MAAS_API_BASE = os.environ["MAAS_API_BASE"]
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_API_BASE = os.environ.get("GEMINI_API_BASE")

init_image_vars()

user_prompt_text = st.text_area(
    "Write detailed description for the image to be generated:",
    placeholder="Write the description of the image to be generated here...",
    height=30,
    key="user_prompt_text",
    disabled=st.session_state.disable_all
)

print(f"User directory: {st.session_state.user_dir}")
generate_image = st.button("Generate Image code", disabled=st.session_state.disable_all)

st.session_state.d2_image_code = st.text_area(
   "Write or edit your d2lang code here:",
    placeholder="Write your d2lang code here...",
    value=st.session_state.d2_image_code,
    height=300,
    key="st.session_state.d2_image_code",
    on_change=update_d2_image_code,
    disabled=st.session_state.disable_all
    )

col1, col2, col3 = st.columns(3)

with col1:        
    render_image = st.button("Render Image", disabled=st.session_state.disable_all)

with col2:
    st.session_state.image_file_name_str = st.text_input(" ", placeholder="Image file name (without extension) here" , key="st.session_state.image_file_name_str", label_visibility="collapsed", disabled=st.session_state.disable_all)

with col3:
    save_image = st.button("Save Image", disabled=not bool(st.session_state.image_file_name_str))

if save_image:
    save_image_file()


if generate_image:
    st.session_state.user_prompt = user_prompt_text
    print(f"Generating image code for User Prompt: {st.session_state.user_prompt}")    
    if not st.session_state.user_prompt.strip():
        st.warning("Please enter a description for the image to be generated.")
        st.stop()

    st.session_state.user_prompt_generate_image = f"""
    Generate the D2 code for the following diagram description:  
    {st.session_state.user_prompt}

    """
    generate_image_code()
    #render_image_from_code()

if render_image:
    render_image_from_code()

# Directory where image files are located
if os.path.exists(st.session_state.image_data_dir):
    show_image_files()
else:
    st.info("No image files found. Please generate and save an image file to see it listed here.")
