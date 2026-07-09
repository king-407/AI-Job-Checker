# AI Job Fit Checker

An agentic AI application that compares a candidate’s resume with a job description, calculates an explainable fit score, generates personalized recommendations, and answers follow-up career questions.

The application combines AI agents with deterministic business logic. AI agents extract and explain information, while a regular scoring function calculates the numerical score. This makes the result more transparent and consistent than asking an LLM to invent a score.

> This project is currently a working prototype intended for learning, experimentation, and portfolio demonstration. Its output should not be treated as a professional hiring decision.

## Features

- Parse resume text into a structured candidate profile
- Upload and extract text from PDF resumes
- Analyze job descriptions and identify requirements
- Separate required skills from preferred skills
- Calculate a deterministic job-fit score
- Display matched and missing skills
- Generate a personalized Markdown report
- Recommend resume improvements and project ideas
- Suggest interview preparation topics
- Answer follow-up questions through an AI career coach
- Preserve session context using SQLite
- Support OpenAI and Gemini models
- Trace agent workflows using the OpenAI Agents SDK

## Application Preview

The interface allows users to:

1. Paste resume text or upload a PDF resume.
2. Paste a job description.
3. Run the agentic analysis workflow.
4. Review the fit score and category breakdown.
5. Inspect matched and missing skills.
6. Read a personalized job-fit report.
7. Ask follow-up questions about the result.

Add your screenshots or demo GIF here:

```markdown
![Application Preview](docs/application-preview.png)
```

## Architecture

```text
┌───────────────────────────┐
│ Resume / PDF              │
│ Job Description           │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│ FastAPI Backend           │
│ Request Validation        │
└─────────────┬─────────────┘
              │
       ┌──────┴──────┐
       ▼             ▼
┌──────────────┐ ┌────────────────┐
│ Resume       │ │ Job Analyzer   │
│ Parser Agent │ │ Agent          │
└──────┬───────┘ └───────┬────────┘
       │                 │
       └────────┬────────┘
                ▼
┌───────────────────────────┐
│ Deterministic Scoring     │
│ Tool                      │
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│ Fit Analysis Agent        │
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│ Final Report Agent        │
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│ SQLite Session Memory     │
│ Follow-up Coach Agent     │
└───────────────────────────┘
```

## Agent Workflow

The analysis is divided into specialized stages.

### 1. Resume Parser Agent

Extracts structured candidate information from the supplied resume:

- Candidate name
- Current or most recent title
- Estimated years of experience
- Skills and tools
- Projects
- Work experience
- Education
- Achievements
- Missing or unclear information

The agent is instructed to remain factual and avoid inventing qualifications.

### 2. Job Analyzer Agent

Transforms the job description into structured requirements:

- Role title
- Company
- Seniority
- Required skills
- Preferred skills
- Responsibilities
- Domain keywords
- Constraints
- Ambiguous or missing information

### 3. Scoring Tool Agent

Calls the deterministic scoring function with the structured resume and job profiles.

The numerical score does not come directly from an LLM. It is calculated using explicit weights and matching rules.

### 4. Fit Scorer Agent

Interprets the deterministic result and produces:

- Fit confidence
- Overall verdict
- Strong and partial matches
- Missing skills
- Application risks
- Improvement actions
- Interview preparation topics

### 5. Final Report Agent

Converts the structured analysis into a concise, human-readable Markdown report.

### 6. Follow-up Coach Agent

Uses the saved session context to answer questions such as:

- How can I improve my resume for this role?
- Which missing skill should I learn first?
- What projects would strengthen my profile?
- What interview questions should I prepare for?
- Is this position suitable for my experience level?

## Deterministic Scoring

The score is calculated out of 100 points.

| Category | Maximum score |
|---|---:|
| Required skills | 40 |
| Relevant experience | 25 |
| Project and domain match | 15 |
| Preferred skills | 10 |
| Seniority fit | 10 |
| **Total** | **100** |

The function normalizes skill names and compares the candidate’s skills, tools, projects, work experience, and achievements with the job requirements.

The response also includes:

- Matched required skills
- Missing required skills
- Matched preferred skills
- Missing preferred skills
- Matched project or domain keywords
- Evidence describing how the score was calculated

This scoring system is intentionally transparent and can be extended with improved normalization, aliases, semantic matching, constraint checks, and role-specific weighting.

