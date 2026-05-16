"""
Configuration module for the Smart Accident Detection and Alert System.
Loads environment variables and defines application constants.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Directory Paths
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
FRAMES_DIR = BASE_DIR / "frames"
FRONTEND_DIR = BASE_DIR.parent / "frontend"
FRONTEND_DIST_DIR = FRONTEND_DIR / "dist"

# Create directories if they do not exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
FRAMES_DIR.mkdir(parents=True, exist_ok=True)

# SendGrid Email Configuration
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", "alert@accidentdetection.ai")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")

# Detection Configuration
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.4"))
FRAME_SAMPLE_RATE = int(os.getenv("FRAME_SAMPLE_RATE", "3"))
MAX_VIDEO_SIZE_MB = int(os.getenv("MAX_VIDEO_SIZE_MB", "100"))
ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

# CNN Model Configuration
CNN_MODEL_PATH = os.getenv(
    "CNN_MODEL_PATH",
    str(BASE_DIR / "models" / "pretrained" / "accident_cnn.keras"),
)
CNN_INPUT_SIZE = int(os.getenv("CNN_INPUT_SIZE", "224"))

# Groq AI Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
