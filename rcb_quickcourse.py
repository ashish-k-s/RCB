import streamlit as st
import os
import re
import csv
import shutil
import time

from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from io import StringIO


from rcb_init import init_page, init_llm_vars, init_quickcourse_page, add_log, init_quickcourse_vars, init_quickcourse_prompts, init_translation_prompts, init_transcript_prompts
from rcb_llm_manager import call_llm_to_generate_response
from rcb_rag_manager import retrieve_context
from rcb_audio import generate_audio_file_from_transcript
    
def extract_code_blocks(text):
    """
    Extract text from triple backtick code blocks.
    If no triple backtick blocks are found, return the original text as-is.
    """
    # Find all code blocks between triple backticks
    code_blocks = re.findall(r'```(?:[a-zA-Z0-9_-]*\n)?(.*?)```', text, re.DOTALL)

    print(f"Extracted code blocks: {code_blocks}")

    # If any code blocks are found, return them
    if code_blocks:
        return code_blocks

    # Otherwise, return the text as is
    print(f"No code blocks found, returning original text. {text}")
    return [text]

def generate_filename(text):
    # Convert to lowercase
    text = text.lower()
    
    # Replace special characters with space
    text = re.sub(r'[^\w\s-]', '', text)
    
    # Replace whitespace with a single hyphen
    text = re.sub(r'\s+', '-', text.strip())

    # Remove leading/trailing hyphens
    text = text.strip('-')

    return text

def multiline_to_csv(input_text):
    output = StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(["original_text", "filename"])

    for line in input_text.strip().splitlines():
        clean_line = line.strip()
        if clean_line:  # skip empty lines
            filename = generate_filename(clean_line)
            writer.writerow([clean_line, filename])

    csv_output = output.getvalue()
    print(csv_output)

    st.session_state.course_structure_csv = f"{st.session_state.user_dir}/TEMP-course_structure_file.csv"
    with open(st.session_state.course_structure_csv, 'w', encoding='utf-8') as file:
        file.write(csv_output)

    st.session_state.show_proceed_button = False
    st.session_state.show_submit_button = False
    st.session_state.show_logs = True
    st.session_state.logs.append("Proceeding to generate course layout...")
    st.session_state.logs.append(f"Course outline file generated: {st.session_state.course_outline_file}")

    st.rerun()

