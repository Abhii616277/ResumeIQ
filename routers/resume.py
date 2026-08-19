"""
routers/resume.py — all résumé-related HTTP endpoints.
"""
from bson import ObjectId
from fastapi import APIRouter, Request, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse, Response, RedirectResponse
from fastapi.templating import Jinja2Templates

from database import collection, fs
from services.extractor import extract_text
from services.gemini_service import analyze_resume
from services.parser import parse_ai_response
from services.auth_service import require_admin, get_token_payload, RedirectException
from utils.logger import logger


def _score_meta(score: int) -> dict:
    """Return display colour, dim colour and verdict label for a score."""
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


def _error_page(title: str, message: str, status_code: int = 500) -> HTMLResponse:
    """Return a styled error HTML page."""
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>Error — {title}</title>
      <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Cormorant+Garamond:wght@300;400&display=swap" rel="stylesheet" />
      <style>
        *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
        body{{min-height:100vh;display:grid;place-items:center;background:#0c0b10;
              font-family:'Cormorant Garamond',Georgia,serif;color:#e8e0d0;}}
        .box{{max-width:540px;text-align:center;padding:60px 40px;
              border:1px solid rgba(224,112,112,0.3);border-radius:4px;
              background:#13111a;box-shadow:0 40px 80px rgba(0,0,0,0.5);}}
        .icon{{font-size:3rem;margin-bottom:24px;}}
        h1{{font-family:'Playfair Display',serif;font-size:1.8rem;color:#e07070;margin-bottom:16px;}}
        p{{font-size:1rem;line-height:1.8;color:#998f82;margin-bottom:32px;}}
        a{{display:inline-block;padding:12px 28px;border:1px solid rgba(201,168,76,0.4);
           border-radius:2px;color:#c9a84c;text-decoration:none;font-size:0.8rem;
           letter-spacing:0.2em;text-transform:uppercase;transition:background 0.2s;}}
        a:hover{{background:rgba(201,168,76,0.1);}}
      </style>
    </head>
    <body>
      <div class="box">
        <div class="icon">&#x26A0;&#xFE0F;</div>
        <h1>{title}</h1>
        <p>{message}</p>
        <a href="/resume_upload">&larr; Back to Candidates</a>
      </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=status_code)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

ALLOWED_EXTS = {"pdf", "doc", "docx", "txt"}

MEDIA_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "txt": "text/plain",
}


@router.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    payload = get_token_payload(request)
    if payload:
        if payload.get("role") == "admin":
            return RedirectResponse(url="/resume_upload", status_code=302)
        elif payload.get("role") == "candidate":
            return RedirectResponse(url="/candidate/dashboard", status_code=302)
    return RedirectResponse(url="/login", status_code=302)


@router.get("/about_us", response_class=HTMLResponse)
async def read_about(request: Request):
    return templates.TemplateResponse("about_us.html", {"request": request})


@router.get("/resume_upload", response_class=HTMLResponse)
async def read_get_started(request: Request, current_user = Depends(require_admin)):
    docs = collection.find({})
    newdocs = []
    for doc in docs:
        ai_data = doc.get("ai_result") or {}
        score = ai_data.get("score") if ai_data else doc.get("score")
        filename = doc.get("filename", "")
        file_ext = filename.rsplit(".", 1)[-1].upper() if "." in filename else "?"

        newdocs.append({
            "firstName": doc["personalInfo"]["firstName"],
            "lastName": doc["personalInfo"]["lastName"],
            "email": doc["personalInfo"]["email"],
            "score": score,
            "score_str": str(score) if score is not None else "",
            "summary": ai_data.get("summary") or doc.get("processed_text") or "",
            "strengths": ai_data.get("strengths", []),
            "improvements": ai_data.get("improvements", []),
            "_id": str(doc["_id"]),
            "filename": filename,
            "file_ext": file_ext,
            "is_processed": score is not None,
            "bar_width": str(score) if score is not None else "0",
            "bar_class": "high" if (score or 0) >= 75 else ("mid" if (score or 0) >= 50 else "low"),
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

    # Admin Statistics
    total_candidates = len(newdocs)
    processed_candidates = sum(1 for d in newdocs if d["is_processed"])
    average_score = round(sum(d["score"] for d in newdocs if d["is_processed"]) / processed_candidates) if processed_candidates else 0
    top_score = max((d["score"] for d in newdocs if d["is_processed"]), default=0)

    return templates.TemplateResponse(
        "test1.html",
        {
            "request": request,
            "newdocs": newdocs,
            "stats": {
                "total": total_candidates,
                "processed": processed_candidates,
                "pending": total_candidates - processed_candidates,
                "average": average_score,
                "top": top_score
            }
        }
    )


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    firstName: str = Form(...),
    lastName: str = Form(...),
    email: str = Form(...),
    current_user = Depends(require_admin)
):
    logger.info(f"Upload started: {file.filename}")
    contents = await file.read()

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTS:
        return {"error": f"Unsupported file type: .{ext}. Allowed: {', '.join(ALLOWED_EXTS)}"}

    file_id = fs.put(contents, filename=file.filename)
    logger.info(f"Stored in GridFS: {file_id}")

    collection.insert_one({
        "personalInfo": {
            "firstName": firstName,
            "lastName": lastName,
            "email": email,
        },
        "file_id": file_id,
        "filename": file.filename,
    })
    logger.info("Metadata stored")
    return {"message": "Uploaded successfully"}


@router.get("/get-file/{doc_id}")
async def get_file(request: Request, doc_id: str):
    # Verify JWT authorization and access permissions
    payload = get_token_payload(request)
    if not payload:
        return RedirectResponse(url="/login", status_code=302)
    
    role = payload.get("role")
    if role == "candidate" and payload.get("doc_id") != doc_id:
        return RedirectResponse(url="/login", status_code=302)
    elif role not in ("admin", "candidate"):
        return RedirectResponse(url="/login", status_code=302)

    doc = collection.find_one({"_id": ObjectId(doc_id)})
    if not doc:
        return {"error": "Document not found"}

    file_obj = fs.get(doc["file_id"])
    content = file_obj.read()

    ext = doc["filename"].rsplit(".", 1)[-1].lower() if "." in doc["filename"] else ""
    media_type = MEDIA_TYPES.get(ext, "application/octet-stream")

    return Response(
        content,
        media_type=media_type,
        headers={"Content-Disposition": f"inline; filename={doc['filename']}"}
    )


@router.get("/process/{doc_id}", response_class=HTMLResponse)
async def process_resume(request: Request, doc_id: str, current_user = Depends(require_admin)):
    try:
        doc = collection.find_one({"_id": ObjectId(doc_id)})
    except Exception:
        return _error_page("Invalid ID", "The document ID is invalid or malformed.", 400)

    if not doc:
        return _error_page("Not Found", "No résumé document was found with that ID.", 404)

    # 1. Read file from GridFS
    try:
        file_obj = fs.get(doc["file_id"])
        content = file_obj.read()
    except Exception as e:
        logger.error(f"[GridFS read error] {e}")
        return _error_page("File Read Error", "Could not retrieve the uploaded file from storage. Please re-upload and try again.")

    filename = doc.get("filename", "resume.pdf")

    # 2. Extract text based on file type
    text = extract_text(content, filename)
    if not text.strip():
        return _error_page(
            "Text Extraction Failed",
            f"Could not extract readable text from <strong>{filename}</strong>. "
            "The file may be image-based, password-protected, or corrupt. "
            "Please upload a text-selectable version.",
            422,
        )

    logger.info(f"Extracted {len(text)} characters from {filename}")

    # 3. Send to Gemini
    try:
        raw = analyze_resume(text)
    except Exception as e:
        logger.error(f"[Gemini API error] {e}")
        err_msg = str(e)
        if "leaked" in err_msg.lower() or "PERMISSION_DENIED" in err_msg or "403" in err_msg:
            user_msg = (
                "Your Gemini API key has been <strong>flagged as leaked</strong> by Google and is now blocked. "
                "Please generate a new key at "
                "<a href='https://aistudio.google.com/app/apikey' target='_blank' style='color:#c9a84c'>Google AI Studio</a> "
                "and update it in your <code>.env</code> file."
            )
        else:
            user_msg = f"The AI analysis service is temporarily unavailable. Details: {e}"
        return _error_page("AI Service Error", user_msg)

    # 4. Parse structured response
    try:
        ai_result = parse_ai_response(raw)
        score = ai_result["score"]
        logger.info(f"Score: {score}")
    except Exception as e:
        logger.error(f"[Parse error] {e}")
        return _error_page("Parse Error", "The AI returned an unexpected response format. Please try scoring again.")

    # 5. Persist to MongoDB
    try:
        collection.update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {
                "processed_text": ai_result["summary"],  # backward-compat field
                "score": score,
                "ai_result": ai_result,
            }}
        )
    except Exception as e:
        logger.error(f"[MongoDB update error] {e}")
        # Non-fatal — the result was computed, just not saved. Proceed to render.

    # 6. Render result page
    personal = doc.get("personalInfo", {})
    meta = _score_meta(score)

    return templates.TemplateResponse(
        "result.html",
        {
            "request":          request,
            "doc_id":           doc_id,
            "firstName":        personal.get("firstName", ""),
            "lastName":         personal.get("lastName", ""),
            "email":            personal.get("email", ""),
            "filename":         filename,
            "score":            score,
            "summary":          ai_result["summary"],
            "strengths":        ai_result["strengths"],
            "improvements":     ai_result["improvements"],
            "score_color":      meta["score_color"],
            "score_color_dim":  meta["score_color_dim"],
            "verdict":          meta["verdict"],
        },
    )
