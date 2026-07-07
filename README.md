# Job AI

AI Job Fit Copilot built with the OpenAI Agents SDK.

## What it does

- Parses a resume into structured profile data.
- Parses a job description into structured job requirements.
- Calculates a transparent fit score using a deterministic scoring tool.
- Uses an agent to explain the score and generate a readable report.
- Keeps session-scoped memory with a random UUID.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your API key to `.env`.

## Run

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## Main endpoints

- `GET /` opens the web UI.
- `POST /sessions` creates a new session UUID.
- `POST /analyze` runs the full job-fit workflow.
- `POST /chat` asks follow-up questions using the same session.
- `POST /extract-resume-text` extracts text from a PDF resume.

Use `examples/analyze_request.json` as a sample body for `POST /analyze`.
