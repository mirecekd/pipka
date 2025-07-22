import streamlit as st
from PIL import Image
import io
from random import randint
import shutil

from typing import Dict, Any
import json
import logging
from pathlib import Path
import boto3

from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from boto3.session import Session

from streamlit_extras.stylable_container import stylable_container

from  datetime import datetime

import base64
import io
import os

from PIL import Image

def save_base64_image(base64_image, output_directory, base_name="image", suffix="_1"):
    """
    Saves a base64 encoded image to a specified output directory with a timestamp and a suffix.

    Args:
        base64_image (str): The base64 encoded image string.
        output_directory (str): The directory where the image will be saved.
        suffix (str, optional): A suffix to be added to the filename. Defaults to "_1".
    Returns:
        PIL.Image.Image: The Pillow Image object representing the saved image.
    """
    image_bytes = base64.b64decode(base64_image)
    image = Image.open(io.BytesIO(image_bytes))
    save_image(image, output_directory, base_name, suffix)
    return image


def save_image(image, output_directory, base_name="image", suffix="_1"):
    """
    Saves a Pillow Image object to a specified output directory with a timestamp and a suffix.

    Args:
        image (PIL.Image.Image): The Pillow Image object to be saved.
        output_directory (str): The directory where the image will be saved.
        suffix (str, optional): A suffix to be added to the filename. Defaults to "_1".
    Returns:
        None
    """
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    file_name = f"{base_name}{suffix}.png"
    file_path = os.path.join(output_directory, file_name)
    image.save(file_path)
    #print(f"Generated file: {file_path}")
    
def save_base64_images(base64_images, output_directory, base_name="image"):
    """
    Saves a list of base64 encoded images to a specified output directory.

    Args:
        base64_images (list): A list of base64 encoded image strings.
        output_directory (str): The directory where the images will be saved.
    Returns:
        An array of Pillow Image objects representing the saved images.
    """
    images = []
    for i, base64_image in enumerate(base64_images):
        image = save_base64_image(
            base64_image, output_directory, base_name=base_name, suffix=f"_{i+1}"
        )
        images.append(image)

    return images

logger = logging.getLogger(__name__)
# boto has a default timeout of 60 seconds which can be
# surpassed when generating multiple images.
config = Config(read_timeout=300)


class ImageGenerationError(Exception):
    """Custom exception for image generation errors.

    This exception is raised when any error occurs during the image generation process,
    including AWS service errors, file I/O errors, or unexpected runtime errors.

    Args:
        message (str): The error message
    """

    pass


