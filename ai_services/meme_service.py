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
import openai
from openai import OpenAI
import json
import yaml
from dotenv import load_dotenv
import time
import hashlib
from functools import lru_cache
import pickle

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class MemeService:
    """Service for meme generation with text detection and manipulation."""
    
    def __init__(self):
        """Initialize the MemeService."""
        # Initialize OCR reader (lazily to save memory)
        self._ocr_reader = None
        self.outline_thickness = 3
        
        # Set up directories
        self.generated_memes_dir = Path(__file__).parent.parent / "data" / "generated_memes"
        self.generated_memes_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache directory for OCR results
        self.cache_dir = Path(__file__).parent.parent / "data" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize OpenAI
        self.openai_client = None
        if os.getenv('OPENAI_API_KEY'):
            self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        else:
            logger.warning("OpenAI API key not found. AI-generated bounding boxes will not be available.")
        
        # Performance optimization flags
        self.enable_ocr_cache = True
        self.enable_fast_inpaint = True
        self.skip_text_removal_for_templates = True
    
    def _get_image_hash(self, image_path):
        """Generate a hash for an image file for caching purposes."""
        try:
            with open(image_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            return file_hash
        except Exception as e:
            logger.warning(f"Could not generate hash for {image_path}: {e}")
            return None
    
    def _get_cached_ocr_result(self, image_path):
        """Get cached OCR result if available."""
        if not self.enable_ocr_cache:
            return None
            
        image_hash = self._get_image_hash(image_path)
        if not image_hash:
            return None
            
        cache_file = self.cache_dir / f"ocr_{image_hash}.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    cached_result = pickle.load(f)
                logger.info(f"Using cached OCR result for {image_path}")
                return cached_result
            except Exception as e:
                logger.warning(f"Failed to load cached OCR result: {e}")
        return None
    
    def _cache_ocr_result(self, image_path, ocr_result):
        """Cache OCR result for future use."""
        if not self.enable_ocr_cache:
            return
            
        image_hash = self._get_image_hash(image_path)
        if not image_hash:
            return
            
        cache_file = self.cache_dir / f"ocr_{image_hash}.pkl"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(ocr_result, f)
            logger.debug(f"Cached OCR result for {image_path}")
        except Exception as e:
            logger.warning(f"Failed to cache OCR result: {e}")

    @property
    def ocr_reader(self):
        """Lazy initialization of OCR reader."""
        if self._ocr_reader is None:
            logger.info("Initializing EasyOCR reader...")
            self._ocr_reader = easyocr.Reader(['en'])
            logger.info("EasyOCR reader initialized")
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
    
    def merge_nearby_text_regions(self, text_results, merge_threshold=50):
        """
        Merge nearby text regions that likely belong to the same text area.
        
        Args:
            text_results: List of (bbox, text, confidence) from OCR
            merge_threshold: Maximum distance between text regions to merge them
            
        Returns:
            List of merged text regions
        """
        if not text_results:
            return text_results
        
        # Sort by vertical position (y-coordinate)
        sorted_results = sorted(text_results, key=lambda x: min(point[1] for point in x[0]))
        
        merged_regions = []
        current_group = [sorted_results[0]]
        
        for i in range(1, len(sorted_results)):
            current_bbox, current_text, current_conf = sorted_results[i]
            prev_bbox, prev_text, prev_conf = current_group[-1]
            
            # Calculate vertical distance between current and previous text
            current_y_min = min(point[1] for point in current_bbox)
            current_y_max = max(point[1] for point in current_bbox)
            prev_y_min = min(point[1] for point in prev_bbox)
            prev_y_max = max(point[1] for point in prev_bbox)
            
            # Check if they overlap vertically or are close enough
            vertical_distance = max(0, current_y_min - prev_y_max)
            
            # Also check horizontal overlap
            current_x_min = min(point[0] for point in current_bbox)
            current_x_max = max(point[0] for point in current_bbox)
            prev_x_min = min(point[0] for point in prev_bbox)
            prev_x_max = max(point[0] for point in prev_bbox)
            
            # Check if there's horizontal overlap or they're close
            horizontal_overlap = not (current_x_max < prev_x_min or prev_x_max < current_x_min)
            horizontal_distance = min(abs(current_x_min - prev_x_max), abs(prev_x_min - current_x_max))
            
            # Merge if they're close vertically and have some horizontal relationship
            if (vertical_distance <= merge_threshold and horizontal_overlap) or \
               (vertical_distance <= merge_threshold/2 and horizontal_distance <= merge_threshold):
                current_group.append(sorted_results[i])
            else:
                # Process current group and start new group
                if current_group:
                    merged_regions.append(self._merge_text_group(current_group))
                current_group = [sorted_results[i]]
        
        # Don't forget the last group
        if current_group:
            merged_regions.append(self._merge_text_group(current_group))
        
        logger.info(f"Merged {len(text_results)} text regions into {len(merged_regions)} major text areas")
        
        return merged_regions
    
    def _merge_text_group(self, text_group):
        """
        Merge a group of text detections into a single region.
        
        Args:
            text_group: List of (bbox, text, confidence) that should be merged
            
        Returns:
            Single (bbox, text, confidence) tuple representing the merged region
        """
        if len(text_group) == 1:
            return text_group[0]
        
        # Combine all text with spaces
        combined_text = " ".join([text for _, text, _ in text_group])
        
        # Calculate average confidence
        avg_confidence = sum(conf for _, _, conf in text_group) / len(text_group)
        
        # Calculate bounding box that encompasses all regions
        all_points = []
        for bbox, _, _ in text_group:
            all_points.extend(bbox)
        
        x_coords = [point[0] for point in all_points]
        y_coords = [point[1] for point in all_points]
        
        # Create new bounding box
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        
        merged_bbox = [[x_min, y_min], [x_max, y_min], [x_max, y_max], [x_min, y_max]]
        
        logger.info(f"Merged {len(text_group)} text parts into: '{combined_text}' (confidence: {avg_confidence:.2f})")
        
        return (merged_bbox, combined_text, avg_confidence)

    def detect_text(self, image_path):
        """
        Detect text in an image using EasyOCR with caching support.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple of (text_results, image) where text_results is a list of 
            (bounding_box, text, confidence) tuples
        """
        # Check cache first
        cached_result = self._get_cached_ocr_result(image_path)
        if cached_result is not None:
            text_results, image_shape = cached_result
            # Load image for return
            image = cv2.imread(image_path)
            return text_results, image
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not read image from {image_path}")
        
        # Perform OCR
        start_time = time.time()
        logger.info(f"Running OCR on {image_path}...")
        
        results = self.ocr_reader.readtext(image)
        
        ocr_time = time.time() - start_time
        logger.info(f"OCR completed in {ocr_time:.2f} seconds, found {len(results)} text regions")
        
        # Process results
        text_results = []
        for (bbox, text, prob) in results:
            # Convert bbox to list of [x, y] points
            bbox_points = [[int(point[0]), int(point[1])] for point in bbox]
            text_results.append((bbox_points, text, prob))
            logger.debug(f"Detected: '{text}' with confidence {prob:.2f}")
        
        # Merge nearby text regions for better performance
        merged_results = self.merge_nearby_text_regions(text_results)
        
        # Cache the result
        cache_data = (merged_results, image.shape)
        self._cache_ocr_result(image_path, cache_data)
        
        return merged_results, image
    
    def fast_inpaint(self, image, mask, inpaint_radius=3):
        """
        Fast inpainting method with optimizations.
        
        Args:
            image: Input image (numpy array)
            mask: Mask indicating areas to inpaint
            inpaint_radius: Radius for inpainting
            
        Returns:
            Inpainted image
        """
        if not self.enable_fast_inpaint:
            return cv2.inpaint(image, mask, inpaint_radius, cv2.INPAINT_TELEA)
        
        # Use faster INPAINT_NS method for better performance
        return cv2.inpaint(image, mask, inpaint_radius, cv2.INPAINT_NS)
    
    def remove_text_and_inpaint(self, image_path, min_confidence=0.5, output_path=None):
        """
        Remove all text regions with confidence > min_confidence and inpaint them.
        Optimized version with caching and fast inpainting.
        
        Args:
            image_path: Path to the input image
            min_confidence: Minimum confidence for text to be removed
            output_path: Path to save the cleaned image (optional)
        Returns:
            Path to the cleaned image
        """
        # Check if we have a cached cleaned version
        if output_path and os.path.exists(output_path):
            logger.info(f"Using existing cleaned image: {output_path}")
            return output_path
        
        start_time = time.time()
        text_results, image = self.detect_text(image_path)
        
        # Create mask for text regions
        mask = np.zeros(image.shape[:2], np.uint8)
        text_regions_removed = 0
        
        for bbox, text, prob in text_results:
            if prob > min_confidence:
                x_min = min(point[0] for point in bbox)
                y_min = min(point[1] for point in bbox)
                x_max = max(point[0] for point in bbox)
                y_max = max(point[1] for point in bbox)
                
                # Add small padding to ensure complete text removal
                padding = 2
                x_min = max(0, x_min - padding)
                y_min = max(0, y_min - padding)
                x_max = min(image.shape[1], x_max + padding)
                y_max = min(image.shape[0], y_max + padding)
                
                cv2.rectangle(mask, (int(x_min), int(y_min)), (int(x_max), int(y_max)), 255, -1)
                text_regions_removed += 1
        
        if text_regions_removed == 0:
            logger.info("No text regions found to remove")
            # Just copy the original image
            if output_path is None:
                output_path = str(Path(image_path).with_name(Path(image_path).stem + '_cleaned.jpg'))
            shutil.copy2(image_path, output_path)
            return output_path
        
        # Perform fast inpainting
        logger.info(f"Inpainting {text_regions_removed} text regions...")
        inpainted = self.fast_inpaint(image, mask, inpaint_radius=3)
        
        if output_path is None:
            output_path = str(Path(image_path).with_name(Path(image_path).stem + '_cleaned.jpg'))
        
        cv2.imwrite(output_path, inpainted)
        
        inpaint_time = time.time() - start_time
        logger.info(f"Text removal and inpainting completed in {inpaint_time:.2f} seconds")
        
        return output_path
    
    @lru_cache(maxsize=32)
    def get_font(self, size, font_path=None):
        """
        Get a font object with caching for better performance.
        
        Args:
            size: Font size in pixels
            font_path: Optional path to custom font file
            
        Returns:
            PIL ImageFont object
        """
        try:
            if font_path and os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
            else:
                # Try to use a system font
                system_fonts = [
                    "/System/Library/Fonts/Arial.ttf",  # macOS
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
                    "C:/Windows/Fonts/arial.ttf",  # Windows
                    "/System/Library/Fonts/Helvetica.ttc",  # macOS alternative
                ]
                
                for font_file in system_fonts:
                    if os.path.exists(font_file):
                        return ImageFont.truetype(font_file, size)
                
                # Fallback to default font
                return ImageFont.load_default()
        except Exception as e:
            logger.warning(f"Could not load font: {e}")
            return ImageFont.load_default()
    
    def optimize_image_for_processing(self, image_path, max_dimension=1024):
        """
        Optimize image size for faster processing while maintaining quality.
        
        Args:
            image_path: Path to the input image
            max_dimension: Maximum width or height for processing
            
        Returns:
            Tuple of (optimized_image_path, scale_factor)
        """
        image = cv2.imread(image_path)
        if image is None:
            return image_path, 1.0
        
        height, width = image.shape[:2]
        
        # If image is already small enough, return as-is
        if max(width, height) <= max_dimension:
            return image_path, 1.0
        
        # Calculate scale factor
        scale_factor = max_dimension / max(width, height)
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        
        # Resize image
        resized_image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        # Save optimized image
        optimized_path = str(Path(image_path).with_name(Path(image_path).stem + '_optimized.jpg'))
        cv2.imwrite(optimized_path, resized_image, [cv2.IMWRITE_JPEG_QUALITY, 90])
        
        logger.info(f"Optimized image from {width}x{height} to {new_width}x{new_height} (scale: {scale_factor:.2f})")
        
        return optimized_path, scale_factor
    
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

    def normalize_bounding_boxes(self, bounding_boxes, source_image_shape):
        """
        Convert absolute bounding box coordinates to relative coordinates (0-1 range).
        
        Args:
            bounding_boxes: List of bounding box detections with absolute coordinates
            source_image_shape: Shape of the source image (height, width, channels)
            
        Returns:
            List of normalized bounding boxes with relative coordinates
        """
        source_height, source_width = source_image_shape[:2]
        normalized_boxes = []
        
        for bbox, text, confidence in bounding_boxes:
            # Convert absolute coordinates to relative (0-1 range)
            normalized_bbox = []
            for point in bbox:
                x_rel = point[0] / source_width
                y_rel = point[1] / source_height
                normalized_bbox.append([x_rel, y_rel])
            
            normalized_boxes.append((normalized_bbox, text, confidence))
            
        logger.info(f"Normalized {len(bounding_boxes)} bounding boxes to relative coordinates")
        return normalized_boxes
    
    def scale_normalized_bboxes_to_target(self, normalized_bboxes, target_image_shape):
        """
        Scale normalized bounding boxes (0-1 range) to target image dimensions.
        
        Args:
            normalized_bboxes: List of normalized bounding box detections
            target_image_shape: Shape of the target image (height, width, channels)
            
        Returns:
            List of bounding boxes scaled to target image dimensions
        """
        target_height, target_width = target_image_shape[:2]
        scaled_boxes = []
        
        for bbox, text, confidence in normalized_bboxes:
            # Convert relative coordinates back to absolute for target image
            scaled_bbox = []
            for point in bbox:
                x_abs = point[0] * target_width
                y_abs = point[1] * target_height
                scaled_bbox.append([x_abs, y_abs])
            
            scaled_boxes.append((scaled_bbox, text, confidence))
            
        logger.info(f"Scaled {len(normalized_bboxes)} bounding boxes to target image dimensions ({target_width}x{target_height})")
        return scaled_boxes

    def apply_text_to_template_with_bboxes(self, template_path, text_list, bounding_boxes, 
                                      source_image_path=None, output_path=None, text_color=(0, 0, 0), 
                                      outline_color=(255, 255, 255), font_path=None):
        """
        Apply text to a template image using provided bounding boxes.
        
        Args:
            template_path: Path to the template image
            text_list: List of text strings to place
            bounding_boxes: List of bounding box coordinates (either from OCR or OpenAI)
            source_image_path: Path to source image (for scaling if needed, None if no scaling)
            output_path: Output path for the generated meme
            text_color: RGB tuple for text color
            outline_color: RGB tuple for outline color
            font_path: Path to custom font file
            
        Returns:
            Path to the generated meme
        """
        try:
            # Load template image
            template_image = Image.open(template_path).convert('RGB')
            template_width, template_height = template_image.size
            
            # Create a copy for drawing
            meme_image = template_image.copy()
            draw = ImageDraw.Draw(meme_image)
            
            logger.info(f"Template dimensions: {template_width}x{template_height}")
            logger.info(f"Processing {len(text_list)} text parts with {len(bounding_boxes)} bounding boxes")
            
            # Check if we need to scale bounding boxes
            need_scaling = source_image_path and source_image_path != template_path
            
            if need_scaling:
                # Load source image to get dimensions for scaling
                source_image = Image.open(source_image_path)
                source_width, source_height = source_image.size
                logger.info(f"Source image dimensions: {source_width}x{source_height}")
                
                # Normalize bounding boxes from source image coordinates
                normalized_bboxes = self.normalize_bounding_boxes(bounding_boxes, (source_height, source_width))
                
                # Scale to template dimensions
                scaled_bboxes = self.scale_normalized_bboxes_to_target(normalized_bboxes, (template_height, template_width))
                logger.info("Scaled bounding boxes from source to template dimensions")
            else:
                # Use bounding boxes directly (already for template image)
                scaled_bboxes = bounding_boxes
                logger.info("Using bounding boxes directly for template (no scaling needed)")
            
            # Apply text to each bounding box
            for i, (text_part, bbox_data) in enumerate(zip(text_list, scaled_bboxes)):
                if i >= len(scaled_bboxes):
                    logger.warning(f"Not enough bounding boxes for text part {i+1}: '{text_part}'")
                    continue
                
                # Extract bounding box coordinates and font size
                openai_font_size = None
                if isinstance(bbox_data, tuple):
                    if len(bbox_data) >= 4:
                        # Format: (bbox_coords, text, confidence, font_size) from OpenAI
                        bbox_coords = bbox_data[0]
                        openai_font_size = bbox_data[3]
                    elif len(bbox_data) >= 1:
                        # Format: (bbox_coords, text, confidence) from OCR
                        bbox_coords = bbox_data[0]
                else:
                    # Direct bbox coordinates
                    bbox_coords = bbox_data
                
                if not bbox_coords or len(bbox_coords) != 4:
                    logger.warning(f"Invalid bounding box for text part {i+1}: {bbox_coords}")
                    continue
                
                # Calculate bounding box dimensions
                x_coords = [point[0] for point in bbox_coords]
                y_coords = [point[1] for point in bbox_coords]
                
                bbox_left = min(x_coords)
                bbox_top = min(y_coords)
                bbox_right = max(x_coords)
                bbox_bottom = max(y_coords)
                
                bbox_width = bbox_right - bbox_left
                bbox_height = bbox_bottom - bbox_top
                
                logger.info(f"Text {i+1}: '{text_part}' -> Box: ({bbox_left}, {bbox_top}, {bbox_right}, {bbox_bottom})")
                
                # Use OpenAI suggested font size if available, otherwise calculate optimal size
                if openai_font_size:
                    font_size = int(openai_font_size)
                    logger.info(f"Using OpenAI suggested font size: {font_size} for text '{text_part}'")
                else:
                    # Calculate optimal font size for this bounding box
                    font_size = self.calculate_optimal_font_size(
                        text_part, bbox_width, bbox_height, 
                        default_size=40, min_size=20, max_size=80
                    )
                    logger.info(f"Calculated font size: {font_size} for text '{text_part}'")
                
                # Get font
                font = self.get_font(font_size, font_path)
                
                # Calculate text position (center of bounding box)
                text_bbox = draw.textbbox((0, 0), text_part, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                # Center text in bounding box
                text_x = bbox_left + (bbox_width - text_width) // 2
                text_y = bbox_top + (bbox_height - text_height) // 2
                
                # Ensure text stays within image bounds
                text_x = max(0, min(text_x, template_width - text_width))
                text_y = max(0, min(text_y, template_height - text_height))
                
                # Draw text with outline
                self._draw_text_with_outline_at_position(
                    draw, text_part, font, text_x, text_y, text_color, outline_color
                )
                
                logger.info(f"Applied text '{text_part}' at position ({text_x}, {text_y}) with font size {font_size}")
            
            # Save the result
            if not output_path:
                timestamp = int(time.time())
                output_filename = f"meme_with_bboxes_{timestamp}.jpg"
                output_path = str(self.generated_memes_dir / output_filename)
            
            meme_image.save(output_path, 'JPEG', quality=95)
            logger.info(f"Generated meme with bounding boxes saved to {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error applying text to template with bounding boxes: {e}")
            raise

    def get_image_dimensions(self, image_path):
        """
        Get the dimensions of an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple of (width, height) in pixels
        """
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not read image at {image_path}")
            
            height, width = image.shape[:2]
            logger.info(f"Image dimensions: {width}x{height}")
            return width, height
            
        except Exception as e:
            logger.error(f"Error getting image dimensions: {e}")
            raise
    
    def generate_bounding_boxes_with_openai(self, image_path, text_parts):
        """
        Generate bounding box coordinates for text placement using OpenAI Vision API.
        
        Args:
            image_path: Path to the meme template image
            text_parts: List of text strings to place on the image
            
        Returns:
            List of tuples: (bounding_box_coords, text, confidence)
        """
        try:
            if not text_parts:
                logger.warning("No text parts provided for OpenAI bounding box generation")
                return []
            
            # Get image dimensions
            width, height = self.get_image_dimensions(image_path)
            num_texts = len(text_parts)
            
            # Validate text parts
            if num_texts == 0:
                logger.warning("Empty text parts list provided")
                return []
            
            # Create display text for prompt
            display_text = "\n".join([f"- {text}" for text in text_parts])
            
            # Encode image to base64 for OpenAI Vision API
            import base64
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Create prompt for OpenAI Vision API
            prompt = f"""Look at this meme template image and provide optimum bounding box coordinates AND text sizes for the following text parts:

Text parts to place:
{display_text}

The image resolution is: {width}x{height}

STRICT REQUIREMENTS for text sizing:
- For images under 500px width: font size 15-25 pixels MAX
- For images 500-800px width: font size 20-35 pixels MAX  
- For images 800-1200px width: font size 25-45 pixels MAX
- For images over 1200px width: font size 30-55 pixels MAX
- Text height should NEVER exceed 8% of image height
- Text width should NEVER exceed 85% of image width
- Prioritize READABILITY over large text - smaller is better than overlapping

Analyze the image and place text in optimal positions that:
- Avoid covering the main subject/character completely
- Use traditional meme layout positions (top/bottom for 2 texts, distributed for more)
- Leave appropriate margins from edges (minimum 5% of image dimensions)
- Keep text compact and readable
- Choose CONSERVATIVE text sizes - err on the side of smaller text

Return ONLY a JSON dictionary in this EXACT format with EXACTLY these keys:
{{"text1": {{"bbox": [[x1, y1], [x2, y1], [x2, y2], [x1, y2]], "font_size": 25}}, "text2": {{"bbox": [[x1, y1], [x2, y1], [x2, y2], [x1, y2]], "font_size": 22}}, "text3": {{"bbox": [[x1, y1], [x2, y1], [x2, y2], [x1, y2]], "font_size": 20}}}}

CRITICAL SIZING RULES:
- For this {width}x{height} image, maximum font size is {min(55, max(15, int(width * 0.04)))} pixels
- Bounding box height should be 6-10% of image height maximum
- Text should fit comfortably within bounding boxes with padding
- Use ONLY "text1", "text2", "text3" etc. as keys (NOT the actual text content)
- Each bounding box is a rectangle with 4 corner coordinates in pixels
- Return ONLY the JSON, no other text or explanation"""

            logger.info(f"Sending prompt to OpenAI Vision API for {num_texts} text parts: {text_parts}")
            
            # Call OpenAI Vision API
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            # Parse response
            response_text = response.choices[0].message.content.strip()
            logger.info(f"OpenAI Vision API response: {response_text}")
            
            # Try to parse JSON
            try:
                # Strip markdown code blocks if present
                if response_text.startswith("```json"):
                    # Remove ```json from start and ``` from end
                    response_text = response_text[7:]  # Remove ```json
                    if response_text.endswith("```"):
                        response_text = response_text[:-3]  # Remove ```
                elif response_text.startswith("```"):
                    # Remove ``` from start and end
                    response_text = response_text[3:]
                    if response_text.endswith("```"):
                        response_text = response_text[:-3]
                
                # Clean up any remaining whitespace
                response_text = response_text.strip()
                
                logger.info(f"Cleaned JSON for parsing: {response_text}")
                
                bounding_boxes = json.loads(response_text)
                
                # Validate the response format
                if not isinstance(bounding_boxes, dict):
                    raise ValueError("Response is not a dictionary")
                
                # Convert to the format expected by our system
                formatted_boxes = []
                for i, text_part in enumerate(text_parts):
                    text_key = f"text{i+1}"
                    if text_key in bounding_boxes:
                        text_data = bounding_boxes[text_key]
                        
                        # Handle both old format (direct bbox) and new format (bbox + font_size)
                        if isinstance(text_data, dict) and "bbox" in text_data:
                            # New format with bbox and font_size
                            bbox_coords = text_data["bbox"]
                            font_size = text_data.get("font_size", 40)  # Default to 40 if missing
                        elif isinstance(text_data, list):
                            # Old format (direct bbox coordinates)
                            bbox_coords = text_data
                            font_size = 40  # Default font size
                        else:
                            logger.warning(f"Invalid format for {text_key}: {text_data}")
                            continue
                        
                        if len(bbox_coords) == 4 and all(len(coord) == 2 for coord in bbox_coords):
                            # Format: (bbox, text, confidence, font_size) - Include font size
                            formatted_boxes.append((bbox_coords, text_part, 1.0, font_size))
                            logger.info(f"Generated bounding box for '{text_part}': {bbox_coords} with font size {font_size}")
                        else:
                            logger.warning(f"Invalid bounding box format for {text_key}")
                    else:
                        logger.warning(f"Missing bounding box for {text_key}")
                
                logger.info(f"Generated {len(formatted_boxes)} bounding boxes using OpenAI Vision API")
                return formatted_boxes
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse OpenAI response as JSON: {e}")
                logger.error(f"Response was: {response_text}")
                raise ValueError("OpenAI returned invalid JSON")
                
        except Exception as e:
            logger.error(f"Error generating bounding boxes with OpenAI Vision API: {e}")
            raise 