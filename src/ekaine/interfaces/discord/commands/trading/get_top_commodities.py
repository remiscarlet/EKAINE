from collections import defaultdict
from pprint import pformat

from interactions import Embed, OptionType, SlashContext, slash_option
from tabulate import tabulate

from ekaine.common.logging import get_logger
from ekaine.interfaces.discord import (
    discord_handler_wrapper,
    ephemeral_option,
    send_error_embed,
)
from ekaine.interfaces.discord.commands.trading import cmd_group
from ekaine.postgresql.adapter import (
    ApiCommandAdapter,
    SystemsAdapter,
)
from ekaine.postgresql.types import TopCommodityResult

logger = get_logger(__name__)


@cmd_group.subcommand(
    sub_cmd_name="get-top-commodities",
    sub_cmd_description="Get list of top commodities at each station in a given system",
)
@slash_option(
    name="system_name", description="Target system name to acquire", required=True, opt_type=OptionType.STRING
)
@slash_option(
    name="number_commodities",
    description="Max number of commodities to list per station",
    required=False,
    opt_type=OptionType.INTEGER,
)
@slash_option(
    name="minimum_demand",
    description="Minimum demand for a given commodity to be included in the list",
    required=False,
    opt_type=OptionType.INTEGER,
)
@ephemeral_option
@discord_handler_wrapper()
async def get_top_commodities(
    ctx: SlashContext,
    system_name: str,
    number_commodities: int = 5,
    minimum_demand: int = 1,
    ephemeral: bool = True,
) -> None:
    await ctx.defer(ephemeral=ephemeral)

    try:
        SystemsAdapter().get_system(system_name)
    except ValueError:
        return await send_error_embed(ctx, f"Could not find system '{system_name}'!")

    with ApiCommandAdapter() as adapter:
        commodities = adapter.get_top_commodities_in_system(system_name, number_commodities, minimum_demand, False)

    commodities_by_station: dict[str, list[TopCommodityResult]] = defaultdict(lambda: list())
    for commodity in commodities:
        station = commodity.station_name
        commodities_by_station[station].append(commodity)

    logger.info(pformat(commodities_by_station))

    table_headers = ["Commodity", "Price/Demand"]
    embeds: list[Embed] = []
    for station_name in sorted(commodities_by_station.keys()):
        commodities = commodities_by_station[station_name]

        commodity_rows = list(
            map(lambda c: (c.commodity_sym, f"{c.sell_price:3,} CR / {c.demand:3,} Dem"), commodities)
        )

        logger.info(tabulate(commodity_rows, headers=table_headers))
        desc = tabulate(commodity_rows, headers=table_headers)
        logger.info(f"Desc Len: {len(desc)}")

        embed = Embed(
            title=f"Top Commodities At **{station_name}** ({system_name})",
            description=f"```{desc}```",
            color=0x3498DB,
        )

        embeds.append(embed)

    embeds.sort(key=lambda e: e.title or "")
    await ctx.send(embeds=embeds[:10], ephemeral=ephemeral)
