drop materialized view if exists derived.hotspot_acquisition_routes_view;
create materialized view derived.hotspot_acquisition_routes_view as
with acquisition_routes_with_hotspots as (
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
        hrv.ring_name,
        hrv.ring_type,
        hrv.hotspot_commodity_sym,
        hrv.hotspot_count
    from derived.potential_acquisition_routes_view as parv
    inner join
        derived.hotspot_ring_view as hrv
        on parv.vector_id = hrv.system_id
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
        hrv.ring_name,
        hrv.ring_type,
        hrv.hotspot_commodity_sym,
        hrv.hotspot_count
)

select distinct on (
    arh.vector_id, arh.target_id, arh.ring_name, arh.hotspot_commodity_sym, scv.station_name
)
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
    arh.hotspot_count,
    arh.hotspot_commodity_sym,
    scv.station_name,
    scv.sell_price,
    scv.demand,
    scv.updated_at as market_updated_at
from acquisition_routes_with_hotspots as arh
inner join lateral (
    select
        scv.station_name,
        scv.sell_price,
        scv.demand,
        scv.updated_at
    from derived.station_commodities_view as scv
    where
        scv.system_id = arh.target_id
        and scv.commodity_sym = arh.hotspot_commodity_sym
        and scv.type <> 'Drake-Class Carrier'
    order by scv.updated_at desc
) as scv on true;

-- Create an index directly in the SQL,
-- since we don't have a SA2.0 class table definition to define the index on.
create unique index hotspot_ar_view_uidx on derived.hotspot_acquisition_routes_view (
    vector_id, target_id, ring_name, hotspot_commodity_sym, station_name
);
create index if not exists hotspot_ar_view_vector_id_idx
on derived.hotspot_acquisition_routes_view (
    vector_id
);
create index if not exists hotspot_ar_view_vector_state_idx
on derived.hotspot_acquisition_routes_view (
    vector_state
);
create index if not exists hotspot_ar_view_target_id_idx
on derived.hotspot_acquisition_routes_view (
    target_id
);
create index if not exists hotspot_ar_view_target_state_idx
on derived.hotspot_acquisition_routes_view (
    target_state
);
create index if not exists hotspot_ar_view_target_population_idx
on derived.hotspot_acquisition_routes_view (
    target_population
);
create index if not exists hotspot_ar_view_target_body_count_idx
on derived.hotspot_acquisition_routes_view (
    target_body_count
);
create index if not exists hotspot_ar_view_target_primary_economy_idx
on derived.hotspot_acquisition_routes_view (
    target_primary_economy
);
create index if not exists hotspot_ar_view_controlling_faction_id_idx
on derived.hotspot_acquisition_routes_view (
    controlling_faction_id
);
create index if not exists hotspot_ar_view_ring_type_idx
on derived.hotspot_acquisition_routes_view (
    ring_type
);
create index if not exists hotspot_ar_view_commodity_sym_idx
on derived.hotspot_acquisition_routes_view (
    hotspot_commodity_sym
);
create index if not exists hotspot_ar_view_station_name_idx
on derived.hotspot_acquisition_routes_view (
    station_name
);
create index if not exists hotspot_ar_view_sell_price_idx
on derived.hotspot_acquisition_routes_view (
    sell_price
);
create index if not exists hotspot_ar_view_demand_idx
on derived.hotspot_acquisition_routes_view (
    demand
);
create index if not exists hotspot_ar_view_market_updated_at_idx
on derived.hotspot_acquisition_routes_view (
    market_updated_at
);
