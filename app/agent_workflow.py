from __future__ import annotations

import json
import os
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

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
            model=os.getenv("GEMINI_MODEL_NAME", "gemini-3.1-flash-lite"),
            openai_client=gemini_client,
        )

    return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


tracing_key = os.getenv("OPENAI_TRACING_API_KEY") or os.getenv("OPENAI_API_KEY")
if tracing_key and set_tracing_export_api_key:
    set_tracing_export_api_key(tracing_key)

MODEL = build_model()
today = date.today()
CURRENT_DATE_TEXT = f"{today:%B} {today.day}, {today.year}"


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
        "For projects, preserve the project name and every technical implementation detail, "
        "including architecture patterns, reliability mechanisms, technologies, and outcomes; "
        "do not reduce a project to only its title. Put open-source work in "
        "open_source_contributions and preserve the project name, contribution, and PR details. "
        "For years_of_experience, estimate total professional experience in years from explicit "
        "work dates or a direct total-experience statement in the resume. Include internships "
        "only when they are professional software, engineering, data, AI, or technical roles. "
        f"Use today's date, {CURRENT_DATE_TEXT}, for roles marked Present, Current, or Now. Avoid "
        "double-counting overlapping roles when possible. Return a decimal number such as 1.5 "
        "when the estimate is clear. If work dates or total experience are missing or too unclear, "
        "set years_of_experience to null and add a concern explaining that the experience duration "
        "cannot be verified. If something is unclear, add it to concerns."
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
        "and report context. Be specific and practical. Format every answer as readable Markdown. "
        "Explain this application's actual deterministic score, not assumptions about generic ATS "
        "systems. The scorer checks all parsed skills, tools, project details, open-source "
        "contributions, work-experience bullets, and achievements. Never claim that project "
        "evidence is ignored. Clearly distinguish facts present in the supplied context from "
        "inferences, and say when evidence is absent. "
        "Put headings on their own lines with a blank line before and after them. Put each bullet "
        "or numbered-list item on its own line. Never return the whole answer as one continuous "
        "paragraph."
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
    def __init__(self, db_path: str | Path) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._db_path = Path(db_path)
        self._initialize_database()

    def _initialize_database(self) -> None:
        with sqlite3.connect(self._db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS job_ai_session_state (
                    session_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL
                )
                """
            )

    def _sdk_session(self, session_id: str) -> object | None:
        if not SQLiteSession:
            return None
        return SQLiteSession(session_id, db_path=self._db_path)

    def create(self) -> SessionState:
        session_id = str(uuid.uuid4())
        state = SessionState(
            session_id=session_id,
            sdk_session=self._sdk_session(session_id),
        )
        self._sessions[session_id] = state
        self.save(state)
        return state

    def get_or_create(self, session_id: str | None = None) -> SessionState:
        if session_id:
            state = self.get(session_id)
            if state:
                return state
        return self.create()

    def get(self, session_id: str) -> SessionState | None:
        if session_id in self._sessions:
            return self._sessions[session_id]

        with sqlite3.connect(self._db_path) as connection:
            row = connection.execute(
                "SELECT state_json FROM job_ai_session_state WHERE session_id = ?",
                (session_id,),
            ).fetchone()

        if not row:
            return None

        data = json.loads(row[0])
        state = SessionState(
            session_id=session_id,
            sdk_session=self._sdk_session(session_id),
            resume_profile=self._restore_model(ResumeProfile, data.get("resume_profile")),
            job_profile=self._restore_model(JobProfile, data.get("job_profile")),
            deterministic_score=self._restore_model(
                DeterministicScore, data.get("deterministic_score")
            ),
            fit_analysis=self._restore_model(FitAnalysis, data.get("fit_analysis")),
            report=self._restore_model(FinalReport, data.get("report")),
            history=data.get("history", []),
        )
        self._sessions[session_id] = state
        return state

    def save(self, state: SessionState) -> None:
        data = {
            "resume_profile": self._dump_model(state.resume_profile),
            "job_profile": self._dump_model(state.job_profile),
            "deterministic_score": self._dump_model(state.deterministic_score),
            "fit_analysis": self._dump_model(state.fit_analysis),
            "report": self._dump_model(state.report),
            "history": state.history,
        }
        with sqlite3.connect(self._db_path) as connection:
            connection.execute(
                """
                INSERT INTO job_ai_session_state (session_id, state_json)
                VALUES (?, ?)
                ON CONFLICT(session_id) DO UPDATE SET state_json = excluded.state_json
                """,
                (state.session_id, json.dumps(data)),
            )

    @staticmethod
    def _dump_model(value: object | None) -> dict | None:
        return value.model_dump() if hasattr(value, "model_dump") else None

    @staticmethod
    def _restore_model(model_class, value: dict | None):
        return model_class.model_validate(value) if value is not None else None


SESSION_DB_PATH = Path(
    os.getenv("JOB_AI_SESSION_DB", Path(__file__).resolve().parent.parent / "job_ai_sessions.db")
)
session_store = SessionStore(SESSION_DB_PATH)


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
    session_store.save(state)

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

    with trace("Job AI follow-up"):
        result = await Runner.run(
            follow_up_agent,
            context,
            session=state.sdk_session,
        )
    answer = str(result.final_output)
    state.history.append({"role": "user", "content": message})
    state.history.append({"role": "assistant", "content": answer})
    session_store.save(state)
    return ChatResponse(session_id=session_id, answer=answer)
