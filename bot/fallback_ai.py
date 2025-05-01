"""
Handles AI-powered caption generation and image understanding.
"""
import logging
import openai
from pathlib import Path
import yaml
import os

logger = logging.getLogger(__name__)

class FallbackAI:
    def __init__(self):
        self.config = self._load_config()
        openai.api_key = self.config['openai']['api_key']
        
    def _load_config(self) -> dict:
        """Load configuration from config.yaml"""
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def generate_caption(self, image_path: str) -> str:
        """
        Generate a witty caption for an image using GPT-4.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Generated caption
        """
        try:
            # First, get image description
            description = self._describe_image(image_path)
            
            # Then generate caption based on description
            prompt = f"""
            Create a witty, meme-worthy caption for this image:
            {description}
            
            The caption should be:
            - Funny and engaging
            - No more than 100 characters
            - Relevant to the image content
            - Use internet/meme culture references if appropriate
            """
            
            response = openai.ChatCompletion.create(
                model=self.config['ai']['caption_model'],
                messages=[
                    {"role": "system", "content": "You are a meme caption generator. Create witty, engaging captions."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config['ai']['max_tokens'],
                temperature=self.config['ai']['temperature']
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating caption: {e}")
            return "Check out this meme! 😄"
    
    def _describe_image(self, image_path: str) -> str:
        """
        Generate a description of the image using GPT-4 Vision.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Image description
        """
        try:
            with open(image_path, "rb") as image_file:
                response = openai.ChatCompletion.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Describe this image in detail, focusing on the main subject, action, and any notable elements that could be used for a meme caption."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_file.read().hex()}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=300
                )
                
                return response.choices[0].message.content
                
        except Exception as e:
            logger.error(f"Error describing image: {e}")
            return "An interesting image" 