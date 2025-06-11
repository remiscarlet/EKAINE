drop function if exists derived.calculate_epoch_duration_since_timestamp;
create or replace function derived.calculate_epoch_duration_since_timestamp(
    ts timestamp
)
returns int
as $$
    ----------------
    -- Deprecated --
    ----------------
    --
    -- Use helpers.calculate_epoch_duration_since_timestamp
    --
    select cast(extract(epoch from now() - ts) as integer) as age
$$ language sql;
