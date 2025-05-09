"""
MemeService module for text detection and meme generation.
"""
import logging
import cv2
import numpy as np
import easyocr
from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path
import sys
import shutil

logger = logging.getLogger(__name__)

class MemeService:
    """Service for meme generation with text detection and manipulation."""
    
    def __init__(self):
        """Initialize the MemeService."""
        # Initialize OCR reader (lazily to save memory)
        self._ocr_reader = None
        self.outline_thickness = 3
    
    @property
    def ocr_reader(self):
        """Lazy initialization of OCR reader."""
        if self._ocr_reader is None:
            self._ocr_reader = easyocr.Reader(['en'])
        return self._ocr_reader
    
    def calculate_optimal_font_size(self, text, image_width, max_height, default_size=40, min_size=20, max_size=80):
        """
        Calculate optimal font size based on actual text width requirements.
        Target: Make text occupy approximately 80% of available width.
        
        Args:
            text: Text to render
            image_width: Width of the image in pixels
            max_height: Maximum height available for text
            default_size: Default font size if no text is provided
            min_size: Minimum font size
            max_size: Maximum font size
            
        Returns:
            Optimal font size for the given text and image dimensions
        """
        if not text:
            return default_size
        
        # Average character width factor (approximate ratio of font size to character width)
        # This varies by font, but a reasonable estimate is 0.6 for most fonts
        char_width_factor = 0.6
        
        # Target is 80% of image width
        target_width = image_width * 0.8
        
        # Calculate initial font size based on target width
        text_length = len(text)
        
        # Estimate: total text width = font_size * char_width_factor * text_length
        # Therefore: font_size = target_width / (char_width_factor * text_length)
        estimated_size = int(target_width / (char_width_factor * text_length))
        
        # Apply bounds
        size = max(min_size, min(estimated_size, max_size))
        
        # Fine-tune based on text length
        if text_length <= 5:
            # Very short text can be bigger
            size = min(int(size * 1.2), max_size)
        elif text_length <= 10:
            # Short text gets slight boost
            size = min(int(size * 1.1), max_size)
        elif text_length >= 50:
            # Very long text needs to be smaller
            size = max(int(size * 0.9), min_size)
        
        # Final safety check
        return max(min_size, min(size, max_size))
    
    def detect_text(self, image_path):
        """
        Detect text in an image using EasyOCR.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple of (detected_text_with_bounding_boxes, image)
        """
        # Read image
        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"Failed to read image at {image_path}")
            raise ValueError(f"Could not read image at {image_path}")
        
        # Detect text and return bounding boxes
        results = self.ocr_reader.readtext(image_path)
        
        # Filter results with good confidence
        filtered_results = [r for r in results if r[2] > 0.5]
        
        logger.info(f"Detected {len(filtered_results)} text regions in image {image_path}")
        
        return filtered_results, image
    
    def get_font(self, size, font_path=None):
        """
        Get a font object with the specified size.
        
        Args:
            size: Font size
            font_path: Optional path to a custom font file
            
        Returns:
            PIL.ImageFont object
        """
        if font_path:
            try:
                return ImageFont.truetype(font_path, size)
            except IOError:
                logger.warning(f"Custom font at {font_path} not found, trying system fonts")
        
        try:
            return ImageFont.truetype("Impact.ttf", size)
        except IOError:
            try:
                return ImageFont.truetype("Arial.ttf", size)
            except IOError:
                logger.warning("Standard fonts not found, using default font")
                try:
                    return ImageFont.load_default().font_variant(size=size)
                except:
                    return ImageFont.load_default()
    
    def generate_meme(self, image_path, text_list=None, output_path=None, 
                       remove_existing_text=True, text_color=(0, 0, 0), outline_color=(255, 255, 255), font_path=None):
        """
        Generate a meme by adding text to an image based on detected text regions.
        
        Args:
            image_path: Path to the input image
            text_list: List of strings to add to the image (will be matched with detected text regions)
            output_path: Path where to save the result (default: generates a path in data/generated_memes)
            remove_existing_text: Whether to remove existing text from the image
            text_color: Color of the text (RGB tuple)
            outline_color: Color of the text outline (RGB tuple)
            font_path: Optional path to custom font
            
        Returns:
            Path to the generated meme
        """
        try:
            # Ensure text_list is a list
            if text_list is None:
                text_list = []
            elif isinstance(text_list, str):
                text_list = [text_list]
            
            # Process the image with text replacement
            result_image = self.replace_text_in_image(
                image_path, text_list, font_path=font_path, text_color=text_color, outline_color=outline_color
            )
            
            # Generate output path if not provided
            if output_path is None:
                data_dir = Path(__file__).parent.parent / "data" / "generated_memes"
                data_dir.mkdir(parents=True, exist_ok=True)
                output_filename = f"meme_{os.path.basename(image_path)}"
                output_path = str(data_dir / output_filename)
            
            # Save the result
            cv2.imwrite(output_path, result_image)
            logger.info(f"Generated meme saved to {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating meme: {e}")
            raise
    
    def replace_text_in_image(self, image_path, text_list, font_path=None, 
                            text_color=(0, 0, 0), outline_color=(255, 255, 255)):
        """
        Replace detected text in an image with new text from the provided list.
        
        Args:
            image_path: Path to the input image
            text_list: List of strings to add to the image
            font_path: Optional path to custom font
            text_color: Color of the text (RGB tuple)
            outline_color: Color of the text outline (RGB tuple)
            
        Returns:
            OpenCV image with replaced text
        """
        # Get text locations and image
        text_results, image = self.detect_text(image_path)
        
        # Make a copy of the original image
        result_image = image.copy()
        
        logger.info("Removing existing text...")
        
        # First, remove all detected text
        for i, detection in enumerate(text_results):
            bbox, text, prob = detection
            logger.info(f"Removing text #{i+1}: '{text}' (Confidence: {prob:.4f})")
            
            # Convert bbox points to rectangle format for inpainting
            # bbox format from EasyOCR: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
            x_min = min(point[0] for point in bbox)
            y_min = min(point[1] for point in bbox)
            x_max = max(point[0] for point in bbox)
            y_max = max(point[1] for point in bbox)
            
            # Create a mask for the text region - make it slightly larger to ensure all text is removed
            mask = np.zeros(image.shape[:2], np.uint8)
            padding = 5  # Add padding around text
            cv2.rectangle(mask, 
                         (max(0, int(x_min-padding)), max(0, int(y_min-padding))), 
                         (min(image.shape[1], int(x_max+padding)), min(image.shape[0], int(y_max+padding))), 
                         255, -1)
            
            # Inpaint the text region (remove text)
            result_image = cv2.inpaint(result_image, mask, 3, cv2.INPAINT_TELEA)
        
        # Convert to PIL image for drawing
        pil_image = Image.fromarray(cv2.cvtColor(result_image, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)
        
        logger.info("Adding new text...")
        
        # Add new text at detected positions
        for i, detection in enumerate(text_results):
            if i < len(text_list) and text_list[i]:
                bbox, _, _ = detection
                
                # Calculate the center of the bounding box
                x_min = min(point[0] for point in bbox)
                y_min = min(point[1] for point in bbox)
                x_max = max(point[0] for point in bbox)
                y_max = max(point[1] for point in bbox)
                
                bbox_width = x_max - x_min
                bbox_height = y_max - y_min
                
                # Calculate optimal font size based on bounding box size
                box_max_height = bbox_height * 1.2  # Allow slight increase for better readability
                font_size = self.calculate_optimal_font_size(
                    text_list[i], bbox_width, box_max_height, min_size=10, max_size=100
                )
                
                # Get font
                font = self.get_font(font_size, font_path)
                
                # Get text dimensions
                if hasattr(font, "getbbox"):
                    text_bbox = font.getbbox(text_list[i])
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                else:
                    text_width, text_height = font.getsize(text_list[i])
                
                # Position text at center of bounding box
                text_x = x_min + (bbox_width - text_width) / 2
                text_y = y_min + (bbox_height - text_height) / 2
                
                # Draw text with outline
                self._draw_text_with_outline_at_position(
                    draw, text_list[i], font, int(text_x), int(text_y),
                    text_color=text_color, outline_color=outline_color
                )
                
                logger.info(f"Added text '{text_list[i]}' at detected position {i+1}")
        
        # Handle extra text (more text items than detected regions)
        if len(text_list) > len(text_results):
            # If there are no detected regions, or more text than regions, add them as traditional top/bottom text
            if len(text_results) == 0 or len(text_list) > len(text_results):
                # For top text, use the first extra item
                if len(text_results) < len(text_list):
                    top_text = text_list[len(text_results)]
                    font_size = self.calculate_optimal_font_size(
                        top_text, pil_image.width, 100, min_size=20, max_size=80
                    )
                    font = self.get_font(font_size, font_path)
                    
                    # Get text dimensions
                    if hasattr(font, "getbbox"):
                        text_bbox = font.getbbox(top_text)
                        text_width = text_bbox[2] - text_bbox[0]
                        text_height = text_bbox[3] - text_bbox[1]
                    else:
                        text_width, text_height = font.getsize(top_text)
                    
                    # Position at top
                    text_x = (pil_image.width - text_width) / 2
                    text_y = 20  # Some padding from top
                    
                    # Draw text
                    self._draw_text_with_outline_at_position(
                        draw, top_text, font, int(text_x), int(text_y),
                        text_color=text_color, outline_color=outline_color
                    )
                    
                    logger.info(f"Added top text: '{top_text}'")
                
                # For bottom text, use the last extra item
                if len(text_results) + 1 < len(text_list):
                    bottom_text = text_list[-1]
                    font_size = self.calculate_optimal_font_size(
                        bottom_text, pil_image.width, 100, min_size=20, max_size=80
                    )
                    font = self.get_font(font_size, font_path)
                    
                    # Get text dimensions
                    if hasattr(font, "getbbox"):
                        text_bbox = font.getbbox(bottom_text)
                        text_width = text_bbox[2] - text_bbox[0]
                        text_height = text_bbox[3] - text_bbox[1]
                    else:
                        text_width, text_height = font.getsize(bottom_text)
                    
                    # Position at bottom
                    text_x = (pil_image.width - text_width) / 2
                    text_y = pil_image.height - text_height - 20  # Some padding from bottom
                    
                    # Draw text
                    self._draw_text_with_outline_at_position(
                        draw, bottom_text, font, int(text_x), int(text_y),
                        text_color=text_color, outline_color=outline_color
                    )
                    
                    logger.info(f"Added bottom text: '{bottom_text}'")
        
        # Convert back to OpenCV format
        final_result = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        
        return final_result
    
    def _draw_text_with_outline_at_position(self, draw, text, font, x, y, 
                                           text_color=(0, 0, 0), outline_color=(255, 255, 255)):
        """
        Draw text with outline at the specified position.
        
        Args:
            draw: PIL.ImageDraw object
            text: Text to draw
            font: Font to use
            x: X-coordinate for text position
            y: Y-coordinate for text position
            text_color: Color of the text (RGB tuple)
            outline_color: Color of the text outline (RGB tuple)
        """
        # Draw text outline
        for offset_x in range(-self.outline_thickness, self.outline_thickness + 1):
            for offset_y in range(-self.outline_thickness, self.outline_thickness + 1):
                if offset_x != 0 or offset_y != 0:
                    draw.text((x + offset_x, y + offset_y), text, font=font, fill=outline_color)
        
        # Draw main text
        draw.text((x, y), text, font=font, fill=text_color)
    
    def _draw_text_with_outline(self, draw, image_width, text, font, vertical_position='top', 
                               padding=0, image_height=None, text_color=(0, 0, 0), outline_color=(255, 255, 255)):
        """
        Draw text with outline at the specified position.
        
        Args:
            draw: PIL.ImageDraw object
            image_width: Width of the image
            text: Text to draw
            font: Font to use
            vertical_position: 'top' or 'bottom'
            padding: Padding from the top or bottom
            image_height: Height of the image (needed for bottom text)
            text_color: Color of the text (RGB tuple)
            outline_color: Color of the text outline (RGB tuple)
        """
        # Get text dimensions
        if hasattr(font, "getbbox"):
            bbox = font.getbbox(text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            text_width, text_height = font.getsize(text)
        
        # Center the text horizontally
        text_x = (image_width - text_width) // 2
        
        # Position vertically based on top or bottom
        if vertical_position == 'top':
            text_y = (padding - text_height) // 2
        else:
            text_y = image_height - padding + (padding - text_height) // 2
        
        # Draw text using the helper method
        self._draw_text_with_outline_at_position(
            draw, text, font, text_x, text_y, text_color, outline_color
        )
        
        logger.info(f"Added {vertical_position} text: '{text}'")
        
        # Debug: print text width percentage
        text_percentage = (text_width / image_width) * 100
        logger.debug(f"{vertical_position.capitalize()} text width: {text_width}px ({text_percentage:.1f}% of image width)")
    
    def generate_white_box_meme(self, image_path, top_text, bottom_text, output_path=None, font_path=None):
        """
        Generate a meme by adding white boxes (top and bottom) sized to the input text, and add the text inside the boxes.
        Args:
            image_path: Path to the input image
            top_text: Text to add at the top
            bottom_text: Text to add at the bottom
            output_path: Path to save the result (optional)
            font_path: Optional path to custom font
        Returns:
            Path to the generated meme
        """
        from PIL import ImageDraw, ImageFont
        image = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(image)
        width, height = image.size
        font_size = self.calculate_optimal_font_size(top_text + bottom_text, width, height // 8, min_size=20, max_size=80)
        font = self.get_font(font_size, font_path)
        
        # Top text box
        if top_text:
            # Use font.getbbox() instead of draw.textsize() (which is deprecated)
            try:
                # For newer Pillow versions
                bbox = font.getbbox(top_text)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            except AttributeError:
                # Fall back to getsize for older Pillow versions
                text_width, text_height = font.getsize(top_text)
                
            box_height = text_height + 20
            draw.rectangle([(0, 0), (width, box_height)], fill="white")
            draw.text(((width - text_width) // 2, 10), top_text, fill="black", font=font)
            
        # Bottom text box
        if bottom_text:
            # Use font.getbbox() instead of draw.textsize() (which is deprecated)
            try:
                # For newer Pillow versions
                bbox = font.getbbox(bottom_text)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            except AttributeError:
                # Fall back to getsize for older Pillow versions
                text_width, text_height = font.getsize(bottom_text)
                
            box_height = text_height + 20
            draw.rectangle([(0, height - box_height), (width, height)], fill="white")
            draw.text(((width - text_width) // 2, height - box_height + 10), bottom_text, fill="black", font=font)
            
        # Save result
        if output_path is None:
            data_dir = Path(__file__).parent.parent / "data" / "generated_memes"
            data_dir.mkdir(parents=True, exist_ok=True)
            output_filename = f"whitebox_{os.path.basename(image_path)}"
            output_path = str(data_dir / output_filename)
        image.save(output_path)
        return output_path
    
    def smart_generate_meme(self, image_path, top_text, bottom_text, vector_db=None, similarity_threshold=0.4, font_path=None):
        """
        Smart meme generation: search for similar image, use white box if similar, else use current approach.
        Args:
            image_path: Path to the input image
            top_text: Top text for meme
            bottom_text: Bottom text for meme
            vector_db: ImageVectorDB instance
            similarity_threshold: Similarity threshold for using white box approach
            font_path: Optional font path
        Returns:
            (Path to generated meme, from_template: bool)
        """
        if vector_db is None:
            from ai_services.image_vector_db import ImageVectorDB
            vector_db = ImageVectorDB()
        # Search for similar image
        similar_path, similarity = vector_db.search(image_path, threshold=similarity_threshold)
        print(f"Similarity: {similarity}")
        if similar_path:
            # Use white box meme approach
            meme_path = self.generate_white_box_meme(similar_path, top_text, bottom_text, font_path=font_path)
            from_template = True
        else:
            # Use current approach: remove text, add new text
            meme_path = self.generate_meme(image_path, [top_text, bottom_text])
            from_template = False
            similarity = 0.0
        # Add this image to the vector DB if not already present
        if not similar_path or os.path.abspath(similar_path) != os.path.abspath(image_path):
            vector_db.add_image(image_path)
        return meme_path, from_template
    
    def remove_text_and_inpaint(self, image_path, min_confidence=0.5, output_path=None):
        """
        Remove all text regions with confidence > min_confidence and inpaint them.
        Args:
            image_path: Path to the input image
            min_confidence: Minimum confidence for text to be removed
            output_path: Path to save the cleaned image (optional)
        Returns:
            Path to the cleaned image
        """
        text_results, image = self.detect_text(image_path)
        mask = np.zeros(image.shape[:2], np.uint8)
        for bbox, text, prob in text_results:
            if prob > min_confidence:
                x_min = min(point[0] for point in bbox)
                y_min = min(point[1] for point in bbox)
                x_max = max(point[0] for point in bbox)
                y_max = max(point[1] for point in bbox)
                cv2.rectangle(mask, (int(x_min), int(y_min)), (int(x_max), int(y_max)), 255, -1)
        inpainted = cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)
        if output_path is None:
            output_path = str(Path(image_path).with_name(Path(image_path).stem + '_cleaned.jpg'))
        cv2.imwrite(output_path, inpainted)
        return output_path
    
    def generate_meme_from_clean(self, clean_image_path, text_list=None, output_path=None, 
                                text_color=(0, 0, 0), outline_color=(255, 255, 255), font_path=None,
                                detect_text_areas=True):
        """
        Generate a meme from an already cleaned image, skipping the text removal step.
        
        Args:
            clean_image_path: Path to the already cleaned input image
            text_list: List of strings to add to the image. Can be:
                - None or empty list: No text added
                - Single item: Added as top text
                - Two items: Added as top and bottom text
                - More items: First as top, last as bottom, rest placed intelligently
            output_path: Path where to save the result (default: generates a path in data/generated_memes)
            text_color: Color of the text (RGB tuple)
            outline_color: Color of the text outline (RGB tuple)
            font_path: Optional path to custom font
            detect_text_areas: Whether to detect text areas for placement (set False to add as top/bottom text)
            
        Returns:
            Path to the generated meme
        """
        try:
            # Ensure text_list is a list and handle empty text
            if text_list is None:
                text_list = []
            elif isinstance(text_list, str):
                text_list = [text_list]
            
            # Filter out empty strings
            text_list = [text for text in text_list if text.strip()]
            
            # If no text provided, just return the cleaned image
            if not text_list:
                # Create directory if needed
                data_dir = Path(__file__).parent.parent / "data" / "generated_memes"
                data_dir.mkdir(parents=True, exist_ok=True)
                
                # Default output path
                if output_path is None:
                    output_filename = f"meme_{os.path.basename(clean_image_path)}"
                    output_path = str(data_dir / output_filename)
                
                # Just copy the cleaned image
                shutil.copy2(clean_image_path, output_path)
                logger.info(f"No text provided, returning cleaned image: {output_path}")
                return output_path
            
            # Load the image directly (skip text removal)
            image = cv2.imread(clean_image_path)
            if image is None:
                raise ValueError(f"Could not read image from {clean_image_path}")
                
            # Convert to PIL for text manipulation
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(image_rgb)
            draw = ImageDraw.Draw(pil_image)

            # Extract top, bottom and middle texts
            top_text = text_list[0] if len(text_list) > 0 else ""
            bottom_text = text_list[-1] if len(text_list) > 1 else ""
            middle_texts = text_list[1:-1] if len(text_list) > 2 else []
            
            # Log what we're working with
            if top_text:
                logger.info(f"Using top text: '{top_text}'")
            if bottom_text and bottom_text != top_text:
                logger.info(f"Using bottom text: '{bottom_text}'")
            if middle_texts:
                logger.info(f"Additional middle texts: {len(middle_texts)}")

            # Detected text areas (if requested and available)
            text_positions = []
            if detect_text_areas and middle_texts:
                # Only detect text areas for middle texts
                text_results, _ = self.detect_text(clean_image_path)
                
                # If we have middle texts and detected areas, match them
                if text_results and middle_texts:
                    # Use only as many text areas as we have middle texts
                    text_areas = text_results[:len(middle_texts)] if len(text_results) <= len(middle_texts) else text_results
                    
                    # Process detected text positions
                    for i, detection in enumerate(text_areas):
                        if i < len(middle_texts):
                            bbox, _, _ = detection
                            
                            # Calculate the center of the bounding box
                            x_min = min(point[0] for point in bbox)
                            y_min = min(point[1] for point in bbox)
                            x_max = max(point[0] for point in bbox)
                            y_max = max(point[1] for point in bbox)
                            
                            bbox_width = x_max - x_min
                            bbox_height = y_max - y_min
                            
                            # Save position data
                            text_positions.append({
                                'x_min': x_min,
                                'y_min': y_min,
                                'width': bbox_width,
                                'height': bbox_height,
                                'text': middle_texts[i]
                            })
            
            # Add top text (if any)
            if top_text:
                font_size = self.calculate_optimal_font_size(
                    top_text, pil_image.width, 100, min_size=20, max_size=80
                )
                font = self.get_font(font_size, font_path)
                
                # Get text dimensions
                if hasattr(font, "getbbox"):
                    text_bbox = font.getbbox(top_text)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                else:
                    text_width, text_height = font.getsize(top_text)
                
                # Position at top
                text_x = (pil_image.width - text_width) / 2
                text_y = 20  # Some padding from top
                
                # Draw text
                self._draw_text_with_outline_at_position(
                    draw, top_text, font, int(text_x), int(text_y),
                    text_color=text_color, outline_color=outline_color
                )
                
                logger.info(f"Added top text: '{top_text}'")
            
            # Add bottom text (if any and different from top)
            if bottom_text and (len(text_list) > 1 or not top_text):
                font_size = self.calculate_optimal_font_size(
                    bottom_text, pil_image.width, 100, min_size=20, max_size=80
                )
                font = self.get_font(font_size, font_path)
                
                # Get text dimensions
                if hasattr(font, "getbbox"):
                    text_bbox = font.getbbox(bottom_text)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                else:
                    text_width, text_height = font.getsize(bottom_text)
                
                # Position at bottom
                text_x = (pil_image.width - text_width) / 2
                text_y = pil_image.height - text_height - 20  # Some padding from bottom
                
                # Draw text
                self._draw_text_with_outline_at_position(
                    draw, bottom_text, font, int(text_x), int(text_y),
                    text_color=text_color, outline_color=outline_color
                )
                
                logger.info(f"Added bottom text: '{bottom_text}'")
            
            # Draw middle texts at detected positions
            for position in text_positions:
                # Calculate optimal font size for the area
                text = position['text']
                box_width = position['width']
                box_height = position['height'] * 1.2  # Allow slight increase
                
                font_size = self.calculate_optimal_font_size(
                    text, box_width, box_height, min_size=10, max_size=100
                )
                
                font = self.get_font(font_size, font_path)
                
                # Get text dimensions
                if hasattr(font, "getbbox"):
                    text_bbox = font.getbbox(text)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                else:
                    text_width, text_height = font.getsize(text)
                
                # Position text at center of detected area
                text_x = position['x_min'] + (position['width'] - text_width) / 2
                text_y = position['y_min'] + (position['height'] - text_height) / 2
                
                # Draw text with outline
                self._draw_text_with_outline_at_position(
                    draw, text, font, int(text_x), int(text_y),
                    text_color=text_color, outline_color=outline_color
                )
                
                logger.info(f"Added middle text '{text}' at detected position")
            
            # Additional middle texts that didn't get positioned based on detection
            remaining_middle_texts = middle_texts[len(text_positions):]
            if remaining_middle_texts:
                # Distribute remaining texts evenly in the middle area of the image
                available_height = pil_image.height - 100  # Allow margin for top/bottom texts
                start_y = 100  # Start after the top margin
                
                # Calculate spacing between lines
                spacing = available_height / (len(remaining_middle_texts) + 1)
                
                for i, text in enumerate(remaining_middle_texts):
                    y_position = start_y + spacing * (i + 1)
                    
                    font_size = self.calculate_optimal_font_size(
                        text, pil_image.width * 0.9, 80, min_size=15, max_size=60
                    )
                    font = self.get_font(font_size, font_path)
                    
                    # Get text dimensions
                    if hasattr(font, "getbbox"):
                        text_bbox = font.getbbox(text)
                        text_width = text_bbox[2] - text_bbox[0]
                        text_height = text_bbox[3] - text_bbox[1]
                    else:
                        text_width, text_height = font.getsize(text)
                    
                    # Center horizontally
                    text_x = (pil_image.width - text_width) / 2
                    text_y = y_position - text_height / 2  # Center on calculated y position
                    
                    # Draw text
                    self._draw_text_with_outline_at_position(
                        draw, text, font, int(text_x), int(text_y),
                        text_color=text_color, outline_color=outline_color
                    )
                    
                    logger.info(f"Added middle text '{text}' at calculated position")
            
            # Convert back to OpenCV format
            result_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            # Generate output path if not provided
            if output_path is None:
                data_dir = Path(__file__).parent.parent / "data" / "generated_memes"
                data_dir.mkdir(parents=True, exist_ok=True)
                output_filename = f"meme_{os.path.basename(clean_image_path)}"
                output_path = str(data_dir / output_filename)
            
            # Save the result
            cv2.imwrite(output_path, result_image)
            logger.info(f"Generated meme saved to {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating meme from clean image: {e}")
            raise 