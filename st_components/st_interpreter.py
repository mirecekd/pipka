import streamlit as st
from src.utils.prompts import PROMPTS


def setup_interpreter():
    try:
        st.session_state['interpreter'].reset()
    except:
        pass
        
    st.session_state['interpreter'].conversation_filename = st.session_state['current_conversation']["id"]
    st.session_state['interpreter'].conversation_history = True
    st.session_state['interpreter'].messages = st.session_state.get(
        'messages',
        st.session_state.get('mensajes',[])
    )
    st.session_state['interpreter'].llm.model = f"bedrock/us.{st.session_state['model']}"
    st.session_state['interpreter'].llm.temperature = st.session_state['temperature']
    st.session_state['interpreter'].llm.max_tokens = st.session_state['max_tokens']
    st.session_state['interpreter'].llm.system_message = st.session_state['system_message']
    st.session_state['interpreter'].llm.modify_params=True 

    st.session_state['interpreter'].stream =  True
    st.session_state['interpreter'].verbose =  True

    if st.session_state['kill_umans'] == "Yes":
        st.session_state['interpreter'].auto_run = True
        st.session_state['interpreter'].system_message = PROMPTS.system_message_run
    else:
        st.session_state['interpreter'].auto_run = False
        st.session_state['interpreter'].system_message = PROMPTS.system_message_confirm

    st.session_state['interpreter'].computer.emit_images = True
