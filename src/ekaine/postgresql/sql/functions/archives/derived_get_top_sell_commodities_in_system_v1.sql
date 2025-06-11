drop function if exists derived.get_top_sell_commodities_in_system;
create or replace function derived.get_top_sell_commodities_in_system(
    p_system_name text,
    p_number_commodities integer,
    p_min_demand integer
)
returns table (
    system_name text,
    station_name text,
    type text,
    distance_to_arrival float,
    commodity_sym text,
    sell_price integer,
    demand integer,
    buy_price integer,
    supply integer,
    updated_at timestamp,
    rank bigint
) as $$
    select
        r.system_name,
        r.station_name,
        r.type,
        r.distance_to_arrival,
        r.commodity_sym,
        r.sell_price,
        r.demand,
        r.buy_price,
        r.supply,
        r.updated_at,
        r.rank
    from (
        select
            sc.system_name,
            sc.station_name,
            sc.type,
            sc.distance_to_arrival,
            sc.commodity_sym,
            sc.sell_price,
            sc.demand,
            sc.buy_price,
            sc.supply,
            sc.updated_at,
            dense_rank() over (
                partition by sc.station_name
                order by derived.calculate_commodity_score(sc.sell_price, sc.demand) desc
            ) as rank
        from derived.station_commodities_view sc
        where sc.system_name = p_system_name
        and sc.demand >= p_min_demand
    ) r
    where r.rank <= p_number_commodities
$$ language sql;
