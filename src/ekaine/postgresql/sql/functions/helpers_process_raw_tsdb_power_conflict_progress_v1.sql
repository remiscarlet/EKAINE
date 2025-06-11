drop procedure if exists helpers.process_raw_tsdb_power_conflict_progress;
create or replace procedure helpers.process_raw_tsdb_power_conflict_progress(
    p_bucket_interval_duration text
)
language sql
as $$
with constants as (
  select
    p_bucket_interval_duration::interval as duration,
    date_trunc('minute', now()::timestamp without time zone) as now
), time_bucket as (
  select generate_series(
    date_trunc('week', (select now from constants)),
    (select now from constants),
    (select duration from constants)
  ) as bucket_start
  order by bucket_start desc
  offset 1
  limit 1
), config as (
  select
    c.duration,
    c.now,
    tb.bucket_start,
    tb.bucket_start + c.duration as bucket_end
  from constants c
  join time_bucket tb on true
), flattened_timescale_rows as (
    select
      time_bucket((select duration from config)::interval, max(timestamp)) as timestamp,
      system_id,
      power_name,
      mode() within group (order by progress) as progress,
      (select bucket_start from config) as updated_at,
      false as is_backfilled
    from raw_timescaledb.power_conflict_progress
    where (select bucket_start from config) <= timestamp and timestamp < (select bucket_end from config)
    group by system_id, power_name
), all_known_system_conflicts as (
    select
        pcp.system_id,
        pcp.power_name
    from timescaledb.power_conflict_progress pcp
    join core.systems s on pcp.system_id = s.id
    where s.power_state = 'Unoccupied'
    group by pcp.system_id, pcp.power_name
), missing_system_conflict_pairs as (
    select
        aksc.system_id,
        aksc.power_name
    from all_known_system_conflicts aksc
    left join flattened_timescale_rows ftr on aksc.system_id = ftr.system_id
    where ftr.system_id is null
), backfill_rows as (
    select
      (select bucket_start from config) as timestamp,
      mscp.system_id,
      mscp.power_name,
      latest_row.progress,
      latest_row.updated_at,
      true as is_backfilled
    from missing_system_conflict_pairs mscp
    join lateral (
        select *
          from raw_timescaledb.power_conflict_progress pcp
         where pcp.system_id = mscp.system_id and pcp.power_name = mscp.power_name
         order by timestamp desc
         limit 1
    ) latest_row on true
), all_rows as (
    select * from backfill_rows
    union all
    select * from flattened_timescale_rows
)
insert into timescaledb.power_conflict_progress (
    timestamp,
    system_id,
    power_name,
    progress,
    updated_at,
    is_backfilled
)
select
    timestamp,
    system_id,
    power_name,
    progress,
    updated_at,
    is_backfilled
from all_rows
on conflict (timestamp, system_id, power_name) do update
set progress = EXCLUDED.progress,
  updated_at = EXCLUDED.updated_at,
  is_backfilled = EXCLUDED.is_backfilled
;
$$
