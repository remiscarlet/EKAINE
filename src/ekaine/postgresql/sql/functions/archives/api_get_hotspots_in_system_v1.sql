drop function if exists api.get_hotspots_in_system;
create or replace function api.get_hotspots_in_system(
    p_system_name text
) returns table (
    system_name text,
    body_name text,
    ring_name text,
    ring_type text,
    commodity text,
    count integer
)
as $$
begin
    return query
    select
        h.system_name,
        h.body_name,
        h.ring_name,
        h.ring_type,
        h.commodity,
        h.count
      from derived.hotspot_ring_view h
     where h.system_name = p_system_name;
end;
$$ language plpgsql;
