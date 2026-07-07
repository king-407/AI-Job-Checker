from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .agent_workflow import analyze_job_fit, answer_follow_up, session_store
from .models import AnalyzeRequest, AnalyzeResponse, ChatRequest, ChatResponse
from .pdf_utils import extract_pdf_text

app = FastAPI(
    title="Job AI",
    description="AI Job Fit Copilot using OpenAI Agents SDK",
    version="0.1.0",
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "name": "Job AI",
        "docs": "/docs",
        "flow": "resume + job description -> parsed profiles -> deterministic score -> fit report",
    }


@app.post("/sessions")
def create_session() -> dict[str, str]:
    state = session_store.create()
    return {"session_id": state.session_id}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    return await analyze_job_fit(
        resume_text=request.resume_text,
        job_description=request.job_description,
        session_id=request.session_id,
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        return await answer_follow_up(request.session_id, request.message)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/extract-resume-text")
async def extract_resume_text(file: UploadFile = File(...)) -> dict[str, str]:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Please upload a PDF file")

    text = extract_pdf_text(await file.read())
    if not text:
        raise HTTPException(status_code=422, detail="Could not extract text from this PDF")

    return {"text": text}
