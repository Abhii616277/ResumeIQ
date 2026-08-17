"""
models/schemas.py — Pydantic models for API responses.
"""
from typing import List, Optional

from pydantic import BaseModel


class AIResult(BaseModel):
    score: int
    summary: str
    strengths: List[str] = []
    improvements: List[str] = []


class UploadResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    error: str


class ProcessResponse(BaseModel):
    message: str
    score: int
    summary: str
    strengths: List[str]
    improvements: List[str]


class CandidateView(BaseModel):
    """Shape used when rendering the resume list page."""
    firstName: str
    lastName: str
    email: str
    score: Optional[int] = None
    score_str: str
    summary: str
    strengths: List[str] = []
    improvements: List[str] = []
    id: str
    filename: str
    file_ext: str
    is_processed: bool
    bar_width: str
    bar_class: str
    rank: str
