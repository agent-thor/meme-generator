#!/usr/bin/env python3
"""
Script to search for similar images in the vector database.
Takes an image file path as input and returns the top 5 similar images with their similarity scores.
"""

import argparse
import os
import sys
from pathlib import Path
import glob
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Add parent directory to path to import ai_services
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
sys.path.append(str(project_root))

from ai_services.image_vector_db import ImageVectorDB

def search_similar_images(image_path, k=5, threshold=0.1):
    """
    Search for similar images in the vector database
    
    Args:
        image_path: Path to the query image
        k: Number of top results to return
        threshold: Minimum similarity score to include
        
    Returns:
        List of (image_path, similarity_score) tuples
    """
    # Initialize the vector database
    db = ImageVectorDB()
    
    # Get database stats
    stats = db.get_database_stats()
    logger.info(f"Vector database has {stats['total_images']} images")
    
    if stats['total_images'] == 0:
        logger.error("Vector database is empty. Run build_vector_db.py first.")
        return []
    
    # Check if the image exists
    if not os.path.exists(image_path):
        logger.error(f"Image file '{image_path}' not found")
        return []
    
    # Get the top k similar images
    results = db.search_top_k(image_path, k=k, threshold=threshold)
    
    return results

def format_path_for_display(path, project_root):
    """Format path for nicer display"""
    try:
        # Try to make path relative to project root
        rel_path = os.path.relpath(path, str(project_root))
        # If path is outside project, use full path
        if rel_path.startswith('..'):
            return path
        return rel_path
    except:
        # If any error, return original path
        return path

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Search for similar images in the vector database')
    parser.add_argument('image_path', type=str, help='Path to the query image')
    parser.add_argument('--k', type=int, default=5, help='Number of top results to return (default: 5)')
    parser.add_argument('--threshold', type=float, default=0.1, help='Minimum similarity score (default: 0.1)')
    parser.add_argument('--stats', action='store_true', help='Display vector database statistics')
    
    args = parser.parse_args()
    
    # If stats flag is provided, just show stats and exit
    if args.stats:
        db = ImageVectorDB()
        stats = db.get_database_stats()
        print("\nVector Database Statistics:")
        print("-" * 80)
        print(f"Total images: {stats['total_images']}")
        print(f"Database path: {stats['database_path']}")
        
        if stats['unique_directories']:
            print("\nDirectories containing images:")
            for i, directory in enumerate(sorted(stats['unique_directories']), 1):
                print(f"{i:2}. {directory}")
        return
    
    # Search for similar images
    image_path = args.image_path
    # If relative path is provided, make it absolute
    if not os.path.isabs(image_path):
        image_path = os.path.join(os.getcwd(), image_path)
    
    results = search_similar_images(image_path, k=args.k, threshold=args.threshold)
    
    # Print the results
    if results:
        print(f"\nTop {len(results)} similar images for '{os.path.basename(args.image_path)}':")
        print("-" * 80)
        print(f"{'Rank':<6}{'Similarity':<12}{'Image Path'}")
        print("-" * 80)
        
        for i, (image_path, similarity) in enumerate(results, 1):
            # Format path for display
            display_path = format_path_for_display(image_path, project_root)
            print(f"{i:<6}{similarity:.4f}      {display_path}")
            
        print("\nTo generate a meme with one of these templates:")
        print(f"python -m webapp.app --template data/meme_templates/TEMPLATE_NAME --text \"Your text here\"")
    else:
        print(f"No similar template images found for {args.image_path}.")
        print("Try running: python scripts/build_vector_db.py")
        print("to build the vector database with your meme templates.")

if __name__ == "__main__":
    main() 