#!/usr/bin/env bash
# Provisionamento mínimo da Sprint 1. Todas as chamadas AWS usam o CLI.
set -euo pipefail

: "${AWS_PROFILE:?Defina AWS_PROFILE com um perfil autenticado}"
: "${AWS_REGION:?Defina AWS_REGION}"
: "${POC_BUCKET:?Defina POC_BUCKET com nome globalmente único}"
: "${POC_BUDGET_EMAIL:?Defina POC_BUDGET_EMAIL}"
: "${POC_BUDGET_USD:=5}"

AWS_BIN="${AWS_BIN:-$(command -v aws || true)}"
if [[ -z "$AWS_BIN" && -x .tools/bin/aws ]]; then AWS_BIN=.tools/bin/aws; fi
if [[ -z "$AWS_BIN" ]]; then echo "AWS CLI não encontrado" >&2; exit 1; fi
aws_poc() { "$AWS_BIN" --profile "$AWS_PROFILE" --region "$AWS_REGION" "$@"; }

IDENTITY_ARN="$(aws_poc sts get-caller-identity --query Arn --output text)"
if [[ "$IDENTITY_ARN" == *:root ]]; then
  echo "Use uma identidade IAM/SSO; a conta root não deve provisionar a POC" >&2
  exit 1
fi
ACCOUNT_ID="$(aws_poc sts get-caller-identity --query Account --output text)"
BUDGET_NAME="medallion-it-tickets-poc"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

cat > "$TMP_DIR/budget.json" <<EOF
{"BudgetName":"$BUDGET_NAME","BudgetType":"COST","TimeUnit":"MONTHLY","BudgetLimit":{"Amount":"$POC_BUDGET_USD","Unit":"USD"}}
EOF
cat > "$TMP_DIR/notifications.json" <<EOF
[
  {"Notification":{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN","Threshold":80,"ThresholdType":"PERCENTAGE"},"Subscribers":[{"SubscriptionType":"EMAIL","Address":"$POC_BUDGET_EMAIL"}]},
  {"Notification":{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN","Threshold":100,"ThresholdType":"PERCENTAGE"},"Subscribers":[{"SubscriptionType":"EMAIL","Address":"$POC_BUDGET_EMAIL"}]}
]
EOF
if ! aws_poc budgets describe-budget --account-id "$ACCOUNT_ID" --budget-name "$BUDGET_NAME" > "$TMP_DIR/budget-status.json" 2> "$TMP_DIR/budget-error.txt"; then
  if ! grep -q 'NotFound\|ResourceNotFound' "$TMP_DIR/budget-error.txt"; then cat "$TMP_DIR/budget-error.txt" >&2; exit 1; fi
  aws_poc budgets create-budget --account-id "$ACCOUNT_ID" \
    --budget "file://$TMP_DIR/budget.json" \
    --notifications-with-subscribers "file://$TMP_DIR/notifications.json"
  echo "Orçamento criado: $BUDGET_NAME ($POC_BUDGET_USD USD/mês)"
else
  echo "Orçamento já existe: $BUDGET_NAME (confira limite e destinatário no CLI)"
fi

if ! aws_poc s3api head-bucket --bucket "$POC_BUCKET" 2> "$TMP_DIR/bucket-error.txt"; then
  if [[ "$AWS_REGION" == "us-east-1" ]]; then
    aws_poc s3api create-bucket --bucket "$POC_BUCKET"
  else
    aws_poc s3api create-bucket --bucket "$POC_BUCKET" \
      --create-bucket-configuration "LocationConstraint=$AWS_REGION"
  fi
  echo "Bucket criado: $POC_BUCKET"
fi
aws_poc s3api put-public-access-block --bucket "$POC_BUCKET" \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws_poc s3api put-bucket-ownership-controls --bucket "$POC_BUCKET" \
  --ownership-controls 'Rules=[{ObjectOwnership=BucketOwnerEnforced}]'
aws_poc s3api put-bucket-encryption --bucket "$POC_BUCKET" \
  --server-side-encryption-configuration \
  'Rules=[{ApplyServerSideEncryptionByDefault={SSEAlgorithm=AES256}}]'
aws_poc s3api put-bucket-versioning --bucket "$POC_BUCKET" \
  --versioning-configuration Status=Enabled
aws_poc s3api put-bucket-tagging --bucket "$POC_BUCKET" \
  --tagging 'TagSet=[{Key=Project,Value=medallion-it-tickets-poc},{Key=Environment,Value=poc}]'

cat > "$TMP_DIR/bucket-policy.json" <<EOF
{"Version":"2012-10-17","Statement":[{"Sid":"DenyInsecureTransport","Effect":"Deny","Principal":"*","Action":"s3:*","Resource":["arn:aws:s3:::$POC_BUCKET","arn:aws:s3:::$POC_BUCKET/*"],"Condition":{"Bool":{"aws:SecureTransport":"false"}}}]}
EOF
aws_poc s3api put-bucket-policy --bucket "$POC_BUCKET" \
  --policy "file://$TMP_DIR/bucket-policy.json"

aws_poc s3api get-public-access-block --bucket "$POC_BUCKET" \
  --query PublicAccessBlockConfiguration
aws_poc s3api get-bucket-encryption --bucket "$POC_BUCKET" \
  --query ServerSideEncryptionConfiguration
aws_poc s3api get-bucket-versioning --bucket "$POC_BUCKET"
aws_poc budgets describe-budget --account-id "$ACCOUNT_ID" --budget-name "$BUDGET_NAME" \
  --query 'Budget.[BudgetName,BudgetLimit]'
echo "Provisionamento concluído. Prefixos lógicos: bronze/, silver/, gold/, athena-results/."
