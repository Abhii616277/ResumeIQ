"""
routers/resume.py — all résumé-related HTTP endpoints.
"""
from bson import ObjectId
from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from database import collection, fs
from services.extractor import extract_text
from services.gemini_service import analyze_resume
from services.parser import parse_ai_response
from utils.logger import logger

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
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/about_us", response_class=HTMLResponse)
async def read_about(request: Request):
    return templates.TemplateResponse("about_us.html", {"request": request})


@router.get("/resume_upload", response_class=HTMLResponse)
async def read_get_started(request: Request):
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

    return templates.TemplateResponse(
        "test1.html",
        {"request": request, "newdocs": newdocs}
    )


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    firstName: str = Form(...),
    lastName: str = Form(...),
    email: str = Form(...),
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
async def get_file(doc_id: str):
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


@router.get("/process/{doc_id}")
async def process_resume(doc_id: str):
    doc = collection.find_one({"_id": ObjectId(doc_id)})
    if not doc:
        return {"error": "Document not found"}

    # 1. Read file from GridFS
    file_obj = fs.get(doc["file_id"])
    content = file_obj.read()
    filename = doc.get("filename", "resume.pdf")

    # 2. Extract text based on file type
    text = extract_text(content, filename)
    if not text.strip():
        return {"error": f"Could not extract text from {filename}. The file may be scanned/image-based or corrupt."}

    logger.info(f"Extracted {len(text)} characters from {filename}")

    # 3. Send to Gemini
    raw = analyze_resume(text)

    # 4. Parse structured response
    ai_result = parse_ai_response(raw)
    logger.info(f"Score: {ai_result['score']}")

    # 5. Persist to MongoDB
    collection.update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": {
            "processed_text": ai_result["summary"],  # backward-compat field
            "score": ai_result["score"],
            "ai_result": ai_result,
        }}
    )

    return {
        "message": "Processed successfully",
        "score": ai_result["score"],
        "summary": ai_result["summary"],
        "strengths": ai_result["strengths"],
        "improvements": ai_result["improvements"],
    }
