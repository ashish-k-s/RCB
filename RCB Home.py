"""
Main page: Login | Create new project or Select existing project
Create or Set the data directory path
Project page: File upload for RAG | Select project DB for RAG
"""
import streamlit as st
import tempfile
import shutil
import os

st.set_page_config(
    page_title="Rapid Course Builder (RCB)"
)

st.title("Rapid Course Builder (RCB)")
st.sidebar.success("Select a page above.")

if 'use_maas' not in st.session_state:
    st.session_state.use_maas = True

# START Initialize session state variables 

# END Initialize session state variables

# START Function definitions

# END Function definitions

username = "rcbuser1"

# column_left, column_right = st.columns([1,2])

# with column_left:
#     st.subheader("GitHub Repo")

# with column_right:
#     FILE_SIZE_MAX = 10 ## move this to config
#     st.markdown("#### Data for RAG")
#     st.markdown("#### Document Upload")

#     uploaded_files = st.file_uploader(
#         "Upload Documents,",
#         type=['pdf','txt'],
#         accept_multiple_files=True,
#         help=f"Upload documents to provide context for the AI. Max Size {FILE_SIZE_MAX} MB per file"
#     )

#     if uploaded_files:
#         process_files_button = st.button("Process Documents")
#         if process_files_button:
#             print(f"UPLOADED FILES:\n {uploaded_files}")
#             ## Remove duplicate file names
#             unique_files = []
#             seen_names = set()
#             for file in uploaded_files:
#                 if file.name not in seen_names:
#                     unique_files.append(file)
#                     seen_names.add(file.name)
#             #uploaded_files = list(set(uploaded_files))
#             print(f"UPLOADED_UNIQUE_FILES: \n {unique_files}")
#             process_uploaded_documents(unique_files)

#     # GitHub Repository Information
#     ##st.subheader("GitHub Repository")
#     # st.write(f"Repository URL: {st.session_state.repo_url}")
#     # st.write(f"Repository Verified: {st.session_state.repo_verified}")
    
#     # repo_name = st.text_input(
#     #     "Repository Name",
#     #     help="Enter the name of the GitHub repository"
#     # )

#     if not st.session_state.repo_name:
#         st.session_state.repo_name = repo_name.strip()

#     # Repos setup button
#     if st.button("Setup Repository", disabled=not repo_name.strip()):
#         with st.spinner("Setting up repository..."):
#             exists = check_github_repo_exists(repo_name)
#             if exists:
#                 st.session_state.repo_verified = True
#                 st.markdown("Repository already exists. Content will be overwritten.")
#                 st.session_state.repo_url = f"https://github.com/{GITHUB_USER}/{repo_name}"
#                 add_log(f"Repository '{repo_name}' already exists. Content will be overwritten.")
#             elif not exists:
#                 # If repository does not exist, create it
#                 st.session_state.repo_verified = False
#                 add_log(f"Creating new repository '{repo_name}'...")
#                 success = create_github_repo(repo_name)
#                 if success:
#                     st.session_state.repo_verified = True
#                     st.markdown("Repository created successfully.")
#                     st.session_state.repo_url = f"https://github.com/{GITHUB_USER}/{repo_name}"
#                     add_log(f"Repository '{repo_name}' created successfully.")
#                 else:
#                     st.session_state.repo_verified = False
#                     st.session_state.repo_url = ""
#                     add_log(f"Failed to create repository '{repo_name}'. Please check the logs.")
        
#     # Show repository link if verified
#     if st.session_state.repo_verified and st.session_state.repo_url:
#         st.markdown(f"Repository URL: [View Repository]({st.session_state.repo_url})", unsafe_allow_html=True)

#         # Clone the repository if it exists
#         try:
#             if not st.session_state.repo_cloned:
#                 # Use a spinner to indicate cloning process
#                 st.session_state.uploaded_files = []  # Reset uploaded files list
#                 st.session_state.repo_dir = ""  # Reset repo directory
#                 # Create a temporary directory to clone the repository
#                 with st.spinner("Cloning repository..."):
#                     # Clone the repository to a temporary directory
#                     time.sleep(5)
#                     if not st.session_state.repo_dir:
#                         temp_dir = tempfile.mkdtemp()
#                         st.session_state.repo_dir = f"{st.session_state.datadir}/content/{st.session_state.repo_name}"
#                         st.session_state.repo_dir = Path(st.session_state.repo_dir)
#                     ssh_url = convert_https_to_ssh(st.session_state.repo_url)
#                     Repo.clone_from(ssh_url, st.session_state.repo_dir)
#                     print(f"Repository is cloned at '{st.session_state.repo_dir}'")
#                     st.session_state.uploaded_files = os.listdir(st.session_state.repo_dir)
#                     add_log(f"Repository '{st.session_state.repo_name}' from url '{st.session_state.repo_url}' cloned successfully at '{st.session_state.repo_dir}'.")
#                     st.session_state.repo_cloned = True
#         except Exception as e:
#             st.error(f"Failed to clone repository: {e}")
#             add_log(f"Error cloning repository '{st.session_state.repo_name}': {e}")
#             st.session_state.repo_verified = False
#             st.session_state.repo_url = ""  


# EMBEDDING_MODEL = 
# LLM_MODEL = 