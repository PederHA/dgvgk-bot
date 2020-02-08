"""
Add/remove bot cogs in this module.
"""

from discord.ext import commands

from cogs.admin_cog import AdminCog
from cogs.mc_cog import MinecraftCog
from cogs.stats_cog import StatsCog
from cogs.user_cog import UserCog


# List of all cogs in the local namespace
# This should be imported in the bot's main module
COGS = [
    v for k, v in dict(locals()).items()
    if k.endswith("Cog") and issubclass(v, commands.Cog)
]
