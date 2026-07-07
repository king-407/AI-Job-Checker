from __future__ import annotations

import re

from .models import DeterministicScore, JobProfile, ResumeProfile, ScoreBreakdown


def normalize_term(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9+#. ]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def match_terms(source_terms: list[str], target_terms: list[str]) -> tuple[list[str], list[str]]:
    normalized_source = {normalize_term(term) for term in source_terms if normalize_term(term)}
    matched: list[str] = []
    missing: list[str] = []

    for target in target_terms:
        normalized_target = normalize_term(target)
        if not normalized_target:
            continue

        found = any(
            normalized_target == source
            or normalized_target in source
            or source in normalized_target
            for source in normalized_source
        )

        if found:
            matched.append(target)
        else:
            missing.append(target)

    return matched, missing


def ratio_score(matched_count: int, total_count: int, weight: float) -> float:
    if total_count == 0:
        return weight * 0.7
    return round((matched_count / total_count) * weight, 2)


def calculate_fit_score(resume: ResumeProfile, job: JobProfile) -> DeterministicScore:
    resume_terms = resume.skills + resume.tools + resume.projects + resume.work_experience + resume.achievements

    matched_required, missing_required = match_terms(resume_terms, job.required_skills)
    matched_preferred, missing_preferred = match_terms(resume_terms, job.preferred_skills)
    matched_keywords, _ = match_terms(resume_terms, job.domain_keywords + job.responsibilities)

    required_score = ratio_score(len(matched_required), len(job.required_skills), 40)
    preferred_score = ratio_score(len(matched_preferred), len(job.preferred_skills), 10)
    project_score = min(15.0, round(len(matched_keywords) * 3.0, 2))

    experience_score = 12.5
    if resume.years_of_experience is not None:
        if resume.years_of_experience >= 3:
            experience_score = 22
        elif resume.years_of_experience >= 1:
            experience_score = 18
        else:
            experience_score = 12

    seniority_score = 7.0
    seniority = normalize_term(job.seniority or "")
    if seniority:
        if "intern" in seniority or "junior" in seniority or "entry" in seniority:
            seniority_score = 9.0 if (resume.years_of_experience or 0) <= 2 else 7.0
        elif "senior" in seniority:
            seniority_score = 9.0 if (resume.years_of_experience or 0) >= 4 else 4.0
        else:
            seniority_score = 7.5

    breakdown = ScoreBreakdown(
        required_skills=required_score,
        relevant_experience=experience_score,
        project_domain_match=project_score,
        preferred_skills=preferred_score,
        seniority_fit=seniority_score,
    )

    total = round(
        breakdown.required_skills
        + breakdown.relevant_experience
        + breakdown.project_domain_match
        + breakdown.preferred_skills
        + breakdown.seniority_fit,
        2,
    )

    evidence = [
        f"Matched {len(matched_required)} of {len(job.required_skills)} required skills.",
        f"Matched {len(matched_preferred)} of {len(job.preferred_skills)} preferred skills.",
        f"Found {len(matched_keywords)} project/domain keyword matches.",
    ]

    return DeterministicScore(
        total_score=min(total, 100),
        breakdown=breakdown,
        matched_required_skills=matched_required,
        missing_required_skills=missing_required,
        matched_preferred_skills=matched_preferred,
        missing_preferred_skills=missing_preferred,
        matched_keywords=matched_keywords,
        evidence=evidence,
    )
