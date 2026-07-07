from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field

from dotenv import load_dotenv
from openai import AsyncOpenAI

from agents import Agent, OpenAIChatCompletionsModel, Runner, function_tool, trace

try:
    from agents import SQLiteSession
except ImportError:  # pragma: no cover - older SDK fallback
    SQLiteSession = None

try:
    from agents import set_tracing_export_api_key
except ImportError:  # pragma: no cover - older SDK fallback
    set_tracing_export_api_key = None

from .models import (
    AnalyzeResponse,
    ChatResponse,
    DeterministicScore,
    FinalReport,
    FitAnalysis,
    JobProfile,
    ResumeProfile,
)
from .scoring import calculate_fit_score

load_dotenv()


def build_model():
    use_gemini = os.getenv("USE_GEMINI", "false").lower() == "true"

    if use_gemini:
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise RuntimeError("USE_GEMINI=true but GOOGLE_API_KEY is missing")

        gemini_client = AsyncOpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=google_api_key,
        )
        return OpenAIChatCompletionsModel(
            model=os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash-lite"),
            openai_client=gemini_client,
        )

    return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


tracing_key = os.getenv("OPENAI_TRACING_API_KEY") or os.getenv("OPENAI_API_KEY")
if tracing_key and set_tracing_export_api_key:
    set_tracing_export_api_key(tracing_key)

MODEL = build_model()


@function_tool
def calculate_fit_score_tool(resume_profile_json: str, job_profile_json: str) -> str:
    """
    Calculate a deterministic job-fit score from a parsed resume profile and parsed job profile.

    Args:
        resume_profile_json: JSON string matching the ResumeProfile schema.
        job_profile_json: JSON string matching the JobProfile schema.
    """
    resume_profile = ResumeProfile.model_validate_json(resume_profile_json)
    job_profile = JobProfile.model_validate_json(job_profile_json)
    return calculate_fit_score(resume_profile, job_profile).model_dump_json(indent=2)


resume_parser_agent = Agent(
    name="Resume Parser Agent",
    instructions=(
        "Extract the candidate profile from the resume text. "
        "Be factual. Do not invent skills, projects, companies, or degrees. "
        "If something is unclear, add it to concerns."
    ),
    model=MODEL,
    output_type=ResumeProfile,
)

job_analyzer_agent = Agent(
    name="Job Analyzer Agent",
    instructions=(
        "Extract the job requirements from the job description. "
        "Separate must-have required skills from preferred/nice-to-have skills. "
        "If the job description is vague, add concerns."
    ),
    model=MODEL,
    output_type=JobProfile,
)

scoring_tool_agent = Agent(
    name="Scoring Tool Agent",
    instructions=(
        "You calculate the deterministic job-fit score. "
        "You must call calculate_fit_score_tool exactly once using the provided ResumeProfile JSON "
        "and JobProfile JSON. Return the tool result unchanged as a DeterministicScore. "
        "Do not invent or adjust the score yourself."
    ),
    model=MODEL,
    tools=[calculate_fit_score_tool],
    output_type=DeterministicScore,
)

fit_scorer_agent = Agent(
    name="Fit Scorer Agent",
    instructions=(
        "You receive a resume profile, job profile, and deterministic scoring result. "
        "Use the deterministic score as the numeric source of truth. "
        "Your job is to explain the fit honestly, identify risks, and recommend practical improvements. "
        "Do not inflate the score."
    ),
    model=MODEL,
    output_type=FitAnalysis,
)

report_agent = Agent(
    name="Final Report Agent",
    instructions=(
        "Create a concise, readable Markdown job-fit report for the candidate. "
        "Use human language, not raw JSON. Include score, verdict, evidence, missing skills, "
        "resume improvements, project suggestions, and interview preparation points."
    ),
    model=MODEL,
    output_type=FinalReport,
)

follow_up_agent = Agent(
    name="Follow-up Coach Agent",
    instructions=(
        "Answer follow-up questions using the current session's resume, job description, score, "
        "and report context. Be specific and practical."
    ),
    model=MODEL,
)


