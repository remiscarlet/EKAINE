drop function if exists api.get_top_mining_reinforcement_routes;
create or replace function api.get_top_reinforcement_mining_routes(
    p_power_name text,
    p_power_states text [],
    p_commodity_names text [],
    p_ignored_ring_types text [],
    p_min_sell_price int,
    p_min_demand int,
    p_results int,
    p_max_data_age_interval text
)
returns table (
    system_name text,
    body_name text,
    ring_name text,
    ring_type text,
    commodity text,
    count int,
    power_state text,
    station_name text,
    distance_to_arrival float,
    sell_price int,
    demand int,
    updated_at timestamp
) as $$
BEGIN
    return query
    select
        hrv.system_name,
        hrv.body_name,
        hrv.ring_name,
        hrv.ring_type,
        hrv.commodity,
        hrv.count,
        s.power_state,
        scv.station_name,
        scv.distance_to_arrival,
        scv.sell_price,
        scv.demand,
        scv.updated_at
      from derived.get_systems_with_power_and_state(p_power_name, p_power_states) s
      join derived.hotspot_ring_view hrv
        on s.name = hrv.system_name
      join derived.station_commodities_view scv
        on hrv.system_name = scv.system_name
       and hrv.commodity = scv.commodity_sym
     where hrv.commodity = any(p_commodity_names)
       and not hrv.ring_type = any(p_ignored_ring_types)
       and scv.sell_price > p_min_sell_price -- Eventually make this % of galactic average per comm?
       and scv.demand > p_min_demand
       and scv.updated_at >= now() - p_max_data_age_interval::interval
     order by scv.updated_at desc
     limit p_results;
END;
$$ language plpgsql;