class BedrockImageGenerator:
    """A class to handle image generation using AWS Bedrock service.

    This class provides functionality to generate images using AWS Bedrock's image generation
    models. It handles the AWS client initialization, API calls, and response processing.

    Attributes:
        DEFAULT_MODEL_ID (str): The default AWS Bedrock model ID for image generation.
        DEFAULT_REGION (str): The default AWS region for the Bedrock service.
        region_name (str): The AWS region being used.
        endpoint_url (Optional[str]): Custom endpoint URL for the AWS service, if any.
        output_directory (Path): Directory path where generated files will be saved.
        bedrock_client (boto3.client): The initialized AWS Bedrock client.
    """

    DEFAULT_MODEL_ID: str = "amazon.nova-canvas-v1:0"
    DEFAULT_REGION: str = "us-east-1"

    def __init__(
        self,
        region_name: str = DEFAULT_REGION,
        output_directory: str = "./output",
    ) -> None:
        """Initialize the BedrockImageGenerator.

        Args:
            region_name (str): AWS region name. Defaults to DEFAULT_REGION.
            endpoint_url (Optional[str]): Optional custom endpoint URL for the AWS service.
            output_directory (str): Directory path for saving output files. Defaults to "./output".

        Raises:
            ImageGenerationError: If the Bedrock client initialization fails.
        """
        self.region_name = region_name
        self.output_directory = Path(output_directory)
        self.bedrock_client = self._initialize_bedrock_client()

    def _initialize_bedrock_client(self) -> boto3.client:
        """Initialize and return the AWS Bedrock client.

        Returns:
            boto3.client: Initialized Bedrock client.

        Raises:
            ImageGenerationError: If client initialization fails due to AWS service errors.
        """
        try:
            session = Session()
            return session.client(
                service_name="bedrock-runtime",
                region_name=self.region_name,
                config=config
            )
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to initialize Bedrock client: {str(e)}")
            raise ImageGenerationError("Failed to initialize AWS Bedrock client") from e

    def _save_json_to_file(self, data: Dict[str, Any], filename: str) -> None:
        """Save JSON data to a file in the output directory.

        Args:
            data (Dict[str, Any]): Dictionary containing JSON-serializable data.
            filename (str): Name of the file to save the data to.

        Raises:
            ImageGenerationError: If saving the file fails.
        """
        try:
            filepath = self.output_directory / filename
            with filepath.open("w") as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save {filename}: {str(e)}")
            raise ImageGenerationError(f"Failed to save {filename}") from e

    def _get_image_count(self, inference_params: Dict[str, Any]) -> int:
        """Extract the number of images to generate from the inference parameters.

        Args:
            inference_params (Dict[str, Any]): Dictionary containing image generation parameters.

        Returns:
            int: Number of images to generate, defaults to 1 if not specified.
        """
        return inference_params.get("imageGenerationConfig", {}).get(
            "numberOfImages", 1
        )

    def _log_generation_details(
        self, inference_params: Dict[str, Any], model_id: str
    ) -> None:
        """Log details about the image generation request for monitoring purposes.

        Args:
            inference_params (Dict[str, Any]): Dictionary containing image generation parameters.
            model_id (str): The ID of the model being used for generation.
        """
        image_count = self._get_image_count(inference_params)
        logger.info(
            f"Generating {image_count} image(s) with {model_id} in region {self.region_name}"
        )

        seed = inference_params.get("imageGenerationConfig", {}).get("seed")
        if seed is not None:
            logger.info(f"Using seed: {seed}")

    def generate_images(
        self,
        inference_params: Dict[str, Any],
        model_id: str = DEFAULT_MODEL_ID,
    ) -> Dict[str, Any]:
        """Generate images using AWS Bedrock's image generation models.

        This method handles the entire image generation process, including:
        - Creating the output directory if it doesn't exist
        - Logging generation details
        - Making the API call to AWS Bedrock
        - Saving request and response data
        - Error handling and logging

        Args:
            inference_params (Dict[str, Any]): Dictionary containing the parameters for image generation.
                Must include required fields as per AWS Bedrock's API specifications.
            model_id (str): The model ID to use for generation. Defaults to DEFAULT_MODEL_ID.

        Returns:
            Dict[str, Any]: Dictionary containing the complete response from the model, including
                generated images and any additional metadata.

        Raises:
            ImageGenerationError: If any error occurs during the generation process,
                including AWS service errors or file I/O errors.
        """
        try:
            # Create output directory if it doesn't exist
            self.output_directory.mkdir(parents=True, exist_ok=True)

            self._log_generation_details(inference_params, model_id)

            # Prepare and save request
            body_json = json.dumps(inference_params, indent=2)
            self._save_json_to_file(json.loads(body_json), "request.json")

            # Make the API call
            response = self.bedrock_client.invoke_model(
                body=body_json,
                modelId=model_id,
                accept="application/json",
                contentType="application/json",
            )

            # Save response metadata
            self._save_json_to_file(
                response.get("ResponseMetadata", {}), "response_metadata.json"
            )

            # Process and save response body
            response_body = json.loads(response.get("body").read())
            self._save_json_to_file(response_body, "response_body.json")

            # Log request ID for tracking
            request_id = response.get("ResponseMetadata", {}).get("RequestId")
            if request_id:
                logger.info(f"Request ID: {request_id}")

            # Check for API errors
            if error_msg := response_body.get("error"):
                if error_msg == "":
                    logger.warning(
                        "Response included empty string error (possible API bug)"
                    )
                else:
                    logger.warning(f"Error in response: {error_msg}")

            return response_body

        except (BotoCoreError, ClientError) as e:
            logger.error(f"AWS service error: {str(e)}")
            if hasattr(e, "response"):
                self._save_json_to_file(e.response, "error_response.json")
            raise ImageGenerationError(
                "Failed to generate images: AWS service error"
            ) from e

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise ImageGenerationError(
                "Unexpected error during image generation"
            ) from e

