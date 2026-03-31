import sys
import os

# Add the project root to the path so we can import the app
sys.path.append(os.getcwd())

try:
    from app.utils.image_processing import remove_background
    import PIL.Image
    import io
    print("Integration Check: SUCCESS - Module imported.")
    
    # Check for the model file
    model_path = os.path.expanduser("~/.u2net/u2net.onnx")
    if os.path.exists(model_path):
        print(f"Model Check: SUCCESS - Found at {model_path}")
    else:
        print(f"Model Check: FAILED - Could not find model at {model_path}")
        print("Please ensure you placed u2net.onnx in C:\\Users\\shabi\\.u2net\\")

    # Test processing
    print("\nTesting background removal on a dummy image...")
    img = PIL.Image.new('RGB', (100, 100), color='blue')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    
    output = remove_background(img_byte_arr.getvalue())
    if len(output) > 100:
        print("Final Status: READY - Background removal is working!")
    else:
        print("Final Status: ERROR - Model loaded but output is invalid.")

except Exception as e:
    print(f"Final Status: FAILED - {e}")
