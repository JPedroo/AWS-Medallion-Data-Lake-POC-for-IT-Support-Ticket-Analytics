"""Registra as tabelas externas e valida as contagens pelo Athena."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path

import boto3


SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
DDL_FILES = ("01_database.sql", "02_silver.sql", "03_gold_type_priority.sql", "04_gold_queue_language.sql")
DATABASE = "medallion_it_tickets_poc"


def query(athena, sql: str, bucket: str, database: bool = True) -> tuple[list[list[str]], dict]:
    context = {"Catalog": "AwsDataCatalog"}
    if database:
        context["Database"] = DATABASE
    execution_id = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext=context,
        ResultConfiguration={
            "OutputLocation": f"s3://{bucket}/athena-results/",
            "EncryptionConfiguration": {"EncryptionOption": "SSE_S3"},
        },
        WorkGroup="primary",
    )["QueryExecutionId"]
    for _ in range(60):
        execution = athena.get_query_execution(QueryExecutionId=execution_id)["QueryExecution"]
        state = execution["Status"]["State"]
        if state == "SUCCEEDED":
            break
        if state in {"FAILED", "CANCELLED"}:
            raise RuntimeError(f"Athena {execution_id}: {state}: {execution['Status'].get('StateChangeReason', '')}")
        time.sleep(2)
    else:
        raise TimeoutError(f"Athena {execution_id}: consulta não terminou em 120 s")
    rows = []
    for page in athena.get_paginator("get_query_results").paginate(QueryExecutionId=execution_id):
        for row in page["ResultSet"]["Rows"]:
            rows.append([cell.get("VarCharValue", "") for cell in row["Data"]])
    return rows[1:], {
        "query_execution_id": execution_id,
        "data_scanned_bytes": execution["Statistics"].get("DataScannedInBytes", 0),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", default=os.getenv("POC_BUCKET"), required=False)
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "us-east-1"))
    parser.add_argument("--profile", default=os.getenv("AWS_PROFILE"))
    parser.add_argument("--metrics", type=Path, default=Path("data/processed/quality.json"))
    parser.add_argument("--evidence", type=Path, default=Path("data/processed/athena_validation.json"))
    args = parser.parse_args()
    if not args.bucket or not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", args.bucket):
        parser.error("Informe um --bucket S3 válido ou POC_BUCKET")
    metrics = json.loads(args.metrics.read_text(encoding="utf-8"))
    session = boto3.Session(profile_name=args.profile, region_name=args.region) if args.profile else boto3.Session(region_name=args.region)
    athena = session.client("athena")
    evidence = {"ddl": [], "validation": []}
    for filename in DDL_FILES:
        sql = (SQL_DIR / filename).read_text(encoding="utf-8").format(bucket=args.bucket).strip()
        _, result = query(athena, sql, args.bucket, database=filename != "01_database.sql")
        evidence["ddl"].append({"file": filename, **result})
    checks = (
        ("silver_valid", "SELECT count(*) FROM silver_tickets WHERE quality_status = 'valid'", metrics["valid_rows"]),
        ("silver_rejected", "SELECT count(*) FROM silver_tickets WHERE quality_status = 'rejected'", metrics["rejected_rows"]),
        ("gold_type_priority", "SELECT coalesce(sum(ticket_count), 0) FROM gold_tickets_by_type_priority", metrics["valid_rows"]),
        ("gold_queue_language", "SELECT coalesce(sum(ticket_count), 0) FROM gold_tickets_by_queue_language", metrics["valid_rows"]),
        (
            "gold_type_priority_groups",
            "WITH expected AS (SELECT \"type\", priority, count(*) AS n FROM silver_tickets WHERE quality_status = 'valid' GROUP BY \"type\", priority) "
            "SELECT count(*) FROM expected e FULL OUTER JOIN gold_tickets_by_type_priority g "
            "ON e.\"type\" = g.\"type\" AND e.priority = g.priority WHERE coalesce(e.n, -1) <> coalesce(g.ticket_count, -1)",
            0,
        ),
        (
            "gold_queue_language_groups",
            "WITH expected AS (SELECT queue, language, count(*) AS n FROM silver_tickets WHERE quality_status = 'valid' GROUP BY queue, language) "
            "SELECT count(*) FROM expected e FULL OUTER JOIN gold_tickets_by_queue_language g "
            "ON e.queue = g.queue AND e.language = g.language WHERE coalesce(e.n, -1) <> coalesce(g.ticket_count, -1)",
            0,
        ),
    )
    for label, sql, expected in checks:
        rows, result = query(athena, sql, args.bucket)
        actual = int(rows[0][0])
        evidence["validation"].append({"check": label, "expected": expected, "actual": actual, **result})
        if actual != expected:
            raise RuntimeError(f"{label}: Athena retornou {actual}, esperado {expected}")
    output = json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
