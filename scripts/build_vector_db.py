import os
from pathlib import Path
import sys
import logging
import shutil

# Add parent directory to sys.path to allow importing from other modules
sys.path.append(str(Path(__file__).parent.parent))
from ai_services.image_vector_db import ImageVectorDB
from ai_services.meme_service import MemeService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def build_vector_db(image_folder="data/meme_templates", db_path="data/image_vectors.npz", clean_images=False):
    """
    Build a vector database from images in the specified folder.
    
    Args:
        image_folder: Path to folder containing template images
        db_path: Path to save the vector DB
        clean_images: Whether to clean text from images before adding to DB (default: False)
    """
    # Clear existing database by creating a new one
    logger.info(f"Creating a new vector database at {db_path}")
    if os.path.exists(db_path):
        os.remove(db_path)
    
    vector_db = ImageVectorDB(db_path=db_path)
    meme_service = MemeService() if clean_images else None
    
    # Get absolute paths
    project_root = Path(__file__).parent.parent
    image_folder = project_root / image_folder
    cleaned_folder = project_root / "data" / "cleaned_templates"
    
    # Ensure cleaned templates directory exists
    if clean_images:
        if cleaned_folder.exists():
            logger.info(f"Clearing existing cleaned templates directory: {cleaned_folder}")
            shutil.rmtree(cleaned_folder)
        cleaned_folder.mkdir(parents=True, exist_ok=True)
    
    # Find all image files
    image_files = []
    for ext in ['.jpg', '.jpeg', '.png']:
        image_files.extend(list(image_folder.glob(f"*{ext}")))
    
    logger.info(f"Found {len(image_files)} images in {image_folder}")
    logger.info(f"Using original images (without text cleaning)")
    
    for i, img_path in enumerate(image_files):
        try:
            logger.info(f"Processing [{i+1}/{len(image_files)}] {img_path}")
            
            # Always store the original path in the vector DB
            original_path = str(img_path)
            
            # If cleaning images, clean text first
            if clean_images:
                cleaned_filename = f"cleaned_{img_path.name}"
                cleaned_path = cleaned_folder / cleaned_filename
                
                logger.info(f"  Cleaning text from {img_path.name}")
                try:
                    meme_service.remove_text_and_inpaint(
                        str(img_path), 
                        min_confidence=0.5,
                        output_path=str(cleaned_path)
                    )
                    
                    # Get embedding from cleaned image but store original path
                    embedding = vector_db.get_image_embedding(str(cleaned_path))
                    vector_db.embeddings.append(embedding)
                    vector_db.image_paths.append(original_path)
                    logger.info(f"  Added to vector DB: {img_path.name} (using cleaned version)")
                except Exception as e:
                    logger.warning(f"  Cleaning failed for {img_path.name}: {e}")
                    logger.info(f"  Falling back to original image")
                    
                    # Add original image embedding with original path
                    embedding = vector_db.get_image_embedding(original_path)
                    vector_db.embeddings.append(embedding)
                    vector_db.image_paths.append(original_path)
                    logger.info(f"  Added to vector DB: {img_path.name} (using original)")
            else:
                # Add original image embedding with original path
                embedding = vector_db.get_image_embedding(original_path)
                vector_db.embeddings.append(embedding)
                vector_db.image_paths.append(original_path)
                logger.info(f"  Added to vector DB: {img_path.name}")
            
        except Exception as e:
            logger.error(f"Error processing {img_path}: {e}")
    
    # Save the database
    vector_db._save()
    logger.info(f"Vector DB built with {len(vector_db.image_paths)} images and saved to {db_path}")
    logger.info("To search for similar images, use: python scripts/sim_search.py path/to/image.jpg")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build a vector database of meme templates")
    parser.add_argument("--folder", default="data/meme_templates", help="Path to folder containing template images")
    parser.add_argument("--db-path", default="data/image_vectors.npz", help="Path to save the vector DB")
    parser.add_argument("--clean", action="store_true", help="Enable text cleaning (disabled by default)")
    
    args = parser.parse_args()
    build_vector_db(args.folder, args.db_path, args.clean) 