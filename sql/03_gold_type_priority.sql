CREATE EXTERNAL TABLE IF NOT EXISTS medallion_it_tickets_poc.gold_tickets_by_type_priority (
  `type` string,
  priority string,
  ticket_count bigint
)
STORED AS PARQUET
LOCATION 's3://{bucket}/gold/tickets_by_type_priority/'
