"""
Utility functions for the meme generator.
"""
import logging
import requests
import os
import time
from pathlib import Path
import urllib.parse
import aiohttp
import aiofiles

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_image_from_url(url: str) -> str:
    """
    Downloads an image from a URL and saves it in the data/user_query_meme folder.
    
    Args:
        url: URL of the image to download
        
    Returns:
        Path to the downloaded image
    """
    try:
        # Create the user_query_meme directory if it doesn't exist
        save_dir = Path(__file__).parent.parent / "data" / "user_query_meme"
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename from URL or timestamp
        if url.split('?')[0].lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            # Extract filename from URL
            parsed_url = urllib.parse.urlparse(url)
            filename = os.path.basename(parsed_url.path)
            # Ensure filename uniqueness with timestamp prefix
            timestamp = str(int(time.time()))
            filename = f"{timestamp}_{filename}"
        else:
            # Use timestamp if URL doesn't have a recognizable image extension
            timestamp = str(int(time.time()))
            filename = f"{timestamp}.jpg"
        
        # Full path to save the image
        save_path = save_dir / filename
        
        # Download the image
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        
        # Save the image
        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        
        logger.info(f"Downloaded image from {url} to {save_path}")
        return str(save_path)
        
    except Exception as e:
        logger.error(f"Error downloading image from {url}: {e}")
        raise

async def download_image_from_url_async(url: str) -> str:
    """
    Asynchronously download an image from a URL and save it to the data directory.
    
    Args:
        url: URL of the image
        
    Returns:
        Path to the downloaded image
    """
    try:
        # Create data directory if it doesn't exist
        save_dir = Path(__file__).parent.parent / "data" / "downloads"
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate a filename from the URL
        filename = f"{hash(url)}.jpg"
        
        # Full path to save the image
        save_path = save_dir / filename
        
        # Download the image asynchronously
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                response.raise_for_status()
                
                # Save the image asynchronously
                async with aiofiles.open(save_path, 'wb') as file:
                    while True:
                        chunk = await response.content.read(8192)
                        if not chunk:
                            break
                        await file.write(chunk)
        
        logger.info(f"Asynchronously downloaded image from {url} to {save_path}")
        return str(save_path)
        
    except Exception as e:
        logger.error(f"Error downloading image from {url}: {e}")
        raise 