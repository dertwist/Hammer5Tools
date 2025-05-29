import os
from datetime import datetime
from vmap_parser import parse

pfd = r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\de_sanctum\maps\de_sanctum.vmap"

print(f"Loading VMAP file: {pfd}")

# Parse the VMAP file for point_camera entities
cameras = parse(pfd, show_entity_properties=False)
print(cameras)

print(f"Loaded {len(cameras)} point_camera entities from the VMAP file.")

# Get map name from file path
map_name = os.path.splitext(os.path.basename(pfd))[0]
current_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
screenshot_path = f"screenshots\\Hammer5Tools"

# Initialize console commands
commands = [
    "sv_cheats 1",
    "noclip 1",
    "ent_fire cmd kill",
    "ent_create point_servercommand {targetname cmd}",
    f"screenshot_subdir {screenshot_path}"
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
    # Try common .NET QAngle property names
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

# Generate CS2 console commands for each camera
for camera_count, cam in enumerate(cameras):
    origin = cam.get("origin", None)
    angles = cam.get("angles", None)
    fov = cam.get("FOV", None)

    delay = camera_count * tick * 10 + 0.1

    origin_str = vector3_to_str(origin)
    angles_str = qangle_to_str(angles)

    # Only add commands if both origin and fov are valid (not None or empty)
    if origin_str and fov not in (None, "", "N/A"):
        commands.extend([
            f'ent_fire worldent addoutput "OnUser1>cmd>command>setpos {origin_str}>{delay}>1"',
            f'ent_fire worldent addoutput "OnUser1>cmd>command>setang {angles_str}>{delay}>1"' if angles_str else "",
            f'ent_fire worldent addoutput "OnUser1>cmd>command>fov_cs_debug {fov}>{delay}>1"',
            f'ent_fire worldent addoutput "OnUser1>cmd>command>png_screenshot {map_name}>{delay + (tick * 2)}>1"'
        ])

# Remove any empty commands (e.g., if angles_str is empty)
commands = [cmd for cmd in commands if cmd]

if cameras:
    # Add final commands to restore settings
    final_delay = (len(cameras) - 1) * tick * 10 + 1
    commands.extend([
        f'ent_fire worldent addoutput "OnUser1>cmd>command>r_drawviewmodel 1;cl_drawhud 1;r_drawpanorama 1;noclip 0>{final_delay}>1"',
        "r_drawviewmodel 0",
        "cl_drawhud 0",
        "r_drawpanorama 0",
        "ent_fire worldent FireUser1"
    ])

    # Print the final command string
    print("\nGenerated console commands:")
    print(';'.join(commands))
else:
    print("No point_camera entities found.")