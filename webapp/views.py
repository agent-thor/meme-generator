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
import aiohttp
import aiofiles

from .forms import MemeForm, ChatForm
from utils import upload_image_to_s3, upload_image_to_s3_async
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

async def save_image_from_response(response, directory):
    """
    Save image from response to specified directory
    
    Args:
        response: Response object from requests
        directory: Directory to save image to
        
    Returns:
        Path to saved image
    """
    try:
        # Create directory if it doesn't exist
        Path(directory).mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        timestamp = int(datetime.now().timestamp())
        filename = f"meme_{timestamp}.jpg"
        save_path = os.path.join(directory, filename)
        
        # Save image content
        content = await response.read() if hasattr(response, 'read') else response.content
        
        async with aiofiles.open(save_path, 'wb') as f:
            await f.write(content)
        
        logger.info(f"Saved image to {save_path}")
        return save_path
    except Exception as e:
        logger.error(f"Error saving image: {e}")
        return None

@main.route('/', methods=['GET', 'POST'])
async def index():
    """Render the main page with meme generator form."""
    form = MemeForm()
    
    if request.method == 'POST':
        # Get form data
        form_data = await request.form
        
        # Check if an image was uploaded
        files = await request.files
        if 'image' in files:
            uploaded_file = files['image']
            
            # Create a safe filename
            filename = werkzeug.utils.secure_filename(uploaded_file.filename)
            
            # Create temp directory for uploads if it doesn't exist
            user_query_dir = Path(__file__).parent.parent / "data" / "user_query_meme"
            user_query_dir.mkdir(parents=True, exist_ok=True)
            
            # Save the file temporarily with a unique name
            unique_filename = f"{int(datetime.now().timestamp())}_{filename}"
            original_path = user_query_dir / unique_filename
            
            # Read and save file
            file_data = await uploaded_file.read()
            async with aiofiles.open(original_path, 'wb') as f:
                await f.write(file_data)
            
            logger.info(f"Saved original image to {original_path}")
            
            # Upload to S3 and get URL
            image_url = await upload_image_to_s3_async(original_path)
            
            if not image_url:
                await flash("Failed to upload image. Please try again.", "error")
                return redirect(url_for('main.index'))
            
            # Collect text from the form
            top_text = form_data.get('top_text', '')
            bottom_text = form_data.get('bottom_text', '')
            additional_text = form_data.get('additional_text', '')
            
            # Combine all text parts with pipe separator for API
            caption = "|".join(filter(None, [top_text, bottom_text, additional_text]))
            
            try:
                # Call the meme generation API
                api_url = request.host_url.rstrip('/') + get_api_url()
                
                payload = {
                    'image_url': image_url,
                    'caption': caption
                }
                
                # Use aiohttp for async request
                async with aiohttp.ClientSession() as client:
                    async with client.post(api_url, data=payload, timeout=30) as response:
                        if response.status == 200:
                            # Create user_response_meme directory if it doesn't exist
                            user_response_dir = Path(__file__).parent.parent / "data" / "user_response_meme"
                            user_response_dir.mkdir(parents=True, exist_ok=True)
                            
                            # Try to parse JSON response to get template info
                            try:
                                content_type = response.headers.get('Content-Type', '')
                                if 'application/json' in content_type:
                                    resp_data = await response.json()
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
                            result_path = await save_image_from_response(
                                response, 
                                str(user_response_dir)
                            )
                            
                            # Instead of using the remote URL, use the local file path for display
                            if result_path:
                                # Convert to relative path for use in templates
                                rel_path = os.path.relpath(result_path, Path(__file__).parent.parent)
                                session['last_meme_url'] = f"/{rel_path.replace(os.sep, '/')}"
                                await flash("Meme generated successfully!", "success")
                            else:
                                # Fallback to response URL if local save failed
                                session['last_meme_url'] = str(response.url)
                                await flash("Meme generated successfully, but couldn't save locally.", "warning")
                        else:
                            resp_text = await response.text()
                            await flash(f"Error generating meme: {resp_text}", "error")
            
            except Exception as e:
                logger.error(f"Error calling meme API: {e}")
                await flash(f"Error: {str(e)}", "error")
        else:
            await flash("Please upload an image to generate a meme.", "warning")
            
        return redirect(url_for('main.index'))
    
    return await render_template('index.html', form=form, last_meme_url=session.get('last_meme_url'))

