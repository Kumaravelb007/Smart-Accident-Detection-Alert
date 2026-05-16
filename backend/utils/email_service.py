"""
Email Alert Service
Sends accident alert emails via SendGrid with attached frame images.
"""

import base64
import logging
from pathlib import Path

from config import SENDGRID_API_KEY, ALERT_EMAIL_FROM, FRAMES_DIR

logger = logging.getLogger(__name__)


def _build_html_body(timestamp: str, confidence: float, message: str, ai_report: str = "", location: str = "") -> str:
    """Build a styled HTML email body for the accident alert."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8">
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 0; background: #0a0e27; }}
        .container {{ max-width: 600px; margin: 0 auto; background: #111637; border-radius: 12px; overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #ff3366, #ff6b3d); padding: 30px; text-align: center; }}
        .header h1 {{ color: #fff; margin: 0; font-size: 24px; }}
        .header .emoji {{ font-size: 40px; display: block; margin-bottom: 10px; }}
        .body {{ padding: 30px; color: #e0e0e0; }}
        .field {{ margin-bottom: 20px; }}
        .field .label {{ color: #888; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }}
        .field .value {{ color: #fff; font-size: 16px; font-weight: 600; }}
        .confidence-bar {{ background: #1a2040; border-radius: 8px; overflow: hidden; height: 8px; margin-top: 5px; }}
        .confidence-fill {{ height: 100%; border-radius: 8px; background: linear-gradient(90deg, #00e676, #ff3366); width: {confidence*100:.0f}%; }}
        .footer {{ padding: 20px 30px; text-align: center; color: #555; font-size: 12px; border-top: 1px solid #1a2040; }}
    </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <span class="emoji">🚨</span>
                <h1>ACCIDENT DETECTED</h1>
            </div>
            <div class="body">
                <div class="field">
                    <div class="label">Detection Time</div>
                    <div class="value">{timestamp}</div>
                </div>
                <div class="field">
                    <div class="label">Confidence Score</div>
                    <div class="value">{confidence:.1%}</div>
                    <div class="confidence-bar"><div class="confidence-fill"></div></div>
                </div>
                <div class="field">
                    <div class="label">Location</div>
                    <div class="value">{location}</div>
                </div>
                <div class="field">
                    <div class="label">Detection Details</div>
                    <div class="value">{message}</div>
                </div>
                <div class="field">
                    <div class="label">AI Accident Analysis Report</div>
                    <div class="value" style="background: rgba(0, 212, 255, 0.1); padding: 15px; border-left: 4px solid #00d4ff; font-weight: normal; font-size: 14px; line-height: 1.5; border-radius: 4px;">
                        {ai_report.replace('\n', '<br>') if ai_report else "No AI report generated."}
                    </div>
                </div>
                <div class="field">
                    <div class="label">Evidence</div>
                    <div class="value" style="color:#888; font-style:italic;">Accident frame attached to this email</div>
                </div>
            </div>
            <div class="footer">
                Smart Accident Detection &amp; Alert System &bull; Automated Alert
            </div>
        </div>
    </body>
    </html>
    """


def send_accident_alert(
    frame_filename: str,
    timestamp: str,
    confidence: float,
    message: str,
    receiver_email: str,
    ai_report: str = "",
    location: str = "",
) -> dict:
    """
    Send accident alert email via SendGrid REST API using `requests`.

    Uses requests instead of the sendgrid library to avoid Python 3.14
    SSL CERTIFICATE_VERIFY_FAILED errors with urllib.
    """
    import requests

    api_key = SENDGRID_API_KEY
    if not api_key or api_key == "your_sendgrid_api_key_here":
        logger.warning("SendGrid API key not configured — email skipped")
        return {"status": "skipped", "message": "SendGrid API key not configured. Set SENDGRID_API_KEY in .env file."}

    # ALWAYS use the verified sender from .env — SendGrid requires it
    from_email = ALERT_EMAIL_FROM
    if not from_email:
        return {"status": "skipped", "message": "No sender email configured in .env (ALERT_EMAIL_FROM)."}

    if not receiver_email:
        return {"status": "skipped", "message": "No receiver email available."}

    try:
        html_content = _build_html_body(timestamp=timestamp, confidence=confidence, message=message, ai_report=ai_report, location=location)

        # Build SendGrid v3 API payload
        payload = {
            "personalizations": [
                {"to": [{"email": receiver_email}]}
            ],
            "from": {"email": from_email},
            "subject": f"🚨 ACCIDENT ALERT — Detected at {timestamp}",
            "content": [
                {"type": "text/html", "value": html_content}
            ],
        }

        # Attach the accident frame image
        frame_path = FRAMES_DIR / frame_filename
        if frame_path.exists():
            with open(frame_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
            payload["attachments"] = [
                {
                    "content": encoded,
                    "filename": frame_filename,
                    "type": "image/jpeg",
                    "disposition": "attachment",
                }
            ]

        # Send via SendGrid REST API using requests (no urllib SSL issues)
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

        if response.status_code in (200, 201, 202):
            logger.info(f"Email sent to {receiver_email}: status={response.status_code}")
            return {"status": "sent", "message": f"Alert email sent to {receiver_email}", "status_code": response.status_code}
        else:
            error_detail = response.text
            logger.error(f"SendGrid API error: {response.status_code} — {error_detail}")
            return {"status": "error", "message": f"SendGrid returned {response.status_code}: {error_detail}"}

    except Exception as e:
        logger.error(f"Email failed: {e}")
        return {"status": "error", "message": f"Failed to send email: {str(e)}"}

