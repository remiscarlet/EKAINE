from collections import defaultdict
from pprint import pformat

from interactions import Embed, OptionType, SlashContext, slash_option
from tabulate import tabulate

from ekaine.common.logging import get_logger
from ekaine.common.utils import get_time_since
from ekaine.interfaces.discord import (
    discord_handler_wrapper,
    ephemeral_option,
    send_error_embed,
)
from ekaine.interfaces.discord.commands.mining import cmd_group
from ekaine.interfaces.discord.utils import split_comma_delimited_string
from ekaine.postgresql.adapter import (
    ApiCommandAdapter,
)
from ekaine.postgresql.types import MiningReinforcementResult

logger = get_logger(__name__)


@cmd_group.subcommand(
    sub_cmd_name="get-top-reinf-routes", sub_cmd_description="Get top N mining reinforcement routes in the galaxy"
)
@slash_option(name="power_name", description="Power to query for", required=False, opt_type=OptionType.STRING)
@slash_option(
    name="power_states",
    description="Comma delimited string of power states, eg 'Exploited,Fortified'",
    required=False,
    opt_type=OptionType.STRING,
)
@slash_option(
    name="commodity_names",
    description="Comma delimited string of commodities, eg 'Monazite,Platinum'",
    required=False,
    opt_type=OptionType.STRING,
)
@slash_option(
    name="ignored_ring_types",
    description="Comma delimited string of ring types to ignore, eg 'Metal Rich'",
    required=False,
    opt_type=OptionType.STRING,
)
@slash_option(
    name="min_sell_price",
    description="Minimum sell price for commodity",
    required=False,
    opt_type=OptionType.INTEGER,
)
@slash_option(
    name="min_demand",
    description="Minimum demand for commodity at the station",
    required=False,
    opt_type=OptionType.INTEGER,
)
@slash_option(
    name="num_results",
    description="Number of results to list",
    required=False,
    opt_type=OptionType.INTEGER,
)
@slash_option(
    name="max_data_age_dur_str",
    description="Max age of data. Format eg, '1w3d10h30m'",
    required=False,
    opt_type=OptionType.STRING,
)
@ephemeral_option
@discord_handler_wrapper()
async def get_top_reinforcement_mining_routes(
    ctx: SlashContext,
    power_name: str = "Nakato Kaine",
    power_states: str = "Exploited, Fortified",
    commodity_names: str = "Monazite, Platinum",
    ignored_ring_types: str = "Metal Rich",
    min_sell_price: int = 50000,
    min_demand: int = 10,
    num_results: int = 25,
    max_data_age_dur_str: str = "3d",
    ephemeral: bool = True,
) -> None:
    await ctx.defer(ephemeral=ephemeral)

    with ApiCommandAdapter() as adapter:
        mining_routes = adapter.get_top_reinforcement_mining_routes(
            power_name,
            split_comma_delimited_string(power_states),
            split_comma_delimited_string(commodity_names),
            split_comma_delimited_string(ignored_ring_types),
            min_sell_price,
            min_demand,
            num_results,
            max_data_age_dur_str,
        )

    if not mining_routes:
        await send_error_embed(ctx, "Uh oh, the provided arguments didn't find any valid results!")
        return

    routes_by_system: dict[str, list[MiningReinforcementResult]] = defaultdict(lambda: list())
    for route in mining_routes:
        system = route.system_name
        routes_by_system[system].append(route)

    logger.info(pformat(routes_by_system))

    table_headers = ["Station Name", "Distance", "Price/Demand"]
    embeds: list[Embed] = []
    for system_name in sorted(routes_by_system.keys()):
        routes = routes_by_system[system_name]

        rings = set()
        routes_by_commodity: dict[str, list[MiningReinforcementResult]] = defaultdict(lambda: list())
        for route in routes:
            rings.add(f"{route.ring_name} ({route.ring_type})")
            commodity = route.commodity_sym
            routes_by_commodity[commodity].append(route)

        for commodity in sorted(routes_by_commodity.keys()):
            routes = routes_by_commodity[commodity]

            desc = "**Mine In:**\n"
            for ring in sorted(list(rings)):
                desc += f"-> {ring}\n"
            desc += "\n"

            commodity_rows = list(
                set(
                    map(
                        lambda r: (
                            r.station_name,
                            f"{r.distance_to_arrival:3,.2f} LS",
                            f"{r.sell_price:3,} CR / {r.demand:3,} Dem",
                        ),
                        routes,
                    )
                )
            )
            logger.info(tabulate(commodity_rows, headers=table_headers))
            desc += "**Sell At:**\n"
            desc += f"```{tabulate(commodity_rows, headers=table_headers)}```\n"

            updated_ats = set()
            for route in routes:
                updated_ats.add(f"-# Station `{route.station_name}` updated {get_time_since(route.updated_at)}")
            desc += "\n".join(list(updated_ats))

            logger.info(f"Desc Len: {len(desc)}")

            power_state = routes[0].power_state
            embed = Embed(
                title=f"**{system_name} ({power_state})** Reinforcement Mining Routes - **{commodity}**",
                description=desc,
                color=0x3498DB,
            )

            embeds.append(embed)

    embeds.sort(key=lambda e: e.title or "")
    await ctx.send(embeds=embeds[:10], ephemeral=ephemeral)
