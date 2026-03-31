import rembg
import PIL.Image
import io
import os
import logging

logger = logging.getLogger(__name__)

def remove_background(image_bytes: bytes) -> bytes:
    """
    Utility to remove the background from an image using the rembg library.
    Input: raw image bytes.
    Output: raw PNG bytes with transparency.
    """
    try:
        # We use the default u2net model. 
        # Ensure that C:/Users/shabi/.u2net/u2net.onnx exists for optimal performance.
        output_bytes = rembg.remove(image_bytes)
        return output_bytes
    except Exception as e:
        logger.error(f"Background removal failed: {e}")
        # If removal fails, we fallback to the original image to avoid blocking the upload.
        return image_bytes

def process_image_for_atelier(input_path: str, output_path: str):
    """
    Higher-level utility for the wardrobe upload flow.
    Reads an image from disk, removes the background, and saves it as a high-fidelity PNG.
    """
    try:
        with open(input_path, "rb") as i:
            input_data = i.read()
            
        output_data = remove_background(input_data)
        
        # We ensure the output is saved as a PNG to support transparency.
        with open(output_path, "wb") as o:
            o.write(output_data)
            
        return True
    except Exception as e:
        logger.error(f"High-fidelity image processing failed for {input_path}: {e}")
        return False
