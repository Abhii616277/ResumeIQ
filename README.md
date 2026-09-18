# ResumeIQ — AI Resume Screening Platform

ResumeIQ is an AI-powered resume screening web application built with **FastAPI**, **MongoDB/GridFS**, and **Google Gemini**. It provides separate candidate and administrator workflows for uploading resumes, securely authenticating users, extracting resume text, generating an AI-based resume assessment, and presenting the results through a web dashboard.

## ✨ Features

* **AI-powered resume analysis** using Google Gemini
* **Resume scoring from 0–100** using a defined screening rubric
* AI-generated **summary, strengths, and improvement suggestions**
* Supports **PDF, DOC, DOCX, and TXT** resumes
* **PDF/DOCX/DOC/TXT text extraction** before AI analysis
* **MongoDB** for candidate/application metadata
* **GridFS** for storing uploaded resume files
* Separate **Admin** and **Candidate** portals
* Candidate **registration and login**
* **Admin authentication** with JWT
* Password hashing with **bcrypt**
* JWT stored in an **HttpOnly cookie**
* Admin dashboard with candidate statistics, ranking, and processing status
* Resume preview through an authenticated endpoint
* Responsive server-rendered UI using **Jinja2 templates**
* Graceful handling of extraction, AI-service, and parsing failures

## 🧠 How ResumeIQ Works

```text
Resume Upload
     │
     ▼
Validate File Type
     │
     ▼
Store File in MongoDB GridFS
     │
     ▼
Extract Resume Text
(PDF / DOC / DOCX / TXT)
     │
     ▼
Send Text to Google Gemini
     │
     ▼
Structured AI Response
     │
     ├── Score (0–100)
     ├── Summary
     ├── Strengths
     └── Improvements
     │
     ▼
Parse + Persist Result in MongoDB
     │
     ▼
Display Result
     ├── Admin Dashboard
     └── Candidate Dashboard
```

## 📊 AI Scoring Rubric

Gemini evaluates resumes using the following scoring framework:

| Criterion                               |      Weight |
| --------------------------------------- | ----------: |
| Relevant work experience & achievements |      30 pts |
| Education & certifications              |      20 pts |
| Technical / professional skills         |      20 pts |
| Resume clarity, formatting & grammar    |      15 pts |
| Measurable impact / quantified results  |      15 pts |
| **Total**                               | **100 pts** |

This makes the generated score more structured than a purely free-form AI response.

## 🏗️ Project Architecture

The project is organized into separate routing, service, model, template, and utility layers.

```text
ResumeIQ/
├── main.py
├── config.py
├── database.py
├── models/
│   └── schemas.py
├── routers/
│   ├── auth.py
│   └── resume.py
├── services/
│   ├── auth_service.py
│   ├── extractor.py
│   ├── gemini_service.py
│   └── parser.py
├── templates/
│   ├── index.html
│   ├── login_select.html
│   ├── login_admin.html
│   ├── login_candidate.html
│   ├── resume_upload.html
│   ├── candidate_dashboard.html
│   ├── result.html
│   ├── test1.html
│   └── about_us.html
├── static/
│   └── style.css
├── utils/
│   └── logger.py
├── requirements.txt
└── .gitignore
```

### Core Components

#### `main.py`

Creates the FastAPI application, mounts static assets, registers routers, and handles the custom redirect exception.

#### `routers/auth.py`

Contains authentication and candidate account routes:

* Admin login
* Candidate login
* Candidate registration
* Candidate dashboard
* Logout
* Authentication cookie management

#### `routers/resume.py`

Handles the complete resume workflow:

* Resume upload
* Resume retrieval
* Candidate listing
* Candidate statistics
* Resume processing
* AI result rendering

#### `services/auth_service.py`

Provides:

* Password hashing
* Password verification
* JWT creation
* JWT decoding
* Role-based authorization
* Admin/candidate access validation

#### `services/extractor.py`

Extracts text from uploaded resumes based on file type.

| File Type | Library              |
| --------- | -------------------- |
| PDF       | `pdfplumber`         |
| DOCX      | `python-docx`        |
| DOC       | `mammoth`            |
| TXT       | Python text decoding |

DOCX extraction also processes text contained inside tables.

#### `services/gemini_service.py`

Communicates with the Google Gemini API.

The application:

1. Limits the resume input to 12,000 characters.
2. Sends the content with a structured screening prompt.
3. Requests JSON output.
4. Returns the raw AI response to the parser.

#### `services/parser.py`

Converts Gemini's response into structured application data.

It handles:

* Normal JSON responses
* JSON wrapped inside Markdown code fences
* Fallback extraction from responses containing `SCORE: NN`

#### `database.py`

Uses:

* **MongoDB** for application metadata
* **GridFS** for uploaded resume storage

---

## 🔐 Authentication & Authorization

ResumeIQ provides two distinct application roles.

### Candidate

A candidate can:

1. Register with name, email, password, and resume.
2. Sign in using email/password.
3. View their application status.
4. View their AI-generated resume evaluation.
5. Access their own uploaded resume.
6. Log out.

### Administrator

An administrator can:

1. Authenticate through the admin portal.
2. View submitted candidates.
3. View processing statistics.
4. Process individual resumes.
5. Open stored resume files.
6. Review AI-generated screening results.

### Security Mechanisms

ResumeIQ uses:

* `bcrypt` password hashing
* Signed JWT authentication
* JWT expiry
* `HttpOnly` authentication cookies
* Role-based authorization
* Candidate-specific document access checks

---

## 📄 Supported Resume Formats

ResumeIQ accepts:

```text
.pdf
.doc
.docx
.txt
```

The frontend enforces a **10 MB** file-size limit and validates supported extensions before submission.

The backend also validates supported extensions before storing the file.

---

