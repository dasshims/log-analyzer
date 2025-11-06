"""FastAPI service for analyzing user activity CSV uploads.

The service validates incoming datasets, computes summary statistics, and can
optionally call the OpenAI Chat Completions API to draft a support-ticket-style
summary of the dataset health.
"""

from __future__ import annotations

import csv
import io
import os
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


EXPECTED_COLUMNS = ["user_id", "sessions", "clicks", "errors"]
NUMERIC_COLUMNS = ["sessions", "clicks", "errors"]


class SummaryStatistics(BaseModel):
    """Aggregate metrics describing the dataset."""

    total_users: int
    average_sessions_per_user: float
    percent_users_with_errors: float


class AnalysisResponse(BaseModel):
    """Payload returned to clients after a successful analysis."""

    warnings: List[str]
    statistics: SummaryStatistics
    ai_summary: Optional[str]
    ai_notice: Optional[str]


def parse_csv_rows(csv_text: str) -> List[Dict[str, str]]:
    """Create a row dictionary for each CSV record.

    Args:
        csv_text: Raw CSV file contents as text.

    Raises:
        ValueError: if headers are missing, required columns are absent, or there
            are no data rows.
    """
    csv_stream = io.StringIO(csv_text)
    reader = csv.DictReader(csv_stream)

    if reader.fieldnames is None:
        raise ValueError("The input file is missing a header row.")

    missing_columns = [col for col in EXPECTED_COLUMNS if col not in reader.fieldnames]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}.")

    rows = list(reader)
    if not rows:
        raise ValueError("The input file is empty. Please upload a valid dataset.")

    return rows


def validate_rows(
    rows: List[Dict[str, str]]
) -> Tuple[List[str], Dict[str, List[int]], Dict[str, bool], List[str]]:
    """Validate each CSV row and gather metrics for later aggregation.

    Row numbering follows the CSV line numbers (header is row 1), meaning the
    first data row is reported to users as row 2.
    """
    warnings: List[str] = []
    seen_user_ids: set[str] = set()
    sessions_per_user: Dict[str, List[int]] = defaultdict(list)
    errors_flag_by_user: Dict[str, bool] = defaultdict(bool)
    unique_user_ids: List[str] = []

    for row_number, row in enumerate(rows, start=2):
        user_id = (row.get("user_id") or "").strip()

        if user_id:
            if user_id not in seen_user_ids:
                unique_user_ids.append(user_id)
                seen_user_ids.add(user_id)
            else:
                warnings.append(f"Row {row_number}: duplicate user_id {user_id} detected.")
        else:
            warnings.append(f"Row {row_number}: missing value in user_id column.")

        for column in NUMERIC_COLUMNS:
            raw_value = (row.get(column) or "").strip()

            if raw_value == "":
                warnings.append(f"Row {row_number}: missing value in {column} column.")
                continue

            try:
                numeric_value = int(raw_value)
            except ValueError:
                warnings.append(
                    f"Row {row_number}: invalid integer value '{raw_value}' in {column} column."
                )
                continue

            if numeric_value < 0:
                warnings.append(f"Row {row_number}: negative value in {column} column.")
                continue

            if column == "sessions" and user_id:
                sessions_per_user[user_id].append(numeric_value)
            if column == "errors" and user_id and numeric_value > 0:
                errors_flag_by_user[user_id] = True

    return warnings, sessions_per_user, errors_flag_by_user, unique_user_ids


def compute_summary_statistics(
    unique_user_ids: List[str],
    sessions_per_user: Dict[str, List[int]],
    errors_flag_by_user: Dict[str, bool],
) -> SummaryStatistics:
    """Summarize validated data with key metrics."""
    unique_user_count = len(unique_user_ids)

    aggregated_sessions = {
        user_id: sum(values)
        for user_id, values in sessions_per_user.items()
        if values
    }
    if aggregated_sessions:
        avg_sessions = sum(aggregated_sessions.values()) / len(aggregated_sessions)
    else:
        avg_sessions = 0.0

    users_with_errors = {
        user_id for user_id, has_errors in errors_flag_by_user.items() if has_errors
    }
    error_percentage = (
        (len(users_with_errors) / unique_user_count) * 100 if unique_user_count else 0.0
    )

    return SummaryStatistics(
        total_users=unique_user_count,
        average_sessions_per_user=round(avg_sessions, 2),
        percent_users_with_errors=round(error_percentage, 2),
    )


