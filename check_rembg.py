import rembg
import PIL.Image
import io
import os

def test_rembg():
    print(f"rembg version: {rembg.__version__}")
    
    # Create a small dummy image (red square)
    img = PIL.Image.new('RGB', (100, 100), color='red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    input_bytes = img_byte_arr.getvalue()
    
    print("Processing dummy image...")
    try:
        output_bytes = rembg.remove(input_bytes)
        print(f"Success! Output size: {len(output_bytes)} bytes")
        return True
    except Exception as e:
        print(f"Failed: {e}")
        return False

if __name__ == "__main__":
    test_rembg()
