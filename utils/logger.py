"""
utils/logger.py — shared logger configuration.

Usage:
    from utils.logger import logger
    logger.info("message")
"""
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger("resume_app")