def build_openai_prompt(
    warnings: List[str],
    stats: SummaryStatistics,
    sample_rows: List[Dict[str, str]],
) -> str:
    """Assemble a concise prompt describing the dataset health."""
    warning_text = "None" if not warnings else "\n".join(f"- {item}" for item in warnings)
    prompt = (
        "You are assisting a Technical Support Engineer reviewing a CSV upload.\n\n"
        "DATA SUMMARY:\n"
        f"- Total Users: {stats.total_users}\n"
        f"- Average Sessions per User: {stats.average_sessions_per_user:.2f}\n"
        f"- Percent Users with Errors: {stats.percent_users_with_errors:.2f}%\n\n"
        "VALIDATION WARNINGS:\n"
        f"{warning_text}\n\n"
        "SAMPLE ROWS:\n"
    )

    for row in sample_rows[:5]:
        prompt += f"- {row}\n"

    prompt += (
        "\nWrite a brief support ticket update that:\n"
        "1. Summarizes the health of the dataset.\n"
        "2. Suggests 2-3 likely causes for inconsistent uploads.\n"
        "3. Recommends one immediate remediation step.\n"
        "Keep the tone clear, professional, and action-oriented. Do not include code."
    )
    return prompt


def generate_openai_summary(
    warnings: List[str],
    stats: SummaryStatistics,
    rows: List[Dict[str, str]],
) -> Tuple[Optional[str], Optional[str]]:
    """Attempt to request an OpenAI-generated support summary.

    Returns:
        ai_summary: The generated summary text, if available.
        ai_notice: A user-facing message describing why the summary is missing.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None, "OpenAI analysis skipped: OPENAI_API_KEY environment variable is not set."

    try:
        from openai import OpenAI
    except ImportError:
        return None, "OpenAI analysis skipped: install the 'openai' package to enable this feature."

    client = OpenAI(api_key=api_key)
    prompt = build_openai_prompt(warnings, stats, rows)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful technical support co-pilot.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=400,
        )
    except Exception as error:  # pragma: no cover - surface API issues
        return None, f"OpenAI API call failed: {error}"

    if not response.choices:
        return None, "OpenAI API returned no completion choices."

    message = response.choices[0].message
    content = getattr(message, "content", None)
    if not content:
        return None, "OpenAI API completion contained no message content."

    usage = response.usage
    print(f"prompt tokens: {usage.prompt_tokens}")
    print(f"completion tokens: {usage.completion_tokens}")
    print(f"total tokens: {usage.total_tokens}")
    
    return content.strip(), None


def analyze_csv_content(csv_text: str) -> AnalysisResponse:
    """Perform the full validation and summary workflow on provided CSV data."""
    rows = parse_csv_rows(csv_text)
    warnings, sessions_per_user, errors_flag_by_user, unique_user_ids = validate_rows(rows)
    stats = compute_summary_statistics(unique_user_ids, sessions_per_user, errors_flag_by_user)
    ai_summary, ai_notice = generate_openai_summary(warnings, stats, rows)

    return AnalysisResponse(
        warnings=warnings,
        statistics=stats,
        ai_summary=ai_summary,
        ai_notice=ai_notice,
    )


app = FastAPI(
    title="Data Health Analyzer",
    description="Validate user activity CSV uploads and summarize dataset health.",
    version="1.0.0",
)

# Allow local development clients (e.g., React dev server) to access the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Simple endpoint to verify the service is running."""
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_dataset(file: UploadFile = File(...)) -> AnalysisResponse:
    """Accept a CSV upload, validate it, and return the analysis results."""
    if file.content_type not in {"text/csv", "application/vnd.ms-excel"}:
        raise HTTPException(status_code=400, detail="Please upload a CSV file.")

    content_bytes = await file.read()
    if not content_bytes:
        raise HTTPException(
            status_code=400,
            detail="The input file is empty. Please upload a valid dataset.",
        )

    try:
        # Accept UTF-8 with or without BOM; fallback to latin-1 to avoid decode errors.
        csv_text = content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Unable to decode file as UTF-8: {exc}") from exc

    try:
        return analyze_csv_content(csv_text)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
