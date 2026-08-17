from fastapi import FastAPI, Request, UploadFile, File, Form
import google.generativeai as genai
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
from bson import ObjectId
import gridfs
import pdfplumber
import io
import json
import re

# SERVER  INITIALIZATION
app = FastAPI()
# HTML RENDERING FILESYSTEM SETUP
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# DATABASE SETUP
conn = MongoClient("mongodb+srv://rj616277_db_user:Rajkumar12@cluster0.qitfhku.mongodb.net/")
db = conn["Node"]
collection = db["node"]
fs = gridfs.GridFS(db)

# ──────────────    ───────────────────────────────
# Helper: extract plain text from any supported format
# ─────────────────────────────────────────────
def extract_text(content: bytes, filename: str) -> str:
    """
    Extract plain text from PDF, DOCX, DOC, or TXT files.
    Returns an empty string if extraction fails.
    """
    ext = filename.rsplit(".", 1)[-1].lower()

    if ext == "pdf":
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception as e:
            print(f"[PDF extraction error] {e}")
            return ""

    elif ext == "docx":
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
            print(f"[DOCX extraction error] {e}")
            return ""

    elif ext == "doc":
        # Try mammoth first (best quality for .doc), fall back to textract
        try:
            import mammoth
            result = mammoth.extract_raw_text(io.BytesIO(content))
            return result.value
        except Exception as e:
            print(f"[DOC/mammoth error] {e}")
            # Fallback: try reading as latin-1 encoded text (some .doc files are plain-ish)
            try:
                return content.decode("latin-1", errors="ignore")
            except Exception:
                return ""

    elif ext == "txt":
        # Try UTF-8 first, fall back to latin-1
        for encoding in ("utf-8", "utf-16", "latin-1"):
            try:
                return content.decode(encoding)
            except (UnicodeDecodeError, Exception):
                continue
        return content.decode("ascii", errors="ignore")

    else:
        return ""


# ─────────────────────────────────────────────
# Helper: parse score + summary from Gemini JSON response
# ─────────────────────────────────────────────
def parse_ai_response(raw_text: str) -> dict:
    """
    Expects Gemini to return a JSON block. Gracefully falls back if parsing fails.
    Returns {"score": int, "summary": str, "strengths": [...], "improvements": [...]}
    """
    # Try to locate a JSON block (Gemini sometimes wraps it in ```json ... ```)
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if json_match:
        raw_text = json_match.group(1)

    try:
        data = json.loads(raw_text)
        return {
            "score":        int(data.get("score", 0)),
            "summary":      data.get("summary", ""),
            "strengths":    data.get("strengths", []),
            "improvements": data.get("improvements", []),
        }
    except (json.JSONDecodeError, ValueError):
        # Fallback: try to pull a SCORE: line
        score_match = re.search(r"SCORE[:\s]+(\d{1,3})", raw_text, re.IGNORECASE)
        score = int(score_match.group(1)) if score_match else 0
        return {
            "score":        min(score, 100),
            "summary":      raw_text.strip(),
            "strengths":    [],
            "improvements": [],
        }


# ─────────────────────────────────────────────
# Gemini setup
# ─────────────────────────────────────────────
import google.generativeai as genai

genai.configure(api_key="AIzaSyATfovNvEjrCLqoxG1F2rqT6epbbd9BVlE")
model = genai.GenerativeModel("gemini-2.5-flash")

