# from PIL import Image

# def get_image_resolution(image_path):
#     try:
#         with Image.open(image_path) as img:
#             width, height = img.size
#             print(f"Image resolution: {width} x {height}")
#     except Exception as e:
#         print(f"Error: {e}")

# # Example usage
# image_path = "/Users/krishnayadav/Downloads/98ca983b7763ec024284eac62288ecc8.jpg"  # Replace with your image file path
# get_image_resolution(image_path)


from PIL import Image, ImageDraw, ImageFont

def draw_text_on_image(image_path, output_path, text_boxes):
    # Load image
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    
    # Load default font
    try:
        font = ImageFont.truetype("arial.ttf", size=20)
    except:
        font = ImageFont.load_default()
    
    for text, box in text_boxes:
        # Convert bounding box to top-left and bottom-right
        x0, y0 = box[0]
        x1, y1 = box[2]
        
        # Calculate text size
        text_width, text_height = draw.textsize(text, font=font)
        
        # Center the text
        x = x0 + (x1 - x0 - text_width) / 2
        y = y0 + (y1 - y0 - text_height) / 2

        # Optional: Draw box for visibility
        draw.rectangle([x0, y0, x1, y1], outline="red", width=2)

        # Draw text
        draw.text((x, y), text, fill="black", font=font)
    
    # Save the result
    image.save(output_path)
    print(f"Saved image to {output_path}")

# Example usage:
text_boxes = [
    ("Girl in Red", [[80, 150], [220, 150], [220, 190], [80, 190]]),
    ("Boyfriend", [[320, 120], [460, 120], [460, 160], [320, 160]]),
    ("Girlfriend", [[540, 130], [700, 130], [700, 170], [540, 170]])
]

draw_text_on_image("/Users/krishnayadav/Downloads/98ca983b7763ec024284eac62288ecc8.jpg", "output.jpg", text_boxes)
