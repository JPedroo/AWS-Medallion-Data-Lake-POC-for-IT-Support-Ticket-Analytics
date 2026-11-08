#!/usr/bin/env bash
# Cria uma política IAM mínima para um usuário IAM existente da ingestão Bronze.
set -euo pipefail
: "${AWS_PROFILE:?Defina AWS_PROFILE}"
: "${AWS_REGION:?Defina AWS_REGION}"
: "${POC_BUCKET:?Defina POC_BUCKET}"
: "${POC_INGEST_USER:?Defina POC_INGEST_USER com um usuário IAM existente}"
AWS_BIN="${AWS_BIN:-$(command -v aws || true)}"
if [[ -z "$AWS_BIN" && -x .tools/bin/aws ]]; then AWS_BIN=.tools/bin/aws; fi
if [[ -z "$AWS_BIN" ]]; then echo "AWS CLI não encontrado" >&2; exit 1; fi
aws_poc() { "$AWS_BIN" --profile "$AWS_PROFILE" --region "$AWS_REGION" "$@"; }
ACCOUNT_ID="$(aws_poc sts get-caller-identity --query Account --output text)"
POLICY_NAME="medallion-it-tickets-bronze-ingest"
POLICY_ARN="arn:aws:iam::$ACCOUNT_ID:policy/$POLICY_NAME"
TMP_POLICY="$(mktemp)"
trap 'rm -f "$TMP_POLICY"' EXIT
cat > "$TMP_POLICY" <<EOF
{"Version":"2012-10-17","Statement":[
  {"Sid":"ListBronze","Effect":"Allow","Action":"s3:ListBucket","Resource":"arn:aws:s3:::$POC_BUCKET","Condition":{"StringLike":{"s3:prefix":["bronze/*"]}}},
  {"Sid":"BucketLocation","Effect":"Allow","Action":"s3:GetBucketLocation","Resource":"arn:aws:s3:::$POC_BUCKET"},
  {"Sid":"ReadWriteBronze","Effect":"Allow","Action":["s3:GetObject","s3:PutObject"],"Resource":"arn:aws:s3:::$POC_BUCKET/bronze/*"}
]}
EOF
if ! aws_poc iam get-policy --policy-arn "$POLICY_ARN" >/dev/null 2>&1; then
  aws_poc iam create-policy --policy-name "$POLICY_NAME" \
    --policy-document "file://$TMP_POLICY" >/dev/null
fi
aws_poc iam attach-user-policy --user-name "$POC_INGEST_USER" --policy-arn "$POLICY_ARN"
aws_poc iam list-attached-user-policies --user-name "$POC_INGEST_USER" \
  --query "AttachedPolicies[?PolicyArn=='$POLICY_ARN']"
