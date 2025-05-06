import cv2
import numpy as np
import easyocr
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import os

def calculate_optimal_font_size(text, image_width, max_height, default_size=40, min_size=20, max_size=80):
    """
    Calculate optimal font size based on actual text width requirements
    Target: Make text occupy approximately 80% of available width
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
    
    # Fine-tune based on text length (some adjustments for character density)
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

def detect_text(image_path):
    """
    Detect text in an image using EasyOCR
    Returns the text and bounding boxes
    """
    # Initialize the OCR reader
    reader = easyocr.Reader(['en'])  # Specify language
    
    # Read image
    image = cv2.imread(image_path)
    
    # Detect text and return bounding boxes
    results = reader.readtext(image_path)
    
    return results, image

def remove_text_and_create_meme(image_path, top_text, bottom_text=None, font_path=None, text_color=(0, 0, 0), outline_color=(255, 255, 255)):
    """
    First remove all detected text, then create a meme with new text (with optimized font sizing)
    """
    # Get text locations and image
    text_results, image = detect_text(image_path)
    
    # Make a copy of the original image
    result_image = image.copy()
    
    print("Removing existing text...")
    # Process each text region
    for i, detection in enumerate(text_results):
        bbox, text, prob = detection
        
        # Only process text with good confidence
        if prob < 0.5:
            continue
            
        print(f"Removing text #{i+1}: '{text}' (Confidence: {prob:.4f})")
        
        # Convert bbox points to rectangle format for inpainting
        # bbox format from EasyOCR: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
        x_min = min(point[0] for point in bbox)
        y_min = min(point[1] for point in bbox)
        x_max = max(point[0] for point in bbox)
        y_max = max(point[1] for point in bbox)
        
        print(f"Rectangle (x_min, y_min, x_max, y_max): ({x_min:.1f}, {y_min:.1f}, {x_max:.1f}, {y_max:.1f})")
        
        # Create a mask for the text region - make it slightly larger to ensure all text is removed
        mask = np.zeros(image.shape[:2], np.uint8)
        padding = 5  # Add padding around text
        cv2.rectangle(mask, 
                     (max(0, int(x_min-padding)), max(0, int(y_min-padding))), 
                     (min(image.shape[1], int(x_max+padding)), min(image.shape[0], int(y_max+padding))), 
                     255, -1)
        
        # Inpaint the text region (remove text)
        result_image = cv2.inpaint(result_image, mask, 3, cv2.INPAINT_TELEA)
    
    # Convert to PIL image
    pil_image = Image.fromarray(cv2.cvtColor(result_image, cv2.COLOR_BGR2RGB))
    
    # Calculate proper padding based on text size
    # We need to get the actual text dimensions first
    padding_top = 0
    padding_bottom = 0
    
    # Calculate font sizes for both texts using optimized function
    top_font_size = calculate_optimal_font_size(top_text, pil_image.width, 200, min_size=10, max_size=100) if top_text else 0
    bottom_font_size = calculate_optimal_font_size(bottom_text if bottom_text else "", pil_image.width, 200, min_size=10, max_size=100) if bottom_text else 0
    
    print(f"Calculated font sizes - Top: {top_font_size}, Bottom: {bottom_font_size}")
    
    # Create temporary fonts to get text dimensions
    if font_path:
        try:
            temp_top_font = ImageFont.truetype(font_path, top_font_size) if top_text else None
            temp_bottom_font = ImageFont.truetype(font_path, bottom_font_size) if bottom_text else None
        except:
            try:
                temp_top_font = ImageFont.load_default().font_variant(size=top_font_size) if top_text else None
                temp_bottom_font = ImageFont.load_default().font_variant(size=bottom_font_size) if bottom_text else None
            except:
                temp_top_font = ImageFont.load_default() if top_text else None
                temp_bottom_font = ImageFont.load_default() if bottom_text else None
    else:
        try:
            temp_top_font = ImageFont.load_default().font_variant(size=top_font_size) if top_text else None
            temp_bottom_font = ImageFont.load_default().font_variant(size=bottom_font_size) if bottom_text else None
        except:
            temp_top_font = ImageFont.load_default() if top_text else None
            temp_bottom_font = ImageFont.load_default() if bottom_text else None
    
    # Get actual text dimensions
    if top_text and temp_top_font:
        if hasattr(temp_top_font, "getbbox"):
            bbox = temp_top_font.getbbox(top_text)
            top_text_height = bbox[3] - bbox[1]
        else:
            _, top_text_height = temp_top_font.getsize(top_text)
        padding_top = top_text_height + 40  # Add 40px extra margin
    
    if bottom_text and temp_bottom_font:
        if hasattr(temp_bottom_font, "getbbox"):
            bbox = temp_bottom_font.getbbox(bottom_text)
            bottom_text_height = bbox[3] - bbox[1]
        else:
            _, bottom_text_height = temp_bottom_font.getsize(bottom_text)
        padding_bottom = bottom_text_height + 40  # Add 40px extra margin
    
    # Create a new image with appropriate padding
    new_height = pil_image.height + padding_top + padding_bottom
    new_image = Image.new('RGB', (pil_image.width, new_height), (255, 255, 255))
    new_image.paste(pil_image, (0, padding_top))
    
    # Prepare for drawing
    draw = ImageDraw.Draw(new_image)
    
    print("Adding new text...")
    
    # Load fonts with calculated sizes
    if font_path:
        try:
            top_font = ImageFont.truetype(font_path, top_font_size) if top_text else None
            bottom_font = ImageFont.truetype(font_path, bottom_font_size) if bottom_text else None
        except:
            print("Warning: Custom font failed to load. Using default font.")
            try:
                top_font = ImageFont.load_default().font_variant(size=top_font_size) if top_text else None
                bottom_font = ImageFont.load_default().font_variant(size=bottom_font_size) if bottom_text else None
            except:
                top_font = ImageFont.load_default() if top_text else None
                bottom_font = ImageFont.load_default() if bottom_text else None
    else:
        try:
            top_font = ImageFont.load_default().font_variant(size=top_font_size) if top_text else None
            bottom_font = ImageFont.load_default().font_variant(size=bottom_font_size) if bottom_text else None
        except:
            top_font = ImageFont.load_default() if top_text else None
            bottom_font = ImageFont.load_default() if bottom_text else None
    
    # Draw top text
    if top_text and top_font:
        # Get text dimensions
        if hasattr(top_font, "getbbox"):
            bbox = top_font.getbbox(top_text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            text_width, text_height = top_font.getsize(top_text)
        
        # Center the text horizontally and vertically in the top padding area
        text_x = (new_image.width - text_width) // 2
        text_y = (padding_top - text_height) // 2
        
        # Debug: print actual text width vs image width
        text_percentage = (text_width / new_image.width) * 100
        print(f"Top text width: {text_width}px ({text_percentage:.1f}% of image width)")
        
        # Draw text with outline for better readability
        outline_thickness = 3
        # Draw outline
        for offset_x in range(-outline_thickness, outline_thickness + 1):
            for offset_y in range(-outline_thickness, outline_thickness + 1):
                if offset_x != 0 or offset_y != 0:
                    draw.text((text_x + offset_x, text_y + offset_y), top_text, font=top_font, fill=outline_color)
        # Draw main text
        draw.text((text_x, text_y), top_text, font=top_font, fill=text_color)
        print(f"Added top text: '{top_text}' with font size {top_font_size}")
    
    # Draw bottom text
    if bottom_text and bottom_font:
        # Get text dimensions
        if hasattr(bottom_font, "getbbox"):
            bbox = bottom_font.getbbox(bottom_text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            text_width, text_height = bottom_font.getsize(bottom_text)
        
        # Center the text horizontally and vertically in the bottom padding area
        text_x = (new_image.width - text_width) // 2
        text_y = new_image.height - padding_bottom + (padding_bottom - text_height) // 2
        
        # Debug: print actual text width vs image width
        text_percentage = (text_width / new_image.width) * 100
        print(f"Bottom text width: {text_width}px ({text_percentage:.1f}% of image width)")
        
        # Draw text with outline for better readability
        # Draw outline
        for offset_x in range(-outline_thickness, outline_thickness + 1):
            for offset_y in range(-outline_thickness, outline_thickness + 1):
                if offset_x != 0 or offset_y != 0:
                    draw.text((text_x + offset_x, text_y + offset_y), bottom_text, font=bottom_font, fill=outline_color)
        # Draw main text
        draw.text((text_x, text_y), bottom_text, font=bottom_font, fill=text_color)
        print(f"Added bottom text: '{bottom_text}' with font size {bottom_font_size}")
    
    # Convert back to OpenCV format
    final_result = cv2.cvtColor(np.array(new_image), cv2.COLOR_RGB2BGR)
    
    return final_result, text_results

def main(index):
    # Example usage
    image_path = f"/Users/krishnayadav/Documents/forgex/meme-generator/data/sample_memes/meme{index}.png"
    
    # Get detected text first to understand the meme structure
    reader = easyocr.Reader(['en'])
    results = reader.readtext(image_path)
    
    # Print detected text
    print("Detected text:")
    for i, detection in enumerate(results):
        bbox, text, prob = detection
        if prob > 0.5:  # Only show confident detections
            print(f"{i+1}. '{text}' (Confidence: {prob:.4f})")
    
    # Create a new meme with custom text
    text_list = ["wrong girlfriend selected", "But you don't know why"]
    
    # Extract top and bottom text from text_list
    top_text = text_list[0] if len(text_list) > 0 else ""
    bottom_text = text_list[1] if len(text_list) > 1 else None
    
    # Remove original text and create new meme
    result_image, _ = remove_text_and_create_meme(image_path, top_text, bottom_text)
    
    # Save the result
    output_path = os.path.join("data", f"new_meme_{index}.jpg")
    os.makedirs("data", exist_ok=True)
    cv2.imwrite(output_path, result_image)
    
    # Display before and after
    plt.figure(figsize=(12, 6))
    plt.subplot(1, 2, 1)
    plt.title("Original Meme")
    plt.imshow(cv2.cvtColor(cv2.imread(image_path), cv2.COLOR_BGR2RGB))
    plt.subplot(1, 2, 2)
    plt.title("Modified Meme")
    plt.imshow(cv2.cvtColor(result_image, cv2.COLOR_BGR2RGB))
    plt.show()

if __name__ == "__main__":
    for index in range(1, 6):
        main(index)