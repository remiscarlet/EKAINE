drop materialized view if exists derived.mining_map_acquisition_routes_view;
create materialized view derived.mining_map_acquisition_routes_view as
with acquisition_routes_with_mining_maps as (
    select
        parv.vector_name,
        parv.vector_id,
        parv.vector_state,
        parv.target_name,
        parv.target_id,
        parv.target_state,
        parv.target_population,
        parv.target_body_count,
        parv.target_primary_economy,
        parv.target_pcp,
        parv.controlling_faction_id,
        parv.target_updated_at,
        parv.distance,
        r.name as ring_name,
        r.type as ring_type,
        mm.name as map_name,
        mm.map_url,
        mm.rock_count,
        mmc.commodity_sym,
        mmc.approximate_tonnage_solo
    from derived.potential_acquisition_routes_view as parv
    inner join core.mining_maps as mm on parv.vector_id = mm.system_id
    inner join core.mining_map_commodities as mmc on mm.id = mmc.mining_map_id
    inner join core.rings as r on mm.ring_id = r.id
    group by
        parv.vector_name, parv.vector_id, parv.vector_state,
        parv.target_name, parv.target_id, parv.target_state,
        parv.target_population,
        parv.target_body_count,
        parv.target_primary_economy,
        parv.target_pcp,
        parv.controlling_faction_id,
        parv.target_updated_at,
        parv.distance,
        r.name, r.type,
        mm.name, mm.map_url, mm.rock_count, mmc.commodity_sym, mmc.approximate_tonnage_solo
)

select distinct on (
    armm.vector_id, armm.target_id, armm.ring_name, armm.commodity_sym, scv.station_name
)
    armm.vector_name,
    armm.vector_id,
    armm.vector_state,
    armm.distance,
    armm.target_name,
    armm.target_id,
    armm.target_state,
    armm.target_population,
    armm.target_body_count,
    armm.target_primary_economy,
    armm.target_pcp,
    armm.target_updated_at,
    armm.ring_name,
    armm.ring_type,
    armm.map_name,
    armm.map_url,
    armm.rock_count,
    armm.commodity_sym,
    armm.approximate_tonnage_solo,
    scv.station_name,
    scv.controlling_faction_id,
    scv.sell_price,
    scv.demand,
    scv.updated_at as market_updated_at
from acquisition_routes_with_mining_maps as armm
inner join lateral (
    select
        scv.station_name,
        f.id as controlling_faction_id,
        scv.sell_price,
        scv.demand,
        scv.updated_at
    from derived.station_commodities_view as scv
    inner join core.stations as s on scv.station_id = s.id
    inner join core.factions as f on s.controlling_faction = f.name
    where
        scv.system_id = armm.target_id
        and scv.commodity_sym = armm.commodity_sym
        and scv.type <> 'Drake-Class Carrier'
    order by scv.updated_at desc
) as scv on true;

-- Create an index directly in the SQL,
-- since we don't have a SA2.0 class table definition to define the index on.
create unique index mining_map_ar_view_uidx on derived.mining_map_acquisition_routes_view (
    vector_id, target_id, map_name, commodity_sym, station_name
);
create index if not exists mining_map_ar_view_vector_id_idx
on derived.mining_map_acquisition_routes_view (
    vector_id
);
create index if not exists mining_map_ar_view_vector_state_idx
on derived.mining_map_acquisition_routes_view (
    vector_state
);
create index if not exists mining_map_ar_view_target_id_idx
on derived.mining_map_acquisition_routes_view (
    target_id
);
create index if not exists mining_map_ar_view_target_state_idx
on derived.mining_map_acquisition_routes_view (
    target_state
);
create index if not exists mining_map_ar_view_target_population_idx
on derived.mining_map_acquisition_routes_view (
    target_population
);
create index if not exists mining_map_ar_view_target_body_count_idx
on derived.mining_map_acquisition_routes_view (
    target_body_count
);
create index if not exists mining_map_ar_view_target_primary_economy_idx
on derived.mining_map_acquisition_routes_view (target_primary_economy);
create index if not exists mining_map_ar_view_controlling_faction_id_idx
on derived.mining_map_acquisition_routes_view (controlling_faction_id);
create index if not exists mining_map_ar_view_ring_type_idx
on derived.mining_map_acquisition_routes_view (
    ring_type
);
create index if not exists mining_map_ar_view_map_name_idx
on derived.mining_map_acquisition_routes_view (
    map_name
);
create index if not exists mining_map_ar_view_commodity_sym_idx
on derived.mining_map_acquisition_routes_view (
    commodity_sym
);
create index if not exists mining_map_ar_view_station_name_idx
on derived.mining_map_acquisition_routes_view (
    station_name
);
create index if not exists mining_map_ar_view_sell_price_idx
on derived.mining_map_acquisition_routes_view (
    sell_price
);
create index if not exists mining_map_ar_view_demand_idx
on derived.mining_map_acquisition_routes_view (
    demand
);
create index if not exists mining_map_ar_view_market_updated_at_idx
on derived.mining_map_acquisition_routes_view (
    market_updated_at
);
