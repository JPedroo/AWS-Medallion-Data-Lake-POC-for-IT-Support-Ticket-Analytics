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

## Sessão 5 — 2026-11-08 — Execução do passo 8 na AWS

### Atividades realizadas

- Confirmado pelo AWS CLI que `medallion-poc` autentica como `user/medallion-poc-operator`, sem usar root.
- Executado `scripts/provision_aws.sh` com região `us-east-1`, limite mensal de US$ 5 e e-mail de alertas informado pelo usuário.
- Verificado que o orçamento já existia com limite correto; conferidos pelo CLI os alertas de 80% e 100% e seus destinatários.
- Criado e configurado o bucket da POC; conferidos bloqueio público, SSE-S3, versionamento, política TLS e tags.

### Arquivos criados ou alterados

`README.md`, `Plan.md`, `Documentation.md` e `docs/diario_do_projeto.md`. Nenhuma credencial, e-mail pessoal ou ID real da conta foi incluído nos arquivos versionados.

### Comandos e testes executados

- `.tools/bin/aws --version` → AWS CLI 2.39.6.
- `.tools/bin/aws sts get-caller-identity --profile medallion-poc` → usuário IAM esperado.
- `AWS_PROFILE=medallion-poc AWS_REGION=us-east-1 POC_BUCKET=<bucket-da-conta> POC_BUDGET_EMAIL=<email-informado> POC_BUDGET_USD=5 AWS_BIN="$PWD/.tools/bin/aws" bash scripts/provision_aws.sh` → concluído.
- `aws budgets describe-budget`, `describe-notifications-for-budget` e `describe-subscribers-for-notification` → limite e alertas confirmados.
- `aws s3api get-bucket-policy`, `get-bucket-tagging` e verificações do próprio script → configurações confirmadas.
- `aws budgets describe-budget --query 'Budget.CalculatedSpend.ActualSpend'` → USD 0,00 calculado na consulta.

### Problemas encontrados e soluções

- A consulta STS inicial não alcançou o endpoint pelo ambiente isolado; a execução com acesso de rede funcionou.
- O orçamento já existia. O script não o alterou; limite, limiares e destinatário foram conferidos com comandos de leitura.
- A consulta adicional `s3api get-bucket-ownership-controls` recebeu `AccessDenied` porque falta `s3:GetBucketOwnershipControls` na política da identidade. `put-bucket-ownership-controls` concluiu sem erro no script; o estado não foi confirmado por leitura independente.

### Decisões técnicas

- Manter a região `us-east-1` e o bucket privado único da arquitetura. Não ampliar a política IAM apenas para a consulta opcional de propriedade.
- Parar no passo 8 solicitado pelo usuário; a ingestão Bronze fica para o passo 9.

### Resultados, custos e evidências

- Orçamento mensal existente: US$ 5, alertas ACTUAL em 80% e 100% para o e-mail fornecido.
- Bucket criado na região escolhida, com bloqueio público total, SSE-S3, versionamento habilitado, tags e negação de tráfego sem TLS.
- Gasto calculado no orçamento: **US$ 0,00 no momento da consulta**. A AWS pode atualizar esse valor após atraso de faturamento; não equivale a uma fatura fechada.
- Evidências: saídas dos comandos AWS CLI desta sessão. CSV e manifesto ainda não estão na Bronze.

### Próxima atividade planejada

Executar o passo 9: enviar CSV original e manifesto com boto3, verificar `head-object`, baixar e conferir SHA-256; após a validação, remover `MedallionPocBootstrap` no console IAM.

## Sessão 6 — 2026-11-08 — Bronze publicada e validada

### Atividades realizadas

- Revalidado o CSV versionado do Kaggle e executada a ingestão boto3 na Bronze do bucket privado.
- Conferidos CSV e manifesto com AWS CLI, download e comparação byte a byte com a fonte local.
- Reexecutada a ingestão e comparados os IDs de versão S3 para validar que não houve sobrescrita.
- Tentada a retirada da política temporária pelo AWS CLI; a identidade da POC não tem permissão IAM para fazê-la.
- Ajustado o fechamento do corpo de resposta S3 no código de ingestão.

### Arquivos criados ou alterados

`src/ingest_bronze.py`, `README.md`, `Plan.md`, `Documentation.md`, `docs/diario_do_projeto.md`. Os downloads de verificação em `data/staging/` permanecem ignorados pelo Git.

### Comandos e testes executados

