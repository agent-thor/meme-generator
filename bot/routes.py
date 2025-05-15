"""
Web application routes for meme generation.
"""
import logging
from flask import request, jsonify, send_file, session
from werkzeug.utils import secure_filename
import os
import time
import shutil
from pathlib import Path
import yaml
import sys
from tempfile import NamedTemporaryFile
import requests
import aiohttp
import aiofiles

# Add parent directory to sys.path to allow importing from other modules
sys.path.append(str(Path(__file__).parent.parent))
from ai_services.meme_service import MemeService
from ai_services.image_vector_db import ImageVectorDB
from utils import download_image_from_url, download_image_from_url_async

logger = logging.getLogger(__name__)

def configure_routes(app):
    """Configure Flask routes."""
    meme_engine = MemeService()
    
    @app.route('/')
    async def index():
        """Serve the main page."""
        return jsonify({
            'name': 'Meme Generator API',
            'version': '1.0.0',
            'endpoints': ['/api/generate', '/api/smart_generate']
        })
    
    @app.route('/api/generate', methods=['POST'])
    async def generate_meme():
        """Generate a meme from uploaded image."""
        try:
            form = await request.form
            
            # Get parameters from request
            image_url = form.get('image_url')
            top_text = form.get('top_text', '')
            bottom_text = form.get('bottom_text', '')
            remove_text = form.get('remove_text', 'false').lower() == 'true'
            
            # Initialize the meme service
            meme_service = MemeService()
            
            # Setup necessary directories
            project_root = Path(__file__).parent.parent
            output_dir = project_root / "data" / "generated_memes"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate a unique filename
            timestamp = str(int(time.time()))
            output_path = str(output_dir / f"meme_{timestamp}.jpg")
            
            # Process the image URL or uploaded file
            if image_url:
                # Download the image
                image_path = await download_image_from_url_async(image_url)
            elif 'image' in form:
                # Handle file upload
                file = form['image']
                filename = secure_filename(file.filename)
                image_path = str(project_root / "data" / "uploads" / f"{timestamp}_{filename}")
                
                # Ensure the directory exists
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                
                # Save the uploaded file
                file_data = await file.read()
                async with aiofiles.open(image_path, 'wb') as f:
                    await f.write(file_data)
            else:
                return jsonify({'error': 'No image provided'}), 400
            
            # Generate the meme
            meme_path = meme_service.generate_meme(
                image_path=image_path,
                text_list=[top_text, bottom_text] if top_text or bottom_text else None,
                output_path=output_path,
                remove_existing_text=remove_text
            )
            
            # Return the meme file
            return await send_file(
                meme_path,
                mimetype='image/jpeg',
                as_attachment=True,
                attachment_filename=f"meme_{os.path.basename(image_path)}"
            )
            
        except Exception as e:
            logger.error(f"Error generating meme: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/smart_generate', methods=['POST'])
    async def smart_generate_meme():
        """API endpoint for meme generation with similarity search and white box logic."""
        try:
            form = await request.form
            image_url = form.get('image_url')
            caption = form.get('caption', '')
            
            # Process the caption text carefully
            if caption:
                # Split by pipe character for top/bottom/middle text
                text_parts = [part.strip() for part in caption.split('|')]
                # Remove any empty strings from the list
                text_parts = [part for part in text_parts if part]
                
                # For template-based memes, we'll use just top and bottom texts
                top_text = text_parts[0] if text_parts else ""
                bottom_text = text_parts[1] if len(text_parts) > 1 else ""
                
                # Log what we received
                logger.info(f"Caption received: '{caption}'")
                logger.info(f"Parsed into {len(text_parts)} text parts")
            else:
                text_parts = []
                top_text = ""
                bottom_text = ""
                logger.info("No caption text provided")
            
            # Setup necessary directories
            project_root = Path(__file__).parent.parent
            user_query_dir = project_root / "data" / "user_query_meme"
            cleaned_image_dir = project_root / "data" / "cleaned_images"
            meme_templates_dir = project_root / "data" / "meme_templates"
            response_dir = project_root / "data" / "user_response_meme"
            
            # Ensure all directories exist
            for directory in [user_query_dir, cleaned_image_dir, meme_templates_dir, response_dir]:
                directory.mkdir(parents=True, exist_ok=True)
            
            # Generate timestamp for unique filenames
            timestamp = str(int(time.time()))
            
            # Download image locally if needed
            if image_url:
                # Download the image from S3 or remote URL asynchronously
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url, timeout=30) as resp:
                        if resp.status == 200:
                            # Save to user_query_meme with timestamp
                            filename = f"{timestamp}_url_image.jpg"
                            local_image_path = str(user_query_dir / filename)
                            
                            # Save the file asynchronously
                            async with aiofiles.open(local_image_path, 'wb') as f:
                                while True:
                                    chunk = await resp.content.read(1024)
                                    if not chunk:
                                        break
                                    await f.write(chunk)
                        else:
                            return jsonify({'error': 'Failed to download image from URL'}), 400
            elif 'image' in form:
                # Handle direct file upload
                file = form['image']
                filename = secure_filename(file.filename)
                local_image_path = str(user_query_dir / f"{timestamp}_{filename}")
                
                # Save the file asynchronously
                file_data = await file.read()
                async with aiofiles.open(local_image_path, 'wb') as f:
                    await f.write(file_data)
            else:
                return jsonify({'error': 'No image provided'}), 400
            
            # Initialize services
            meme_service = MemeService()
            vector_db = ImageVectorDB()
            
            # First, clean any text from the image with confidence > 0.5
            logger.info(f"Cleaning text from image: {local_image_path}")
            original_filename = os.path.basename(local_image_path)
            cleaned_filename = f"cleaned_{original_filename}"
            cleaned_image_path = str(cleaned_image_dir / cleaned_filename)
            
            # Remove text and save to cleaned_images folder
            meme_service.remove_text_and_inpaint(
                local_image_path, 
                min_confidence=0.5,
                output_path=cleaned_image_path
            )
            logger.info(f"Text cleaned, saved to: {cleaned_image_path}")
            
            # Then search for similar images in the meme_templates folder using the cleaned image
            try:
                # Get top 5 similar images with scores
                top_results = vector_db.search_top_k(cleaned_image_path, k=5)
                logger.info("Top 5 similar images:")
                for i, (path, score) in enumerate(top_results):
                    logger.info(f"  Similar image {i+1}. {path}: {score*100:.2f}%")
                
                # Use the top result if available and score is high enough
                if top_results and top_results[0][1] >= 0.8:
                    similar_path, similarity = top_results[0]
                    logger.info(f"Using top similar image: {similar_path} with score: {similarity*100:.2f}%")
                else:
                    similar_path = None
                    similarity = 0
                    logger.info(f"No template found with similarity >= 50%")
            except Exception as e:
                logger.warning(f"Error getting top 5 similar images: {e}")
                similar_path = None
                similarity = 0
            
            # Test if similar template exists
            if similar_path and os.path.exists(similar_path):
                # Use white box meme approach with template from meme_templates
                logger.info(f"Generating meme from template: {similar_path}")
                meme_path = meme_service.generate_white_box_meme(
                    similar_path, top_text, bottom_text
                )
                from_template = True
                logger.info(f"DEBUG - Using template: from_template={from_template}")
            else:
                # Use the cleaned image with new method to avoid redundant cleaning
                logger.info(f"No similar template found, generating from cleaned image")
                # Pass all text parts to handle properly
                meme_path = meme_service.generate_meme_from_clean(
                    cleaned_image_path, 
                    text_parts,  # Pass all parsed text parts
                    detect_text_areas=True
                )
                from_template = False
                logger.info(f"DEBUG - Not using template: from_template={from_template}")
            
            # Get the similarity score
            similarity_score = float(similarity * 100) if from_template else 0  # Convert to percentage
            
            # Copy the generated meme to user_response_meme directory
            output_filename = f"response_{os.path.basename(local_image_path)}"
            output_path = str(response_dir / output_filename)
            
            # Copy the file
            shutil.copy2(meme_path, output_path)
            
            logger.info(f"Saved meme response to {output_path}")
            
            # Return response with template info if requested via AJAX/JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                # Get relative path for web display
                rel_path = os.path.relpath(output_path, project_root)
                meme_url = f"/{rel_path.replace(os.sep, '/')}"
                
                # Print debug info
                print(f"DEBUG - Returning template info in JSON response: from_template={from_template}, similarity_score={similarity_score}")
                
                return jsonify({
                    'meme_url': meme_url, 
                    'from_template': from_template,
                    'similarity_score': similarity_score
                })
            
            # Otherwise return the file directly
            return await send_file(
                output_path,
                mimetype='image/jpeg',
                as_attachment=True,
                download_name=f"meme_{os.path.basename(local_image_path)}"
            )
        except Exception as e:
            logger.error(f"Error generating smart meme: {e}", exc_info=True)
            return jsonify({'error': f'Error generating meme: {str(e)}'}), 500
   