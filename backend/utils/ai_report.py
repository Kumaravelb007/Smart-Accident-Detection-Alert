"""
Groq AI Reporting Module
Generates accident analysis reports and handles chat interactions.
"""

import logging
import re
from typing import Optional

from groq import Groq

from config import GROQ_API_KEY

logger = logging.getLogger(__name__)

# Initialize Groq client conditionally
client = None
if GROQ_API_KEY and GROQ_API_KEY != "your_groq_api_key_here":
    try:
        client = Groq(api_key=GROQ_API_KEY)
    except Exception as exc:
        logger.error("Failed to initialize Groq client: %s", exc)


def _sanitize_report_text(
    text: str,
    confidence: float,
    severity: str,
    location: str,
    time: str,
) -> str:
    """Normalize AI report text to plain readable content without placeholders or markdown symbols."""
    clean = (text or "").strip()
    if not clean:
        clean = (
            f"At {time}, the system flagged a {severity.lower()} collision risk at {location} "
            f"with {confidence * 100:.1f}% confidence. Immediate verification and on-site response are recommended."
        )

    replacements = {
        "[Location]": location,
        "<Location>": location,
        "{location}": location,
        "[Time]": time,
        "<Time>": time,
        "{time}": time,
        "[Severity]": severity,
        "<Severity>": severity,
        "{severity}": severity,
    }
    for key, value in replacements.items():
        clean = clean.replace(key, str(value))

    clean = clean.replace("**", "")
    clean = clean.replace("__", "")
    clean = clean.replace("##", "")
    clean = clean.replace("#", "")
    clean = clean.replace("`", "")

    clean = re.sub(r"\[(placeholder|tbd|to be filled|add details here)\]", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\b(placeholder|tbd|to be determined)\b", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s{2,}", " ", clean).strip()

    return clean


def generate_accident_report(
    confidence: float,
    vehicle_count: int,
    message: str,
    location: str,
    time: str,
    severity: str = "Minor",
    traffic_analysis: Optional[dict] = None,
) -> str:
    """Generate an AI report for detected incidents."""
    if not client:
        return "AI analysis unavailable. Please check Groq API configuration."

    traffic_analysis = traffic_analysis or {}

    prompt = f"""
You are an AI traffic safety analyst.
Create a concise professional report from the detection output below.
Use 4-5 sentences max.
Strict output rules:
- Replace all placeholders with concrete values from the detection data.
- Do not use markdown symbols such as **, ##, or bullet formatting.
- Return clean, readable plain text only.

Detection Data:
- Collision confidence: {confidence * 100:.1f}%
- Severity class: {severity}
- Peak vehicles in scene: {vehicle_count}
- Detection indicators: {message}
- Traffic density: {traffic_analysis.get("traffic_density", "Unknown")}
- Congestion detected: {traffic_analysis.get("congestion_detected", False)}
- Anomaly score: {traffic_analysis.get("anomaly_score", 0.0)}
- Estimated location: {location}
- Detection time: {time}

Include:
1) what likely happened,
2) probable impact/risk level,
3) immediate response recommendations.
Avoid intro/outro filler.
"""

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a professional traffic accident analyst."},
                {"role": "user", "content": prompt},
            ],
            model="llama-3.1-8b-instant",
            temperature=0.3,
            max_tokens=250,
        )
        raw_report = response.choices[0].message.content.strip()
        return _sanitize_report_text(
            raw_report,
            confidence=confidence,
            severity=severity,
            location=location,
            time=time,
        )
    except Exception as exc:
        logger.error("Groq API error during report generation: %s", exc)
        return "AI report generation failed due to an API error."


def chat_with_ai(user_message: str, history: list) -> str:
    """Handle chat interaction with the AI assistant."""
    if not client:
        return "I'm sorry, my AI capabilities are currently offline. Please configure the Groq API key."

    messages = [
        {
            "role": "system",
            "content": (
                "You are an AI assistant for the Smart Accident Detection System. "
                "You help users understand accident reports, system capabilities, and road safety. "
                "Keep answers concise."
            ),
        }
    ]

    for msg in history:
        messages.append(msg)

    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            messages=messages,
            model="llama-3.1-8b-instant",
            temperature=0.5,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("Groq API error during chat: %s", exc)
        return "Sorry, I encountered an error while processing your request."
