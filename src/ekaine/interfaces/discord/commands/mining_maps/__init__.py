from interactions import Embed, EmbedField

from ekaine.interfaces.discord import cmd_base
from ekaine.postgresql.db import MiningMapsDB

cmd_group = cmd_base.group(name="mining-maps", description="Mining map submission related commands")


def mining_map_to_embed(mining_map: MiningMapsDB) -> Embed:
    description = f"**Map URL:** {mining_map.map_url}"

    fields = []
    fields.append(EmbedField("Map ID", str(mining_map.id), inline=True))
    fields.append(EmbedField("Ring Name", mining_map.ring.name, inline=True))

    if mining_map.rock_count is not None:
        fields.append(EmbedField("Ring Count", str(mining_map.rock_count), inline=True))

    if mining_map.approximate_merits_solo is not None:
        fields.append(EmbedField("Approximate Merits (Solo)", str(mining_map.approximate_merits_solo), inline=True))

    embed_commodities_str = ""
    for commodity in mining_map.commodities:
        tonnage = commodity.approximate_tonnage_solo
        name = commodity.commodity_sym
        if tonnage is not None:
            embed_commodities_str += f"- `{name}` ({tonnage}T)\n"
        else:
            embed_commodities_str += f"- `{name}`\n"

    fields.append(EmbedField("Commodities", embed_commodities_str, inline=False))

    return Embed(
        title=mining_map.name,
        description=description,
        fields=fields,
        color=0x3498DB,
    )
