"""
Handles image processing and AI suggestions for the web application.
"""
import logging
from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path
import yaml
import openai
import tempfile

logger = logging.getLogger(__name__)

class MemeEngine:
    def __init__(self):
        self.config = self._load_config()
        openai.api_key = self.config['openai']['api_key']
        self.font = self._load_font()
        self.templates = self._load_templates()
        
    def _load_config(self) -> dict:
        """Load configuration from config.yaml"""
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _load_font(self) -> ImageFont.FreeTypeFont:
        """Load font for meme text."""
        try:
            return ImageFont.truetype("Arial.ttf", 40)
        except IOError:
            logger.warning("Arial font not found, using default font")
            return ImageFont.load_default()
    
    def _load_templates(self) -> dict:
        """Load meme templates from JSON file."""
        templates_path = Path(__file__).parent.parent / self.config['paths']['templates']
        if not templates_path.exists():
            logger.warning(f"Templates file not found at {templates_path}")
            return {}
        with open(templates_path, 'r') as f:
            return yaml.safe_load(f)
    
    def generate_meme(self, image_path: str, caption: str) -> str:
        """
        Generate a meme from an image with the given caption.
        
        Args:
            image_path: Path to the image file
            caption: Caption text to add to the image
            
        Returns:
            Path to the generated meme
        """
        try:
            with Image.open(image_path) as img:
                # Resize if needed
                if img.size[0] > 1000 or img.size[1] > 1000:
                    img.thumbnail((1000, 1000))
                
                # Add caption
                self._add_text_to_image(img, caption)
                
                # Save the meme
                output_path = os.path.join(
                    self.config['paths']['sample_memes'],
                    f"meme_{os.path.basename(image_path)}"
                )
                img.save(output_path)
                
                return output_path
                
        except Exception as e:
            logger.error(f"Error generating meme: {e}")
            raise
    
    def generate_caption(self, image_path: str) -> str:
        """
        Generate a witty caption for an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Generated caption
        """
        try:
            # Get image description
            description = self._describe_image(image_path)
            
            # Generate caption based on description
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
    
    def get_templates(self) -> dict:
        """Get available meme templates."""
        return self.templates
    
    def _add_text_to_image(self, image: Image.Image, text: str):
        """Add text to an image."""
        draw = ImageDraw.Draw(image)
        
        # Calculate text position (centered)
        text_bbox = draw.textbbox((0, 0), text, font=self.font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        x = (image.width - text_width) // 2
        y = image.height - text_height - 20
        
        # Add text with outline
        for offset in range(-2, 3):
            draw.text((x + offset, y), text, font=self.font, fill='black')
            draw.text((x, y + offset), text, font=self.font, fill='black')
        
        # Add main text
        draw.text((x, y), text, font=self.font, fill='white') 