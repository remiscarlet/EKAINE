-- This is a helper view.
-- "Potential" determined by valid system power states.
-- Ie, Stronghold/Fortified systems in range of Unoccupied systems with Kaine influence.
-- "Potential" because this view does not account for hotspot/mining map viability.

drop view if exists derived.potential_acquisition_routes_view;
create view derived.potential_acquisition_routes_view as
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
        s.powers @> array['Nakato Kaine']
        and s.power_state = 'Unoccupied'
)

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