@main.route('/chat', methods=['GET', 'POST'])
async def chat():
    """Render chat interface."""
    form = ChatForm()
    
    # Initialize chat history in session if not present
    if 'chat_history' not in session:
        session['chat_history'] = []
    
    if request.method == 'POST':
        form_data = await request.form
        message = form_data.get('message', '')
        image_url = None
        original_path = None
        
        # Handle image upload
        files = await request.files
        if 'image' in files and files['image'].filename:
            # Get the uploaded file
            uploaded_file = files['image']
            
            # Create a safe filename
            filename = werkzeug.utils.secure_filename(uploaded_file.filename)
            
            # Create user_query_meme directory if it doesn't exist
            user_query_dir = Path(__file__).parent.parent / "data" / "user_query_meme"
            user_query_dir.mkdir(parents=True, exist_ok=True)
            
            # Save the file with a unique name
            unique_filename = f"{int(datetime.now().timestamp())}_{filename}"
            original_path = user_query_dir / unique_filename
            
            # Read and save file
            file_data = await uploaded_file.read()
            async with aiofiles.open(original_path, 'wb') as f:
                await f.write(file_data)
            
            logger.info(f"Saved original image to {original_path}")
            
            # Upload to S3 and get URL
            image_url = await upload_image_to_s3_async(original_path)
            
            if not image_url:
                await flash("Failed to upload image. Please try again.", "error")
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
                
                # Use aiohttp for async request
                async with aiohttp.ClientSession() as client:
                    async with client.post(api_url, data=payload, timeout=30) as response:
                        if response.status == 200:
                            # Create user_response_meme directory if it doesn't exist
                            user_response_dir = Path(__file__).parent.parent / "data" / "user_response_meme"
                            user_response_dir.mkdir(parents=True, exist_ok=True)
                            
                            # Save the generated meme
                            result_path = await save_image_from_response(
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
                                image_path = str(response.url)
                            
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
                            resp_text = await response.text()
                            error_response = {
                                'user': False,
                                'text': f"Sorry, I couldn't generate a meme. Error: {resp_text}",
                                'image': None,
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            chat_history.append(error_response)
                    
            except Exception as e:
                logger.error(f"Error calling meme API: {e}")
                error_response = {
                    'user': False,
                    'text': f"Sorry, I encountered an error: {str(e)}",
                    'image': None,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                chat_history.append(error_response)
        
        # Update session
        session['chat_history'] = chat_history
        
        return redirect(url_for('main.chat'))
    
    return await render_template('chat.html', form=form, chat_history=session.get('chat_history', []))

@main.route('/api/chat', methods=['POST'])
async def api_chat():
    """API endpoint for chat messages."""
    try:
        # Get JSON data
        data = await request.json
        message = data.get('message', '')
        image_url = data.get('image_url')
        
        # Initialize chat history in session if not present
        if 'chat_history' not in session:
            session['chat_history'] = []
        
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
                
                # Use aiohttp for async request
                async with aiohttp.ClientSession() as client:
                    async with client.post(api_url, data=payload, timeout=30) as response:
                        if response.status == 200:
                            # Create user_response_meme directory if it doesn't exist
                            user_response_dir = Path(__file__).parent.parent / "data" / "user_response_meme"
                            user_response_dir.mkdir(parents=True, exist_ok=True)
                            
                            # Save the generated meme
                            result_path = await save_image_from_response(
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
                                image_path = str(response.url)
                            
                            # Add bot response to chat history
                            meme_response = {
                                'user': False,
                                'text': "Here's your meme!",
                                'image': image_path,
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            chat_history.append(meme_response)
                            
                            # Update session
                            session['chat_history'] = chat_history
                            
                            return {
                                'success': True,
                                'response': meme_response
                            }
                        else:
                            # Add error response
                            resp_text = await response.text()
                            error_response = {
                                'user': False,
                                'text': f"Sorry, I couldn't generate a meme. Error: {resp_text}",
                                'image': None,
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            chat_history.append(error_response)
                            
                            # Update session
                            session['chat_history'] = chat_history
                            
                            return {
                                'success': False,
                                'error': resp_text,
                                'response': error_response
                            }
            except Exception as e:
                logger.error(f"Error calling meme API: {e}")
                error_response = {
                    'user': False,
                    'text': f"Sorry, I encountered an error: {str(e)}",
                    'image': None,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                chat_history.append(error_response)
                
                # Update session
                session['chat_history'] = chat_history
                
                return {
                    'success': False,
                    'error': str(e),
                    'response': error_response
                }
        
        # Update session
        session['chat_history'] = chat_history
        
        return {
            'success': True,
            'message': 'Message received'
        }
    except Exception as e:
        logger.error(f"Error in API chat: {e}")
        return {
            'success': False,
            'error': str(e)
        }

@main.route('/clear-chat', methods=['POST'])
async def clear_chat():
    """Clear the chat history."""
    session['chat_history'] = []
    return redirect(url_for('main.chat')) 