import streamlit as st

from st_components.st_conversations import init_conversations
from st_components.st_messages import chat_with_interpreter
from st_components.st_canvas import show_image_manipulator

from src.data.database import get_chats_by_conversation_id, save_conversation
from src.data.models import Conversation
import uuid

import instructor
from pydantic import BaseModel
from anthropic import AnthropicBedrock
import time
import base64
import json
from litellm import completion
import mimetypes
import imghdr
#import litellm
import os

class StepResponse(BaseModel):
    title: str
    content: str
    next_action: str
    confidence: float

def prepare_reasoning_chain():
    #print('entering prepare_reasoning_chain')
    #client = instructor.from_anthropic(AnthropicBedrock(), mode=instructor.mode.Mode.ANTHROPIC_JSON)
    client = instructor.from_anthropic(AnthropicBedrock())
    #client = instructor.from_litellm(completion)

    def make_api_call(system_prompt, messages, max_tokens, is_final_answer=False):
        #print(messages)
        #print('entering make_api_call')
        for attempt in range(3):
            try:
                #litellm.modify_params=True

                # Messages should already be in the correct format for Bedrock
                #response = client.messages.create(
                #response = client.converse(
                response = client.chat.completions.create(
                    model="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                    #model="bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0",
                    #model="bedrock/anthropic.claude-3-5-haiku-20241022-v1:0",
                    ##model="bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0",
                    #betas=["pdfs-2024-09-25", "prompt-caching-2024-07-31", "token-counting-2024-11-01", ],
                    max_tokens=max_tokens,
                    temperature=0.2,
                    top_p=0.99,
                    system=system_prompt,
                    messages=messages,
                    response_model=StepResponse
                )
                #print(response.stopReason)
                #print(response)
                return response
            except Exception as e:
                st.error(f'{str(e)}')
                print(f'{str(e)}')

                if attempt == 2:
                    return StepResponse(
                        title="Error",
                        content=f"Failed to generate {'final answer' if is_final_answer else 'step'} after 3 attempts. Error: {str(e)}",
                        next_action="final_answer",
                        confidence=0.5
                    )
                time.sleep(1)

    def generate_response(prompt, max_steps=10, max_tokens=900):
        #print('entering generate_response')
        system_prompt = """You are an AI assistant that explains your reasoning step by step, incorporating dynamic Chain of Thought (CoT), reflection, and verbal reinforcement learning. Follow these instructions:

        1. Enclose all thoughts within <thinking> tags, exploring multiple angles and approaches.
        2. Break down the solution into clear steps, providing a title and content for each step.
        3. After each step, decide if you need another step or if you're ready to give the final answer.
        4. Continuously adjust your reasoning based on intermediate results and reflections, adapting your strategy as you progress.
        5. Regularly evaluate your progress, being critical and honest about your reasoning process.
        6. Assign a quality score between 0.0 and 1.0 to guide your approach:
            - 0.8+: Continue current approach
            - 0.5-0.7: Consider minor adjustments
            - Below 0.5: Seriously consider backtracking and trying a different approach
        7. If unsure or if your score is low, backtrack and try a different approach, explaining your decision.
        8. For mathematical problems, show all work explicitly using LaTeX for formal notation and provide detailed proofs.
        9. Explore multiple solutions individually if possible, comparing approaches in your reflections.
        10. Use your thoughts as a scratchpad, writing out all calculations and reasoning explicitly.
        11. Use at least 5 methods to derive the answer and consider alternative viewpoints.
        12. Be aware of your limitations as an AI and what you can and cannot do.

        After every 3 steps, perform a detailed self-reflection on your reasoning so far, considering potential biases and alternative viewpoints."""

        messages = prompt
        
        steps = []
        step_count = 1
        total_thinking_time = 0
        
        while step_count <= max_steps:
            start_time = time.time()
            step_data = make_api_call(system_prompt, messages, max_tokens)
            end_time = time.time()
            thinking_time = end_time - start_time
            total_thinking_time += thinking_time
            
            steps.append((f"Step {step_count}: {step_data.title}", 
                            step_data.content, 
                            thinking_time, 
                            step_data.confidence))
            
            messages.append({"role": "assistant", "content": step_data.model_dump_json()})
            
            if step_data.next_action == 'final_answer' or step_count == max_steps:
                break
            elif step_data.next_action == 'reflect' or step_count % 3 == 0:
                messages.append({"role": "user", "content": "Please perform a detailed self-reflection on your reasoning so far, considering potential biases and alternative viewpoints."})
            else:
                messages.append({"role": "user", "content": "Please continue with the next step in your analysis."})
            
            step_count += 1
            yield steps, None

        messages.append({"role": "user", "content": "Please provide a comprehensive final answer based on your reasoning above, summarizing key points and addressing any uncertainties."})
        
        start_time = time.time()
        final_data = make_api_call(system_prompt, messages, 750, is_final_answer=True)
        end_time = time.time()
        thinking_time = end_time - start_time
        total_thinking_time += thinking_time
        
        steps.append(("Final Answer", final_data.content, thinking_time, final_data.confidence))

        yield steps, total_thinking_time

    return generate_response

