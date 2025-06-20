from pprint import pformat
from typing import Any, Callable

from interactions import BaseContext, SlashContext, check

from ekaine.common.logging import get_logger
from ekaine.interfaces.discord.commands.mining_maps import cmd_group

logger = get_logger(__name__)


def my_check() -> Callable[[Any], Any]:
    async def predicate(ctx: BaseContext) -> bool:
        logger.info(pformat(ctx))
        logger.info(pformat(ctx.author))
        return ctx.author.username.startswith("a")

    return check(predicate)


@cmd_group.subcommand(sub_cmd_name="submit", sub_cmd_description="Submit a new Mining map")
@my_check()
async def submit_mining_map(ctx: SlashContext) -> None:
    logger.info(pformat(ctx))
    pass
