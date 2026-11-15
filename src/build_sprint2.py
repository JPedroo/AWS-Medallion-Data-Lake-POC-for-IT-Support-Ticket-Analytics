"""Constrói Silver e duas agregações Gold a partir da Bronze versionada."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import tempfile
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from pyspark.sql import SparkSession, Window, functions as F, types as T

from fetch_dataset import EXPECTED_SHA256
from ingest_bronze import FIELDS, VERSION, inspect_csv, sha256_file


DATASET = "multilingual-customer-support-tickets"
PIPELINE_VERSION = "sprint2-v1"
OUTPUTS = {
    "silver": "silver/tickets/part-00000.parquet",
    "gold_type_priority": "gold/tickets_by_type_priority/part-00000.parquet",
    "gold_queue_language": "gold/tickets_by_queue_language/part-00000.parquet",
}


def bronze_key() -> str:
    return (
        f"bronze/dataset={DATASET}/version={VERSION}/sha256={EXPECTED_SHA256}/"
        "dataset-tickets-multi-lang3-4k.csv"
    )


def normalize(frame):
    text_fields = {"subject", "body", "answer"}
    lower_fields = {"type", "priority", "language"}
    for name in FIELDS:
        value = F.trim(F.coalesce(F.col(name), F.lit("")))
        if name in lower_fields:
            value = F.lower(value)
        if name not in text_fields:
            value = F.when(value == "", F.lit("unknown")).otherwise(value)
        frame = frame.withColumn(name, value)
    frame = frame.withColumn("subject_missing", F.col("subject") == "")
    frame = frame.withColumn("body_missing", F.col("body") == "")
    frame = frame.withColumn(
        "quality_status",
        F.when(F.col("subject_missing") & F.col("body_missing"), "rejected").otherwise("valid"),
    )
    # JSON de struct preserva a fronteira entre campos e gera o mesmo ID em reexecuções.
    frame = frame.withColumn(
        "ticket_id", F.sha2(F.to_json(F.struct(*[F.col(name) for name in FIELDS])), 256)
    )
    return frame


def deduplicate(normalized):
    order = Window.partitionBy("ticket_id").orderBy(F.to_json(F.struct(*[F.col(n) for n in FIELDS])))
    return normalized.withColumn("_rank", F.row_number().over(order)).where(F.col("_rank") == 1).drop("_rank")


def build(spark: SparkSession, source: Path, output_dir: Path) -> dict:
    rows, _ = inspect_csv(source)
    digest, _ = sha256_file(source)
    if digest != EXPECTED_SHA256:
        raise ValueError(f"SHA-256 da Bronze divergente: {digest}")
    schema = T.StructType([T.StructField(name, T.StringType(), True) for name in FIELDS])
    raw = (
        spark.read.option("header", True).option("multiLine", True)
        .option("quote", '"').option("escape", '"').option("mode", "FAILFAST")
        .schema(schema).csv(str(source))
    )
    if raw.count() != rows:
        raise RuntimeError("Contagem Spark divergente do CSV validado")
    normalized = normalize(raw)
    # IDs iguais representam o mesmo conteúdo normalizado; a ordenação é determinística.
    silver = deduplicate(normalized).cache()
    kept = silver.count()
    valid = silver.where(F.col("quality_status") == "valid").cache()
    valid_count = valid.count()
    rejected = kept - valid_count
    metrics = {
        "schema_version": 1,
        "pipeline_version": PIPELINE_VERSION,
        "source_sha256": digest,
        "source_rows": rows,
        "silver_rows": kept,
        "duplicate_rows": rows - kept,
        "valid_rows": valid_count,
        "rejected_rows": rejected,
        "subject_missing_rows": silver.where(F.col("subject_missing")).count(),
        "body_missing_rows": silver.where(F.col("body_missing")).count(),
        "unknown_dimension_rows": silver.where(
            (F.col("type") == "unknown") | (F.col("queue") == "unknown") |
            (F.col("priority") == "unknown") | (F.col("language") == "unknown")
        ).count(),
    }
    metrics["subject_missing_pct"] = round(100 * metrics["subject_missing_rows"] / kept, 2)
    metrics["body_missing_pct"] = round(100 * metrics["body_missing_rows"] / kept, 2)
    if rows != kept + metrics["duplicate_rows"] or kept != valid_count + rejected:
        raise RuntimeError("Falha na reconciliação de linhas")
    if silver.select("ticket_id").distinct().count() != kept:
        raise RuntimeError("ticket_id duplicado na Silver")
    gold_a = valid.groupBy("type", "priority").agg(F.count("*").alias("ticket_count"))
    gold_b = valid.groupBy("queue", "language").agg(F.count("*").alias("ticket_count"))
    for name, frame in (
        ("silver", silver.select("ticket_id", *FIELDS, "subject_missing", "body_missing", "quality_status")),
        ("gold_type_priority", gold_a),
        ("gold_queue_language", gold_b),
    ):
        target = output_dir / name
        sort_columns = ["ticket_id"] if name == "silver" else ["type", "priority"] if name == "gold_type_priority" else ["queue", "language"]
        frame.orderBy(*sort_columns).coalesce(1).write.mode("overwrite").option("compression", "snappy").parquet(str(target))
        if name != "silver":
            total = spark.read.parquet(str(target)).agg(F.sum("ticket_count")).first()[0]
            if total != valid_count:
                raise RuntimeError(f"Agregação {name} não reconcilia com a Silver")
        metrics[f"{name}_parquet_bytes"] = next(target.glob("*.parquet")).stat().st_size
    (output_dir / "quality.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    valid.unpersist()
    silver.unpersist()
    return metrics


def publish(s3, bucket: str, output_dir: Path, account_id: str) -> None:
    objects = [(output_dir / name, key) for name, key in OUTPUTS.items()]
    objects = [(next(path.glob("*.parquet")), key) for path, key in objects]
    objects.append((output_dir / "quality.json", "silver/quality/metrics.json"))
    for path, key in objects:
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).digest()
        checksum = base64.b64encode(digest).decode("ascii")
        try:
            head = s3.head_object(Bucket=bucket, Key=key, ChecksumMode="ENABLED", ExpectedBucketOwner=account_id)
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") not in {"404", "NoSuchKey", "NotFound"}:
                raise
            head = None
        if head:
            if key.endswith(".json"):
                if head.get("ChecksumSHA256") != checksum:
                    raise RuntimeError(f"Métricas existentes divergem: s3://{bucket}/{key}")
            elif head.get("Metadata", {}).get("source-sha256") != EXPECTED_SHA256 or head.get("Metadata", {}).get("pipeline-version") != PIPELINE_VERSION:
                raise RuntimeError(f"Parquet existente tem outra proveniência: s3://{bucket}/{key}")
            continue
        try:
            s3.put_object(
                Bucket=bucket, Key=key, Body=payload, IfNoneMatch="*",
                ExpectedBucketOwner=account_id,
                ChecksumSHA256=checksum, ServerSideEncryption="AES256",
                Metadata={"source-sha256": EXPECTED_SHA256, "pipeline-version": PIPELINE_VERSION},
                ContentType="application/json" if key.endswith(".json") else "application/octet-stream",
            )
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") not in {"PreconditionFailed", "412"}:
                raise
        head = s3.head_object(Bucket=bucket, Key=key, ChecksumMode="ENABLED", ExpectedBucketOwner=account_id)
        if head.get("ChecksumSHA256") != checksum:
            raise RuntimeError(f"Checksum divergente após upload: {key}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="CSV local validado; sem este argumento, baixa a Bronze do S3")
    parser.add_argument("--bucket", default=os.getenv("POC_BUCKET"))
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "us-east-1"))
    parser.add_argument("--profile", default=os.getenv("AWS_PROFILE"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    if (args.publish or not args.source) and not args.bucket:
        parser.error("Informe --bucket ou POC_BUCKET para baixar/publicar no S3")
    if args.bucket and not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", args.bucket):
        parser.error("Nome de bucket inválido")
    session = boto3.Session(profile_name=args.profile, region_name=args.region) if args.profile else boto3.Session(region_name=args.region)
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="medallion-sprint2-") as temporary:
        work = Path(temporary)
        source = args.source
        s3 = None
        if source is None or args.publish:
            s3 = session.client("s3")
            account_id = session.client("sts").get_caller_identity()["Account"]
            expected_bucket = f"medallion-it-tickets-poc-{account_id}-{args.region}"
            if args.bucket != expected_bucket:
                raise ValueError(f"Bucket da POC diferente do esperado para a conta autenticada: {expected_bucket}")
            s3.head_bucket(Bucket=args.bucket, ExpectedBucketOwner=account_id)
        if source is None:
            source = work / "dataset-tickets-multi-lang3-4k.csv"
            s3.download_file(args.bucket, bronze_key(), str(source), ExtraArgs={"ExpectedBucketOwner": account_id})
        spark = SparkSession.builder.master("local[2]").appName("medallion-sprint2").getOrCreate()
        spark.sparkContext.setLogLevel("ERROR")
        try:
            metrics = build(spark, source.resolve(), args.output_dir.resolve())
        finally:
            spark.stop()
        if args.publish:
            publish(s3, args.bucket, args.output_dir.resolve(), account_id)
        print(json.dumps({"published": args.publish, "processing_seconds": round(time.perf_counter() - started, 2), "metrics": metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
