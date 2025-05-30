import cv2
import easyocr
import json
import requests
import hashlib
import os
from pathlib import Path
from googleapiclient.discovery import build
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import urllib.parse

class MemeTemplateAnalyzer:
    def __init__(self, google_api_key, search_engine_id):
        """
        Initialize with Google Custom Search API credentials
        Get these from: https://console.developers.google.com/
        """
        self.google_api_key = google_api_key
        self.search_engine_id = search_engine_id
        self.service = build("customsearch", "v1", developerKey=google_api_key)
        self.reader = easyocr.Reader(['en'])
        self.templates_db = {}
        self.cache_dir = Path("meme_cache")
        self.cache_dir.mkdir(exist_ok=True)
        
    def search_meme_examples(self, meme_name, num_results=10):
        """Search for meme examples using Google Custom Search API"""
        query = f"{meme_name} meme template text"
        
        try:
            result = self.service.cse().list(
                q=query,
                cx=self.search_engine_id,
                searchType='image',
                num=num_results,
                imgType='photo',
                imgSize='medium'
            ).execute()
            
            if 'items' not in result:
                print(f"No results found for: {meme_name}")
                return []
                
            image_urls = []
            for item in result['items']:
                image_urls.append({
                    'url': item['link'],
                    'title': item.get('title', ''),
                    'context': item.get('snippet', '')
                })
                
            return image_urls
            
        except Exception as e:
            print(f"Error searching for {meme_name}: {e}")
            return []
    
    def download_image(self, url, filename):
        """Download image from URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            with open(filename, 'wb') as f:
                f.write(response.content)
            return True
        except Exception as e:
            print(f"Error downloading {url}: {e}")
            return False
    
    def get_image_hash(self, image_path):
        """Generate hash for image to avoid duplicates"""
        with open(image_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def detect_text_regions(self, image_path):
        """Detect text regions in an image using EasyOCR"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                return []
                
            results = self.reader.readtext(image)
            
            text_regions = []
            for (bbox, text, confidence) in results:
                if confidence > 0.3 and len(text.strip()) > 1:  # Filter low confidence and single chars
                    # Convert polygon bbox to rectangle
                    bbox_array = np.array(bbox, dtype=np.int32)
                    x, y, w, h = cv2.boundingRect(bbox_array)
                    
                    text_regions.append({
                        "bbox": [x, y, x + w, y + h],
                        "text": text.strip(),
                        "confidence": confidence,
                        "area": w * h
                    })
            
            # Sort by position (top to bottom, left to right)
            text_regions.sort(key=lambda r: (r["bbox"][1], r["bbox"][0]))
            return text_regions
            
        except Exception as e:
            print(f"Error detecting text in {image_path}: {e}")
            return []
    
    def analyze_meme_template(self, meme_name, max_examples=10):
        """Main function to analyze a meme template"""
        print(f"\n=== Analyzing meme template: {meme_name} ===")
        
        # Step 1: Search for meme examples
        print("1. Searching for meme examples...")
        image_urls = self.search_meme_examples(meme_name, max_examples)
        
        if not image_urls:
            print("No images found!")
            return None
        
        print(f"Found {len(image_urls)} potential images")
        
        # Step 2: Download and analyze images
        print("2. Downloading and analyzing images...")
        all_text_regions = []
        downloaded_images = []
        
        for i, img_data in enumerate(image_urls):
            url = img_data['url']
            filename = self.cache_dir / f"{meme_name}_{i}.jpg"
            
            if self.download_image(url, filename):
                # Detect text in the image
                text_regions = self.detect_text_regions(str(filename))
                
                if text_regions:  # Only keep images with detected text
                    print(f"  ✓ Image {i+1}: Found {len(text_regions)} text regions")
                    all_text_regions.append({
                        'image_path': str(filename),
                        'regions': text_regions,
                        'source_url': url
                    })
                    downloaded_images.append(str(filename))
                else:
                    print(f"  ✗ Image {i+1}: No text detected")
                    os.remove(filename)  # Remove images without text
            else:
                print(f"  ✗ Image {i+1}: Download failed")
        
        if not all_text_regions:
            print("No images with detectable text found!")
            return None
        
        # Step 3: Find common text regions
        print("3. Analyzing common text regions...")
        common_regions = self.find_common_text_regions(all_text_regions)
        
        # Step 4: Save template data
        template_data = {
            "meme_name": meme_name,
            "analyzed_images": len(all_text_regions),
            "common_regions": common_regions,
            "example_images": [item['image_path'] for item in all_text_regions],
            "analysis_date": str(Path().resolve())
        }
        
        # Save to JSON
        json_path = self.cache_dir / f"{meme_name}_template.json"
        with open(json_path, 'w') as f:
            json.dump(template_data, f, indent=2)
        
        print(f"4. Template data saved to: {json_path}")
        print(f"   Found {len(common_regions)} common text regions")
        
        self.templates_db[meme_name] = template_data
        return template_data
    
    def find_common_text_regions(self, all_text_regions):
        """Find common text regions across multiple images"""
        if not all_text_regions:
            return []
        
        # Get image dimensions (assuming all images are similar size)
        first_image = cv2.imread(all_text_regions[0]['image_path'])
        img_height, img_width = first_image.shape[:2]
        
        # Normalize coordinates to percentages for better comparison
        normalized_regions = []
        for img_data in all_text_regions:
            image = cv2.imread(img_data['image_path'])
            h, w = image.shape[:2]
            
            normalized = []
            for region in img_data['regions']:
                x1, y1, x2, y2 = region['bbox']
                normalized.append({
                    'x1_pct': x1 / w,
                    'y1_pct': y1 / h,
                    'x2_pct': x2 / w,
                    'y2_pct': y2 / h,
                    'text': region['text'],
                    'confidence': region['confidence']
                })
            normalized_regions.append(normalized)
        
        # Group similar regions (simple clustering by position)
        common_regions = []
        position_threshold = 0.15  # 15% difference allowed
        
        # For each region in the first image, find similar regions in other images
        if normalized_regions:
            for base_region in normalized_regions[0]:
                similar_regions = [base_region]
                
                # Check other images for similar positioned regions
                for other_img_regions in normalized_regions[1:]:
                    for region in other_img_regions:
                        if (abs(region['x1_pct'] - base_region['x1_pct']) < position_threshold and
                            abs(region['y1_pct'] - base_region['y1_pct']) < position_threshold):
                            similar_regions.append(region)
                            break
                
                # If this region appears in at least 50% of images, consider it common
                if len(similar_regions) >= len(normalized_regions) * 0.5:
                    # Calculate average position
                    avg_x1 = sum(r['x1_pct'] for r in similar_regions) / len(similar_regions)
                    avg_y1 = sum(r['y1_pct'] for r in similar_regions) / len(similar_regions)
                    avg_x2 = sum(r['x2_pct'] for r in similar_regions) / len(similar_regions)
                    avg_y2 = sum(r['y2_pct'] for r in similar_regions) / len(similar_regions)
                    
                    common_regions.append({
                        'bbox_percent': [avg_x1, avg_y1, avg_x2, avg_y2],
                        'bbox_pixel': [
                            int(avg_x1 * img_width),
                            int(avg_y1 * img_height),
                            int(avg_x2 * img_width),
                            int(avg_y2 * img_height)
                        ],
                        'occurrences': len(similar_regions),
                        'total_images': len(normalized_regions),
                        'example_texts': [r['text'] for r in similar_regions[:3]],  # First 3 examples
                        'position_type': self.classify_position(avg_y1)
                    })
        
        # Sort by position (top to bottom)
        common_regions.sort(key=lambda r: r['bbox_percent'][1])
        return common_regions
    
    def classify_position(self, y_percent):
        """Classify text position as top, middle, or bottom"""
        if y_percent < 0.33:
            return "top"
        elif y_percent < 0.66:
            return "middle"
        else:
            return "bottom"
    
    def load_template(self, meme_name):
        """Load template data from JSON file"""
        json_path = self.cache_dir / f"{meme_name}_template.json"
        if json_path.exists():
            with open(json_path, 'r') as f:
                return json.load(f)
        return None
    
    def generate_meme_with_template(self, template_image_path, texts, meme_name):
        """Generate meme using detected template regions"""
        template_data = self.load_template(meme_name)
        
        if not template_data:
            print(f"No template data found for {meme_name}. Please analyze it first.")
            return None
        
        # Load template image
        image = cv2.imread(template_image_path)
        if image is None:
            print(f"Could not load template image: {template_image_path}")
            return None
        
        # Convert to PIL for better text rendering
        pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)
        
        # Use common regions to place text
        regions = template_data['common_regions']
        
        for i, text in enumerate(texts):
            if i < len(regions):
                region = regions[i]
                bbox = region['bbox_pixel']
                
                # Calculate font size based on region size
                region_width = bbox[2] - bbox[0]
                region_height = bbox[3] - bbox[1]
                font_size = min(region_width // len(text) * 2, region_height // 3, 60)
                font_size = max(font_size, 20)  # Minimum font size
                
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    font = ImageFont.load_default()
                
                # Center text in region
                text_bbox = draw.textbbox((0, 0), text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                x = bbox[0] + (region_width - text_width) // 2
                y = bbox[1] + (region_height - text_height) // 2
                
                # Draw text with outline
                outline_color = "black"
                text_color = "white"
                
                # Draw outline
                for dx in [-2, -1, 0, 1, 2]:
                    for dy in [-2, -1, 0, 1, 2]:
                        if dx != 0 or dy != 0:
                            draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
                
                # Draw main text
                draw.text((x, y), text, font=font, fill=text_color)
        
        # Convert back to OpenCV format
        result_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        return result_image

# Example usage
def main():
    # You need to get these from Google Cloud Console
    GOOGLE_API_KEY = "your_google_api_key_here"
    SEARCH_ENGINE_ID = "your_custom_search_engine_id_here"
    
    analyzer = MemeTemplateAnalyzer(GOOGLE_API_KEY, SEARCH_ENGINE_ID)
    
    # Analyze a meme template
    meme_name = "distracted_boyfriend"
    template_data = analyzer.analyze_meme_template(meme_name, max_examples=15)
    
    if template_data:
        print(f"\n=== Analysis Results for {meme_name} ===")
        print(f"Common regions found: {len(template_data['common_regions'])}")
        
        for i, region in enumerate(template_data['common_regions']):
            print(f"\nRegion {i+1} ({region['position_type']}):")
            print(f"  Position: {region['bbox_percent']}")
            print(f"  Found in: {region['occurrences']}/{region['total_images']} images")
            print(f"  Example texts: {region['example_texts']}")
    
    # Generate meme using template
    template_image = "path/to/your/blank/template.jpg"  # Your blank template
    texts = ["When you see a new framework", "But you're still learning the basics"]
    
    result = analyzer.generate_meme_with_template(template_image, texts, meme_name)
    
    if result is not None:
        cv2.imshow('Generated Meme', result)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        
        # Save result
        cv2.imwrite('generated_meme.jpg', result)
        print("Generated meme saved as 'generated_meme.jpg'")

if __name__ == "__main__":
    main()