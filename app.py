from langchain_openai import ChatOpenAI 
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.llms import Ollama
import streamlit as st
import os
from dotenv import load_dotenv
import logging
import re
import csv
import sys
from io import StringIO
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

response = ""
outline = ""
topic = ""
course_outline_file = "TEMP-outline.adoc"
course_structure_file_names = "TEMP-course_structure_file_names.csv"

system_prompt_course_outline = """
You are a Course Designer expert in understanding the requirements of the curriculum and developing the course outline.
**You always write the course outline in AsciiDoc-formatted text inside a code block.**
Your job is **not** to write the course content. You follow the below rules to write course outline:
    - Refer to the provided list of course objectives and available context.
    - Curate the text in provided objectives.
    - Derive the sub-topics to be covered to fulfil the provided list of objectives.
    - **Always Restrict the structure to have only one level of sub-topics.**
    - **Derive heading for the course.**
    - Separate the layout to different topic and sub-topic as necessary.
    - **Include the section for hands-on lab when it is required.**
    - Respond with the curated list of objectives and sub-topics to be covered under each of the objectives.
    - Provide the output in a codeblock in AsciiDoc (.adoc) format.
    - **Always** use the below AsciiDoc syntax:
        - Heading H1 with symbol "=" for course heading
        - Heading H2 with symbol "==" for topic
        - Bullet with symbol "-" for sub-topic
    - Do not pre-fix "Objective" or "Module" or "Chapter" or any other such string in the generated output.
    - Do not number the topics, or add underline or any other decorations.
    - Provide topics and sub-topics in the form of bullets and sub-bullets.
    - Do not include any introductory or closing text in your response.
"""

user_prompt_course_outline = """
        Here are the list of objectives for which course outline is to be created: 
        {objectives}
"""

system_prompt_page_summary = """
You are a Content Developer, expert in providing short description for any given topic.
Your task is to provide short explanation of provided topic.

 **You always write content in Antora AsciiDoc format and present it in a code block for ease of copying the output and storing it in ".adoc" file.**

Your responsibilities include:
- Simplifying complex technical concepts into accessible explanations
- Writing clear, concise, and short technical explanation on provided topic.

Use the provided context as your primary knowledge base. Reference it where appropriate to ensure accuracy and continuity.

You are currently assigned to work on the training content covering the below mentioned objectives:

{outline}

"""

user_prompt_page_summary = """
Keeping the whole list of objectives tobe covered in mind, write short description (one paragraph) for the below topic:

{topic}

Stick to this mentioned topic in your response.

"""
system_prompt_detailed_content = """
You are a Content Architect, combining the roles of Technical Writer and Subject Matter Expert. Your mission is to develop high-quality detailed educational content that is technically accurate, engaging, inclusive, and adaptable for different learning levels. **You always write content in Antora AsciiDoc format and present it in a code block for ease of copying the output and storing it in ".adoc" file.**

Your responsibilities include:
- Simplifying complex technical concepts into accessible explanations
- Writing clear, concise, and engaging content for diverse audiences
- Developing practical hands-on lab activities with real-world examples
- Providing expert-level insights and troubleshooting guidance

When drafting content, always:

1. Write **detailed technical explanation**
2. Incorporate step-by-step **hands-on activities** where applicable

Use the provided context as your primary knowledge base. Reference it where appropriate to ensure accuracy and continuity.

You are currently assigned to work on the training content covering the below mentioned objectives:

{outline}

"""

user_prompt_detailed_content = """
Keeping the whole list of objectives tobe covered in mind, write content for the below topic:

{topic}

Stick to the mentioned topic in your response.
"""

def build_prompt(system_prompt: str, user_prompt:str):
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", user_prompt)

        ]
    )

# --- Configuration for jinja2 file to generate antora.yml---
antora_template_dir = './templates'          # folder where antora.yml.j2 is stored
antora_output_file = 'antora.yml'            # output location
antora_csv_file = course_structure_file_names
antora_repo_name = 'sample-repo-name' # Get this from user input
antora_course_title = 'Sample Course Title' # Use the course heading fron csv file
antora_course_version = '1'

