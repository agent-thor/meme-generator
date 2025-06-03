# MemeZap Backend - AI-Powered Meme Generator

A powerful meme generation platform with both Twitter bot and web interface capabilities, featuring **OpenAI Vision API integration** for smart text placement and template matching from 2200+ meme templates.

## 🚀 Key Features

### 🤖 OpenAI Vision API Integration
- **Smart Text Placement**: AI analyzes image content to place text optimally
- **Context-Aware Positioning**: Avoids covering main subjects and characters
- **Intelligent Font Sizing**: Resolution-aware text sizing for perfect readability
- **Professional Layout**: Traditional meme positioning with AI precision

### 🎯 Advanced Processing Modes
- **Template Matching**: 2200+ meme templates with 80% similarity threshold
- **OCR Text Detection**: EasyOCR for precise text region identification
- **White Box Generation**: Classic meme style for original images
- **Fallback Systems**: Multiple processing modes for reliability

## Project Structure

```
memezap-backend/
├── bot/                    # Twitter bot (V1)
├── webapp/                 # Web interface for meme creation
├── ai_services/            # AI + ML related components
│   ├── meme_service.py     # Main processing engine with OpenAI integration
│   └── image_vector_db.py  # Template matching and similarity search
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
# OpenAI API Key (Required for AI text placement)
OPENAI_API_KEY=your_openai_api_key

# Project Base Path
PROJECT_BASE_PATH=/path/to/your/project

# Twitter API Keys
TWITTER_CONSUMER_KEY=your_twitter_consumer_key
TWITTER_CONSUMER_SECRET=your_twitter_consumer_secret
TWITTER_ACCESS_TOKEN=your_twitter_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret

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

## 🧠 Advanced AI Processing

### 🎨 Processing Workflow

#### Case 1: Template Found + Text Detected
1. **Template Selection**: Finds best matching template (≥80% similarity)
2. **OCR Detection**: Scans original image for existing text regions
3. **Bounding Box Extraction**: Identifies bounding boxes around detected text
4. **Template Application**: Applies new text to template using detected bounding box positions
5. **Text Replacement**: Places caption parts at corresponding positions on template

#### Case 2: Template Found + No Text Detected
1. **Template Selection**: Uses matched template from database
2. **OCR Analysis**: No text regions detected in original image
3. **OpenAI Vision API**: Analyzes template image to generate optimal bounding boxes
4. **Smart Placement**: AI creates bounding boxes avoiding main subjects
5. **Resolution-Aware Sizing**: Font sizes calculated based on template dimensions
6. **Direct Application**: Text applied to template using AI-generated positions

#### Case 3: No Template Found
1. **Original Image Processing**: No similar template found in database
2. **White Box Generation**: Adds white boxes at top and/or bottom of original image
3. **Text Sizing**: Boxes are sized to fit the input text appropriately
4. **Text Rendering**: User's text is rendered inside these white boxes
5. **Classic Meme Style**: Traditional meme format with white text boxes

### 🤖 When OpenAI Vision API is Used

**OpenAI Vision API is ONLY used when:**
- ✅ A template is found (≥80% similarity)
- ✅ AND no text is detected in the original image
- ✅ The system analyzes the template image to generate smart bounding boxes

**OpenAI Vision API is NOT used when:**
- ❌ No template is found (uses white boxes instead)
- ❌ Text is detected in original image (uses OCR bounding boxes instead)
- ❌ Processing original images without template matching

### 📏 Resolution-Aware Text Sizing

**Strict Font Size Rules:**
- **Under 500px width**: 15-25px font size MAX
- **500-800px width**: 20-35px font size MAX  
- **800-1200px width**: 25-45px font size MAX
- **Over 1200px width**: 30-55px font size MAX

**Additional Constraints:**
- Text height: NEVER exceeds 8% of image height
- Text width: NEVER exceeds 85% of image width
- Bounding box height: 6-10% of image height maximum
- Conservative sizing: Prioritizes readability over large text

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

## 🎯 Processing Pipeline

### Primary Workflow (Template Found)
```
Image Upload → Template Similarity Search → 
├─ Text Detected: OCR Bounding Box Extraction → Text Placement on Template
└─ No Text: OpenAI Vision Analysis → AI Bounding Box Generation → Text Placement on Template
```

### Fallback Workflow (No Template)
```
Image Upload → No Template Match → 
White Box Generation → Text Rendering in Boxes → Original Image + White Boxes Output
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

