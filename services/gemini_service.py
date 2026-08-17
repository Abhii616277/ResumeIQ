"""
services/gemini_service.py — communication with Google Gemini for résumé analysis.
"""
import google.generativeai as genai

from config import GEMINI_API_KEY, GEMINI_MODEL_NAME
from utils.logger import logger

genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel(GEMINI_MODEL_NAME)

GEMINI_PROMPT = """\
You are a professional HR recruiter. Analyze the following résumé text and return ONLY a valid JSON object — no extra text, no markdown fences, no explanation outside the JSON.

The JSON must have exactly these keys:
{{
  "score": <integer 0-100 reflecting overall résumé quality>,
  "summary": "<2-3 sentence professional overview of the candidate>",
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "improvements": ["<improvement 1>", "<improvement 2>"]
}}

Scoring rubric (use all criteria):
- Relevant work experience & achievements  (30 pts)
- Education & certifications               (20 pts)
- Technical / professional skills          (20 pts)
- Resume clarity, formatting & grammar     (15 pts)
- Measurable impact / quantified results   (15 pts)

Résumé text:
{text}
"""

# Cap input to stay comfortably within token limits
MAX_INPUT_CHARS = 12000


def analyze_resume(text: str) -> str:
    """
    Send résumé text to Gemini and return the raw response text.
    Raises whatever exception the underlying SDK call raises; callers
    should handle/log as appropriate.
    """
    prompt = GEMINI_PROMPT.format(text=text[:MAX_INPUT_CHARS])
    logger.info(f"Sending {len(prompt)} characters to Gemini ({GEMINI_MODEL_NAME})")
    response = _model.generate_content(prompt)
    return response.text
