import os
import re
from datetime import datetime
try:
    from .vmap_parser import parse
except:
    try:
        from vmap_parser import parse
    except:
        from gui.editors.loading_editor.vmap_parser import parse

try:
    from gui.other.cs2_netcon import CS2Netcon
except Exception:
    CS2Netcon = None

# setpos moves the player origin while the screenshot is taken from the eye,
# so camera positions are lowered by the standing view height. Tune this if
# shots sit consistently above or below the point_camera in Hammer.
PLAYER_EYE_HEIGHT = 70.0

_NUMBER = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def _numbers(value) -> tuple[float, ...]:
    """Read the numbers out of a Core entity property.

    Core projects these as text: "619.4 621.27 284.07" for vectors, and older
    builds projected angles as the debug form "QAngle { Pitch = 7.6, ... }".
    Both reduce to the same ordered numbers, which is all a console command
    needs.
    """
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        try:
            return tuple(float(item) for item in value)
        except (TypeError, ValueError):
            return ()
    try:
        return tuple(float(match) for match in _NUMBER.findall(str(value)))
    except ValueError:
        return ()


def _number(value: float) -> str:
    """Format one number for a console command, without trailing zeros."""
    return f"{value:.4f}".rstrip("0").rstrip(".") or "0"


def _vector(*values: float) -> str:
    return " ".join(_number(value) for value in values)


def _screenshot_name(targetname) -> str:
    """A camera's targetname reduced to something safe as a file prefix.

    The name is embedded in an ent_fire addoutput parameter, where a space
    would end the command early and a quote would break the string.
    """
    if not targetname or targetname == "N/A":
        return ""
    return re.sub(r"_+", "_", re.sub(r"[^A-Za-z0-9_.-]", "_", str(targetname))).strip("_")


def generate_commands(vmap_path, history=False) -> tuple[list, str | None]:
    """
    Generate CS2 console commands for point_camera entities in a VMAP file.
    Args:
        vmap_path (str): Path to the .vmap file
        history (bool): If True, uses a date-stamped History subfolder.
    Returns:
        tuple[list, str | None]: (commands, session_date) where session_date is the
            date-stamped folder name used in screenshot_subdir (only set when history=True,
            otherwise None).
    """
    print(f"Loading VMAP file: {vmap_path}")
    cameras = parse(vmap_path, show_entity_properties=False)
    print(cameras)
    print(f"Loaded {len(cameras)} point_camera entities from the VMAP file.")

    # Query the user's current value of r_always_render_all_windows so we
    # can restore it after taking screenshots.
    render_cvar = "r_always_render_all_windows"
    user_render_value = "false"  # safe default
    if CS2Netcon is not None:
        queried = CS2Netcon.query(render_cvar)
        if queried is not None:
            user_render_value = queried

    map_name = os.path.splitext(os.path.basename(vmap_path))[0]
    current_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session_date = current_date if history else None
    if history:
        screenshot_path = f"screenshots\\Hammer5Tools\\History\\{current_date}"
    else:
        screenshot_path = f"screenshots\\Hammer5Tools\\LoadingScreen"
    commands = [
        "cl_firstperson_legs 0",
        "sv_cheats 1",
        "bot_kick",
        "noclip 1",
        "ent_fire cmd kill",
        "ent_create point_servercommand {targetname cmd}",
        f"screenshot_subdir {screenshot_path}",
    ]
    tick = 1.0 / 64.0
    for camera_count, cam in enumerate(cameras):
        # Core projects entity properties as strings ("619.4 621.27 284.07"),
        # so both position and angles have to be read back as numbers here.
        origin = _numbers(cam.get("origin"))
        angles = _numbers(cam.get("angles"))
        fov = _numbers(cam.get("FOV"))
        targetname = cam.get("targetname", None)
        delay = camera_count * tick * 10 + 0.1
        if len(origin) < 3:
            continue
        # setpos places the player's origin, but the shot is taken from the
        # eye, so drop the camera down by the standing view height.
        origin_str = _vector(origin[0], origin[1], origin[2] - PLAYER_EYE_HEIGHT)
        angles_str = _vector(*angles[:3]) if len(angles) >= 3 else ""
        # Set screenshot prefix to camera name if available, otherwise use map name
        screenshot_name = _screenshot_name(targetname) or f"{map_name}_cam{camera_count}"
        commands.extend([
            f'ent_fire worldent addoutput "OnUser1>cmd>command>screenshot_prefix {screenshot_name}>{delay}>1"',
            f'ent_fire worldent addoutput "OnUser1>cmd>command>setpos {origin_str}>{delay}>1"',
            f'ent_fire worldent addoutput "OnUser1>cmd>command>setang {angles_str}>{delay}>1"' if angles_str else "",
            # A camera without a usable FOV keeps whatever the view already has
            # rather than losing the shot entirely.
            f'ent_fire worldent addoutput "OnUser1>cmd>command>fov_cs_debug {_number(fov[0])}>{delay}>1"' if fov else "",
            f'ent_fire worldent addoutput "OnUser1>cmd>command>r_always_render_all_windows true>{delay}>1"',
            f'ent_fire worldent addoutput "OnUser1>cmd>command>png_screenshot>{delay + (tick * 2)}>1"'
        ])
    commands = [cmd for cmd in commands if cmd]
    if cameras:
        final_delay = (len(cameras) - 1) * tick * 10 + 1
        commands.extend([
            f'ent_fire worldent addoutput "OnUser1>cmd>command>screenshot_prefix shot>{final_delay}>1"',
            f'ent_fire worldent addoutput "OnUser1>cmd>command>r_drawviewmodel 1;cl_drawhud 1;r_drawpanorama 1;noclip 0>{final_delay}>1"',
            f'ent_fire worldent addoutput "OnUser1>cmd>command>r_always_render_all_windows {user_render_value}>{final_delay}>1"',
            "r_drawviewmodel 0",
            "cl_drawhud 0",
            "r_drawpanorama 0",
            "ent_fire worldent FireUser1"
        ])
    return commands, session_date

if __name__ == "__main__":
    pfd = r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\de_sanctum\maps\de_sanctum.vmap"
    commands, session_date = generate_commands(pfd)
    if commands:
        print("\nGenerated console commands:")
        print(';'.join(commands))
    else:
        print("No point_camera entities found.")