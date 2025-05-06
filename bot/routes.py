"""
Web application routes for meme generation.
"""
import logging
from flask import request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import time
import shutil
from pathlib import Path
import yaml
import sys

# Add parent directory to sys.path to allow importing from other modules
sys.path.append(str(Path(__file__).parent.parent))
from ai_services.meme_service import MemeService
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
    
   