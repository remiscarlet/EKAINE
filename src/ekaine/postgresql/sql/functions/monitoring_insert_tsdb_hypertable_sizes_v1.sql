drop procedure if exists monitoring.insert_tsdb_hypertable_sizes;
create or replace procedure monitoring.insert_tsdb_hypertable_sizes()
language sql
as $$
with hypertable_sizes as (
    SELECT
        date_trunc('minute', now()) as timestamp,
        h.schema_name,
        h.table_name,
        hypertable_size(format('%I.%I', h.schema_name, h.table_name)::regclass) as size,
        row_estimate.row_estimate
    FROM _timescaledb_catalog.hypertable h
        CROSS JOIN LATERAL ( SELECT sum(cl.reltuples) AS row_estimate
            FROM _timescaledb_catalog.chunk c
                JOIN pg_class cl ON cl.relname = c.table_name
            WHERE c.hypertable_id = h.id
            GROUP BY h.schema_name, h.table_name) row_estimate
    ORDER BY row_estimate desc, schema_name, table_name
)
insert into monitoring.hypertable_sizes (
    timestamp,
    schema_name,
    table_name,
    size,
    row_estimate
)
select
    timestamp,
    schema_name,
    table_name,
    size,
    row_estimate
from hypertable_sizes
on conflict (schema_name, table_name, timestamp) do update
set size = EXCLUDED.size,
    row_estimate = EXCLUDED.row_estimate
;
$$
