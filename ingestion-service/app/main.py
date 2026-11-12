import httpx
from fastapi import FastAPI, UploadFile, File, HTTPException
from pathlib import Path
from uuid import uuid4
import csv

app = FastAPI(
    title="Insurance Data Ingestion Service",
    description="API for ingesting insurance policy data",
    version="1.0.0"
)

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "data" / "raw"


RAW_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_COLUMNS = {
    "policy_id",
    "customer_name",
    "premium",
    "start_date"
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@app.get("/health")
def health_check():
    return {
        "service": "Insurance Ingestion Service",
        "status": "healthy"
    }


@app.post("/api/v1/ingestions/upload")
async def upload_policy_file(file: UploadFile = File(...)):

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported"
        )

    execution_id = str(uuid4())
    temp_path = RAW_DIR / f"{execution_id}.tmp"
    file_path = RAW_DIR / f"{execution_id}.csv"

    try:
        file_size = 0

        with temp_path.open("wb") as destination:
            while chunk := await file.read(1024 * 1024):
                file_size += len(chunk)

                if file_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="File exceeds 10 MB limit"
                    )

                destination.write(chunk)

        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty"
            )

        with temp_path.open(
            "r", encoding="utf-8-sig", newline=""
        ) as source:
            reader = csv.DictReader(source)

            if not reader.fieldnames:
                raise HTTPException(
                    status_code=400,
                    detail="CSV header is missing"
                )

            columns = set(reader.fieldnames)

            if not REQUIRED_COLUMNS.issubset(columns):
                missing = sorted(REQUIRED_COLUMNS - columns)

                raise HTTPException(
                    status_code=400,
                    detail=f"Missing mandatory columns: {missing}"
                )

            record_count = sum(1 for _ in reader)

        temp_path.replace(file_path)
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"http://processing-service:8002/api/v1/process/{execution_id}")

        response.raise_for_status()
        processing_result = response.json()

        return {
            "execution_id": execution_id,
            "file_name": file.filename,
            "record_count": record_count,
            "file_size_bytes": file_size,
            "status": "INGESTED",
            "raw_file": str(file_path),
             "processing_result": processing_result
        }

    except HTTPException:
        raise

    except (UnicodeDecodeError, csv.Error):
        raise HTTPException(
            status_code=400,
            detail="Invalid CSV file format or encoding"
        )

    finally:
        if temp_path.exists():
            temp_path.unlink()

        await file.close()
