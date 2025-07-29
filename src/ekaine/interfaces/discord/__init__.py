from collections import namedtuple
from typing import Any, Callable, TypeVar

from interactions import Embed, OptionType, SlashCommand, SlashContext, slash_option

from ekaine.common.constants import ENVIRONMENT_TYPE
from ekaine.postgresql.types import MiningAcquisitionResult

cmd_base_name = "ekaine" if ENVIRONMENT_TYPE == "production" else "ekaine-dev"

cmd_base = SlashCommand(name=cmd_base_name, description="EKAINE bot commands base")

# Monkey Patch: Set ephemeral to True by default for all commands.
_original_send = SlashContext.send
_original_defer = SlashContext.defer


async def _patched_send(
    self: Any,
    *args: Any,
    ephemeral: bool = True,
    **kwargs: Any,
) -> Any:
    return await _original_send(
        self,
        *args,
        ephemeral=(True if ephemeral is None else ephemeral),
        **kwargs,
    )


async def _patched_defer(
    self: Any,
    *args: Any,
    ephemeral: bool = True,
    **kwargs: Any,
) -> Any:
    return await _original_defer(
        self,
        *args,
        ephemeral=(True if ephemeral is None else ephemeral),
        **kwargs,
    )


SlashContext.send = _patched_send  # type: ignore
SlashContext.defer = _patched_defer  # type: ignore


T = TypeVar("T", bound=Callable[..., Any])


def ephemeral_option(func: Any) -> Any:
    """Adds an `ephemeral: bool` slash-option (defaults to True)."""
    return slash_option(
        name="ephemeral",
        description="Show bot response only to yourself? Defaults to True",
        opt_type=OptionType.BOOLEAN,
        required=False,
    )(func)


async def send_error_embed(ctx: Any, msg: str) -> None:
    await ctx.send(
        embed=Embed(title="Error!", description=msg, color=0xFF1111),
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
        if route.commodity_sym != self.name:
            raise ValueError(f"Tried adding invalid route for MineableDataDisplay '{self.name}'")

        self.mineable_rings.add(route.ring_name)
        self.sell_stations.add(StationPriceDemand(route.station_name, route.sell_price, route.demand))
