"""
Flask application entrypoint for the meme generation API.
"""
import os
from flask import Flask
from bot.routes import configure_routes
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create the Flask application
app = Flask(__name__)

# Configure routes for meme generation API
configure_routes(app)

# Models will load on first request (lazy loading)
print("Server starting... Models will load on first request")

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get("APP_PORT", 5000))
    host = os.environ.get("APP_HOST", "0.0.0.0")
    debug = os.environ.get("APP_DEBUG", "true").lower() == "true"
    
    print(f"Starting meme generation API on http://127.0.0.1:{port}")
    
    # Run the app
    app.run(debug=debug, host=host, port=port) 