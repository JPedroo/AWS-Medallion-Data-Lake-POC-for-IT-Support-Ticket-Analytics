# Diário do projeto

## Sessão 1 — 2026-11-08 — Sprint 1

### Atividades realizadas

- Lido o briefing de 11 páginas fornecido pelo usuário; delimitado o trabalho à Sprint 1.
- Validada a fonte Kaggle via SDK: título, autor, licença CC BY 4.0, versão 14 e arquivos disponíveis.
- Escolhido o arquivo original de 4.000 registros; validados esquema, codificação, delimitador, vazios e distribuições.
- Preparados ambiente virtual, AWS CLI v2, Java e PySpark; executado job Spark local mínimo.
- Implementados obtenção versionada, ingestão boto3 com hash/checksum e manifesto, além de scripts CLI de provisionamento.
- Organizada documentação, plano, Git ignore e dependências fixadas.

### Arquivos criados ou alterados

`.gitignore`, `.env.example`, `requirements.txt`, `README.md`, `Plan.md`, `Documentation.md`, `docs/dataset.md`, `docs/diario_do_projeto.md`, `src/fetch_dataset.py`, `src/ingest_bronze.py`, `scripts/check_spark.py`, `scripts/provision_aws.sh`, `scripts/create_ingest_policy.sh`, `tests/test_ingest_bronze.py`.

Arquivos locais **ignorados**: `.venv/`, `.tools/`, `data/raw/`.

### Comandos e testes executados

- `git status --short --branch`, `git remote -v`, `git ls-remote origin HEAD`: remoto configurado, sem commits anteriores.
- `python3 -m venv .venv` e instalação de `pypdf`, `boto3`, `kagglehub`, `pyspark==4.3.0`.
- Extração do PDF com `pypdf` e inspeção de metadados do dataset por `KaggleClient().datasets.dataset_api_client.get_dataset(...)`.
- `kagglehub.dataset_download(...)` e leitura CSV com `csv.DictReader`/`csv.reader`.
- `.venv/bin/python src/fetch_dataset.py --output-dir data/staging/fetch-validation` → download isolado do arquivo, 6.873.542 bytes e hash esperado; reexecução local reutiliza o arquivo validado.
- `.tools/bin/aws --version` → AWS CLI 2.39.6; `.tools/bin/aws configure list` → nenhum perfil/chave/região.
- `java -version` → OpenJDK 17.0.19; `SPARK_LOCAL_IP=127.0.0.1 .venv/bin/python scripts/check_spark.py` → Spark 4.3.0, contagem 5.
- `bash -n scripts/provision_aws.sh scripts/create_ingest_policy.sh` → sintaxe válida.
- `.venv/bin/python src/ingest_bronze.py --source data/raw/dataset-tickets-multi-lang3-4k.csv --dry-run` → manifesto com 4.000 linhas, 6.873.542 bytes, SHA-256 esperado.
- `.venv/bin/python -m unittest discover -s tests -v` → 1 teste aprovado; valida bytes preservados, manifesto e reexecução sem overwrite.

### Problemas encontrados e soluções

- O repositório estava vazio e `aws`/`gh` não estavam instalados. A AWS CLI v2 foi instalada localmente em `.tools/`; o Git remoto já existia.
- A rede do sandbox impediu acesso a PyPI/GitHub e a primeira tentativa do Spark falhou ao abrir loopback. Instalação/execução foram repetidas com a permissão de execução adequada e concluídas.
- O endpoint REST público legado do Kaggle respondeu 404. Os metadados foram consultados pelo SDK usado no download.
- O usuário informou que **não há perfil AWS configurado**. Por isso não foram criados orçamento, IAM, bucket ou objetos S3; os comandos e requisitos de autenticação estão no README.

### Decisões técnicas

- Fixar dataset versão 14 e hash do CSV de 4.000 linhas; manter o arquivo fora do Git e sem alteração na Bronze.
- Chave S3 baseada no SHA-256, `IfNoneMatch=*` e versionamento do bucket para apoiar imutabilidade e reexecução.
- Usar um bucket privado e uma região; orçamento antes do bucket; identidade não root e política mínima para `bronze/`.
- Não criar métricas de SLA ou séries temporais de negócio porque a origem não contém datas.

### Resultados, custos e evidências

- Fonte validada: 4.000 linhas, 17 colunas, UTF-8, vírgula, SHA-256 `9aae7120cf459fc27561febe29c7757c6d222bfebff50e8baa868991e57b87d1`.
- Ambientes locais verificados; ingestão verificada apenas em modo `--dry-run`.
- **Recursos AWS criados: nenhum. Custo AWS observado: indisponível**, pois não houve autenticação nem chamadas à conta. Não confundir essa ausência de medição com custo zero da conta.
- Evidências textuais em `docs/dataset.md`, saída do `--dry-run` e comandos de validação acima. Os arquivos brutos permanecem apenas localmente e ignorados pelo Git.

### Próxima atividade planejada

Configurar perfil AWS não root (SSO ou role existente), confirmar conta e e-mail de alerta, executar `scripts/provision_aws.sh`, associar política de ingestão se necessário, publicar Bronze e conferir CSV/manifesto com `head-object` e checksum. Depois registrar custo real e iniciar Sprint 2 conforme autorização.
