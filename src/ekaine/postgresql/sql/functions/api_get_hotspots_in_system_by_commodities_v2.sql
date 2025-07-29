drop function if exists api.get_hotspots_in_system_by_commodities(
    text, text []
);
create or replace function api.get_hotspots_in_system_by_commodities(
    p_system_name text,
    commodities text []
) returns table (
    system_name text,
    body_name text,
    ring_name text,
    ring_type text,
    commodity_sym text,
    hotspot_count integer
)
as $$
begin
    return query
    select
        h.system_name,
        h.body_name,
        h.ring_name,
        h.ring_type,
        h.commodity_sym,
        h.hotspot_count
      from derived.hotspot_ring_view h
      join core.commodities c
        on h.commodity_sym = c.symbol
     where h.system_name = p_system_name
       and c.symbol=any(commodities);
end;
$$ language plpgsql;