- `.venv/bin/python src/fetch_dataset.py` → CSV local de 6.873.542 bytes, hash fixado.
- `.venv/bin/python -m unittest discover -s tests -q` → 1 teste aprovado.
- `.venv/bin/python src/ingest_bronze.py --source data/raw/dataset-tickets-multi-lang3-4k.csv --dry-run` → 4.000 linhas e 17 campos.
- `aws sts get-caller-identity` e `aws s3api head-bucket` → usuário IAM esperado e bucket em `us-east-1`.
- `.venv/bin/python src/ingest_bronze.py --source ... --bucket ... --region us-east-1 --profile medallion-poc` → CSV e manifesto publicados; segunda execução reutilizou os objetos.
- `aws s3api head-object`, `get-object` e `list-objects-v2` → dois objetos Bronze encontrados; CSV com SHA-256 e checksum esperados, ambos com SSE-S3.
- Comparação Python local → CSV baixado idêntico em bytes ao original; manifesto com origem, licença, versão, tamanho, esquema, hash e contagem corretos.
- `aws budgets describe-budget` → US$ 0,00 de gasto calculado no momento da consulta.
- `aws iam list-attached-user-policies` e `detach-user-policy` → `AccessDenied` nas duas ações.
- Após o ajuste do `StreamingBody`, `.venv/bin/python -m unittest discover -s tests -q` → 1 teste aprovado; `git diff --check` → sem erro de formatação.
- `rg` nos arquivos versionados alterados → nenhum ID real da conta nem e-mail pessoal incluído.

### Problemas encontrados e soluções

- O ambiente isolado exigiu acesso de rede para chamadas AWS; o CLI e o boto3 funcionaram com a permissão de execução adequada.
- O usuário da POC não possui `iam:ListAttachedUserPolicies` nem `iam:DetachUserPolicy`. A política temporária permanece anexada até a remoção por uma identidade administradora no console IAM; os passos manuais foram enviados ao usuário.

### Decisões técnicas

- Preservar o CSV original na Bronze e limitar a conferência remota a leituras pelo AWS CLI; nenhuma transformação foi aplicada.
- Manter as políticas IAM de execução restritas. Não conceder ao operador permissões administrativas apenas para retirar a política temporária.
- Fechar explicitamente o `StreamingBody` do manifesto no código Python após a leitura.

### Resultados, custos e evidências

- Bronze contém CSV original (6.873.542 bytes) e manifesto (1.271 bytes) sob `version=14/sha256=9aae7120cf459fc27561febe29c7757c6d222bfebff50e8baa868991e57b87d1/`.
- CSV possui 4.000 linhas, 17 campos e SHA-256 `9aae7120cf459fc27561febe29c7757c6d222bfebff50e8baa868991e57b87d1`; checksum S3 em base64 `mq5xIM9Fn8J1Yf6+Kcd1fG0iK/6/9Q6LqoaJkeV7h9E=`.
- Os IDs de versão dos dois objetos permaneceram iguais após nova execução; a ingestão foi idempotente nesta verificação.
- Orçamento mostrou **US$ 0,00 calculado** após o upload. O valor ainda pode mudar com o atraso de faturamento da AWS.
- Evidências: saídas AWS CLI, cópias locais ignoradas pelo Git e validação de bytes/hash desta sessão.

### Próxima atividade planejada

Confirmar pelo console administrador que MFA está ativo no usuário `medallion-poc-operator` e remover somente `MedallionPocBootstrap`; então marcar a Sprint 1 como encerrada. Sprint 2 permanece apenas planejada.

## Sessão 7 — 2026-11-08 — Fechamento da Sprint 1

### Atividades realizadas

- Recebida confirmação do usuário de que retirou `MedallionPocBootstrap` e verificou MFA ativo no console IAM.
- Confirmado pelo AWS CLI que o perfil `medallion-poc` continua autenticado como `user/medallion-poc-operator` e consegue ler o CSV Bronze após a alteração.
- Marcada a Sprint 1 como concluída no plano e atualizados os documentos de entrada.

### Arquivos criados ou alterados

`README.md`, `Plan.md`, `Documentation.md`, `docs/aws_access.md` e `docs/diario_do_projeto.md`.

### Comandos e testes executados

- `aws sts get-caller-identity --profile medallion-poc` → usuário IAM esperado.
- `aws s3api head-object --profile medallion-poc --checksum-mode ENABLED` → CSV com 6.873.542 bytes, checksum SHA-256 esperado e mesmo ID de versão.
- `git status --short --branch` → repositório limpo no início da sessão.

### Problemas encontrados e soluções

- O perfil da POC não tem permissão IAM para inspecionar o MFA nem para remover políticas. O usuário executou e confirmou essas ações pelo console com a identidade administradora; a leitura S3 posterior mostrou que a política runtime continua operacional.

### Decisões técnicas

- Registrar a confirmação manual do usuário como evidência do estado IAM; não apresentar a leitura S3 como prova direta de MFA ou da lista de políticas anexadas.
- Encerrar a Sprint 1 sem iniciar a Sprint 2 nesta sessão.

### Resultados, custos e evidências

- Critérios da Sprint 1 atendidos: dataset e ambiente documentados, orçamento e bucket privados, CSV original e manifesto validados na Bronze, MFA e remoção de bootstrap confirmados.
- Último gasto calculado consultado no orçamento após o upload: **US$ 0,00**, sujeito a atraso de contabilização. Esta sessão não fez nova consulta de custo, pois a política temporária de Budgets foi removida.
- Evidências: confirmação do usuário no console, saída STS/S3 CLI desta sessão e validação de dados registrada na sessão 6.

### Próxima atividade planejada

Iniciar a Sprint 2 somente quando solicitada: regras de qualidade, Silver e Gold em Parquet/Snappy e catálogo/consultas Athena.
