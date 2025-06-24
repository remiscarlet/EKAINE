import traceback
from pprint import pformat
from typing import Any, Callable, cast

from interactions import (
    AutocompleteContext,
    BaseContext,
    OptionType,
    SlashContext,
    check,
    slash_option,
)

from ekaine.common.logging import get_logger
from ekaine.interfaces.discord import send_error_embed
from ekaine.interfaces.discord.commands.mining_maps import cmd_group
from ekaine.postgresql.adapter import RingsAdapter, SystemsAdapter

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


@cmd_group.subcommand(sub_cmd_name="submit", sub_cmd_description="Submit a new Mining map")
@my_check()
@slash_option(
    name="system_name",
    description="System the mining map is located inside",
    required=True,
    opt_type=OptionType.STRING,
    autocomplete=True,
)
@slash_option(
    name="ring_name",
    description="Ring name for the mining map",
    required=True,
    opt_type=OptionType.STRING,
    autocomplete=True,
)
@slash_option(
    name="commodities_comma_list",
    description="Comma separated list of commodities included in the map. Eg, 'Platinum,Osmium'",
    required=True,
    opt_type=OptionType.STRING,
)
@slash_option(
    name="mining_map_url",
    description="Link to the mining map",
    required=True,
    opt_type=OptionType.STRING,
)
@slash_option(
    name="map_name",
    description="Mining map name. Defaults to ring name.",
    required=False,
    opt_type=OptionType.STRING,
)
@slash_option(
    name="rock_count",
    description="Length of mining map by number of rocks",
    required=False,
    opt_type=OptionType.NUMBER,
)
@slash_option(
    name="approximate_merits",
    description="Length of mining map by number of rocks",
    required=False,
    opt_type=OptionType.NUMBER,
)
async def submit_mining_map(
    ctx: SlashContext,
    system_name: str,
    ring_name: str,
    commodities_comma_list: str,
    mining_map_url: str,
    map_name: str | None,
    rock_count: int | None,
    approximate_merits: int | None,
) -> None:
    coalesced_map_name = map_name if map_name is not None else ring_name
    commodities = list(map(lambda s: s.strip(), commodities_comma_list.split(",")))
    await send_error_embed(
        ctx,
        (
            f"Unimplemented! {system_name}-{ring_name}-{commodities}-{mining_map_url}"
            f"-{coalesced_map_name}-{rock_count}-{approximate_merits}"
        ),
    )


@submit_mining_map.autocomplete("system_name")
async def autocomplete_system_name(ctx: AutocompleteContext) -> None:
    prefix_input = ctx.input_text  # can be empty/None

    # Min 3 chars to start autocomplete
    if len(prefix_input) < 3:
        return await ctx.send(choices=[])

    try:
        db_systems = SystemsAdapter().get_system_by_prefix(prefix_input)
    except Exception:
        logger.warning(traceback.format_exc())
        return await ctx.send(choices=[])

    choices: list[str] = []
    for system in db_systems:
        val = system.name
        if val:
            choices.append(val)

    await ctx.send(
        choices=choices[:25],
    )


@submit_mining_map.autocomplete("ring_name")
async def autocomplete_ring_name(ctx: AutocompleteContext) -> None:
    system_name = ctx.kwargs.get("system_name")
    if not system_name:
        return await ctx.send(choices=[])

    try:
        system = SystemsAdapter().get_system(cast(str, system_name))
    except Exception:
        logger.warning(traceback.format_exc())
        return await ctx.send(choices=[])

    prefix_input = ctx.input_text  # can be empty/None
    try:
        db_rings = RingsAdapter().get_rings_by_system_and_substring(system, prefix_input)
        logger.info(pformat(db_rings))
    except Exception:
        logger.warning(traceback.format_exc())
        return await ctx.send(choices=[])

    choices: list[str] = []
    for ring in db_rings:
        val = ring.name
        if val:
            choices.append(val)

    await ctx.send(
        choices=choices[:25],
    )