def image_manipulator():    
    with st.expander(label="Image Manipulator", expanded=False):
        if not st.session_state.get('show_reasoning_chain', False) and not st.session_state.get('show_image_manipulator', True):
            if st.button('Switch to Image Manipulator'):
                st.session_state['show_image_manipulator'] = True
                st.session_state['show_reasoning_chain'] = False
                st.session_state['chat_ready'] = True
                st.rerun()
        
        if st.session_state.get('show_image_manipulator', False):
            if st.button('Back to PIPKA Chat'):
                st.session_state['show_image_manipulator'] = False
                st.session_state['chat_ready'] = False
                st.session_state['current_directory'] = False
                st.rerun()
            
            rs = randint(0, 858993459)
            st.session_state['img_random_seed'] = st.slider(
                'Random seed', 
                min_value=1, 
                max_value=858993459, 
                value=st.session_state.get('img_random_seed', rs), 
                step=1
            )
            
            st.session_state['img_cfgscale'] = st.slider(
                'cfgScale', 
                min_value=1.1, 
                max_value=10.0,
                value=st.session_state.get('img_cfgscale', 6.5), 
                step=0.1
            )


            # Get default or previously set values
            default_width = st.session_state.get('img_width', 1024)
            default_height = st.session_state.get('img_height', 1024)
            
            # Add sliders for width and height
            width = st.slider("Image Width", min_value=320, max_value=4096, value=default_width, step=16)
            height = st.slider("Image Height", min_value=320, max_value=4096, value=default_height, step=16)


            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                with stylable_container(
                    key="small_button_container_1",
                    css_styles="""
                        button {
                            padding: 1px 1px !important;
                            height: 0 !important;
                        }
                    """,
                ):
                    if st.button("1024x768", key="small_button_container1"):
                        st.session_state['img_width'] = 1024
                        st.session_state['img_height'] = 768
                        st.rerun()
            with col2:
                with stylable_container(
                    key="small_button_container_2",
                    css_styles="""
                        button {
                            padding: 1px 1px !important;
                            height: 0 !important;
                        }
                    """,
                ):
                    if st.button("HD", key="small_button_container2"):
                        st.session_state['img_width'] = 1280
                        st.session_state['img_height'] = 720
                        st.rerun()
            with col3:
                with stylable_container(
                    key="small_button_container_3",
                    css_styles="""
                        button {
                            padding: 1px 1px !important;
                            height: 0 !important;
                        }
                    """,
                ):
                    if st.button("FHD", key="small_button_container3"):
                        st.session_state['img_width'] = 1920
                        st.session_state['img_height'] = 1072
                        st.rerun()

            aspect_ratio = max(width, height) / min(width, height)
            total_pixels = width * height
            
            if (320 <= width <= 4096 and 320 <= height <= 4096 and
                width % 16 == 0 and height % 16 == 0 and
                1/4 <= aspect_ratio <= 4 and
                total_pixels < 4194304):
                st.success(f"Valid image size: {width}x{height}")
                st.session_state['img_width'] = width
                st.session_state['img_height'] = height
            else:
                st.error("Invalid image size. Please adjust the dimensions.")
                if width % 16 != 0 or height % 16 != 0:
                    st.warning("Both width and height must be divisible by 16.")
                if aspect_ratio < 1/4 or aspect_ratio > 4:
                    st.warning("Aspect ratio must be between 1:4 and 4:1.")
                if total_pixels >= 4194304:
                    st.warning("Total pixel count must be less than 4,194,304.")

            st.write("**Previously generated images**")
        
            if 'current_directory' not in st.session_state:
                st.session_state['current_directory'] = None

            items = [item for item in os.listdir("workspace") if os.path.isdir(os.path.join("workspace", item)) and item.startswith("nova_canvas_")]
            #print(items)
            items.sort(key=lambda x: x.split('_'), reverse=True)
            #print(items)
            for item in items:
                item_path = os.path.join("workspace", item)
                shortened_name = item[len("nova_canvas_"):]
                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(shortened_name):
                        st.session_state['current_directory'] = item_path
                        st.rerun()
                with col2:
                    if st.button(f"❌", key=f"confirm_delete_{item}"):
                        shutil.rmtree(item_path)
                        st.success(f"Deleted {shortened_name}")
                        st.rerun()
        # Uložení relevantních dat do session state



