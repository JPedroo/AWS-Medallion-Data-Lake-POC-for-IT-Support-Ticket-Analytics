# Sprint 2 — Silver, Gold e Athena

## Fluxo e regras

O script `src/build_sprint2.py` baixa da Bronze o CSV da versão 14 identificado pelo SHA-256 fixado, valida o cabeçalho, as 4.000 linhas e os bytes, e usa PySpark local para transformar os dados. Também aceita `--source` para teste sem AWS. A Bronze não é alterada.

| Etapa | Regra |
| --- | --- |
| Limpeza | `trim` nas bordas de todos os campos; nulos viram string vazia. O texto livre interno permanece intacto. |
| Padronização | `type`, `priority` e `language` em minúsculas; dimensões vazias viram `unknown`. `subject`, `body` e `answer` vazios continuam vazios. |
| Identidade | `ticket_id = SHA-256(JSON struct dos 17 campos normalizados na ordem de origem)`. Não é um ID da fonte. |
| Deduplicação | Uma linha por `ticket_id`; IDs iguais equivalem a conteúdo normalizado igual. Ordenação por conteúdo normalizado define o desempate. |
| Qualidade | `rejected` se `subject` **e** `body` estiverem vazios; caso contrário `valid`. Campos vazios isolados são alertas. |
| Gold | Apenas linhas `valid`; contagem por `type`/`priority` e por `queue`/`language`. Nenhuma data de negócio ou SLA é inferida. |

A reconciliação exige `source_rows = silver_rows + duplicate_rows` e `silver_rows = valid_rows + rejected_rows`. Cada Gold deve somar `valid_rows`. O arquivo `quality.json` registra as contagens, percentuais de assunto/descrição vazios, SHA-256 de origem, versão do pipeline e tamanho dos Parquet. A duração aparece na saída JSON da execução, sem entrar no arquivo de qualidade determinístico. A publicação compara proveniência e checksum para reaproveitar objetos existentes; os bytes Parquet podem variar entre execuções PySpark mesmo com o mesmo conteúdo lógico, por isso os Parquet existentes da mesma fonte e versão do pipeline não são sobrescritos.

## Artefatos

| Tabela/arquivo | Local no S3 | Formato |
| --- | --- | --- |
| Silver `silver_tickets` | `silver/tickets/part-00000.parquet` | Parquet/Snappy |
| Gold `gold_tickets_by_type_priority` | `gold/tickets_by_type_priority/part-00000.parquet` | Parquet/Snappy |
| Gold `gold_tickets_by_queue_language` | `gold/tickets_by_queue_language/part-00000.parquet` | Parquet/Snappy |
| Qualidade | `silver/quality/metrics.json` | JSON, fora do prefixo da tabela |
| Resultados Athena | `athena-results/` | Arquivos de resultado gerados pelo Athena |

Os DDLs em `sql/01_database.sql` a `sql/04_gold_queue_language.sql` registram o banco `medallion_it_tickets_poc` e três tabelas externas no Glue Data Catalog por meio do Athena, sem Crawler. As consultas em `sql/validation.sql` permitem exploração manual. O script `src/catalog_athena.py` executa seis verificações: válidos, rejeitados, total das duas Gold e divergências por grupo das duas Gold. Os resultados, IDs de execução e bytes lidos aparecem na saída e em `data/processed/athena_validation.json` (ignorado pelo Git).

## Reproduzir

Na raiz do repositório, com as dependências de `requirements.txt` instaladas:

```bash
SPARK_LOCAL_IP=127.0.0.1 .venv/bin/python src/build_sprint2.py \
  --source data/raw/dataset-tickets-multi-lang3-4k.csv
cat data/processed/quality.json
```

Para usar a Bronze do S3 e publicar as três tabelas, autentique o perfil e execute:

```bash
export PATH="$PWD/.tools/bin:$PATH"
export AWS_PROFILE=medallion-poc AWS_REGION=us-east-1
aws login --profile "$AWS_PROFILE"
export POC_BUCKET="medallion-it-tickets-poc-$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Account --output text)-$AWS_REGION"
SPARK_LOCAL_IP=127.0.0.1 .venv/bin/python src/build_sprint2.py \
  --bucket "$POC_BUCKET" --region "$AWS_REGION" --profile "$AWS_PROFILE" --publish
.venv/bin/python src/catalog_athena.py \
  --bucket "$POC_BUCKET" --region "$AWS_REGION" --profile "$AWS_PROFILE"
```

