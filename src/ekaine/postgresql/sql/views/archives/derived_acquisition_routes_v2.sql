drop view if exists derived.acquisition_routes;
create or replace view derived.acquisition_routes as
with acquisition_vectors as (
    select
        s.id,
        s.id64,
        s.id_spansh,
        s.id_edsm,
        s.name,
        s.controlling_faction_id,
        s.x,
        s.y,
        s.z,
        s.coords,
        s.date,
        s.allegiance,
        s.population,
        s.primary_economy,
        s.secondary_economy,
        s.security,
        s.government,
        s.body_count,
        s.controlling_power,
        s.power_conflict_progress,
        s.power_state,
        s.power_state_control_progress,
        s.power_state_reinforcement,
        s.power_state_undermining,
        s.powers,
        s.thargoid_war,
        s.controlling_power_updated_at,
        s.power_state_updated_at,
        s.powers_updated_at
    from
        derived.get_systems_with_power_and_state(
            'Nakato Kaine', array['Fortified', 'Stronghold']
        ) as s
),

unoccupied_systems as (
    select
        s.id,
        s.id64,
        s.id_spansh,
        s.id_edsm,
        s.name,
        s.controlling_faction_id,
        s.x,
        s.y,
        s.z,
        s.coords,
        s.date,
        s.allegiance,
        s.population,
        s.primary_economy,
        s.secondary_economy,
        s.security,
        s.government,
        s.body_count,
        s.controlling_power,
        s.power_conflict_progress,
        s.power_state,
        s.power_state_control_progress,
        s.power_state_reinforcement,
        s.power_state_undermining,
        s.powers,
        s.thargoid_war,
        s.controlling_power_updated_at,
        s.power_state_updated_at,
        s.powers_updated_at
    from core.systems as s
    where
        'Nakato Kaine' = any(s.powers)
        and s.power_state = 'Unoccupied'
        and s.date >= (now() - INTERVAL '7 days')
),

all_acquisition_routes as (
    select
        av.name as vector_name,
        av.id as vector_id,
        av.power_state as vector_state,
        us.name as target_name,
        us.id as target_id,
        us.power_state as target_state,
        us.population as target_population,
        us.body_count as target_body_count,
        us.primary_economy as target_primary_economy,
        us.power_conflict_progress as target_pcp,
        us.controlling_faction_id,
        us.date as target_updated_at,
        st_3ddistance(av.coords, us.coords) as distance
    from acquisition_vectors as av
    inner join unoccupied_systems as us on st_3ddwithin(
        av.coords,
        us.coords,
        case when av.power_state = 'Stronghold' then 30 else 20 end
    )
),

acquisition_routes_with_hotspots as (
    select
        aar.vector_name,
        aar.vector_id,
        aar.vector_state,
        aar.target_name,
        aar.target_id,
        aar.target_state,
        aar.target_population,
        aar.target_body_count,
        aar.target_primary_economy,
        aar.target_pcp,
        aar.controlling_faction_id,
        aar.target_updated_at,
        aar.distance,
        hrv.ring_name,
        hrv.ring_type,
        hrv.commodity,
        hrv.count
    from all_acquisition_routes as aar
    inner join
        derived.hotspot_ring_view as hrv
        on aar.vector_name = hrv.system_name
)

select
    arh.vector_name,
    arh.vector_id,
    arh.vector_state,
    arh.distance,
    arh.target_name,
    arh.target_id,
    arh.target_state,
    arh.target_population,
    arh.target_body_count,
    arh.target_primary_economy,
    arh.target_pcp,
    arh.controlling_faction_id,
    arh.target_updated_at,
    arh.ring_name,
    arh.ring_type,
    arh.count,
    scv.commodity_sym,
    scv.station_name,
    scv.sell_price,
    scv.demand,
    scv.updated_at as market_updated_at
from acquisition_routes_with_hotspots as arh
inner join
    derived.station_commodities_view as scv
    on arh.target_name = scv.system_name
where
    arh.commodity = scv.commodity_sym
