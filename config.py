"""
config.py — centralized environment variable configuration.

Set these in a .env file (loaded via python-dotenv) or in your shell/deployment
environment. Never commit real secrets to source control.
"""
import os
from dotenv import load_dotenv

load_dotenv()  # loads variables from a .env file if present

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "Node")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "node")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")

# ── Admin credentials ────────────────────────────────────────────────────────
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# ── JWT settings ─────────────────────────────────────────────────────────────
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
JWT_COOKIE_SECURE = os.getenv("JWT_COOKIE_SECURE", "True").lower() == "true"

# ── Startup validation ────────────────────────────────────────────────────────
_missing = [
    name for name, val in [
        ("GEMINI_API_KEY", GEMINI_API_KEY),
        ("ADMIN_USERNAME", ADMIN_USERNAME),
        ("ADMIN_PASSWORD", ADMIN_PASSWORD),
        ("JWT_SECRET", JWT_SECRET),
    ] if not val
]
if _missing:
    raise RuntimeError(
        f"Missing required environment variables: {', '.join(_missing)}. "
        "Add them to your .env file."
    )

