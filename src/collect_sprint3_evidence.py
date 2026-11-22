"""Confere Bronze→Gold→Athena e registra evidência verificável da Sprint 3."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from build_sprint2 import OUTPUTS, PIPELINE_VERSION, bronze_key
from catalog_athena import DATABASE
from fetch_dataset import EXPECTED_SHA256


PROCESSED = Path("data/processed")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def object_evidence(s3, bucket: str, key: str, account: str) -> dict:
    head = s3.head_object(Bucket=bucket, Key=key, ExpectedBucketOwner=account, ChecksumMode="ENABLED")
    if head.get("ServerSideEncryption") != "AES256":
        raise RuntimeError(f"SSE-S3 ausente: {key}")
    return {
        "key": key,
        "bytes": head["ContentLength"],
        "version_id": head.get("VersionId"),
        "last_modified_utc": head["LastModified"].astimezone(timezone.utc).isoformat(),
        "checksum_sha256_base64": head.get("ChecksumSHA256"),
        "metadata": head.get("Metadata", {}),
        "sse": head["ServerSideEncryption"],
    }


def collect(session: boto3.Session, bucket: str) -> dict:
    identity = session.client("sts").get_caller_identity()
    account = identity["Account"]
    if identity["Arn"].endswith(":root"):
        raise RuntimeError("Não execute a POC com a conta root")
    if bucket != f"medallion-it-tickets-poc-{account}-{session.region_name}":
        raise RuntimeError("Bucket não corresponde à conta e região autenticadas")

    metrics = read_json(PROCESSED / "quality.json")
    build = read_json(PROCESSED / "sprint3_build.json")
    athena_checks = read_json(PROCESSED / "sprint3_athena.json")
    if not build["published"] or build["metrics"] != metrics:
        raise RuntimeError("Métricas da execução divergem do arquivo de qualidade")
    if metrics["source_sha256"] != EXPECTED_SHA256 or metrics["pipeline_version"] != PIPELINE_VERSION:
        raise RuntimeError("Fonte ou versão do pipeline divergente")
    if metrics["source_rows"] != metrics["silver_rows"] + metrics["duplicate_rows"]:
        raise RuntimeError("Bronze e Silver não reconciliam")
    if metrics["silver_rows"] != metrics["valid_rows"] + metrics["rejected_rows"]:
        raise RuntimeError("Silver e status de qualidade não reconciliam")
    for check in athena_checks["validation"]:
        if check["actual"] != check["expected"]:
            raise RuntimeError(f"Validação Athena falhou: {check['check']}")

    s3 = session.client("s3")
    s3.head_bucket(Bucket=bucket, ExpectedBucketOwner=account)
    csv_key = bronze_key()
    manifest_key = csv_key.rsplit("/", 1)[0] + "/manifest.json"
    objects = {"bronze_csv": object_evidence(s3, bucket, csv_key, account)}
    objects["bronze_manifest"] = object_evidence(s3, bucket, manifest_key, account)
    with s3.get_object(Bucket=bucket, Key=manifest_key, ExpectedBucketOwner=account)["Body"] as body:
        manifest = json.load(body)
    if (manifest["source_sha256"] != EXPECTED_SHA256 or
            manifest["source_rows"] != metrics["source_rows"] or
            manifest["source_bytes"] != objects["bronze_csv"]["bytes"] or
            manifest["csv_key"] != csv_key):
        raise RuntimeError("Manifesto Bronze diverge do CSV ou das métricas")
    if objects["bronze_csv"]["metadata"].get("sha256") != EXPECTED_SHA256:
        raise RuntimeError("Metadado SHA-256 da Bronze divergente")
    expected_checksum = base64.b64encode(bytes.fromhex(EXPECTED_SHA256)).decode("ascii")
    if objects["bronze_csv"]["checksum_sha256_base64"] != expected_checksum:
        raise RuntimeError("Checksum SHA-256 da Bronze divergente")

    for name, key in OUTPUTS.items():
        obj = object_evidence(s3, bucket, key, account)
        if obj["metadata"].get("source-sha256") != EXPECTED_SHA256 or obj["metadata"].get("pipeline-version") != PIPELINE_VERSION:
            raise RuntimeError(f"Proveniência divergente: {key}")
        objects[name] = obj
    quality_key = "silver/quality/metrics.json"
    objects["quality"] = object_evidence(s3, bucket, quality_key, account)
    digest = base64.b64encode(hashlib.sha256((PROCESSED / "quality.json").read_bytes()).digest()).decode("ascii")
    if objects["quality"]["checksum_sha256_base64"] != digest:
        raise RuntimeError("Checksum das métricas no S3 divergente")

    glue = session.client("glue")
    table_keys = {
        "silver_tickets": "silver/tickets/",
        "gold_tickets_by_type_priority": "gold/tickets_by_type_priority/",
        "gold_tickets_by_queue_language": "gold/tickets_by_queue_language/",
    }
    tables = {}
    for table, prefix in table_keys.items():
        location = glue.get_table(DatabaseName=DATABASE, Name=table)["Table"]["StorageDescriptor"]["Location"]
        if location.rstrip("/") != f"s3://{bucket}/{prefix}".rstrip("/"):
            raise RuntimeError(f"Localização Glue divergente: {table}")
        tables[table] = location

    athena = session.client("athena")
    executions = []
    for entry in athena_checks["ddl"] + athena_checks["validation"]:
        execution = athena.get_query_execution(QueryExecutionId=entry["query_execution_id"])["QueryExecution"]
        if execution["Status"]["State"] != "SUCCEEDED":
            raise RuntimeError(f"Consulta Athena não concluída: {entry['query_execution_id']}")
        stats = execution["Statistics"]
        if stats.get("DataScannedInBytes", 0) != entry["data_scanned_bytes"]:
            raise RuntimeError(f"Bytes Athena divergentes: {entry['query_execution_id']}")
        executions.append({
            "query_execution_id": entry["query_execution_id"],
            "check": entry.get("check", entry.get("file")),
            "state": "SUCCEEDED",
            "data_scanned_bytes": stats.get("DataScannedInBytes", 0),
            "total_execution_ms": stats.get("TotalExecutionTimeInMillis"),
            "engine_execution_ms": stats.get("EngineExecutionTimeInMillis"),
            "submission_utc": execution["Status"]["SubmissionDateTime"].astimezone(timezone.utc).isoformat(),
        })

    collected_at = datetime.now(timezone.utc).isoformat()
    cost = {"status": "indisponivel", "scope": "orcamento mensal da conta; nao atribuivel exclusivamente a POC"}
    try:
        budget = session.client("budgets", region_name="us-east-1").describe_budget(
            AccountId=account, BudgetName="medallion-it-tickets-poc"
        )["Budget"]
        spend = budget.get("CalculatedSpend", {}).get("ActualSpend", {})
        cost = {
            "status": "observado_no_orcamento",
            "scope": "orcamento mensal da conta; nao atribuivel exclusivamente a POC",
            "actual_spend": spend.get("Amount"),
            "unit": spend.get("Unit"),
            "budget_limit": budget.get("BudgetLimit"),
        }
    except ClientError as error:
        cost["error_code"] = error.response.get("Error", {}).get("Code")

    return {
        "collected_at_utc": collected_at,
        "account_id": account,
        "principal_arn": identity["Arn"],
        "region": session.region_name,
        "bucket": bucket,
        "pipeline_processing_seconds": build["processing_seconds"],
        "metrics": metrics,
        "bronze_manifest_run_id": manifest["pipeline_run_id"],
        "bronze_ingested_at": manifest["ingested_at"],
        "objects": objects,
        "glue_tables": tables,
        "athena_validation": athena_checks["validation"],
        "athena_executions": executions,
        "athena_data_scanned_bytes_total": sum(x["data_scanned_bytes"] for x in executions),
        "cost": cost,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", default=os.getenv("POC_BUCKET"), required=False)
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "us-east-1"))
    parser.add_argument("--profile", default=os.getenv("AWS_PROFILE"))
    parser.add_argument("--output", type=Path, default=PROCESSED / "sprint3_evidence.json")
    args = parser.parse_args()
    if not args.bucket:
        parser.error("Informe --bucket ou POC_BUCKET")
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    evidence = collect(session, args.bucket)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "aprovado",
        "evidence": str(args.output),
        "source_rows": evidence["metrics"]["source_rows"],
        "valid_rows": evidence["metrics"]["valid_rows"],
        "athena_data_scanned_bytes_total": evidence["athena_data_scanned_bytes_total"],
        "cost": evidence["cost"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
