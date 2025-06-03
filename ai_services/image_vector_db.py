import numpy as np
from PIL import Image
from pathlib import Path
import os
from transformers import CLIPProcessor, CLIPModel
import torch
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

class ImageVectorDB:
    def __init__(self, db_path="data/image_vectors.npz"):
        self.db_path = Path(db_path)
        self.embeddings = []
        self.image_paths = []
        self._load()
        
        # Initialize CLIP model with GPU support if available
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")
        
        self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch16").to(self.device)
        self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch16")
        
        # Set model to evaluation mode for better performance
        self.clip_model.eval()
        
        # Enable optimizations
        if self.device == "cuda":
            # Enable mixed precision for faster inference
            self.clip_model = self.clip_model.half()
            logger.info("Enabled half-precision for GPU acceleration")

    def _load(self):
        if self.db_path.exists():
            try:
                data = np.load(self.db_path, allow_pickle=True)
                self.embeddings = list(data["embeddings"])
                self.image_paths = list(data["image_paths"])
                logger.info(f"Loaded vector database with {len(self.image_paths)} images from {self.db_path}")
            except Exception as e:
                logger.error(f"Error loading vector database: {e}")
                self.embeddings = []
                self.image_paths = []
        else:
            logger.warning(f"Vector database file {self.db_path} does not exist")
            self.embeddings = []
            self.image_paths = []

    def _save(self):
        try:
            # Ensure directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            np.savez(self.db_path, embeddings=np.array(self.embeddings), image_paths=np.array(self.image_paths))
            logger.info(f"Saved vector database with {len(self.image_paths)} images to {self.db_path}")
        except Exception as e:
            logger.error(f"Error saving vector database: {e}")

    @lru_cache(maxsize=128)
    def get_image_embedding(self, image_path):
        """Get image embedding with caching for better performance."""
        try:
            # Load and preprocess image
            image = Image.open(image_path).convert("RGB")
            
            # Resize image for faster processing if it's too large
            max_size = 512
            if max(image.size) > max_size:
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            inputs = self.clip_processor(images=image, return_tensors="pt")
            
            # Move inputs to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Use half precision if on GPU
            if self.device == "cuda":
                inputs = {k: v.half() if v.dtype == torch.float32 else v for k, v in inputs.items()}
            
            with torch.no_grad():
                embedding = self.clip_model.get_image_features(**inputs)
            
            embedding = embedding.cpu().numpy().flatten()
            # Normalize for cosine similarity
            embedding = embedding / np.linalg.norm(embedding)
            return embedding
        except Exception as e:
            logger.error(f"Error getting image embedding for {image_path}: {e}")
            raise

    def add_image(self, image_path):
        """Add image to vector database with optimizations."""
        try:
            # Check if image already exists
            if str(image_path) in self.image_paths:
                logger.info(f"Image {image_path} already in database")
                return True
                
            embedding = self.get_image_embedding(image_path)
            self.embeddings.append(embedding)
            self.image_paths.append(str(image_path))
            self._save()
            logger.info(f"Added image {image_path} to vector database")
            return True
        except Exception as e:
            logger.error(f"Error adding image {image_path} to vector database: {e}")
            return False

    def search(self, image_path, threshold=0.8):
        """Fast similarity search with optimizations."""
        if not self.embeddings:
            return None, 0.0
            
        query_emb = self.get_image_embedding(image_path)
        
        # Use numpy for faster computation
        embeddings_array = np.stack(self.embeddings)
        similarities = np.dot(embeddings_array, query_emb)
        
        idx = np.argmax(similarities)
        max_sim = similarities[idx]
        
        if max_sim >= threshold:
            return self.image_paths[idx], max_sim
        return None, max_sim

    def search_top_k(self, image_path, k=5, threshold=0.0):
        """
        Optimized search for the top-k most similar images.
        
        Args:
            image_path: Path to the query image
            k: Number of top results to return (default: 5)
            threshold: Minimum similarity score to include in results (default: 0.0)
            
        Returns:
            List of (image_path, similarity_score) tuples, sorted by similarity (highest first)
        """
        if not self.embeddings or k <= 0:
            logger.warning("No embeddings in database or invalid k value")
            return []
            
        try:
            # Get embedding for query image
            query_emb = self.get_image_embedding(image_path)
            
            # Calculate similarity with all embeddings using vectorized operations
            embeddings_array = np.stack(self.embeddings)
            similarities = np.dot(embeddings_array, query_emb)
            
            # Get indices of top-k results efficiently
            if len(similarities) <= k:
                top_indices = np.argsort(similarities)[::-1]
            else:
                # Use argpartition for better performance with large datasets
                top_indices = np.argpartition(similarities, -k)[-k:]
                top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]
            
            # Return top-k paths and scores, filtered by threshold
            results = []
            for idx in top_indices:
                sim_score = similarities[idx]
                if sim_score >= threshold:
                    # Normalize the path to use consistent directory separators
                    path = self.image_paths[idx]
                    norm_path = os.path.normpath(path)
                    results.append((norm_path, sim_score))
            
            logger.info(f"Found {len(results)} similar images with scores >= {threshold}")
            return results
        except Exception as e:
            logger.error(f"Error searching for similar images: {e}")
            return []
    
    def get_database_stats(self):
        """
        Get statistics about the vector database
        
        Returns:
            Dictionary with database statistics
        """
        stats = {
            "total_images": len(self.image_paths),
            "database_exists": self.db_path.exists(),
            "database_path": str(self.db_path),
        }
        
        # Get unique directories
        if self.image_paths:
            dirs = set()
            for path in self.image_paths:
                try:
                    dirs.add(os.path.dirname(path))
                except:
                    pass
            stats["unique_directories"] = list(dirs)
        else:
            stats["unique_directories"] = []
            
        return stats 