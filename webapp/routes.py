"""
Web application routes for meme generation.
"""
import logging
from flask import request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
from pathlib import Path
import yaml
from meme_engine import MemeEngine

logger = logging.getLogger(__name__)

def configure_routes(app):
    """Configure Flask routes."""
    meme_engine = MemeEngine()
    
    @app.route('/')
    def index():
        """Serve the main page."""
        return app.send_static_file('index.html')
    
    @app.route('/api/generate', methods=['POST'])
    def generate_meme():
        """Generate a meme from uploaded image."""
        try:
            if 'image' not in request.files:
                return jsonify({'error': 'No image provided'}), 400
            
            file = request.files['image']
            if file.filename == '':
                return jsonify({'error': 'No selected file'}), 400
            
            # Save uploaded file
            filename = secure_filename(file.filename)
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(upload_path)
            
            # Get caption from request or generate one
            caption = request.form.get('caption')
            if not caption:
                caption = meme_engine.generate_caption(upload_path)
            
            # Generate meme
            output_path = meme_engine.generate_meme(upload_path, caption)
            
            # Return the generated meme
            return send_file(
                output_path,
                mimetype='image/jpeg',
                as_attachment=True,
                download_name=f"meme_{filename}"
            )
            
        except Exception as e:
            logger.error(f"Error generating meme: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/templates', methods=['GET'])
    def get_templates():
        """Get available meme templates."""
        try:
            templates = meme_engine.get_templates()
            return jsonify(templates)
        except Exception as e:
            logger.error(f"Error getting templates: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/caption', methods=['POST'])
    def generate_caption():
        """Generate a caption for an image."""
        try:
            if 'image' not in request.files:
                return jsonify({'error': 'No image provided'}), 400
            
            file = request.files['image']
            if file.filename == '':
                return jsonify({'error': 'No selected file'}), 400
            
            # Save uploaded file temporarily
            filename = secure_filename(file.filename)
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(upload_path)
            
            # Generate caption
            caption = meme_engine.generate_caption(upload_path)
            
            # Clean up
            os.remove(upload_path)
            
            return jsonify({'caption': caption})
            
        except Exception as e:
            logger.error(f"Error generating caption: {e}")
            return jsonify({'error': str(e)}), 500 