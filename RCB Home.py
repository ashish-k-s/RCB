"""
Main page: Login | Create new project or Select existing project
Create or Set the data directory path
Project page: File upload for RAG | Select project DB for RAG
"""
import sys
print(sys.executable)
import streamlit as st
import tempfile
import shutil
import os
from authlib.integrations.requests_client import OAuth2Session
import secrets
import requests

from rcb_init import init_page
from rcb_rag_manager import process_uploaded_documents, show_file_content_dialog, clear_uploaded_content

if 'vectorstore' not in st.session_state:
    st.session_state.vectorstore = None
if 'retriever' not in st.session_state:
    st.session_state.retriever = None

st.set_page_config(
    page_title="Rapid Course Builder (RCB)"
)

st.title("Rapid Course Builder (RCB)")
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Home"
st.session_state.current_page = "Home"

init_page()




if st.session_state.auth_type == "Keycloak":
    # Initialize session state
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None
    if 'access_token' not in st.session_state:
        st.session_state.access_token = None

    # Keycloak configuration from secrets
    KEYCLOAK_CONFIG = {
        'client_id': st.secrets["auth"]["keycloak"]["client_id"],
        'client_secret': st.secrets["auth"]["keycloak"]["client_secret"],
        'server_metadata_url': st.secrets["auth"]["keycloak"]["server_metadata_url"],
        'scope': st.secrets["auth"]["keycloak"]["scope"],
        'redirect_uri': st.secrets["auth"].get("redirect_uri", "http://localhost:8501")
    }

    # Fetch OIDC discovery document
    @st.cache_resource
    def get_oidc_config():
        """Fetch OpenID Connect discovery document from Keycloak"""
        try:
            response = requests.get(KEYCLOAK_CONFIG['server_metadata_url'])
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Failed to fetch OIDC configuration: {e}")
            return None

    oidc_config = get_oidc_config()

    print(f"OIDC Configuration: {oidc_config}")

    print(f"User Info: {st.session_state.user_info}")

    print(f"Query Params: {st.query_params.to_dict()}")

    if oidc_config is None:
        st.error("Cannot connect to Keycloak. Please check your configuration.")
        st.stop()

    # Handle OAuth callback
    if 'code' in st.query_params:
        code = st.query_params['code']

        # Exchange authorization code for tokens
        oauth = OAuth2Session(
            client_id=KEYCLOAK_CONFIG['client_id'],
            client_secret=KEYCLOAK_CONFIG['client_secret'],
            redirect_uri=KEYCLOAK_CONFIG['redirect_uri'],
            scope=KEYCLOAK_CONFIG['scope']
        )

        try:
            token = oauth.fetch_token(
                url=oidc_config['token_endpoint'],
                authorization_response=st.query_params.to_dict(),
                code=code
            )

            st.session_state.access_token = token.get('access_token')

            # Fetch user info
            userinfo_response = requests.get(
                oidc_config['userinfo_endpoint'],
                headers={'Authorization': f'Bearer {st.session_state.access_token}'}
            )
            userinfo_response.raise_for_status()
            st.session_state.user_info = userinfo_response.json()

            # Clear query params and rerun
            st.query_params.clear()
            # st.rerun()
        except Exception as e:
            st.error(f"Authentication failed: {e}")
            st.session_state.user_info = None
            st.session_state.access_token = None

    # Display UI based on authentication status
    if st.session_state.user_info is None:
        st.write("Please log in to continue.")

        if st.button("SSO Login"):
            # Generate state parameter for CSRF protection
            state = secrets.token_urlsafe(32)

            # Create OAuth session
            oauth = OAuth2Session(
                client_id=KEYCLOAK_CONFIG['client_id'],
                redirect_uri=KEYCLOAK_CONFIG['redirect_uri'],
                scope=KEYCLOAK_CONFIG['scope'],
                state=state
            )

            # Generate authorization URL
            authorization_url, state = oauth.create_authorization_url(
                oidc_config['authorization_endpoint']
            )

            # Redirect to Keycloak login
            st.markdown(f'<meta http-equiv="refresh" content="0;url={authorization_url}">', unsafe_allow_html=True)
            st.write(f"[Click here if not redirected automatically]({authorization_url})")
    else:
        user = st.session_state.user_info
        st.write(f"Welcome, {user.get('name', user.get('preferred_username', 'User'))}!")
        st.session_state.username = user.get('preferred_username', 'User')
        st.session_state.disable_all = False
        print(f"Logged in as: {st.session_state.username}")

        # st.write("**User Information:**")
        # st.json(user)
    
print(f"Username in session state: {st.session_state.get('username', '')}")
if st.session_state.username is set:
    if st.button("Log out"):
        # Clear session
        st.session_state.user_info = None
        st.session_state.access_token = None

        # Optional: redirect to Keycloak logout endpoint
        logout_url = oidc_config.get('end_session_endpoint')
        if logout_url:
            redirect_after_logout = KEYCLOAK_CONFIG['redirect_uri']
            full_logout_url = f"{logout_url}?redirect_uri={redirect_after_logout}"
            st.markdown(f'<meta http-equiv="refresh" content="0;url={full_logout_url}">', unsafe_allow_html=True)
        else:
            st.rerun()
        # st.rerun()




if 'use_maas' not in st.session_state:
    st.session_state.use_maas = True

# If no SSO, set AUTH_TYPE = "placeholder" in .env file
if st.session_state.auth_type == "placeholder":
    st.subheader("This is a placeholder login page")
    user_name = st.text_input("Username", value=st.session_state.username)

    if st.button("Login"):
        st.session_state.username = user_name
        st.session_state.disable_all = False
        print(f"Logged in as: {st.session_state.username}")
        # st.rerun()

with open("RCB Home.md", "r") as f:
    markdown_content = f.read()
st.markdown(markdown_content)

with st.sidebar:
    st.subheader("RAG Documents Upload")
    uploaded_files = st.file_uploader(
        "Upload Documents for RAG,",
        type=["pdf", "docx", "xlsx", "pptx", "csv", "asciidoc"],
        accept_multiple_files=True,
        help=f"Upload documents to provide context for the AI. Supported formats: pdf, docx, xlsx, pptx, csv, asciidoc",
        disabled=st.session_state.disable_all
    )
    if uploaded_files:
        process_files_button = st.button("Process Documents")
        if process_files_button:
            print(f"UPLOADED FILES:\n {uploaded_files}")
            ## Remove duplicate file names
            unique_files = []
            seen_names = set()
            for file in uploaded_files:
                if file.name not in seen_names:
                    unique_files.append(file)
                    seen_names.add(file.name)
            #uploaded_files = list(set(uploaded_files))
            print(f"UPLOADED_UNIQUE_FILES: \n {unique_files}")
            process_uploaded_documents(unique_files)
            #save_uploaded_documents(unique_files)

    if os.path.exists(f"{st.session_state.user_dir}/uploads"):
        view_uploads = st.button("View uploads")
        clear_uploads = st.button("Clear uploads")

        if view_uploads:
            show_file_content_dialog(f"{st.session_state.user_dir}/uploads-hash.txt")

        if clear_uploads:
            clear_uploaded_content()

