import streamlit as st
import requests
import time
import os
import shutil

from pathlib import Path
from git import Repo

from rcb_init import init_github_vars, add_log

def create_github_repo(repo_name) -> bool:
    """
    Function to create a GitHub repository using the GitHub API.
    Returns True if successful, False otherwise.
    """

    template_owner, template_repo_name = st.session_state.template_repo.split('/')
    headers = {
        "Authorization": f"token {st.session_state.github_token}",
        "Accept": "application/vnd.github.baptiste-preview+json"
    }

    payload = {
        "owner": st.session_state.github_org,
        "name": repo_name,
        "description": "Repository created from template using script",
        "private": st.session_state.is_private,
        "include_all_branches": True
    }

    response = requests.post(
        f"https://api.github.com/repos/{template_owner}/{template_repo_name}/generate",
        headers=headers,
        json=payload
    )

    if response.status_code == 201:
        print(f"Repository '{repo_name}' created successfully.")
        st.session_state.repo_verified = True
        st.session_state.repo_url = response.json().get('html_url', '')
        return True
    else:
        print(f"Failed to create repository: {response.json()}")
        st.session_state.repo_verified = False
        st.session_state.repo_url = ""
        return False

def check_github_repo_exists(repo_name: str) -> bool:
    """Check if GitHub repository exists"""
    init_github_vars()
    url = f"https://api.github.com/repos/{st.session_state.github_org}/{repo_name}"
    response = requests.get(url)
    if response.status_code == 200:
        print(f"Repository '{repo_name}' already exists.")
        st.session_state.repo_verified = True
        st.session_state.repo_url = response.json().get('html_url', '')
        return True
    elif response.status_code == 404:
        print(f"Repository '{repo_name}' does not exist.")
        st.session_state.repo_verified = False
        st.session_state.repo_url = ""
        return False
    else:
        print(f"Error checking repository: {response.json()}")
        st.session_state.repo_verified = False
        st.session_state.repo_url = ""
        return False

def convert_https_to_ssh(https_url: str) -> str:
    if https_url.startswith("https://github.com/"):
        repo_path = https_url.replace("https://github.com/", "")
        if repo_path.endswith(".git"):
            repo_path = repo_path[:-4]
        return f"git@github.com:{repo_path}.git"
    else:
        raise ValueError("Invalid GitHub HTTPS URL")

def setup_github_repo():
    with st.spinner("Setting up repository..."):
        exists = check_github_repo_exists(st.session_state.repo_name)
        if exists:
            st.session_state.repo_verified = True
            st.markdown("Repository already exists. Content will be overwritten.")
            st.session_state.repo_url = f"https://github.com/{st.session_state.github_org}/{st.session_state.repo_name}"
            print(f"Repository '{st.session_state.repo_name}' already exists. Content will be overwritten.")
            return True
        elif not exists:
            # If repository does not exist, create it
            st.session_state.repo_verified = False
            print(f"Creating new repository '{st.session_state.repo_name}'...")
            repo_created = create_github_repo(st.session_state.repo_name)
            if repo_created:
                st.session_state.repo_verified = True
                st.markdown("Repository created successfully.")
                st.session_state.repo_url = f"https://github.com/{st.session_state.github_org}/{st.session_state.repo_name}"
                print(f"Repository '{st.session_state.repo_name}' created successfully.")
                return True
            else:
                st.session_state.repo_verified = False
                st.session_state.repo_url = ""
                print(f"Failed to create repository '{st.session_state.repo_name}'. Please check the logs.")
                return False
    
    # Show repository link if verified
    if st.session_state.repo_verified and st.session_state.repo_url:
        # st.markdown(f"Repository URL: [View Repository]({st.session_state.repo_url})", unsafe_allow_html=True)

        # Clone the repository if it exists
        try:
            if not st.session_state.repo_cloned:
                # Use a spinner to indicate cloning process
                st.session_state.uploaded_files = []  # Reset uploaded files list
                st.session_state.repo_dir = ""  # Reset repo directory
                # Create a temporary directory to clone the repository
                with st.spinner("Cloning repository..."):
                    # Clone the repository to a temporary directory
                    time.sleep(5)
                    if not st.session_state.repo_dir:
                        ###temp_dir = tempfile.mkdtemp()
                        st.session_state.repo_dir = f"{st.session_state.user_dir}/content/{st.session_state.repo_name}"
                        st.session_state.repo_dir = Path(st.session_state.repo_dir)
                    if os.path.exists(st.session_state.repo_dir):
                        print(f"Directory {st.session_state.repo_dir} already exists, deleting the directory")
                        shutil.rmtree(f"{st.session_state.repo_dir}")
                    ssh_url = convert_https_to_ssh(st.session_state.repo_url)
                    print(f"Cloning {ssh_url} at {st.session_state.repo_dir}")
                    Repo.clone_from(ssh_url, st.session_state.repo_dir)
                    print(f"Repository is cloned at '{st.session_state.repo_dir}'")
                    st.session_state.uploaded_files = os.listdir(st.session_state.repo_dir)
                    add_log(f"Repository '{st.session_state.repo_name}' from url '{st.session_state.repo_url}' cloned successfully at '{st.session_state.repo_dir}'.")
                    st.session_state.modules_dir = st.session_state.repo_dir / "modules"
                    print(f"=====DEBUG: Set modules_dir to {st.session_state.modules_dir}")
                    st.session_state.repo_cloned = True
        except Exception as e:
            st.error(f"Failed to clone repository: {e}")
            add_log(f"Error cloning repository '{st.session_state.repo_name}': {e}")
            st.session_state.repo_verified = False
            st.session_state.repo_url = ""  

        # # Show required structure for the course objectives
        # st.markdown("""
        # **Required Structure for Training Objectives:**
                    
        # - Use `=` for course heading
        # - Use `==` for section headings
        # - Use `-` for topics under sections
        # """)

        st.session_state.chat_enabled = True
        
        # # Enable the chat interface if repository is verified
        # if not st.session_state.chat_enabled:
        #     st.session_state.chat_enabled = True

