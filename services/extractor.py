"""
services/extractor.py — extract plain text from résumé files.

Supports PDF, DOCX, DOC, and TXT. Unsupported types or extraction failures
return an empty string, which callers should treat as "no text found".
"""
import io

import pdfplumber

from utils.logger import logger


def extract_text(content: bytes, filename: str) -> str:
    """
    Extract plain text from PDF, DOCX, DOC, or TXT files.
    Returns an empty string if extraction fails or the type is unsupported.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "pdf":
        return _extract_pdf(content)
    elif ext == "docx":
        return _extract_docx(content)
    elif ext == "doc":
        return _extract_doc(content)
    elif ext == "txt":
        return _extract_txt(content)
    else:
        logger.warning(f"Unsupported extension for extraction: .{ext}")
        return ""


def _extract_pdf(content: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as e:
        logger.error(f"[PDF extraction error] {e}")
        return ""


def _extract_docx(content: bytes) -> str:
    try:
        import docx  # python-docx

        document = docx.Document(io.BytesIO(content))
        paragraphs = [p.text for p in document.paragraphs if p.text.strip()]

        # Also grab table cells
        for table in document.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        paragraphs.append(cell.text.strip())

        return "\n".join(paragraphs)
    except Exception as e:
        logger.error(f"[DOCX extraction error] {e}")
        return ""


def _extract_doc(content: bytes) -> str:
    # Try mammoth first (best quality for .doc), fall back to a lossy decode
    try:
        import mammoth

        result = mammoth.extract_raw_text(io.BytesIO(content))
        return result.value
    except Exception as e:
        logger.error(f"[DOC/mammoth error] {e}")
        try:
            return content.decode("latin-1", errors="ignore")
        except Exception:
            return ""


def _extract_txt(content: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("ascii", errors="ignore")
