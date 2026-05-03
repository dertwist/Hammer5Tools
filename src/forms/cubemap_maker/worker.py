import os
import time
import shutil
import socket
import struct
import glob
import sys
import numpy as np
from PIL import Image
from PySide6.QtCore import QThread, Signal

from src.settings.main import get_cs2_path, get_addon_name
from .stitcher import CubemapStitcher

# --- Worker ---

class CaptureWorker(QThread):
    finished = Signal(str)
    progress = Signal(str)
    error = Signal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config

    def load_local_faces(self, ss_dir, ev_suffix, session_id):
        """Loads and crops 6 faces from the specified screenshots directory."""
        face_names = ["forward", "right", "back", "left", "up", "down"]
        faces = []
        
        for name in face_names:
            pattern = os.path.join(ss_dir, f"{session_id}_cube_{ev_suffix}_{name}*.png")
            files = glob.glob(pattern)
            if not files:
                raise FileNotFoundError(f"Missing face: {name} for session {session_id}")
            
            # Get latest file
            latest = max(files, key=os.path.getctime)
            img = Image.open(latest).convert("RGB")
            
            # Center crop
            w, h = img.size
            s = min(w, h)
            img = img.crop(((w-s)//2, (h-s)//2, (w+s)//2, (h+s)//2))
            
            # Resize to consistent size
            if img.size != (self.config['res'], self.config['res']):
                img = img.resize((self.config['res'], self.config['res']), Image.Resampling.LANCZOS)
            
            faces.append(np.array(img))
            
        return np.array(faces, dtype=np.uint8)

    def run(self):
        from src.other.cs2_netcon import CS2Netcon
        cs2_root = get_cs2_path()
        if not cs2_root:
            self.error.emit("CS2 path not found in settings.")
            return

        # Query original value of r_always_render_all_windows
        original_render_all = "false"
        if CS2Netcon:
            queried = CS2Netcon.query("r_always_render_all_windows")
            if queried is not None:
                original_render_all = queried

        # 1. Verify files
        cs2_post_path = os.path.join(cs2_root, "game", "csgo", "lighting", "postprocessing", "editor")
        # Check vposts folder (Handle PyInstaller bundling)
        if getattr(sys, 'frozen', False):
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
            # Possible locations in a PyInstaller bundle
            vpost_src_dir = os.path.join(base_dir, "src", "forms", "cubemap_maker", "vposts")
            if not os.path.exists(vpost_src_dir):
                vpost_src_dir = os.path.join(os.path.dirname(__file__), "vposts")
        else:
            vpost_src_dir = os.path.join(os.path.dirname(__file__), "vposts")

        if not os.path.exists(vpost_src_dir):
            raise FileNotFoundError(f"Critical: vposts directory not found at {vpost_src_dir}")
        
        post_files = ["basic_tonemap_ev0.vpost_c", "basic_tonemap_ev1.vpost_c", "basic_tonemap_ev2.vpost_c", "basic_tonemap_evm1.vpost_c", "basic_tonemap_evm4.vpost_c"]
        
        if not os.path.exists(cs2_post_path):
            try: os.makedirs(cs2_post_path, exist_ok=True)
            except: self.error.emit(f"Cannot create CS2 post-processing folder: {cs2_post_path}"); return

        for f in post_files:
            target = os.path.join(cs2_post_path, f)
            if not os.path.exists(target):
                self.progress.emit(f"Copying {f}...")
                shutil.copy2(os.path.join(vpost_src_dir, f), target)

        # 2. Capture Loop
        ev_steps = [0]
        if self.config['hdr']: ev_steps = [0, 1, 2, -1, -4]
        x, y, z = self.config['pos']
        
        # Cleanup old screenshots to avoid using stale files
        addon_name = get_addon_name()
        possible_dirs = [
            os.path.join(cs2_root, "game", "csgo_addons", addon_name, "screenshots", "cubemap"),
            os.path.join(cs2_root, "game", "csgo", "screenshots", "cubemap")
        ]
        
        # Proactively create the cubemap directory in the most likely location
        # Usually the addon folder if it exists, otherwise the root game folder
        target_ss_dir = possible_dirs[0] if get_addon_name() != "addon" else possible_dirs[1]
        try: os.makedirs(target_ss_dir, exist_ok=True)
        except: pass

        for d in possible_dirs:
            if os.path.exists(d):
                try: shutil.rmtree(d)
                except: pass
        
        # Ensure it exists again after rmtree cleanup
        try: os.makedirs(target_ss_dir, exist_ok=True)
        except: pass

        # Use a unique session ID to avoid glob collisions with old files
        session_id = int(time.time())

        for ev in ev_steps:
            self.progress.emit(f"Capturing EV {ev}...")
            ev_suffix = f"ev{ev}" if ev >= 0 else f"evm{abs(ev)}"
            
            # Use CS2Netcon for commands
            pp_cmd = f'ent_fire post_processing_volume kill; ent_create post_processing_volume {{ model "models/dev/dev_cube.vmdl" master "1" fadetime "0.01" postprocessing "postprocess/basic_tonemap_{ev_suffix}.vpost" }}'
            CS2Netcon.send(pp_cmd)
            time.sleep(0.5)
            
            # Build command list to avoid semicolon issues in netcon
            cmds = [
                "sv_cheats 1", "noclip 1", "r_drawviewmodel 0", "cl_drawhud 0", "r_drawpanorama 0", "cl_firstperson_legs 0",
                "fov_cs_debug 106.260205", "ent_fire cmd kill", "ent_create point_servercommand {targetname cmd}",
                "screenshot_subdir screenshots\\\\cubemap",
                'ent_fire worldent addoutput "OnUser1>cmd>command>r_always_render_all_windows true>0.01>1"',
                # Forward
                f'ent_fire worldent addoutput "OnUser1>cmd>command>setpos_exact {x} {y} {z}>{1*0.5}>1"',
                f'ent_fire worldent addoutput "OnUser1>cmd>command>setang 0 0 0>{1*0.5}>1"',
                f'ent_fire worldent addoutput "OnUser1>cmd>command>screenshot_prefix {session_id}_cube_{ev_suffix}_forward>{1*0.5 + 0.1}>1"',
                f'ent_fire worldent addoutput "OnUser1>cmd>command>png_screenshot>{1*0.5 + 0.2}>1"',
                # Right
                f'ent_fire worldent addoutput "OnUser1>cmd>command>setpos_exact {x} {y} {z}>{2*0.5}>1"',
                f'ent_fire worldent addoutput "OnUser1>cmd>command>setang 0 270 0>{2*0.5}>1"',
                f'ent_fire worldent addoutput "OnUser1>cmd>command>screenshot_prefix {session_id}_cube_{ev_suffix}_right>{2*0.5 + 0.1}>1"',
                f'ent_fire worldent addoutput "OnUser1>cmd>command>png_screenshot>{2*0.5 + 0.2}>1"',
                # Back
                f'ent_fire worldent addoutput "OnUser1>cmd>command>setpos_exact {x} {y} {z}>{3*0.5}>1"',
                f'ent_fire worldent addoutput "OnUser1>cmd>command>setang 0 180 0>{3*0.5}>1"',
                f'ent_fire worldent addoutput "OnUser1>cmd>command>screenshot_prefix {session_id}_cube_{ev_suffix}_back>{3*0.5 + 0.1}>1"',
                f'ent_fire worldent addoutput "OnUser1>cmd>command>png_screenshot>{3*0.5 + 0.2}>1"',
                # Left
                f'ent_fire worldent addoutput "OnUser1>cmd>command>setpos_exact {x} {y} {z}>{4*0.5}>1"',
                f'ent_fire worldent addoutput "OnUser1>cmd>command>setang 0 90 0>{4*0.5}>1"',
                f'ent_fire worldent addoutput "OnUser1>cmd>command>screenshot_prefix {session_id}_cube_{ev_suffix}_left>{4*0.5 + 0.1}>1"',
                f'ent_fire worldent addoutput "OnUser1>cmd>command>png_screenshot>{4*0.5 + 0.2}>1"',
                # Up
                f'ent_fire worldent addoutput "OnUser1>cmd>command>setpos_exact {x} {y} {z}>{5*0.5}>1"',
                f'ent_fire worldent addoutput "OnUser1>cmd>command>setang -90 0 0>{5*0.5}>1"',
                f'ent_fire worldent addoutput "OnUser1>cmd>command>screenshot_prefix {session_id}_cube_{ev_suffix}_up>{5*0.5 + 0.1}>1"',
                f'ent_fire worldent addoutput "OnUser1>cmd>command>png_screenshot>{5*0.5 + 0.2}>1"',
                # Down
                f'ent_fire worldent addoutput "OnUser1>cmd>command>setpos_exact {x} {y} {z}>{6*0.5}>1"',
                f'ent_fire worldent addoutput "OnUser1>cmd>command>setang 90 0 0>{6*0.5}>1"',
                f'ent_fire worldent addoutput "OnUser1>cmd>command>screenshot_prefix {session_id}_cube_{ev_suffix}_down>{6*0.5 + 0.1}>1"',
                f'ent_fire worldent addoutput "OnUser1>cmd>command>png_screenshot>{6*0.5 + 0.2}>1"',
                # Cleanup
                f'ent_fire worldent addoutput "OnUser1>cmd>command>cl_drawhud 1;r_drawviewmodel 1;r_drawpanorama 1;cl_firstperson_legs 1;fov_cs_debug 0;noclip 0>4.0>1"',
                f'ent_fire worldent addoutput "OnUser1>cmd>command>r_always_render_all_windows {original_render_all}>4.2>1"',
                'ent_fire worldent addoutput "OnUser1>cmd>command>screenshot_subdir \"\">4.2>1"',
                'ent_fire worldent addoutput "OnUser1>cmd>command>echo [Cubemap Done]>4.5>1"'
            ]
            
            CS2Netcon.send_many(cmds) # Send all setup commands including the sentinel echo
            
            # Use send_and_listen for the trigger to watch for the [Cubemap Done] sentinel
            CS2Netcon.send_and_listen(
                command="ent_fire worldent FireUser1",
                sentinel="[Cubemap Done]",
                timeout=15.0
            )

        # 3. Stitching
        self.progress.emit("Stitching images...")
        stitcher = CubemapStitcher(face_size=self.config['res'])
        
        # Determine screenshot directory
        cs2_ss_dir = target_ss_dir
        
        for ev in ev_steps:
            ev_suffix = f"ev{ev}" if ev >= 0 else f"evm{abs(ev)}"
            try:
                faces = self.load_local_faces(cs2_ss_dir, ev_suffix, session_id)
                out_name = f"output_cubemap_{ev_suffix}.exr"
                if len(ev_steps) == 1: out_name = "output_cubemap.exr"
                
                output_path = os.path.join(self.config['out'], out_name)
                os.makedirs(self.config['out'], exist_ok=True)
                
                if self.config['mode'] == "CrossHLayout":
                    stitcher.stitch_cross(faces, output_path)
                else:
                    stitcher.stitch_equirectangular(faces, output_path)
                    
            except Exception as e:
                self.error.emit(f"Error stitching EV {ev}: {e}")
                return

        self.finished.emit(f"Success! Cubemap saved to: {self.config['out']}")
            
        # Ensure output folder exists
        os.makedirs(self.config['out'], exist_ok=True)

        out_name = "output_cubemap"
        if self.config['mode'] == "CrossHLayout":
            out_path = os.path.join(self.config['out'], f"{out_name}.exr")
            stitcher.stitch_cross(faces, out_path)
        else:
            out_path = os.path.join(self.config['out'], f"{out_name}.jpg")
            stitcher.stitch_equirectangular(faces, out_path)
            
        # Success cleanup
        try: shutil.rmtree(cs2_ss_dir)
        except: pass

        self.finished.emit(f"Success! Output saved to: {out_path}")
