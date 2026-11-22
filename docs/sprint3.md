# Sprint 3 — Validação e entrega

## Escopo e estado

Dias 11 e 12: Grafana local com três visualizações sobre as tabelas Gold do Athena. Dia 13: reexecução do pipeline e conferência de contagens, duração, custos e rastreabilidade. A fonte tem um recorte fixo de 4.000 registros e não possui data de negócio; os gráficos são distribuições, sem linha temporal ou filtro de período.

Em 2026-11-22, o usuário IAM `medallion-poc-operator` foi autenticado, o Grafana passou no teste de conexão Athena e as três consultas dos gráficos retornaram 4.000 tickets cada. O pipeline foi reexecutado na AWS e o coletor de evidências aprovou todas as verificações. O gasto observado do orçamento permanece pendente: `budgets:DescribeBudget` retornou `AccessDeniedException` e o usuário confirmou não ter acesso ao orçamento no Console. As duas tentativas iniciais que ofereceram a sessão root foram recusadas; somente o perfil IAM foi usado na execução.

## Painel

O arquivo [tickets.json](../grafana/provisioning/dashboards/json/tickets.json) provisiona exatamente três gráficos. Todos usam a fonte `Athena POC`, banco `medallion_it_tickets_poc`, catálogo `AwsDataCatalog`, workgroup `primary` e região `us-east-1`.

| Gráfico | Consulta | Leitura |
| --- | --- | --- |
| Tickets por tipo e prioridade | `gold_tickets_by_type_priority` | Barras empilhadas por `low`, `medium` e `high` para cada tipo. |
| Tickets por fila | `gold_tickets_by_queue_language` | Total por fila, em ordem decrescente. |
| Tickets por idioma | `gold_tickets_by_queue_language` | Participação dos idiomas no conjunto válido. |

