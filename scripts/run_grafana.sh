#!/usr/bin/env bash
# Inicia o Grafana local com credenciais temporárias do perfil AWS da POC.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AWS_BIN="${AWS_BIN:-$ROOT/.tools/bin/aws}"
PROFILE="${AWS_PROFILE:-medallion-poc}"
REGION="${AWS_REGION:-us-east-1}"
STAGING="$ROOT/data/staging"
ENV_FILE="$STAGING/grafana-aws.env"
PASSWORD_FILE="$STAGING/grafana-admin-password.txt"

if [[ ! -x "$AWS_BIN" ]]; then
  AWS_BIN="$(command -v aws || true)"
fi
if [[ -z "$AWS_BIN" || ! -x "$AWS_BIN" ]]; then
  echo "AWS CLI não encontrado; instale ou defina AWS_BIN." >&2
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "Docker Desktop não está em execução. Inicie-o e repita este comando." >&2
  exit 1
fi

ACCOUNT="$($AWS_BIN --profile "$PROFILE" --region "$REGION" sts get-caller-identity --query Account --output text)" || {
  echo "Sessão AWS indisponível. Execute aws login --profile $PROFILE e repita." >&2
  exit 1
}
if [[ ! "$ACCOUNT" =~ ^[0-9]{12}$ ]]; then
  echo "A conta AWS retornada não é válida." >&2
  exit 1
fi
BUCKET="medallion-it-tickets-poc-$ACCOUNT-$REGION"
mkdir -p "$STAGING"
umask 077

if [[ ! -f "$PASSWORD_FILE" ]]; then
  python3 - "$PASSWORD_FILE" <<'PY'
import os
import secrets
import sys

fd = os.open(sys.argv[1], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as output:
    output.write(secrets.token_hex(24) + "\n")
PY
fi

"$AWS_BIN" --profile "$PROFILE" --region "$REGION" configure export-credentials --format process |
  python3 -c '
import json, os, pathlib, sys

creds = json.load(sys.stdin)
for field in ("AccessKeyId", "SecretAccessKey", "SessionToken", "Expiration"):
    if not creds.get(field):
        raise SystemExit(f"Credencial temporária sem {field}")
target = pathlib.Path(sys.argv[1])
temporary = target.with_suffix(".tmp")
values = {
    "AWS_ACCESS_KEY_ID": creds["AccessKeyId"],
    "AWS_SECRET_ACCESS_KEY": creds["SecretAccessKey"],
    "AWS_SESSION_TOKEN": creds["SessionToken"],
    "AWS_REGION": sys.argv[2],
    "AWS_DEFAULT_REGION": sys.argv[2],
    "AWS_EC2_METADATA_DISABLED": "true",
    "POC_BUCKET": sys.argv[3],
    "GF_SECURITY_ADMIN_USER": "admin",
    "GF_SECURITY_ADMIN_PASSWORD": pathlib.Path(sys.argv[4]).read_text(encoding="utf-8").strip(),
}
with temporary.open("w", encoding="utf-8") as output:
    for key, value in values.items():
        if "\n" in value or "\r" in value:
            raise SystemExit(f"Valor inválido: {key}")
        output.write(f"{key}={value}\n")
os.chmod(temporary, 0o600)
temporary.replace(target)
' "$ENV_FILE" "$REGION" "$BUCKET" "$PASSWORD_FILE"

docker compose -f "$ROOT/compose.grafana.yaml" up -d --force-recreate
echo "Grafana: http://localhost:3000/d/medallion-it-tickets"
echo "Usuário: admin; senha local: $PASSWORD_FILE"
echo "As credenciais AWS exportadas expiram. Repita este script para renová-las após nova autenticação."
