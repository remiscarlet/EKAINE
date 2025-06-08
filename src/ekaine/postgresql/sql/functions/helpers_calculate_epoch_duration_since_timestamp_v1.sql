drop function if exists helpers.calculate_epoch_duration_since_timestamp;
create or replace function helpers.calculate_epoch_duration_since_timestamp(
    ts timestamp
)
returns int
as $$
    select cast(extract(epoch from now() - ts) as integer) as age
$$ language sql;
