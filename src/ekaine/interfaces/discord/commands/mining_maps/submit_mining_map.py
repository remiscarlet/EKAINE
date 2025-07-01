import traceback
from pprint import pformat
from typing import Any, Callable, cast

from interactions import (
    AutocompleteContext,
    BaseContext,
    Embed,
    OptionType,
    SlashContext,
    check,
    slash_option,
)

from ekaine.common.logging import get_logger
from ekaine.interfaces.discord import send_error_embed
from ekaine.interfaces.discord.commands.mining_maps import cmd_group
from ekaine.postgresql import SessionLocalEkaine
from ekaine.postgresql.adapter import RingsAdapter, SystemsAdapter
from ekaine.postgresql.db import MiningMapCommoditiesDB, MiningMapsDB
from ekaine.postgresql.utils import upsert_all

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
    map_name: str | None = None,
    rock_count: int | None = None,
    approximate_merits: int | None = None,
) -> None:
    coalesced_map_name = map_name if map_name is not None else ring_name

    try:
        system = SystemsAdapter().get_system(system_name)
    except ValueError:
        msg = f"Could not find a system with name '{system_name}'!"
        logger.warning(msg)
        return await send_error_embed(ctx, msg)

    try:
        ring = RingsAdapter().get_ring(ring_name)
    except ValueError:
        msg = f"Could not find a ring with name '{ring_name}'!"
        logger.warning(msg)
        return await send_error_embed(ctx, msg)

    try:
        # Check if commodities list is valid before making any DB entries
        map_commodities = MiningMapCommoditiesDB.parse_commodities_str(commodities_comma_list)
    except ValueError as e:
        msg = str(e)
        logger.warning(msg)
        return await send_error_embed(ctx, msg)

    mining_map_dict = MiningMapsDB.to_dict_from_discord(
        system,
        ring,
        coalesced_map_name,
        mining_map_url,
        rock_count,
        approximate_merits,
    )

    db_session = SessionLocalEkaine()
    mining_map_objs = upsert_all(db_session, MiningMapsDB, [mining_map_dict])
    if not mining_map_objs:
        msg = "Didn't get back a MiningMapsDB object from upsert_all! Aborting."
        logger.warning(msg)
        return await send_error_embed(ctx, msg)
    mining_map_obj = mining_map_objs[0]

    mining_map_commodity_dicts = MiningMapCommoditiesDB.to_dicts_from_discord(mining_map_obj, commodities_comma_list)
    mining_map_objs = upsert_all(db_session, MiningMapCommoditiesDB, mining_map_commodity_dicts)  # type: ignore
    if not mining_map_objs:
        msg = "Didn't get back any MiningMapCommoditiesDB objects from upsert_all! Aborting."
        logger.warning(msg)
        return await send_error_embed(ctx, msg)

    description = f"""
    System Name: `{system.name}`
    Ring Name: `{ring.name}`
    Map Name: `{coalesced_map_name}`
    Rock Count: `{rock_count}`
    Approximate Merits: `{approximate_merits}`
    Commodities:
    """
    for commodity in map_commodities:
        name, tonnage = commodity
        if tonnage is not None:
            description += f"- `{name}` ({tonnage}T)\n"
        else:
            description += f"- `{name}`\n"

    embed = Embed(
        title="Mining Map Successfully Submitted!",
        description=description,
        color=0x3498DB,
    )
    await ctx.send(embeds=[embed])


@submit_mining_map.autocomplete("system_name")
async def autocomplete_system_name(ctx: AutocompleteContext) -> None:
    substring_input = ctx.input_text  # can be empty/None

    # Min 3 chars to start autocomplete
    if len(substring_input) < 3:
        return await ctx.send(choices=[])

    try:
        db_systems = SystemsAdapter().get_system_by_substring(substring_input)
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

    substring_input = ctx.input_text  # can be empty/None
    try:
        db_rings = RingsAdapter().get_rings_by_system_and_substring(system, substring_input)
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