GEMINI_PROMPT = """\
You are a professional HR recruiter. Analyze the following résumé text and return ONLY a valid JSON object — no extra text, no markdown fences, no explanation outside the JSON.

The JSON must have exactly these keys:
{{
  "score": <integer 0–100 reflecting overall résumé quality>,
  "summary": "<2–3 sentence professional overview of the candidate>",
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


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/about_us", response_class=HTMLResponse)
async def read_about(request: Request):
    return templates.TemplateResponse("about_us.html", {"request": request})


@app.get("/resume_upload", response_class=HTMLResponse)
async def read_get_started(request: Request):
    docs = collection.find({})
    newdocs = []
    for doc in docs:
        ai_data  = doc.get("ai_result") or {}
        score    = ai_data.get("score") if ai_data else doc.get("score")
        filename = doc.get("filename", "")
        # Safe extension extraction — no Jinja2 gymnastics needed
        file_ext = filename.rsplit(".", 1)[-1].upper() if "." in filename else "?"

        newdocs.append({
            "firstName":    doc["personalInfo"]["firstName"],
            "lastName":     doc["personalInfo"]["lastName"],
            "email":        doc["personalInfo"]["email"],
            "score":        score,                          # int or None
            "score_str":    str(score) if score is not None else "",
            "summary":      ai_data.get("summary") or doc.get("processed_text") or "",
            "strengths":    ai_data.get("strengths", []),
            "improvements": ai_data.get("improvements", []),
            "_id":          str(doc["_id"]),
            "filename":     filename,
            "file_ext":     file_ext,
            "is_processed": score is not None,
            # bar width for CSS (0-100, safe string)
            "bar_width":    str(score) if score is not None else "0",
            # colour class
            "bar_class":    "high" if (score or 0) >= 75 else ("mid" if (score or 0) >= 50 else "low"),
        })

    # Sort: processed first (descending score), unprocessed last
    newdocs.sort(key=lambda d: d["score"] if d["score"] is not None else -1, reverse=True)

    # Assign display rank only to processed candidates
    rank = 1
    for d in newdocs:
        if d["is_processed"]:
            d["rank"] = str(rank)
            rank += 1
        else:
            d["rank"] = "—"

    return templates.TemplateResponse(
        "test1.html",
        {"request": request, "newdocs": newdocs}
    )


@app.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    firstName: str = Form(...),
    lastName: str = Form(...),
    email: str = Form(...)
):
    print("Upload started:", file.filename)
    contents = await file.read()

    # Validate extension on the server side too
    allowed_exts = {"pdf", "doc", "docx", "txt"}
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_exts:
        return {"error": f"Unsupported file type: .{ext}. Allowed: {', '.join(allowed_exts)}"}

    file_id = fs.put(contents, filename=file.filename)
    print("Stored in GridFS:", file_id)

    collection.insert_one({
        "personalInfo": {
            "firstName": firstName,
            "lastName":  lastName,
            "email":     email,
        },
        "file_id":  file_id,
        "filename": file.filename,
    })
    print("Metadata stored")
    return {"message": "Uploaded successfully"}


@app.get("/get-file/{doc_id}")
async def get_file(doc_id: str):
    doc = collection.find_one({"_id": ObjectId(doc_id)})
    if not doc:
        return {"error": "Document not found"}

    file_obj = fs.get(doc["file_id"])
    content   = file_obj.read()

    # Determine media type from extension
    ext = doc["filename"].rsplit(".", 1)[-1].lower() if "." in doc["filename"] else ""
    media_types = {
        "pdf":  "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "doc":  "application/msword",
        "txt":  "text/plain",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    return Response(
        content,
        media_type=media_type,
        headers={"Content-Disposition": f"inline; filename={doc['filename']}"}
    )


@app.get("/process/{doc_id}")
async def process_resume(doc_id: str):
    doc = collection.find_one({"_id": ObjectId(doc_id)})
    if not doc:
        return {"error": "Document not found"}

    # --- 1. Read file from GridFS ---
    file_obj = fs.get(doc["file_id"])
    content  = file_obj.read()
    filename = doc.get("filename", "resume.pdf")

    # --- 2. Extract text based on file type ---
    text = extract_text(content, filename)
    if not text.strip():
        return {"error": f"Could not extract text from {filename}. The file may be scanned/image-based or corrupt."}

    print(f"Extracted {len(text)} characters from {filename}")

    # --- 3. Send to Gemini ---
    prompt   = GEMINI_PROMPT.format(text=text[:12000])   # cap at ~12 k chars to stay within token limits
    response = model.generate_content(prompt)
    raw      = response.text

    # --- 4. Parse structured response ---
    ai_result = parse_ai_response(raw)
    print(f"Score: {ai_result['score']}")

    # --- 5. Persist to MongoDB ---
    collection.update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": {
            "processed_text": ai_result["summary"],   # backward-compat field
            "score":          ai_result["score"],
            "ai_result":      ai_result,
        }}
    )

    return {
        "message":  "Processed successfully",
        "score":    ai_result["score"],
        "summary":  ai_result["summary"],
        "strengths":    ai_result["strengths"],
        "improvements": ai_result["improvements"],
    }