import streamlit as st
from dotenv import load_dotenv

from rcb_init import init_page, init_llm_vars, init_chat_interface_prompts
from rcb_llm_manager import call_llm_to_generate_response

def get_ai_response():
    init_chat_interface_prompts()
    try:
        ai_response = call_llm_to_generate_response(st.session_state.model_choice,st.session_state.system_prompt_chat_interface, st.session_state.user_prompt_chat_interface)
        print(f"AI Response: {ai_response}")
        # Add AI response to chat history
        st.session_state.chat_history.append({
            'role': 'RCB',
            'content': ai_response
        })
        st.session_state.chat_container.info("**RCB:**", icon="🤖", width=100)
        st.session_state.chat_container.write(f"{ai_response}")

        print(f"CHAT HISTORY:\n {st.session_state.chat_history}")

        st.rerun()
    except Exception as e:
        st.error(f"Error generating response: {str(e)}")

def render_chat_interface_ui():
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.session_state.chat_interface_persona = st.selectbox("Select persona", options=["RCB Chat", "RCB Curator"], disabled=st.session_state.disable_all)
    with col2:
        st.checkbox("Use Context from RAG database", disabled=st.session_state.disable_all, value=True)
    with col3:
        st.checkbox("Use Conversation History", disabled=st.session_state.disable_all, value=False)
        st.button("Reset Conversation", disabled=st.session_state.disable_all, on_click=lambda: st.session_state.chat_history.clear())

    st.session_state.chat_container = st.container(height=600, border=True)

    update_chat_container()

    st.session_state.user_input = st.chat_input("Type your message:", key="user_message_input", disabled=st.session_state.disable_all)

    # Process user input
    if st.session_state.user_input and st.session_state.user_input.strip():
        # Add user message to chat history
        st.session_state.chat_history.append({
            'role': 'user',
            'content': st.session_state.user_input
        })
        st.session_state.chat_container.info("**You:**", width=100, icon="👤")
        st.session_state.chat_container.write(f"{st.session_state.user_input}")
        get_ai_response()

def update_chat_container():
    with st.session_state.chat_container:
        for message in st.session_state.chat_history:
            if message['role'] == 'user':
                st.info("**You:**", width=100, icon="👤")
                st.text(f"{message['content']}")
            else:
                st.info("**RCB:**", icon="🤖", width=100)
                st.markdown(f"```\n{message['content']}\n```")

        # Auto-scroll to bottom
        if st.session_state.chat_history:
            st.write("")  # Add space for visual separation

st.title("RCB Chat interface")
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'ChatInterface'
st.session_state.current_page = 'ChatInterface'

st.session_state.use_default_prompts = False
if 'user_input' not in st.session_state:
    st.session_state.user_input = ""
    
# Initialize chat history in session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

init_page()
init_llm_vars()
init_chat_interface_prompts()

render_chat_interface_ui()

