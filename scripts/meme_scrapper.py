import requests
from bs4 import BeautifulSoup
import time
import re

def extract_meme_srcs(max_pages=100):
    all_srcs = []
    
    for page_num in range(1, max_pages + 1):
        url = f"https://imgflip.com/memetemplates?page={page_num}"
        print(f"Scraping page {page_num}...")
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all img elements within mt-box divs
            meme_boxes = soup.find_all('div', class_='mt-box')
            
            page_srcs = []
            for box in meme_boxes:
                img_wrap = box.find('div', class_='mt-img-wrap')
                if img_wrap:
                    img = img_wrap.find('img', class_='shadow')
                    if img and img.get('src'):
                        src = img['src']
                        # Ensure we have the full URL
                        if src.startswith('//'):
                            src = 'https:' + src
                        page_srcs.append(src)
            # Print the number of URLs extracted
            print(f"Extracted {len(page_srcs)} URLs:")
            for idx, link in enumerate(page_srcs, 1):
                print(f"{idx}, {link}")
            
            # If no sources found on this page, we've likely reached the end
            if not page_srcs:
                print(f"No more memes found on page {page_num}. Stopping.")
                break
                
            all_srcs.extend(page_srcs)
            print(f"Found {len(page_srcs)} meme templates on page {page_num}")
            
            # Add a short delay to be respectful to the server
            time.sleep(1)
            
        except Exception as e:
            print(f"Error on page {page_num}: {e}")
            break
    
    return all_srcs

def save_to_file(srcs, filename="meme_template_srcs.txt"):
    with open(filename, 'w') as f:
        for src in srcs:
            f.write(src + '\n')
    
    print(f"Saved {len(srcs)} meme template URLs to {filename}")

if __name__ == "__main__":
    srcs = extract_meme_srcs()
    save_to_file(srcs)