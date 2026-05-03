import numpy as np
from PIL import Image
import os
import subprocess
import shutil

INPUT_DIR = "input"
OUTPUT_DIR = "output"

FACE_NAMES = [
    "forward", "right", "back", "left", "up", "down"
]

# Colors for each face (RGB)
COLORS = [
    (255, 0, 0),     # Red
    (0, 255, 0),     # Green
    (0, 0, 255),     # Blue
    (255, 255, 0),   # Yellow
    (255, 0, 255),   # Magenta
    (0, 255, 255)    # Cyan
]

def generate_test_images():
    print("Generating test images (16:9)...")
    if os.path.exists(INPUT_DIR):
        shutil.rmtree(INPUT_DIR)
    os.makedirs(INPUT_DIR)
        
    width = 1920
    height = 1080
    
    for i, name in enumerate(FACE_NAMES):
        # Create a solid color image with some text/pattern to verify orientation
        data = np.full((height, width, 3), COLORS[i], dtype=np.uint8)
        
        # Add a small white square in the top-left to check orientation
        data[0:100, 0:100] = (255, 255, 255)
        
        img = Image.fromarray(data)
        filename = f"cube_{i+1:03d}_{name}.jpg"
        img.save(os.path.join(INPUT_DIR, filename))
        print(f"Created: {filename}")

def run_tool():
    print("Running main.py...")
    result = subprocess.run(["python", "main.py"], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("Errors:")
        print(result.stderr)
    return result.returncode == 0

def verify_outputs():
    print("Verifying outputs...")
    cross_path = os.path.join(OUTPUT_DIR, "output_cross.jpg")
    equi_path = os.path.join(OUTPUT_DIR, "output_360.jpg")
    
    success = True
    if not os.path.exists(cross_path):
        print("FAIL: output_cross.jpg missing")
        success = False
    else:
        img = Image.open(cross_path)
        # Expected size for Horizontal Cross is (4 * 1080, 3 * 1080)
        expected_size = (4320, 3240)
        if img.size == expected_size:
            print(f"OK: output_cross.jpg found, size: {img.size}")
        else:
            print(f"FAIL: output_cross.jpg size mismatch. Got {img.size}, expected {expected_size}")
            success = False
        
    if not os.path.exists(equi_path):
        print("FAIL: output_360.jpg missing")
        success = False
    else:
        img = Image.open(equi_path)
        print(f"OK: output_360.jpg found, size: {img.size}")
        
    return success

if __name__ == "__main__":
    try:
        generate_test_images()
        if run_tool():
            if verify_outputs():
                print("\nTEST PASSED")
            else:
                print("\nTEST FAILED (Output verification)")
        else:
            print("\nTEST FAILED (Execution error)")
    except Exception as e:
        print(f"\nTEST ERROR: {e}")
