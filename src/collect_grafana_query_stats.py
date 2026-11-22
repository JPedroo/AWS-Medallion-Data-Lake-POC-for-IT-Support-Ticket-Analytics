"""Relaciona as consultas do painel Grafana aos IDs e bytes registrados pelo Athena."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import boto3


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "us-east-1"))
    parser.add_argument("--profile", default=os.getenv("AWS_PROFILE"))
    parser.add_argument("--grafana-evidence", type=Path, default=Path("data/processed/sprint3_grafana_validation.json"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/sprint3_grafana_athena_stats.json"))
    parser.add_argument("--since", help="Horário inicial ISO 8601; padrão: 5 minutos antes da validação Grafana")
    args = parser.parse_args()
    grafana = json.loads(args.grafana_evidence.read_text(encoding="utf-8"))
    checked_at = datetime.fromisoformat(grafana["checked_at_utc"])
    since = datetime.fromisoformat(args.since) if args.since else checked_at - timedelta(minutes=5)
    if since.tzinfo is None:
        parser.error("--since deve incluir fuso horário")
    sqls = {panel["sql"].strip() for panel in grafana["panels"]}
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    athena = session.client("athena")
    matched = []
    for page in athena.get_paginator("list_query_executions").paginate(WorkGroup="primary"):
        for query_id in page.get("QueryExecutionIds", []):
            query = athena.get_query_execution(QueryExecutionId=query_id)["QueryExecution"]
            submitted = query["Status"]["SubmissionDateTime"]
            if submitted < since or query["Query"].strip() not in sqls:
                continue
            stats = query.get("Statistics", {})
            matched.append({
                "query_execution_id": query_id,
                "sql": query["Query"],
                "submission_utc": submitted.astimezone(timezone.utc).isoformat(),
                "state": query["Status"]["State"],
                "data_scanned_bytes": stats.get("DataScannedInBytes", 0),
                "total_execution_ms": stats.get("TotalExecutionTimeInMillis"),
            })
    if len(matched) < 3 or any(query["state"] != "SUCCEEDED" for query in matched):
        raise RuntimeError("Não foram encontradas três consultas Grafana concluídas no Athena")
    output = {
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "since_utc": since.astimezone(timezone.utc).isoformat(),
        "workgroup": "primary",
        "matched_query_count": len(matched),
        "data_scanned_bytes_total": sum(query["data_scanned_bytes"] for query in matched),
        "queries": matched,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "aprovado", "evidence": str(args.output),
                      "matched_query_count": output["matched_query_count"],
                      "data_scanned_bytes_total": output["data_scanned_bytes_total"]},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