## Technology Stack

### Backend

- Python
- FastAPI
- OpenAI Agents SDK
- Pydantic
- SQLite
- pypdf
- Uvicorn

### AI Providers

- OpenAI
- Google Gemini through its OpenAI-compatible API

### Frontend

- HTML
- CSS
- Vanilla JavaScript

## Project Structure

```text
AI-Job-Checker/
├── app/
│   ├── __init__.py
│   ├── agent_workflow.py
│   ├── main.py
│   ├── models.py
│   ├── pdf_utils.py
│   ├── scoring.py
│   └── static/
│       ├── app.js
│       ├── index.html
│       └── styles.css
├── examples/
│   └── analyze_request.json
├── .gitignore
├── README.md
└── requirements.txt
```

### Important Files

| File | Responsibility |
|---|---|
| `app/main.py` | FastAPI application and HTTP endpoints |
| `app/agent_workflow.py` | Agent definitions, orchestration, sessions, and memory |
| `app/models.py` | Pydantic request, response, and agent-output schemas |
| `app/scoring.py` | Deterministic job-fit scoring logic |
| `app/pdf_utils.py` | PDF text extraction |
| `app/static/app.js` | Frontend behavior and API integration |
| `app/static/index.html` | Application interface |
| `app/static/styles.css` | Application styling |

## Getting Started

### Prerequisites

Make sure you have:

- Python 3.10 or newer
- An OpenAI API key or Google Gemini API key
- Git

### 1. Clone the repository

```bash
git clone https://github.com/king-407/AI-Job-Checker.git
cd AI-Job-Checker
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root.

For OpenAI:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-mini
USE_GEMINI=false
```

You can optionally provide a separate key for trace exporting:

```env
OPENAI_TRACING_API_KEY=your_openai_api_key
```

For Gemini:

```env
USE_GEMINI=true
GOOGLE_API_KEY=your_google_api_key
GEMINI_MODEL_NAME=gemini-3.1-flash-lite
```

You can also customize the SQLite database location:

```env
JOB_AI_SESSION_DB=job_ai_sessions.db
```

Do not commit the `.env` file or expose API keys publicly.

### 5. Run the application

```bash
uvicorn app.main:app --reload
```

Open the application:

```text
http://127.0.0.1:8000
```

Interactive API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## API Endpoints

### `GET /`

Opens the browser interface.

### `GET /health`

Returns basic application information and confirms that the API is running.

Example response:

```json
{
  "name": "Job AI",
  "docs": "/docs",
  "flow": "resume + job description -> parsed profiles -> deterministic score -> fit report"
}
```

### `POST /sessions`

Creates a new session.

Example response:

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### `POST /analyze`

Runs the complete job-fit workflow.

Example request:

```json
{
  "resume_text": "Candidate resume text containing experience, skills and projects...",
  "job_description": "Job description containing responsibilities and requirements...",
  "session_id": null
}
```

The `session_id` is optional. When omitted, the application creates a new session.

Example response structure:

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "resume_profile": {},
  "job_profile": {},
  "deterministic_score": {
    "total_score": 76.5,
    "breakdown": {},
    "matched_required_skills": [],
    "missing_required_skills": [],
    "matched_preferred_skills": [],
    "missing_preferred_skills": [],
    "matched_keywords": [],
    "evidence": []
  },
  "fit_analysis": {},
  "report": {
    "title": "Job Fit Report",
    "markdown_report": "..."
  }
}
```

A complete sample request is available in:

```text
examples/analyze_request.json
```

You can call the endpoint using `curl`:

```bash
curl -X POST "http://127.0.0.1:8000/analyze" \
  -H "Content-Type: application/json" \
  --data @examples/analyze_request.json
```

### `POST /chat`

Asks a follow-up question using an existing completed session.

Example request:

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Which missing skill should I prioritize?"
}
```

Example response:

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "answer": "..."
}
```

The session must already contain a completed analysis.

### `POST /extract-resume-text`

Extracts text from an uploaded PDF resume.

Example:

```bash
curl -X POST "http://127.0.0.1:8000/extract-resume-text" \
  -F "file=@resume.pdf"
