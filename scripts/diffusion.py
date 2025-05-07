import os
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from diffusers import AutoPipelineForInpainting
from diffusers.utils import load_image
import torch
from PIL import Image, ImageDraw
import logging
from ai_services.meme_service import MemeService
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_device():
    """Set up the appropriate device for inference."""
    if torch.backends.mps.is_available():
        device = "mps"
        logger.info("Using MPS device")
    elif torch.cuda.is_available():
        device = "cuda"
        logger.info("Using CUDA device")
    else:
        device = "cpu"
        logger.info("Using CPU device")
    return device

def create_output_dir():
    """Create output directory if it doesn't exist."""
    output_dir = Path("data")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

def create_text_mask(image_path, meme_service):
    # Detect text
    text_results, _ = meme_service.detect_text(image_path)
    # Open image to get size
    img = Image.open(image_path)
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    for bbox, _, _ in text_results:
        x_min = min([p[0] for p in bbox])
        y_min = min([p[1] for p in bbox])
        x_max = max([p[0] for p in bbox])
        y_max = max([p[1] for p in bbox])
        draw.rectangle([x_min, y_min, x_max, y_max], fill=255)
    mask_path = "data/diffuser/text_mask.png"
    mask.save(mask_path)
    return mask_path

def main():
    # Set up device
    device = setup_device()
    
    # Create output directory
    output_dir = create_output_dir()
    
    # Initialize the pipeline
    logger.info("Loading diffusion model...")
    pipe = AutoPipelineForInpainting.from_pretrained(
        "diffusers/stable-diffusion-xl-1.0-inpainting-0.1",
        torch_dtype=torch.float16 if device != "cpu" else torch.float32,
        variant="fp16" if device != "cpu" else None
    ).to(device)
    
    # Load example image and mask
    logger.info("Loading example image and mask...")
    meme_service = MemeService()
    image_path = "/Users/krishnayadav/Documents/forgex/meme/Screenshot 2025-05-05 at 3.48.47 PM.png"
    mask_path = create_text_mask(image_path, meme_service)
    
    image = Image.open(image_path)
    mask_image = Image.open(mask_path).resize(image.size)
    
    # Save original image and mask
    image.save(output_dir / "original_image.png")
    mask_image.save(output_dir / "mask_image.png")
    
    # Generate image
    logger.info("Generating image...")
    prompt = "background"  # or something more specific
    generator = torch.Generator(device=device).manual_seed(0)
    
    target_size = (1024, 1024)
    image = image.resize(target_size).convert("RGB")
    mask_image = mask_image.resize(target_size).convert("L")
    
    mask_np = np.array(mask_image)
    
    result = pipe(
        prompt=prompt,
        image=image,
        mask_image=mask_image,
        guidance_scale=8.0,
        num_inference_steps=20,
        strength=0.99,
        generator=generator,
    ).images[0]
    
    # Save the generated image
    output_path = output_dir / "generated_image.png"
    result.save(output_path)
    logger.info(f"Generated image saved to {output_path}")

if __name__ == "__main__":
    main()
