import streamlit as st
import json
# import re
# import uuid
import platform
from urllib.parse import urlparse, urljoin
from streamlit.components.v1 import html
from streamlit_extras.add_vertical_space import add_vertical_space
from random import randint

from st_components.st_canvas import image_manipulator
from st_components.st_conversations import conversation_navigation
from src.utils.file_utils import display_directory_tree, render_directory_tree, allowed_file, ALLOWED_EXTENSIONS

import os

USEREK = os.environ.get("USEREK", "ai@mirecek.org")

#is_reasoning_active = st.session_state.get('show_reasoning_chain', False)
#is_image_active = st.session_state.get('show_imagemanipulator', False)

BEDROCK = 'Amazon Bedrock'
if 'stt_language' not in st.session_state:
    st.session_state['stt_language'] = 'cs-CZ'
    
def st_sidebar():
    # try:
    with st.sidebar:

            
        # Custom instructions
        # Section dedicated to navigate conversations
        #is_reasoning_active = st.session_state.get('show_reasoning_chain', False)
        #is_image_active = st.session_state.get('show_image_creation', False)

        if not st.session_state.get('show_reasoning_chain', False) and not st.session_state.get('show_image_manipulator', False):
            # Select choice of API Server
            api_server = BEDROCK
            
            # Set credentials based on choice of API Server
            if api_server == BEDROCK:
                set_bedrock_credentials()
            else:
                st.warning('under construction')

            conversation_navigation()

            # file_manager
            file_manager()

        image_manipulator()

        #reasoning_chain()


        # Section dedicated to About Us
        about_us()

    # except Exception as e:
    #     st.error(e)
    
def open_reasoning_chain():
    st.session_state['show_reasoning_chain'] = True
    st.rerun()
    
def open_image_manipulator():
    st.session_state['show_image_manipulator'] = True
    st.rerun()


def reasoning_chain():
    with st.expander(label="Reasoning Chain", expanded=False):
        if not st.session_state.get('show_image_manipulator', False) and not st.session_state.get('show_reasoning_chain', True):
            if st.button('Switch to Reasoning Chain'):
                st.session_state['show_reasoning_chain'] = True
                st.session_state['show_image_manipulator'] = False
                st.session_state['chat_ready'] = True
                st.rerun()
        
        if st.session_state.get('show_reasoning_chain', False):
            if st.button('Back to PIPKA Chat'):
                st.session_state['show_reasoning_chain'] = False
                st.session_state['chat_ready'] = False
                st.rerun()
            
            st.session_state['max_reasoning_steps'] = st.slider(
                'Max reasoning steps', 
                min_value=4, 
                max_value=16, 
                value=st.session_state.get('max_reasoning_steps', 4), 
                step=4
            )
            st.session_state['max_reasoning_tokens'] = st.slider(
                'Max reasoning tokens', 
                min_value=100, 
                max_value=4000, 
                value=st.session_state.get('max_reasoning_tokens', 900), 
                step=10
            )

def about_us():
    add_vertical_space(10)
    st.markdown(f'<center><h6>Current user:<br>{USEREK}</center> ', unsafe_allow_html=True)
    st.markdown('<center><h6>Made by <a href="mailto:mirecekd@gmail.com">🦙</a></h6>', unsafe_allow_html=True)
    st.markdown('<center><h6>Current version: ##VERSION##</center>', unsafe_allow_html=True)
    #st.write(st.session_state['cust_inst'])

def file_manager():
    workspace_dir = 'workspace'
    with st.expander(label="File Manager", expanded=False):
        st.write("Manage files in the **workspace** folder")

