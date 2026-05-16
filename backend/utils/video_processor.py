"""
Video Processing Utilities
Handles video frame extraction, metadata retrieval, and frame saving.
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from config import FRAMES_DIR

logger = logging.getLogger(__name__)


def extract_frames(video_path: str, sample_rate: int = 2) -> list[np.ndarray]:
    """
    Extract frames from a video file at a given sample rate (frames per second).

    Args:
        video_path: Path to the video file.
        sample_rate: Number of frames to extract per second of video.

    Returns:
        List of BGR numpy arrays (frames).
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Cannot open video: {video_path}")
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0  # default assumption

    frame_interval = max(1, int(fps / sample_rate))
    frames = []
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_interval == 0:
            # Resize large frames for faster processing
            h, w = frame.shape[:2]
            if w > 1280:
                scale = 1280 / w
                frame = cv2.resize(frame, (1280, int(h * scale)))
            frames.append(frame)

        frame_count += 1

    cap.release()
    logger.info(f"Extracted {len(frames)} frames from {frame_count} total (interval={frame_interval})")
    return frames


def save_frame(frame: np.ndarray, prefix: str = "accident") -> str:
    """
    Save a frame as a JPEG image.

    Args:
        frame: BGR numpy array.
        prefix: Filename prefix.

    Returns:
        Filename of the saved image.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}_{uuid.uuid4().hex[:6]}.jpg"
    filepath = FRAMES_DIR / filename

    cv2.imwrite(str(filepath), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
    logger.info(f"Saved frame: {filepath}")
    return filename


def get_video_metadata(video_path: str) -> dict:
    """
    Get metadata about a video file.

    Returns:
        Dict with duration, fps, resolution, and frame_count.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"error": "Cannot open video"}

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = frame_count / fps if fps > 0 else 0

    cap.release()

    return {
        "duration_seconds": round(duration, 2),
        "fps": round(fps, 2),
        "resolution": f"{width}x{height}",
        "frame_count": frame_count,
    }