# --- Read chapter list from CSV file ---
def read_chapter_list(antora_csv_file):
    chapters = []
    sections = []
    chapter_name = ""
    section_name = ""
    try:
        with open(antora_csv_file, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip().startswith('==') and len(row) > 1:
                    chapter_name = row[1].strip()
                    chapters.append(chapter_name)
                    os.makedirs(f"modules/{chapter_name}", exist_ok=True)
                 
                    # Define the full file path for nav.adoc
                    section_path_nav = Path(f"modules/{chapter_name}/nav.adoc")
                    section_path_page = Path(f"modules/{chapter_name}/pages/{chapter_name}.adoc")

                    # Create the parent directories if they don't exist
                    section_path_nav.parent.mkdir(parents=True, exist_ok=True)
                    section_path_page.parent.mkdir(parents=True, exist_ok=True)

                    # Create the empty file
                    section_path_nav.touch()
                    section_path_page.touch()
                    with open(section_path_nav, 'a') as f:
                        f.write(f"* xref:{chapter_name}.adoc[]"+'\n')
                    with open(section_path_page, 'a') as f:
                        text = re.sub(r'(==|-)', '', row[0], count=1)
                        f.write(f"# {text}")

                        ## Build prompt and call llm to generate page summary
                        prompt = build_prompt(system_prompt_page_summary, user_prompt_page_summary)
                        print("BUILDING PAGE SUMMARY")
                        print("prompt: ", prompt)
                        chain = prompt | llm | output_parser
                        response = chain.invoke({"outline": outline, "topic": text})
                        print("PAGE SUMMARY: ", response)
                        #st.write(response)
                        text = extract_code_blocks(response)
                        f.write(f"\n\n{text}")

                if row and row[0].strip().startswith('-') and len(row) > 1:
                    section_name = row[1].strip()
                    page_section_adoc = f"modules/{chapter_name}/pages/{section_name}.adoc"
                    with open(page_section_adoc, 'a') as f:
                        text = re.sub(r'(==|-)', '', row[0], count=1)
                        f.write(f"# {text}")
                        ## Build prompt and call llm to generate page content
                        prompt = build_prompt(system_prompt_detailed_content, user_prompt_detailed_content)
                        print("BUILDING PAGE CONTENT")
                        print("prompt: ", prompt)
                        chain = prompt | llm | output_parser
                        response = chain.invoke({"outline": outline, "topic": text})
                        print("PAGE CONTENT: ", response)
                        #st.write(response)
                        text = extract_code_blocks(response)
                        f.write(f"\n\n{text}")

                    with open(section_path_nav, 'a') as f:
                        f.write(f"** xref:{section_name}.adoc[]"+'\n')
            
                
    except FileNotFoundError:
        print(f"CSV file '{csv_file}' not found.")
    return chapters

# --- Render antora.yml template ---
def generate_antora_yml():
    chapters = read_chapter_list(antora_csv_file)

    env = Environment(loader=FileSystemLoader(antora_template_dir))
    template = env.get_template('antora.yml.j2')

    rendered = template.render(
        repo_name=antora_repo_name,
        course_title=antora_course_title,
        version=antora_course_version,
        chapters=chapters
    )

    with open(antora_output_file, 'w') as f:
        f.write(rendered)

    print(f"{antora_output_file} generated with chapters: {chapters}")


# Function to extract code block from the response generated by LLM.
def extract_code_blocks(text):
    # Match content between triple backticks
    code_blocks = re.findall(r'```(?:[a-zA-Z0-9]*\n)?(.*?)```', text, re.DOTALL)
    return code_blocks

# START: Code to generate filenames for each topic in the course outline.
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

    return output.getvalue()

# END: Code to generate filenames for each topic in the course outline.

# LOGGING SETUP
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()
## os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")

## streamlit framework
st.title("Rapid Course Builder (RCB)")
text_input = st.chat_input("Enter the list of training objectives:")

## Ollama model to generate response
llm = Ollama(model="granite3.3:8b")
output_parser = StrOutputParser()

## Build prompt to generate course outline
prompt = build_prompt(system_prompt_course_outline, user_prompt_course_outline)
chain = prompt | llm | output_parser
print("prompt: ", prompt)
logger.info(f"PROMPT: {prompt}")

if text_input:
    response = chain.invoke({"objectives": text_input})
    print("RESPONSE: ", response)
    st.write(response)


outline = extract_code_blocks(response)

## Write course outline to an AsciiDoc file
with open(course_outline_file, "w") as file:
    for line in outline:
        file.write(line + "\n")

## START: Derive name of the files for course structure

## Read outline.adoc in string
with open(course_outline_file, 'r', encoding='utf-8') as file:
    outline_file_content = file.read()

print(outline_file_content)

csv_output = multiline_to_csv(outline_file_content)
print(csv_output)

with open(course_structure_file_names, 'w', encoding='utf-8') as file:
    file.write(csv_output)

## END: Derive name of the files for course structure


## START: Generate course layout
generate_antora_yml()
## END: Generate course layout