O perfil deve ser o usuário não root da Sprint 1, com `MedallionPocRuntime` e `SignInLocalDevelopmentAccess`. Se o login tiver expirado, `aws login` renova a sessão sem criar chave de acesso duradoura. A política `MedallionPocBootstrap` não é necessária. O script confirma a conta com STS, exige o nome do bucket desta POC para essa conta/região e passa `ExpectedBucketOwner` nas operações S3. O perfil precisa de S3 `GetObject`/`PutObject` nos prefixos de dados e resultados, Glue Create/Get para banco/tabelas e Athena Start/Get Query no workgroup `primary`.

## Conferir pelo console, se necessário

1. Entre no [console AWS](https://console.aws.amazon.com/) como `medallion-poc-operator` da conta `822218623538`, com a senha **desse usuário IAM** e MFA; selecione a região **US East (N. Virginia) / us-east-1**.
2. Abra **S3 → Buckets → medallion-it-tickets-poc-822218623538-us-east-1**. Verifique os três arquivos `part-00000.parquet` nos prefixos acima e `silver/quality/metrics.json`. Em cada objeto, confira **Properties → Server-side encryption: Amazon S3 managed keys (SSE-S3)**. Não altere a Bronze.
3. Abra **Athena → Query editor**, selecione **Data source: AwsDataCatalog**, **Database: medallion_it_tickets_poc** e **Workgroup: primary**. Em **Settings → Manage**, defina `s3://medallion-it-tickets-poc-822218623538-us-east-1/athena-results/` como local de resultados se o editor solicitar; salve.
4. Confira as tabelas `silver_tickets`, `gold_tickets_by_type_priority` e `gold_tickets_by_queue_language`. Execute as consultas de `sql/validation.sql`, uma por vez. Esperado nesta fonte: 4.000 `valid`, 0 `rejected` e soma 4.000 em cada Gold. O script automatizado também compara os grupos.
5. Se o script falhar com `AccessDenied`, copie apenas o nome da ação negada e o serviço, sem senha, token ou código MFA. Se falhar com `No output location provided`, confirme o caminho do passo 3. O script passa `OutputLocation` explicitamente, portanto essa falha indicaria configuração conflitante do workgroup ou execução manual sem local definido.

O Athena grava arquivos em S3 e cobra pela consulta conforme a modalidade da conta; o bucket versionado também retém versões de objetos. Verifique o orçamento existente e os bytes lidos exibidos pelo script antes de repetir consultas em volume. S3 permanece privado, com bloqueio público, SSE-S3 e exigência de TLS; o perfil IAM deve manter somente as permissões necessárias. Para observabilidade adicional, considerar CloudTrail data events do S3, logs de acesso e métricas CloudWatch, avaliando o custo antes de habilitá-los nesta POC.

## Evidência de 2026-11-15

O PySpark leu a Bronze do S3 com 4.000 linhas e gerou 4.000 linhas Silver, 0 duplicatas, 4.000 válidas e 0 rejeitadas. Foram encontrados 468 assuntos vazios e uma descrição vazia após normalização. As duas agregações somaram 4.000. Os arquivos Parquet/Snappy foram gerados em `data/processed/` e publicados no bucket da mesma conta. O S3 confirmou 3.866.831 bytes Silver, 1.170 bytes Gold tipo/prioridade, 1.605 bytes Gold fila/idioma e 533 bytes de métricas, todos com SSE-S3. A reexecução preservou os quatro IDs de versão.

O Athena criou o banco e as três tabelas externas. As seis validações retornaram os valores esperados, inclusive zero divergências por grupo; IDs e bytes lidos estão em `data/processed/athena_validation.json`. A soma de `DataScannedInBytes` foi 7.478 bytes, sem inferir daí o valor faturado. O perfil runtime não possui permissão para consultar Budgets após a retirada da política temporária; não há nova medição de custo nesta sessão.
