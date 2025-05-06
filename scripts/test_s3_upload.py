#!/usr/bin/env python
"""
Script to test uploading a file to S3.
"""
import os
import sys
import argparse
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

# Import S3 upload function
from utils.s3_utils import upload_image_to_s3, debug_aws_credentials

def create_test_image(output_path):
    """
    Create a simple test image if no input file is provided.
    
    Args:
        output_path: Path to save the test image
        
    Returns:
        str: Path to the created image
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a blank image with white background
        img = Image.new('RGB', (400, 200), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # Add text to the image
        text = "S3 Test Image"
        draw.text((150, 80), text, fill=(0, 0, 0))
        
        # Add timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        draw.text((130, 120), timestamp, fill=(100, 100, 100))
        
        # Save the image
        img.save(output_path)
        print(f"Created test image at {output_path}")
        return output_path
        
    except ImportError:
        print("PIL not available. Using a text file instead.")
        with open(output_path, 'w') as f:
            f.write("This is a test file for S3 upload.")
        return output_path

def main():
    """Run the S3 upload test."""
    parser = argparse.ArgumentParser(description="Test S3 file upload")
    parser.add_argument('--file', help="Path to file to upload (will create a test image if not provided)")
    args = parser.parse_args()
    
    print("\n===== S3 Upload Test =====\n")
    
    # First check credentials
    print("Checking AWS credentials...")
    debug_info = debug_aws_credentials()
    
    if not debug_info['boto3_session_valid']:
        print("\n❌ AWS credentials are not valid. Running the credentials test...")
        from scripts.test_aws_credentials import main as test_credentials
        test_credentials()
        print("\nContinuing with test upload anyway (will use local fallback)...\n")
    
    # Get or create a test file
    file_path = args.file
    if not file_path:
        test_dir = Path(__file__).parent.parent / "data" / "test"
        test_dir.mkdir(exist_ok=True, parents=True)
        test_image_path = test_dir / "test_image.jpg"
        file_path = create_test_image(test_image_path)
    
    print(f"Using file: {file_path}")
    print("Uploading to S3...")
    
    # Try to upload
    result_url = upload_image_to_s3(file_path)
    
    print("\n===== Upload Result =====")
    if result_url:
        print(f"Upload successful!")
        print(f"URL: {result_url}")
        
        if result_url.startswith("file://"):
            print("\n⚠️ NOTE: This is a local file URL, not an S3 URL.")
            print("This indicates that S3 upload was skipped due to credential issues.")
            print("The file was not actually uploaded to S3.")
        else:
            print("\n✅ This is an S3 URL, indicating successful upload to S3.")
    else:
        print("❌ Upload failed. No URL returned.")
    
    print("\n=========================\n")

if __name__ == "__main__":
    main() 