O painel não atualiza automaticamente. Cada abertura/atualização pode disparar consultas Athena e gerar arquivos em `athena-results/`. O Grafana usa o plugin oficial Athena 3.4.2 e imagem Grafana 12.1.0. O acesso HTTP é limitado a `127.0.0.1:3000`. Os arquivos de configuração ficam versionados; os segredos temporários e a senha local ficam em `data/staging/`, fora do Git. A [configuração do plugin](https://grafana.com/docs/plugins/grafana-athena-datasource/latest/configure/) e o [provisionamento](https://grafana.com/docs/grafana/latest/administration/provisioning/) seguem a documentação oficial do Grafana.

O plugin recebe credenciais temporárias exportadas do perfil `medallion-poc` no início. Como o processo do container recebe uma cópia dessas credenciais, reinicie com `bash scripts/run_grafana.sh` quando expirarem. O script recria somente o container e preserva o volume local do Grafana. A senha de `admin` é gerada na primeira execução e guardada em `data/staging/grafana-admin-password.txt` (modo `0600`).

## Passo a passo para concluir no Mac

1. Entre no Console AWS como **usuário IAM** `medallion-poc-operator` da conta `822218623538`, usando uma janela privada se o navegador estiver na sessão root. Conclua o MFA. Não escolha root na página do AWS CLI. No Terminal, na raiz do repositório, execute:

   ```bash
   .tools/bin/aws login --profile medallion-poc
   .tools/bin/aws --profile medallion-poc --region us-east-1 sts get-caller-identity
   ```

   Confira `Account = 822218623538` e `Arn` terminado em `user/medallion-poc-operator`. Se a CLI perguntar se deve substituir a sessão do perfil pela root, responda `n` e entre novamente como o usuário IAM.

2. Abra o Docker Desktop e aguarde até `docker info` responder. Inicie o Grafana:

   ```bash
   bash scripts/run_grafana.sh
   ```

   O script confirma a conta via STS, deriva o nome do bucket, exporta credenciais de curta duração e inicia o Grafana. Caso falte o plugin ou o container falhe, leia `docker compose -f compose.grafana.yaml logs --tail=100 grafana`.

3. Abra <http://localhost:3000/d/medallion-it-tickets>. Entre com usuário `admin` e a senha exibida por `cat data/staging/grafana-admin-password.txt`. Em **Connections → Data sources → Athena POC**, use **Save & test**. Confirme as três visualizações com dados: tipo/prioridade, fila e idioma. Execute `python3 src/validate_grafana.py` para consultar os três gráficos pela API e gravar `data/processed/sprint3_grafana_validation.json`. Cada gráfico deve reconciliar em 4.000 tickets; não há série temporal. Se aparecer `AccessDenied`, confira as permissões Athena, Glue e S3 em `config/iam_poc_runtime_policy.template.json`, sem copiar credenciais para o chat. Se aparecer token expirado, execute novamente `bash scripts/run_grafana.sh`.

4. Execute a validação de ponta a ponta:

   ```bash
   bash scripts/run_sprint3.sh
   ```

   O script baixa a Bronze do S3, reconstrói Silver/Gold, confirma a publicação sem sobrescrever objetos de mesma proveniência, executa DDL e seis consultas Athena e grava `data/processed/sprint3_evidence.json`. Ele interrompe a execução se as contagens ou os metadados divergirem. O PySpark pode levar alguns minutos. Use `SPARK_LOCAL_IP=127.0.0.1` se executar os scripts Python individualmente.

5. Abra o JSON de evidência e confira: `source_rows = 4000`, `silver_rows = 4000`, `duplicate_rows = 0`, `valid_rows = 4000`, `rejected_rows = 0`, as duas somas Gold = 4.000 e as duas divergências por grupo = 0. Os campos `pipeline_processing_seconds`, `athena_executions[*].total_execution_ms`, `athena_data_scanned_bytes_total`, `objects[*].version_id`, `bronze_manifest_run_id`, SHA-256 e `glue_tables` documentam tempo e rastreabilidade. O arquivo também registra a identidade IAM, região e hora UTC da coleta. Ele é ignorado pelo Git porque contém IDs da conta e da execução.

6. Para o **custo observado**, veja `cost` no JSON. O script tenta ler o orçamento `medallion-it-tickets-poc`; o perfil runtime provavelmente receberá `AccessDenied` porque a política temporária de bootstrap foi retirada na Sprint 1. Nesse caso, entre no Console com uma identidade com acesso a Billing, abra **Billing and Cost Management → Budgets → medallion-it-tickets-poc** e anote **Actual spend**, moeda e horário da consulta no relatório final. O orçamento é mensal da conta e não mede isoladamente esta POC. O total de `DataScannedInBytes` do Athena é volume técnico, não cobrança. A AWS atualiza os dados do Cost Explorer ao menos diariamente e pode contabilizar uso recente depois; não interprete ausência de linha como custo zero. [Documentação AWS sobre atualização de custos](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html).

   Se a página **Budgets** também mostrar falta de acesso, peça a uma identidade administradora autorizada da conta para consultar esse orçamento ou conceder leitura `budgets:DescribeBudget` ao usuário IAM da POC. Não reanexe a política temporária `MedallionPocBootstrap` inteira apenas para ler o orçamento. Depois registre o valor, moeda e horário em `docs/relatorio_final.md`, deixando claro que é o gasto mensal da conta e que o dado pode ser atualizado pela AWS.

7. Para os IDs e bytes das consultas do painel, execute `.venv/bin/python src/collect_grafana_query_stats.py --profile medallion-poc --region us-east-1`. O resultado fica em `data/processed/sprint3_grafana_athena_stats.json`. Reabra o painel, confirme que não há erro e, se precisar de evidência visual, capture uma imagem local dos três gráficos. Confira **Athena → Recent queries** pelos IDs nos JSON de evidência, **S3** pelos objetos listados e **Glue → Tables** pelos três caminhos. Guarde a captura fora do Git, por exemplo em `data/staging/sprint3-dashboard.png`.

## Interpretação de custo

O arquivo de evidência guarda o gasto calculado do orçamento apenas se `budgets:DescribeBudget` estiver permitido. Isso é uma leitura de gasto mensal da conta, sujeito a atraso, sem atribuição exclusiva à POC. O preço efetivo do Athena depende da modalidade de cobrança, do mínimo por consulta e da região; não converter automaticamente bytes lidos em valor faturado. Consulte a [página oficial de preços do Athena](https://aws.amazon.com/athena/pricing/) e o painel de Billing para o valor observado. O Grafana local não cria um workspace Amazon Managed Grafana; consultas e arquivos Athena/S3 podem gerar encargos.

## Evidências a entregar

- Código e configuração: `compose.grafana.yaml`, `grafana/provisioning/`, `scripts/run_grafana.sh`, `scripts/run_sprint3.sh`, `src/collect_sprint3_evidence.py`.
- Resultado local da execução: `data/processed/sprint3_build.json`, `sprint3_athena.json`, `sprint3_evidence.json`.
- Resultado do painel: `data/processed/sprint3_grafana_validation.json` e `sprint3_grafana_athena_stats.json`.
- Captura de tela opcional: `data/staging/sprint3-dashboard.png`, após visualização real dos dados.
- Relatório: [relatorio_final.md](relatorio_final.md), com o estado efetivamente verificado e a leitura de custo que for possível.
- Registro versionado: [sprint3_evidencias.md](sprint3_evidencias.md), com contagens, versões S3 e IDs das consultas.

## Evidência executada em 2026-11-22

- A reexecução AWS levou **19,37 s** no processamento/publicação; Bronze e Silver têm 4.000 linhas, 0 duplicatas, 4.000 válidas e 0 rejeitadas. As duas Gold somam 4.000 e não há divergências por grupo no Athena.
- Os seis checks Athena leram **7.478 bytes**; os quatro DDLs leram zero. Os IDs, as durações individuais e os caminhos S3/Glue estão em `data/processed/sprint3_evidence.json`. Os IDs de versão dos seis objetos conferidos foram preservados na reexecução.
- O Grafana retornou 4 linhas no gráfico tipo/prioridade, 10 filas e 5 idiomas. Cada gráfico soma **4.000** tickets; a API da fonte respondeu `Data source is working`. Foram feitas duas rodadas de três consultas para verificar os gráficos; os seis IDs Athena correspondentes leram **2.352 bytes**. O total técnico das consultas do pipeline e dessas duas rodadas foi **9.830 bytes**. Isso não é custo faturado.
- O orçamento mensal da conta não pôde ser lido com o perfil runtime (`AccessDeniedException`). O usuário confirmou que não tem acesso ao orçamento no Console; o valor atual da cobrança **não foi medido**.