def show_image_manipulator():
    st.title("Image Manipulator - Do whatever Nova Canvas can do")
    st.info("👉 This part of PIPKA aims to create and manipulate with images together with Nova Canvas model 🤘")
    st.warning("If you want to manipulate with specific file, please upload it first, then type prompt and/or chose what to do with image. Please use English for best results")

    uploaded_file = st.file_uploader('Upload files',
        label_visibility='hidden',
        type= ['png', 'jpg', 'jpeg'],
        accept_multiple_files=False)


    # event = st_file_browser("workspace",
    #     show_choose_file=True,
    #     show_choose_folder=True,
    #     show_delete_file=True,
    #     show_download_file=True,
    #     show_new_folder=True,
    #     show_rename_file=True,
    #     show_rename_folder=True,
    #     use_cache=False)
    # st.write(event)

    if uploaded_file is not None:
        # Read the file
        image_bytes = uploaded_file.getvalue()
        
        # Open the image using PIL
        image = Image.open(io.BytesIO(image_bytes))
        
        # Get the image dimensions
        width, height = image.size
        
        # Adjust dimensions to be divisible by 16
        width = (width // 16) * 16
        height = (height // 16) * 16
        
        # Ensure dimensions are within allowed range
        width = max(320, min(width, 4096))
        height = max(320, min(height, 4096))
        
        # Update session state
        st.session_state['img_width'] = width
        st.session_state['img_height'] = height
        
        # Display the image
        st.image(image, caption='Uploaded Image', use_container_width=True)

        source_image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Background removal"):
                inference_params = {
                    "taskType": "BACKGROUND_REMOVAL",
                    "backgroundRemovalParams": {
                        "image": source_image_base64,
                    },
                }
                generation_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                output_directory = f"workspace/nova_canvas_{generation_id}"
                generator = BedrockImageGenerator(output_directory=output_directory)
                with st.spinner('Generating image...'):
                    response = generator.generate_images(inference_params)
                if "images" in response:
                    # Save and display the generated image
                    image_data = base64.b64decode(response["images"][0])
                    image = Image.open(io.BytesIO(image_data))
                    
                    # Display the generated image
                    st.image(image, caption='Generated Image', use_container_width=True)
                    
                    # Save the image
                    save_base64_images(response["images"], output_directory, "image")
                    st.success(f"Image saved in {output_directory}")
                else:
                    st.error("Failed to generate image. Please try again.")
                if st.button("Clear Screen"):
                        st.session_state['current_directory'] = False
                        st.rerun()
        with col2:
            col2_prompt = st.text_area("...", max_chars=512, label_visibility="collapsed")
            if st.button("Manipulate by prompt"):
                
                inference_params = {
                    "taskType": "INPAINTING",
                    "inPaintingParams": {
                        "image": source_image_base64,
                        "maskPrompt": col2_prompt
                    },
                    "imageGenerationConfig": {
                        "numberOfImages": 1,
                        "quality": "standard",
                        "cfgScale": st.session_state.get('img_cfgscale', 6.5),
                        "seed": st.session_state.get('img_random_seed', randint(0, 858993459)),
                    },

                }
                generation_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                output_directory = f"workspace/nova_canvas_{generation_id}"
                generator = BedrockImageGenerator(output_directory=output_directory)
                with st.spinner('Generating image...'):
                    response = generator.generate_images(inference_params)
                if "images" in response:
                    # Save and display the generated image
                    image_data = base64.b64decode(response["images"][0])
                    image = Image.open(io.BytesIO(image_data))
                    
                    # Display the generated image
                    st.image(image, caption='Generated Image', use_container_width=True)
                    
                    # Save the image
                    save_base64_images(response["images"], output_directory, "image")
                    st.success(f"Image saved in {output_directory}")
                else:
                    st.error("Failed to generate image. Please try again.")
                if st.button("Clear Screen"):
                        st.session_state['current_directory'] = False
                        st.rerun()

        # Force a rerun to update the sliders in the sidebar
        #st.rerun()

    user_input = st.chat_input("Enter your prompt for image generation. If you want to add negative prompt use at the end NEGATIVE: followed by negative prompt",max_chars=1024)    
    if user_input:
        if "NEGATIVE:" in user_input:
            prompt, negative_prompt = user_input.split("NEGATIVE:", 1)
            prompt = prompt.strip()
            negative_prompt = negative_prompt.strip()
        else:
            prompt = user_input.strip()
            negative_prompt = "."

        #st.write(f"User Input: {user_input}")
        st.write(f"Prompt: {prompt}")
        st.write(f"Negative prompt: {negative_prompt}")
        
        # Configure the inference parameters
        inference_params = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": prompt,
                "negativeText": negative_prompt,  # You can add negative prompts if needed
            },
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "quality": "standard",
                "width": st.session_state.get('img_width', 1024),
                "height": st.session_state.get('img_height', 1024),
                "cfgScale": st.session_state.get('img_cfgscale', 6.5),
                "seed": st.session_state.get('img_random_seed', randint(0, 858993459)),
            },
        }

        # Define an output directory with a unique name
        generation_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_directory = f"workspace/nova_canvas_{generation_id}"

        # Create the generator
        generator = BedrockImageGenerator(output_directory=output_directory)

        # Generate the image(s)
        with st.spinner('Generating image...'):
            response = generator.generate_images(inference_params)

        if "images" in response:
            # Save and display the generated image
            image_data = base64.b64decode(response["images"][0])
            image = Image.open(io.BytesIO(image_data))
            
            # Display the generated image
            st.image(image, caption='Generated Image', use_container_width=True)
            
            # Save the image
            save_base64_images(response["images"], output_directory, "image")
            st.success(f"Image saved in {output_directory}")
        else:
            st.error("Failed to generate image. Please try again.")
        if st.button("Clear Screen"):
                st.session_state['current_directory'] = False
                st.rerun()
    #st.write('Show only workspace files')
    #eventA = st_file_browser("workspace", key='A')
    #eventC = st_file_browser("workspace", artifacts_site="http://localhost:1024", show_choose_file=True, show_download_file=True, glob_patterns=('workspace/nova_canvas_*',), key='C')
    #st.write(eventA)
    #st.write(eventC)
    if st.session_state.get('current_directory'):
        current_dir = st.session_state['current_directory']
        image_path = os.path.join(current_dir, "image_1.png")
        request_path = os.path.join(current_dir, "request.json")
    
        if os.path.exists(image_path):
            image = Image.open(image_path)
            st.image(image, caption='Generated Image', use_container_width=True)

        if os.path.exists(request_path):
            with open(request_path, 'r') as file:
                request_data = json.load(file)
            st.json(request_data,expanded=False)
                        
            # Uložení relevantních dat do session state
            st.session_state['img_width'] = request_data.get('imageGenerationConfig', {}).get('width')
            st.session_state['img_height'] = request_data.get('imageGenerationConfig', {}).get('height')
            st.session_state['img_cfgscale'] = request_data.get('imageGenerationConfig', {}).get('cfgScale')
            st.session_state['img_random_seed'] = request_data.get('imageGenerationConfig', {}).get('seed')
            #st.rerun()

            if st.button("Clear Screen"):
                st.session_state['current_directory'] = False
                st.rerun()