## ⚙️ Technology Stack

### Backend

* Python
* FastAPI
* Uvicorn
* Pydantic
* Jinja2

### AI / NLP

* Google Gemini API
* Structured prompt-based resume evaluation

### Database & Storage

* MongoDB
* PyMongo
* GridFS

### Document Processing

* pdfplumber
* python-docx
* mammoth

### Authentication

* bcrypt
* Passlib
* python-jose
* JWT
* HttpOnly cookies

### Frontend

* HTML5
* CSS3
* JavaScript
* Jinja2 templates

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Abhii616277/ResumeIQ.git
cd ResumeIQ
```

### 2. Create a virtual environment

#### Windows

```powershell
python -m venv venv
venv\Scripts\activate
```

#### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root.

```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=your_database
MONGO_COLLECTION_NAME=your_collection

GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL_NAME=gemini-2.5-flash

ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_admin_password

JWT_SECRET=your_long_random_secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480
JWT_COOKIE_SECURE=False
```

The application validates the required Gemini, admin, and JWT environment variables when starting.

> **Never commit API keys, passwords, JWT secrets, or database credentials to GitHub.**

### 5. Start the application

```bash
uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

---

## 🔌 Application Routes

### Authentication Routes

| Method | Endpoint           | Description                       |
| ------ | ------------------ | --------------------------------- |
| GET    | `/login`           | Portal selection                  |
| GET    | `/login/admin`     | Admin login page                  |
| POST   | `/login/admin`     | Admin authentication              |
| GET    | `/login/candidate` | Candidate login/registration page |
| POST   | `/login/candidate` | Candidate authentication          |
| POST   | `/register`        | Candidate registration            |
| GET    | `/logout`          | Logout                            |

### Resume Routes

| Method | Endpoint               | Description                 |
| ------ | ---------------------- | --------------------------- |
| GET    | `/resume_upload`       | Admin candidate dashboard   |
| POST   | `/upload`              | Upload a resume             |
| GET    | `/process/{doc_id}`    | Process a resume with AI    |
| GET    | `/get-file/{doc_id}`   | Retrieve an uploaded resume |
| GET    | `/candidate/dashboard` | Candidate dashboard         |
| GET    | `/about_us`            | About page                  |

---

## 🤖 AI Analysis

The Gemini service instructs the model to return structured JSON containing:

```json
{
  "score": 84,
  "summary": "Professional overview of the candidate.",
  "strengths": [
    "Strong technical experience",
    "Relevant projects",
    "Clear presentation"
  ],
  "improvements": [
    "Add more quantified achievements",
    "Improve role-specific keyword coverage"
  ]
}
```

The result is parsed and persisted in MongoDB as part of the candidate record.

---

## 📊 Admin Dashboard

The administrator dashboard calculates:

* Total candidates
* Processed candidates
* Pending candidates
* Average processed score
* Highest processed score
* Candidate ranking

Processed candidates are sorted by score, while unprocessed applications remain at the bottom.

---

## 🖥️ User Interface

The frontend uses a dark, gold-accented visual theme with responsive layouts.

The application includes:

* Animated score rings
* Candidate dashboards
* AI summary cards
* Strength and improvement sections
* Resume upload interface
* Drag-and-drop file selection
* Responsive mobile layouts
* Animated transitions and visual feedback

---

## 🛡️ Error Handling

The resume processing pipeline separates common failure cases:

```text
Invalid Document ID
        ↓
File Retrieval Error
        ↓
Text Extraction Failure
        ↓
Gemini API Failure
        ↓
AI Response Parsing Failure
        ↓
Database Persistence Failure
```

The application provides user-facing error pages for major processing failures and logs backend errors through the project's logging utility.

---

## 🔒 Security Considerations

The repository is configured to ignore `.env` files and Python cache files.

Before deploying publicly, review the security configuration carefully.

### Recommended production configuration

* Use a strong random `JWT_SECRET`
* Set `JWT_COOKIE_SECURE=True` when running behind HTTPS
* Keep all database credentials in environment variables
* Enforce server-side file-size validation
* Add rate limiting
* Add request/input validation
* Restrict allowed origins where appropriate
* Add automated security tests
* Use a production MongoDB deployment

### Important

The current repository contains database configuration that should **not** be stored as a hard-coded credential in source code.

Use:

```python
MongoClient(MONGO_URI)
```

with `MONGO_URI` supplied through the environment instead.

---

## 🧪 Current Project Scope

ResumeIQ currently focuses on:

* Resume intake
* Candidate authentication
* Admin authentication
* Resume storage
* Document text extraction
* AI resume screening
* Resume scoring
* Candidate dashboards
* Admin screening dashboards

It is not intended to replace a complete Applicant Tracking System (ATS).

The AI-generated score should be treated as **decision-support information**, not as a definitive measure of candidate ability or hiring suitability.

---

## 🚧 Future Improvements

Potential future extensions include:

* Job-description-based resume matching
* ATS keyword analysis
* Skill extraction and normalization
* Job-specific scoring
* Candidate search and filtering
* Recruiter notes
* Application status pipelines
* Exportable screening reports
* Background processing with Celery/RQ
* Automated testing
* CI/CD pipelines
* OCR for image-based resumes
* Improved production deployment architecture

---

## 👨‍💻 Author

**Abhinav Raj**

GitHub:
https://github.com/Abhii616277

Project:
https://github.com/Abhii616277/ResumeIQ

---

## 📜 License

No license file is currently included in the repository.

Add a license such as **MIT** before positioning the project as open-source software for unrestricted reuse.

---

## ⚠️ Disclaimer

ResumeIQ provides AI-assisted resume analysis for screening support. AI-generated scores, summaries, strengths, and recommendations can contain inaccuracies and should be reviewed by a human before being used for consequential hiring decisions.
