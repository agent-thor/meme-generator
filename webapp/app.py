"""
Flask application entrypoint for the webapp interface.
"""
import os
from flask import Flask, jsonify, redirect, url_for, request, send_from_directory
from datetime import datetime
import requests
from pathlib import Path
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to sys.path to allow importing from other modules
parent_dir = str(Path(__file__).parent.parent)
sys.path.append(parent_dir)

# Flask application setup
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),
    static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
)

# Configure the app
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'meme-generator-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Set jinja global variable for footer
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

# Serve files from data directory
@app.route('/data/<path:filename>')
def serve_data_file(filename):
    """Serve files from the data directory."""
    return send_from_directory(
        os.path.join(parent_dir, 'data'),
        filename
    )

# Create a proxy route to the meme API
@app.route('/api/generate', methods=['POST'])
def proxy_to_meme_api():
    """Proxy requests to the meme generation API."""
    try:
        # Configure the API URL (assuming the main API runs on port 5000)
        meme_api_port = os.environ.get('MEME_API_PORT', '5000')
        api_url = f"http://localhost:{meme_api_port}/api/generate"
        
        # Forward the request to the API
        response = requests.post(
            api_url, 
            data=request.form, 
            files=request.files if request.files else None,
            timeout=30
        )
        
        # Return the API response
        return (
            response.content, 
            response.status_code, 
            {'Content-Type': response.headers.get('Content-Type', 'application/json')}
        )
    except requests.RequestException as e:
        return jsonify({
            'error': f"Failed to connect to meme API: {str(e)}"
        }), 500

# Import and register routes
from webapp.views import main
app.register_blueprint(main)

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get("PORT", 8000))  # Use port 8000 by default for webapp
    
    print(f"Starting webapp on http://127.0.0.1:{port}")
    print(f"Template folder: {app.template_folder}")
    print(f"Static folder: {app.static_folder}")
    
    # Run the app
    app.run(debug=True, host="0.0.0.0", port=port) 