def st_main():
        
    # try:
        if not st.session_state['chat_ready']:
            introduction()

        elif st.session_state.get('show_reasoning_chain', True):
            show_reasoning_chain()

        elif st.session_state.get('show_image_manipulator', True):
            show_image_manipulator()

        else:    

            create_or_get_current_conversation()

            render_messages()
            
            chat_with_interpreter()
            #st.write(st.session_state['interpreter'])
    
    # except Exception as e:
    #     st.error(e)

def show_reasoning_chain():
    st.title("Reasoning Chain - Extended self-reflection and analysis")
    st.info("👉 This part of PIPKA aims to create reasoning chains with extended self-reflection to improve output accuracy. It now thinks for longer periods and provides more detailed analysis 🤘")
    st.warning("If you want to reason over files, upload them first, then ask your question in the chat window. Please use English for best reasoning results")
#    with st.expander("Supported file types"):
#        st.write("Images: jpg, jpeg, png, gif, webp")
#        st.write("Documents: pdf, doc, docx, rtf, epub, odt, odp, pptx, txt, md, tex, latex")
#        st.write("Codes: py, ipyng, js, html, css, java, cs, php, c, cpp, cxx, h, hpp, rs, r, rmd, swift, go, rb, kt, kts, ts, tsx, m, scala, dart, lua, pl, pm, t, sh, bash, zsh, sql, bat, coffee")

    uploaded_files = st.file_uploader('Upload files',
                                        label_visibility='hidden',
                                        #type= ['png', 'jpg', 'jpeg','gif','webp', 'pdf', 'csv', 'doc', 'docx', 'xls', 'xlsx', 'html', 'txt', 'md'],
                                        type= ['png', 'jpg', 'jpeg','gif','webp'],
                                        accept_multiple_files=True)
    
    max_steps = st.session_state.get('max_reasoning_steps', 4)
    max_tokens = st.session_state.get('max_reasoning_tokens', 900)
    prompt = st.chat_input(placeholder="Write here your message to PIPKA Reasoning Chain...")

    if prompt:
        st.chat_message("user").write(prompt)
        
        output_container = st.container()
        
        with st.spinner('Thinking...'):
            def process_steps(steps):
                output_container.empty()
                
                with output_container:
                    with st.chat_message("assistant"):
                        for step in steps[-1:]:  
                            with st.expander(step[0], expanded=True):
                                st.write(step[1])
                                st.write(f"Confidence: {step[3]:.2f}")
                                st.write(f"Thinking time: {step[2]:.2f} seconds")

            bedrock_message = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt}
                    ]
                }
            ]

            if uploaded_files:
                for uploaded_file in uploaded_files:
                    file_bytes = uploaded_file.read()
                    encoded_file = base64.b64encode(file_bytes).decode('utf-8')
                    # Detect MIME type
                    mime_type, _ = mimetypes.guess_type(uploaded_file.name)
                    print(mime_type)
                    if mime_type and mime_type.startswith('image/'):
                        # For images, use imghdr to get the actual image format
                        img_format = imghdr.what(None, h=file_bytes)
                        if img_format == 'jpg':
                            img_format = 'jpeg'  # Adjust JPEG to JPG
                        
                        bedrock_message[0]["content"].append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": encoded_file
                            }
                        })
                    else:
                        _, file_extension = os.path.splitext(uploaded_file.name)
                        file_extension = file_extension.lower().lstrip('.')
                        print(file_extension)

                        # bedrock_message[0]["content"].append({
                        #     "type": "document",
                        #     "document": {
                        #         "name": uploaded_file.name,
                        #         "format": file_extension,
                        #         "source":{
                        #             "bytes": f"{file_bytes}"
                        #         }
                        #     }
                        # })
                        #bedrock_message[0]["content"].append(
                        #{
                        #        "type": "image_url",
                        #        "image_url": "data:{mime_type};base64,{encoded_file}"
                        #})
                        bedrock_message[0]["content"].append({
                            "type": "image_url",
                            "image_url": "data:{mime_type};base64,{encoded_file}"
                        })

            #print(json.dumps(bedrock_message, indent=2))
            #print(len(bedrock_message))

            reasoning_chain = prepare_reasoning_chain()
            for steps, total_time in reasoning_chain(bedrock_message, max_steps=max_steps, max_tokens=max_tokens):
                process_steps(steps)

            if total_time:
                st.chat_message("assistant").write(f"Total thinking time: {total_time:.2f} seconds")
                if st.button('New reasoning'):
                    st.session_state['show_reasoning_chain'] = True
                    st.session_state['chat_ready'] = True
                    st.rerun()

def create_or_get_current_conversation():
    if 'current_conversation' not in st.session_state:
        conversations, conversation_options = init_conversations()
        if conversations:
            st.session_state['current_conversation'] = conversations[0]
        else:
            conversation_id = str(uuid.uuid4())
            new_conversation = Conversation(conversation_id, st.session_state.user_id, f"Conversation {len(conversations)}")
            save_conversation(new_conversation)
            st.session_state['current_conversation'] = new_conversation
            st.session_state["messages"] = []
            st.rerun()
    else:
        st.session_state.messages = get_chats_by_conversation_id(st.session_state['current_conversation']["id"])

def render_messages():
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.chat_message(msg["role"]).markdown(f'<p>{msg["content"]}</p>', True)
        elif msg["role"] == "assistant":
            st.chat_message(msg["role"]).markdown(msg["content"])

def introduction():
    st.warning("👉 Set your AWS Bedrock model, parameters and press \'Save Changes 🚀\' buttonek 🤘")
