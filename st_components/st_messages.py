import streamlit as st
import re
import speech_recognition as sr
import boto3
from streamlit_extras.stylable_container import stylable_container
from st_components.st_interpreter import setup_interpreter
from src.data.database import save_chat
from src.data.models import Chat
from src.utils.prompts import PROMPTS
from PIL import Image
from io import BytesIO
import base64
import time
from pydub import AudioSegment
import io
import asyncio

if 'is_playing' not in st.session_state:
    st.session_state.is_playing = False

polly_client = boto3.Session(region_name='eu-central-1').client('polly')

def text_to_speech(text, language):
    polly_client = boto3.client('polly', region_name='eu-central-1')
   
    language_voice_map = {
        'en-US': ('Amy', 'neural'),
        'cs-CZ': ('Jitka', 'neural'),
        'sk-SK': ('Jitka', 'neural'),  # Using Czech voice for Slovak
        'ro-RO': ('Carmen', 'standard'),
        'de-DE': ('Vicki', 'neural'),
        'fr-FR': ('Lea', 'neural'),
        'en-IN': ('Kajal', 'neural')
    }
   
    voice_id, engine = language_voice_map.get(language, ('Amy', 'standard'))
   
    try:
        response = polly_client.synthesize_speech(
            Text=text,
            OutputFormat='mp3',
            VoiceId=voice_id,
            Engine=engine
        )
       
        audio_stream = response['AudioStream'].read()
        return base64.b64encode(audio_stream).decode('utf-8')
    except Exception as e:
        print(f"Error in text_to_speech: {str(e)}")
        return None

def transcribe_audio(audio_bytes):
    recognizer = sr.Recognizer()
    with sr.AudioFile(BytesIO(audio_bytes)) as source:
        audio = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio, language=st.session_state.get('stt_language', 'cs-CZ'))
        return text
    except sr.UnknownValueError:
        return "Speech Recognition could not understand audio"
    except sr.RequestError as e:
        return f"Could not request results from Speech Recognition service; {e}"

def chat_with_interpreter():

    prompt_t = st.chat_input(placeholder="Write here your message to PIPKA", disabled=not st.session_state['chat_ready'])
    
    col1, col2 = st.columns([5, 1])
    with col2:
        with stylable_container(
        key="bottom_content",
        css_styles="""
            {
                position: fixed;
                bottom: 100px;
            }
            [data-testid="stAudioInput"] {
                opacity: 0.5;
            }
            """,
        ):
            prompt_a = st.audio_input('Record audio',disabled=False,label_visibility="hidden",key="audio_input")
    
    #prompt = ""
    if prompt_t:
        prompt = prompt_t
        setup_interpreter()
        handle_user_message(prompt)
        asyncio.run(handle_assistant_response(prompt))
    elif prompt_a:
        audio_bytes = prompt_a.read()
        prompt = transcribe_audio(audio_bytes)    
        setup_interpreter()
        handle_user_message(prompt)
        asyncio.run(handle_assistant_response(prompt))

def handle_user_message(prompt):
    with st.chat_message("user"):
        st.markdown(f'<p>{prompt}</p>', True)
        st.session_state.messages.append({"role": "user", "content": prompt})
        user_chat = Chat(
            st.session_state['current_conversation']["id"], "user", prompt)
        save_chat(user_chat)

def add_memory(prompt):
    look_back = -2*st.session_state['num_pair_messages_recall']
    memory = '\n'.join(
        [f"{i['role'].capitalize()}: {i['content']}" for i in st.session_state['messages'][look_back:]]
    ).replace('User', '\nUser')
    prompt_with_memory = f"user's request:{prompt}. --- \nBelow is the transcript of your past conversation with the user: {memory} ---\n"
    return prompt_with_memory

