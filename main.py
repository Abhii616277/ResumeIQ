from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from routers import resume, auth
from services.auth_service import RedirectException

app = FastAPI(title="Resume Analyzer")

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.exception_handler(RedirectException)
async def redirect_exception_handler(request: Request, exc: RedirectException):
    return RedirectResponse(url=exc.url, status_code=302)


app.include_router(auth.router)
app.include_router(resume.router)

