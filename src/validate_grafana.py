"""Consulta os três painéis do Grafana e salva evidência de dados reais do Athena."""

from __future__ import annotations

import argparse
import base64
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


def get_json(base_url: str, path: str, authorization: str) -> dict:
    request = urllib.request.Request(base_url + path, headers={"Authorization": authorization})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def query_panels(base_url: str, panels: list[dict], authorization: str) -> dict:
    queries = []
    for panel in panels:
        target = dict(panel["targets"][0])
        target.update(refId=str(panel["id"]), maxDataPoints=1000, intervalMs=60000)
        queries.append(target)
    now = datetime.now(timezone.utc)
    payload = json.dumps({
        "queries": queries,
        "from": (now - timedelta(hours=6)).isoformat(),
        "to": now.isoformat(),
    }).encode("utf-8")
    request = urllib.request.Request(
        base_url + "/api/ds/query", data=payload, method="POST",
        headers={"Authorization": authorization, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.load(response)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:3000")
    parser.add_argument("--password-file", type=Path, default=Path("data/staging/grafana-admin-password.txt"))
    parser.add_argument("--metrics", type=Path, default=Path("data/processed/quality.json"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/sprint3_grafana_validation.json"))
    args = parser.parse_args()
    authorization = "Basic " + base64.b64encode(
        ("admin:" + args.password_file.read_text(encoding="utf-8").strip()).encode("utf-8")
    ).decode("ascii")
    base_url = args.base_url.rstrip("/")
    health = get_json(base_url, "/api/datasources/uid/athena-medallion/health", authorization)
    if health.get("status") != "OK":
        raise RuntimeError(f"Fonte Athena indisponível: {health.get('message')}")
    dashboard = get_json(base_url, "/api/dashboards/uid/medallion-it-tickets", authorization)["dashboard"]
    panels = dashboard["panels"]
    if len(panels) != 3:
        raise RuntimeError(f"Painel contém {len(panels)} visualizações, esperado 3")
    datasource = get_json(base_url, "/api/datasources/uid/athena-medallion", authorization)
    settings = datasource["jsonData"]
    if (datasource["type"] != "grafana-athena-datasource" or
            settings["catalog"] != "AwsDataCatalog" or
            settings["database"] != "medallion_it_tickets_poc" or
            settings["workgroup"] != "primary"):
        raise RuntimeError("Fonte Grafana aponta para outro catálogo, banco ou workgroup")
    expected = json.loads(args.metrics.read_text(encoding="utf-8"))["valid_rows"]
    result = query_panels(base_url, panels, authorization)["results"]
    records = []
    for panel in panels:
        item = result[str(panel["id"])]
        if item.get("status") != 200 or item.get("error") or len(item.get("frames", [])) != 1:
            raise RuntimeError(f"Consulta Grafana falhou: {panel['title']}: {item.get('error')}")
        frame = item["frames"][0]
        columns = [field["name"] for field in frame["schema"]["fields"]]
        values = frame["data"]["values"]
        if panel["id"] == 1:
            total = sum(sum(column) for column in values[1:])
        else:
            total = sum(values[1])
        if total != expected:
            raise RuntimeError(f"{panel['title']}: {total} tickets, esperado {expected}")
        records.append({
            "panel_id": panel["id"],
            "title": panel["title"],
            "visualization": panel["type"],
            "sql": panel["targets"][0]["rawSQL"],
            "columns": columns,
            "rows": len(values[0]),
            "ticket_total": total,
            "values": values,
        })
    evidence = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "datasource_uid": datasource["uid"],
        "datasource_settings": settings,
        "datasource_health": health,
        "dashboard_uid": dashboard["uid"],
        "expected_valid_rows": expected,
        "panels": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "aprovado", "evidence": str(args.output),
                      "panels": [{"title": row["title"], "rows": row["rows"], "ticket_total": row["ticket_total"]}
                                 for row in records]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
