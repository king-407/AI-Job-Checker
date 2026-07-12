from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ResumeProfile(BaseModel):
    candidate_name: str | None = Field(default=None, description="Candidate name if present")
    current_title: str | None = Field(default=None, description="Current or most recent role/title")
    years_of_experience: float | None = Field(default=None, description="Estimated total years of experience")
    skills: list[str] = Field(default_factory=list, description="Technical and professional skills")
    tools: list[str] = Field(default_factory=list, description="Tools, libraries, frameworks, platforms")
    projects: list[str] = Field(
        default_factory=list,
        description="Project names and detailed technical implementation bullets",
    )
    open_source_contributions: list[str] = Field(
        default_factory=list,
        description="Open-source projects, pull requests, fixes, tests, and contribution details",
    )
    work_experience: list[str] = Field(default_factory=list, description="Relevant work experience bullets")
    education: list[str] = Field(default_factory=list, description="Education details")
    achievements: list[str] = Field(default_factory=list, description="Achievements, awards, measurable impact")
    concerns: list[str] = Field(default_factory=list, description="Missing or unclear resume details")


class JobProfile(BaseModel):
    role_title: str | None = Field(default=None, description="Job role title")
    company: str | None = Field(default=None, description="Company name if present")
    seniority: str | None = Field(default=None, description="Seniority level")
    required_skills: list[str] = Field(default_factory=list, description="Must-have skills")
    preferred_skills: list[str] = Field(default_factory=list, description="Nice-to-have skills")
    responsibilities: list[str] = Field(default_factory=list, description="Main responsibilities")
    domain_keywords: list[str] = Field(default_factory=list, description="Domain, industry, and role keywords")
    constraints: list[str] = Field(default_factory=list, description="Location, degree, visa, timing, or other constraints")
    concerns: list[str] = Field(default_factory=list, description="Ambiguous or missing JD details")


class ScoreBreakdown(BaseModel):
    required_skills: float = Field(ge=0, le=40)
    relevant_experience: float = Field(ge=0, le=25)
    project_domain_match: float = Field(ge=0, le=15)
    preferred_skills: float = Field(ge=0, le=10)
    seniority_fit: float = Field(ge=0, le=10)


class DeterministicScore(BaseModel):
    total_score: float = Field(ge=0, le=100)
    breakdown: ScoreBreakdown
    matched_required_skills: list[str]
    missing_required_skills: list[str]
    matched_preferred_skills: list[str]
    missing_preferred_skills: list[str]
    matched_keywords: list[str]
    evidence: list[str]


class FitAnalysis(BaseModel):
    score: float = Field(ge=0, le=100)
    confidence: Literal["low", "medium", "high"]
    verdict: Literal["strong_match", "possible_match", "weak_match"]
    summary: str
    strong_matches: list[str]
    partial_matches: list[str]
    missing_skills: list[str]
    risks: list[str]
    improvement_actions: list[str]
    interview_focus: list[str]


class FinalReport(BaseModel):
    title: str
    markdown_report: str


class AnalyzeRequest(BaseModel):
    resume_text: str = Field(min_length=50)
    job_description: str = Field(min_length=50)
    session_id: str | None = None


class AnalyzeResponse(BaseModel):
    session_id: str
    resume_profile: ResumeProfile
    job_profile: JobProfile
    deterministic_score: DeterministicScore
    fit_analysis: FitAnalysis
    report: FinalReport


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    session_id: str
    answer: str