@dataclass
class SessionState:
    session_id: str
    sdk_session: object | None = None
    resume_profile: ResumeProfile | None = None
    job_profile: JobProfile | None = None
    deterministic_score: DeterministicScore | None = None
    fit_analysis: FitAnalysis | None = None
    report: FinalReport | None = None
    history: list[dict[str, str]] = field(default_factory=list)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def create(self) -> SessionState:
        session_id = str(uuid.uuid4())
        sdk_session = SQLiteSession(session_id) if SQLiteSession else None
        state = SessionState(session_id=session_id, sdk_session=sdk_session)
        self._sessions[session_id] = state
        return state

    def get_or_create(self, session_id: str | None = None) -> SessionState:
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]
        return self.create()

    def get(self, session_id: str) -> SessionState | None:
        return self._sessions.get(session_id)


session_store = SessionStore()


def to_json(value: object) -> str:
    if hasattr(value, "model_dump"):
        return json.dumps(value.model_dump(), indent=2)
    return json.dumps(value, indent=2)


async def analyze_job_fit(
    resume_text: str,
    job_description: str,
    session_id: str | None = None,
) -> AnalyzeResponse:
    state = session_store.get_or_create(session_id)

    with trace("Job AI fit analysis"):
        resume_result = await Runner.run(
            resume_parser_agent,
            f"Resume text:\n\n{resume_text}",
            session=state.sdk_session,
        )
        resume_profile = resume_result.final_output

        job_result = await Runner.run(
            job_analyzer_agent,
            f"Job description:\n\n{job_description}",
            session=state.sdk_session,
        )
        job_profile = job_result.final_output

        scoring_prompt = (
            "Calculate the deterministic fit score using the scoring tool.\n\n"
            f"ResumeProfile JSON:\n{to_json(resume_profile)}\n\n"
            f"JobProfile JSON:\n{to_json(job_profile)}"
        )
        scoring_result = await Runner.run(
            scoring_tool_agent,
            scoring_prompt,
            session=state.sdk_session,
        )
        deterministic_score = scoring_result.final_output

        fit_prompt = (
            "Resume profile:\n"
            f"{to_json(resume_profile)}\n\n"
            "Job profile:\n"
            f"{to_json(job_profile)}\n\n"
            "Deterministic score:\n"
            f"{to_json(deterministic_score)}"
        )
        fit_result = await Runner.run(
            fit_scorer_agent,
            fit_prompt,
            session=state.sdk_session,
        )
        fit_analysis = fit_result.final_output

        report_prompt = (
            "Create the final user-facing report from this data.\n\n"
            f"Resume profile:\n{to_json(resume_profile)}\n\n"
            f"Job profile:\n{to_json(job_profile)}\n\n"
            f"Deterministic score:\n{to_json(deterministic_score)}\n\n"
            f"Fit analysis:\n{to_json(fit_analysis)}"
        )
        report_result = await Runner.run(
            report_agent,
            report_prompt,
            session=state.sdk_session,
        )
        report = report_result.final_output

    state.resume_profile = resume_profile
    state.job_profile = job_profile
    state.deterministic_score = deterministic_score
    state.fit_analysis = fit_analysis
    state.report = report
    state.history.append({"role": "system", "content": "Completed job fit analysis."})

    return AnalyzeResponse(
        session_id=state.session_id,
        resume_profile=resume_profile,
        job_profile=job_profile,
        deterministic_score=deterministic_score,
        fit_analysis=fit_analysis,
        report=report,
    )


async def answer_follow_up(session_id: str, message: str) -> ChatResponse:
    state = session_store.get(session_id)
    if not state or not state.report:
        raise ValueError("Session not found or no analysis has been completed for this session")

    context = (
        "Current session context:\n\n"
        f"Resume profile:\n{to_json(state.resume_profile)}\n\n"
        f"Job profile:\n{to_json(state.job_profile)}\n\n"
        f"Score:\n{to_json(state.deterministic_score)}\n\n"
        f"Fit analysis:\n{to_json(state.fit_analysis)}\n\n"
        f"Report:\n{to_json(state.report)}\n\n"
        f"User question: {message}"
    )

    result = await Runner.run(
        follow_up_agent,
        context,
        session=state.sdk_session,
    )
    answer = str(result.final_output)
    state.history.append({"role": "user", "content": message})
    state.history.append({"role": "assistant", "content": answer})
    return ChatResponse(session_id=session_id, answer=answer)
