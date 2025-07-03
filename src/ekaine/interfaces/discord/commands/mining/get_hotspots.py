from collections import defaultdict
from itertools import batched
from pprint import pformat

from interactions import Embed, OptionType, SlashContext, slash_option

from ekaine.common.logging import get_logger
from ekaine.interfaces.discord import ephemeral_option, send_error_embed
from ekaine.interfaces.discord.commands.mining import cmd_group
from ekaine.postgresql.adapter import (
    ApiCommandAdapter,
    SystemsAdapter,
)
from ekaine.postgresql.types import HotspotResult

logger = get_logger(__name__)


@cmd_group.subcommand(sub_cmd_name="get-hotspots", sub_cmd_description="Get list of hotspots in a given system")
@slash_option(
    name="system_name", description="Target system name to acquire", required=True, opt_type=OptionType.STRING
)
@ephemeral_option
async def get_hotspots(ctx: SlashContext, system_name: str, ephemeral: bool = True) -> None:
    await ctx.defer(ephemeral=ephemeral)

    try:
        SystemsAdapter().get_system(system_name)
    except ValueError:
        await send_error_embed(ctx, f"Could not find system '{system_name}'!")
        return

    hotspots = ApiCommandAdapter().get_hotspots_in_system(system_name)

    results_by_commodity: dict[str, list[HotspotResult]] = defaultdict(lambda: list())
    for hotspot in hotspots:
        name = hotspot.commodity
        results_by_commodity[name].append(hotspot)

    logger.info(pformat(results_by_commodity))

    embeds: list[Embed] = []
    for commodity_name in sorted(results_by_commodity.keys()):
        hotspots = results_by_commodity[commodity_name]

        ring_names = list(map(lambda hs: f"=> {hs.ring_name} (x{hs.count}) ({hs.ring_type})", hotspots))
        hotspots_str = "**Mine In**:\n"
        hotspots_str += "\n".join(ring_names)
        embed = Embed(
            title=f"{commodity_name} Hotspots ({system_name})",
            description=hotspots_str,
            color=0x3498DB,
        )

        embeds.append(embed)

    embeds.sort(key=lambda e: e.title or "")
    for embeds_batch in batched(embeds, 10):
        await ctx.send(embeds=list(embeds_batch), ephemeral=ephemeral)
