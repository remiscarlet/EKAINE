from collections import namedtuple

from interactions import Embed, SlashCommand, SlashContext

from ekaine.postgresql.types import MiningAcquisitionResult

cmd_base = SlashCommand(name="ekaine", description="EKAINE bot commands base")


async def send_error_embed(ctx: SlashContext, msg: str) -> None:
    await ctx.send(
        embed=Embed(
            title="Error!",
            description=msg,
            color=0xFF1111,
        ),
        ephemeral=True,
    )


StationPriceDemand = namedtuple("StationPriceDemand", ["station", "price", "demand"])


class MineableDataDisplay:
    name: str
    mineable_rings: set[str]
    sell_stations: set[StationPriceDemand]

    def __init__(self, commodity_name: str) -> None:
        self.name = commodity_name
        self.mineable_rings = set()
        self.sell_stations = set()

    def add_route(self, route: MiningAcquisitionResult) -> None:
        if route.commodity != self.name:
            raise ValueError(f"Tried adding invalid route for MineableDataDisplay '{self.name}'")

        self.mineable_rings.add(route.ring_name)
        self.sell_stations.add(StationPriceDemand(route.station_name, route.sell_price, route.demand))
