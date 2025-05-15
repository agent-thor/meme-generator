"""
Quart application entrypoint for the webapp interface.
"""
import sys
from pathlib import Path
# Define parent_dir for use throughout the app
parent_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(parent_dir)
import os
import asyncio
import aiohttp
from quart import Quart, jsonify, redirect, url_for, request, send_from_directory, send_file, session
from datetime import datetime
from dotenv import load_dotenv
from quart_cors import cors

# Load environment variables from .env file
load_dotenv()

# Quart application setup
app = Quart(
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
async def serve_data_file(filename):
    """Serve files from the data directory."""
    return await send_from_directory(
        os.path.join(parent_dir, 'data'),
        filename
    )

# Create a proxy route to the meme API
@app.route('/api/generate', methods=['POST'])
async def proxy_to_meme_api():
    """Proxy requests to the meme generation API."""
    try:
        # Configure the API URL (backend runs on port 5000 by default)
        meme_api_port = os.environ.get('MEME_API_PORT', '5000')
        api_url = f"http://localhost:{meme_api_port}/api/smart_generate"
        
        # Get form data and files
        form_data = await request.form
        files = {}
        
        # Handle file uploads if present
        if 'image' in form_data and hasattr(form_data['image'], 'read'):
            file_data = form_data['image']
            files = {'image': (file_data.filename, await file_data.read(), file_data.content_type)}
        
        # Forward the request to the API using aiohttp
        async with aiohttp.ClientSession() as client_session:
            headers = {}
            if request.headers.get('X-Requested-With'):
                headers['X-Requested-With'] = request.headers.get('X-Requested-With')
                
            async with client_session.post(
                api_url, 
                data=form_data, 
                headers=headers,
                timeout=30
            ) as response:
                content = await response.read()
                content_type = response.headers.get('Content-Type', 'application/json')
                
                # If JSON response, store info in session
                if content_type.startswith('application/json'):
                    try:
                        data = await response.json()
                        # Convert boolean to string to avoid session serialization issues
                        is_from_template = data.get('from_template', False)
                        session['from_template'] = 'true' if is_from_template else 'false'
                        session['similarity_score'] = data.get('similarity_score', 0)
                        print(f"DEBUG - Session data: from_template={session['from_template']}, similarity_score={session['similarity_score']}")
                    except Exception as e:
                        print(f"DEBUG - Error parsing JSON in proxy: {e}")
                        pass
                
                # Return the API response
                return content, response.status, {'Content-Type': content_type}
    except Exception as e:
        return jsonify({
            'error': f"Failed to connect to meme API: {str(e)}"
        }), 500

# Import and register routes
from webapp.views import main
app.register_blueprint(main)

# Add CORS support
app = cors(app, allow_origin=["https://your-vercel-domain.vercel.app"])

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get("PORT", 8000))  # Use port 8000 by default for webapp
    
    print(f"Starting webapp on http://127.0.0.1:{port}")
    print(f"Template folder: {app.template_folder}")
    print(f"Static folder: {app.static_folder}")
    
    # Run the app with hypercorn for better concurrency
    import hypercorn.asyncio
    from hypercorn.config import Config
    
    config = Config()
    config.bind = [f"0.0.0.0:{port}"]
    config.use_reloader = True
    config.workers = os.cpu_count() or 4  # Use CPU count for workers
    
    asyncio.run(hypercorn.asyncio.serve(app, config)) 