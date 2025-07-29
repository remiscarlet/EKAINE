drop materialized view if exists derived.hotspot_ring_view;
create materialized view derived.hotspot_ring_view as
select
    s.id as system_id,
    s.name as system_name,
    b.id as body_id,
    b.name as body_name,
    r.id as ring_id,
    r.name as ring_name,
    r.mass as ring_mass,
    r.outer_radius as ring_outer_radius,
    r.inner_radius as ring_inner_radius,
    r.type as ring_type,
    b.reserve_level as body_reserve_level,
    hs.commodity_sym,
    hs.count as hotspot_count,
    b.mean_anomaly_updated_at as body_mean_anomaly_updated_at,
    b.distance_to_arrival_updated_at as body_distance_to_arrival_updated_at,
    hs.updated_at as hotspot_updated_at
from core.hotspots as hs
inner join core.rings as r
    on hs.ring_id = r.id
inner join core.bodies as b
    on r.body_id = b.id
inner join core.systems as s
    on b.system_id = s.id;

-- Create an index directly in the SQL,
-- since we don't have a SA2.0 class table definition to define the index on.
drop index if exists derived.hotspot_ring_view_system_id_idx;
create unique index if not exists hotspot_ring_view_system_id_idx on derived.hotspot_ring_view (
    system_id, body_id, ring_id, commodity_sym
);
create index if not exists hotspot_ring_view_body_id_idx on derived.hotspot_ring_view (
    body_id
);
create index if not exists hotspot_ring_view_ring_id_idx on derived.hotspot_ring_view (
    ring_id
);
create index if not exists hotspot_ring_view_ring_type_idx on derived.hotspot_ring_view (
    ring_type
);
create index if not exists hotspot_ring_view_body_reserve_level_idx on derived.hotspot_ring_view (
    body_reserve_level
);
create index if not exists hotspot_ring_view_commodity_sym_id
on derived.hotspot_ring_view (commodity_sym);
