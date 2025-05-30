import cv2
import easyocr
import numpy as np

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'])  # English language

# Load image
image_path = '/Users/krishnayadav/Downloads/images (1) (11).jpeg'
image = cv2.imread(image_path)

if image is None:
    print("Error: Could not load image. Please check the file path.")
    exit()

print(f"Image loaded successfully. Shape: {image.shape}")

# Create a copy for drawing bounding boxes
bbox_image = image.copy()

# Detect text using EasyOCR
results = reader.readtext(image)

print(f"Number of text regions detected: {len(results)}")

# Draw bounding boxes
for (bbox, text, confidence) in results:
    print(f"Detected text: '{text}' with confidence: {confidence:.2f}")
    
    # Convert bbox to integer coordinates
    bbox = np.array(bbox, dtype=np.int32)
    
    # Get bounding rectangle
    x, y, w, h = cv2.boundingRect(bbox)
    
    # Draw red rectangle
    cv2.rectangle(bbox_image, (x, y), (x + w, y + h), (0, 0, 255), 2)
    
    # Add text label
    cv2.putText(bbox_image, f"{text} ({confidence:.2f})", (x, y - 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    
    # Optional: Draw the exact polygon (more precise)
    cv2.polylines(bbox_image, [bbox], True, (255, 0, 0), 2)

# Display results
cv2.imshow('Original Image', image)
cv2.imshow('Text Detection - EasyOCR', bbox_image)

# Wait for window close or key press
while True:
    key = cv2.waitKey(1) & 0xFF
    if (key != 255 or 
        cv2.getWindowProperty('Original Image', cv2.WND_PROP_VISIBLE) < 1 or
        cv2.getWindowProperty('Text Detection - EasyOCR', cv2.WND_PROP_VISIBLE) < 1):
        break

cv2.destroyAllWindows()

# Save result
output_path = '/Users/krishnayadav/Downloads/easyocr_detection.jpg'
cv2.imwrite(output_path, bbox_image)
print(f"Result saved to: {output_path}")