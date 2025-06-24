drop function if exists derived.get_bodies_in_system;
create or replace function derived.get_bodies_in_system(
    p_system_id int
)
returns table (
    id int,
    id64 bigint,
    name text,
    body_id int,
    type text,
    mass float,
    inner_radius float,
    outer_radius float
) as $$
    select
        r.id, r.id64, r.name, r.body_id, r.type, r.mass,
        r.inner_radius, r.outer_radius
    from core.rings r
    join core.bodies b on b.id = r.body_id
    join core.systems s on s.id = b.system_id
    where s.id = p_system_id
$$ language sql;
