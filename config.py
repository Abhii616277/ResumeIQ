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

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Add it to your environment or a .env file."
    )
