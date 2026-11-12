import pandas as pd
import json
import time
from datetime import datetime
from collections import Counter
from fastapi import FastAPI, HTTPException
from pathlib import Path


app = FastAPI(
    title="Insurance Data Processing Service",
    description="Validates and processes insurance policy records",
    version="1.0.0"
)

# Project folder location
BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DIR = BASE_DIR / "data" / "raw"
CURATED_DIR = BASE_DIR / "data" / "curated"
REJECTED_DIR = BASE_DIR / "data" / "rejected"
REPORT_DIR = BASE_DIR / "data" / "reports"
AUDIT_DIR = BASE_DIR / "data" / "audit"

CURATED_DIR.mkdir(parents=True, exist_ok=True)
REJECTED_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/health")
def health_check():
    return {
        "service": "Insurance Processing Service",
        "status": "healthy"
    }


@app.post("/api/v1/process/{execution_id}")
def process_insurance_data(execution_id: str):

    raw_file = RAW_DIR / f"{execution_id}.csv"

    if not raw_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Raw file not found for this execution ID"
        )

    try:
        start_time = datetime.now()
        df = pd.read_csv(raw_file)

        required_columns = [
            "policy_id",
            "customer_name",
            "premium",
            "start_date"
        ]

        missing_columns = [
            col for col in required_columns
            if col not in df.columns
        ]

        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing columns: {missing_columns}"
            )

        # Store rejection reasons for each record
        rejection_reasons = [[] for _ in range(len(df))]

        # Check mandatory fields
        for col in required_columns:
            missing = (
                df[col].isna()
                | df[col].astype(str).str.strip().eq("")
            )

            for index in df.index[missing]:
                rejection_reasons[index].append(
                    f"{col} is missing"
                )

        # Validate premium
        premium = pd.to_numeric(
            df["premium"], errors="coerce"
        )

        for index in df.index[premium.isna()]:
            rejection_reasons[index].append(
                "Premium is not a valid number"
            )

        for index in df.index[premium.notna() & (premium <= 0)]:
            rejection_reasons[index].append(
                "Premium must be greater than zero"
            )

        # Validate start date
        dates = pd.to_datetime(
            df["start_date"], errors="coerce"
        )

        for index in df.index[dates.isna()]:
            rejection_reasons[index].append(
                "Invalid start date"
            )

        # Detect duplicate policy IDs
        duplicate = (
            df["policy_id"].notna()
            & df["policy_id"].astype(str).str.strip().ne("")
            & df["policy_id"].duplicated(keep="first")
        )

        for index in df.index[duplicate]:
            rejection_reasons[index].append(
                "Duplicate policy ID"
            )

        # Separate valid and rejected records
        rejected_mask = [
            len(reasons) > 0
            for reasons in rejection_reasons
        ]

        valid_df = df.loc[~pd.Series(
            rejected_mask, index=df.index
        )].copy()

        rejected_df = df.loc[
            pd.Series(rejected_mask, index=df.index)
        ].copy()

        rejected_df["rejection_reason"] = [
            "; ".join(rejection_reasons[index])
            for index in rejected_df.index
        ]

        # Save processing results
        curated_file = CURATED_DIR / f"{execution_id}_curated.csv"
        rejected_file = REJECTED_DIR / f"{execution_id}_rejected.csv"

        valid_df.to_csv(curated_file, index=False)
        rejected_df.to_csv(rejected_file, index=False)
	
	
        # Generate data quality report
        rejection_counts = Counter(
            reason
            for reasons in rejection_reasons
            for reason in reasons
        )

        report = {
            "execution_id": execution_id,
            "processing_status": "COMPLETED",
            "total_records": len(df),
            "valid_records": len(valid_df),
            "rejected_records": len(rejected_df),
            "valid_percentage": round(
                len(valid_df) / len(df) * 100, 2
            ) if len(df) else 0,
            "rejected_percentage": round(
                len(rejected_df) / len(df) * 100, 2
            ) if len(df) else 0,
            "rejection_reasons": dict(rejection_counts),
            "report_generated_at": time.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        }

        report_file = REPORT_DIR / f"{execution_id}_report.json"

        with report_file.open("w", encoding="utf-8") as file:
            json.dump(report, file, indent=4)
            end_time = datetime.now()
            duration_seconds = round((end_time - start_time).total_seconds(), 2)
            audit_record = {
            "execution_id": execution_id,
            "status": "COMPLETED",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration_seconds,
            "total_records": len(df),
            "valid_records": len(valid_df),
            "rejected_records": len(rejected_df)
        }

        audit_file = AUDIT_DIR / f"{execution_id}_audit.json"

        with audit_file.open("w", encoding="utf-8") as file:
            json.dump(audit_record, file, indent=4)

        return {
            "execution_id": execution_id,
            "status": "COMPLETED",
            "total_records": len(df),
            "valid_records": len(valid_df),
            "rejected_records": len(rejected_df),
            "curated_file": str(curated_file),
            "rejected_file": str(rejected_file),
            "report_file": str(report_file),
            "audit_file": str(audit_file)
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(error)}"
        )

