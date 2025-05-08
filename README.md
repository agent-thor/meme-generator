# Meme Generator

A powerful meme generation platform with both Twitter bot and web interface capabilities.

## Features

- Twitter bot for meme generation on demand
- Web interface for easy meme creation
- AI-powered caption generation
- Template matching and image understanding
- Support for custom templates

## Project Structure

```
memezap/
├── bot/                    # Twitter bot (V1)
├── webapp/                 # Web interface for meme creation
├── ai_services/            # AI + ML related components
├── data/                   # Meme templates and examples
├── scripts/                # Utility or setup scripts
└── tests/                  # Unit & integration tests
```

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables:
   ```bash
   # Copy the example .env file
   cp .env.example .env
   
   # Edit .env with your API keys and settings
   nano .env
   ```
4. Run the applications:
   - To run both components together (API and webapp):
     ```bash
     # In one terminal
     ./run_api.sh
     
     # In another terminal
     ./run_webapp.sh
     ```
   - OR run them individually:
     ```bash
     # For just the meme generation API
     python app.py
     
     # For just the web interface
     python webapp/app.py
     ```

## Environment Variables

The application uses environment variables for configuration. Create a `.env` file at the project root with the following variables:

```
# Twitter API Keys
TWITTER_CONSUMER_KEY=your_twitter_consumer_key
TWITTER_CONSUMER_SECRET=your_twitter_consumer_secret
TWITTER_ACCESS_TOKEN=your_twitter_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret

# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key

# AWS Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_REGION_NAME=us-east-1
AWS_S3_BUCKET=meme-generator-uploads

# Application Settings
APP_DEBUG=true
APP_HOST=0.0.0.0
APP_PORT=5000

# Web App Settings
FLASK_SECRET_KEY=change-this-to-a-secure-random-string
MEME_API_PORT=5000

# AI Settings
AI_CAPTION_MODEL=gpt-4
AI_IMAGE_MODEL=blip
AI_MAX_TOKENS=100
AI_TEMPERATURE=0.7
```

## Running the Components

### Meme Generation API

The meme generation API runs on port 5000 by default and provides endpoints for generating memes.

```bash
./run_api.sh
# or
python app.py
```

### Web Interface

The web interface runs on port 8000 by default and provides a user-friendly interface for creating memes.

```bash
./run_webapp.sh
# or
python webapp/app.py
```

## AWS S3 Configuration

For image uploading to work properly, you need to:

1. Create an S3 bucket with public read access
2. Configure CORS settings for your bucket to allow uploads from your webapp
3. Set the proper environment variables in your `.env` file

Example CORS configuration for your S3 bucket:
```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST"],
    "AllowedOrigins": ["*"],
    "ExposeHeaders": []
  }
]
```

### Testing AWS Credentials

If you're having trouble with S3 uploads, you can use the diagnostic scripts to check your AWS credentials:

```bash
# Test AWS credentials
python scripts/test_aws_credentials.py

# Test file upload to S3
python scripts/test_s3_upload.py
```

The application includes a fallback mechanism that will use local file storage if S3 uploads fail, so you can still test the application even without valid AWS credentials.

## Configuration

Edit `config.yaml` to set up:
- Twitter API credentials
- OpenAI API key
- AWS S3 credentials
- Application settings
- Path configurations
- AI model settings

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License

## How It Works

### Workflow Diagram

```
User Uploads Image
        |
        v
Upload to S3 & Download Locally
        |
        v
Remove Text (Inpaint) from Uploaded Image
        |
        v
Vector DB Similarity Search (on cleaned image)
        |
   +----+----+
   |         |
[Similarity > 80%]   [No Good Match]
   |         |
   v         v
White Box   Classic Meme
Meme        Generation
   |         |
   +----+----+
        |
        v
Return/Display Meme
```

### Working Process

1. **Image Upload**
    - User uploads an image via the web interface or API.

2. **Upload to S3 & Download Locally**
    - The image is uploaded to your S3 bucket for storage.
    - The image is then downloaded to your local server for processing.

3. **Remove Text from Uploaded Image**
    - The backend uses `MemeService.remove_text_and_inpaint` to:
      - Detect all text regions in the image (using EasyOCR).
      - For each region with confidence > 0.5, create a mask and inpaint (remove) the text.
      - Save the cleaned (text-free) image to a temporary file.

4. **Image Similarity Search**
    - The cleaned image is passed to the vector database (`ImageVectorDB`).
    - The vector DB computes the image embedding (using CLIP) and searches for the most similar image among your pre-indexed meme templates.
    - If a match is found with **similarity > 80%** (or your chosen threshold):
        - The path to the most similar image is returned.
    - If no match is found above the threshold, the process continues with the original image.

5. **Meme Generation Logic**
    - **If a similar image is found (similarity > 80%):**
        - The system uses the matched template image.
        - It adds a white box at the top and/or bottom of the image, sized to fit the input text.
        - The user's text is rendered inside these boxes.
        - The result is saved as the generated meme.
    - **If no similar image is found:**
        - The system uses the current meme generation approach:
            - Detects and removes any existing text from the uploaded image.
            - Adds the user's text in the appropriate locations (using detected regions or as classic meme text).
        - The result is saved as the generated meme.

6. **Return/Display the Meme**
    - The generated meme image is saved in `data/generated_memes/`.
    - The path or URL to the meme is returned to the user (or displayed in the web interface).

---

- **Vector DB Build Script (`scripts/build_vector_db.py`):**
    - Run this script to precompute and store embeddings for all your meme templates (e.g., in `data/meme_templates/`).
    - This ensures fast and accurate similarity search at runtime.

- **Text Removal Utility:**
    - The `remove_text_and_inpaint` method in `MemeService` can be used both during upload and when building the vector DB (if you want to store only cleaned templates).