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
- `git diff --cached --check`, `git commit -m 'Implement Sprint 1 preparation and Bronze ingestion'` e `git push -u origin main` → commit `f260189` publicado na branch `main`.

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
- Código e documentação publicados em `https://github.com/JPedroo/AWS-Medallion-Data-Lake-POC-for-IT-Support-Ticket-Analytics` (branch `main`, commit `f260189`).

### Próxima atividade planejada

Configurar perfil AWS não root (SSO ou role existente), confirmar conta e e-mail de alerta, executar `scripts/provision_aws.sh`, associar política de ingestão se necessário, publicar Bronze e conferir CSV/manifesto com `head-object` e checksum. Depois registrar custo real e iniciar Sprint 2 conforme autorização.

## Sessão 2 — 2026-11-08 — Identidade AWS para conta pessoal

### Atividades realizadas

- Reavaliado o acesso após o usuário informar que a conta é pessoal.
- Validada a documentação atual da AWS sobre `aws login`, boto3, IAM Identity Center, Budgets e políticas para S3/Athena/Glue.
- Definido o caminho de um usuário IAM `medallion-poc-operator` com MFA e credenciais temporárias via login do console. Uma role manual não é necessária nesta conta pessoal; se a conta já usar AWS Organizations, o permission set do Identity Center cria a role automaticamente.
- Preparado passo a passo de console e modelos de política com permissões separadas para bootstrap e runtime.

### Arquivos criados ou alterados

`docs/aws_access.md`, `config/iam_poc_bootstrap_policy.template.json`, `config/iam_poc_runtime_policy.template.json`, `README.md`, `Documentation.md`, `Plan.md`, `docs/diario_do_projeto.md`.

### Comandos e testes executados

- `git status --short --branch` para confirmar o repositório limpo no início da sessão.
- `rg` nos scripts AWS para alinhar as ações IAM com chamadas reais.
- Consulta às referências oficiais AWS de IAM, AWS CLI, Boto3, Budgets, S3, Athena e Glue.
- `.venv/bin/python -c ... json.loads(...)` → os dois modelos de política são JSON válido; `git diff --check` → sem erro de formatação.
- `.venv/bin/python -m pip install 'boto3[crt]==1.43.126'` → AWS CRT 0.38.0 instalado, exigido pelo boto3 para `aws login`.
- `.tools/bin/aws login help` → subcomando disponível; `.venv/bin/python -m unittest discover -s tests -q` → 1 teste aprovado.
- `git diff --cached --check`, `git commit -m 'Document personal AWS account access for POC'` e `git push origin main` → guia publicado no GitHub no commit `17acfdb`.

### Problemas encontrados e soluções

- A recomendação genérica anterior de SSO depende de uma instância organizacional do IAM Identity Center. Habilitar AWS Organizations em uma conta pessoal Free Tier pode alterar o plano e encerrar créditos; o guia agora prioriza `aws login` com IAM user e apresenta SSO apenas se já estiver disponível.
- A autenticação AWS ainda depende de intervenção manual no console; nenhum usuário ou recurso foi criado por esta sessão.
- O requisito adicional `boto3[crt]` para usar `aws login` foi identificado na documentação oficial e fixado em `requirements.txt`.

### Decisões técnicas

- Não criar role IAM manual para uma POC local em conta pessoal; usar perfil `medallion-poc` com credenciais temporárias do AWS CLI.
- Separar permissões de bootstrap das permissões de execução; retirar bootstrap após a Sprint 1.
- Fixar o banco Athena/Glue planejado em `medallion_it_tickets_poc` e o workgroup em `primary` para escopo de IAM. Validar os detalhes de Grafana quando a Sprint 3 começar.

### Resultados, custos e evidências

- Guia e modelos de políticas criados; nenhum acesso AWS foi usado e nenhum custo foi medido.
- Evidências: documentação oficial citada em `docs/aws_access.md` e modelos JSON versionados.

### Próxima atividade planejada

Criar o usuário/políticas pelo console, executar `aws login --profile medallion-poc`, confirmar ARN não root, provisionar orçamento/bucket pelo CLI, ingerir e validar Bronze; remover a política temporária de bootstrap após o checkpoint C3.

## Sessão 3 — 2026-11-08 — Esclarecimento do acesso AWS

### Atividades realizadas

