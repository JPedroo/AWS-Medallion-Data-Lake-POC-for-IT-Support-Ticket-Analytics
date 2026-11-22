# Evidências da Sprint 3 — 2026-11-22

## Escopo da execução

Perfil confirmado por STS: `arn:aws:iam::822218623538:user/medallion-poc-operator`, região `us-east-1`, bucket `medallion-it-tickets-poc-822218623538-us-east-1`. A coleta foi concluída às `2026-11-22T14:20:48Z`. Os JSON completos, ignorados pelo Git, estão em `data/processed/sprint3_evidence.json`, `sprint3_grafana_validation.json` e `sprint3_grafana_athena_stats.json`.

| Métrica | Resultado |
| --- | ---: |
| Linhas Bronze | 4.000 |
| Linhas Silver | 4.000 |
| Duplicatas | 0 |
| Válidas | 4.000 |
| Rejeitadas | 0 |
| Assuntos vazios | 468 |
| Descrições vazias | 1 |
| Soma Gold tipo/prioridade | 4.000 |
| Soma Gold fila/idioma | 4.000 |
| Divergências Gold/Silver por grupo | 0 em ambas |
| Processamento/publicação AWS | 19,37 s |
| Consultas de validação Athena | 7.478 bytes lidos |
| Consultas Grafana/Athena, duas rodadas | 2.352 bytes lidos |
| Total técnico dessas consultas | 9.830 bytes lidos |

Fonte fixada: versão 14 do dataset Kaggle, CSV com SHA-256 `9aae7120cf459fc27561febe29c7757c6d222bfebff50e8baa868991e57b87d1`. O manifesto Bronze tem `pipeline_run_id` `69be473b-d936-47b8-b813-63a78fc02d18` e foi gravado em `2026-11-08T20:56:31.700728Z`. O coletor conferiu checksum SHA-256, tamanho, metadados de origem, SSE-S3, IDs de versão e localizações das três tabelas Glue. Os objetos derivados têm `LastModified` de 2026-11-15, anterior à reexecução, o que confirma que não foram sobrescritos nesta sprint.

| Objeto | Bytes | Versão S3 |
| --- | ---: | --- |
| Bronze CSV | 6.873.542 | `VoIbFrU7q_Nn6uMtX2H76HGF23n5_GkK` |
| Bronze manifesto | 1.271 | `UDEL7YMiJ6nPHEq.tB.YlOFfA1KSFonP` |
| Silver Parquet | 3.866.831 | `jRXHaY7XTK8APXvMezuB2_17KmOmh3h6` |
| Gold tipo/prioridade | 1.170 | `fjCflxH2KEqxRG_g.4LJJE8d5PUNAq.n` |
| Gold fila/idioma | 1.605 | `I4Qx72WNy_vc6ejtAlJBWidX9HOBolQR` |
| Qualidade JSON | 533 | `QeLkjsAujdKf9kPET1ws0Jx8a_YiVIra` |

## Consultas Athena da reexecução

| Verificação | ID da consulta | Bytes lidos | Duração Athena (ms) |
| --- | --- | ---: | ---: |
| Banco | `809ec077-004a-4ab9-a9da-6897cbba8d81` | 0 | 456 |
| Silver DDL | `7ae82c43-8d50-4454-a263-5840202a4a62` | 0 | 545 |
| Gold tipo/prioridade DDL | `88d77b38-9862-417a-8c00-2ffe1db77f79` | 0 | 412 |
| Gold fila/idioma DDL | `9c1ff615-dcaa-40b2-9587-99868a3dcf1d` | 0 | 378 |
| Silver válidos | `c8d9a0e3-6a30-409f-ab6a-670cab3f36aa` | 59 | 1.023 |
| Silver rejeitados | `0c8710d6-20dc-4fee-98e7-5b85fbe9a46d` | 0 | 797 |
| Gold tipo/prioridade | `47ea7cae-3fd6-4a6c-9d49-15fc32b66490` | 90 | 727 |
| Gold fila/idioma | `0e0e3421-78a1-4d25-8fe9-c4062d8e5bcf` | 266 | 805 |
| Divergência por tipo/prioridade | `efbc25c2-3145-4905-afc9-15b2fb02440d` | 2.514 | 660 |
| Divergência por fila/idioma | `f2b4aec3-2963-4470-8c70-b491b8ca2fa4` | 4.549 | 756 |

## Painel Grafana

A fonte `athena-medallion` respondeu `Data source is working`. O painel `medallion-it-tickets` consultou as duas Gold com três visualizações: tipo/prioridade (4 linhas), fila (10 linhas) e idioma (5 linhas). Cada consulta retornou 4.000 tickets. As duas rodadas de teste produziram seis consultas Athena bem-sucedidas, com os seguintes IDs:

| ID da consulta | Bytes lidos | Duração Athena (ms) |
| --- | ---: | ---: |
| `dbaec5a2-c332-419b-971b-a393d0fad405` | 552 | 606 |
| `2718793e-15ce-4c3c-8f99-c2cd3594de66` | 263 | 798 |
| `1584b8e8-aa59-4e51-9355-cb463c360473` | 361 | 629 |
| `5df3d8f8-9c01-433a-9431-85463d44e3b7` | 361 | 685 |
| `8e93b019-143f-443f-8065-c87f9299e891` | 263 | 624 |
| `9db3df0e-9132-4792-abf5-cff9702ad2bc` | 552 | 996 |

## Custo observado

O perfil runtime recebeu `AccessDeniedException` para `budgets:DescribeBudget`; o usuário confirmou não ter acesso ao orçamento no Console. **Não há medição atual de custo faturado.** O número de bytes lidos é evidência técnica e não corresponde diretamente à cobrança. O valor de US$ 0,00 registrado na Sprint 1 é histórico. O [passo a passo da Sprint 3](sprint3.md) indica como uma identidade autorizada pode registrar o gasto mensal da conta com horário e moeda.
