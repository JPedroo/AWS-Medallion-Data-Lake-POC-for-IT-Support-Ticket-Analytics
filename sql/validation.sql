-- Consultas de validação; o script catalog_athena.py executa as equivalentes e compara com quality.json.
SELECT quality_status, count(*) AS ticket_count
FROM medallion_it_tickets_poc.silver_tickets
GROUP BY quality_status;

SELECT sum(ticket_count) AS ticket_count
FROM medallion_it_tickets_poc.gold_tickets_by_type_priority;

SELECT sum(ticket_count) AS ticket_count
FROM medallion_it_tickets_poc.gold_tickets_by_queue_language;

SELECT "type", priority, ticket_count
FROM medallion_it_tickets_poc.gold_tickets_by_type_priority
ORDER BY ticket_count DESC;

SELECT queue, language, ticket_count
FROM medallion_it_tickets_poc.gold_tickets_by_queue_language
ORDER BY ticket_count DESC;
