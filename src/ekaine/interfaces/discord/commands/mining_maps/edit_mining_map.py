import traceback
from pprint import pformat
from typing import Any, cast

from interactions import (
    AutocompleteContext,
    OptionType,
    SlashContext,
    slash_option,
)
from sqlalchemy import CursorResult

from ekaine.common.logging import get_logger
from ekaine.interfaces.discord import discord_handler_wrapper, ephemeral_option
from ekaine.interfaces.discord.commands.mining_maps import (
    cmd_group,
    ekaine_bot_superuser_check,
    log_and_send_error_embed,
    mining_maps_diff_to_embed,
)
from ekaine.postgresql import SessionLocalEkaine
from ekaine.postgresql.adapter import MiningMapsAdapter, RingsAdapter, SystemsAdapter
from ekaine.postgresql.db import MiningMapCommoditiesDB, MiningMapsDB
from ekaine.postgresql.utils import upsert_all

logger = get_logger(__name__)


@cmd_group.subcommand(sub_cmd_name="edit", sub_cmd_description="Edit an existing mining map")
@ekaine_bot_superuser_check()
@slash_option(
    name="map_name_to_edit",
    description="Current name of the map to edit.",
    required=True,
    opt_type=OptionType.STRING,
    autocomplete=True,
)
@slash_option(
    name="system_name",
    description="Overwrite the system the mining map is located inside",
    required=False,
    opt_type=OptionType.STRING,
    autocomplete=True,
)
@slash_option(
    name="ring_name",
    description="Overwrite the ring name for the mining map",
    required=False,
    opt_type=OptionType.STRING,
    autocomplete=True,
)
@slash_option(
    name="commodities_comma_list",
    description="Comma-separated list of commodities. Can optionally include tonnage. Eg, 'Platinum:100T,Osmium'",
    required=False,
    opt_type=OptionType.STRING,
)
@slash_option(
    name="mining_map_url",
    description="Overwrite the link to the mining map",
    required=False,
    opt_type=OptionType.STRING,
)
@slash_option(
    name="new_map_name",
    description="Overwrite the map name.",
    required=False,
    opt_type=OptionType.STRING,
)
@slash_option(
    name="rock_count",
    description="Overwrite the length of mining map by number of rocks",
    required=False,
    opt_type=OptionType.NUMBER,
)
@slash_option(
    name="approximate_merits",
    description="Overwrite the approximate merits earned when the map is done solo",
    required=False,
    opt_type=OptionType.NUMBER,
)
@ephemeral_option
@discord_handler_wrapper()
async def edit_mining_map(
    ctx: SlashContext,
    map_name_to_edit: str,
    system_name: str | None = None,
    ring_name: str | None = None,
    commodities_comma_list: str | None = None,
    mining_map_url: str | None = None,
    new_map_name: str | None = None,
    rock_count: int | None = None,
    approximate_merits: int | None = None,
    ephemeral: bool = True,
) -> None:
    with SessionLocalEkaine() as session:
        try:
            with MiningMapsAdapter(session) as adapter:
                old_map = adapter.get_mining_map(map_name_to_edit)
                session.expunge(old_map)  # Don't autoupdate old_map's attributes when we update it in the DB later on.
        except ValueError:
            return await log_and_send_error_embed(ctx, f"No map named “{map_name_to_edit}”")

        if system_name:
            try:
                with SystemsAdapter(session) as adapter:
                    system = adapter.get_system(system_name)
            except ValueError:
                return await log_and_send_error_embed(ctx, f"No system named “{system_name}”")
        else:
            system = old_map.system

        if ring_name:
            try:
                with RingsAdapter(session) as adapter:
                    ring = adapter.get_ring_by_system_and_name(system or old_map.system, ring_name)
            except ValueError:
                return await log_and_send_error_embed(
                    ctx, f"No ring “{ring_name}” in {(system or old_map.system).name}"
                )
        elif system_name:
            return await log_and_send_error_embed(ctx, "If changing system, you must also supply a ring_name")
        else:
            ring = old_map.ring

        map_name = map_name_to_edit if new_map_name is None else new_map_name
        payload = MiningMapsDB.to_dict_from_discord(
            system,
            ring,
            map_name,
            old_map.map_url if mining_map_url is None else mining_map_url,
            old_map.rock_count if rock_count is None else rock_count,
            old_map.approximate_merits_solo if approximate_merits is None else approximate_merits,
        )

        with MiningMapsAdapter(session) as adapter:
            result = adapter.update_mining_map(old_map.id, payload)
            if cast(CursorResult[Any], result).rowcount != 1:
                return await log_and_send_error_embed(ctx, "Failed to update the mining map")

        # This explicit get loads the foreign key relationships as well
        with MiningMapsAdapter(session) as adapter:
            updated_map = adapter.get_mining_map(map_name)

        if commodities_comma_list:
            comm_payloads = MiningMapCommoditiesDB.to_dicts_from_discord(updated_map, commodities_comma_list)
            inserted = upsert_all(session, MiningMapCommoditiesDB, comm_payloads)
            if not inserted:
                return await log_and_send_error_embed(ctx, "Failed to upsert map commodities")

        diff_embed = mining_maps_diff_to_embed(old_map, updated_map)
        await ctx.send(embeds=[diff_embed], ephemeral=ephemeral)


@edit_mining_map.autocomplete("map_name_to_edit")
@discord_handler_wrapper(choices=[])
async def autocomplete_map_name_to_edit(ctx: AutocompleteContext) -> None:
    substring_input = ctx.input_text

    try:
        with MiningMapsAdapter() as adapter:
            mining_maps = adapter.get_mining_maps_by_filters(mining_map_substring=substring_input)
    except Exception:
        logger.warning(traceback.format_exc())
        return await ctx.send(choices=[])

    choices: list[str] = []
    logger.info(pformat(mining_maps))
    for mining_map in mining_maps:
        val = mining_map.name
        if val:
            choices.append(val)

    await ctx.send(
        choices=choices[:25],
    )


@edit_mining_map.autocomplete("system_name")
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


@edit_mining_map.autocomplete("ring_name")
async def autocomplete_ring_name(ctx: AutocompleteContext) -> None:
    map_to_edit = ctx.kwargs.get("map_name_to_edit")
    system_name = ctx.kwargs.get("system_name")

    if not system_name and map_to_edit:
        try:
            with MiningMapsAdapter() as adapter:
                existing_mining_map = adapter.get_mining_map(map_to_edit)
            system = existing_mining_map.system
        except ValueError:
            return await ctx.send(choices=[])
    elif system_name:
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
