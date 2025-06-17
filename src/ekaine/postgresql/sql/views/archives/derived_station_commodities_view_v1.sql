drop view if exists derived.station_commodities_view;
create or replace view derived.station_commodities_view as
select
    sy.name as system_name,
    st.name as station_name,
    st.type,
    st.distance_to_arrival,
    mc.commodity_sym,
    mc.sell_price,
    mc.demand,
    mc.buy_price,
    mc.supply,
    mc.updated_at
from core.market_commodities as mc
inner join derived.resolved_stations_view as st on mc.station_id = st.id
left join core.systems as sy
    on st.system_id = sy.id
where mc.supply > 0 or mc.demand > 0;
