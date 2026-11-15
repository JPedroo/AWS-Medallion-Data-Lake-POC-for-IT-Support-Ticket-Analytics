CREATE EXTERNAL TABLE IF NOT EXISTS medallion_it_tickets_poc.silver_tickets (
  ticket_id string,
  subject string,
  body string,
  answer string,
  `type` string,
  queue string,
  priority string,
  language string,
  business_type string,
  tag_1 string,
  tag_2 string,
  tag_3 string,
  tag_4 string,
  tag_5 string,
  tag_6 string,
  tag_7 string,
  tag_8 string,
  tag_9 string,
  subject_missing boolean,
  body_missing boolean,
  quality_status string
)
STORED AS PARQUET
LOCATION 's3://{bucket}/silver/tickets/'
