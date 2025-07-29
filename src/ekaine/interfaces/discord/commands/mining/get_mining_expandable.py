from pprint import pformat

from interactions import Embed, OptionType, SlashContext, slash_option

from ekaine.common.logging import get_logger
from ekaine.interfaces.discord import (
    MineableDataDisplay,
    ephemeral_option,
    send_error_embed,
)
from ekaine.interfaces.discord.commands.mining import cmd_group
from ekaine.postgresql.adapter import (
    ApiCommandAdapter,
    SystemsAdapter,
)

logger = get_logger(__name__)


@cmd_group.subcommand(
    sub_cmd_name="get-expandable", sub_cmd_description="Get list of mining routes for acquiring a target system"
)
@slash_option(
    name="system_name", description="Target system name to acquire", required=True, opt_type=OptionType.STRING
)
@ephemeral_option
async def get_mining_expandable(ctx: SlashContext, system_name: str, ephemeral: bool = True) -> None:
    await ctx.defer(ephemeral=ephemeral)

    try:
        with SystemsAdapter() as adapter:
            system = adapter.get_system(system_name)
    except ValueError:
        await send_error_embed(ctx, f"Could not find system '{system_name}'!")
        return

    if system.power_state != "Unoccupied":
        await send_error_embed(ctx, f"System '{system_name}' is not unoccupied!")
        return

    if "Nakato Kaine" not in (system.powers or []):
        await send_error_embed(
            ctx, f"Unoccupied system '{system_name}' is not within Councillor Kaine's sphere of influence!"
        )
        return

    with ApiCommandAdapter() as adapter:
        routes = adapter.get_mining_expandable_systems_in_range(system_name)

    mineable_data: dict[str, MineableDataDisplay] = {}
    for route in routes:
        name = route.commodity_sym
        if name not in mineable_data:
            mineable_data[name] = MineableDataDisplay(name)
        mineable_data[name].add_route(route)

    logger.info(pformat(mineable_data))

    embeds: list[Embed] = []
    for name, data in mineable_data.items():
        mine_in = "**Mine In:**\n"
        for ring in data.mineable_rings:
            mine_in += f"-> {ring}\n"

        embed = Embed(
            title=f"{name} Mining Routes - Acquiring {system_name}",
            description=mine_in,
            color=0x3498DB,
        )

        embed.add_field("---------", "**Sell At:**")

        for station_price in data.sell_stations:
            embed.add_field(
                f"{station_price.station} ({system_name})",
                f"{station_price.price:3,} CR w/ {station_price.demand:3,} Dem",
            )

        embeds.append(embed)

    embeds.sort(key=lambda e: e.title or "")
    await ctx.send(embeds=embeds[:10], ephemeral=ephemeral)
