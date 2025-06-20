import logging

from interactions import (
    Client,
    Intents,
    listen,
)

from ekaine.common.constants import DEV_GUILD_ID, DISCORD_BOT_TOKEN
from ekaine.common.logging import configure_logger, get_logger
from ekaine.interfaces.discord import cmd_base
from ekaine.interfaces.discord.commands import *  # noqa: F401, F403

logger = get_logger(__name__)

bot = Client(intents=Intents.DEFAULT, debug_scope=DEV_GUILD_ID)

# @cmd_base.subcommand(sub_cmd_name="hello2", sub_cmd_description="foobar")
# async def hello2(ctx: SlashContext) -> None:
#     await send_error_embed(ctx, "Foobar!")
#     return

bot.add_interaction(cmd_base)


@listen()
async def on_ready() -> None:
    logger.info("Ready")
    logger.info(f"This bot is owned by {bot.owner}")


configure_logger(logging.INFO)
bot.start(DISCORD_BOT_TOKEN)
