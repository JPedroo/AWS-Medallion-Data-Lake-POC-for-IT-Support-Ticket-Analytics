# POC: Data Lake Medalhão na AWS para tickets de suporte

Sprint 1 da POC acadêmica de três semanas descrita no briefing fornecido pelo usuário. O fluxo preserva um CSV versionado do Kaggle na camada Bronze de um bucket privado, acompanhado por manifesto auditável. Silver/Gold, Athena e Grafana estão planejados para as Sprints 2 e 3.

**Estado em 2026-11-08:** dataset e ambiente local validados; código Bronze pronto. A conta AWS ainda não tem perfil CLI configurado nesta máquina, então orçamento, bucket, IAM e upload permanecem pendentes. Não há custo AWS observado nesta sessão.

## Fonte e atribuição

“Customer IT Support - Ticket Dataset”, de Tobias Bueck, [Kaggle](https://www.kaggle.com/datasets/tobiasbueck/multilingual-customer-support-tickets), licença [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Usamos o arquivo original `dataset-tickets-multi-lang3-4k.csv` da versão 14 (4.000 registros). Consulte [docs/dataset.md](docs/dataset.md) para esquema, perfil e indicadores. O CSV contém texto livre e fica fora do Git.

## Pré-requisitos locais

- macOS com Python 3.11 ou superior e Java 17 ou superior. Validados nesta máquina: Python 3.14.6, Java 17.0.19, PySpark 4.3.0.
- Git e acesso ao repositório remoto.
- Para executar na AWS: perfil CLI de uma identidade não root com permissões de Budgets e S3. Para criar política IAM, permissões IAM adicionais.

Na raiz do repositório:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
java -version
SPARK_LOCAL_IP=127.0.0.1 .venv/bin/python scripts/check_spark.py
```

O instalador oficial da AWS CLI v2 foi usado nesta máquina para instalar `aws` em `.tools/bin/`. Em outro Mac, siga o [guia oficial da AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) e verifique `aws --version`. Para esta cópia do projeto:

```bash
export PATH="$PWD/.tools/bin:$PATH"
aws --version
```

## Baixar e validar a fonte

```bash
.venv/bin/python src/fetch_dataset.py
.venv/bin/python src/ingest_bronze.py \
  --source data/raw/dataset-tickets-multi-lang3-4k.csv --dry-run
```

O script fixa a versão 14 e verifica SHA-256 antes da ingestão. A opção Pandas do `kagglehub` mencionada no pedido carrega o conteúdo em memória, mas a Bronze exige preservar o **arquivo original**; por isso usamos o download direto do arquivo versionado. O cliente Kaggle ainda usa cache/download local nos dois modos.

## Intervenção manual para acesso AWS

Para a **conta pessoal** informada pelo usuário, siga os **passos 1 a 9**, em ordem, em [docs/aws_access.md](docs/aws_access.md). O guia mostra os cliques no console, como copiar as políticas do Mac, criar o usuário IAM `medallion-poc-operator`, ativar MFA e autenticar o CLI com `aws login`. A AWS CLI v2 e o boto3 desta POC usam credenciais temporárias nesse fluxo, sem criar access keys permanentes. A política temporária de bootstrap deve ser removida depois da Sprint 1.

Após criar o usuário no console, execute na raiz do projeto:

```bash
export PATH="$PWD/.tools/bin:$PATH"
aws login --profile medallion-poc
aws sts get-caller-identity --profile medallion-poc
```

Confira que o ARN retornado termina em `user/medallion-poc-operator`, nunca em `:root`. Se a conta já tiver IAM Identity Center de uma AWS Organization, use o fluxo SSO do guia em vez de criar outro usuário IAM.

Depois da autenticação, escolha um e-mail que receberá alertas e execute:

```bash
export AWS_PROFILE=medallion-poc
export AWS_REGION=us-east-1
export POC_BUCKET="medallion-it-tickets-poc-$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Account --output text)-$AWS_REGION"
export POC_BUDGET_EMAIL='SEU_EMAIL_DE_ALERTA'
export POC_BUDGET_USD=5
bash scripts/provision_aws.sh
```

Troque `SEU_EMAIL_DE_ALERTA` pelo endereço real. O script cria **primeiro** um orçamento mensal em USD com avisos em 80% e 100%, depois o bucket privado, criptografia SSE-S3, bloqueio público, versionamento e exigência de TLS. O orçamento avisa; ele não impede gastos. `us-east-1` é a região padrão desta POC e deve ser mantida em todas as etapas; outro valor também funciona se escolhido antes do provisionamento. Verifique o limite e o destinatário de um orçamento já existente, pois o script não os altera.

Se futuramente houver uma identidade **separada** somente para ingestão Bronze, o administrador pode associar a política mínima a um usuário IAM existente:

```bash
export POC_INGEST_USER='NOME_DO_USUARIO_IAM_EXISTENTE'
bash scripts/create_ingest_policy.sh
```

Esta etapa é opcional quando a ingestão roda com uma role temporária já limitada a `bronze/`. O script não cria usuário nem chave. O perfil usado em `src/ingest_bronze.py` deve ser o da identidade de ingestão com `s3:GetObject` e `s3:PutObject` em `bronze/`.

## Publicar e conferir a Bronze

```bash
.venv/bin/python src/ingest_bronze.py \
  --source data/raw/dataset-tickets-multi-lang3-4k.csv \
  --bucket "$POC_BUCKET" --region "$AWS_REGION" --profile "$AWS_PROFILE"

SHA256=9aae7120cf459fc27561febe29c7757c6d222bfebff50e8baa868991e57b87d1
PREFIX="bronze/dataset=multilingual-customer-support-tickets/version=14/sha256=$SHA256"
aws s3api head-object --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --bucket "$POC_BUCKET" --key "$PREFIX/dataset-tickets-multi-lang3-4k.csv" --checksum-mode ENABLED
aws s3api head-object --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --bucket "$POC_BUCKET" --key "$PREFIX/manifest.json"
mkdir -p data/staging
aws s3api get-object --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --bucket "$POC_BUCKET" --key "$PREFIX/manifest.json" data/staging/manifest.json
aws s3api get-object --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --bucket "$POC_BUCKET" --key "$PREFIX/dataset-tickets-multi-lang3-4k.csv" data/staging/bronze.csv
shasum -a 256 data/staging/bronze.csv
```

No retorno do primeiro `head-object`, confira `ContentLength=6873542`, `Metadata.sha256` igual ao hash acima e `ChecksumSHA256` correspondente. O manifesto deve declarar `source_rows=4000`. O resultado do `shasum` deve coincidir com o hash acima.

## Repositório e continuidade

`data/`, `.venv/`, `.tools/` e `.env` estão ignorados no Git. O histórico de trabalho está em [docs/diario_do_projeto.md](docs/diario_do_projeto.md); o plano em [Plan.md](Plan.md); as decisões técnicas em [Documentation.md](Documentation.md). Ao fim de **cada sessão**, atualizar o diário com atividades, arquivos, comandos/testes, problemas e soluções, decisões, resultados/custos/evidências e próxima atividade, além de revisar os três documentos principais.

Teste local da lógica de imutabilidade da Bronze: `.venv/bin/python -m unittest discover -s tests -v`.
