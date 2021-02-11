import sys
from contextlib import suppress
from typing import List, Optional

with suppress(ImportError):
    import uvloop
    uvloop.install()

from discord.ext.commands import Bot, Cog, Command

from .botsecrets import BOT_TOKEN
from .cogs import COGS
from .config import load
from .utils.patching.commands import patch_command_signature

patch_command_signature(Command)


def run(config_path: str="config.yml", *, cogs: Optional[List[Cog]]=None) -> None:       
    if not cogs:
        cogs = []
    cogs.extend(COGS)
    
    # Bot setup
    bot = Bot(command_prefix="?", description="De Gode Venners Gamingkrok Bot", pm_help=False)
    setattr(bot, "config", load())
    
    # Add cogs
    for cog in cogs:
        bot.add_cog(cog(bot=bot))

    # Run bot
    bot.run(bot.config["discord"]["token"])
