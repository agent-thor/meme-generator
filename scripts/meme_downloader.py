import os
import requests
from pathlib import Path

def download_images(url_file, output_dir):
    # Ensure output directory exists
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Read URLs from file
    with open(url_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"Found {len(urls)} URLs to download.")

    for idx, url in enumerate(urls, 1):
        print(f"Downloading {idx} of {len(urls)}")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            # Use the last part of the URL as the filename
            filename = url.split('/')[-1].split('?')[0]
            # If filename is empty, use a default
            if not filename:
                filename = f"meme_{idx}.jpg"
            out_path = output_dir / filename
            with open(out_path, 'wb') as img_file:
                img_file.write(response.content)
            print(f"{idx}: Downloaded {url} -> {out_path}")
        except Exception as e:
            print(f"{idx}: Failed to download {url}: {e}")

if __name__ == "__main__":
    url_file = "meme_template_srcs.txt"
    output_dir = "data/meme_templates"
    download_images(url_file, output_dir)
