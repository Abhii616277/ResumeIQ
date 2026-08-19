"""
routers/auth.py — all authentication and login/registration routes.
"""
from fastapi import APIRouter, Request, Form, UploadFile, File, Response, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId

from database import collection, fs
from services.auth_service import hash_password, verify_password, create_token, get_token_payload, score_meta
from config import ADMIN_USERNAME, ADMIN_PASSWORD, JWT_COOKIE_SECURE

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
async def login_select(request: Request):
    # If already logged in, redirect to respective dashboard
    payload = get_token_payload(request)
    if payload:
        if payload.get("role") == "admin":
            return RedirectResponse(url="/resume_upload", status_code=302)
        elif payload.get("role") == "candidate":
            return RedirectResponse(url="/candidate/dashboard", status_code=302)
    return templates.TemplateResponse("login_select.html", {"request": request})


@router.get("/login/admin", response_class=HTMLResponse)
async def login_admin_get(request: Request):
    payload = get_token_payload(request)
    if payload and payload.get("role") == "admin":
        return RedirectResponse(url="/resume_upload", status_code=302)
    return templates.TemplateResponse("login_admin.html", {"request": request})


@router.post("/login/admin")
async def login_admin_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        token = create_token({"sub": username, "role": "admin"})
        response = RedirectResponse(url="/resume_upload", status_code=302)
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=JWT_COOKIE_SECURE,
            max_age=28800, # 8 hours
            samesite="lax"
        )
        return response
    
    return templates.TemplateResponse(
        "login_admin.html",
        {"request": request, "error": "Invalid admin username or password"}
    )


@router.get("/login/candidate", response_class=HTMLResponse)
async def login_candidate_get(request: Request):
    payload = get_token_payload(request)
    if payload and payload.get("role") == "candidate":
        return RedirectResponse(url="/candidate/dashboard", status_code=302)
    return templates.TemplateResponse("login_candidate.html", {"request": request, "active_tab": "login"})


@router.post("/login/candidate")
async def login_candidate_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    # Find candidate
    doc = collection.find_one({"personalInfo.email": email.strip().lower()})
    if doc and "hashed_password" in doc:
        if verify_password(password, doc["hashed_password"]):
            token = create_token({"sub": email, "role": "candidate", "doc_id": str(doc["_id"])})
            response = RedirectResponse(url="/candidate/dashboard", status_code=302)
            response.set_cookie(
                key="access_token",
                value=token,
                httponly=True,
                secure=JWT_COOKIE_SECURE,
                max_age=28800,
                samesite="lax"
            )
            return response
            
    return templates.TemplateResponse(
        "login_candidate.html",
        {"request": request, "active_tab": "login", "error": "Invalid email or password"}
    )


@router.post("/register")
async def register_post(
    request: Request,
    firstName: str = Form(...),
    lastName: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    file: UploadFile = File(...)
):
    email_clean = email.strip().lower()
    
    # Check if candidate already exists
    existing = collection.find_one({"personalInfo.email": email_clean})
    if existing:
        return templates.TemplateResponse(
            "login_candidate.html",
            {
                "request": request,
                "active_tab": "register",
                "error": "Email is already registered. Please login instead."
            }
        )
        
    # Read file and put in GridFS
    contents = await file.read()
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    allowed_exts = {"pdf", "doc", "docx", "txt"}
    
    if ext not in allowed_exts:
        return templates.TemplateResponse(
            "login_candidate.html",
            {
                "request": request,
                "active_tab": "register",
                "error": f"Unsupported file type: .{ext}. Allowed: {', '.join(allowed_exts)}"
            }
        )
        
    file_id = fs.put(contents, filename=file.filename)
    hashed_pwd = hash_password(password)
    
    # Store in MongoDB
    new_doc = {
        "personalInfo": {
            "firstName": firstName.strip(),
            "lastName": lastName.strip(),
            "email": email_clean,
        },
        "hashed_password": hashed_pwd,
        "file_id": file_id,
        "filename": file.filename,
        "role": "candidate"
    }
    
    result = collection.insert_one(new_doc)
    doc_id = str(result.inserted_id)
    
    # Auto-login after registration
    token = create_token({"sub": email_clean, "role": "candidate", "doc_id": doc_id})
    response = RedirectResponse(url="/candidate/dashboard", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=JWT_COOKIE_SECURE,
        max_age=28800,
        samesite="lax"
    )
    return response


@router.get("/candidate/dashboard", response_class=HTMLResponse)
async def candidate_dashboard(request: Request):
    payload = get_token_payload(request)
    if not payload or payload.get("role") != "candidate":
        return RedirectResponse(url="/login", status_code=302)
        
    doc_id = payload.get("doc_id")
    doc = collection.find_one({"_id": ObjectId(doc_id)})
    if not doc:
        return RedirectResponse(url="/logout", status_code=302)
        
    score = doc.get("score")
    is_processed = score is not None
    ai_data = doc.get("ai_result") or {}
    
    meta = score_meta(score) if is_processed else {
        "score_color": "#7a7265",
        "score_color_dim": "rgba(122,114,101,0.18)",
        "verdict": "Pending review"
    }
    
    return templates.TemplateResponse(
        "candidate_dashboard.html",
        {
            "request": request,
            "firstName": doc["personalInfo"]["firstName"],
            "lastName": doc["personalInfo"]["lastName"],
            "email": doc["personalInfo"]["email"],
            "filename": doc.get("filename", ""),
            "score": score,
            "is_processed": is_processed,
            "summary": ai_data.get("summary") or doc.get("processed_text") or "",
            "strengths": ai_data.get("strengths", []),
            "improvements": ai_data.get("improvements", []),
            "score_color": meta["score_color"],
            "score_color_dim": meta["score_color_dim"],
            "verdict": meta["verdict"],
        }
    )


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response
