import pyopencl as cl
import numpy as np
from PIL import Image
import os
import glob
import imageio

# --- CONFIGURATION ---
# Target size for each face (square)
FACE_SIZE = 1080 
# Equirectangular panorama dimensions
OUT_WIDTH = 4096 
OUT_HEIGHT = 2048

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(SCRIPT_DIR, "input")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")

# Standard cubemap face order
# 0: Forward (+Z), 1: Right (+X), 2: Back (-Z), 3: Left (-X), 4: Up (+Y), 5: Down (-Y)
FACE_NAMES = [
    "forward",
    "right",
    "back",
    "left",
    "up",
    "down"
]

def crop_to_square(img):
    """Crops a wide-format image to a 1:1 square from the center."""
    width, height = img.size
    if width == height:
        return img
    
    # Center crop logic
    size = min(width, height)
    left = (width - size) / 2
    top = (height - size) / 2
    right = (width + size) / 2
    bottom = (height + size) / 2
    
    return img.crop((left, top, right, bottom))

def load_faces(input_path):
    """Loads and crops 6 faces from the specified input path."""
    faces = []
    files = glob.glob(os.path.join(input_path, "*"))
    
    found_faces = {}
    for f in files:
        fname = os.path.basename(f).lower()
        for i, name in enumerate(FACE_NAMES):
            # Match by name in filename (e.g., cube_001_forward.jpg)
            if f"_{name}" in fname or name == fname.split('.')[0]:
                found_faces[i] = f
    
    # Fallback: if not all faces found by name, try order-based (001-006)
    if len(found_faces) < 6:
        for i in range(1, 7):
            matches = [f for f in files if f"_{i:03d}_" in os.path.basename(f)]
            if matches and (i-1) not in found_faces:
                found_faces[i-1] = matches[0]

    if len(found_faces) < 6:
        missing = [FACE_NAMES[i] for i in range(6) if i not in found_faces]
        raise FileNotFoundError(f"Missing faces in {input_path}: {missing}. Expected filenames like 'cube_001_forward.jpg'")

    for i in range(6):
        path = found_faces[i]
        print(f"Loading face {FACE_NAMES[i]}: {path}")
        img = Image.open(path).convert("RGB")
        img = crop_to_square(img)
        
        # Resize to consistent FACE_SIZE if needed
        # Resize to consistent FACE_SIZE if needed
        if img.size != (FACE_SIZE, FACE_SIZE):
            img = img.resize((FACE_SIZE, FACE_SIZE), Image.Resampling.LANCZOS)
        
        # Convert to numpy
        faces.append(np.array(img))
    
    return np.array(faces, dtype=np.uint8)

def create_horizontal_cross(faces, output_path):
    """Assembles 6 faces into a Horizontal Cross layout (3x4 grid)."""
    print(f"Generating Horizontal Cross for {output_path}...")
    # Layout:
    #          [4:Up]
    # [3:Left] [0:Forward] [1:Right] [2:Back]
    #          [5:Down]
    
    cross_img = np.zeros((FACE_SIZE * 3, FACE_SIZE * 4, 3), dtype=np.uint8)
    
    # Flip all faces horizontally for CS2 format before assembly
    flipped_faces = [np.fliplr(f) for f in faces]
    
    # Row 0
    cross_img[0:FACE_SIZE, FACE_SIZE:FACE_SIZE*2] = flipped_faces[4]              # Up
    
    # Row 1
    cross_img[FACE_SIZE:FACE_SIZE*2, 0:FACE_SIZE] = flipped_faces[3]              # Left
    cross_img[FACE_SIZE:FACE_SIZE*2, FACE_SIZE:FACE_SIZE*2] = flipped_faces[0]      # Forward
    cross_img[FACE_SIZE:FACE_SIZE*2, FACE_SIZE*2:FACE_SIZE*3] = flipped_faces[1]      # Right
    cross_img[FACE_SIZE:FACE_SIZE*2, FACE_SIZE*3:FACE_SIZE*4] = flipped_faces[2]      # Back
    
    # Row 2
    cross_img[FACE_SIZE*2:FACE_SIZE*3, FACE_SIZE:FACE_SIZE*2] = flipped_faces[5]      # Down
    
    out_file = os.path.join(output_path, "output_cross.exr")
    # Convert to float32 (0.0 to 1.0) for standard EXR format
    cross_float = cross_img.astype(np.float32) / 255.0
    imageio.imwrite(out_file, cross_float)
    print(f"Saved: {out_file}")

