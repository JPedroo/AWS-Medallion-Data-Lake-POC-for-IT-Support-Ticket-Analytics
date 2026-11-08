# Plano da POC em três sprints

Fonte de escopo: briefing local `briefing_projeto_data_lake_medalhao_aws_poc_3_semanas.pdf`, fornecido pelo usuário. A Sprint 1 é o trabalho autorizado nesta sessão; as demais são planejamento.

| Sprint | Período | Entrega | Estado em 2026-11-08 |
| --- | --- | --- | --- |
| 1 — Preparação e Bronze | Dias 1–5 | Dataset validado, ambiente, orçamento e bucket privados, CSV original e manifesto no S3 | **Parcial**: fonte, código, CLI e Spark locais validados; AWS aguarda perfil autenticado; upload pendente |
| 2 — Silver e Gold | Dias 6–11 | Qualidade, Parquet/Snappy, duas tabelas Gold, DDL/consultas Athena | Planejada |
| 3 — Consumo e entrega | Dias 12–15 | Grafana local, evidências, custo observado, relatório e vídeo | Planejada |

## Sprint 1 — critérios de aceite

- [x] Licença, versão, arquivo, esquema, codificação, delimitador, amostra e indicadores documentados.
- [x] Git local e remoto `origin` configurados; dependências fixadas; dados e segredos ignorados.
- [x] Python, Java, AWS CLI e job PySpark mínimo validados localmente.
- [ ] Perfil AWS não root autenticado e permissões de provisionamento verificadas.
- [ ] Orçamento mensal com alertas criado antes dos recursos de dados.
- [ ] Bucket privado em uma região, bloqueio público, criptografia e versionamento verificados.
- [ ] Política IAM mínima associada a identidade de ingestão existente, se aplicável.
- [x] Ingestão boto3 e manifesto com SHA-256 implementados e validados em modo local.
- [ ] CSV original e manifesto no S3; `head-object` e checksum conferidos.
- [ ] Commit enviado ao GitHub remoto.

## Decisões para a Sprint 2

- Usar PySpark local e boto3 para staging entre S3 e disco local.
- Criar `ticket_id` estável a partir de conteúdo, porque a origem não fornece ID.
- Definir `quality_status` e reconciliar registros antes de agregar.
- Gravar Silver e Gold em Parquet/Snappy; criar o catálogo com DDL versionado, sem Crawler.
- Evitar qualquer métrica temporal de negócio ou SLA por falta de datas na origem.
