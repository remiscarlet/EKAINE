from pprint import pformat
from typing import Any, Callable

from interactions import (
    BaseContext,
    OptionType,
    SlashContext,
    check,
    slash_option,
)
from interactions.ext.paginators import Paginator

from ekaine.common.logging import get_logger
from ekaine.interfaces.discord import send_error_embed
from ekaine.interfaces.discord.commands.mining_maps import (
    cmd_group,
    mining_map_to_embed,
)
from ekaine.postgresql.adapter import MiningMapsAdapter

logger = get_logger(__name__)

allowlisted_discord_usernames = [
    "remiscarlet",
]


def my_check() -> Callable[[Any], Any]:
    async def predicate(ctx: BaseContext) -> bool:
        logger.info(pformat(ctx))
        logger.info(pformat(ctx.author))
        return ctx.author.username in allowlisted_discord_usernames

    return check(predicate)


@cmd_group.subcommand(
    sub_cmd_name="list",
    sub_cmd_description="List known Mining Maps. Filters are additive. All options are case insensitive",
)
@my_check()
@slash_option(
    name="system_name_substring",
    description="Filter by mining map(s) in systems matching substring",
    required=False,
    opt_type=OptionType.STRING,
)
@slash_option(
    name="commodities_comma_list",
    description="Filter by comma separated list of commodities in the map. Eg, 'Platinum,Osmium'",
    required=False,
    opt_type=OptionType.STRING,
)
@slash_option(
    name="map_name_substring",
    description="Filter by map name substring",
    required=False,
    opt_type=OptionType.STRING,
)
@slash_option(
    name="page_number",
    description="Pagination page number if there's more than one 'page' of results.",
    required=False,
    opt_type=OptionType.INTEGER,
)
async def list_mining_maps(
    ctx: SlashContext,
    system_name_substring: str | None = None,
    commodities_comma_list: str | None = None,
    map_name_substring: str | None = None,
    page_number: int = 1,
) -> None:
    mining_maps, _ = MiningMapsAdapter().get_mining_maps_by_filters(
        system_name_substring, map_name_substring, commodities_comma_list, page_number, page_size=10
    )

    if not mining_maps:
        return await send_error_embed(ctx, "Could not find any mining maps matching ALL of the supplied filters!")

    embeds = []
    for mining_map in mining_maps:
        embed = mining_map_to_embed(mining_map)
        if len(mining_maps) > 25:
            embed.add_field(
                "\u200b",  # "blank" string
                "Note: The dropdown below is limited to 25 options by the Discord API",
                inline=False,
            )
        embeds.append(embed)

    paginator = Paginator.create_from_embeds(ctx.client, *embeds)
    paginator.show_select_menu = True

    await paginator.send(ctx, ephemeral=True)
