"""Extract short video clips for Nemotron's 2-minute input limit."""

import subprocess
from pathlib import Path

MAX_CLIP_DURATION = 120


def extract_clip(video_path: Path, start_seconds: float, end_seconds: float,
                 output_dir: Path) -> Path | None:
    """Extract a clip from a video file using ffmpeg.

    Returns path to the clip, or None if ffmpeg fails.
    """
    duration = min(end_seconds - start_seconds, MAX_CLIP_DURATION)
    if duration <= 0:
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    clip_name = f"{video_path.stem}_{int(start_seconds)}_{int(start_seconds + duration)}.mp4"
    clip_path = output_dir / clip_name

    if clip_path.exists():
        return clip_path

    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", str(start_seconds),
                "-i", str(video_path),
                "-t", str(duration),
                "-c:v", "libx264", "-preset", "fast",
                "-c:a", "aac",
                "-loglevel", "error",
                str(clip_path),
            ],
            capture_output=True,
            timeout=60,
            check=True,
        )
        return clip_path
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        clip_path.unlink(missing_ok=True)
        return None
