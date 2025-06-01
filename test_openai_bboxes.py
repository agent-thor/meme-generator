#!/usr/bin/env python3
"""
Test script for OpenAI-powered bounding box generation.
"""

import sys
from pathlib import Path
import logging

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent))

from ai_services.meme_service import MemeService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_openai_bboxes():
    """Test OpenAI bounding box generation with sample data."""
    
    # Initialize the service
    meme_service = MemeService()
    
    # Test cases
    test_cases = [
        {
            "caption": "When you realize it's Monday|But you're still in weekend mode",
            "image_dimensions": (800, 600),
            "description": "Two-part meme (classic top/bottom)"
        },
        {
            "caption": "Me trying to code|My computer|The bugs that appear",
            "image_dimensions": (600, 800),
            "description": "Three-part meme (distributed layout)"
        },
        {
            "caption": "Going to work|Going to vacation|Going to sleep|Going to eat",
            "image_dimensions": (1000, 800),
            "description": "Four-part meme (complex layout)"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"TEST CASE {i}: {test_case['description']}")
        print(f"Caption: {test_case['caption']}")
        print(f"Image Dimensions: {test_case['image_dimensions']}")
        print(f"{'='*60}")
        
        try:
            # Create a dummy image file for testing (we'll just use dimensions)
            # In real usage, this would be an actual image file
            
            # For testing, we'll modify the method to accept dimensions directly
            width, height = test_case['image_dimensions']
            caption = test_case['caption']
            
            # Parse caption text
            text_parts = [part.strip() for part in caption.split('|') if part.strip()]
            num_texts = len(text_parts)
            
            print(f"Number of text parts: {num_texts}")
            print(f"Text parts: {text_parts}")
            
            # Create a mock prompt (what would be sent to OpenAI)
            prompt = f"""You are an expert meme designer. I have a meme image with dimensions {width}x{height} pixels.

I need to place {num_texts} text parts from this caption: "{caption}"

The text parts are: {text_parts}

Please provide bounding box coordinates for each text part in the optimal meme layout positions. Consider:
- Traditional meme layouts (top/bottom for 2 texts, distributed for more)
- Avoid placing text in the center where the main subject usually is
- Leave appropriate margins from edges
- Make text areas large enough to be readable
- For multiple texts, distribute them evenly

Return ONLY a JSON dictionary in this exact format:
{{"text1": [[x1, y1], [x2, y1], [x2, y2], [x1, y2]], "text2": [[x1, y1], [x2, y1], [x2, y2], [x1, y2]], ...}}

Where:
- Each text area is a rectangle with 4 corner coordinates
- Coordinates are in pixels within the {width}x{height} image
- text1, text2, etc. correspond to the text parts in order
- Make text areas approximately 15-20% of image height for good readability"""

            print(f"\nPrompt that would be sent to OpenAI:")
            print("-" * 40)
            print(prompt)
            print("-" * 40)
            
            # Example of what OpenAI might return
            if num_texts == 2:
                example_response = {
                    "text1": [[50, 50], [width-50, 50], [width-50, 150], [50, 150]],
                    "text2": [[50, height-150], [width-50, height-150], [width-50, height-50], [50, height-50]]
                }
            elif num_texts == 3:
                example_response = {
                    "text1": [[50, 50], [width-50, 50], [width-50, 150], [50, 150]],
                    "text2": [[50, height//2-50], [width-50, height//2-50], [width-50, height//2+50], [50, height//2+50]],
                    "text3": [[50, height-150], [width-50, height-150], [width-50, height-50], [50, height-50]]
                }
            else:
                # Distribute evenly
                section_height = height // num_texts
                example_response = {}
                for j in range(num_texts):
                    y_start = j * section_height + 20
                    y_end = y_start + 80
                    example_response[f"text{j+1}"] = [
                        [50, y_start], [width-50, y_start], 
                        [width-50, y_end], [50, y_end]
                    ]
            
            print(f"\nExample OpenAI response:")
            import json
            print(json.dumps(example_response, indent=2))
            
            print(f"\nFormatted bounding boxes for our system:")
            for j, text_part in enumerate(text_parts):
                text_key = f"text{j+1}"
                if text_key in example_response:
                    bbox_coords = example_response[text_key]
                    print(f"  Text '{text_part}': {bbox_coords}")
            
        except Exception as e:
            logger.error(f"Error in test case {i}: {e}")
    
    print(f"\n{'='*60}")
    print("TEST COMPLETE")
    print("To use this functionality:")
    print("1. Set your OPENAI_API_KEY environment variable")
    print("2. Upload an image that doesn't match any template")
    print("3. The system will automatically use OpenAI to generate bounding boxes")
    print(f"{'='*60}")

if __name__ == "__main__":
    test_openai_bboxes() 