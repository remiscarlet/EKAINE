drop view if exists derived.resolved_stations_view;
create view derived.resolved_stations_view as
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
    case
        when st.owner_type = 'system' then st.owner_id
        when st.owner_type = 'body' then b.system_id
    end as system_id
from core.stations as st
left join core.bodies as b on st.owner_type = 'body' and st.owner_id = b.id;