```

Example response:

```json
{
  "text": "Extracted resume content..."
}
```

## Structured Data Models

The application uses Pydantic schemas for agent inputs and outputs.

Important models include:

- `ResumeProfile`
- `JobProfile`
- `ScoreBreakdown`
- `DeterministicScore`
- `FitAnalysis`
- `FinalReport`
- `AnalyzeRequest`
- `AnalyzeResponse`
- `ChatRequest`
- `ChatResponse`

Structured outputs help reduce parsing failures and make the information easier to validate, store, score, and display.

## Session Memory

Each user session receives a random UUID.

The application stores the following context:

- Parsed resume profile
- Parsed job profile
- Deterministic score
- Fit analysis
- Final report
- Follow-up conversation history

Session data is persisted in SQLite, allowing the follow-up coach to retain the analysis context.

The database files are excluded from Git through `.gitignore`.

## Design Decisions

### Why use multiple agents?

Each agent has a focused responsibility. This reduces prompt complexity and makes the workflow easier to understand, test, trace, and improve.

### Why use structured outputs?

Pydantic models enforce predictable response shapes and reduce dependence on manually parsing free-form LLM responses.

### Why use deterministic scoring?

LLM-generated scores can vary between runs and may not clearly explain their reasoning. A deterministic function provides explicit weighting and a reproducible breakdown.

### Why keep the LLM in the analysis?

Deterministic matching calculates the numerical result, while agents handle tasks that benefit from language understanding:

- Extracting information
- Identifying ambiguity
- Explaining evidence
- Recommending improvements
- Generating readable reports
- Answering contextual questions

## Current Limitations

This project is an evolving prototype and currently has several limitations:

- Skill matching primarily uses normalized text and substring matching.
- Skill aliases and equivalent technologies are not fully supported.
- Experience scoring uses general thresholds rather than every job’s exact requirement.
- Job constraints are extracted but not fully included in the score.
- Scanned image-only PDFs require OCR and may not extract correctly.
- Results depend on the quality of the resume and job-description text.
- LLM outputs may still contain errors or unsupported interpretations.
- The workflow makes multiple model calls, affecting cost and latency.
- Authentication and rate limiting are not yet implemented.
- The application has not been designed for automated hiring decisions.

## Responsible Use

The generated fit score is an informational estimate, not an objective measure of a candidate’s ability.

Do not use this project as the sole basis for:

- Hiring or rejection decisions
- Ranking candidates
- Employment screening
- Evaluating protected personal characteristics

Users should review the original resume, job description, extracted evidence, and recommendations themselves.

Sensitive resumes should not be uploaded to an untrusted or publicly deployed instance.

## Roadmap

Planned improvements include:

- [ ] Automated unit and API tests
- [ ] Agent evaluation dataset
- [ ] Token-aware skill matching
- [ ] Skill aliases and taxonomy support
- [ ] Semantic similarity matching
- [ ] Job-specific experience scoring
- [ ] Constraint and eligibility checks
- [ ] Prompt-injection protection
- [ ] OCR support for scanned PDFs
- [ ] Authentication and rate limiting
- [ ] Session expiration and deletion
- [ ] Retry and timeout handling
- [ ] Parallel resume and job analysis
- [ ] Cost and latency monitoring
- [ ] Docker support
- [ ] CI/CD workflow
- [ ] Cloud deployment

## Security Notes

- Never commit API keys.
- Keep `.env` outside version control.
- Add file-size limits before public deployment.
- Add authentication and rate limiting before exposing the API.
- Treat resume and job-description content as untrusted input.
- Review privacy requirements before storing real candidate information.
- Provide a way to delete stored session information in production.

## Contributing

Contributions and constructive feedback are welcome.

1. Fork the repository.
2. Create a feature branch:

```bash
git checkout -b feature/your-feature-name
```

3. Commit your changes:

```bash
git commit -m "Add your feature"
```

4. Push the branch:

```bash
git push origin feature/your-feature-name
```

5. Open a pull request.

## Author

**Shivam Tiwari**

GitHub: [king-407](https://github.com/king-407)

## License

No license has been added yet.

If you want others to use, modify, or distribute this project, add an appropriate open-source license such as the MIT License.

## Feedback

If you find the project useful or have suggestions for improving its architecture, scoring logic, or agent workflow, feel free to open an issue or start a discussion.

If you like the project, consider giving the repository a star.
