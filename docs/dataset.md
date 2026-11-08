# Dataset e indicadores da POC

## Fonte, direito de uso e recorte

- Fonte: [Customer IT Support - Ticket Dataset, Tobias Bueck](https://www.kaggle.com/datasets/tobiasbueck/multilingual-customer-support-tickets).
- Licença informada pelo publicador nos metadados retornados pelo SDK Kaggle: **Attribution 4.0 International (CC BY 4.0)**. O uso e a redistribuição exigem atribuição; este repositório contém só código e documentação. Consulte o [texto da licença](https://creativecommons.org/licenses/by/4.0/).
- Versão fixada: **14**, publicada em 2025-12-02 conforme metadados do SDK; consulta realizada em 2026-11-08. O download da versão mais recente sem fixação poderia mudar a fonte entre execuções.
- Arquivo escolhido: `dataset-tickets-multi-lang3-4k.csv`. É um arquivo completo oferecido nessa versão, com 4.000 registros, adequado ao recorte de 1.000 a 5.000 tickets do briefing. A Bronze preserva todos os seus bytes; não recortamos linhas do CSV.
- Tamanho: **6.873.542 bytes**; SHA-256: `9aae7120cf459fc27561febe29c7757c6d222bfebff50e8baa868991e57b87d1`.
- Codificação validada: **UTF-8**; delimitador: **vírgula**; cabeçalho e 4.000 linhas lidos com `csv.reader(strict=True)`. O arquivo contém campos entre aspas e quebras de linha em textos.
- Dados sintéticos de suporte ao cliente; servem como aproximação didática de ITSM, sem equivalência direta com ServiceNow. Há texto livre, inclusive nomes e empresas fictícios; não publicar exemplos de tickets nem o CSV no GitHub.

## Esquema real

Todos os campos são texto no CSV. Não existem `id`, `created_at`, data de resolução ou SLA.

| Campo | Papel no recorte | Vazios observados |
| --- | --- | ---: |
| `subject` | Assunto do ticket | 468 |
| `body` | Descrição | 1 |
| `answer` | Resposta do agente; preservada na Bronze | 0 |
| `type` | Tipo de ticket | 0 |
| `queue` | Fila/grupo | 0 |
| `priority` | Prioridade | 0 |
| `language` | Idioma | 0 |
| `business_type` | Contexto do negócio | 0 |
| `tag_1` a `tag_9` | Tags de origem, sem interpretação semântica na Sprint 1 | `tag_9`: 4.000 |

O cabeçalho na ordem de origem é `subject,body,answer,type,queue,priority,language,business_type,tag_1,tag_2,tag_3,tag_4,tag_5,tag_6,tag_7,tag_8,tag_9`.

### Amostra estrutural, sem texto livre

| Registro | `subject` | `body` | `type` | `queue` | `priority` | `language` |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | preenchido | preenchido | Incident | Technical Support | high | es |
| 2 | preenchido | preenchido | Request | Customer Service | low | de |

### Perfil observado

| Dimensão | Valores e contagens observadas |
| --- | --- |
| Tipo | Incident 1.608; Request 1.097; Problem 853; Change 442 |
| Prioridade | high 1.649; medium 1.603; low 748 |
| Idioma | en 1.391; de 848; es 812; fr 476; pt 473 |
| Fila | 10 valores; maiores: Technical Support 1.317, Product Support 690, Customer Service 627 |
| Duplicatas exatas | 0 |

## Indicadores definidos

1. **Volume**: registros de entrada, válidos, rejeitados e duplicados por execução; reconciliar `entrada = mantidos + duplicados` e `mantidos = válidos + rejeitados`.
2. **Distribuição operacional**: tickets válidos por `type`, `priority` e `queue`; idioma como dimensão secundária. Não inferir categorias a partir do texto.
3. **Qualidade**: percentual de `subject` vazio, `body` vazio, IDs derivados, valores `unknown` e rejeições. A regra de rejeição proposta é assunto **e** descrição vazios; cada campo vazio isolado é alerta.
4. **Rastreabilidade**: versão, hash, bytes e data de ingestão do CSV; duração do processamento e tamanhos CSV/Parquet quando Silver/Gold existirem.
5. **Consulta**: bytes lidos no Athena e custo observado somente após execução real.

Como não há ID de origem, a Silver deverá criar um hash estável de campos definidos e documentar a regra de desempate. Como não há data de evento confiável, nenhum indicador de série temporal de negócio ou SLA será criado; `ingested_at` é apenas metadado de pipeline.

## Evidência reproduzível

```bash
.venv/bin/python src/fetch_dataset.py
.venv/bin/python src/ingest_bronze.py --source data/raw/dataset-tickets-multi-lang3-4k.csv --dry-run
```

`kagglehub.dataset_download` grava um arquivo em disco/cache mesmo quando se usa o adaptador Pandas. Baixar o arquivo versionado diretamente é necessário aqui para preservar e verificar os bytes originais na Bronze.
