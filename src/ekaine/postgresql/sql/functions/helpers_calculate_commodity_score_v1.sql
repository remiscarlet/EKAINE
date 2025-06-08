drop function if exists helpers.calculate_commodity_score;
create or replace function helpers.calculate_commodity_score(
    price int,
    supplydemand int
)
returns int
as $$
    select (power(price, 0.98) * power(supplydemand, 0.02))::int;
$$ language sql;
