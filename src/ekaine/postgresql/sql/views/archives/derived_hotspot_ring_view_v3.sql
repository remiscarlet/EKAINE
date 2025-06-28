drop view if exists derived.hostspot_ring_view;
create or replace view derived.hotspot_ring_view as
select
    s.id as system_id,
    s.name as system_name,
    b.id as body_id,
    b.name as body_name,
    r.id as ring_id,
    r.name as ring_name,
    r.type as ring_type,
    b.reserve_level as body_reserve_level,
    hs.commodity_sym as commodity,
    hs.count
from core.hotspots as hs
inner join core.rings as r
    on hs.ring_id = r.id
inner join core.bodies as b
    on r.body_id = b.id
inner join core.systems as s
    on b.system_id = s.id;
