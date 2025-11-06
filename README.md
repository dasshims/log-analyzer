# Data Health Analyzer

A small FastAPI & React application that validates CSV uploads containing user activity metrics, computes basic health statistics, and (optionally) generates a support-ticket-ready summary using the OpenAI Chat Completions API.

- **Backend** (`data_health_analyzer.py`): Exposes a `/analyze` endpoint that validates uploaded CSV data, computes summary metrics, and calls OpenAI when an API key is configured.
- **Frontend** (`frontend/`): Vite + React UI for uploading CSV files and reviewing the validation results, computed statistics, and AI-generated summary.
- **Sample Data** (`sample_user_metrics.csv`): Example dataset for local testing.

## Requirements

- Python 3.10+
- Node.js 18+ and npm
- Optional: `OPENAI_API_KEY` environment variable to enable AI summaries

All Python dependencies are listed in `requirements.txt`; frontend dependencies are managed via npm in `frontend/package.json`.

## Getting Started

### 1. Backend API

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export OPENAI_API_KEY=sk-...         # optional, enables AI summaries
uvicorn data_health_analyzer:app --reload
```

The API exposes:

- `GET /health` – liveness probe returning `{"status": "ok"}`
- `POST /analyze` – accepts `multipart/form-data` containing a CSV file under the `file` field. Returns validation warnings, summary statistics, and AI messaging (or a reason why AI was skipped).

### 2. Frontend UI

```bash
cd frontend
npm install
npm run dev
```

By default Vite serves the UI on `http://localhost:5173`, which is already allowed by the backend CORS configuration. Upload a CSV file to trigger analysis.

## CSV Validation Rules

The backend expects columns `user_id,sessions,clicks,errors`. Validation reports:

- Missing header row, missing required columns, or empty files are treated as errors.
- Missing numeric values, negative numbers, or duplicate user IDs register as warnings and are surfaced in the response.
- Summary statistics are derived from the full dataset, even when warnings are present.

Row numbers in warning messages are 1-based and count the header as row 1, so the first data line is row 2.

## Development Notes

- The OpenAI integration is optional. When `OPENAI_API_KEY` is absent or the `openai` package is unavailable, the API returns a user-facing notice instead of failing.
- `sample_user_metrics.csv` demonstrates typical validation findings (missing values, negatives, duplicates) and can be used to manually verify the workflow.
- Run `uvicorn` with `--reload` during development for hot reloading of backend changes; Vite provides fast HMR for the frontend.
