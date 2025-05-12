"""
Flask application entrypoint for the webapp interface.
"""
import sys
from pathlib import Path
# Define parent_dir for use throughout the app
parent_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(parent_dir)
import os
from flask import Flask, jsonify, redirect, url_for, request, send_from_directory, send_file, session
from datetime import datetime
import requests
from dotenv import load_dotenv
from flask_cors import CORS

# Load environment variables from .env file
load_dotenv()

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
        # Configure the API URL (backend runs on port 5000 by default)
        meme_api_port = os.environ.get('MEME_API_PORT', '5000')
        api_url = f"http://localhost:{meme_api_port}/api/smart_generate"
        
        # Forward the request to the API
        response = requests.post(
            api_url, 
            data=request.form, 
            files=request.files if request.files else None,
            headers={'X-Requested-With': 'XMLHttpRequest'} if request.headers.get('X-Requested-With') else {},
            timeout=30
        )
        
        # If JSON response, store info in session
        if response.headers.get('Content-Type', '').startswith('application/json'):
            try:
                data = response.json()
                # Convert boolean to string to avoid session serialization issues
                is_from_template = data.get('from_template', False)
                session['from_template'] = 'true' if is_from_template else 'false'
                session['similarity_score'] = data.get('similarity_score', 0)
                print(f"DEBUG - Session data: from_template={session['from_template']}, similarity_score={session['similarity_score']}")
            except Exception as e:
                print(f"DEBUG - Error parsing JSON in proxy: {e}")
                pass
        
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

# Add CORS support
CORS(app, origins=["https://your-vercel-domain.vercel.app"])

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get("PORT", 8000))  # Use port 8000 by default for webapp
    
    print(f"Starting webapp on http://127.0.0.1:{port}")
    print(f"Template folder: {app.template_folder}")
    print(f"Static folder: {app.static_folder}")
    
    # Run the app
    app.run(debug=True, host="0.0.0.0", port=port) 