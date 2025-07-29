drop function if exists api.get_mining_expandable_systems_in_range;
create or replace function api.get_mining_expandable_systems_in_range(
    p_unoccupied_system_name TEXT
)
returns table (
    expanding_system TEXT,
    ring_name TEXT,
    commodity TEXT,
    unoccupied_system TEXT,
    station_name TEXT,
    sell_price INT,
    demand INT
) as $$
BEGIN
    return query
    with hotspots_in_expandable_systems_in_range as (
        select
            sy.name as system_name,
            b.name as body_name,
            r.name as ring_name,
            hs.commodity_sym as commodity
        from derived.get_expandable_systems_in_range(p_unoccupied_system_name) sy
        inner join core.bodies b
        on sy.id = b.system_id
        inner join core.rings r
        on b.id = r.body_id
        inner join core.hotspots hs
        on r.id = hs.ring_id
        inner join core.commodities c
        on hs.commodity_sym = c.symbol
        where r.type = any(c.ring_types)
    ), top_sell_commodities_in_target_system as (
        select
            c.system_name,
            c.station_name,
            c.type,
            c.distance_to_arrival,
            c.commodity_sym as commodity,
            c.sell_price,
            c.demand,
            c.buy_price,
            c.supply,
            c.updated_at,
            c.rank
        from derived.get_top_sell_commodities_in_system(p_unoccupied_system_name, 15, 1) c
    )
    select
        es.system_name as expanding_system,
        es.ring_name as ring_name,
        es.commodity as commodity,
        ts.system_name as unoccupied_system,
        ts.station_name as station_name,
        ts.sell_price as sell_price,
        ts.demand as demand
    from top_sell_commodities_in_target_system ts
    inner join hotspots_in_expandable_systems_in_range es
    on ts.commodity = es.commodity;
END;
$$ language plpgsql;
