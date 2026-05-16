"""
Detection API Routes
Handles video upload, processing, detection, and alert triggering.
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from config import (
    ALLOWED_EXTENSIONS,
    CNN_INPUT_SIZE,
    CNN_MODEL_PATH,
    CONFIDENCE_THRESHOLD,
    FRAME_SAMPLE_RATE,
    MAX_VIDEO_SIZE_MB,
    UPLOAD_DIR,
)
from models.detector import AccidentDetector
from utils.ai_report import generate_accident_report
from utils.auth import get_user_by_token
from utils.database import get_user_history, save_detection
from utils.email_service import send_accident_alert
from utils.video_processor import extract_frames, get_video_metadata, save_frame

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["detection"])

# Initialize detector once

detector = AccidentDetector(
    model_path=CNN_MODEL_PATH,
    confidence_threshold=CONFIDENCE_THRESHOLD,
    cnn_input_size=CNN_INPUT_SIZE,
)


@router.post("/detect")
async def detect_accident(
    video: UploadFile = File(...),
    sender_email: str = Form(""),  # preserved for backward compatibility
    authorization: str = Header(""),
):
    """
    Upload a video and run accident detection.
    Uses the logged-in user's email as the alert recipient.
    sender_email is kept for compatibility with older clients.
    """
    _ = sender_email

    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Please login to use this feature.")

    receiver_email = user["email"]

    file_ext = Path(video.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file_ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    video_id = uuid.uuid4().hex[:10]
    video_filename = f"{video_id}{file_ext}"
    video_path = UPLOAD_DIR / video_filename

    try:
        content = await video.read()
        size_mb = len(content) / (1024 * 1024)
        if size_mb > MAX_VIDEO_SIZE_MB:
            raise HTTPException(
                status_code=400,
                detail=f"File too large ({size_mb:.1f} MB). Max: {MAX_VIDEO_SIZE_MB} MB.",
            )

        with open(video_path, "wb") as out:
            out.write(content)
        logger.info("Saved video: %s (%.1f MB)", video_path, size_mb)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to save video: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save uploaded video.")

    metadata = get_video_metadata(str(video_path))

    frames = extract_frames(str(video_path), sample_rate=FRAME_SAMPLE_RATE)
    if not frames:
        raise HTTPException(status_code=400, detail="Could not extract frames. Video may be corrupt.")

    result = detector.detect(frames)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    frame_filename = None
    frame_url = None
    if result.frame is not None:
        prefix = "accident" if result.accident_detected else "frame"
        frame_filename = save_frame(result.frame, prefix=prefix)
        frame_url = f"/frames/{frame_filename}"

    ai_report_text = ""
    location = "Unknown (Simulated Location for Analysis)"

    email_status = {
        "status": "not_triggered",
        "message": "No accident detected - email not sent.",
    }

    if result.accident_detected and frame_filename:
        ai_report_text = generate_accident_report(
            confidence=result.confidence,
            vehicle_count=result.vehicle_count,
            message=result.message,
            location=location,
            time=timestamp,
            severity=result.severity,
            traffic_analysis=result.traffic_analysis,
        )

        email_status = send_accident_alert(
            frame_filename=frame_filename,
            timestamp=timestamp,
            confidence=result.confidence,
            message=result.message,
            receiver_email=receiver_email,
            ai_report=ai_report_text,
            location=location,
        )

    save_detection(
        user_email=receiver_email,
        timestamp=timestamp,
        accident_detected=result.accident_detected,
        confidence=result.confidence,
        message=result.message,
        vehicle_count=result.vehicle_count,
        frame_url=frame_url or "",
        ai_report=ai_report_text,
        severity=result.severity,
        detection_strategy=result.strategy or detector.active_strategy,
        traffic_density=result.traffic_analysis.get("traffic_density", "Low"),
        average_speed_kmh=float(result.traffic_analysis.get("average_speed_kmh", 0.0)),
        anomaly_score=float(result.traffic_analysis.get("anomaly_score", 0.0)),
        congestion_detected=bool(result.traffic_analysis.get("congestion_detected", False)),
    )

    return JSONResponse(
        content={
            "accident_detected": result.accident_detected,
            "confidence": round(result.confidence, 4),
            "confidence_percent": f"{result.confidence:.1%}",
            "severity": result.severity,
            "timestamp": timestamp,
            "frame_url": frame_url,
            "frame_index": result.frame_index,
            "message": result.message,
            "vehicle_count": result.vehicle_count,
            "traffic_analysis": result.traffic_analysis,
            "detection_strategy": result.strategy or detector.active_strategy,
            "video_metadata": metadata,
            "email_alert": email_status,
            "ai_report": ai_report_text,
            "location": location,
        }
    )


@router.get("/health")
async def health_check():
    """API health check."""
    return {
        "status": "healthy",
        "detection_strategy": detector.active_strategy,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/history")
async def get_history(authorization: str = Header("")):
    """Fetch user's detection history."""
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Please login to view history.")

    history = get_user_history(user["email"], limit=120)
    return {"history": history}
