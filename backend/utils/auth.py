"""
User Authentication Utilities
Simple JSON file-based user management with hashed passwords.
"""

import hashlib
import json
import logging
import secrets
from pathlib import Path

logger = logging.getLogger(__name__)

USERS_FILE = Path(__file__).resolve().parent.parent / "users.json"
SESSIONS = {}  # In-memory session store: {token: email}


def _load_users() -> dict:
    """Load users from JSON file."""
    if USERS_FILE.exists():
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_users(users: dict):
    """Save users to JSON file."""
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def _hash_password(password: str) -> str:
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def signup(name: str, email: str, password: str) -> dict:
    """Register a new user."""
    email = email.strip().lower()
    if not email or not password or not name:
        return {"success": False, "message": "All fields are required."}

    if len(password) < 6:
        return {"success": False, "message": "Password must be at least 6 characters."}

    users = _load_users()
    if email in users:
        return {"success": False, "message": "Email already registered."}

    users[email] = {
        "name": name.strip(),
        "email": email,
        "password": _hash_password(password),
    }
    _save_users(users)
    logger.info(f"New user registered: {email}")

    # Auto-login after signup
    token = secrets.token_hex(32)
    SESSIONS[token] = email
    return {"success": True, "message": "Account created successfully!", "token": token, "name": name.strip(), "email": email}


def login(email: str, password: str) -> dict:
    """Authenticate user and return session token."""
    email = email.strip().lower()
    users = _load_users()

    if email not in users:
        return {"success": False, "message": "Invalid email or password."}

    if users[email]["password"] != _hash_password(password):
        return {"success": False, "message": "Invalid email or password."}

    token = secrets.token_hex(32)
    SESSIONS[token] = email
    logger.info(f"User logged in: {email}")
    return {"success": True, "message": "Login successful!", "token": token, "name": users[email]["name"], "email": email}


def get_user_by_token(token: str) -> dict | None:
    """Get user info from session token."""
    email = SESSIONS.get(token)
    if not email:
        return None
    users = _load_users()
    return users.get(email)


def logout(token: str):
    """Remove session."""
    SESSIONS.pop(token, None)
