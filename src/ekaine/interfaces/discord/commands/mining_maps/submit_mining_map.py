import traceback
from pprint import pformat
from typing import cast

from interactions import (
    AutocompleteContext,
    OptionType,
    SlashContext,
    slash_option,
)

from ekaine.common.logging import get_logger
from ekaine.interfaces.discord import discord_handler_wrapper, ephemeral_option
from ekaine.interfaces.discord.commands.mining_maps import (
    cmd_group,
    ekaine_bot_superuser_check,
    log_and_send_error_embed,
    mining_map_to_embed,
)
from ekaine.postgresql import SessionLocalEkaine
from ekaine.postgresql.adapter import RingsAdapter, SystemsAdapter
from ekaine.postgresql.db import MiningMapCommoditiesDB, MiningMapsDB
from ekaine.postgresql.utils import upsert_all

logger = get_logger(__name__)


@cmd_group.subcommand(sub_cmd_name="submit", sub_cmd_description="Submit a new Mining map")
@ekaine_bot_superuser_check()
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
    description="Comma-separated list of commodities. Can optionally include tonnage. Eg, 'Platinum:100T,Osmium'",
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
    description="The approximate merits earned when the map is done solo",
    required=False,
    opt_type=OptionType.NUMBER,
)
@ephemeral_option
@discord_handler_wrapper()
async def submit_mining_map(
    ctx: SlashContext,
    system_name: str,
    ring_name: str,
    commodities_comma_list: str,
    mining_map_url: str,
    map_name: str | None = None,
    rock_count: int | None = None,
    approximate_merits: int | None = None,
    ephemeral: bool = True,
) -> None:
    coalesced_map_name = map_name if map_name is not None else ring_name

    try:
        with SystemsAdapter() as adapter:
            system = adapter.get_system(system_name)
    except ValueError:
        return await log_and_send_error_embed(ctx, f"Could not find a system with name '{system_name}'!")

    try:
        with RingsAdapter() as adapter:
            ring = adapter.get_ring(ring_name)
    except ValueError:
        return await log_and_send_error_embed(ctx, f"Could not find a ring with name '{ring_name}'!")

    try:
        MiningMapCommoditiesDB.parse_commodities_str(commodities_comma_list)
    except ValueError as e:
        return await log_and_send_error_embed(ctx, str(e))

    mining_map_dict = MiningMapsDB.to_dict_from_discord(
        system,
        ring,
        coalesced_map_name,
        mining_map_url,
        rock_count,
        approximate_merits,
    )

    with SessionLocalEkaine() as session:
        mining_maps = upsert_all(session, MiningMapsDB, [mining_map_dict])
        if not mining_maps:
            return await log_and_send_error_embed(
                ctx, "Didn't get back a MiningMapsDB object from upsert_all! Aborting."
            )

        mining_map = mining_maps[0]

        mining_map_commodity_dicts = MiningMapCommoditiesDB.to_dicts_from_discord(mining_map, commodities_comma_list)
        mining_map_commodities = upsert_all(session, MiningMapCommoditiesDB, mining_map_commodity_dicts)
        if not mining_map_commodities:
            return await log_and_send_error_embed(
                ctx, "Didn't get back any MiningMapCommoditiesDB objects from upsert_all! Aborting."
            )

        embed = mining_map_to_embed(mining_map)
        await ctx.send(embeds=[embed], ephemeral=ephemeral)


@submit_mining_map.autocomplete("system_name")
@discord_handler_wrapper(choices=[])
async def autocomplete_system_name(ctx: AutocompleteContext) -> None:
    substring_input = ctx.input_text  # can be empty/None

    # Min 3 chars to start autocomplete
    if len(substring_input) < 3:
        return await ctx.send(choices=[])

    try:
        with SystemsAdapter() as adapter:
            systems = adapter.get_system_by_substring(substring_input)
    except Exception:
        logger.warning(traceback.format_exc())
        return await ctx.send(choices=[])

    choices: list[str] = []
    for system in systems:
        val = system.name
        if val:
            choices.append(val)

    await ctx.send(
        choices=choices[:25],
    )


@submit_mining_map.autocomplete("ring_name")
@discord_handler_wrapper(choices=[])
async def autocomplete_ring_name(ctx: AutocompleteContext) -> None:
    system_name = ctx.kwargs.get("system_name")
    if not system_name:
        return await ctx.send(choices=[])

    try:
        with SystemsAdapter() as adapter:
            system = adapter.get_system(cast(str, system_name))
    except Exception:
        logger.warning(traceback.format_exc())
        return await ctx.send(choices=[])

    substring_input = ctx.input_text  # can be empty/None
    try:
        with RingsAdapter() as adapter:
            rings = adapter.get_rings_by_system_and_substring(system, substring_input)
        logger.info(pformat(rings))
    except Exception:
        logger.warning(traceback.format_exc())
        return await ctx.send(choices=[])

    choices: list[str] = []
    for ring in rings:
        val = ring.name
        if val:
            choices.append(val)

    await ctx.send(
        choices=choices[:25],
    )
