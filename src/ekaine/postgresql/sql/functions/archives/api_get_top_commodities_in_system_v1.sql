create or replace function api.get_top_commodities_in_system(
    p_system_name text,
    p_number_commodities integer,
    p_min_supplydemand integer,
    p_is_buying boolean
)
returns table (
    system_name text,
    station_name text,
    station_type text,
    distance_to_arrival float,
    commodity text,
    sell_price integer,
    demand integer,
    buy_price integer,
    supply integer,
    updated_at timestamp,
    rank bigint
) as $$
declare
    func_name text := case
        when p_is_buying then 'derived.get_top_buy_commodities_in_system'
        else 'derived.get_top_sell_commodities_in_system'
    end;
    sql text;
begin
    sql := format($f$
        select
            r.system_name,
            r.station_name,
            r.type as station_type,
            r.distance_to_arrival,
            r.commodity_sym as commodity,
            r.sell_price,
            r.demand,
            r.buy_price,
            r.supply,
            r.updated_at,
            r.rank
        from %s(%L, %s, %s) r
    $f$,
        func_name,
        p_system_name,
        p_number_commodities,
        p_min_supplydemand
    );

    return query execute sql;
end;
$$ language plpgsql;
