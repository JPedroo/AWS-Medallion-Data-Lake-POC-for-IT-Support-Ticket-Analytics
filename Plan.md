# Plano da POC em três sprints

Fonte de escopo: briefing local `briefing_projeto_data_lake_medalhao_aws_poc_3_semanas.pdf`, fornecido pelo usuário, e detalhamento da Sprint 2 informado na conversa.

| Sprint | Período | Entrega | Estado em 2026-11-22 |
| --- | --- | --- | --- |
| 1 — Preparação e Bronze | Dias 1–5 | Dataset validado, ambiente, orçamento e bucket privados, CSV original e manifesto no S3 | **Concluída**: entrega técnica validada; MFA e retirada da política temporária confirmados pelo usuário no console |
| 2 — Processamento e consulta | Dias 6–10 | Qualidade, Parquet/Snappy, duas tabelas Gold, DDL/consultas Athena | **Concluída**: Silver/Gold publicadas; banco, tabelas e consultas Athena validados |
| 3 — Validação e entrega | Dias 11–13 | Grafana local com três visualizações; reexecução, contagens, duração, custo e rastreabilidade | Entrega técnica validada; leitura atual do orçamento pendente por falta de acesso |

## Sprint 1 — critérios de aceite

- [x] Licença, versão, arquivo, esquema, codificação, delimitador, amostra e indicadores documentados.
- [x] Git local e remoto `origin` configurados; dependências fixadas; dados e segredos ignorados.
- [x] Python, Java, AWS CLI e job PySpark mínimo validados localmente.
- [x] Usuário IAM da conta pessoal criado; perfil `aws login` não root autenticado e permissões de provisionamento testadas. MFA ativo confirmado pelo usuário no console. Guia em `docs/aws_access.md`; políticas em `config/`.
- [x] Orçamento mensal de US$ 5 existente, com alertas em 80% e 100% e destinatário conferidos antes da ingestão.
- [x] Bucket privado em `us-east-1`, bloqueio público, criptografia SSE-S3, versionamento e política TLS verificados. A configuração `BucketOwnerEnforced` foi aplicada; a leitura independente recebeu `AccessDenied` por falta de `s3:GetBucketOwnershipControls`.
- [x] Política runtime específica da POC associada ao usuário IAM usado na ingestão; identidade separada de ingestão não foi necessária.
- [x] Ingestão boto3 e manifesto com SHA-256 implementados e validados em modo local.
- [x] CSV original e manifesto no S3; `head-object`, checksum, bytes baixados, conteúdo do manifesto e reexecução sem overwrite conferidos.
- [x] MFA confirmado e `MedallionPocBootstrap` retirado pelo usuário no console administrador; o perfil `medallion-poc` continuou com leitura da Bronze após a mudança. A retirada não pôde ser feita pelo perfil da POC por falta de `iam:DetachUserPolicy`.
- [x] Código, documentos e diário publicados no GitHub remoto na branch `main`.

## Decisões para a Sprint 2

- Usar PySpark local e boto3 para staging entre S3 e disco local.
- Criar `ticket_id` estável a partir de conteúdo, porque a origem não fornece ID.
- Definir `quality_status` e reconciliar registros antes de agregar.
- Gravar Silver e Gold em Parquet/Snappy; criar o catálogo com DDL versionado, sem Crawler.
- Evitar qualquer métrica temporal de negócio ou SLA por falta de datas na origem.

## Sprint 2 — critérios de aceite

- [x] Transformação Silver implementada em PySpark: limpeza, padronização, ID estável, deduplicação e `quality_status`.
- [x] Reconciliação e métricas de qualidade locais: 4.000 entradas, 4.000 mantidas, 0 duplicatas, 4.000 válidas e 0 rejeitadas.
- [x] Silver e duas Gold gravadas localmente em Parquet/Snappy; agregações locais reconciliadas.
- [x] Publicação S3 e DDL/consultas Athena implementadas e versionadas no repositório.
- [x] Publicação de Silver/Gold no bucket da POC e verificação dos quatro objetos S3 com SSE-S3; reexecução preservou os IDs de versão.
- [x] Banco e três tabelas externas no Athena criados; seis consultas de validação executadas e confrontadas com as métricas locais. Os prefixos de cada tabela foram confirmados no Glue.

## Sprint 3 — critérios de aceite

- [x] Grafana local configurado como código com plugin Athena, fonte e painel de três visualizações.
- [x] Fonte Grafana validada e três visualizações consultadas com dados reais das duas Gold; cada uma soma 4.000 tickets.
- [x] Script de reexecução e coleta de evidências implementado.
- [x] Pipeline reexecutado na AWS com Bronze, Silver, Gold, Glue e Athena reconciliados.
- [x] Duração, IDs, bytes lidos e proveniência registrados em `data/processed/sprint3_evidence.json` e nas evidências do Grafana.
- [ ] Custo observado no orçamento ou no console Billing registrado com data, escopo e ressalva de atraso.
- [x] Documentação e relatório final preparados em `docs/sprint3.md` e `docs/relatorio_final.md`.