async def handle_assistant_response(prompt):
    st.session_state['interpreter'].llm.modify_params=True
    
    with st.chat_message("assistant"):
        full_response = ""
        message_placeholder = st.empty()
        message = add_memory(prompt)
        in_code_block = False
        current_sentence = ""

        col1, col2, col3 = st.columns([4, 1, 1])
        with col1:
            with stylable_container(
                key="stop_button_container",
                css_styles="""
                    {
                        position: fixed;
                        bottom: 120px;
                    }
                    [data-testid="stBaseButton-secondary"] {
                        opacity: 0.3;
                    }
                """
            ):
                stop_button = st.button("STOP", key="stop_button")
                if stop_button:
                    st.session_state.is_playing = False
                    st.stop()

        with col2:
            with stylable_container(
                key="audio_container",
                css_styles="""
                    {
                        position: fixed;
                        bottom: 120px;
                    }
                    [data-testid="stAudio"] {
                        opacity: 0.3;
                    }
                """
            ):
                audio_container = st.empty()

        async def play_audio(audio_data):
            with audio_container:
                st.audio(audio_data, format="audio/mp3", autoplay=True)
            audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
            await asyncio.sleep((len(audio)) / 950.0)

        if st.session_state['kill_umans'] == "Yes":
            st.session_state['interpreter'].auto_run = True
            st.session_state['interpreter'].custom_instructions = f"You have female voice. NEVER ask user for confirmation before running code, you can run it! Talk to user in {st.session_state.get('stt_language', 'en-US')} language. {st.session_state.get('cust_inst', ' ')}"
        else:
            st.session_state['interpreter'].auto_run = False
            st.session_state['interpreter'].custom_instructions = f"You have female voice. First write code do not run it and only show it to user. ALWAYS ask user for permission to run any code! Talk to user in {st.session_state.get('stt_language', 'en-US')} language. {st.session_state.get('cust_inst', ' ')}"
            
        for chunk in st.session_state['interpreter'].chat([{"role": "user", "type": "message", "content": message}], display=False, stream=True):
            full_response = format_response(chunk, full_response)
            
            if chunk['type'] == 'message' and st.session_state.talk == True:
                content = chunk.get('content', '')
                
                if '```' in content:
                    in_code_block = not in_code_block
                    if in_code_block and current_sentence.strip():
                        audio_base64 = text_to_speech(current_sentence.strip(), st.session_state.get('stt_language', 'cs'))
                        if audio_base64:
                            audio_data = base64.b64decode(audio_base64)
                            await play_audio(audio_data)
                        current_sentence = ""
                    continue

                if not in_code_block:
                    current_sentence += content
                    
                    sentences = re.split(r'(?<!\d)([.!?:])\s+', current_sentence)
                    for i in range(0, len(sentences) - 1, 2):
                        complete_sentence = sentences[i] + sentences[i+1]
                        audio_base64 = text_to_speech(complete_sentence.strip(), st.session_state.get('stt_language', 'cs'))
                        if audio_base64:
                            audio_data = base64.b64decode(audio_base64)
                            await play_audio(audio_data)
                    
                    current_sentence = sentences[-1] if len(sentences) % 2 != 0 else ""

            message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)

        if current_sentence.strip() and not in_code_block:
            audio_base64 = text_to_speech(current_sentence.strip(), st.session_state.get('stt_language', 'cs'))
            if audio_base64:
                audio_data = base64.b64decode(audio_base64)
                await play_audio(audio_data)

        st.session_state.messages.append(
            {"role": "assistant", "content": full_response})
        assistant_chat = Chat(
            st.session_state['current_conversation']["id"], "assistant", full_response)
        save_chat(assistant_chat)
        st.session_state['mensajes'] = st.session_state['interpreter'].messages

def format_response(chunk, full_response):
    if chunk['type'] == "message":
        full_response += chunk.get("content", "")
        if chunk.get('end', False):
            full_response += "\n"
            if chunk.get('token_limit_reached', False):
                full_response += "\n[Token limit reached. Click 'Continue Generation' to proceed.]\n"
    elif chunk['type'] == "code":
        if chunk.get('start', False):
            full_response += "```python\n"
        full_response += chunk.get('content', '')
        if chunk.get('end', False):
            full_response += "\n```\n"
    elif chunk['type'] == "confirmation":
        if chunk.get('start', False):
            full_response += "```python\n"
        full_response += chunk.get('content', {}).get('code', '')
        if chunk.get('end', False):
            full_response += "```\n"
    elif chunk['type'] == "console":
        if chunk.get('start', False):
            full_response += "```python\n"
        if chunk.get('format', '') == "active_line":
            console_content = chunk.get('content', '')
            if console_content is None:
                full_response += "No output available on console."
        if chunk.get('format', '') == "output":
            console_content = chunk.get('content', '')
            full_response += console_content
        if chunk.get('end', False):
            full_response += "\n```\n"
    elif chunk['type'] == "image":
        if chunk.get('start', False) or chunk.get('end', False):
            full_response += "\n"
        else:
            image_format = chunk.get('format', '')
            if image_format == 'base64.png':
                image_content = chunk.get('content', '')
                if image_content:
                    image = Image.open(BytesIO(base64.b64decode(image_content)))
                    new_image = Image.new("RGB", image.size, "white")
                    new_image.paste(image, mask=image.split()[3])
                    buffered = BytesIO()
                    new_image.save(buffered, format="PNG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    full_response += f"![Image](data:image/png;base64,{img_str})\n"
            elif image_format == 'path':
                # Přidáno: Zobrazení obrázku z lokální cesty
                image_path = chunk.get('content', '')
                if image_path and os.path.exists(image_path):
                    with open(image_path, "rb") as image_file:
                        encoded_string = base64.b64encode(image_file.read()).decode()
                        ext = os.path.splitext(image_path)[1][1:].lower()
                        full_response += f"![Image](data:image/{ext};base64,{encoded_string})\n"
    return full_response
