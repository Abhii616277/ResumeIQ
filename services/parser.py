"""
services/parser.py — parse score + summary from Gemini's raw text response.
"""
import json
import re


def parse_ai_response(raw_text: str) -> dict:
    """
    Expects Gemini to return a JSON block. Gracefully falls back if parsing fails.
    Returns {"score": int, "summary": str, "strengths": [...], "improvements": [...]}
    """
    # Gemini sometimes wraps its JSON in ```json ... ``` fences
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if json_match:
        raw_text = json_match.group(1)

    try:
        data = json.loads(raw_text)
        return {
            "score": int(data.get("score", 0)),
            "summary": data.get("summary", ""),
            "strengths": data.get("strengths", []),
            "improvements": data.get("improvements", []),
        }
    except (json.JSONDecodeError, ValueError):
        # Fallback: try to pull a "SCORE: NN" line out of free text
        score_match = re.search(r"SCORE[:\s]+(\d{1,3})", raw_text, re.IGNORECASE)
        score = int(score_match.group(1)) if score_match else 0
        return {
            "score": min(score, 100),
            "summary": raw_text.strip(),
            "strengths": [],
            "improvements": [],
        }