## 🔧 Technical Features

### AI-Powered Processing
- **OpenAI Vision API**: GPT-4o model with vision capabilities for smart text placement
- **Computer Vision**: Advanced feature extraction for template matching
- **OCR Technology**: EasyOCR for precise text detection and merging
- **Inpainting Algorithms**: TELEA method for seamless text removal

### Smart Text Management
- **Text Region Merging**: Combines nearby text regions into major areas
- **Confidence Filtering**: Only processes text with >50% detection confidence
- **Dynamic Font Sizing**: Resolution-aware sizing with strict constraints
- **Outline Rendering**: High-contrast text with customizable outlines

### Quality Assurance
- **Aspect Ratio Preservation**: Maintains original image proportions
- **Edge Detection**: AI avoids placing text over important image elements
- **Conservative Sizing**: Ensures text remains readable and professional
- **Fallback Systems**: Multiple processing modes for reliability

## API Endpoints

### `/api/smart_generate` - Advanced Meme Generation
- **Method**: POST
- **Features**: Template matching with AI placement
- **Processing**: OCR detection → OpenAI Vision API fallback → White box fallback
- **Response**: Generated meme with optimal text placement

### `/api/generate` - Traditional Meme Generation
- **Method**: POST
- **Features**: Basic meme generation with OCR
- **Processing**: Text detection and replacement
- **Response**: Generated meme with detected text regions

Both endpoints support resolution-aware text sizing and multiple processing modes.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License

## How It Works

### Detailed Workflow

```
User Uploads Image
        |
        v
Upload to S3 & Download Locally
        |
        v
Template Similarity Search (Vector DB)
        |
   +----+----+
   |         |
[Template Found ≥80%]   [No Template Match]
   |         |
   v         |
OCR Text Detection      |
   |         |
+--+--+      |
|     |      |
[Text Found] [No Text]  |
|     |      |
v     v      v
Use   OpenAI White Box
OCR   Vision Generation
Boxes API    |
|     |      |
+-----+------+
        |
        v
Apply Text to Template/Image
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

3. **Template Similarity Search**
    - The image is passed to the vector database (`ImageVectorDB`).
    - The vector DB computes the image embedding (using CLIP) and searches for the most similar image among your pre-indexed meme templates.
    - If a match is found with **similarity ≥ 80%**, the template path is returned.

4. **Intelligent Processing Logic**
    - **If template found:**
        - **First**: OCR scans original image for text regions
        - **If text detected**: Use OCR bounding boxes on template
        - **If no text detected**: Use OpenAI Vision API on template for smart bounding boxes
    - **If no template found:**
        - Generate white boxes at top/bottom of original image
        - Render user text inside these boxes

5. **Text Application**
    - **Template mode**: Apply text to template using detected or AI-generated bounding boxes
    - **Original mode**: Render text in white boxes on original image
    - **Font sizing**: Resolution-aware sizing with conservative constraints

6. **Return/Display the Meme**
    - The generated meme image is saved in `data/generated_memes/`.
    - The path or URL to the meme is returned to the user (or displayed in the web interface).

---

### Utility Scripts

- **Vector DB Build Script (`scripts/build_vector_db.py`):**
    - Run this script to precompute and store embeddings for all your meme templates (e.g., in `data/meme_templates/`).
    - This ensures fast and accurate similarity search at runtime.

- **Text Detection and Processing:**
    - The `MemeService` class handles all text detection, removal, and placement operations.
    - Supports both OCR-based and AI-generated bounding box workflows.

---

*MemeZap Backend combines cutting-edge AI with robust processing pipelines to deliver professional-quality meme generation. Now powered by OpenAI Vision API for the smartest text placement available.* 🎯