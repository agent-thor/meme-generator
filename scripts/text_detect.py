import cv2
import numpy as np
import easyocr
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import os

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

def remove_text_and_create_meme(image_path, top_text, bottom_text=None, font_path=None, font_size=40, text_color=(0, 0, 0)):
    """
    First remove all detected text, then create a meme with new text
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
        if prob < 0.3:
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
    
    # Create a new image with extra space for top and bottom text
    pil_image = Image.fromarray(cv2.cvtColor(result_image, cv2.COLOR_BGR2RGB))
    
    # Create a new image with padding
    padding_top = 100 if top_text else 0
    padding_bottom = 100 if bottom_text else 0
    new_height = pil_image.height + padding_top + padding_bottom
    
    new_image = Image.new('RGB', (pil_image.width, new_height), (255, 255, 255))
    new_image.paste(pil_image, (0, padding_top))
    
    # Prepare for drawing
    draw = ImageDraw.Draw(new_image)
    
    # Choose font
    if font_path:
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()
    else:
        # Use default font
        try:
            # Try to get a larger font for meme text
            font = ImageFont.load_default().font_variant(size=font_size)
        except:
            font = ImageFont.load_default()
    
    print("Adding new text...")
    # Draw top text
    if top_text:
        # Get text dimensions
        if hasattr(font, "getbbox"):
            bbox = font.getbbox(top_text)
            text_width = bbox[2] - bbox[0]
        else:
            text_width, _ = font.getsize(top_text)
        
        # Center the text
        text_x = (new_image.width - text_width) // 2
        text_y = padding_top // 4
        
        # Draw the text
        draw.text((text_x, text_y), top_text, font=font, fill=text_color)
        print(f"Added top text: '{top_text}'")
    
    # Draw bottom text
    if bottom_text:
        # Get text dimensions
        if hasattr(font, "getbbox"):
            bbox = font.getbbox(bottom_text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            text_width, text_height = font.getsize(bottom_text)
        
        # Center the text
        text_x = (new_image.width - text_width) // 2
        text_y = new_image.height - padding_bottom // 2 - text_height // 2
        
        # Draw the text
        draw.text((text_x, text_y), bottom_text, font=font, fill=text_color)
        print(f"Added bottom text: '{bottom_text}'")
    
    # Convert back to OpenCV format
    final_result = cv2.cvtColor(np.array(new_image), cv2.COLOR_RGB2BGR)
    
    return final_result, text_results

def main():
    # Example usage
    image_path = "/Users/krishnayadav/Documents/forgex/meme-generator/data/sample_memes/meme1.png"
    
    # Get detected text first to understand the meme structure
    reader = easyocr.Reader(['en'])
    results = reader.readtext(image_path)
    
    # Print detected text
    print("Detected text:")
    for i, detection in enumerate(results):
        bbox, text, prob = detection
        if prob > 0.1:  # Only show confident detections
            print(f"{i+1}. '{text}' (Confidence: {prob:.4f})")
    
    # Create a new meme with custom text
    top_text = "wrong girlfriend selected"
    bottom_text = "But you don't know why"
    
    # Remove original text and create new meme
    result_image, _ = remove_text_and_create_meme(image_path, top_text, bottom_text)
    
    # Save the result
    output_path = os.path.join("data", "new_meme.jpg")
    os.makedirs("data", exist_ok=True)
    cv2.imwrite(output_path, result_image)
    
    # Display before and after
    plt.figure(figsize=(12, 6))
    plt.subplot(1, 2, 1)
    plt.title("Original Meme")
    plt.imshow(cv2.cvtColor(cv2.imread(image_path), cv2.COLOR_BGR2RGB))
    plt.subplot(1, 2, 2)
    plt.title("Modified Meme")
    plt.imshow(cv2.cvtColor(result_image, cv2.COLOR_RGB2BGR))
    plt.show()

if __name__ == "__main__":
    main()