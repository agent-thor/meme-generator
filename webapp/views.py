"""
Views for the web application.
"""
import os
import json
import logging
from pathlib import Path
from datetime import datetime
import requests
import uuid
from flask import (
    Blueprint, render_template, redirect, url_for, 
    flash, request, jsonify, current_app, session
)
import werkzeug.utils
import shutil

from .forms import MemeForm, ChatForm
from utils import upload_image_to_s3
import sys

# Add parent directory to path to import from other modules
sys.path.append(str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

# Create blueprint
main = Blueprint('main', __name__)

# Default API URL when running locally
DEFAULT_API_URL = "http://localhost:5000/api/generate"

def get_api_url():
    """Get the configured API URL from environment or use the default."""
    return os.environ.get('MEME_API_URL', '/api/generate')

def save_image_from_response(response, directory):
    """
    Save image from response to specified directory
    
    Args:
        response: Response object from requests
        directory: Directory to save image to
        
    Returns:
        Path to saved image
    """
    # Create directory if it doesn't exist
    Path(directory).mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    filename = f"{uuid.uuid4()}.jpg"
    save_path = os.path.join(directory, filename)
    
    # Save image content
    with open(save_path, 'wb') as f:
        f.write(response.content)
    
    logger.info(f"Saved image to {save_path}")
    return save_path

@main.route('/', methods=['GET', 'POST'])
def index():
    """Render the main page with meme generator form."""
    form = MemeForm()
    
    if form.validate_on_submit():
        # Process the form data here
        if form.image.data:
            # Get the uploaded file
            uploaded_file = form.image.data
            
            # Create a safe filename
            filename = werkzeug.utils.secure_filename(uploaded_file.filename)
            
            # Create temp directory for uploads if it doesn't exist
            user_query_dir = Path(__file__).parent.parent / "data" / "user_query_meme"
            user_query_dir.mkdir(parents=True, exist_ok=True)
            
            # Save the file temporarily with a unique name
            unique_filename = f"{int(datetime.now().timestamp())}_{filename}"
            original_path = user_query_dir / unique_filename
            uploaded_file.save(original_path)
            
            logger.info(f"Saved original image to {original_path}")
            
            # Upload to S3 and get URL
            image_url = upload_image_to_s3(original_path)
            
            if not image_url:
                flash("Failed to upload image. Please try again.", "error")
                return redirect(url_for('main.index'))
            
            # Collect text from the form
            top_text = form.top_text.data or ""
            bottom_text = form.bottom_text.data or ""
            additional_text = form.additional_text.data or ""
            
            # Combine all text parts with pipe separator for API
            caption = "|".join(filter(None, [top_text, bottom_text, additional_text]))
            
            try:
                # Call the meme generation API
                api_url = request.host_url.rstrip('/') + get_api_url()
                
                payload = {
                    'image_url': image_url,
                    'caption': caption
                }
                
                response = requests.post(api_url, data=payload, timeout=30)
                
                if response.status_code == 200:
                    # Create user_response_meme directory if it doesn't exist
                    user_response_dir = Path(__file__).parent.parent / "data" / "user_response_meme"
                    user_response_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Try to parse JSON response to get template info
                    try:
                        content_type = response.headers.get('Content-Type', '')
                        if 'application/json' in content_type:
                            resp_data = response.json()
                            is_from_template = resp_data.get('from_template', False)
                            session['from_template'] = 'true' if is_from_template else 'false'
                            session['similarity_score'] = resp_data.get('similarity_score', 0)
                            logger.info(f"Meme source info: from_template={session['from_template']}, similarity={session['similarity_score']}")
                        else:
                            # Not a JSON response, use default values
                            session['from_template'] = 'false'
                            session['similarity_score'] = 0
                            logger.info("Response is not JSON, setting default values")
                    except Exception as e:
                        # Error parsing JSON
                        session['from_template'] = 'false'
                        session['similarity_score'] = 0
                        logger.warning(f"Error parsing JSON response: {e}")
                    
                    # Save the generated meme
                    result_path = save_image_from_response(
                        response, 
                        str(user_response_dir)
                    )
                    
                    # Instead of using the remote URL, use the local file path for display
                    if result_path:
                        # Convert to relative path for use in templates
                        rel_path = os.path.relpath(result_path, Path(__file__).parent.parent)
                        session['last_meme_url'] = f"/{rel_path.replace(os.sep, '/')}"
                        flash("Meme generated successfully!", "success")
                    else:
                        # Fallback to response URL if local save failed
                        session['last_meme_url'] = response.url
                        flash("Meme generated successfully, but couldn't save locally.", "warning")
                else:
                    flash(f"Error generating meme: {response.text}", "error")
            
            except Exception as e:
                logger.error(f"Error calling meme API: {e}")
                flash(f"Error: {str(e)}", "error")
        else:
            flash("Please upload an image to generate a meme.", "warning")
            
        return redirect(url_for('main.index'))
    
    return render_template('index.html', form=form, last_meme_url=session.get('last_meme_url'))

@main.route('/chat', methods=['GET', 'POST'])
def chat():
    """Render chat interface."""
    form = ChatForm()
    
    # Initialize chat history in session if not present
    if 'chat_history' not in session:
        session['chat_history'] = []
    
    if form.validate_on_submit():
        message = form.message.data
        image_url = None
        original_path = None
        
        # Handle image upload
        if form.image.data:
            # Get the uploaded file
            uploaded_file = form.image.data
            
            # Create a safe filename
            filename = werkzeug.utils.secure_filename(uploaded_file.filename)
            
            # Create user_query_meme directory if it doesn't exist
            user_query_dir = Path(__file__).parent.parent / "data" / "user_query_meme"
            user_query_dir.mkdir(parents=True, exist_ok=True)
            
            # Save the file with a unique name
            unique_filename = f"{int(datetime.now().timestamp())}_{filename}"
            original_path = user_query_dir / unique_filename
            uploaded_file.save(original_path)
            
            logger.info(f"Saved original image to {original_path}")
            
            # Upload to S3 and get URL
            image_url = upload_image_to_s3(original_path)
            
            if not image_url:
                flash("Failed to upload image. Please try again.", "error")
                return redirect(url_for('main.chat'))
        
        # Add message to chat history
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        chat_message = {
            'user': True,
            'text': message,
            'image': image_url,
            'timestamp': timestamp
        }
        
        # Add user message to history
        chat_history = session.get('chat_history', [])
        chat_history.append(chat_message)
        
        # If image is present, call the meme generation API
        if image_url:
            try:
                # Use the API endpoint
                api_url = request.host_url.rstrip('/') + get_api_url()
                
                payload = {
                    'image_url': image_url,
                    'caption': message
                }
                
                response = requests.post(api_url, data=payload, timeout=30)
                
                if response.status_code == 200:
                    # Create user_response_meme directory if it doesn't exist
                    user_response_dir = Path(__file__).parent.parent / "data" / "user_response_meme"
                    user_response_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Save the generated meme
                    result_path = save_image_from_response(
                        response, 
                        str(user_response_dir)
                    )
                    
                    # Use local file path if available, otherwise use response URL
                    image_path = None
                    if result_path:
                        # Convert to relative path for use in templates
                        rel_path = os.path.relpath(result_path, Path(__file__).parent.parent)
                        image_path = f"/{rel_path.replace(os.sep, '/')}"
                    else:
                        image_path = response.url
                    
                    # Add bot response to chat history
                    meme_response = {
                        'user': False,
                        'text': "Here's your meme!",
                        'image': image_path,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    chat_history.append(meme_response)
                else:
                    # Add error response
                    error_response = {
                        'user': False,
                        'text': f"Sorry, I couldn't generate a meme. Error: {response.text}",
                        'image': None,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    chat_history.append(error_response)
                    
            except Exception as e:
                logger.error(f"Error calling meme API: {e}")
                error_response = {
                    'user': False,
                    'text': "Sorry, something went wrong when generating your meme.",
                    'image': None,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                chat_history.append(error_response)
        else:
            # Simple text response if no image
            text_response = {
                'user': False,
                'text': "Please upload an image to generate a meme!",
                'image': None,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            chat_history.append(text_response)
        
        # Update session
        session['chat_history'] = chat_history
        
        return redirect(url_for('main.chat'))
    
    return render_template('chat.html', form=form, chat_history=session.get('chat_history', []))

@main.route('/api/chat', methods=['POST'])
def api_chat():
    """API endpoint for chat messages."""
    data = request.json
    
    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400
    
    message = data['message']
    image_url = data.get('image_url')
    
    # Process the message and image here
    # This would typically involve calling your meme generator
    
    response = {
        'success': True,
        'message': 'Received your message!',
        'timestamp': datetime.now().isoformat()
    }
    
    if image_url:
        # Call the meme generation API
        try:
            # Use the API endpoint
            api_url = request.host_url.rstrip('/') + get_api_url()
            
            payload = {
                'image_url': image_url,
                'caption': message
            }
            
            meme_response = requests.post(api_url, data=payload, timeout=30)
            
            if meme_response.status_code == 200:
                # Create user_response_meme directory if it doesn't exist
                user_response_dir = Path(__file__).parent.parent / "data" / "user_response_meme"
                user_response_dir.mkdir(parents=True, exist_ok=True)
                
                # Save the generated meme
                result_path = save_image_from_response(
                    meme_response, 
                    str(user_response_dir)
                )
                
                if result_path:
                    # Convert to relative path for use in API response
                    rel_path = os.path.relpath(result_path, Path(__file__).parent.parent)
                    response['meme_url'] = f"/{rel_path.replace(os.sep, '/')}"
                else:
                    response['meme_url'] = meme_response.url
            else:
                response['error'] = f"Failed to generate meme: {meme_response.text}"
                
        except Exception as e:
            logger.error(f"Error calling meme API: {e}")
            response['error'] = str(e)
    
    return jsonify(response)

@main.route('/clear-chat', methods=['POST'])
def clear_chat():
    """Clear the chat history."""
    session.pop('chat_history', None)
    return redirect(url_for('main.chat')) 