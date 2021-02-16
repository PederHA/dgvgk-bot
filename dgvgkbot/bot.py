import sys
from contextlib import suppress
from typing import List, Optional, Dict, Any

with suppress(ImportError):
    import uvloop
    uvloop.install()

from discord.ext.commands import Bot, Cog, Command

from .cogs import COGS
from .config import load
from .utils.patching.commands import patch_command_signature
from .db import init_db, DatabaseConnection

patch_command_signature(Command)

class DiscordBot(Bot):
    db: DatabaseConnection
    config: Dict[str, Any]

    def set_db(self, db: DatabaseConnection) -> None:
        """Sets the `db` attribute of bot to an instance of `db.DatabaseConnection`"""
        self.db = db
    
    def set_config(self, config: Dict[str, Any]) -> None:
        self.config = config


def run(config_path: str="config.yml", *, cogs: Optional[List[Cog]]=None) -> None:       
    if not cogs:
        cogs = []
    cogs.extend(COGS)
    
    # Bot setup
    bot = DiscordBot(command_prefix="?", description="De Gode Venners Gamingkrok Bot", pm_help=False)
    bot.set_config(load())
    bot.set_db(init_db(bot))

    # Add cogs
    for cog in cogs:
        bot.add_cog(cog(bot=bot))

    # Run bot
    bot.run(bot.config["discord"]["token"])
