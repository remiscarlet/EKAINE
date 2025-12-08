import traceback
from collections import namedtuple
from typing import Any, Awaitable, Callable, Concatenate, ParamSpec, TypeVar, Union

from interactions import (
    AutocompleteContext,
    Embed,
    OptionType,
    SlashCommand,
    SlashContext,
    slash_option,
)

from ekaine.common.constants import IS_PROD
from ekaine.common.logging import get_logger
from ekaine.postgresql.types import MiningAcquisitionResult

logger = get_logger(__name__)

cmd_base_name = "ekaine" if IS_PROD else "ekaine-dev"

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


P = ParamSpec("P")
R = TypeVar("R")
Ctx = TypeVar("Ctx", SlashContext, AutocompleteContext)


def discord_handler_wrapper(
    **error_kwargs: Any,
) -> Callable[[Callable[Concatenate[Ctx, P], Awaitable[R]]], Callable[Concatenate[Ctx, P], Awaitable[Union[R, None]]]]:
    """Gracefully catches any errors and returns error embeds if so.

    The decorator accepts async callables whose first parameter is a context-like
    object (ctx) followed by arbitrary other parameters (captured by ParamSpec P).
    Using Concatenate[Ctx, P] preserves those parameter types for the type checker.
    """

    def decorator(
        func: Callable[Concatenate[Ctx, P], Awaitable[R]],
    ) -> Callable[Concatenate[Ctx, P], Awaitable[Union[R, None]]]:
        async def wrapper(ctx: Ctx, /, *args: P.args, **kwargs: P.kwargs) -> R | None:
            try:
                return await func(ctx, *args, **kwargs)
            except Exception:
                logger.warning(traceback.format_exc())
                if not error_kwargs:
                    await send_error_embed(ctx, "Uncaught discord handler error!")
                else:
                    await ctx.send(**error_kwargs)
                return None

        return wrapper

    return decorator


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
