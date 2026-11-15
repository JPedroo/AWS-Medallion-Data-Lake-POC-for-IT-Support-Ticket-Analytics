# Data Lake Medalhão na AWS para tickets de suporte

Prova de conceito acadêmica de um data lake para análise de tickets de suporte. O projeto usa um conjunto de dados público do Kaggle, processa os registros com PySpark e disponibiliza tabelas em Parquet para consulta no Amazon Athena. As camadas Bronze, Silver e Gold e o catálogo Athena estão implementados; o consumo em Grafana integra a etapa seguinte.

## Fonte de dados

O dataset é [Customer IT Support - Ticket Dataset](https://www.kaggle.com/datasets/tobiasbueck/multilingual-customer-support-tickets), de Tobias Bueck, sob licença [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). A POC usa o arquivo `dataset-tickets-multi-lang3-4k.csv` da versão 14, com 4.000 registros e 17 campos. Ele inclui assunto, descrição, resposta, tipo, fila, prioridade, idioma e tags.

O CSV original contém texto livre e não é versionado neste repositório. O esquema, o perfil dos dados e as limitações do recorte estão em [docs/dataset.md](docs/dataset.md).

## Arquitetura

```mermaid
flowchart LR
    K[Dataset Kaggle] --> B[Bronze: CSV original e manifesto no S3]
    B --> S[Silver: limpeza, qualidade e deduplicação em Parquet]
    S --> G[Gold: duas agregações em Parquet]
    G --> A[Glue Data Catalog e Athena]
```

- **Bronze:** preserva o CSV original e um manifesto com informações da fonte e verificação de integridade.
- **Silver:** padroniza os campos, cria um identificador derivado, remove duplicatas e registra métricas de qualidade.
- **Gold:** oferece contagens por tipo e prioridade e por fila e idioma, considerando apenas registros válidos.
- **Consulta:** três tabelas externas no catálogo permitem explorar Silver e Gold com SQL no Athena.

## Requisitos

- Python 3.11 ou superior e Java 17 ou superior para execução local com PySpark.
- Dependências Python de [requirements.txt](requirements.txt).
- AWS CLI v2 e um perfil com acesso aos serviços S3, Athena e Glue para reproduzir as etapas na AWS.
- Acesso ao Kaggle para baixar a versão do dataset usada na POC.

Para preparar o ambiente local:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
SPARK_LOCAL_IP=127.0.0.1 .venv/bin/python scripts/check_spark.py
```

Os diretórios `data/`, `.venv/` e `.tools/` ficam fora do Git. Os testes podem ser executados com:

```bash
SPARK_LOCAL_IP=127.0.0.1 .venv/bin/python -m unittest discover -s tests -v
```

## Documentação

- [Plan.md](Plan.md): etapas e estado do projeto.
- [Documentation.md](Documentation.md): arquitetura e decisões técnicas.
- [docs/sprint2.md](docs/sprint2.md): regras de transformação, artefatos, execução e validação.
- [docs/aws_access.md](docs/aws_access.md): configuração de acesso à AWS.
- [docs/diario_do_projeto.md](docs/diario_do_projeto.md): histórico das implementações e evidências.
