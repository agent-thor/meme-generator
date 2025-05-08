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

# Add parent directory to sys.path to allow importing from other modules
sys.path.append(str(Path(__file__).parent.parent))
from ai_services.meme_service import MemeService
from ai_services.image_vector_db import ImageVectorDB
from utils import download_image_from_url

logger = logging.getLogger(__name__)

def configure_routes(app):
    """Configure Flask routes."""
    meme_engine = MemeService()
    
    @app.route('/')
    def index():
        """Serve the main page."""
        return app.send_static_file('index.html')
    
    @app.route('/api/generate', methods=['POST'])
    def generate_meme():
        """Generate a meme from uploaded image."""
        try:
            # Check if request contains an image file or URL
            image_path = None
            
            if 'image' in request.files:
                # Handle file upload
                file = request.files['image']
                if file.filename == '':
                    return jsonify({'error': 'No selected file'}), 400
                
                # Create user_query_meme directory if it doesn't exist
                save_dir = Path(__file__).parent.parent / "data" / "user_query_meme"
                save_dir.mkdir(parents=True, exist_ok=True)
                
                # Generate timestamp filename
                timestamp = str(int(time.time()))
                filename = secure_filename(file.filename)
                save_path = save_dir / f"{timestamp}_{filename}"
                
                # Save the uploaded file
                file.save(save_path)
                image_path = str(save_path)
                
            elif 'image_url' in request.form:
                # Handle image URL
                image_url = request.form['image_url']
                if not image_url:
                    return jsonify({'error': 'No image URL provided'}), 400
                
                # Download image from URL to user_query_meme directory
                image_path = download_image_from_url(image_url)
            
            else:
                return jsonify({'error': 'No image or image URL provided'}), 400
            
            # Get caption from request or generate one
            caption = request.form.get('caption')
            caption_list = caption.split('|') if caption else []
            
            # First generate meme to a temporary path
            temp_output = meme_engine.generate_meme(image_path, caption_list)
            
            # Create user_response_meme directory if it doesn't exist
            response_dir = Path(__file__).parent.parent / "data" / "user_response_meme"
            response_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy the generated meme to user_response_meme directory
            output_filename = f"response_{os.path.basename(image_path)}"
            output_path = str(response_dir / output_filename)
            
            # Copy the file
            shutil.copy2(temp_output, output_path)
            
            logger.info(f"Saved meme response to {output_path}")
            
            # Return the generated meme
            return send_file(
                output_path,
                mimetype='image/jpeg',
                as_attachment=True,
                download_name=f"meme_{os.path.basename(image_path)}"
            )
            
        except Exception as e:
            logger.error(f"Error generating meme: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/smart_generate', methods=['POST'])
    def smart_generate_meme():
        """API endpoint for meme generation with similarity search and white box logic."""
        try:
            image_url = request.form.get('image_url')
            caption = request.form.get('caption', '')
            top_text, bottom_text, *_ = (caption.split('|') + ['', ''])[:2]
            
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
                # Download the image from S3 or remote URL
                resp = requests.get(image_url, stream=True)
                if resp.status_code == 200:
                    # Save to user_query_meme with timestamp
                    filename = f"{timestamp}_url_image.jpg"
                    local_image_path = str(user_query_dir / filename)
                    with open(local_image_path, 'wb') as f:
                        for chunk in resp.iter_content(1024):
                            f.write(chunk)
                else:
                    return jsonify({'error': 'Failed to download image from URL'}), 400
            elif 'image' in request.files:
                # Handle direct file upload
                file = request.files['image']
                filename = secure_filename(file.filename)
                local_image_path = str(user_query_dir / f"{timestamp}_{filename}")
                file.save(local_image_path)
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
            # logger.info(f"Searching for similar templates in database")
            # similar_path, similarity = vector_db.search(cleaned_image_path, threshold=0.8)
            
            # Log the top 5 most similar images
            try:
                # Get top 5 similar images with scores
                top_results = vector_db.search_top_k(cleaned_image_path, k=5)
                logger.info("Top 5 similar images:")
                for i, (path, score) in enumerate(top_results):
                    logger.info(f"  Simailr image {i+1}. {path}: {score*100:.2f}%")
                
                # Use the top result if available and score is high enough
                if top_results and top_results[0][1] >= 0.5:
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
            
            # Generate meme based on similarity search result
            if similar_path and os.path.exists(similar_path):
                # Use white box meme approach with template from meme_templates
                logger.info(f"Generating meme from template: {similar_path}")
                meme_path = meme_service.generate_white_box_meme(
                    similar_path, top_text, bottom_text
                )
                from_template = True
            else:
                # Use the cleaned image with normal text approach
                logger.info(f"No similar template found, generating from cleaned image")
                meme_path = meme_service.generate_meme(cleaned_image_path, [top_text, bottom_text])
                from_template = False
            
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
                return jsonify({
                    'meme_url': meme_url, 
                    'from_template': from_template,
                    'similarity_score': similarity_score
                })
            
            # Otherwise return the file directly
            return send_file(
                output_path,
                mimetype='image/jpeg',
                as_attachment=True,
                download_name=f"meme_{os.path.basename(local_image_path)}"
            )
        except Exception as e:
            logger.error(f"Error generating smart meme: {e}", exc_info=True)
            return jsonify({'error': f'Error generating meme: {str(e)}'}), 500
   