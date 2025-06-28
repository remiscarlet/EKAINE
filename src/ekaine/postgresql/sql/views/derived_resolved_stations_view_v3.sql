drop materialized view if exists derived.resolved_stations_view;
create materialized view derived.resolved_stations_view as
select
    st.id,
    st.id64,
    st.id_spansh,
    st.id_edsm,
    st.name,
    st.owner_id,
    st.owner_type,
    st.allegiance,
    st.controlling_faction,
    st.controlling_faction_state,
    st.distance_to_arrival,
    st.economies,
    st.government,
    st.small_landing_pads,
    st.medium_landing_pads,
    st.large_landing_pads,
    st.primary_economy,
    st.services,
    st.type,
    st.prohibited_commodities,
    st.carrier_name,
    st.latitude,
    st.longitude,
    st.spansh_updated_at,
    st.edsm_updated_at,
    st.eddn_updated_at,
    sy.id as system_id
from core.stations as st
inner join core.systems as sy
    on st.owner_type = 'system' and st.owner_id = sy.id

union all

select
    st.id,
    st.id64,
    st.id_spansh,
    st.id_edsm,
    st.name,
    st.owner_id,
    st.owner_type,
    st.allegiance,
    st.controlling_faction,
    st.controlling_faction_state,
    st.distance_to_arrival,
    st.economies,
    st.government,
    st.small_landing_pads,
    st.medium_landing_pads,
    st.large_landing_pads,
    st.primary_economy,
    st.services,
    st.type,
    st.prohibited_commodities,
    st.carrier_name,
    st.latitude,
    st.longitude,
    st.spansh_updated_at,
    st.edsm_updated_at,
    st.eddn_updated_at,
    sy.id as system_id
from core.stations as st
inner join core.bodies as b
    on st.owner_type = 'body' and st.owner_id = b.id
inner join core.systems as sy
    on b.system_id = sy.id;


drop index if exists derived.resolved_stations_view_id_idx;
create unique index if not exists resolved_stations_view_id_idx
on derived.resolved_stations_view (id);
create index if not exists resolved_stations_view_name_idx on derived.resolved_stations_view (
    name
);
create index if not exists resolved_stations_view_type_idx on derived.resolved_stations_view (
    type
);
create index if not exists resolved_stations_view_primary_economy_idx
on derived.resolved_stations_view (primary_economy);
create index if not exists resolved_stations_view_government_idx on derived.resolved_stations_view (
    government
);
create index if not exists resolved_stations_view_allegiance_idx on derived.resolved_stations_view (
    allegiance
);
create index
if not exists resolved_stations_view_services_idx on derived.resolved_stations_view using gin (
    services
);
create index if not exists resolved_stations_view_system_id_idx on derived.resolved_stations_view (
    system_id
);
