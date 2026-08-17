
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from routers import resume

app = FastAPI(title="Resume Analyzer")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(resume.router)
