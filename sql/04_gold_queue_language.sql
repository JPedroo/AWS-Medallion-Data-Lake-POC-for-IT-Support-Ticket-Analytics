CREATE EXTERNAL TABLE IF NOT EXISTS medallion_it_tickets_poc.gold_tickets_by_queue_language (
  queue string,
  language string,
  ticket_count bigint
)
STORED AS PARQUET
LOCATION 's3://{bucket}/gold/tickets_by_queue_language/'
