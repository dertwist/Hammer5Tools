"""mp3 <-> wav conversion using the ffmpeg binary bundled with imageio-ffmpeg."""
import os
import subprocess
import imageio_ffmpeg

# CREATE_NO_WINDOW so ffmpeg doesn't flash a console on Windows
_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def convert_audio(src_path, dst_ext, overwrite=True):
    """Convert ``src_path`` to a sibling file with ``dst_ext`` ('wav' or 'mp3').

    Returns the output path. Raises subprocess.CalledProcessError if ffmpeg fails
    or FileExistsError if the target exists and overwrite is False.
    """
    dst_ext = dst_ext.lower().lstrip(".")
    dst_path = os.path.splitext(src_path)[0] + "." + dst_ext
    if os.path.abspath(dst_path) == os.path.abspath(src_path):
        raise ValueError("source and destination are the same file")
    if not overwrite and os.path.exists(dst_path):
        raise FileExistsError(dst_path)

    args = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", src_path]
    if dst_ext == "mp3":
        args += ["-codec:a", "libmp3lame", "-qscale:a", "2"]  # ~190 kbps VBR
    args.append(dst_path)
    subprocess.run(
        args, check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=_NO_WINDOW,
    )
    return dst_path
