drop function if exists derived.calculate_commodity_score;
create or replace function derived.calculate_commodity_score(
    price int,
    supplydemand int
)
returns int
as $$
    ----------------
    -- Deprecated --
    ----------------
    --
    -- Use helpers.calculate_commodity_score
    --
    select (power(price, 0.98) * power(supplydemand, 0.02))::int;
$$ language sql;