def create_equirectangular_opencl(faces, output_path):
    """Converts cubemap faces to Equirectangular projection using OpenCL."""
    print(f"Generating Equirectangular panorama for {output_path} via OpenCL...")
    
    try:
        platforms = cl.get_platforms()
        if not platforms:
            print("No OpenCL platforms found.")
            return
        
        # Select first platform and device
        ctx = cl.Context(dev_type=cl.device_type.ALL, properties=[(cl.context_properties.PLATFORM, platforms[0])])
        queue = cl.CommandQueue(ctx)
        
        out_img = np.zeros((OUT_HEIGHT, OUT_WIDTH, 3), dtype=np.uint8)
        
        mf = cl.mem_flags
        faces_buf = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=faces)
        out_buf = cl.Buffer(ctx, mf.WRITE_ONLY, out_img.nbytes)
        
        kernel_code = """
        #define M_PI_F 3.141592653589793f
        
        __kernel void equi_to_cube(
            __global const uchar *faces,
            __global uchar *out,
            const int face_size,
            const int out_width,
            const int out_height
        ) {
            int x = get_global_id(0);
            int y = get_global_id(1);
            
            if (x >= out_width || y >= out_height) return;
            
            float u = (float)x / (out_width - 1);
            float v = (float)y / (out_height - 1);
            
            float yaw = (u - 0.5f) * 2.0f * M_PI_F;
            float pitch = (0.5f - v) * M_PI_F;
            
            float dx = cos(pitch) * sin(yaw);
            float dy = sin(pitch);
            float dz = cos(pitch) * cos(yaw);
            
            float absX = fabs(dx);
            float absY = fabs(dy);
            float absZ = fabs(dz);
            
            int face_idx = 0;
            float face_u = 0.0f;
            float face_v = 0.0f;
            
            if (absX >= absY && absX >= absZ) {
                if (dx > 0.0f) { // Right
                    face_idx = 1; face_u = -dz / absX; face_v = -dy / absX;
                } else {         // Left
                    face_idx = 3; face_u = dz / absX; face_v = -dy / absX;
                }
            } else if (absY >= absX && absY >= absZ) {
                if (dy > 0.0f) { // Up
                    face_idx = 4; face_u = dx / absY; face_v = dz / absY;
                } else {         // Down
                    face_idx = 5; face_u = dx / absY; face_v = -dz / absY;
                }
            } else {
                if (dz > 0.0f) { // Forward
                    face_idx = 0; face_u = dx / absZ; face_v = -dy / absZ;
                } else {         // Back
                    face_idx = 2; face_u = -dx / absZ; face_v = -dy / absZ;
                }
            }
            
            face_u = (face_u + 1.0f) * 0.5f;
            face_v = (face_v + 1.0f) * 0.5f;
            
            int px = clamp((int)(face_u * face_size), 0, face_size - 1);
            int py = clamp((int)(face_v * face_size), 0, face_size - 1);
            
            int out_idx = (y * out_width + x) * 3;
            int in_idx = (face_idx * face_size * face_size + py * face_size + px) * 3;
            
            out[out_idx] = faces[in_idx];
            out[out_idx + 1] = faces[in_idx + 1];
            out[out_idx + 2] = faces[in_idx + 2];
        }
        """
        
        prg = cl.Program(ctx, kernel_code).build()
        
        prg.equi_to_cube(queue, (OUT_WIDTH, OUT_HEIGHT), None, 
                         faces_buf, out_buf, 
                         np.int32(FACE_SIZE), np.int32(OUT_WIDTH), np.int32(OUT_HEIGHT))
        
        cl.enqueue_copy(queue, out_img, out_buf).wait()
        
        out_path_file = os.path.join(output_path, "output_360.jpg")
        Image.fromarray(out_img).save(out_path_file, quality=95)
        print(f"Saved: {out_path_file}")
        
    except Exception as e:
        print(f"OpenCL error: {e}")

def process_folder(input_path, output_path):
    """Processes a single folder of cubemap faces."""
    if not os.path.exists(output_path):
        os.makedirs(output_path)
        
    try:
        faces_data = load_faces(input_path)
        create_horizontal_cross(faces_data, output_path)
        create_equirectangular_opencl(faces_data, output_path)
    except Exception as e:
        print(f"Failed to process {input_path}: {e}")

if __name__ == "__main__":
    # Check for subdirectories in INPUT_DIR
    subdirs = [d for d in os.listdir(INPUT_DIR) if os.path.isdir(os.path.join(INPUT_DIR, d))]
    
    if subdirs:
        print(f"Found {len(subdirs)} subdirectories in {INPUT_DIR}. Processing all...")
        for sd in subdirs:
            input_p = os.path.join(INPUT_DIR, sd)
            output_p = os.path.join(OUTPUT_DIR, sd)
            process_folder(input_p, output_p)
    else:
        # Fallback to root input directory
        process_folder(INPUT_DIR, OUTPUT_DIR)
        
    print("Processing complete.")
