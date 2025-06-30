drop materialized view if exists derived.average_ring_metadata_view;
create materialized view derived.average_ring_metadata_view as
select
    r.type,
    b.reserve_level,
    avg(r.mass) as avg_mass,
    avg(r.ring_area) as avg_ring_area,
    avg(r.surface_density) as avg_surface_density
from core.rings as r
inner join core.bodies as b on r.body_id = b.id
group by r.type, b.reserve_level;

drop index if exists derived.average_ring_metadata_view_type_reserve_level_idx;
create unique index if not exists average_ring_metadata_view_type_reserve_level_idx
on derived.average_ring_metadata_view (type, reserve_level);
create index if not exists average_ring_metadata_view_reserve_level_idx
on derived.average_ring_metadata_view (reserve_level);
