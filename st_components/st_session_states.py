import streamlit as st
import uuid
import json
import os
from interpreter import interpreter

from src.utils.prompts import PROMPTS

def init_session_states():
    if 'models' not in st.session_state:
        with open("models.json", "r") as file:
            st.session_state['models'] = json.load(file)
    if 'api_choice' not in st.session_state:
        st.session_state['api_choice'] = 'bedrock'
    if 'chat_ready' not in st.session_state:
        st.session_state['chat_ready'] = False
    if 'user_id' not in st.session_state:
        #st.session_state['user_id'] = str(uuid.uuid4())
        st.session_state['user_id'] = os.environ.get("USEREK", "nobody@trustsoft.eu")
    if 'interpreter' not in st.session_state:
        st.session_state['interpreter'] = interpreter
    if 'kill_umans' not in st.session_state:
        st.session_state['kill_umans'] = 'No'
    if 'stt_language' not in st.session_state:
        st.session_state['stt_language'] = 'en-US'
    if 'talk' not in st.session_state:
        st.session_state['talk'] = False
    if 'audio_queue' not in st.session_state:
        st.session_state['audio_queue'] = []
    if 'cust_inst' not in st.session_state:
        st.session_state['cust_inst'] = ''

    if 'token_limit_reached' not in st.session_state:
        st.session_state.token_limit_reached = False

    if 'show_reasoning_chain' not in st.session_state:
        st.session_state['show_reasoning_chain'] = False

    if 'show_image_manipulator' not in st.session_state:
        st.session_state['show_image_manipulator'] = False

    if 'system_message' not in st.session_state:
        if st.session_state['kill_umans'] == "Yes":
            st.session_state['interpreter'].auto_run = True
            st.session_state['interpreter'].system_message = PROMPTS.system_message_run
            st.session_state['system_message'] = PROMPTS.system_message_run
        else:
            st.session_state['interpreter'].auto_run = False
            st.session_state['interpreter'].system_message = PROMPTS.system_message_confirm
            st.session_state['system_message'] = PROMPTS.system_message_confirm
