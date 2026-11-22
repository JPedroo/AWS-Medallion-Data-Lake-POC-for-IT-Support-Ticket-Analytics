#!/usr/bin/env bash
# Reexecuta Silver/Gold, valida o Athena e coleta evidências da Sprint 3.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export AWS_PROFILE="${AWS_PROFILE:-medallion-poc}"
export AWS_REGION="${AWS_REGION:-us-east-1}"
export SPARK_LOCAL_IP="${SPARK_LOCAL_IP:-127.0.0.1}"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
AWS_BIN="${AWS_BIN:-$ROOT/.tools/bin/aws}"
ACCOUNT="$($AWS_BIN --profile "$AWS_PROFILE" --region "$AWS_REGION" sts get-caller-identity --query Account --output text)"
export POC_BUCKET="medallion-it-tickets-poc-$ACCOUNT-$AWS_REGION"
mkdir -p data/processed

"$PYTHON" src/build_sprint2.py \
  --bucket "$POC_BUCKET" --region "$AWS_REGION" --profile "$AWS_PROFILE" --publish \
  > data/processed/sprint3_build.json
"$PYTHON" src/catalog_athena.py \
  --bucket "$POC_BUCKET" --region "$AWS_REGION" --profile "$AWS_PROFILE" \
  --evidence data/processed/sprint3_athena.json \
  > data/processed/sprint3_catalog_stdout.json
"$PYTHON" src/collect_sprint3_evidence.py \
  --bucket "$POC_BUCKET" --region "$AWS_REGION" --profile "$AWS_PROFILE"
