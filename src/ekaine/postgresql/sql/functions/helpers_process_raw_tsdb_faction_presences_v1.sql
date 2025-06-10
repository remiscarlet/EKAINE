drop procedure if exists helpers.process_raw_tsdb_faction_presences;
create or replace procedure helpers.process_raw_tsdb_faction_presences(
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
  limit 1
), config as (
  select
    c.duration,
    c.now,
    tb.bucket_start,
    tb.bucket_start + c.duration as bucket_end
  from constants c
  join time_bucket tb on true
),flattened_timescale_rows as (
    select
      time_bucket((select duration from config)::interval, max(timestamp)) as timestamp,
      --timestamp as orig_timestamp,
      --(select now from config), (select bucket_start from config), (select bucket_end from config),
      system_id,
      faction_id,
      mode() within group (order by influence) as influence,
      mode() within group (order by state) as state,
      mode() within group (order by happiness) as happiness,
      mode() within group (order by active_states) as active_states,
      mode() within group (order by recovering_states) as recovering_states,
      mode() within group (order by pending_states) as pending_states,
      (select bucket_start from config) as updated_at,
      false as is_backfilled
    from raw_timescaledb.faction_presences
    where (select bucket_start from config) <= timestamp and timestamp < (select bucket_end from config)
    group by system_id, faction_id
), all_known_system_faction_pairs as (
    select
        system_id,
        faction_id
    from core.faction_presences fp
    group by system_id, faction_id
), missing_system_faction_pairs as (
    select
        aksfp.system_id,
        aksfp.faction_id
    from all_known_system_faction_pairs aksfp
    left join flattened_timescale_rows ftr on aksfp.faction_id = ftr.faction_id and aksfp.system_id = ftr.system_id
    where ftr.system_id is null
), backfill_rows as (
    select
      (select bucket_start from config) as timestamp,
      msfp.system_id,
      msfp.faction_id,
      latest_row.influence,
      latest_row.state,
      latest_row.happiness,
      latest_row.active_states,
      latest_row.recovering_states,
      latest_row.pending_states,
      latest_row.updated_at,
      true as is_backfilled
    from missing_system_faction_pairs msfp
    join lateral (
        select *
          from raw_timescaledb.faction_presences fp
         where fp.faction_id = msfp.faction_id
           and fp.system_id = msfp.system_id
         order by timestamp desc
         limit 1
    ) latest_row on true
), all_rows as (
    select * from backfill_rows
    union all
    select * from flattened_timescale_rows
)
insert into timescaledb.faction_presences (
    timestamp,
    system_id,
    faction_id,
    influence,
    state,
    happiness,
    active_states,
    pending_states,
    recovering_states,
    updated_at,
    is_backfilled
)
select
    timestamp,
    system_id,
    faction_id,
    influence,
    state,
    happiness,
    active_states,
    pending_states,
    recovering_states,
    updated_at,
    is_backfilled
from all_rows
on conflict (timestamp, system_id, faction_id) do update
set influence = EXCLUDED.influence,
  state = EXCLUDED.state,
  happiness = EXCLUDED.happiness,
  active_states = EXCLUDED.active_states,
  pending_states = EXCLUDED.pending_states,
  recovering_states = EXCLUDED.recovering_states,
  updated_at = EXCLUDED.updated_at,
  is_backfilled = EXCLUDED.is_backfilled
;
$$
