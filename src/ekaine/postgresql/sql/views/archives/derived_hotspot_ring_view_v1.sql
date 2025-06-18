drop view if exists derived.hostspot_ring_view;
create or replace view derived.hotspot_ring_view as
select
    s.name as system_name,
    b.name as body_name,
    r.name as ring_name,
    r.type as ring_type,
    hs.commodity_sym as commodity,
    hs.count
from core.hotspots as hs
inner join core.rings as r
    on hs.ring_id = r.id
inner join core.bodies as b
    on r.body_id = b.id
inner join core.systems as s
    on b.system_id = s.id;