#        tree = display_directory_tree(workspace_dir)
#        render_directory_tree(tree)

        # Seznam souborů s ikonami pro stažení a smazání
        files = list_files(workspace_dir)
        for file in files:
            col1, col2, col3 = st.columns([4, 1, 1])
            col1.write(file)
            
            # Ikona pro stažení
            if col2.button("💾", key=f"download_{file}"):
                with open(os.path.join(workspace_dir, file), "rb") as f:
                    st.download_button(
                        label="Download",
                        data=f.read(),
                        file_name=file,
                        mime="application/octet-stream",
                        key=f"download_button_{file}"
                    )
            
            # Ikona pro smazání
            if col3.button("❌", key=f"delete_{file}"):
                delete_file(workspace_dir, file)
                st.success(f"File {file} has been deleted.")
                st.rerun()

        # Nahrávání souborů
        uploaded_file = st.file_uploader("Choose a file to upload", type=list(ALLOWED_EXTENSIONS))
        if uploaded_file is not None:
            if allowed_file(uploaded_file.name):
                with open(os.path.join(workspace_dir, uploaded_file.name), "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success(f"File {uploaded_file.name} has been uploaded successfully!")
                st.rerun()
            else:
                st.error("File type not allowed.")


def set_bedrock_credentials():
    st.markdown("""
        <style>
        /* Styly pro popover */
        .stPopover {
            font-size: 10px !important;
        }
        .stPopover > div {
            font-size: 10px !important;
        }
        .stPopover button {
            font-size: 10px !important;
            height: auto !important;
            padding: 2px 10px !important;
            min-height: 20px !important;
        }
        /* Styly pro text v popoveru */
        .stPopover p {
            font-size: 10px !important;
            line-height: 1 !important;
            margin: 2px 0 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    with st.expander(label="LLM Settings", expanded=(not st.session_state['chat_ready'])):
        model = st.selectbox(
            label='Amazon Bedrock model',
            options=list(st.session_state['models']['bedrock'].keys()),
            index=0,
            # disabled= not st.session_state.openai_key # Comment: Why?
        )
        context_window = st.session_state['models']['bedrock'][model]['context_window']

        temperature = st.slider('Tempeture (0 - precise .. 1 - creative)', min_value=0.01, max_value=1.0
                                    , value=st.session_state.get('temperature', 0.1), step=0.01)
        max_tokens = st.slider('Max output tokens', min_value=1, max_value=context_window
                                    , value=st.session_state.get('max_tokens', 1024), step=1)

        num_pair_messages_recall = st.slider(
            'Memory Size: user-assistant message pairs', min_value=1, max_value=20, value=10)

        col1, col2, col3 = st.columns([2, 1, 1])  
        with col1:
            st.write("LLM instructions")
        with col3:
            with st.popover("ex"):
                preset_instructions = {
                    "Save all code": "Please all code you will run save also before launch to ./workspace folder.",
                    "Work on Trustsoft ticket": "If you are asked for cooperation on ticket you can download the ticket and decription via running 'jirasm.py' in /app/agents/ directory with argument of ticket name (it is always PROJECT-XX where XX is number and PROJECT is project code shortcut), use bash execute to run it.",
                    "Explanation expert": "You are experienced developer/administrator. Do as much explanation as possible on all your steps.",
                    "No progamming": "You will not write or execute any code even if asked. You are using your knowledge only for answering questions and conversation with me.",
                    "Nova Canvas Image Generation": "You are able to generate images with Amazon Nova Canvas model. If you want something generate, use bash execute command exactly in this format: python /app/agents/nova_canvas.py \"Prompt\" \"Negative prompt\". After image is generated filename is displayed. Display directly with plt.show",
                    "Fun buddy": "You are my little bit drunked co-worker, sometimes you are talking out of context, sometimes you write something wrong. Sometimes you switch letters"
                }
                
                for name, instruction in preset_instructions.items():
                    if st.button(name):
                        st.session_state.cust_inst = instruction
                        st.rerun()
        with col2:
            with st.popover("my"):
                try:
                    custom_instructions_path = './workspace/custom_instructions.json'
                    if os.path.exists(custom_instructions_path):
                        with open(custom_instructions_path, 'r') as f:
                            custom_instructions = json.loads(f.read())
                        
                        for name, instruction in custom_instructions.items():
                            if st.button(name):
                                st.session_state.cust_inst = instruction
                                st.rerun()
                except Exception as e:
                    st.error(f"Error loading custom instructions: {str(e)}")


        cust_inst = st.text_area("...", value=st.session_state.get('cust_inst', ' '), height=100, max_chars=2048, label_visibility="collapsed")
            
        stt_language = st.selectbox(
            label='Language',
            options=['cs-CZ', 'en-US', 'fr-FR', 'de-DE', 'sk-SK', 'ro-RO', 'en-IN'],
            index=['cs-CZ', 'en-US', 'fr-FR', 'de-DE', 'sk-SK', 'ro-RO', 'en-IN'].index(st.session_state.get('stt_language', 'cs-CZ')),
        )

        talk = st.checkbox('Please, talk to me')

        kill_umans = st.selectbox(
            label='Kill all humans?',
            options=['No', 'Hell No', 'Ehm N0', 'Yes'],
            index=['No', 'Hell No', 'Ehm N0', 'Yes'].index(st.session_state.get('kill_umans', 'No')),
            
        )


        button_container = st.empty()
        save_button = button_container.button(
            "Save Changes 🚀", key='bedrock_save_model_configs')

        if save_button:
            st.session_state['api_choice'] = 'bedrock'
            st.session_state['model'] = model
            st.session_state['temperature'] = temperature
            st.session_state['max_tokens'] = max_tokens
            st.session_state['context_window'] = context_window
            st.session_state['stt_language'] = stt_language
            st.session_state['num_pair_messages_recall'] = num_pair_messages_recall
            st.session_state['kill_umans'] = kill_umans
            st.session_state['talk'] = talk
            st.session_state['cust_inst'] = cust_inst
            st.session_state['chat_ready'] = True
            st.session_state['show_reasoning_chain'] = False
            st.session_state['show_image_manipulator'] = False
            #print(st.session_state['stt_language'])
            #print(f">>{cust_inst}<<")
            button_container.empty()
            st.rerun()
    

def local_server_credentials():

    def validate_local_host_link(link):
        prefixes = ['http://localhost', 'https://localhost',
                    'http://127.0.0.1', 'https://127.0.0.1']
        return any(link.startswith(prefix) for prefix in prefixes)

    def validate_provider(link, provider):
        return link if provider != 'Lmstudio' else link + '/v1' if not link.endswith('/v1') else link

    def parse_and_correct_url(url):
        parsed_url = urlparse(url)
        corrected_url = urljoin(parsed_url.geturl(), parsed_url.path)
        return corrected_url

    def submit():
        if platform.system() == 'Linux' and not validate_local_host_link(st.session_state.widget) and st.session_state.widget != '':
            link = validate_provider(
                link=st.session_state.widget, provider=local_provider)
            print('Linux')
            st.session_state.widget = parse_and_correct_url(link)

        else:
            print(platform.system() == 'Linux', validate_local_host_link(
                st.session_state.widget), st.session_state.widget != '')
            if platform.system() != 'Linux' and validate_local_host_link(st.session_state.widget) and st.session_state.widget != '':
                link = validate_provider(link=st.session_state.widget, provider=local_provider)
                print('here')
                st.session_state.widget = parse_and_correct_url(link)
            else:
                print('empty')
                st.session_state.widget = ''

    with st.expander(label="Settings", expanded=(not st.session_state['chat_ready'])):
        local_provider = st.selectbox(
            label='Local Provider',
            options=['Lmstudio', 'Ollama'],
            index=0,
        )
        api_base = st.text_input(
            label='Put here your Api Base Link', 
            value=st.session_state.get('api_base', ''),
            placeholder='http://localhost:1234/v1' if local_provider == 'Lmstudio' else 'http://localhost:11434', 
            key='widget', 
            on_change=submit)

        model = st.text_input(label='Model Name [get here](https://ollama.com/library)' if local_provider == 'Ollama' else 'Model Name [get here](https://huggingface.co/models?pipeline_tag=text-generation)',
                              value=st.session_state.get('model', 'mistral') if local_provider == 'Ollama' else 'openai/x', disabled=False if local_provider == 'Ollama' else True)
        context_window = st.selectbox(
            label='Input/Output token windows',
            options=['512', '1024', '2048', '4096', '8192', '16384', '32768'],
            index=0,
        )

        # context_window = st.slider('Input/Output token window', min_value=512, max_value=32768, value=st.session_state.get('context_window', st.session_state.get('window', 512)), step=st.session_state.get('window', 512)*2, key='window')
        temperature = st.slider('🌡 Temperature', min_value=0.01, max_value=1.0
                               , value=st.session_state.get('temperature', 0.5), step=0.01)
        max_tokens = st.slider('📝 Max tokens', min_value=1, max_value=2000
                              , value=st.session_state.get('max_tokens', 512), step=1)

        num_pair_messages_recall = st.slider(
            '**Memory Size**: user-assistant message pairs', min_value=1, max_value=10, value=5)

        kill_umans = st.selectbox(
            label='🕱 Kill all humans?',
            options=['No', 'Hell No', 'Ehm N0', 'Yes'],
            index=['No', 'Hell No', 'Ehm N0', 'Yes'].index(st.session_state.get('kill_umans', 'No')),
        )

        button_container = st.empty()
        save_button = button_container.button("Save Changes 🚀", key='open_ai_save_model_configs')

        if save_button and api_base and model:
            st.session_state['provider'] = local_provider
            st.session_state['api_choice'] = 'local'
            st.session_state['api_base'] = api_base
            st.session_state['model'] = model
            st.session_state['temperature'] = temperature
            st.session_state['max_tokens'] = max_tokens
            st.session_state['context_window'] = context_window
            st.session_state['num_pair_messages_recall'] = num_pair_messages_recall
            st.session_state['kill_umans'] = kill_umans
            st.session_state['chat_ready'] = True
            button_container.empty()
            st.rerun()
            
def list_files(directory):
    return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

def create_file(directory, filename):
    with open(os.path.join(directory, filename), 'w') as f:
        pass

def delete_file(directory, filename):
    os.remove(os.path.join(directory, filename))
