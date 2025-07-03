from pprint import pformat
from typing import Any, Callable

from interactions import BaseContext, Embed, EmbedField, SlashContext, check

from ekaine.common.logging import get_logger
from ekaine.interfaces.discord import cmd_base, send_error_embed
from ekaine.postgresql.db import MiningMapsDB

logger = get_logger(__name__)

cmd_group = cmd_base.group(name="mining-maps", description="Mining map submission related commands")

ALLOWLISTED_DISCORD_USERNAMES = [
    "remiscarlet",
]


def ekaine_bot_superuser_check() -> Callable[[Any], Any]:
    async def predicate(ctx: BaseContext) -> bool:
        logger.info(pformat(ctx))
        logger.info(pformat(ctx.author))
        return ctx.author.username in ALLOWLISTED_DISCORD_USERNAMES

    return check(predicate)


async def log_and_send_error_embed(ctx: SlashContext, msg: str) -> None:
    logger.warning(msg)
    return await send_error_embed(ctx, msg)


def mining_map_commodities_to_embed_str(mining_map: MiningMapsDB) -> str:
    embed_commodities_str = ""
    for commodity in mining_map.commodities:
        tonnage = commodity.approximate_tonnage_solo
        name = commodity.commodity_sym
        if tonnage is not None:
            embed_commodities_str += f"- `{name}` ({tonnage}T)\n"
        else:
            embed_commodities_str += f"- `{name}`\n"
    return embed_commodities_str


def mining_map_to_embed(mining_map: MiningMapsDB) -> Embed:
    description = f"**Map URL:** {mining_map.map_url}"

    fields = [EmbedField("Ring Name", mining_map.ring.name, inline=True)]

    if mining_map.rock_count is not None:
        fields.append(EmbedField("Rock Count", str(mining_map.rock_count), inline=True))

    if mining_map.approximate_merits_solo is not None:
        fields.append(EmbedField("Approximate Merits (Solo)", str(mining_map.approximate_merits_solo), inline=True))

    fields.append(EmbedField("Commodities", mining_map_commodities_to_embed_str(mining_map), inline=False))

    return Embed(
        title=mining_map.name,
        description=description,
        fields=fields,
        color=0x3498DB,
    )


def mining_maps_diff_to_embed(old_mining_map: MiningMapsDB, new_mining_map: MiningMapsDB) -> Embed:
    logger.debug("Diffing:")
    logger.debug(old_mining_map)
    logger.debug(new_mining_map)

    # Map URL
    if old_mining_map.map_url == new_mining_map.map_url:
        description = f"**Map URL:** {new_mining_map.map_url}"
    else:
        description = (
            "**DIFF:**\n" "**Map URL:**\n" f"_From:_ {old_mining_map.map_url}\n" f"_To:_ {new_mining_map.map_url}"
        )

    # Ring Name
    if old_mining_map.ring.name == new_mining_map.ring.name:
        fields = [EmbedField("Ring Name", new_mining_map.ring.name, inline=True)]
    else:
        val = "**DIFF:**\n" f"{old_mining_map.ring.name}\n" "->\n" f"{new_mining_map.ring.name}\n"
        fields = [EmbedField("Ring Name", val, inline=True)]

    # Rock Count
    if old_mining_map.rock_count == new_mining_map.rock_count and new_mining_map.rock_count is not None:
        fields.append(EmbedField("Ring Count", str(new_mining_map.rock_count), inline=True))
    elif new_mining_map.rock_count is not None:
        val = "**DIFF:**\n" f"{old_mining_map.rock_count}\n" "->\n" f"{new_mining_map.rock_count}"
        fields.append(EmbedField("Rock Count", val, inline=True))

    # Approx Merits
    if (
        old_mining_map.approximate_merits_solo == new_mining_map.approximate_merits_solo
        and new_mining_map.approximate_merits_solo is not None
    ):
        fields.append(EmbedField("Approximate Merits (Solo)", str(new_mining_map.approximate_merits_solo), inline=True))
    elif new_mining_map.approximate_merits_solo is not None:
        val = (
            "**DIFF:**\n"
            f"{old_mining_map.approximate_merits_solo}\n"
            "->\n"
            f"{new_mining_map.approximate_merits_solo}"
        )
        fields.append(EmbedField("Rock Count", val, inline=True))

    # Map Commodities
    if old_mining_map.commodities == new_mining_map.commodities and new_mining_map.commodities:
        fields.append(EmbedField("Commodities", mining_map_commodities_to_embed_str(new_mining_map), inline=False))
    else:
        val = (
            "**DIFF:**\n"
            f"{mining_map_commodities_to_embed_str(old_mining_map)}\n"
            "->\n"
            f"{mining_map_commodities_to_embed_str(new_mining_map)}"
        )
        fields.append(EmbedField("Commodities", val, inline=False))

    if old_mining_map.name == new_mining_map.name:
        title = new_mining_map.name
    else:
        title = f"NAME CHANGE: {old_mining_map.name} -> {new_mining_map.name}"

    return Embed(
        title=title,
        description=description,
        fields=fields,
        color=0x3498DB,
    )