# --- Read chapter list from CSV file ---
def read_chapter_list(course_structure_csv):
    chapters = []
    sections = []
    chapter_name = ""
    section_name = ""
    print(f"DEBUG: Reading chapter list from {st.session_state.course_structure_csv}...")
    try:
        with open(st.session_state.course_structure_csv, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip().startswith('=') and len(row) > 1:

                    antora_course_title = row[0].strip()
                    if not st.session_state.antora_course_title:
                        st.session_state.antora_course_title = antora_course_title
                    print(f"DEBUG: st.session_state.antora_course_title: {st.session_state.antora_course_title}")

                if row and row[0].strip().startswith('==') and len(row) > 1:
                    chapter_name = row[1].strip()
                    chapters.append(chapter_name)
                    chapter_desc_str = row[0].strip()
                    st.session_state.desc_chapters.append(chapter_desc_str)

                    os.makedirs(f"{st.session_state.modules_dir}/{chapter_name}", exist_ok=True)
                 
                    # Define the full file path for nav.adoc
                    section_path_nav = Path(f"{st.session_state.modules_dir}/{chapter_name}/nav.adoc")
                    section_path_page = Path(f"{st.session_state.modules_dir}/{chapter_name}/pages/{chapter_name}.adoc")

                    root_path_nav = Path(f"{st.session_state.modules_dir}/ROOT/nav.adoc")
                    root_path_index = Path(f"{st.session_state.modules_dir}/ROOT/pages/index.adoc")
                    root_path_index.parent.mkdir(parents=True, exist_ok=True)     

                    # Create the parent directories if they don't exist
                    section_path_nav.parent.mkdir(parents=True, exist_ok=True)
                    section_path_page.parent.mkdir(parents=True, exist_ok=True)

                    root_path_nav.parent.mkdir(parents=True, exist_ok=True)

                    # Create the empty file
                    section_path_nav.touch()
                    section_path_page.touch()
                    root_path_nav.touch()
                    root_path_index.touch()
                    print("\n\nDEBUG: course_outline_str", st.session_state.course_outline_str)

                    with open(section_path_nav, 'a') as f:
                        f.write(f"* xref:{chapter_name}.adoc[]"+'\n')
                    with open(section_path_page, 'a') as f:
                        text = re.sub(r'(==|-)', '', row[0], count=1)
                        st.session_state.topic = text
                        f.write(f"# {text}")
                        
                        # Retrieve RAG context for this chapter/topic
                        st.session_state.context_from_rag = retrieve_context(text)

                        print("BUILDING PAGE SUMMARY")
                        st.session_state.progress_logs.info(f"Building page summary for topic: {text}")
                        init_quickcourse_prompts() # Re-initialize prompts to update context and topics
                        response = call_llm_to_generate_response(st.session_state.model_choice, st.session_state.system_prompt_page_summary, st.session_state.user_prompt_page_summary)
                        print("PAGE SUMMARY: ", response)
                        f.write("\n\n")
                        f.write(response)

                if row and row[0].strip().startswith('-') and len(row) > 1:
                    section_name = row[1].strip()
                    page_section_adoc = f"{st.session_state.modules_dir}/{chapter_name}/pages/{section_name}.adoc"
                    with open(page_section_adoc, 'a') as f:
                        text = re.sub(r'(==|-)', '', row[0], count=1)
                        st.session_state.topic = text
                        f.write(f"# {text}")
                        print(f"DEBUG: Topic text: {text}")
                        # Retrieve RAG context for this section/topic
                        st.session_state.context_from_rag = retrieve_context(text)

                        print("BUILDING PAGE CONTENT")
                        st.session_state.progress_logs.info(f"Building page content for topic: {text}")


                        print("BUILDING DETAILED CONTENT")
                        st.session_state.progress_logs.info(f"Building detailed content for topic: {text}")

                        init_quickcourse_prompts() # Re-initialize prompts to update context and topics
                        response = call_llm_to_generate_response(st.session_state.model_choice, st.session_state.system_prompt_detailed_content, st.session_state.user_prompt_detailed_content)
                        print("PAGE SUMMARY: ", response)
                        ##st.write(response)
                        f.write("\n\n")
                        f.write(response)

                    with open(section_path_nav, 'a') as f:
                        f.write(f"** xref:{section_name}.adoc[]"+'\n')
            
                
    except FileNotFoundError:
        print(f"CSV file '{st.session_state.course_structure_csv}' not found.")
    return chapters

# --- Render antora.yml template ---
def generate_antora_yml():
    chapters = read_chapter_list(st.session_state.course_structure_csv)
    st.session_state.progress_logs.info(f"Generating supporting files")

    env = Environment(loader=FileSystemLoader(st.session_state.antora_template_dir))
    template = env.get_template('antora.yml.j2')
    template_pb = env.get_template('antora-playbook.yml.j2')
    template_root_index = env.get_template('root-index.adoc.j2')

    print(f"DEBUG: antora_course_title before assignment: >>>>>>>>>> {st.session_state.antora_course_title}")
    if st.session_state.antora_course_title:
        course_title_str = st.session_state.antora_course_title.strip('=')

    topics = [chapter_desc.strip('=') for chapter_desc in st.session_state.desc_chapters]

    print(f"DEBUG: Assigned repo name: {st.session_state.repo_name}")
    print(f"DEBUG: course title: {course_title_str}")

    print(f"==== st.session_state.repo_name: {st.session_state.repo_name}")
    rendered = template.render(
        repo_name=st.session_state.repo_name,
        course_title=course_title_str,
        version='1.0.0',
        chapters=chapters
    )

    print(f"DEBUG: antora_output_file: >>>>>>>>>> {st.session_state.antora_output_file}")
    with open(st.session_state.antora_output_file, 'w') as f:
        f.write(rendered)

    rendered_pb = template_pb.render(
        repo_name=st.session_state.repo_name,
        course_title=course_title_str,
    )

    with open(st.session_state.antora_pb_file, 'w') as f:
        f.write(rendered_pb)

    print(f"DEBUG: antora_course_title: >>>>>>>>>> {st.session_state.antora_course_title}")
    print(f"DEBUG: st.session_state.antora_course_title: >>>>>>>>>> {st.session_state.antora_course_title}")
    print(f"DEBUG: st.session_state.desc_chapters: >>>>>>>>>> {st.session_state.desc_chapters}")


    rendered_root_index = template_root_index.render(
        course_title=course_title_str,
        desc_chapters=topics
    )

    with open(f"{st.session_state.modules_dir}/ROOT/pages/index.adoc", 'w') as f:
        f.write(rendered_root_index)

    # Create nav.adoc file in ROOT
    with open(f"{st.session_state.modules_dir}/ROOT/nav.adoc", "w") as file:
        file.write("* xref:index.adoc[]\n")


    print(f"{st.session_state.antora_output_file} generated with chapters: {chapters}")
    print(f"Topics covered in the training: {st.session_state.desc_chapters}")

def translate_adoc(target_language) -> str:
    # Perform translation or other processing here
    init_translation_prompts(target_language)
    translated_content = call_llm_to_generate_response(st.session_state.model_choice, st.session_state.system_prompt_translate_content, st.session_state.user_prompt_translate_content)
    return translated_content

def create_transcript_adoc(adoc_content) -> str:
    # Perform transcript creation here
    init_transcript_prompts()
    transcript_txt = call_llm_to_generate_response(st.session_state.model_choice, st.session_state.system_prompt_create_transcript, st.session_state.user_prompt_create_transcript)
    return transcript_txt

def translate_all_adoc_files(target_language: str):
    st.session_state.show_logs = True
    for source_file in st.session_state.source_modules.rglob("*.adoc"):
        # Corresponding target file path
        target_file = st.session_state.target_modules / relative_path

        # Create target directory if it doesn't exist
        target_file.parent.mkdir(parents=True, exist_ok=True)

        print(f"Processing {source_file} for translation to {target_language} at {target_file}")
        if source_file.name == "nav.adoc":
            st.session_state.progress_logs.info(f"Copying {source_file}")
            print(f"Copying {source_file}")
            shutil.copy2(source_file, target_file)

        # st.write(f"Translating {source_file} to {target_language}")
        # st.session_state.logs.append(f"Translating {source_file} to {target_language}")

        print(f"Translating {source_file} to {target_language}")
        st.session_state.progress_logs.info(f"Translating {source_file} to {target_language}")

        # Relative path from source modules directory
        relative_path = source_file.relative_to(st.session_state.source_modules)

        # Read source content
        with open(source_file, "r", encoding="utf-8") as f:
            st.session_state.adoc_content = f.read()

        # Process content
        translated_content = translate_adoc(target_language)

        # Write to target location
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(translated_content)

        print(f"Processed: {source_file}")
        print(f"Written to: {target_file}")
    return True

def copy_module_assets(src_repo, dst_repo):
    """
    Copy directories under modules/*/* except 'pages'.

    Example copies:
      modules/chapter1/images
      modules/appendix/attachments

    Example excludes:
      modules/chapter1/pages
      modules/chapter1/nav.adoc
      modules/chapter2/nav.adoc
    """

    src_modules = Path(src_repo) / "modules"
    dst_modules = Path(dst_repo) / "modules"

    if not src_modules.exists():
        raise FileNotFoundError(f"Source modules directory not found: {src_modules}")

    for module_dir in src_modules.iterdir():
        if not module_dir.is_dir():
            continue

        # Look only at modules/<module_name>/*
        for item in module_dir.iterdir():
            # Skip files (e.g. nav.adoc)
            if not item.is_dir():
                continue

            # Skip pages directory
            if item.name == "pages":
                continue

            relative_path = item.relative_to(src_modules)
            destination = dst_modules / relative_path

            print(f"Copying: {item} -> {destination}")
            st.session_state.progress_logs.info(f"Copying: {item} -> {destination}")

            # Python 3.8+: overwrite existing destination
            shutil.copytree(item, destination, dirs_exist_ok=True)


def generate_audio_all():
    print(f"Generating audio for all .txt files in {st.session_state.repo_name} using model {st.session_state.model_choice}")
    st.session_state.repo_path = Path(st.session_state.repo_dir) / "modules"
    print(f"Repo path for audio generation: {st.session_state.repo_path}")

    for txt_file in st.session_state.repo_path.rglob("*.txt"):
        print(f"Processing transcript for {txt_file}")
        p = Path(txt_file)
        images_dir = p.parent.parent / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        transcript_wav_file = images_dir / f"{p.stem}.wav"
        print(f"Audio file path: {transcript_wav_file}")
        if transcript_wav_file.is_file():
            print(f"Audio file already exists: {transcript_wav_file}")
            st.session_state.progress_logs.info(f"Audio file already exists: {transcript_wav_file}")
            time.sleep(1)
            continue
        print(f"Generating audio for {txt_file} in {transcript_wav_file} file")
        st.session_state.progress_logs.info(f"Generating audio for {txt_file} in {transcript_wav_file} file")

        # Read source content
        # with open(txt_file, "r", encoding="utf-8") as f:
        #     st.session_state.transcript_txt_content = f.read()
        st.session_state.default_audio_file_path_txt = txt_file
        st.session_state.default_audio_file_path_wav = transcript_wav_file
        st.session_state.default_audio_file_path_mp3 = str(transcript_wav_file).replace(".wav",".mp3")
        generate_audio_file_from_transcript()

        print(f"Processed: {txt_file}")
        print(f"Written to: {transcript_wav_file}")
    st.session_state.progress_logs.info(f"Audio generation completed for all .txt files in {st.session_state.repo_name}")
    return True

def create_transcript_all():
    print(f"Creating transcript for all .adoc files in {st.session_state.repo_name} using model {st.session_state.model_choice}")
    st.session_state.show_logs = True
    st.session_state.repo_path = Path(st.session_state.repo_dir) / "modules"

    for adoc_file in st.session_state.repo_path.rglob("*.adoc"):
        print(f"Processing transcript for {adoc_file}")
        ## QuickCourse repo supports json file for transcript with timestamp. Creation of JSON file with timestamp to be implemented in the future.
        p = Path(adoc_file)
        images_dir = p.parent.parent / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        transcript_txt_file = images_dir / f"{p.stem}.txt"
        print(f"Teanscript file path: {transcript_txt_file}")
        if adoc_file.name == "nav.adoc":
            st.session_state.progress_logs.info(f"Skipping transript for {adoc_file}")
            print(f"Skipping transcript for {adoc_file}")
            st.session_state.progress_logs.info(f"Skipping creation of transcript for {adoc_file}")
            continue

        # adoc_file_txt = str(Path(adoc_file).with_suffix(".txt"))
        ## Skip creation of transcript if it already exists
        if transcript_txt_file.exists():
            st.session_state.progress_logs.info(f"Transcript file already exists: {transcript_txt_file}")
            print(f"Transcript file already exists: {transcript_txt_file}")
            time.sleep(1)
            continue
        print(f"Creating transcript for {adoc_file} in {transcript_txt_file} file")
        st.session_state.progress_logs.info(f"Creating transcript for {adoc_file} in {transcript_txt_file} file")

        # Read source content
        with open(adoc_file, "r", encoding="utf-8") as f:
            st.session_state.adoc_content = f.read()

        # Process content
        transcript_txt = create_transcript_adoc(st.session_state.adoc_content)

        # Write to target location
        with open(transcript_txt_file, "w", encoding="utf-8") as f:
            f.write(transcript_txt)

        print(f"Processed: {adoc_file}")
        print(f"Written to: {transcript_txt_file}")
        ## Delete the audio files associated with the transcript
        audio_file = images_dir / f"{p.stem}.wav"
        if audio_file.exists():
            st.session_state.progress_logs.info(f"Deleting audio file: {audio_file}")
            audio_file.unlink()
            print(f"Deleted audio file: {audio_file}")
    st.session_state.progress_logs.info(f"Transcript creation completed for all .adoc files in {st.session_state.repo_name}")
    return True

def update_adocs_for_audio():
    st.session_state.progress_logs.info("Updating .adoc files to include audio and transcript attributes")
    for adoc_file in st.session_state.repo_path.rglob("*.adoc"):
        file_path = Path(adoc_file)
        audio_line = f":page-audio-src: {file_path.stem}.wav"
        transcript_line = f":page-transcript-src: {file_path.stem}.txt"

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Idempotency check
        content = "".join(lines)
        if audio_line in content and transcript_line in content:
            print("Attributes already present. No changes made.")
            st.session_state.progress_logs.info(f"Attributes already present in {file_path}. No changes made.")
        else:
            new_lines = []
            inserted = False

            for line in lines:
                new_lines.append(line)

                if not inserted and line.startswith("= "):
                    if audio_line not in content:
                        new_lines.append(audio_line + "\n")
                    if transcript_line not in content:
                        new_lines.append(transcript_line + "\n")
                    inserted = True

            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            print("Attributes added.")
            st.session_state.progress_logs.info(f"Attributes added to {st.session_state.repo_name}.")
    # return True            