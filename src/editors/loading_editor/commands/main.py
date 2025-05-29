import os
from datetime import datetime
try:
    from .vmap_parser import parse
except:
    from vmap_parser import parse

def generate_commands(vmap_path, history=False):
    """
    Generate CS2 console commands for point_camera entities in a VMAP file.
    Args:
        vmap_path (str): Path to the .vmap file
    Returns:
        list: List of generated console command strings
    """
    print(f"Loading VMAP file: {vmap_path}")
    cameras = parse(vmap_path, show_entity_properties=False)
    print(cameras)
    print(f"Loaded {len(cameras)} point_camera entities from the VMAP file.")
    map_name = os.path.splitext(os.path.basename(vmap_path))[0]
    current_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if history:
        screenshot_path = f"screenshots\\Hammer5Tools\\History\\{current_date}"
    else:
        screenshot_path = f"screenshots\\Hammer5Tools\\LoadingScreen"
    commands = [
        "sv_cheats 1",
        "noclip 1",
        "ent_fire cmd kill",
        "ent_create point_servercommand {targetname cmd}",
        f"screenshot_subdir {screenshot_path}",
        "jpeg_quality 100"
    ]
    tick = 1.0 / 64.0
    def vector3_to_str(vec):
        if vec is None:
            return ""
        if isinstance(vec, str):
            return vec
        if hasattr(vec, "X") and hasattr(vec, "Y") and hasattr(vec, "Z"):
            return f"{vec.X} {vec.Y} {vec.Z}"
        if hasattr(vec, "__iter__"):
            return ' '.join(str(x) for x in vec)
        return str(vec)
    def qangle_to_str(qang):
        if qang is None:
            return ""
        for names in [
            ("Pitch", "Yaw", "Roll"),
            ("pitch", "yaw", "roll"),
            ("x", "y", "z"),
        ]:
            if all(hasattr(qang, n) for n in names):
                return f"{getattr(qang, names[0])} {getattr(qang, names[1])} {getattr(qang, names[2])}"
        if isinstance(qang, str):
            return qang
        if hasattr(qang, "__iter__"):
            return ' '.join(str(x) for x in qang)
        return str(qang)
    for camera_count, cam in enumerate(cameras):
        origin = cam.get("origin", None)
        angles = cam.get("angles", None)
        fov = cam.get("FOV", None)
        targetname = cam.get("targetname", None)
        delay = camera_count * tick * 10 + 0.1
        origin_str = vector3_to_str(origin)
        angles_str = qangle_to_str(angles)
        if origin_str and fov not in (None, "", "N/A"):
            # Set screenshot prefix to camera name if available, otherwise use map name
            screenshot_name = targetname if targetname and targetname != "N/A" else f"{map_name}_cam{camera_count}"
            commands.extend([
                f'ent_fire worldent addoutput "OnUser1>cmd>command>screenshot_prefix {screenshot_name}>{delay}>1"',
                f'ent_fire worldent addoutput "OnUser1>cmd>command>setpos {origin_str}>{delay}>1"',
                f'ent_fire worldent addoutput "OnUser1>cmd>command>setang {angles_str}>{delay}>1"' if angles_str else "",
                f'ent_fire worldent addoutput "OnUser1>cmd>command>fov_cs_debug {fov}>{delay}>1"',
                f'ent_fire worldent addoutput "OnUser1>cmd>command>jpeg_screenshot>{delay + (tick * 2)}>1"'
            ])
    commands = [cmd for cmd in commands if cmd]
    if cameras:
        final_delay = (len(cameras) - 1) * tick * 10 + 1
        commands.extend([
            f'ent_fire worldent addoutput "OnUser1>cmd>command>screenshot_prefix shot>{final_delay}>1"',
            f'ent_fire worldent addoutput "OnUser1>cmd>command>r_drawviewmodel 1;cl_drawhud 1;r_drawpanorama 1;noclip 0>{final_delay}>1"',
            "r_drawviewmodel 0",
            "cl_drawhud 0",
            "r_drawpanorama 0",
            "ent_fire worldent FireUser1"
        ])
    return commands

if __name__ == "__main__":
    pfd = r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\de_sanctum\maps\de_sanctum.vmap"
    commands = generate_commands(pfd)
    if commands:
        print("\nGenerated console commands:")
        print(';'.join(commands))
    else:
        print("No point_camera entities found.")