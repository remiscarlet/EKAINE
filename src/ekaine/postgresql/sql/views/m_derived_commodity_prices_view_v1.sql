-- Rolling average prices for all commodities on a monthly window

drop materialized view if exists derived.commodity_prices_view;
create materialized view derived.commodity_prices_view as
select
    c.symbol,
    avg(mc.sell_price) as avg_sell,
    avg(mc.buy_price) as avg_buy,
    transaction_timestamp() as refreshed_at
from core.commodities as c
inner join core.market_commodities as mc on c.symbol = mc.commodity_sym
where now() - mc.updated_at <= '1 month'::interval
group by c.symbol;

-- Create an index directly in the SQL,
-- since we don't have a SA2.0 class table definition to define the index on.
create unique index
if not exists commodity_prices_view_symbol_idx
on derived.commodity_prices_view (
    symbol
);
