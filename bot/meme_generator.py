"""
Handles meme generation and manipulation.
"""
import logging
import requests
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import yaml
import os
import tempfile

logger = logging.getLogger(__name__)

class MemeGenerator:
    def __init__(self):
        self.config = self._load_config()
        self.templates = self._load_templates()
        self.font = self._load_font()
        
    def _load_config(self) -> dict:
        """Load configuration from config.yaml"""
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _load_templates(self) -> dict:
        """Load meme templates from JSON file."""
        templates_path = Path(__file__).parent.parent / self.config['paths']['templates']
        if not templates_path.exists():
            logger.warning(f"Templates file not found at {templates_path}")
            return {}
        with open(templates_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _load_font(self) -> ImageFont.FreeTypeFont:
        """Load font for meme text."""
        try:
            return ImageFont.truetype("Arial.ttf", 40)
        except IOError:
            logger.warning("Arial font not found, using default font")
            return ImageFont.load_default()
    
    def generate_meme(self, image_url: str, template_id: str = None) -> str:
        """
        Generate a meme from an image URL.
        
        Args:
            image_url: URL of the image to use
            template_id: Optional template ID to use
            
        Returns:
            Path to the generated meme image
        """
        try:
            # Download the image
            response = requests.get(image_url)
            response.raise_for_status()
            
            # Create temporary file for the downloaded image
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_file.write(response.content)
                temp_path = temp_file.name
            
            # Open the image
            with Image.open(temp_path) as img:
                # Resize if needed
                if img.size[0] > 1000 or img.size[1] > 1000:
                    img.thumbnail((1000, 1000))
                
                # Add text if template is specified
                if template_id and template_id in self.templates:
                    template = self.templates[template_id]
                    self._add_text_to_image(img, template['text'])
                
                # Save the meme
                output_path = os.path.join(
                    self.config['paths']['sample_memes'],
                    f"meme_{os.path.basename(temp_path)}"
                )
                img.save(output_path)
                
                return output_path
                
        except Exception as e:
            logger.error(f"Error generating meme: {e}")
            raise
    
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