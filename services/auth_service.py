"""
services/auth_service.py — JWT token creation/decoding and password hashing.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
import bcrypt
from fastapi import Request

from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES


# ── Password helpers ─────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Return bcrypt hash of plain-text password."""
    pw_bytes = plain.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pw_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    """Verify plain-text password against stored hash."""
    pw_bytes = plain.encode('utf-8')
    hashed_bytes = hashed.encode('utf-8')
    try:
        return bcrypt.checkpw(pw_bytes, hashed_bytes)
    except Exception:
        return False


# ── JWT helpers ──────────────────────────────────────────────────────────────

def create_token(data: dict, expires_minutes: int = JWT_EXPIRE_MINUTES) -> str:
    """Encode a signed JWT with an expiry timestamp."""
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT. Returns payload dict or None on failure."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


def get_token_payload(request: Request) -> Optional[dict]:
    """
    Read and decode the 'access_token' httpOnly cookie.
    Returns the decoded payload dict or None if absent / invalid / expired.
    """
    token = request.cookies.get("access_token")
    if not token:
        return None
    return decode_token(token)


class RedirectException(Exception):
    def __init__(self, url: str):
        self.url = url


def require_admin(request: Request):
    """Dependency to check if user is admin, else redirect to login."""
    payload = get_token_payload(request)
    if not payload or payload.get("role") != "admin":
        raise RedirectException(url="/login")
    return payload


def require_candidate_or_admin(doc_id: str):
    """Dependency creator to check if user is admin or the specific candidate."""
    def dependency(request: Request):
        payload = get_token_payload(request)
        if not payload:
            raise RedirectException(url="/login")
        
        role = payload.get("role")
        if role == "admin":
            return payload
        elif role == "candidate" and payload.get("doc_id") == doc_id:
            return payload
            
        raise RedirectException(url="/login")
    return dependency


# ── Score display helpers (shared by resume.py and auth.py) ─────────────────

def score_meta(score: int) -> dict:
    """Return CSS colour, dim colour and verdict label for a given score."""
    if score >= 75:
        return {
            "score_color":     "#5ec97d",
            "score_color_dim": "rgba(94,201,125,0.18)",
            "verdict":         "Excellent",
        }
    elif score >= 50:
        return {
            "score_color":     "#c9a84c",
            "score_color_dim": "rgba(201,168,76,0.18)",
            "verdict":         "Good",
        }
    else:
        return {
            "score_color":     "#e07070",
            "score_color_dim": "rgba(224,112,112,0.18)",
            "verdict":         "Needs Work",
        }
