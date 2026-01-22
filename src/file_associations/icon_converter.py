"""
Icon converter for file association icons.
Extracts CS2 smart_prop icon and converts to ICO format.
"""
import os
import sys
from pathlib import Path
from typing import Optional

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: PIL/Pillow not available. Icon conversion will use fallback.")


def get_appdata_path() -> Path:
    """Get the application data directory for Hammer5Tools."""
    if sys.platform == "win32":
        appdata = os.getenv('APPDATA')
        if appdata:
            path = Path(appdata) / "Hammer5Tools" / "icons"
            path.mkdir(parents=True, exist_ok=True)
            return path
    
    # Fallback to program directory
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_path = Path(sys.executable).parent
    else:
        # Running as script
        base_path = Path(__file__).parent.parent.parent
    
    icon_path = base_path / "icons"
    icon_path.mkdir(parents=True, exist_ok=True)
    return icon_path


def extract_cs2_icon(cs2_path: str) -> Optional[str]:
    """
    Locate the smart_prop_lg.png icon from CS2 installation.
    
    Args:
        cs2_path: Path to CS2 installation
        
    Returns:
        Path to smart_prop PNG, or None if not found
    """
    if not cs2_path or not os.path.exists(cs2_path):
        return None
    
    icon_path = Path(cs2_path) / "game" / "core" / "tools" / "images" / "assettypes" / "smart_prop_lg.png"
    
    if icon_path.exists():
        return str(icon_path)
    
    return None


def convert_png_to_ico(png_path: str, output_path: str, sizes: list = None) -> bool:
    """
    Convert PNG to ICO format with multiple resolutions.
    
    Args:
        png_path: Path to source PNG file
        output_path: Path where ICO file will be saved
        sizes: List of icon sizes to include (default: [16, 32, 48, 256])
        
    Returns:
        True if conversion successful, False otherwise
    """
    if not PIL_AVAILABLE:
        print("Cannot convert PNG to ICO: Pillow not installed")
        return False
    
    if sizes is None:
        sizes = [16, 32, 48, 256]
    
    try:
        # Open the source PNG
        img = Image.open(png_path)
        
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Create resized versions
        icon_images = []
        for size in sizes:
            resized = img.resize((size, size), Image.Resampling.LANCZOS)
            icon_images.append(resized)
        
        # Save as ICO
        icon_images[0].save(
            output_path,
            format='ICO',
            sizes=[(img.width, img.height) for img in icon_images],
            append_images=icon_images[1:]
        )
        
        return True
        
    except Exception as e:
        print(f"Error converting PNG to ICO: {e}")
        return False


def get_fallback_icon_path() -> str:
    """
    Get path to fallback icon (app icon) if CS2 icon unavailable.
    
    Returns:
        Path to fallback ICO file
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_path = Path(sys.executable).parent
    else:
        # Running as script
        base_path = Path(__file__).parent.parent
    
    appicon_path = base_path / "appicon.ico"
    
    if appicon_path.exists():
        return str(appicon_path)
    
    # Last resort: return executable path itself (Windows will use embedded icon)
    return sys.executable


def get_vsmart_icon_path(cs2_path: Optional[str] = None, force_recreate: bool = False) -> str:
    """
    Get or create the .vsmart file association icon.
    
    This function:
    1. Checks if icon already exists in cache
    2. Tries to extract from CS2 installation
    3. Converts PNG to ICO format
    4. Falls back to app icon if CS2 unavailable
    
    Args:
        cs2_path: Path to CS2 installation (optional)
        force_recreate: If True, recreate icon even if it exists
        
    Returns:
        Path to ICO file suitable for registry registration
    """
    icon_cache_dir = get_appdata_path()
    cached_icon_path = icon_cache_dir / "vsmart.ico"
    
    # Return cached icon if it exists and we're not forcing recreation
    if cached_icon_path.exists() and not force_recreate:
        return str(cached_icon_path)
    
    # Try to extract and convert CS2 icon
    if cs2_path and PIL_AVAILABLE:
        cs2_icon_png = extract_cs2_icon(cs2_path)
        
        if cs2_icon_png:
            success = convert_png_to_ico(
                cs2_icon_png,
                str(cached_icon_path),
                sizes=[16, 32, 48, 256]
            )
            
            if success:
                print(f"Created vsmart icon from CS2: {cached_icon_path}")
                return str(cached_icon_path)
    
    # Fallback: use app icon
    fallback_path = get_fallback_icon_path()
    
    # Try to copy fallback to cache for consistency
    try:
        import shutil
        shutil.copy2(fallback_path, str(cached_icon_path))
        return str(cached_icon_path)
    except:
        # If copy fails, return fallback directly
        return fallback_path


def validate_icon_path(icon_path: str) -> bool:
    """
    Validate that an icon file exists and is accessible.
    
    Args:
        icon_path: Path to icon file
        
    Returns:
        True if icon is valid, False otherwise
    """
    try:
        path = Path(icon_path)
        return path.exists() and path.is_file() and path.suffix.lower() == '.ico'
    except:
        return False
