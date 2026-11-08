"""Valida e ingere o CSV original e um manifesto imutável na Bronze do S3."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


DATASET = "tobiasbueck/multilingual-customer-support-tickets"
VERSION = 14
FIELDS = (
    "subject", "body", "answer", "type", "queue", "priority", "language",
    "business_type", "tag_1", "tag_2", "tag_3", "tag_4", "tag_5",
    "tag_6", "tag_7", "tag_8", "tag_9",
)


def inspect_csv(path: Path) -> tuple[int, list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, strict=True)
        header = next(reader)
        if tuple(header) != FIELDS:
            raise ValueError(f"Esquema inesperado: {header}")
        rows = 0
        for number, row in enumerate(reader, start=2):
            if len(row) != len(header):
                raise ValueError(f"Linha {number}: {len(row)} campos; esperado {len(header)}")
            rows += 1
    if rows == 0:
        raise ValueError("CSV sem registros")
    return rows, header


def sha256_file(path: Path) -> tuple[str, str]:
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").digest()
    return digest.hex(), base64.b64encode(digest).decode("ascii")


def head_or_none(client, bucket: str, key: str):
    try:
        return client.head_object(Bucket=bucket, Key=key, ChecksumMode="ENABLED")
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
            return None
        raise


def put_once(client, bucket: str, key: str, **kwargs) -> None:
    try:
        client.put_object(Bucket=bucket, Key=key, IfNoneMatch="*", **kwargs)
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") not in {"PreconditionFailed", "412", "ConditionalRequestConflict", "409"}:
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--bucket", default=os.getenv("POC_BUCKET"))
    parser.add_argument("--region", default=os.getenv("AWS_REGION"))
    parser.add_argument("--profile", default=os.getenv("AWS_PROFILE"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    source = args.source.resolve()
    if not source.is_file() or source.name != "dataset-tickets-multi-lang3-4k.csv":
        parser.error("--source deve apontar para o CSV original versionado escolhido")
    rows, columns = inspect_csv(source)
    digest, checksum_b64 = sha256_file(source)
    from fetch_dataset import EXPECTED_SHA256
    if digest != EXPECTED_SHA256:
        raise ValueError(f"SHA-256 diferente do arquivo validado: {digest}")
    key_base = f"bronze/dataset=multilingual-customer-support-tickets/version={VERSION}/sha256={digest}"
    csv_key = f"{key_base}/{source.name}"
    manifest_key = f"{key_base}/manifest.json"
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    manifest = {
        "schema_version": 1,
        "dataset": DATASET,
        "dataset_version": VERSION,
        "source_url": f"https://www.kaggle.com/datasets/{DATASET}",
        "license": "CC BY 4.0",
        "source_file": source.name,
        "source_sha256": digest,
        "source_bytes": source.stat().st_size,
        "source_rows": rows,
        "source_columns": columns,
        "encoding": "UTF-8",
        "delimiter": ",",
        "ingested_at": now,
        "pipeline_run_id": str(uuid.uuid4()),
        "bucket": args.bucket,
        "csv_key": csv_key,
        "manifest_key": manifest_key,
    }
    if args.dry_run:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return
    if not args.bucket or not args.region:
        parser.error("Informe --bucket e --region ou POC_BUCKET e AWS_REGION")
    session = boto3.Session(profile_name=args.profile, region_name=args.region) if args.profile else boto3.Session(region_name=args.region)
    client = session.client("s3")
    existing_csv = head_or_none(client, args.bucket, csv_key)
    if existing_csv is None:
        with source.open("rb") as stream:
            put_once(
                client, args.bucket, csv_key, Body=stream,
                ContentLength=source.stat().st_size,
                ContentType="text/csv; charset=utf-8",
                ServerSideEncryption="AES256", ChecksumSHA256=checksum_b64,
                Metadata={"sha256": digest, "dataset-version": str(VERSION)},
            )
        existing_csv = head_or_none(client, args.bucket, csv_key)
    if existing_csv is None or existing_csv["ContentLength"] != source.stat().st_size or existing_csv.get("Metadata", {}).get("sha256") != digest:
        raise RuntimeError("Objeto Bronze existente diverge do CSV local")
    if existing_csv.get("ChecksumSHA256") and existing_csv["ChecksumSHA256"] != checksum_b64:
        raise RuntimeError("Checksum do S3 diverge do CSV local")
    existing_manifest = head_or_none(client, args.bucket, manifest_key)
    if existing_manifest is None:
        body = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        put_once(client, args.bucket, manifest_key, Body=body, ContentType="application/json", ServerSideEncryption="AES256")
    with client.get_object(Bucket=args.bucket, Key=manifest_key)["Body"] as body:
        saved_manifest = json.loads(body.read())
    if saved_manifest.get("source_sha256") != digest or saved_manifest.get("csv_key") != csv_key:
        raise RuntimeError("Manifesto Bronze existente diverge do CSV local")
    print(json.dumps({"csv": f"s3://{args.bucket}/{csv_key}", "manifest": f"s3://{args.bucket}/{manifest_key}", "sha256": digest, "rows": rows}, ensure_ascii=False))


if __name__ == "__main__":
    main()
