#!/usr/bin/env python3
"""
Test script for Twitter bot meme generation functionality.
This script tests the meme generation part of the Twitter bot
without actually connecting to Twitter.
"""
import os
import sys
from pathlib import Path
import logging
import argparse

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from bot.twitter_bot import MemeTwitterBot
from utils.utils import download_image_from_url

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_with_local_image(image_path, text):
    """
    Test meme generation with a local image file.
    
    Args:
        image_path: Path to a local image
        text: Text to add to the meme
    """
    try:
        # Create a bot instance - this won't actually connect to Twitter
        bot = MemeTwitterBot.__new__(MemeTwitterBot)
        
        # Configure directories
        bot.user_query_dir = Path(__file__).parent.parent / "data" / "user_query_meme"
        bot.user_response_dir = Path(__file__).parent.parent / "data" / "user_response_meme"
        
        # Create directories if they don't exist
        bot.user_query_dir.mkdir(parents=True, exist_ok=True)
        bot.user_response_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize the meme service
        from ai_services.meme_service import MemeService
        bot.meme_service = MemeService()
        
        # Generate the meme
        meme_path = bot._generate_meme(image_path, text)
        
        if meme_path:
            logger.info(f"Successfully generated meme at: {meme_path}")
            logger.info(f"You can view the meme at this path")
        else:
            logger.error("Failed to generate meme")
            
    except Exception as e:
        logger.error(f"Error testing bot functionality: {e}")

def test_with_url(image_url, text):
    """
    Test meme generation with an image URL.
    
    Args:
        image_url: URL of an image
        text: Text to add to the meme
    """
    try:
        # Download the image
        logger.info(f"Downloading image from URL: {image_url}")
        image_path = download_image_from_url(image_url)
        
        if not image_path:
            logger.error("Failed to download image")
            return
            
        # Test with the downloaded image
        test_with_local_image(image_path, text)
            
    except Exception as e:
        logger.error(f"Error testing with URL: {e}")

def main():
    parser = argparse.ArgumentParser(description="Test Twitter bot meme generation")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image", help="Path to a local image file")
    group.add_argument("--url", help="URL of an image to download")
    parser.add_argument("--text", required=True, help="Text to add to the meme")
    
    args = parser.parse_args()
    
    if args.image:
        logger.info(f"Testing with local image: {args.image}")
        test_with_local_image(args.image, args.text)
    elif args.url:
        logger.info(f"Testing with image URL: {args.url}")
        test_with_url(args.url, args.text)

if __name__ == "__main__":
    main() 