import os
import numpy as np
from PIL import Image
import imageio
import pyopencl as cl

class CubemapStitcher:
    def __init__(self, face_size=1024):
        self.face_size = face_size
        self.face_names = ["forward", "right", "back", "left", "up", "down"]
        
        # OpenCL setup
        try:
            self.ctx = cl.create_some_context(interactive=False)
            self.queue = cl.CommandQueue(self.ctx)
        except:
            self.ctx = None

    def stitch_cross(self, faces, output_path):
        """Creates a 3x4 horizontal cross layout for CS2."""
        # CS2 format: every face flipped horizontally
        flipped_faces = [np.fliplr(f) for f in faces]
        
        cross_img = np.zeros((self.face_size * 3, self.face_size * 4, 3), dtype=np.uint8)
        
        # Row 0
        cross_img[0:self.face_size, self.face_size:self.face_size*2] = flipped_faces[4] # Up
        # Row 1
        cross_img[self.face_size:self.face_size*2, 0:self.face_size] = flipped_faces[3] # Left
        cross_img[self.face_size:self.face_size*2, self.face_size:self.face_size*2] = flipped_faces[0] # Forward
        cross_img[self.face_size:self.face_size*2, self.face_size*2:self.face_size*3] = flipped_faces[1] # Right
        cross_img[self.face_size:self.face_size*2, self.face_size*3:self.face_size*4] = flipped_faces[2] # Back
        # Row 2
        cross_img[self.face_size*2:self.face_size*3, self.face_size:self.face_size*2] = flipped_faces[5] # Down
        
        # Save as EXR (normalized float32)
        cross_float = cross_img.astype(np.float32) / 255.0
        imageio.imwrite(output_path, cross_float)
        return output_path

    def stitch_equirectangular(self, faces, output_path, out_w=4096, out_h=2048):
        """Creates an equirectangular panorama using OpenCL."""
        if not self.ctx:
            return None
            
        kernel_code = """
        __kernel void equi_to_cube(
            __global const uchar* faces,
            __global uchar* output,
            const int face_size,
            const int out_w,
            const int out_h
        ) {
            int i = get_global_id(0); // x
            int j = get_global_id(1); // y
            
            if (i >= out_w || j >= out_h) return;
            
            float phi = (float)i / out_w * 2.0f * 3.14159265f - 3.14159265f;
            float theta = (float)j / out_h * 3.14159265f;
            
            float vx = sin(theta) * sin(phi);
            float vy = cos(theta);
            float vz = sin(theta) * cos(phi);
            
            float ax = fabs(vx);
            float ay = fabs(vy);
            float az = fabs(vz);
            
            int face_idx = 0;
            float u = 0, v = 0;
            
            if (ax >= ay && ax >= az) {
                if (vx > 0) { face_idx = 1; u = -vz/ax; v = -vy/ax; } // Right
                else { face_idx = 3; u = vz/ax; v = -vy/ax; }       // Left
            } else if (ay >= ax && ay >= az) {
                if (vy > 0) { face_idx = 4; u = vx/ay; v = vz/ay; }  // Up
                else { face_idx = 5; u = vx/ay; v = -vz/ay; }       // Down
            } else {
                if (vz > 0) { face_idx = 0; u = vx/az; v = -vy/az; } // Forward
                else { face_idx = 2; u = -vx/az; v = -vy/az; }      // Back
            }
            
            int tx = (int)((u + 1.0f) * 0.5f * face_size);
            int ty = (int)((v + 1.0f) * 0.5f * face_size);
            
            tx = clamp(tx, 0, face_size - 1);
            ty = clamp(ty, 0, face_size - 1);
            
            int out_idx = (j * out_w + i) * 3;
            int in_idx = (face_idx * face_size * face_size + ty * face_size + tx) * 3;
            
            output[out_idx] = faces[in_idx];
            output[out_idx+1] = faces[in_idx+1];
            output[out_idx+2] = faces[in_idx+2];
        }
        """
        prg = cl.Program(self.ctx, kernel_code).build()
        
        mf = cl.mem_flags
        faces_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=faces)
        dest_buf = cl.Buffer(self.ctx, mf.WRITE_ONLY, out_w * out_h * 3)
        
        prg.equi_to_cube(self.queue, (out_w, out_h), None, 
                         faces_buf, dest_buf, np.int32(self.face_size), 
                         np.int32(out_w), np.int32(out_h))
        
        output = np.empty((out_h, out_w, 3), dtype=np.uint8)
        cl.enqueue_copy(self.queue, output, dest_buf)
        
        Image.fromarray(output).save(output_path, quality=95)
        return output_path
