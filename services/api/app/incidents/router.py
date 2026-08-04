from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.incidents.analysis import (
    analyze,
    load_incidents_from_bytes,
    metrics_to_csv_string,
    validate_columns,
)
from app.incidents.schemas import AnalysisResult
from app.incidents.store import get_last_analysis, metrics_to_response, save_analysis

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("/analyze", response_model=AnalysisResult)
async def analyze_incidents(file: UploadFile = File(..., description="UTF-8 CSV of patient incidents")) -> AnalysisResult:
    """Upload a patient incident CSV and receive an aggregate analysis summary."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Unable to parse CSV file. Ensure UTF-8 encoding and comma separator.")

    content = await file.read()
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    try:
        df = load_incidents_from_bytes(content)
    except ValueError as exc:
        reason = str(exc)
        if reason == "empty":
            raise HTTPException(status_code=400, detail="The uploaded file is empty.") from exc
        raise HTTPException(
            status_code=400,
            detail="Unable to parse CSV file. Ensure UTF-8 encoding and comma separator.",
        ) from exc

    if len(df) == 0:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    missing_columns = validate_columns(df)
    if missing_columns:
        joined = ", ".join(missing_columns)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid CSV format: missing required columns: {joined}",
        )

    metrics = analyze(df)
    csv_content = metrics_to_csv_string(metrics)
    stored = save_analysis(file.filename, metrics, csv_content)
    return AnalysisResult(**metrics_to_response(stored))


@router.get("/results/export")
async def export_results() -> Response:
    """Download the last analysis as CSV (aggregate metrics only)."""
    stored = get_last_analysis()
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="No analysis results available. Upload a CSV first.",
        )

    return Response(
        content=stored.csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="results.csv"'},
    )