- Reescrito o guia de acesso da conta pessoal após o usuário informar que não conhecia os passos a partir da verificação da identidade administradora.
- Organizado um roteiro único com glossário, nove passos, cliques no console IAM, comandos do Terminal para preparar/copiar políticas, MFA, login do CLI, provisionamento e ingestão.
- Conferidas novamente as instruções oficiais AWS para login do CLI, criação de política/usuário IAM, MFA e entrada pelo link do usuário IAM.

### Arquivos criados ou alterados

`docs/aws_access.md`, `README.md`, `Plan.md`, `Documentation.md`, `docs/diario_do_projeto.md`.

### Comandos e testes executados

- `sed -n` e `rg` para revisar o guia, os scripts, as políticas e os documentos de entrada.
- `git status --short --branch` confirmou a branch `main` limpa no começo da sessão.
- `git diff --check` confirmou ausência de problemas de formatação após a reescrita.

### Problemas encontrados e soluções

- O guia anterior pressupunha familiaridade com root, usuário IAM, política JSON e perfil CLI. Foram adicionadas definições, instruções de copiar e colar no macOS e resultados esperados por etapa.
- Ainda não há perfil AWS autenticado nesta máquina; a intervenção manual no console permanece necessária.

### Decisões técnicas

- Manter o uso do console apenas para a criação da primeira identidade e das políticas, pois não há perfil CLI inicial. Provisionar orçamento e bucket com AWS CLI após o login IAM.
- Preservar as políticas de escopo específico e a remoção da política temporária de bootstrap após a Sprint 1.

### Resultados, custos e evidências

- Guia revisado e alinhado aos scripts existentes. Nenhuma chamada à conta AWS foi feita nesta sessão; orçamento, bucket e Bronze continuam pendentes. Nenhum custo AWS foi medido.
- Evidências: `docs/aws_access.md`, políticas em `config/` e documentação oficial AWS citada no guia.

### Próxima atividade planejada

Usuário seguirá os passos 1 a 7 para criar e autenticar `medallion-poc-operator`. Com o perfil funcional, executar provisionamento CLI, ingestão Bronze e validação S3; registrar evidências e remover `MedallionPocBootstrap`.

## Sessão 4 — 2026-11-08 — Validação dos modelos IAM

### Atividades realizadas

- Esclarecido que `123456789012` é o valor de busca do `sed` e somente `SEU_ID_DE_12_DIGITOS` deve ser editado no comando.
- Inspecionados os dois JSON gerados localmente, sem exibir o ID real da conta.
- Substituída a instrução de executar `grep` isoladamente por uma checagem que imprime `OK` quando os exemplos já foram removidos.

### Arquivos criados ou alterados

`docs/aws_access.md` e `docs/diario_do_projeto.md`. `README.md`, `Plan.md` e `Documentation.md` foram revisados e permanecem coerentes com o fluxo.

### Comandos e testes executados

- Script Python local verificou que os arquivos `data/staging/iam_poc_runtime_policy.json` e `data/staging/iam_poc_bootstrap_policy.json` existem, não contêm `123456789012` nem `SEU_ID_DE_12_DIGITOS` e usam um único ID de 12 dígitos.
- `git status --short --branch` confirmou branch `main` limpa antes desta alteração.
- Bloco `if grep ...; then ...; else ...; fi` → `OK: os números de exemplo foram substituídos`.
- `python3 -m json.tool` em ambos os arquivos gerados → JSON válido; `git diff --check` → sem problemas de formatação.

### Problemas encontrados e soluções

- `grep` retorna código 1 e nenhuma linha quando não encontra o texto, comportamento que foi interpretado como falha. O guia agora explica que esse era o resultado esperado e imprime uma confirmação explícita.

### Decisões técnicas

- Manter os modelos com um ID de exemplo versionado e gerar cópias locais em `data/staging/`, ignorado pelo Git. O valor `123456789012` deve continuar nos comandos de substituição, pois representa o texto a localizar.

### Resultados, custos e evidências

- Os dois arquivos locais já passaram pela substituição de ID. A inspeção não realizou chamadas AWS. Nenhum recurso cloud foi criado e nenhum custo AWS foi medido nesta sessão.

### Próxima atividade planejada

Prosseguir no passo 3 do guia para criar `MedallionPocRuntime` no console IAM, depois a política temporária e o usuário.