def push_to_github():
    """
    Push the changes to the GitHub repository.
    """
    st.session_state.progress_logs.info(f"Pushing changes to GitHub repository...")
    if not st.session_state.repo_dir:
        st.error("Repository directory is not set. Please verify the repository setup.")
        return

    repo_path = Path(st.session_state.repo_dir)
    if not repo_path.exists():
        st.error(f"Repository directory '{repo_path}' does not exist.")
        return

    try:
        repo = Repo(repo_path)
        repo.git.add(A=True)  # Add all changes
        st.session_state.commit_message = f"{st.session_state.commit_message} \nContent generated using {st.session_state.model_choice} via RCB."
        repo.index.commit(st.session_state.commit_message)  # Commit changes
        origin = repo.remote(name='origin')
        origin.pull()  # Pull latest changes from remote to avoid conflicts
        origin.push()  # Push changes to remote
        time.sleep(5)  # Wait for a few seconds to ensure push is complete
        st.session_state.progress_logs.success(f"Changes pushed to GitHub repository '{st.session_state.repo_name}' successfully.")
        print(f"Changes pushed to GitHub repository '{st.session_state.repo_name}' successfully.")
    except Exception as e:
        st.error(f"Failed to push changes: {e}")

def add_github_contributors(contributors_input: str):
    """
    Add contributors to the GitHub repository.
    """
    init_github_vars()
    if not st.session_state.repo_verified or not st.session_state.repo_url:
        st.error("Repository is not verified. Please set up the repository first.")
        return

    # Parse contributors input
    contributors = [c.strip() for c in contributors_input.replace(',', ' ').split() if c.strip()]
    if not contributors:
        st.info("No contributors provided.")
        return

    headers = {
        "Authorization": f"token {st.session_state.github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    for contributor in contributors:
        url = f"https://api.github.com/repos/{st.session_state.github_org}/{st.session_state.repo_name}/collaborators/{contributor}"
        payload = {
            "permission": "push"  # Can be 'pull', 'push', or 'admin'
        }
        response = requests.put(url, headers=headers, json=payload)
        if response.status_code in [201, 204]:
            st.toast(f"Added contributor '{contributor}' successfully.")
            print(f"Contributor '{contributor}' added to repository '{st.session_state.repo_name}'.")
        else:
            st.error(f"Failed to add contributor '{contributor}': {response.json()}")
            print(f"Error adding contributor '{contributor}': {response.json()}")
